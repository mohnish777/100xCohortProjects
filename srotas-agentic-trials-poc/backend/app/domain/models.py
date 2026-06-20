from typing import Literal

from pydantic import BaseModel, Field


ValueType = Literal["boolean", "text", "number", "date"]
CancerTrack = Literal["breast", "lung", "prostate", "mixed"]
CriterionType = Literal["inclusion", "exclusion"]
MatchStatus = Literal["eligible", "possible_match", "excluded"]
FollowUpStatus = Literal["open", "scheduled", "completed", "cancelled"]


class Patient(BaseModel):
    id: str
    display_name: str
    anonymized_code: str
    age_band: str
    sex: str
    cancer_track: CancerTrack


class ClinicalFact(BaseModel):
    key: str
    display_name: str
    description: str
    value_type: ValueType
    unit: str | None = None
    oncology_track: CancerTrack
    question_template: str
    source: str


class PatientFactValue(BaseModel):
    patient_id: str
    fact_key: str
    value: bool | str | float
    display_value: str
    evidence: str
    confidence: float = Field(ge=0, le=1)


class Trial(BaseModel):
    id: str
    title: str
    sponsor: str
    cancer_track: CancerTrack
    protocol_summary: str


class TrialCriterion(BaseModel):
    id: str
    trial_id: str
    criterion_type: CriterionType
    fact_key: str
    operator: str
    expected_value: bool | str | float | None = None
    display: str
    source_quote: str
    required: bool = True


class PatientMatch(BaseModel):
    patient_id: str
    patient_name: str
    status: MatchStatus
    explanation: str
    missing_fact_keys: list[str]
    matched_fact_keys: list[str]


class FollowUpTask(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    trial_id: str
    fact_key: str
    fact_display_name: str
    question: str
    status: FollowUpStatus
    priority: Literal["low", "medium", "high"]
    created_by_agent: str


class AgentActivity(BaseModel):
    agent_name: str
    action: str
    status: Literal["done", "active", "queued"]


class ProtocolLearningStep(BaseModel):
    order: int
    agent_name: str
    title: str
    detail: str


class ProtocolLearningRun(BaseModel):
    trial: Trial
    protocol_excerpt: str
    extracted_facts: list[ClinicalFact]
    extracted_criteria: list[TrialCriterion]
    matched_patients: list[PatientMatch]
    follow_up_tasks: list[FollowUpTask]
    steps: list[ProtocolLearningStep]


class DashboardSnapshot(BaseModel):
    patients: list[Patient]
    clinical_facts: list[ClinicalFact]
    patient_fact_values: list[PatientFactValue]
    selected_trial: Trial
    trial_criteria: list[TrialCriterion]
    matches: list[PatientMatch]
    follow_up_tasks: list[FollowUpTask]
    generated_sql: str
    agent_activity: list[AgentActivity]
