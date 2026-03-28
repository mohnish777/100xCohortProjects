

from fastapi import APIRouter
from app.config import supabase
from app.schemas.Trial_criteria import TrialCriteria
from app.services.agent_service import run_matching_agent


router  = APIRouter()

@router.post("/agent/run")
def run_agent(trial_id: str):
    """Run matching agent to find top patient matches for a trial"""
    # Fetch trial from Supabase
    trial_response = supabase.table("trials").select("*").eq("id", trial_id).execute()

    if not trial_response.data:
        return {"error": "Invalid trial ID"}
    
    trial_data = trial_response.data[0]
    trial = TrialCriteria(**trial_data)

    # Fetch all patients from Supabase
    patients_response = supabase.table("patients").select("*").execute()
    patients = patients_response.data
    
    if not patients:
        return {"message": "No patients found in database"}

    top_matches = run_matching_agent(trial, patients)

    if not top_matches:
        return {"message": "No eligible high-quality matches found"}

    return {
        "total_patients": len(patients),
        "top_matches": top_matches[:5],
        "all_results": top_matches
    }