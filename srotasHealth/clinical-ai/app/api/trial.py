from fastapi import APIRouter, UploadFile, File
import uuid
import os
import re
import json

from app.services.embedding_service import get_embeddings
from app.services.pdf_service import extract_text_from_pdf
from app.services.llm_services import call_llm, extract_with_retry
from app.services.rag_service import chunk_text, retrieve_relevant_context, create_faiss_index

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

trial_db = {}


@router.post("/trial/upload")
async def upload_trial(file: UploadFile = File(...)):
    
    trial_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/{trial_id}.pdf"
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Extract text
    trial_text = extract_text_from_pdf(file_path)

    #chunk trial text
    chunks = chunk_text(trial_text)

    #create embeddings and store in trial_db
    create_faiss_index(trial_id, chunks)

    # retrieve relevant context from vector store for trial text
    queries = [
        "inclusion criteria",
        "exclusion criteria",
        'elegibility requirements'
    ]
    all_chunks = []
    for q in queries:
        context = retrieve_relevant_context(trial_id, q)
        all_chunks.append(context)

    final_context = "\n".join(all_chunks)

    lines = final_context.splitlines()
    seen = set()
    deduped_lines = []
    for line in lines:
        if line not in seen:
            deduped_lines.append(line)
            seen.add(line)

    final_context = "\n".join(deduped_lines)

    # Load prompt
    with open("app/prompts/extract_criteria.txt", "r") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{context}", final_context)  

    # Call LLM
    #print("context output:", final_context)

    # Step 3: Extract with retry
    parsed_output = extract_with_retry(prompt)

    print("parsed_output:", parsed_output)

    # Step 4: Check if criteria found
    criteria_found: bool = (
        parsed_output.get("inclusion_criteria") or 
        parsed_output.get("exclusion_criteria")
    )

    if not criteria_found:
        print("⚠️ RAG failed, falling back to full document")
        full_prompt = prompt_template.replace("{context}", trial_text[:8000])
        parsed_output = extract_with_retry(full_prompt)
    
    trial_db[trial_id] = parsed_output
    
    return {
        "trial_id": trial_id,
        "raw_llm_output": parsed_output
    }

