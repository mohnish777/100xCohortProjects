import logging
from hashlib import sha256

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.data.demo_repository import (
    get_cached_protocol_extraction,
    get_dashboard_snapshot,
    get_protocol_learning_run,
    remember_protocol_extraction,
    reset_demo_session,
    store_patient_intake,
)
from app.data.supabase_persistence import storage_status
from app.domain.models import (
    DashboardSnapshot,
    DemoResetRequest,
    IntakeAgentRun,
    PatientIntakeRequest,
    ProtocolLearningRun,
)
from app.services.intake_agent import extract_intake_with_agent, make_transcript_excerpt
from app.services.protocol_agent import extract_protocol_with_agent
from app.services.protocol_pdf import extract_text_from_pdf_bytes


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/clinical-memory", response_model=DashboardSnapshot)
def clinical_memory_snapshot() -> DashboardSnapshot:
    return get_dashboard_snapshot()


@router.get("/storage-status")
def demo_storage_status() -> dict[str, object]:
    status = storage_status()
    logger.info("Storage status requested storage_mode=%s", status["storage_mode"])
    return status


@router.post("/reset-session", response_model=DashboardSnapshot)
def reset_session(request: DemoResetRequest) -> DashboardSnapshot:
    logger.info("Demo session reset requested patient_name=%s", request.patient_name)
    return reset_demo_session(request.patient_name)


@router.post("/run-protocol-learning", response_model=ProtocolLearningRun)
def run_protocol_learning() -> ProtocolLearningRun:
    return get_protocol_learning_run()


@router.post("/run-intake-agent", response_model=IntakeAgentRun)
def run_intake_agent(request: PatientIntakeRequest) -> IntakeAgentRun:
    transcript = request.transcript.strip()
    logger.info(
        "Intake Agent request received patient_id=%s patient_name=%s transcript_chars=%d",
        request.patient_id,
        request.patient_name,
        len(transcript),
    )

    if len(transcript) < 20:
        logger.warning("Intake Agent request rejected reason=short_transcript")
        raise HTTPException(
            status_code=400,
            detail="Please provide a longer patient history transcript.",
        )

    agent_output, agent_mode = extract_intake_with_agent(transcript)
    store_patient_intake(patient_name=request.patient_name, agent_output=agent_output)
    logger.info(
        "Intake Agent returned patient_id=%s patient_name=%s agent_mode=%s facts=%d missing=%d",
        request.patient_id,
        request.patient_name,
        agent_mode,
        len(agent_output.extracted_facts),
        len(agent_output.missing_facts),
    )

    return IntakeAgentRun(
        patient_id=request.patient_id,
        agent_mode=agent_mode,
        transcript_excerpt=make_transcript_excerpt(transcript),
        output=agent_output,
    )


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

    protocol_hash = sha256(file_bytes).hexdigest()
    cached_protocol = get_cached_protocol_extraction(protocol_hash)
    if cached_protocol:
        logger.info(
            "Protocol upload cache hit filename=%s protocol_hash=%s cached_filename=%s",
            filename,
            protocol_hash,
            cached_protocol.source_filename,
        )
        return get_protocol_learning_run(
            protocol_text=cached_protocol.protocol_text,
            source_filename=filename,
            extraction_mode="pdf_text",
            agent_output=cached_protocol.agent_output,
            agent_mode=cached_protocol.agent_mode,
            protocol_cache_status="cached",
            protocol_hash=protocol_hash,
        )

    logger.info("Protocol upload cache miss filename=%s protocol_hash=%s", filename, protocol_hash)

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
    remember_protocol_extraction(
        protocol_hash=protocol_hash,
        source_filename=filename,
        protocol_text=protocol_text,
        agent_output=agent_output,
        agent_mode=agent_mode,
    )

    return get_protocol_learning_run(
        protocol_text=protocol_text,
        source_filename=filename,
        extraction_mode="pdf_text",
        agent_output=agent_output,
        agent_mode=agent_mode,
        protocol_cache_status="new_extraction",
        protocol_hash=protocol_hash,
    )
