from fastapi import APIRouter
from app.config import supabase
from app.schemas.patient_schema import Patient
from app.services.ai_matching import ai_match
from app.services.scoring_service import calculate_score

from app.schemas.Trial_criteria import TrialCriteria
from app.services.llm_services import call_llm, extract_with_retry
from app.services.matching_service import match_patient

router = APIRouter()


@router.post("/match")
def match(trial_id: str, patient_id: str):

    """Match a patient to a trial using rule-based scoring"""
    
    # Fetch trial from Supabase
    trial_response = supabase.table("trials").select("*").eq("id", trial_id).execute()
    if not trial_response.data:
        return {"error": "Invalid trial ID"}
    
    # Fetch patient from Supabase
    patient_response = supabase.table("patients").select("*").eq("id", patient_id).execute()
    if not patient_response.data:
        return {"error": "Invalid patient ID"}
    
    trial_data = trial_response.data[0]
    patient_data = patient_response.data[0]

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

@router.post("/match-ai")
def match_ai(trial_id: str, patient_id: str):
    """Match a patient to a trial using AI/LLM"""
    
    # Fetch trial from Supabase
    trial_response = supabase.table("trials").select("*").eq("id", trial_id).execute()
    if not trial_response.data:
        return {"error": "Invalid trial ID"}
    
    # Fetch patient from Supabase
    patient_response = supabase.table("patients").select("*").eq("id", patient_id).execute()
    if not patient_response.data:
        return {"error": "Invalid patient ID"}
    
    trial_data = trial_response.data[0]
    patient_data = patient_response.data[0]
    
    trial = TrialCriteria(**trial_data)
    patient = Patient(**patient_data)
    
    result = ai_match(trial, patient)
    
    return result
