import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import agent, match, patient, test, trial, voice


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
AUDIO_DIR = BASE_DIR / "my_audio_files"

UPLOADS_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

app = FastAPI(
    title="Srotas Health API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(test.router)
app.include_router(trial.router)
app.include_router(patient.router)
app.include_router(match.router)
app.include_router(agent.router)
app.include_router(voice.router)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/media", StaticFiles(directory=AUDIO_DIR), name="media")


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "srotas-health-api",
        "docs": "/docs",
    }
