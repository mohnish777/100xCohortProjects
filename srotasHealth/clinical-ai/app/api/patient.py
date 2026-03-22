from fastapi import APIRouter
from app.schemas.patient_schema import Patient
import uuid


router = APIRouter()

patients_db = {}

@router.post("/patient/add")
def add_patient(patient: Patient):
    patient_id = str(uuid.uuid4())
    patients_db[patient_id] = patient.model_dump()
    
    return {
        "patient_id": patient_id,
        "data": patient
        }
