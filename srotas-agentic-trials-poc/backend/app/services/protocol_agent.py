import logging
import re

from app.core.config import settings
from app.domain.models import (
    ProtocolAgentCriterion,
    ProtocolAgentFact,
    ProtocolAgentOutput,
)


logger = logging.getLogger(__name__)


PROTOCOL_AGENT_SYSTEM_PROMPT = """You are the Protocol Agent for a mixed-oncology trial matching system.

Your job is to read clinical trial protocol text and extract structured eligibility facts.

Rules:
- Focus on inclusion and exclusion criteria only.
- Extract facts that can be stored in a clinical fact registry.
- Prefer reusable snake_case fact keys, such as cancer_type, histology, metastatic, pd_l1_tps.
- Return short source quotes copied from the protocol text.
- Do not invent criteria that are not supported by the protocol text.
- If a criterion is ambiguous, include it only when there is a clear source quote.
- Keep patient safety in mind: this is trial pre-screening, not medical advice.
"""


KNOWN_FACT_KEYS = """
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


def select_protocol_context(protocol_text: str, max_chars: int = 14000) -> str:
    normalized = "\n".join(line.strip() for line in protocol_text.splitlines() if line.strip())
    lower = normalized.lower()
    keywords = [
        "inclusion criteria",
        "exclusion criteria",
        "eligible",
        "eligibility",
        "non-small cell",
        "nsclc",
        "pd-l1",
        "pdl1",
        "tumor proportion score",
        "egfr",
        "metastatic",
        "stage iv",
    ]

    windows: list[str] = []
    for keyword in keywords:
        index = lower.find(keyword)
        if index >= 0:
            start = max(index - 1400, 0)
            end = min(index + 2600, len(normalized))
            windows.append(normalized[start:end])

    if not windows:
        return normalized[:max_chars]

    deduped: list[str] = []
    seen: set[str] = set()
    for window in windows:
        fingerprint = window[:180]
        if fingerprint not in seen:
            seen.add(fingerprint)
            deduped.append(window)

    context = "\n\n---\n\n".join(deduped)
    return context[:max_chars]


def extract_protocol_with_agent(protocol_text: str) -> tuple[ProtocolAgentOutput, str]:
    context = select_protocol_context(protocol_text)
    logger.info(
        "Protocol Agent started protocol_chars=%d context_chars=%d openai_key_configured=%s model=%s",
        len(protocol_text),
        len(context),
        bool(settings.openai_api_key),
        settings.openai_model,
    )

    if not settings.openai_api_key:
        logger.info("Protocol Agent using deterministic fallback reason=no_openai_api_key")
        return _fallback_extract(context), "deterministic"

    try:
        from openai import OpenAI

        logger.info("Protocol Agent calling OpenAI structured extraction model=%s", settings.openai_model)
        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )
        completion = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": PROTOCOL_AGENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"{KNOWN_FACT_KEYS}\n\n"
                        "Extract trial eligibility facts and criteria from this protocol text.\n\n"
                        f"Protocol text:\n{context}"
                    ),
                },
            ],
            response_format=ProtocolAgentOutput,
        )

        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("OpenAI returned no parsed structured output.")

        logger.info(
            "Protocol Agent OpenAI structured extraction succeeded request_id=%s facts=%d criteria=%d confidence=%.2f",
            getattr(completion, "_request_id", None),
            len(parsed.extracted_facts),
            len(parsed.extracted_criteria),
            parsed.confidence,
        )
        return parsed, "openai_structured"
    except Exception as exc:
        logger.warning(
            "Protocol Agent OpenAI structured extraction failed; using deterministic fallback error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return _fallback_extract(context), "deterministic"


def _fallback_extract(context: str) -> ProtocolAgentOutput:
    logger.info("Protocol Agent deterministic fallback started context_chars=%d", len(context))
    lower = context.lower()
    facts: list[ProtocolAgentFact] = []
    criteria: list[ProtocolAgentCriterion] = []

    cancer_quote = _quote_around(context, ["non-small cell", "nsclc", "lung cancer"])
    if cancer_quote:
        facts.append(
            ProtocolAgentFact(
                key="cancer_type",
                display_name="Cancer type",
                description="Primary cancer type required by the protocol.",
                value_type="text",
                oncology_track="mixed",
                question_template="What type of cancer were you diagnosed with?",
                source_quote=cancer_quote,
                confidence=0.82,
            )
        )
        criteria.append(
            ProtocolAgentCriterion(
                criterion_type="inclusion",
                fact_key="cancer_type",
                operator="=",
                expected_value="lung",
                display="Cancer type equals lung",
                source_quote=cancer_quote,
                confidence=0.82,
            )
        )

    histology_quote = _quote_around(context, ["non-small cell", "nsclc"])
    if histology_quote:
        facts.append(
            ProtocolAgentFact(
                key="histology",
                display_name="Histology",
                description="Cancer subtype such as NSCLC or SCLC.",
                value_type="text",
                oncology_track="lung",
                question_template="Do your reports mention NSCLC, SCLC, or another subtype?",
                source_quote=histology_quote or "Protocol mentions NSCLC.",
                confidence=0.9,
            )
        )
        criteria.append(
            ProtocolAgentCriterion(
                criterion_type="inclusion",
                fact_key="histology",
                operator="=",
                expected_value="NSCLC",
                display="Histology equals NSCLC",
                source_quote=histology_quote or "Protocol mentions NSCLC.",
                confidence=0.9,
            )
        )

    metastatic_quote = _quote_around(context, ["metastatic", "stage iv", "stage 4"])
    if not metastatic_quote:
        advanced_quote = _quote_around(context, ["advanced"])
        if _is_advanced_disease_quote(advanced_quote):
            metastatic_quote = advanced_quote

    if metastatic_quote:
        metastatic_operator, metastatic_value, metastatic_display = _extract_metastatic_requirement(
            metastatic_quote
        )
        facts.append(
            ProtocolAgentFact(
                key="metastatic",
                display_name="Metastatic disease",
                description="Whether cancer is metastatic or advanced.",
                value_type="boolean",
                oncology_track="mixed",
                question_template="Has your cancer spread or been called metastatic?",
                source_quote=metastatic_quote,
                confidence=0.78,
            )
        )
        criteria.append(
            ProtocolAgentCriterion(
                criterion_type="inclusion",
                fact_key="metastatic",
                operator=metastatic_operator,
                expected_value=metastatic_value,
                display=metastatic_display,
                source_quote=metastatic_quote,
                confidence=0.78 if metastatic_value is not None else 0.68,
            )
        )

    if "pd-l1" in lower or "pdl1" in lower or "tumor proportion score" in lower:
        pdl1_quote = _quote_around(context, ["pd-l1", "pdl1", "tumor proportion score"])
        threshold = _extract_pdl1_threshold(pdl1_quote)
        facts.append(
            ProtocolAgentFact(
                key="pd_l1_tps",
                display_name="PD-L1 TPS",
                description="PD-L1 tumor proportion score used for lung immunotherapy eligibility.",
                value_type="number",
                unit="%",
                oncology_track="lung",
                question_template="Do you have a PD-L1 TPS percentage on your pathology report?",
                source_quote=pdl1_quote or "Protocol mentions PD-L1 expression.",
                confidence=0.86,
            )
        )
        if threshold is None:
            criteria.append(
                ProtocolAgentCriterion(
                    criterion_type="inclusion",
                    fact_key="pd_l1_tps",
                    operator="is_known",
                    expected_value=None,
                    display="PD-L1 TPS must be documented",
                    source_quote=pdl1_quote or "Protocol mentions PD-L1 expression.",
                    confidence=0.72,
                )
            )
        else:
            criteria.append(
                ProtocolAgentCriterion(
                    criterion_type="inclusion",
                    fact_key="pd_l1_tps",
                    operator=">=",
                    expected_value=threshold,
                    display=f"PD-L1 TPS is at least {threshold:g}%",
                    source_quote=pdl1_quote or "Protocol mentions PD-L1 expression.",
                    confidence=0.82,
                )
            )

    if "egfr" in lower:
        egfr_quote = _quote_around(context, ["egfr"])
        egfr_operator, egfr_value, egfr_display = _extract_egfr_requirement(egfr_quote)
        facts.append(
            ProtocolAgentFact(
                key="egfr_mutation",
                display_name="EGFR mutation",
                description="Whether an EGFR mutation is present.",
                value_type="boolean",
                oncology_track="lung",
                question_template="Do your reports mention an EGFR mutation?",
                source_quote=egfr_quote or "Protocol mentions EGFR mutation.",
                confidence=0.84,
            )
        )
        criteria.append(
            ProtocolAgentCriterion(
                criterion_type="inclusion",
                fact_key="egfr_mutation",
                operator=egfr_operator,
                expected_value=egfr_value,
                display=egfr_display,
                source_quote=egfr_quote or "Protocol mentions EGFR mutation.",
                confidence=0.84 if egfr_value is not None else 0.68,
            )
        )

    cancer_track = "lung" if any(fact.oncology_track == "lung" for fact in facts) else "mixed"

    output = ProtocolAgentOutput(
        trial_title="Uploaded Oncology Protocol",
        cancer_track=cancer_track,
        protocol_summary="Protocol Agent extracted oncology eligibility criteria from uploaded protocol text.",
        extracted_facts=facts,
        extracted_criteria=criteria,
        trace_notes=[
            "Selected eligibility-focused protocol context.",
            "Mapped protocol language to reusable clinical fact keys.",
            "Returned strict structured extraction output.",
        ],
        confidence=0.78,
    )
    logger.info(
        "Protocol Agent deterministic fallback completed facts=%d criteria=%d cancer_track=%s",
        len(output.extracted_facts),
        len(output.extracted_criteria),
        output.cancer_track,
    )
    return output


def _quote_around(text: str, keywords: list[str], radius: int = 220) -> str:
    lower = text.lower()
    for keyword in keywords:
        index = lower.find(keyword)
        if index >= 0:
            start = max(index - radius, 0)
            end = min(index + radius, len(text))
            return " ".join(text[start:end].split())
    return ""


def _extract_pdl1_threshold(pdl1_quote: str) -> float | None:
    if not pdl1_quote:
        return None

    quote = " ".join(pdl1_quote.lower().split())
    mentions_pdl1 = any(
        keyword in quote
        for keyword in ["pd-l1", "pdl1", "tumor proportion score", "tps"]
    )

    if not mentions_pdl1:
        return None

    threshold_patterns = [
        r"(?:pd-l1|pdl1|tumor proportion score|tps)[^.;:]{0,140}?(?:>=|≥|at least|greater than or equal to|of at least)\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?",
        r"(?:>=|≥|at least|greater than or equal to|of at least)\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?[^.;:]{0,140}?(?:pd-l1|pdl1|tumor proportion score|tps)",
    ]

    for pattern in threshold_patterns:
        match = re.search(pattern, quote)
        if match:
            return float(match.group(1))

    return None


def _extract_metastatic_requirement(quote: str) -> tuple[str, bool | None, str]:
    normalized = " ".join(quote.lower().split())

    if "metastatic" in normalized or re.search(r"\bstage\s*(?:iv|4)\b", normalized):
        return "=", True, "Metastatic disease is true"

    return "is_known", None, "Advanced or metastatic status must be documented"


def _is_advanced_disease_quote(quote: str) -> bool:
    normalized = " ".join(quote.lower().split())

    if not normalized:
        return False

    advanced_disease_patterns = [
        r"advanced\s+(?:cancer|disease|nsclc|non-small cell|lung)",
        r"(?:cancer|disease|nsclc|non-small cell lung cancer)\s+(?:is\s+)?advanced",
    ]

    return any(re.search(pattern, normalized) for pattern in advanced_disease_patterns)


def _extract_egfr_requirement(quote: str) -> tuple[str, bool | None, str]:
    normalized = " ".join(quote.lower().split())

    negative_patterns = [
        r"egfr[^.;:]{0,80}?(?:negative|wild[- ]type|without|no mutation)",
        r"(?:negative|wild[- ]type|without|no mutation)[^.;:]{0,80}?egfr",
    ]
    positive_patterns = [
        r"egfr[^.;:]{0,80}?(?:mutant|mutation|positive|harbor)",
        r"(?:mutant|mutation|positive|harbor)[^.;:]{0,80}?egfr",
    ]

    if any(re.search(pattern, normalized) for pattern in negative_patterns):
        return "=", False, "EGFR mutation is absent"

    if any(re.search(pattern, normalized) for pattern in positive_patterns):
        return "=", True, "EGFR mutation is present"

    return "is_known", None, "EGFR mutation status must be documented"
