from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.citizen_report import CitizenReport
from app.models.user import User
from app.schemas.citizen_report import CitizenReportCreate, CitizenReportResponse

router = APIRouter(prefix="/citizen-reports", tags=["citizen-reports"])


@router.post("", response_model=CitizenReportResponse)
def create_report(
    payload: CitizenReportCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    report = CitizenReport(
        user_id=current_user.id,
        zone_id=payload.zone_id,
        description=payload.description,
        media_url=payload.media_url,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


@router.get("", response_model=list[CitizenReportResponse])
def list_reports(
    zone_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(CitizenReport)
    if zone_id is not None:
        query = query.where(CitizenReport.zone_id == zone_id)
    return session.exec(query).all()
