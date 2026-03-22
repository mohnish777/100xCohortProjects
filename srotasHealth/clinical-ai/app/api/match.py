from fastapi import APIRouter
from app.schemas.patient_schema import Patient
from app.services.scoring_service import calculate_score
from app.api.patient import patients_db
from app.api.trial import trial_db
from app.schemas.Trial_criteria import TrialCriteria
from app.services.llm_services import call_llm, extract_with_retry
from app.services.matching_service import match_patient

router = APIRouter()


@router.post("/match")
def match(trial_id: str, patient_id: str):

    trial_data = trial_db.get(trial_id)
    patient_data = patients_db.get(patient_id)
    print("trial_db: ",trial_db)
    print("patients_db: ",patients_db)

    if not trial_data or not patient_data:
        return {"error": "Invalid Ids"}
    
    trial = TrialCriteria(**trial_data)
    patient = Patient(**patient_data)
    
    match_result = match_patient(trial, patient)
    
    score = calculate_score(
        match_result["inclusion_met"],
        match_result["inclusion_total"],
        match_result["exclusion_violated"]
        )
    
    eligible  = score > 50 and match_result["exclusion_violated"]==0

    return {
        "eligible": eligible,
        "score": score,
        "reasons": match_result["reasons"]
    }