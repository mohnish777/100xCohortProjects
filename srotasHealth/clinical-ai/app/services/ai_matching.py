


from app.schemas.Trial_criteria import TrialCriteria
from app.schemas.patient_schema import Patient
from app.services.llm_services import call_llm, extract_json

def ai_match(trial: TrialCriteria, patient: Patient):
    trial_context = build_trial_context(trial)
    patient_context = build_patient_context(patient)

    with open("app/prompts/Master_prompt.txt", "r") as f:
        master_prompt = f.read()

    prompt = master_prompt.replace("{trial_context}", trial_context)\
                        .replace("{patient_context}", patient_context)
    print("prompt: ai match:", prompt)
    response = call_llm(prompt)
    parsed = extract_json(response)
    return parsed


def build_patient_context(patient: Patient):
    return f""" 
    Patient Details:
    - Age: {patient.age}
    - Gender: {patient.gender}
    - Conditions: {", ".join(patient.conditions)}
    - Pregnant: {patient.pregnant}
    """

def build_trial_context(trial: TrialCriteria):
    inclusion = "\n".join(f"- {rule}"for rule in trial.inclusion_criteria)
    exclusion = "\n".join(f"- {rule}" for rule in trial.exclusion_criteria)

    return f"""
    Trial Criteria:

    Inclusion Criteria: {inclusion}
    Exclusion Criteria: {exclusion}
    """