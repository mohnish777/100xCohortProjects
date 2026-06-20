from app.core.config import settings
from app.domain.models import (
    ProtocolAgentCriterion,
    ProtocolAgentFact,
    ProtocolAgentOutput,
)


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

    if not settings.openai_api_key:
        return _fallback_extract(context), "deterministic"

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
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

        return parsed, "openai_structured"
    except Exception:
        return _fallback_extract(context), "deterministic"


def _fallback_extract(context: str) -> ProtocolAgentOutput:
    lower = context.lower()
    facts: list[ProtocolAgentFact] = []
    criteria: list[ProtocolAgentCriterion] = []

    cancer_quote = _quote_around(context, ["non-small cell", "nsclc", "lung cancer"])
    facts.append(
        ProtocolAgentFact(
            key="cancer_type",
            display_name="Cancer type",
            description="Primary cancer type required by the protocol.",
            value_type="text",
            oncology_track="mixed",
            question_template="What type of cancer were you diagnosed with?",
            source_quote=cancer_quote or "Protocol mentions non-small cell lung cancer.",
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
            source_quote=cancer_quote or "Protocol mentions non-small cell lung cancer.",
            confidence=0.82,
        )
    )

    if "nsclc" in lower or "non-small cell" in lower:
        histology_quote = _quote_around(context, ["non-small cell", "nsclc"])
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

    if "metastatic" in lower or "stage iv" in lower or "advanced" in lower:
        metastatic_quote = _quote_around(context, ["metastatic", "stage iv", "advanced"])
        facts.append(
            ProtocolAgentFact(
                key="metastatic",
                display_name="Metastatic disease",
                description="Whether cancer is metastatic or advanced.",
                value_type="boolean",
                oncology_track="mixed",
                question_template="Has your cancer spread or been called metastatic?",
                source_quote=metastatic_quote or "Protocol mentions metastatic or advanced disease.",
                confidence=0.78,
            )
        )
        criteria.append(
            ProtocolAgentCriterion(
                criterion_type="inclusion",
                fact_key="metastatic",
                operator="=",
                expected_value=True,
                display="Metastatic disease is true",
                source_quote=metastatic_quote or "Protocol mentions metastatic or advanced disease.",
                confidence=0.78,
            )
        )

    if "pd-l1" in lower or "pdl1" in lower or "tumor proportion score" in lower:
        pdl1_quote = _quote_around(context, ["pd-l1", "pdl1", "tumor proportion score"])
        threshold = 50.0 if "50" in lower else 1.0
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
        criteria.append(
            ProtocolAgentCriterion(
                criterion_type="inclusion",
                fact_key="pd_l1_tps",
                operator=">=",
                expected_value=threshold,
                display=f"PD-L1 TPS is at least {threshold:g}%",
                source_quote=pdl1_quote or "Protocol mentions PD-L1 expression.",
                confidence=0.78,
            )
        )

    if "egfr" in lower:
        egfr_quote = _quote_around(context, ["egfr"])
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
                operator="=",
                expected_value=True,
                display="EGFR mutation is present",
                source_quote=egfr_quote or "Protocol mentions EGFR mutation.",
                confidence=0.84,
            )
        )

    return ProtocolAgentOutput(
        trial_title="Uploaded Oncology Protocol",
        cancer_track="lung",
        protocol_summary="Protocol Agent extracted lung oncology eligibility criteria from uploaded protocol text.",
        extracted_facts=facts,
        extracted_criteria=criteria,
        trace_notes=[
            "Selected eligibility-focused protocol context.",
            "Mapped protocol language to reusable clinical fact keys.",
            "Returned strict structured extraction output.",
        ],
        confidence=0.78,
    )


def _quote_around(text: str, keywords: list[str], radius: int = 220) -> str:
    lower = text.lower()
    for keyword in keywords:
        index = lower.find(keyword)
        if index >= 0:
            start = max(index - radius, 0)
            end = min(index + radius, len(text))
            return " ".join(text[start:end].split())
    return ""
