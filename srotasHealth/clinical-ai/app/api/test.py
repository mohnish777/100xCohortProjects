from fastapi import APIRouter
from app.services.llm_services import call_llm

router = APIRouter()

@router.get("/health")
def test():
    return {"status": "ok"}


@router.post("/test-llm")
def test():
    prompt = "explain what is diabetes in 2 lines"
    response = call_llm(prompt)
    return {"response": response}