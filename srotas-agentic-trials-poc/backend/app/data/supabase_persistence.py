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

    client.table("protocol_extractions").upsert(
        {
            "protocol_hash": protocol_hash,
            "source_filename": source_filename or "uploaded-protocol.pdf",
            "trial_id": snapshot.selected_trial.id,
            "agent_mode": agent_mode or "unknown",
            "extracted_facts": [fact.model_dump() for fact in snapshot.clinical_facts],
            "extracted_criteria": [criterion.model_dump() for criterion in snapshot.trial_criteria],
            "protocol_excerpt": protocol_excerpt,
        },
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
