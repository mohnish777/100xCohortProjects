from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "srotas-agentic-trials-api",
        "model": settings.openai_model,
        "reasoning_effort": settings.openai_reasoning_effort,
    }

