

from fastapi import FastAPI

from app.api import test
from app.api import trial


app = FastAPI()

app.include_router(
    trial.router
    )