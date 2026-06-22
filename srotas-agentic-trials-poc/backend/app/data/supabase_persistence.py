import logging
from functools import lru_cache
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.core.config import settings
from app.domain.models import (
    ClinicalFact,
    DashboardSnapshot,
    FollowUpTask,
    Patient,
    PatientFactValue,
    ProtocolAgentCriterion,
    ProtocolAgentFact,
    ProtocolAgentOutput,
    Trial,
    TrialCriterion,
)


logger = logging.getLogger(__name__)


@lru_cache
def _supabase_client():
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None

    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def supabase_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def storage_mode() -> str:
    return "supabase_dual_write" if supabase_configured() else "memory_only"


def storage_status() -> dict[str, object]:
    schema_ready = False
    schema_error: str | None = None

    client = _supabase_client()
    if client is not None:
        try:
            client.table("clinical_facts").select("key").limit(1).execute()
            schema_ready = True
        except Exception as exc:
            schema_error = str(exc)

    return {
        "storage_mode": storage_mode(),
        "supabase_url_configured": bool(settings.supabase_url),
        "supabase_service_role_key_configured": bool(settings.supabase_service_role_key),
        "schema_ready": schema_ready,
        "schema_error": schema_error,
    }


def get_persisted_protocol_extraction(protocol_hash: str):
    client = _supabase_client()
    if client is None:
        return None

    try:
        response = (
            client.table("protocol_extractions")
            .select("*")
            .eq("protocol_hash", protocol_hash)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "Supabase protocol extraction lookup failed protocol_hash=%s error_type=%s error=%s",
            protocol_hash,
            type(exc).__name__,
            exc,
        )
        return None

    if not response.data:
        return None

    row = response.data[0]
    try:
        agent_output = ProtocolAgentOutput(
            trial_title=row.get("trial_title") or "Uploaded Oncology Protocol",
            cancer_track=row.get("cancer_track") or "mixed",
            protocol_summary=row.get("protocol_summary")
            or "Loaded previously extracted protocol criteria from Supabase.",
            extracted_facts=[
                ProtocolAgentFact.model_validate(fact)
                for fact in row.get("extracted_facts", [])
            ],
            extracted_criteria=[
                ProtocolAgentCriterion.model_validate(criterion)
                for criterion in row.get("extracted_criteria", [])
            ],
            trace_notes=[
                "Loaded existing extraction from Supabase protocol_extractions.",
                "Skipped model extraction because protocol hash already exists.",
            ],
            confidence=1.0,
        )
        return {
            "protocol_hash": protocol_hash,
            "source_filename": row.get("source_filename") or "uploaded-protocol.pdf",
            "protocol_text": row.get("protocol_excerpt") or "",
            "agent_output": agent_output,
            "agent_mode": row.get("agent_mode") or "openai_structured",
        }
    except Exception as exc:
        logger.warning(
            "Supabase protocol extraction row parse failed protocol_hash=%s error_type=%s error=%s",
            protocol_hash,
            type(exc).__name__,
            exc,
        )
        return None


def load_persisted_dashboard() -> DashboardSnapshot | None:
    client = _supabase_client()
    if client is None:
        return None

    try:
        patient_response = (
            client.table("patients")
            .select("*")
            .eq("id", _active_patient_id())
            .limit(1)
            .execute()
        )
        if not patient_response.data:
            return None

        facts_response = client.table("clinical_facts").select("*").execute()
        patient_fact_response = (
            client.table("patient_fact_values")
            .select("*")
            .eq("patient_id", _active_patient_id())
            .execute()
        )
        trial_response = (
            client.table("trials")
            .select("*")
            .eq("id", _active_trial_id())
            .limit(1)
            .execute()
        )
        criteria_response = (
            client.table("trial_criteria")
            .select("*")
            .eq("trial_id", _active_trial_id())
            .execute()
        )

        patient = _patient_from_row(patient_response.data[0])
        trial = (
            _trial_from_row(trial_response.data[0])
            if trial_response.data
            else Trial(
                id=_active_trial_id(),
                title="No protocol uploaded yet",
                sponsor="Srotas Demo Network",
                cancer_track="mixed",
                protocol_summary="Upload a trial protocol PDF to teach the system what facts matter.",
            )
        )
        clinical_facts = [_clinical_fact_from_row(row) for row in facts_response.data]
        patient_fact_values = [_patient_fact_from_row(row) for row in patient_fact_response.data]
        trial_criteria = [_trial_criterion_from_row(row) for row in criteria_response.data]

        return DashboardSnapshot(
            patients=[patient],
            clinical_facts=clinical_facts,
            patient_fact_values=patient_fact_values,
            selected_trial=trial,
            trial_criteria=trial_criteria,
            matches=[],
            follow_up_tasks=[],
            generated_sql="-- Loaded from Supabase; matching is recomputed in memory.",
            agent_activity=[],
        )
    except Exception as exc:
        logger.warning(
            "Supabase dashboard load failed error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return None


def reset_persisted_session(patient: Patient, clinical_facts: list[ClinicalFact]) -> None:
    client = _supabase_client()
    if client is None:
        return

    try:
        _upsert_clinical_facts(client, clinical_facts)
        client.table("follow_up_tasks").delete().eq("patient_id", patient.id).execute()
        client.table("patient_fact_values").delete().eq("patient_id", patient.id).execute()
        client.table("trial_criteria").delete().eq("trial_id", _active_trial_id()).execute()
        _upsert_patient(client, patient)
        logger.info("Supabase demo session reset patient_id=%s", patient.id)
    except Exception as exc:
        logger.warning(
            "Supabase demo session reset failed error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )


def clear_persisted_demo_data() -> None:
    client = _supabase_client()
    if client is None:
        return

    try:
        active_patient_id = _active_patient_id()
        active_trial_id = _active_trial_id()

        client.table("follow_up_tasks").delete().eq("patient_id", active_patient_id).execute()
        client.table("match_runs").delete().eq("trial_id", active_trial_id).execute()
        client.table("patient_fact_values").delete().eq("patient_id", active_patient_id).execute()
        client.table("intake_sessions").delete().eq("patient_id", active_patient_id).execute()
        client.table("trial_criteria").delete().eq("trial_id", active_trial_id).execute()
        client.table("protocol_extractions").delete().eq("trial_id", active_trial_id).execute()
        client.table("trials").delete().eq("id", active_trial_id).execute()
        client.table("patients").delete().eq("id", active_patient_id).execute()
        logger.info("Supabase active demo data cleared")
    except Exception as exc:
        logger.warning(
            "Supabase active demo data clear failed error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )


def persist_dashboard_snapshot(
    snapshot: DashboardSnapshot,
    *,
    protocol_hash: str | None,
    protocol_excerpt: str | None,
    source_filename: str | None,
    agent_mode: str | None,
) -> None:
    client = _supabase_client()
    if client is None:
        return

    try:
        _upsert_clinical_facts(client, snapshot.clinical_facts)
        for patient in snapshot.patients:
            _upsert_patient(client, patient)
        _upsert_patient_facts(client, snapshot.patient_fact_values)
        _upsert_trial(client, snapshot.selected_trial, protocol_hash)
        _replace_trial_criteria(client, snapshot.trial_criteria)
        _upsert_protocol_extraction(
            client,
            snapshot=snapshot,
            protocol_hash=protocol_hash,
            protocol_excerpt=protocol_excerpt,
            source_filename=source_filename,
            agent_mode=agent_mode,
        )
        _replace_follow_up_tasks(
            client,
            snapshot.follow_up_tasks,
            patient_ids=[patient.id for patient in snapshot.patients],
        )
        _insert_match_run(client, snapshot)
        logger.info(
            "Supabase snapshot persisted patients=%d facts=%d criteria=%d followups=%d",
            len(snapshot.patients),
            len(snapshot.patient_fact_values),
            len(snapshot.trial_criteria),
            len(snapshot.follow_up_tasks),
        )
    except Exception as exc:
        logger.warning(
            "Supabase snapshot persistence failed error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )


def _active_trial_id() -> str:
    return "00000000-0000-4000-8000-000000000101"


def _active_patient_id() -> str:
    return "00000000-0000-4000-8000-000000000001"


def _upsert_patient(client, patient: Patient) -> None:
    client.table("patients").upsert(
        {
            "id": patient.id,
            "display_name": patient.display_name,
            "anonymized_code": patient.anonymized_code,
            "age_band": patient.age_band,
            "sex": patient.sex,
            "cancer_track": patient.cancer_track,
            "consent_status": "demo_synthetic",
        }
    ).execute()


def _upsert_clinical_facts(client, facts: list[ClinicalFact]) -> None:
    if not facts:
        return

    client.table("clinical_facts").upsert(
        [
            {
                "key": fact.key,
                "display_name": fact.display_name,
                "description": fact.description,
                "value_type": fact.value_type,
                "unit": fact.unit,
                "oncology_track": fact.oncology_track,
                "question_template": fact.question_template,
                "source": fact.source,
            }
            for fact in facts
        ],
        on_conflict="key",
    ).execute()


def _upsert_patient_facts(client, fact_values: list[PatientFactValue]) -> None:
    if not fact_values:
        return

    client.table("patient_fact_values").upsert(
        [_patient_fact_row(fact_value) for fact_value in fact_values],
        on_conflict="patient_id,fact_key",
    ).execute()


def _upsert_trial(client, trial: Trial, protocol_hash: str | None) -> None:
    client.table("trials").upsert(
        {
            "id": trial.id,
            "title": trial.title,
            "sponsor": trial.sponsor,
            "cancer_track": trial.cancer_track,
            "protocol_source": "demo_upload",
            "protocol_hash": protocol_hash,
            "protocol_summary": trial.protocol_summary,
        }
    ).execute()


def _replace_trial_criteria(client, criteria: list[TrialCriterion]) -> None:
    trial_id = criteria[0].trial_id if criteria else _active_trial_id()
    client.table("trial_criteria").delete().eq("trial_id", trial_id).execute()
    if not criteria:
        return

    client.table("trial_criteria").insert([_criterion_row(criterion) for criterion in criteria]).execute()


def _upsert_protocol_extraction(
    client,
    *,
    snapshot: DashboardSnapshot,
    protocol_hash: str | None,
    protocol_excerpt: str | None,
    source_filename: str | None,
    agent_mode: str | None,
) -> None:
    if not protocol_hash:
        return

    row = {
        "protocol_hash": protocol_hash,
        "source_filename": source_filename or "uploaded-protocol.pdf",
        "trial_id": snapshot.selected_trial.id,
        "agent_mode": agent_mode or "unknown",
        "trial_title": snapshot.selected_trial.title,
        "cancer_track": snapshot.selected_trial.cancer_track,
        "protocol_summary": snapshot.selected_trial.protocol_summary,
        "extracted_facts": [fact.model_dump() for fact in snapshot.clinical_facts],
        "extracted_criteria": [criterion.model_dump() for criterion in snapshot.trial_criteria],
        "protocol_excerpt": protocol_excerpt,
    }

    try:
        client.table("protocol_extractions").upsert(
            row,
            on_conflict="protocol_hash",
        ).execute()
    except Exception as exc:
        if not _is_missing_optional_protocol_column_error(exc):
            raise

        logger.warning(
            "Supabase protocol_extractions optional columns missing; writing compatibility row error=%s",
            exc,
        )
        compatibility_row = {
            key: value
            for key, value in row.items()
            if key not in {"trial_title", "cancer_track", "protocol_summary"}
        }
        client.table("protocol_extractions").upsert(
            compatibility_row,
            on_conflict="protocol_hash",
        ).execute()


def _replace_follow_up_tasks(
    client,
    tasks: list[FollowUpTask],
    *,
    patient_ids: list[str],
) -> None:
    for patient_id in patient_ids:
        client.table("follow_up_tasks").delete().eq("patient_id", patient_id).execute()

    if not tasks:
        return

    client.table("follow_up_tasks").insert([_follow_up_row(task) for task in tasks]).execute()


def _insert_match_run(client, snapshot: DashboardSnapshot) -> None:
    if not snapshot.matches or snapshot.selected_trial.title == "No protocol uploaded yet":
        return

    match_run_id = str(uuid4())
    client.table("match_runs").insert(
        {
            "id": match_run_id,
            "trial_id": snapshot.selected_trial.id,
            "generated_sql": snapshot.generated_sql,
            "status": "completed",
            "created_by_agent": "matching_agent",
        }
    ).execute()

    client.table("match_run_patients").insert(
        [
            {
                "id": str(uuid5(NAMESPACE_URL, f"{match_run_id}:{match.patient_id}")),
                "match_run_id": match_run_id,
                "patient_id": match.patient_id,
                "status": match.status,
                "explanation": match.explanation,
                "missing_fact_keys": match.missing_fact_keys,
            }
            for match in snapshot.matches
        ]
    ).execute()


def _patient_fact_row(fact_value: PatientFactValue) -> dict[str, object]:
    row: dict[str, object] = {
        "patient_id": fact_value.patient_id,
        "fact_key": fact_value.fact_key,
        "evidence": fact_value.evidence,
        "confidence": fact_value.confidence,
        "value_boolean": None,
        "value_text": None,
        "value_numeric": None,
        "value_date": None,
    }

    if isinstance(fact_value.value, bool):
        row["value_boolean"] = fact_value.value
    elif isinstance(fact_value.value, (int, float)):
        row["value_numeric"] = fact_value.value
    else:
        row["value_text"] = str(fact_value.value)

    return row


def _criterion_row(criterion: TrialCriterion) -> dict[str, object]:
    row: dict[str, object] = {
        "id": _stable_uuid(f"criterion:{criterion.trial_id}:{criterion.id}"),
        "trial_id": criterion.trial_id,
        "criterion_type": criterion.criterion_type,
        "fact_key": criterion.fact_key,
        "operator": criterion.operator,
        "source_quote": criterion.source_quote,
        "required": criterion.required,
        "value_boolean": None,
        "value_text": None,
        "value_numeric": None,
        "value_date": None,
    }

    expected = criterion.expected_value
    if isinstance(expected, bool):
        row["value_boolean"] = expected
    elif isinstance(expected, (int, float)):
        row["value_numeric"] = expected
    elif isinstance(expected, str):
        row["value_text"] = expected

    return row


def _follow_up_row(task: FollowUpTask) -> dict[str, object]:
    return {
        "id": _stable_uuid(f"followup:{task.patient_id}:{task.trial_id}:{task.fact_key}"),
        "patient_id": task.patient_id,
        "trial_id": task.trial_id,
        "fact_key": task.fact_key,
        "question": task.question,
        "status": task.status,
        "priority": task.priority,
        "created_by_agent": task.created_by_agent,
    }


def _stable_uuid(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, value))


def _is_missing_optional_protocol_column_error(exc: Exception) -> bool:
    message = str(exc)
    return (
        "protocol_extractions" in message
        and any(
            column in message
            for column in ["trial_title", "cancer_track", "protocol_summary"]
        )
    )


def _patient_from_row(row: dict[str, object]) -> Patient:
    return Patient(
        id=str(row["id"]),
        display_name=str(row["display_name"]),
        anonymized_code=str(row["anonymized_code"]),
        age_band=str(row.get("age_band") or "Not captured"),
        sex=str(row.get("sex") or "Not captured"),
        cancer_track=row.get("cancer_track") or "mixed",
    )


def _clinical_fact_from_row(row: dict[str, object]) -> ClinicalFact:
    return ClinicalFact(
        key=str(row["key"]),
        display_name=str(row["display_name"]),
        description=str(row.get("description") or ""),
        value_type=row.get("value_type") or "text",
        unit=row.get("unit"),
        oncology_track=row.get("oncology_track") or "mixed",
        question_template=str(row.get("question_template") or ""),
        source=str(row.get("source") or "supabase"),
    )


def _patient_fact_from_row(row: dict[str, object]) -> PatientFactValue:
    value = (
        row.get("value_boolean")
        if row.get("value_boolean") is not None
        else row.get("value_numeric")
        if row.get("value_numeric") is not None
        else row.get("value_text")
        if row.get("value_text") is not None
        else row.get("value_date")
    )

    return PatientFactValue(
        patient_id=str(row["patient_id"]),
        fact_key=str(row["fact_key"]),
        value=value,
        display_value=_display_value(str(row["fact_key"]), value),
        evidence=str(row.get("evidence") or "Loaded from Supabase."),
        confidence=float(row.get("confidence") or 0.85),
    )


def _trial_from_row(row: dict[str, object]) -> Trial:
    return Trial(
        id=str(row["id"]),
        title=str(row["title"]),
        sponsor=str(row.get("sponsor") or ""),
        cancer_track=row.get("cancer_track") or "mixed",
        protocol_summary=str(row.get("protocol_summary") or ""),
    )


def _trial_criterion_from_row(row: dict[str, object]) -> TrialCriterion:
    expected_value = (
        row.get("value_boolean")
        if row.get("value_boolean") is not None
        else row.get("value_numeric")
        if row.get("value_numeric") is not None
        else row.get("value_text")
        if row.get("value_text") is not None
        else row.get("value_date")
    )

    return TrialCriterion(
        id=str(row["id"]),
        trial_id=str(row["trial_id"]),
        criterion_type=row.get("criterion_type") or "inclusion",
        fact_key=str(row["fact_key"]),
        operator=str(row["operator"]),
        expected_value=expected_value,
        display=_criterion_display(str(row["fact_key"]), str(row["operator"]), expected_value),
        source_quote=str(row.get("source_quote") or "Loaded from Supabase."),
        required=bool(row.get("required", True)),
    )


def _display_value(fact_key: str, value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if fact_key == "pd_l1_tps" and value is not None:
        return f"{float(value):g}%"
    if fact_key == "psa" and value is not None:
        return f"{float(value):g} ng/mL"
    return str(value)


def _criterion_display(fact_key: str, operator: str, expected_value: object) -> str:
    display_name = fact_key.replace("_", " ").title()
    if operator == "is_known":
        return f"{display_name} must be documented"
    if isinstance(expected_value, bool):
        return f"{display_name} is {'true' if expected_value else 'false'}"
    return f"{display_name} {operator} {expected_value}"
