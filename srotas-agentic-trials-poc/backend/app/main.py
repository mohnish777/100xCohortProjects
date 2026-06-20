import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.demo import router as demo_router
from app.api.health import router as health_router
from app.core.config import settings


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.info(
    "Starting Srotas API openai_key_configured=%s openai_model=%s log_level=%s",
    bool(settings.openai_api_key),
    settings.openai_model,
    settings.log_level,
)

app = FastAPI(
    title="Srotas Agentic Trials API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(demo_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "srotas-agentic-trials-api",
        "docs": "/docs",
    }
