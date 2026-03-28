from fastapi import APIRouter
from app.services.voice_service import generate_summary, text_to_speech
from app.services.agent_service import run_matching_agent
from app.api.patient import patients_db
from app.api.trial import trial_db
from app.schemas.Trial_criteria import TrialCriteria

router = APIRouter()

@router.post("/voice/run")
def voice_run(trial_id: str):

    trial_data = trial_db.get(trial_id)

    if not trial_data:
        return {"error": "Invalid trial ID"}

    trial = TrialCriteria(**trial_data)

    patients = list(patients_db.values())

    agent_result = {
        "top_matches": run_matching_agent(trial, patients)[:5]
    }

    summary = generate_summary(agent_result)

    audio_file = text_to_speech(summary)

    return {
        "summary": summary,
        "audio_file": audio_file
    }