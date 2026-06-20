from fastapi import APIRouter, File, HTTPException, UploadFile

from app.data.demo_repository import get_dashboard_snapshot, get_protocol_learning_run
from app.domain.models import DashboardSnapshot, ProtocolLearningRun
from app.services.protocol_pdf import extract_text_from_pdf_bytes


router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/clinical-memory", response_model=DashboardSnapshot)
def clinical_memory_snapshot() -> DashboardSnapshot:
    return get_dashboard_snapshot()


@router.post("/run-protocol-learning", response_model=ProtocolLearningRun)
def run_protocol_learning() -> ProtocolLearningRun:
    return get_protocol_learning_run()


@router.post("/upload-protocol", response_model=ProtocolLearningRun)
async def upload_protocol(file: UploadFile = File(...)) -> ProtocolLearningRun:
    filename = file.filename or "protocol.pdf"

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF protocol.")

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        protocol_text = extract_text_from_pdf_bytes(file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read this PDF.") from exc

    if len(protocol_text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="No selectable text found. Scanned PDFs will need OCR in a later step.",
        )

    return get_protocol_learning_run(
        protocol_text=protocol_text,
        source_filename=filename,
        extraction_mode="pdf_text",
    )
