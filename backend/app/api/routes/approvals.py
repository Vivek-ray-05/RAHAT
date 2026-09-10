from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.deps import authorize_recommendation_zone_access, get_current_user, require_role
from app.core.roles import RoleEnum
from app.db.session import get_session
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.approval import ModifyRequest, RejectRequest
from app.schemas.recommendation import RecommendationResponse
from app.services import approval_service as svc

router = APIRouter(prefix="/recommendations", tags=["approvals"])

_reviewer_roles = require_role(RoleEnum.ZONE_ADMIN, RoleEnum.CENTRAL_COORDINATOR)


def _get_rec_or_404(session: Session, recommendation_id: int) -> Recommendation:
    rec = session.get(Recommendation, recommendation_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return rec


@router.post("/{recommendation_id}/approve", response_model=RecommendationResponse)
def approve(
    recommendation_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(_reviewer_roles),
):
    rec = _get_rec_or_404(session, recommendation_id)
    authorize_recommendation_zone_access(rec, current_user)
    try:
        return svc.approve(session, rec, current_user.id)
    except svc.ApprovalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{recommendation_id}/modify", response_model=RecommendationResponse)
def modify(
    recommendation_id: int,
    payload: ModifyRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(_reviewer_roles),
):
    rec = _get_rec_or_404(session, recommendation_id)
    authorize_recommendation_zone_access(rec, current_user)
    try:
        return svc.modify(session, rec, current_user.id, payload.modified_payload, payload.reason)
    except svc.ApprovalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{recommendation_id}/reject", response_model=RecommendationResponse)
def reject(
    recommendation_id: int,
    payload: RejectRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(_reviewer_roles),
):
    rec = _get_rec_or_404(session, recommendation_id)
    authorize_recommendation_zone_access(rec, current_user)
    try:
        return svc.reject(session, rec, current_user.id, payload.reason)
    except svc.ApprovalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))