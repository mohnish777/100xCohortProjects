from fastapi import APIRouter, UploadFile, File
import uuid
import os
import re
import json

from app.services.pdf_service import extract_text_from_pdf
from app.services.llm_services import call_llm

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/trial/upload")
async def upload_trial(file: UploadFile = File(...)):
    
    trial_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/{trial_id}.pdf"
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Extract text
    trial_text = extract_text_from_pdf(file_path)

    # Load prompt
    with open("app/prompts/extract_criteria.txt", "r") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{trial_text}", trial_text[:8000])  # limit tokens

    # Call LLM
    llm_response = call_llm(prompt)
    parsed_output = extract_json(llm_response)
    
    if not parsed_output.get("inclusion_criteria") and not parsed_output.get("exclusion_criteria"):
        return {
            "trial_id": trial_id,
            "warning": "No eligibility criteria found. Please upload a valid clinical trial document."
        }

    return {
        "trial_id": trial_id,
        "raw_llm_output": parsed_output
    }

def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}