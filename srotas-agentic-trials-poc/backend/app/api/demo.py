from fastapi import APIRouter

from app.data.demo_repository import get_dashboard_snapshot, get_protocol_learning_run
from app.domain.models import DashboardSnapshot, ProtocolLearningRun


router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/clinical-memory", response_model=DashboardSnapshot)
def clinical_memory_snapshot() -> DashboardSnapshot:
    return get_dashboard_snapshot()


@router.post("/run-protocol-learning", response_model=ProtocolLearningRun)
def run_protocol_learning() -> ProtocolLearningRun:
    return get_protocol_learning_run()
