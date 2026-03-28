import hashlib

from fastapi import APIRouter, UploadFile, File
import uuid
import os
import re
import json
from app.config.supabase import supabase  
from app.services.embedding_service import get_embeddings
from app.services.pdf_service import extract_text_from_pdf
from app.services.llm_services import call_llm, extract_with_retry
from app.services.rag_service import chunk_text, retrieve_relevant_context

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)



@router.post("/trial/upload")
async def upload_trial(file: UploadFile = File(...)):
    # Read file content
    pdf_bytes = await file.read()

    # Calculate hash for deduplication
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    # Check if PDF already processed
    existing = supabase.table("trials").select("*").eq("pdf_hash", pdf_hash).execute()
    if existing.data:
        return {
            "trial_id": existing.data[0]["id"],
            "message": "Trial already exists (deduplicated)",
            "raw_llm_output": {
                "inclusion_criteria": existing.data[0]["inclusion_criteria"],
                "exclusion_criteria": existing.data[0]["exclusion_criteria"]
            }
        }
    
    trial_id = str(uuid.uuid4())

    # Upload PDF to Supabase Storage
    storage_path = f"{trial_id}.pdf"
    supabase.storage.from_("trial-pdfs").upload(
        storage_path, 
        pdf_bytes,
        {"content-type": "application/pdf"}
    )
    # Get public URL
    pdf_url = supabase.storage.from_("trial-pdfs").get_public_url(storage_path)

    # Save locally for processing (or download from storage)
    file_path = f"{UPLOAD_DIR}/{trial_id}.pdf"
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    # Extract text
    trial_text = extract_text_from_pdf(file_path)

    #chunk trial text
    chunks = chunk_text(trial_text)

    # Store embeddings in Supabase instead of in-memory
    embeddings = get_embeddings(chunks)
    embedding_records = [
        {
            "trial_id": trial_id,
            "chunk_text": chunk,
            "embedding": embedding.tolist(),  # Convert numpy to list
            "chunk_index": i
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    
    supabase.table("trial_embeddings").insert(embedding_records).execute()

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
    
    # Save trial to Supabase database
    supabase.table("trials").insert({
        "id": trial_id,
        "pdf_hash": pdf_hash,
        "pdf_url": pdf_url,
        "pdf_filename": file.filename,
        "inclusion_criteria": parsed_output.get("inclusion_criteria", []),
        "exclusion_criteria": parsed_output.get("exclusion_criteria", [])
    }).execute()
    
    return {
        "trial_id": trial_id,
        "raw_llm_output": parsed_output
    }

