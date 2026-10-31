from datetime import date

from fastapi import APIRouter

from app.routers.dependencies import SessionDep, service_errors
from app.schema.analytics import AnalyticsSummary
from app.service.analytics_service import summary_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(session: SessionDep, start: date | None = None, end: date | None = None):
    """Dashboard numbers for start..end (inclusive, business time zone); defaults to the last 12 months."""
    with service_errors():
        return summary_service(session, start=start, end=end)
