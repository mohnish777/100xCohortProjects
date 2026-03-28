from fastapi import APIRouter
from app.config import supabase
from app.schemas.patient_schema import Patient
import uuid


router = APIRouter()


@router.post("/patient/add")
def add_patient(patient: Patient):
    result = supabase.table("patients").insert({
        "age": patient.age,
        "gender": patient.gender,
        "conditions": patient.conditions,
        "pregnant": patient.pregnant
    }).execute()
    
    return {
        "patient_id": result.data[0]["id"],
        "data": patient
        }
