
from app.schemas.Trial_criteria import TrialCriteria
from app.schemas.patient_schema import Patient
from app.services.embedding_service import get_embeddings
import numpy as np


def match_patient(trial_criteria: TrialCriteria, patient: Patient):

    inclusion = trial_criteria.inclusion_criteria or []
    exclusion = trial_criteria.exclusion_criteria or []
    patient_data = patient.model_dump() 

    inclusion_met = 0
    exclusion_violated = 0
    reason = []

    for rule in inclusion:
        if any(semantic_match(rule, cond) for cond in patient_data.values()):
            inclusion_met += 1
            reason.append(f"Matched inclusion: {rule}")

    for rule in exclusion:
        if any(semantic_match(rule, cond) for cond in patient_data.values()):
            exclusion_violated += 1
            reason.append(f"Matched exclusion: {rule}")

    return {
        "inclusion_met": inclusion_met,
        "inclusion_total": len(inclusion),
        "exclusion_violated": exclusion_violated,
        "reasons": reason
    }



def semantic_match(rule, patient_text):
    embeddings = get_embeddings([rule, patient_text])
    score = cosine_similarity(embeddings[0], embeddings[1])
    return score > 0.3  # threshold

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


