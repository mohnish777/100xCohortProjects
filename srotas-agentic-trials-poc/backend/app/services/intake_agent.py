import logging
import re

from app.core.config import settings
from app.domain.models import (
    CancerTrack,
    IntakeAgentOutput,
    IntakeFactValue,
    IntakeMissingFact,
)


logger = logging.getLogger(__name__)


INTAKE_AGENT_SYSTEM_PROMPT = """You are the Patient Intake Agent for a mixed-oncology trial prescreening system.

Your job is to convert a patient or caregiver's free-text clinical history into structured clinical facts.

Rules:
- Extract only facts directly supported by the transcript.
- Do not diagnose, advise, or recommend treatment.
- Do not invent missing biomarker values.
- Use reusable snake_case fact keys from the known registry.
- Put unknown but important facts in missing_facts with a clear follow-up question.
- Return short evidence quotes from the transcript for every extracted value.
- Keep the output useful for trial matching, not for clinical decision-making.
"""


KNOWN_INTAKE_FACT_KEYS = """
Known fact registry keys:
- cancer_type: text
- histology: text
- metastatic: boolean
- pd_l1_tps: number, percent
- egfr_mutation: boolean
- prior_immunotherapy: boolean
- her2_status: text
- psa: number, ng/mL
"""


QUESTION_TEMPLATES = {
    "cancer_type": "What type of cancer were you diagnosed with?",
    "histology": "Do your reports mention NSCLC, SCLC, or another subtype?",
    "metastatic": "Has your cancer spread, or has it been called metastatic or stage IV?",
    "pd_l1_tps": "Do you have a PD-L1 TPS percentage on your pathology report?",
    "egfr_mutation": "Do your reports mention an EGFR mutation result?",
    "prior_immunotherapy": "Have you received immunotherapy before?",
    "her2_status": "Do you know whether your breast cancer is HER2 positive or negative?",
    "psa": "Do you know your latest PSA value?",
}


DISPLAY_NAMES = {
    "cancer_type": "Cancer type",
    "histology": "Histology",
    "metastatic": "Metastatic disease",
    "pd_l1_tps": "PD-L1 TPS",
    "egfr_mutation": "EGFR mutation",
    "prior_immunotherapy": "Prior immunotherapy",
    "her2_status": "HER2 status",
    "psa": "PSA",
}


VALUE_TYPES = {
    "cancer_type": "text",
    "histology": "text",
    "metastatic": "boolean",
    "pd_l1_tps": "number",
    "egfr_mutation": "boolean",
    "prior_immunotherapy": "boolean",
    "her2_status": "text",
    "psa": "number",
}


TRACK_REQUIRED_FACTS: dict[CancerTrack, list[str]] = {
    "lung": [
        "cancer_type",
        "histology",
        "metastatic",
        "pd_l1_tps",
        "egfr_mutation",
        "prior_immunotherapy",
    ],
    "breast": ["cancer_type", "metastatic", "her2_status"],
    "prostate": ["cancer_type", "metastatic", "psa"],
    "mixed": ["cancer_type", "metastatic"],
}


def extract_intake_with_agent(transcript: str) -> tuple[IntakeAgentOutput, str]:
    context = _select_intake_context(transcript)
    logger.info(
        "Intake Agent started transcript_chars=%d context_chars=%d openai_key_configured=%s model=%s",
        len(transcript),
        len(context),
        bool(settings.openai_api_key),
        settings.openai_model,
    )

    if not settings.openai_api_key:
        logger.info("Intake Agent using deterministic fallback reason=no_openai_api_key")
        return _fallback_extract(context), "deterministic"

    try:
        from openai import OpenAI

        logger.info("Intake Agent calling OpenAI structured extraction model=%s", settings.openai_model)
        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )
        completion = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": INTAKE_AGENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"{KNOWN_INTAKE_FACT_KEYS}\n\n"
                        "Extract oncology prescreening facts from this intake transcript.\n\n"
                        f"Transcript:\n{context}"
                    ),
                },
            ],
            response_format=IntakeAgentOutput,
        )

        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("OpenAI returned no parsed structured output.")

        parsed = _normalize_output(parsed)
        logger.info(
            "Intake Agent OpenAI structured extraction succeeded request_id=%s facts=%d missing=%d confidence=%.2f",
            getattr(completion, "_request_id", None),
            len(parsed.extracted_facts),
            len(parsed.missing_facts),
            parsed.confidence,
        )
        return parsed, "openai_structured"
    except Exception as exc:
        logger.warning(
            "Intake Agent OpenAI structured extraction failed; using deterministic fallback error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return _fallback_extract(context), "deterministic"


def make_transcript_excerpt(transcript: str, max_chars: int = 420) -> str:
    normalized = " ".join(transcript.split())
    if len(normalized) <= max_chars:
        return normalized

    return f"{normalized[:max_chars].rstrip()}..."


def _select_intake_context(transcript: str, max_chars: int = 12000) -> str:
    return "\n".join(line.strip() for line in transcript.splitlines() if line.strip())[:max_chars]


def _fallback_extract(transcript: str) -> IntakeAgentOutput:
    logger.info("Intake Agent deterministic fallback started context_chars=%d", len(transcript))
    lower = transcript.lower()
    facts: list[IntakeFactValue] = []

    cancer_track = _infer_cancer_track(lower)
    if cancer_track != "mixed":
        _append_fact(
            facts,
            fact_key="cancer_type",
            value=cancer_track,
            evidence=_quote_around(transcript, [f"{cancer_track} cancer", cancer_track]),
            confidence=0.88,
        )

    histology = _extract_histology(lower)
    if histology:
        _append_fact(
            facts,
            fact_key="histology",
            value=histology,
            evidence=_quote_around(transcript, ["non-small cell", "nsclc", "small cell", "sclc"]),
            confidence=0.9,
        )

    metastatic_value = _extract_metastatic(lower)
    if metastatic_value is not None:
        _append_fact(
            facts,
            fact_key="metastatic",
            value=metastatic_value,
            evidence=_quote_around(
                transcript,
                ["metastatic", "stage iv", "stage 4", "spread", "not spread", "no metastasis"],
            ),
            confidence=0.82,
        )

    pdl1_value = _extract_pdl1_value(lower)
    if pdl1_value is not None:
        _append_fact(
            facts,
            fact_key="pd_l1_tps",
            value=pdl1_value,
            evidence=_quote_around(transcript, ["pd-l1", "pdl1", "tumor proportion score", "tps"]),
            confidence=0.86,
        )

    egfr_value = _extract_egfr_value(lower)
    if egfr_value is not None:
        _append_fact(
            facts,
            fact_key="egfr_mutation",
            value=egfr_value,
            evidence=_quote_around(transcript, ["egfr"]),
            confidence=0.84,
        )

    immunotherapy_value = _extract_prior_immunotherapy(lower)
    if immunotherapy_value is not None:
        _append_fact(
            facts,
            fact_key="prior_immunotherapy",
            value=immunotherapy_value,
            evidence=_quote_around(
                transcript,
                ["immunotherapy", "keytruda", "pembrolizumab", "nivolumab"],
            ),
            confidence=0.83,
        )

    her2_status = _extract_her2_status(lower)
    if her2_status:
        _append_fact(
            facts,
            fact_key="her2_status",
            value=her2_status,
            evidence=_quote_around(transcript, ["her2", "her-2"]),
            confidence=0.85,
        )

    psa_value = _extract_psa_value(lower)
    if psa_value is not None:
        _append_fact(
            facts,
            fact_key="psa",
            value=psa_value,
            evidence=_quote_around(transcript, ["psa"]),
            confidence=0.84,
        )

    output = IntakeAgentOutput(
        patient_summary=_build_patient_summary(cancer_track, facts),
        inferred_cancer_track=cancer_track,
        extracted_facts=facts,
        missing_facts=_build_missing_facts(cancer_track, facts),
        follow_up_questions=[],
        trace_notes=[
            "Read the intake transcript without external retrieval.",
            "Mapped patient language to reusable clinical fact keys.",
            "Separated known values from missing follow-up questions.",
        ],
        confidence=0.78,
    )

    output = _normalize_output(output)
    logger.info(
        "Intake Agent deterministic fallback completed facts=%d missing=%d cancer_track=%s",
        len(output.extracted_facts),
        len(output.missing_facts),
        output.inferred_cancer_track,
    )
    return output


def _append_fact(
    facts: list[IntakeFactValue],
    *,
    fact_key: str,
    value: bool | str | float,
    evidence: str,
    confidence: float,
) -> None:
    if any(fact.fact_key == fact_key for fact in facts):
        return

    facts.append(
        IntakeFactValue(
            fact_key=fact_key,
            display_name=DISPLAY_NAMES[fact_key],
            value_type=VALUE_TYPES[fact_key],
            value=value,
            display_value=_display_value(fact_key, value),
            evidence=evidence or "Supported by patient intake transcript.",
            confidence=confidence,
        )
    )


def _build_missing_facts(
    cancer_track: CancerTrack,
    extracted_facts: list[IntakeFactValue],
) -> list[IntakeMissingFact]:
    extracted_keys = {fact.fact_key for fact in extracted_facts}
    required_keys = TRACK_REQUIRED_FACTS[cancer_track]
    missing_keys = [fact_key for fact_key in required_keys if fact_key not in extracted_keys]

    return [
        IntakeMissingFact(
            fact_key=fact_key,
            display_name=DISPLAY_NAMES[fact_key],
            question=QUESTION_TEMPLATES[fact_key],
            reason="Needed for trial prescreening but not present in the intake transcript.",
        )
        for fact_key in missing_keys
    ]


def _normalize_output(output: IntakeAgentOutput) -> IntakeAgentOutput:
    normalized_facts: list[IntakeFactValue] = []
    seen_fact_keys: set[str] = set()

    for fact in output.extracted_facts:
        fact_key = fact.fact_key
        if fact_key not in DISPLAY_NAMES or fact_key in seen_fact_keys:
            continue

        normalized_value = _normalize_fact_value(fact_key, fact.value)
        if normalized_value is None:
            continue

        seen_fact_keys.add(fact_key)
        fact.display_name = DISPLAY_NAMES[fact_key]
        fact.value_type = VALUE_TYPES[fact_key]
        fact.value = normalized_value
        fact.display_value = _display_value(fact_key, normalized_value)
        normalized_facts.append(fact)

    output.extracted_facts = normalized_facts

    if output.inferred_cancer_track == "mixed":
        output.inferred_cancer_track = _track_from_facts(normalized_facts)

    missing_by_key = {
        missing.fact_key: IntakeMissingFact(
            fact_key=missing.fact_key,
            display_name=DISPLAY_NAMES[missing.fact_key],
            question=missing.question or QUESTION_TEMPLATES[missing.fact_key],
            reason=missing.reason,
        )
        for missing in output.missing_facts
        if missing.fact_key in DISPLAY_NAMES and missing.fact_key not in seen_fact_keys
    }

    for missing in _build_missing_facts(output.inferred_cancer_track, normalized_facts):
        missing_by_key.setdefault(missing.fact_key, missing)

    output.missing_facts = list(missing_by_key.values())

    follow_up_questions = list(output.follow_up_questions)
    for missing in output.missing_facts:
        if missing.question not in follow_up_questions:
            follow_up_questions.append(missing.question)
    output.follow_up_questions = follow_up_questions

    return output


def _normalize_fact_value(
    fact_key: str,
    value: bool | str | float | None,
) -> bool | str | float | None:
    if value is None:
        return None

    if fact_key in {"metastatic", "egfr_mutation", "prior_immunotherapy"}:
        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()
        if normalized in {"true", "yes", "positive", "present"}:
            return True
        if normalized in {"false", "no", "negative", "absent"}:
            return False
        return None

    if fact_key == "cancer_type":
        normalized = str(value).strip().lower()
        for track in ["lung", "breast", "prostate"]:
            if track in normalized:
                return track
        return normalized or None

    if fact_key == "histology":
        normalized = str(value).strip().lower()
        if "non-small" in normalized or "nsclc" in normalized:
            return "NSCLC"
        if "small cell" in normalized or "sclc" in normalized:
            return "SCLC"
        return str(value).strip() or None

    if fact_key == "her2_status":
        normalized = str(value).strip().lower()
        if "positive" in normalized or "amplified" in normalized:
            return "positive"
        if "negative" in normalized or "low" in normalized:
            return "negative"
        return normalized or None

    if fact_key in {"pd_l1_tps", "psa"}:
        if isinstance(value, bool):
            return None

        match = re.search(r"\d+(?:\.\d+)?", str(value))
        if match:
            return float(match.group(0))
        return None

    return str(value).strip() or None


def _track_from_facts(facts: list[IntakeFactValue]) -> CancerTrack:
    cancer_fact = next((fact for fact in facts if fact.fact_key == "cancer_type"), None)
    if cancer_fact and cancer_fact.value in {"lung", "breast", "prostate"}:
        return cancer_fact.value

    if any(fact.fact_key in {"histology", "pd_l1_tps", "egfr_mutation"} for fact in facts):
        return "lung"

    if any(fact.fact_key == "her2_status" for fact in facts):
        return "breast"

    if any(fact.fact_key == "psa" for fact in facts):
        return "prostate"

    return "mixed"


def _infer_cancer_track(lower: str) -> CancerTrack:
    if "lung cancer" in lower or "nsclc" in lower or "non-small cell" in lower or "sclc" in lower:
        return "lung"

    if "breast cancer" in lower or "her2" in lower or "her-2" in lower:
        return "breast"

    if "prostate cancer" in lower or "psa" in lower:
        return "prostate"

    return "mixed"


def _extract_histology(lower: str) -> str | None:
    if "non-small cell" in lower or "nsclc" in lower:
        return "NSCLC"

    if "small cell" in lower or "sclc" in lower:
        return "SCLC"

    return None


def _extract_metastatic(lower: str) -> bool | None:
    negative_patterns = [
        r"\bnot\s+(?:spread|metastatic)\b",
        r"\bno\s+(?:metastasis|metastases|metastatic disease)\b",
        r"\bhas not spread\b",
    ]
    positive_patterns = [
        r"\bmetastatic\b",
        r"\bstage\s*(?:iv|4)\b",
        r"\bhas spread\b",
        r"\bspread to\b",
    ]

    if any(re.search(pattern, lower) for pattern in negative_patterns):
        return False

    if any(re.search(pattern, lower) for pattern in positive_patterns):
        return True

    return None


def _extract_pdl1_value(lower: str) -> float | None:
    if not any(keyword in lower for keyword in ["pd-l1", "pdl1", "tumor proportion score", "tps"]):
        return None

    if re.search(r"(?:do not|don't|dont|not sure|unknown|no idea)[^.;]{0,80}(?:pd-l1|pdl1|tps)", lower):
        return None

    patterns = [
        r"(?:pd-l1|pdl1|tumor proportion score|tps)[^.;:]{0,100}?(\d+(?:\.\d+)?)\s*(?:%|percent)",
        r"(\d+(?:\.\d+)?)\s*(?:%|percent)[^.;:]{0,100}?(?:pd-l1|pdl1|tumor proportion score|tps)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            return float(match.group(1))

    return None


def _extract_egfr_value(lower: str) -> bool | None:
    if "egfr" not in lower:
        return None

    negative_patterns = [
        r"egfr[^.;:]{0,80}?(?:negative|wild[- ]type|no mutation|without mutation)",
        r"(?:negative|wild[- ]type|no mutation|without mutation)[^.;:]{0,80}?egfr",
    ]
    positive_patterns = [
        r"egfr[^.;:]{0,80}?(?:positive|mutation|mutated|mutant)",
        r"(?:positive|mutation|mutated|mutant)[^.;:]{0,80}?egfr",
    ]

    if any(re.search(pattern, lower) for pattern in negative_patterns):
        return False

    if any(re.search(pattern, lower) for pattern in positive_patterns):
        return True

    return None


def _extract_prior_immunotherapy(lower: str) -> bool | None:
    terms = ["immunotherapy", "keytruda", "pembrolizumab", "nivolumab"]
    if not any(term in lower for term in terms):
        return None

    negative_patterns = [
        r"(?:never|no|not)\s+(?:had|received|taken|started)[^.;:]{0,80}(?:immunotherapy|keytruda|pembrolizumab|nivolumab)",
        r"(?:immunotherapy|keytruda|pembrolizumab|nivolumab)[^.;:]{0,80}(?:never|not received|no prior)",
    ]
    if any(re.search(pattern, lower) for pattern in negative_patterns):
        return False

    return True


def _extract_her2_status(lower: str) -> str | None:
    if "her2" not in lower and "her-2" not in lower:
        return None

    if re.search(r"(?:her2|her-2)[^.;:]{0,80}(?:negative|low)", lower):
        return "negative"

    if re.search(r"(?:her2|her-2)[^.;:]{0,80}(?:positive|amplified)", lower):
        return "positive"

    return None


def _extract_psa_value(lower: str) -> float | None:
    match = re.search(r"\bpsa[^.;:]{0,60}?(\d+(?:\.\d+)?)", lower)
    if match:
        return float(match.group(1))

    return None


def _display_value(fact_key: str, value: bool | str | float) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"

    if fact_key == "pd_l1_tps":
        return f"{float(value):g}%"

    if fact_key == "psa":
        return f"{float(value):g} ng/mL"

    return str(value)


def _build_patient_summary(cancer_track: CancerTrack, facts: list[IntakeFactValue]) -> str:
    if not facts:
        return "Patient intake did not include enough oncology details to structure yet."

    fact_summary = ", ".join(f"{fact.display_name}: {fact.display_value}" for fact in facts[:4])
    return f"Inferred {cancer_track} oncology intake with {fact_summary}."


def _quote_around(text: str, keywords: list[str], radius: int = 170) -> str:
    lower = text.lower()
    for keyword in keywords:
        index = lower.find(keyword)
        if index >= 0:
            start = max(index - radius, 0)
            end = min(index + radius, len(text))
            return " ".join(text[start:end].split())
    return ""
