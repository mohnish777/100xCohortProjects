from dataclasses import dataclass, field

from app.domain.models import (
    AgentActivity,
    CancerTrack,
    ClinicalFact,
    DashboardSnapshot,
    FollowUpTask,
    IntakeAgentOutput,
    Patient,
    PatientFactValue,
    PatientMatch,
    ProtocolAgentOutput,
    ProtocolLearningRun,
    ProtocolLearningStep,
    Trial,
    TrialCriterion,
)
from app.data.supabase_persistence import persist_dashboard_snapshot, reset_persisted_session
from app.services.protocol_pdf import make_protocol_excerpt


ACTIVE_PATIENT_ID = "00000000-0000-4000-8000-000000000001"
ACTIVE_TRIAL_ID = "00000000-0000-4000-8000-000000000101"


BASE_CLINICAL_FACTS = [
    ClinicalFact(
        key="cancer_type",
        display_name="Cancer type",
        description="Primary oncology track reported by the patient.",
        value_type="text",
        oncology_track="mixed",
        question_template="What type of cancer were you diagnosed with?",
        source="seed",
    ),
    ClinicalFact(
        key="histology",
        display_name="Histology",
        description="Subtype such as NSCLC or SCLC.",
        value_type="text",
        oncology_track="lung",
        question_template="Do your reports mention NSCLC, SCLC, or another subtype?",
        source="seed",
    ),
    ClinicalFact(
        key="metastatic",
        display_name="Metastatic disease",
        description="Whether cancer is metastatic or advanced.",
        value_type="boolean",
        oncology_track="mixed",
        question_template="Has your cancer spread or been called metastatic?",
        source="seed",
    ),
    ClinicalFact(
        key="pd_l1_tps",
        display_name="PD-L1 TPS",
        description="PD-L1 tumor proportion score used for lung immunotherapy eligibility.",
        value_type="number",
        unit="%",
        oncology_track="lung",
        question_template="Do you have a PD-L1 TPS percentage on your pathology report?",
        source="seed",
    ),
    ClinicalFact(
        key="egfr_mutation",
        display_name="EGFR mutation",
        description="Whether an EGFR mutation is present.",
        value_type="boolean",
        oncology_track="lung",
        question_template="Do your reports mention an EGFR mutation?",
        source="seed",
    ),
    ClinicalFact(
        key="prior_immunotherapy",
        display_name="Prior immunotherapy",
        description="Whether the patient has previously received immunotherapy.",
        value_type="boolean",
        oncology_track="lung",
        question_template="Have you received immunotherapy before?",
        source="seed",
    ),
    ClinicalFact(
        key="her2_status",
        display_name="HER2 status",
        description="HER2 biomarker status for breast cancer.",
        value_type="text",
        oncology_track="breast",
        question_template="Do you know your HER2 status?",
        source="seed",
    ),
    ClinicalFact(
        key="psa",
        display_name="PSA",
        description="Prostate-specific antigen value.",
        value_type="number",
        unit="ng/mL",
        oncology_track="prostate",
        question_template="Do you know your latest PSA value?",
        source="seed",
    ),
]


FACT_BY_KEY = {fact.key: fact for fact in BASE_CLINICAL_FACTS}


EMPTY_TRIAL = Trial(
    id=ACTIVE_TRIAL_ID,
    title="No protocol uploaded yet",
    sponsor="Srotas Demo Network",
    cancer_track="mixed",
    protocol_summary="Upload a trial protocol PDF to teach the system what facts matter.",
)


DEMO_PROTOCOL_EXCERPT = (
    "Eligible participants must have metastatic non-small cell lung cancer. "
    "Tumor PD-L1 expression must be documented with tumor proportion score "
    "of at least 50 percent."
)


@dataclass
class DemoSession:
    patient: Patient
    clinical_facts: list[ClinicalFact] = field(default_factory=lambda: list(BASE_CLINICAL_FACTS))
    patient_fact_values: list[PatientFactValue] = field(default_factory=list)
    selected_trial: Trial = field(default_factory=lambda: EMPTY_TRIAL.model_copy())
    trial_criteria: list[TrialCriterion] = field(default_factory=list)
    protocol_excerpt: str = ""
    protocol_source_filename: str | None = None
    protocol_agent_mode: str = "deterministic"
    protocol_agent_notes: list[str] = field(default_factory=list)
    protocol_hash: str | None = None


@dataclass
class ProtocolExtractionRecord:
    protocol_hash: str
    source_filename: str
    protocol_text: str
    agent_output: ProtocolAgentOutput
    agent_mode: str


_protocol_extraction_cache: dict[str, ProtocolExtractionRecord] = {}


def _new_patient(patient_name: str = "Demo Patient", cancer_track: CancerTrack = "mixed") -> Patient:
    cleaned_name = patient_name.strip() or "Demo Patient"
    return Patient(
        id=ACTIVE_PATIENT_ID,
        display_name=cleaned_name,
        anonymized_code="DEMO-001",
        age_band="Not captured",
        sex="Not captured",
        cancer_track=cancer_track,
    )


_session = DemoSession(patient=_new_patient())


def reset_demo_session(patient_name: str = "Demo Patient") -> DashboardSnapshot:
    global _session
    _session = DemoSession(patient=_new_patient(patient_name))
    reset_persisted_session(_session.patient, _session.clinical_facts)
    return get_dashboard_snapshot()


def get_dashboard_snapshot() -> DashboardSnapshot:
    matches = _match_patients()
    follow_up_tasks = _build_follow_up_tasks(matches)

    return DashboardSnapshot(
        patients=[_session.patient],
        clinical_facts=_session.clinical_facts,
        patient_fact_values=_session.patient_fact_values,
        selected_trial=_session.selected_trial,
        trial_criteria=_session.trial_criteria,
        matches=matches,
        follow_up_tasks=follow_up_tasks,
        generated_sql=_build_generated_sql(),
        agent_activity=_build_agent_activity(matches, follow_up_tasks),
    )


def get_cached_protocol_extraction(protocol_hash: str) -> ProtocolExtractionRecord | None:
    return _protocol_extraction_cache.get(protocol_hash)


def remember_protocol_extraction(
    *,
    protocol_hash: str,
    source_filename: str,
    protocol_text: str,
    agent_output: ProtocolAgentOutput,
    agent_mode: str,
) -> None:
    _protocol_extraction_cache[protocol_hash] = ProtocolExtractionRecord(
        protocol_hash=protocol_hash,
        source_filename=source_filename,
        protocol_text=protocol_text,
        agent_output=agent_output,
        agent_mode=agent_mode,
    )


def store_patient_intake(
    *,
    patient_name: str | None,
    agent_output: IntakeAgentOutput,
) -> None:
    if patient_name:
        _session.patient.display_name = patient_name.strip() or _session.patient.display_name

    _session.patient.cancer_track = agent_output.inferred_cancer_track

    existing_by_key = {value.fact_key: value for value in _session.patient_fact_values}
    for fact in agent_output.extracted_facts:
        if fact.value is None:
            continue

        existing_by_key[fact.fact_key] = PatientFactValue(
            patient_id=_session.patient.id,
            fact_key=fact.fact_key,
            value=fact.value,
            display_value=fact.display_value,
            evidence=fact.evidence,
            confidence=fact.confidence,
        )

    _session.patient_fact_values = list(existing_by_key.values())
    _persist_current_snapshot()


def get_protocol_learning_run(
    protocol_text: str | None = None,
    source_filename: str | None = None,
    extraction_mode: str = "simulation",
    agent_output: ProtocolAgentOutput | None = None,
    agent_mode: str = "deterministic",
    protocol_cache_status: str = "simulation",
    protocol_hash: str | None = None,
) -> ProtocolLearningRun:
    protocol_excerpt = make_protocol_excerpt(protocol_text or DEMO_PROTOCOL_EXCERPT)

    if agent_output:
        extracted_facts = _clinical_facts_from_agent(agent_output)
        extracted_criteria = _criteria_from_agent(agent_output)
        trial = Trial(
            id=ACTIVE_TRIAL_ID,
            title=agent_output.trial_title or "Uploaded Oncology Protocol",
            sponsor="Uploaded protocol",
            cancer_track=agent_output.cancer_track,
            protocol_summary=agent_output.protocol_summary,
        )
        agent_notes = agent_output.trace_notes
    else:
        extracted_facts = [
            FACT_BY_KEY["histology"],
            FACT_BY_KEY["metastatic"],
            FACT_BY_KEY["pd_l1_tps"],
        ]
        extracted_criteria = [
            TrialCriterion(
                id="demo_tc_001",
                trial_id=ACTIVE_TRIAL_ID,
                criterion_type="inclusion",
                fact_key="histology",
                operator="=",
                expected_value="NSCLC",
                display="Histology equals NSCLC",
                source_quote="Eligible participants must have non-small cell lung cancer.",
            ),
            TrialCriterion(
                id="demo_tc_002",
                trial_id=ACTIVE_TRIAL_ID,
                criterion_type="inclusion",
                fact_key="metastatic",
                operator="=",
                expected_value=True,
                display="Metastatic disease is true",
                source_quote="Eligible participants must have metastatic disease.",
            ),
            TrialCriterion(
                id="demo_tc_003",
                trial_id=ACTIVE_TRIAL_ID,
                criterion_type="inclusion",
                fact_key="pd_l1_tps",
                operator=">=",
                expected_value=50,
                display="PD-L1 TPS is at least 50%",
                source_quote="Tumor proportion score of at least 50 percent.",
            ),
        ]
        trial = Trial(
            id=ACTIVE_TRIAL_ID,
            title="Demo PD-L1 High NSCLC Study",
            sponsor="Srotas Demo Network",
            cancer_track="lung",
            protocol_summary="Demo protocol requiring metastatic NSCLC and PD-L1 TPS >= 50.",
        )
        agent_notes = ["Used deterministic demo extraction.", "Mapped protocol text to known facts."]

    _session.selected_trial = trial
    _session.protocol_excerpt = protocol_excerpt
    _session.protocol_source_filename = source_filename
    _session.protocol_agent_mode = agent_mode
    _session.protocol_agent_notes = agent_notes
    _session.protocol_hash = protocol_hash
    _merge_clinical_facts(extracted_facts)
    _session.trial_criteria = extracted_criteria

    snapshot = get_dashboard_snapshot()
    _persist_current_snapshot(snapshot)
    possible_count = sum(1 for match in snapshot.matches if match.status == "possible_match")
    eligible_count = sum(1 for match in snapshot.matches if match.status == "eligible")

    steps = [
        ProtocolLearningStep(
            order=1,
            agent_name="Protocol Agent",
            title="Read protocol text",
            detail=(
                "Extracted selectable PDF text and converted eligibility language into structured facts."
                if extraction_mode == "pdf_text"
                else "Read the demo protocol and found structured eligibility requirements."
            ),
        ),
        ProtocolLearningStep(
            order=2,
            agent_name="Fact Registry Agent",
            title="Register required facts",
            detail="Added protocol-required facts to the clinical fact registry without changing patient columns.",
        ),
        ProtocolLearningStep(
            order=3,
            agent_name="Matching Agent",
            title="Compare facts to patient",
            detail=(
                f"Found {eligible_count} eligible and {possible_count} possible match records "
                "using only stored patient facts."
            ),
        ),
        ProtocolLearningStep(
            order=4,
            agent_name="Voice Follow-up Agent",
            title="Create missing-data tasks",
            detail=(
                f"Queued {len(snapshot.follow_up_tasks)} follow-up task(s) for missing facts."
                if snapshot.follow_up_tasks
                else "No missing required facts were found for follow-up."
            ),
        ),
    ]

    return ProtocolLearningRun(
        trial=trial,
        source_filename=source_filename,
        extraction_mode=extraction_mode,
        agent_mode=agent_mode,
        agent_notes=agent_notes,
        protocol_cache_status=protocol_cache_status,
        protocol_hash=protocol_hash,
        protocol_excerpt=protocol_excerpt,
        extracted_facts=extracted_facts,
        extracted_criteria=extracted_criteria,
        matched_patients=snapshot.matches,
        follow_up_tasks=snapshot.follow_up_tasks,
        steps=steps,
    )


def _persist_current_snapshot(snapshot: DashboardSnapshot | None = None) -> None:
    persist_dashboard_snapshot(
        snapshot or get_dashboard_snapshot(),
        protocol_hash=_session.protocol_hash,
        protocol_excerpt=_session.protocol_excerpt,
        source_filename=_session.protocol_source_filename,
        agent_mode=_session.protocol_agent_mode,
    )


def _clinical_facts_from_agent(agent_output: ProtocolAgentOutput) -> list[ClinicalFact]:
    facts = []
    for fact in agent_output.extracted_facts:
        facts.append(
            ClinicalFact(
                key=fact.key,
                display_name=fact.display_name,
                description=fact.description,
                value_type=fact.value_type,
                unit=fact.unit,
                oncology_track=fact.oncology_track,
                question_template=fact.question_template,
                source="protocol_agent",
            )
        )
    return facts


def _criteria_from_agent(agent_output: ProtocolAgentOutput) -> list[TrialCriterion]:
    return [
        TrialCriterion(
            id=f"agent_tc_{index + 1:03d}",
            trial_id=ACTIVE_TRIAL_ID,
            criterion_type=criterion.criterion_type,
            fact_key=criterion.fact_key,
            operator=criterion.operator,
            expected_value=criterion.expected_value,
            display=criterion.display,
            source_quote=criterion.source_quote,
            required=criterion.required,
        )
        for index, criterion in enumerate(agent_output.extracted_criteria)
        if criterion.fact_key in FACT_BY_KEY or criterion.fact_key
    ]


def _merge_clinical_facts(facts: list[ClinicalFact]) -> None:
    by_key = {fact.key: fact for fact in _session.clinical_facts}
    for fact in facts:
        by_key[fact.key] = fact
    _session.clinical_facts = list(by_key.values())


def _match_patients() -> list[PatientMatch]:
    if not _session.trial_criteria:
        return []

    patient_facts = {value.fact_key: value for value in _session.patient_fact_values}
    matched_keys: list[str] = []
    missing_keys: list[str] = []
    failed_displays: list[str] = []

    for criterion in _session.trial_criteria:
        if criterion.criterion_type != "inclusion" or not criterion.required:
            continue

        patient_value = patient_facts.get(criterion.fact_key)
        if patient_value is None:
            missing_keys.append(criterion.fact_key)
            continue

        if _criterion_matches(patient_value.value, criterion.operator, criterion.expected_value):
            matched_keys.append(criterion.fact_key)
        else:
            failed_displays.append(criterion.display)

    if failed_displays:
        status = "excluded"
        explanation = f"{_session.patient.display_name} is excluded: {failed_displays[0]} was not met."
    elif missing_keys:
        status = "possible_match"
        missing_names = ", ".join(_display_name(key) for key in missing_keys)
        explanation = (
            f"{_session.patient.display_name} matches known criteria, but {missing_names} "
            "is missing."
        )
    else:
        status = "eligible"
        explanation = f"{_session.patient.display_name} meets all extracted required criteria."

    return [
        PatientMatch(
            patient_id=_session.patient.id,
            patient_name=_session.patient.display_name,
            status=status,
            explanation=explanation,
            missing_fact_keys=missing_keys,
            matched_fact_keys=matched_keys,
        )
    ]


def _criterion_matches(
    patient_value: bool | str | float,
    operator: str,
    expected_value: bool | str | float | None,
) -> bool:
    normalized_operator = operator.strip().lower()

    if normalized_operator == "is_known":
        return patient_value is not None

    if expected_value is None:
        return patient_value is not None

    if normalized_operator in {"=", "==", "equals"}:
        return _normalize_comparable(patient_value) == _normalize_comparable(expected_value)

    patient_number = _as_float(patient_value)
    expected_number = _as_float(expected_value)
    if patient_number is None or expected_number is None:
        return False

    if normalized_operator in {">=", "at least"}:
        return patient_number >= expected_number
    if normalized_operator == ">":
        return patient_number > expected_number
    if normalized_operator in {"<=", "at most"}:
        return patient_number <= expected_number
    if normalized_operator == "<":
        return patient_number < expected_number

    return False


def _normalize_comparable(value: bool | str | float) -> bool | str | float:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"lung cancer", "lung"}:
            return "lung"
        if normalized in {"breast cancer", "breast"}:
            return "breast"
        if normalized in {"prostate cancer", "prostate"}:
            return "prostate"
        if normalized in {"non-small cell lung cancer", "non-small cell", "nsclc"}:
            return "nsclc"
        return normalized
    return value


def _as_float(value: bool | str | float) -> float | None:
    if isinstance(value, bool):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_follow_up_tasks(matches: list[PatientMatch]) -> list[FollowUpTask]:
    tasks: list[FollowUpTask] = []
    for match in matches:
        if match.status != "possible_match":
            continue

        for index, fact_key in enumerate(match.missing_fact_keys):
            fact = _fact_for_key(fact_key)
            tasks.append(
                FollowUpTask(
                    id=f"fu_{index + 1:03d}",
                    patient_id=match.patient_id,
                    patient_name=match.patient_name,
                    trial_id=_session.selected_trial.id,
                    fact_key=fact_key,
                    fact_display_name=fact.display_name,
                    question=fact.question_template,
                    status="open",
                    priority="high",
                    created_by_agent="voice_follow_up_agent",
                )
            )
    return tasks


def _build_generated_sql() -> str:
    if not _session.trial_criteria:
        return "-- Upload a protocol to generate a read-only SQL preview."

    lines = [
        "select p.id, p.display_name",
        "from patients p",
    ]

    where_lines = []
    for index, criterion in enumerate(_session.trial_criteria):
        alias = f"f{index + 1}"
        join_type = "left join" if criterion.operator == "is_known" else "join"
        lines.extend(
            [
                f"{join_type} patient_fact_values {alias}",
                f"  on {alias}.patient_id = p.id",
                f" and {alias}.fact_key = '{criterion.fact_key}'",
            ]
        )
        where_clause = _criterion_to_sql(alias, criterion)
        if where_clause:
            where_lines.append(where_clause)

    if where_lines:
        lines.append("where " + "\n  and ".join(where_lines))

    return "\n".join(lines) + ";"


def _criterion_to_sql(alias: str, criterion: TrialCriterion) -> str:
    if criterion.operator == "is_known":
        return f"{alias}.value is not null"

    expected_value = criterion.expected_value
    if isinstance(expected_value, str):
        return f"{alias}.value = '{expected_value}'"
    if isinstance(expected_value, bool):
        return f"{alias}.value = {str(expected_value).lower()}"
    if isinstance(expected_value, (int, float)):
        return f"{alias}.value {criterion.operator} {expected_value:g}"
    return ""


def _build_agent_activity(
    matches: list[PatientMatch],
    follow_up_tasks: list[FollowUpTask],
) -> list[AgentActivity]:
    activity = [
        AgentActivity(
            agent_name="Intake Agent",
            action=(
                f"Stored {len(_session.patient_fact_values)} fact row(s) for "
                f"{_session.patient.display_name}."
            ),
            status="done" if _session.patient_fact_values else "queued",
        ),
        AgentActivity(
            agent_name="Protocol Agent",
            action=(
                f"Extracted {len(_session.trial_criteria)} protocol criterion row(s)."
                if _session.trial_criteria
                else "Waiting for protocol upload."
            ),
            status="done" if _session.trial_criteria else "queued",
        ),
    ]

    if matches:
        activity.append(
            AgentActivity(
                agent_name="Matching Agent",
                action=matches[0].explanation,
                status="done",
            )
        )

    activity.append(
        AgentActivity(
            agent_name="Voice Follow-up Agent",
            action=(
                f"Queued {len(follow_up_tasks)} missing-data call task(s)."
                if follow_up_tasks
                else "No follow-up call needed yet."
            ),
            status="queued" if follow_up_tasks else "done",
        )
    )
    return activity


def _display_name(fact_key: str) -> str:
    return _fact_for_key(fact_key).display_name


def _fact_for_key(fact_key: str) -> ClinicalFact:
    by_key = {fact.key: fact for fact in _session.clinical_facts}
    return by_key.get(
        fact_key,
        ClinicalFact(
            key=fact_key,
            display_name=fact_key.replace("_", " ").title(),
            description="Protocol-discovered fact.",
            value_type="text",
            oncology_track="mixed",
            question_template=f"Can you provide {fact_key.replace('_', ' ')}?",
            source="protocol_agent",
        ),
    )
