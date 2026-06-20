from fastapi import APIRouter

from app.data.demo_repository import get_dashboard_snapshot
from app.domain.models import DashboardSnapshot


router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/clinical-memory", response_model=DashboardSnapshot)
def clinical_memory_snapshot() -> DashboardSnapshot:
    return get_dashboard_snapshot()
