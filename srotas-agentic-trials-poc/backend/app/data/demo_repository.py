from app.domain.models import (
    AgentActivity,
    ClinicalFact,
    DashboardSnapshot,
    FollowUpTask,
    Patient,
    PatientFactValue,
    PatientMatch,
    Trial,
    TrialCriterion,
)


PATIENTS = [
    Patient(
        id="p_lung_014",
        display_name="Patient L-014",
        anonymized_code="LUNG-014",
        age_band="50-59",
        sex="female",
        cancer_track="lung",
    ),
    Patient(
        id="p_lung_027",
        display_name="Patient L-027",
        anonymized_code="LUNG-027",
        age_band="60-69",
        sex="male",
        cancer_track="lung",
    ),
    Patient(
        id="p_breast_009",
        display_name="Patient B-009",
        anonymized_code="BRST-009",
        age_band="40-49",
        sex="female",
        cancer_track="breast",
    ),
    Patient(
        id="p_prostate_021",
        display_name="Patient P-021",
        anonymized_code="PROS-021",
        age_band="70-79",
        sex="male",
        cancer_track="prostate",
    ),
]

CLINICAL_FACTS = [
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
        source="protocol_agent",
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

PATIENT_FACT_VALUES = [
    PatientFactValue(
        patient_id="p_lung_014",
        fact_key="cancer_type",
        value="lung",
        display_value="lung",
        evidence="Patient described a lung cancer diagnosis.",
        confidence=0.94,
    ),
    PatientFactValue(
        patient_id="p_lung_014",
        fact_key="histology",
        value="NSCLC",
        display_value="NSCLC",
        evidence="Patient said the report mentions NSCLC.",
        confidence=0.91,
    ),
    PatientFactValue(
        patient_id="p_lung_014",
        fact_key="metastatic",
        value=True,
        display_value="true",
        evidence="Patient said the cancer has spread.",
        confidence=0.87,
    ),
    PatientFactValue(
        patient_id="p_lung_014",
        fact_key="prior_immunotherapy",
        value=True,
        display_value="true",
        evidence="Patient reported prior immunotherapy.",
        confidence=0.89,
    ),
    PatientFactValue(
        patient_id="p_lung_027",
        fact_key="cancer_type",
        value="lung",
        display_value="lung",
        evidence="Synthetic intake history.",
        confidence=0.95,
    ),
    PatientFactValue(
        patient_id="p_lung_027",
        fact_key="histology",
        value="NSCLC",
        display_value="NSCLC",
        evidence="Synthetic intake history.",
        confidence=0.92,
    ),
    PatientFactValue(
        patient_id="p_lung_027",
        fact_key="metastatic",
        value=True,
        display_value="true",
        evidence="Synthetic intake history.",
        confidence=0.9,
    ),
    PatientFactValue(
        patient_id="p_lung_027",
        fact_key="pd_l1_tps",
        value=72,
        display_value="72%",
        evidence="Pathology report lists PD-L1 TPS 72%.",
        confidence=0.96,
    ),
    PatientFactValue(
        patient_id="p_breast_009",
        fact_key="cancer_type",
        value="breast",
        display_value="breast",
        evidence="Synthetic intake history.",
        confidence=0.95,
    ),
    PatientFactValue(
        patient_id="p_breast_009",
        fact_key="her2_status",
        value="positive",
        display_value="positive",
        evidence="Synthetic intake history.",
        confidence=0.9,
    ),
    PatientFactValue(
        patient_id="p_prostate_021",
        fact_key="cancer_type",
        value="prostate",
        display_value="prostate",
        evidence="Synthetic intake history.",
        confidence=0.95,
    ),
    PatientFactValue(
        patient_id="p_prostate_021",
        fact_key="psa",
        value=18.4,
        display_value="18.4 ng/mL",
        evidence="Synthetic intake history.",
        confidence=0.88,
    ),
]

SELECTED_TRIAL = Trial(
    id="trial_st_402",
    title="ST-402 PD-L1 High NSCLC Study",
    sponsor="Srotas Demo Network",
    cancer_track="lung",
    protocol_summary="Synthetic demo protocol requiring metastatic NSCLC and PD-L1 TPS >= 50.",
)

TRIAL_CRITERIA = [
    TrialCriterion(
        id="tc_001",
        trial_id="trial_st_402",
        criterion_type="inclusion",
        fact_key="cancer_type",
        operator="=",
        expected_value="lung",
        display="Cancer type equals lung",
        source_quote="Participants must have lung cancer.",
    ),
    TrialCriterion(
        id="tc_002",
        trial_id="trial_st_402",
        criterion_type="inclusion",
        fact_key="histology",
        operator="=",
        expected_value="NSCLC",
        display="Histology equals NSCLC",
        source_quote="Participants must have non-small cell lung cancer.",
    ),
    TrialCriterion(
        id="tc_003",
        trial_id="trial_st_402",
        criterion_type="inclusion",
        fact_key="metastatic",
        operator="=",
        expected_value=True,
        display="Metastatic disease is true",
        source_quote="Participants must have metastatic disease.",
    ),
    TrialCriterion(
        id="tc_004",
        trial_id="trial_st_402",
        criterion_type="inclusion",
        fact_key="pd_l1_tps",
        operator=">=",
        expected_value=50,
        display="PD-L1 TPS is at least 50%",
        source_quote="Participants must have PD-L1 TPS of at least 50%.",
    ),
]

GENERATED_SQL = """select p.id, p.anonymized_code
from patients p
join patient_fact_values cancer
  on cancer.patient_id = p.id
 and cancer.fact_key = 'cancer_type'
 and cancer.value_text = 'lung'
join patient_fact_values histology
  on histology.patient_id = p.id
 and histology.fact_key = 'histology'
 and histology.value_text = 'NSCLC'
join patient_fact_values metastatic
  on metastatic.patient_id = p.id
 and metastatic.fact_key = 'metastatic'
 and metastatic.value_boolean = true
left join patient_fact_values pdl1
  on pdl1.patient_id = p.id
 and pdl1.fact_key = 'pd_l1_tps'
where pdl1.value_numeric >= 50
   or pdl1.value_numeric is null;"""


def get_dashboard_snapshot() -> DashboardSnapshot:
    matches = [
        PatientMatch(
            patient_id="p_lung_014",
            patient_name="Patient L-014",
            status="possible_match",
            explanation="Meets known lung, NSCLC, and metastatic criteria, but PD-L1 TPS is missing.",
            missing_fact_keys=["pd_l1_tps"],
            matched_fact_keys=["cancer_type", "histology", "metastatic"],
        ),
        PatientMatch(
            patient_id="p_lung_027",
            patient_name="Patient L-027",
            status="eligible",
            explanation="Meets lung, NSCLC, metastatic, and PD-L1 TPS >= 50 criteria.",
            missing_fact_keys=[],
            matched_fact_keys=["cancer_type", "histology", "metastatic", "pd_l1_tps"],
        ),
        PatientMatch(
            patient_id="p_breast_009",
            patient_name="Patient B-009",
            status="excluded",
            explanation="Cancer type is breast, while the protocol requires lung cancer.",
            missing_fact_keys=[],
            matched_fact_keys=[],
        ),
        PatientMatch(
            patient_id="p_prostate_021",
            patient_name="Patient P-021",
            status="excluded",
            explanation="Cancer type is prostate, while the protocol requires lung cancer.",
            missing_fact_keys=[],
            matched_fact_keys=[],
        ),
    ]

    follow_up_tasks = [
        FollowUpTask(
            id="fu_001",
            patient_id="p_lung_014",
            patient_name="Patient L-014",
            trial_id=SELECTED_TRIAL.id,
            fact_key="pd_l1_tps",
            fact_display_name="PD-L1 TPS",
            question="Can you confirm whether your pathology report shows a PD-L1 TPS percentage?",
            status="open",
            priority="high",
            created_by_agent="fact_registry_agent",
        )
    ]

    agent_activity = [
        AgentActivity(
            agent_name="Intake Agent",
            action="Stored lung cancer history as patient fact rows.",
            status="done",
        ),
        AgentActivity(
            agent_name="Protocol Agent",
            action="Extracted NSCLC and PD-L1 TPS eligibility requirements.",
            status="done",
        ),
        AgentActivity(
            agent_name="Fact Registry Agent",
            action="Registered pd_l1_tps without adding a patient table column.",
            status="done",
        ),
        AgentActivity(
            agent_name="Matching Agent",
            action="Flagged one eligible patient and one possible match.",
            status="active",
        ),
        AgentActivity(
            agent_name="Voice Follow-up Agent",
            action="Queued PD-L1 follow-up for Patient L-014.",
            status="queued",
        ),
    ]

    return DashboardSnapshot(
        patients=PATIENTS,
        clinical_facts=CLINICAL_FACTS,
        patient_fact_values=PATIENT_FACT_VALUES,
        selected_trial=SELECTED_TRIAL,
        trial_criteria=TRIAL_CRITERIA,
        matches=matches,
        follow_up_tasks=follow_up_tasks,
        generated_sql=GENERATED_SQL,
        agent_activity=agent_activity,
    )
