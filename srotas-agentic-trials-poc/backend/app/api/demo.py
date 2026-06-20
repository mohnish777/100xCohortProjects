import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.data.demo_repository import get_dashboard_snapshot, get_protocol_learning_run
from app.domain.models import DashboardSnapshot, ProtocolLearningRun
from app.services.protocol_agent import extract_protocol_with_agent
from app.services.protocol_pdf import extract_text_from_pdf_bytes


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/clinical-memory", response_model=DashboardSnapshot)
def clinical_memory_snapshot() -> DashboardSnapshot:
    return get_dashboard_snapshot()


@router.post("/run-protocol-learning", response_model=ProtocolLearningRun)
def run_protocol_learning() -> ProtocolLearningRun:
    return get_protocol_learning_run()


@router.get("/openai-status")
def openai_status() -> dict[str, object]:
    key_configured = bool(settings.openai_api_key)
    logger.info(
        "OpenAI status check requested openai_key_configured=%s model=%s",
        key_configured,
        settings.openai_model,
    )

    if not key_configured:
        return {
            "openai_key_configured": False,
            "model": settings.openai_model,
            "status": "missing_key",
        }

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )
        model = client.models.retrieve(settings.openai_model)
        logger.info("OpenAI status check succeeded model=%s", settings.openai_model)
        return {
            "openai_key_configured": True,
            "model": settings.openai_model,
            "status": "ok",
            "resolved_model": model.id,
        }
    except Exception as exc:
        logger.warning(
            "OpenAI status check failed model=%s error_type=%s error=%s",
            settings.openai_model,
            type(exc).__name__,
            exc,
        )
        return {
            "openai_key_configured": True,
            "model": settings.openai_model,
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


@router.post("/upload-protocol", response_model=ProtocolLearningRun)
async def upload_protocol(file: UploadFile = File(...)) -> ProtocolLearningRun:
    filename = file.filename or "protocol.pdf"
    logger.info(
        "Protocol upload received filename=%s content_type=%s",
        filename,
        file.content_type,
    )

    if not filename.lower().endswith(".pdf"):
        logger.warning("Protocol upload rejected non_pdf filename=%s", filename)
        raise HTTPException(status_code=400, detail="Please upload a PDF protocol.")

    file_bytes = await file.read()
    logger.info("Protocol upload read filename=%s size_bytes=%d", filename, len(file_bytes))

    if not file_bytes:
        logger.warning("Protocol upload rejected empty_pdf filename=%s", filename)
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        protocol_text = extract_text_from_pdf_bytes(file_bytes)
    except Exception as exc:
        logger.warning(
            "Protocol upload PDF read failed filename=%s error_type=%s error=%s",
            filename,
            type(exc).__name__,
            exc,
        )
        raise HTTPException(status_code=400, detail="Could not read this PDF.") from exc

    if len(protocol_text.strip()) < 20:
        logger.warning(
            "Protocol upload rejected no_selectable_text filename=%s chars=%d",
            filename,
            len(protocol_text.strip()),
        )
        raise HTTPException(
            status_code=400,
            detail="No selectable text found. Scanned PDFs will need OCR in a later step.",
        )

    logger.info("Protocol upload text ready filename=%s chars=%d", filename, len(protocol_text))
    agent_output, agent_mode = extract_protocol_with_agent(protocol_text)
    logger.info(
        "Protocol Agent returned filename=%s agent_mode=%s facts=%d criteria=%d",
        filename,
        agent_mode,
        len(agent_output.extracted_facts),
        len(agent_output.extracted_criteria),
    )

    return get_protocol_learning_run(
        protocol_text=protocol_text,
        source_filename=filename,
        extraction_mode="pdf_text",
        agent_output=agent_output,
        agent_mode=agent_mode,
    )
