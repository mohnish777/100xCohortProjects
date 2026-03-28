

from fastapi import FastAPI

from app.api import agent, match, patient, test, voice
from app.api import trial


app = FastAPI()

app.include_router(trial.router)
app.include_router(patient.router)
app.include_router(match.router)
app.include_router(agent.router)
app.include_router(voice.router)
