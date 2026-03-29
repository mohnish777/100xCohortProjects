from fastapi import APIRouter
from app.config import supabase
from app.services.voice_service import generate_summary, generate_summary_llm, text_to_speech
from app.services.agent_service import run_matching_agent
from app.schemas.Trial_criteria import TrialCriteria

router = APIRouter()

@router.post("/voice/run")
def voice_run(trial_id: str):

    """Generate voice summary of top patient matches"""
    
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
        return {"error": "No patients found in database"}

    agent_result = {
        "top_matches": run_matching_agent(trial, patients)[:5]
    }

    summary = generate_summary(agent_result)

    #summary_llm = generate_summary_llm(agent_result)

    audio_file = text_to_speech(summary)

    return {
        "summary": summary,
        "audio_file": audio_file
    }