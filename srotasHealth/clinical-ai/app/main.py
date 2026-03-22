

from fastapi import FastAPI

from app.api import match, patient, test
from app.api import trial


app = FastAPI()

app.include_router(trial.router)
app.include_router(patient.router)
app.include_router(match.router)