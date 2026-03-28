

from fastapi import APIRouter
from app.api.trial import trial_db
from app.schemas.Trial_criteria import TrialCriteria
from app.api.patient import patients_db
from app.services.agent_service import run_matching_agent


router  = APIRouter()

@router.post("/agent/run")
def run_agent(trial_id: str):
    trial_data = trial_db.get(trial_id)

    if not trial_data:
        return {"error" : "Invalid trial ID"}
    
    trial = TrialCriteria(**trial_data)

    patients = list(patients_db.values())

    top_matches = run_matching_agent(trial, patients)

    if not top_matches:
        return {"message": "No eligible high-quality matches found"}

    return {
        "total_patients": len(patients),
        "top_matches": top_matches[:5],
        "all_results": top_matches
    }