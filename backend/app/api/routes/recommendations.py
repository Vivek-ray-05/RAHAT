from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.roles import RoleEnum
from app.db.session import get_session
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse
from app.services import recommendation_service as svc

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationResponse])
def list_pending(
    simulation_run_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # A zone admin only ever sees their own zone's queue. A coordinator
    # (or anyone without a zone assigned) sees everything.
    zone_id = current_user.zone_id if current_user.role == RoleEnum.ZONE_ADMIN else None
    return svc.get_pending(session, simulation_run_id, zone_id)


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_one(
    recommendation_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    rec = session.get(Recommendation, recommendation_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return rec
