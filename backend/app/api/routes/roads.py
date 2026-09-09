from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_role
from app.core.roles import RoleEnum
from app.db.session import get_session
from app.models.road import Road
from app.models.user import User
from app.schemas.road import BlockRoadRequest, RoadBlockResponse, RoadResponse
from app.services import road_service

router = APIRouter(prefix="/roads", tags=["roads"])


@router.get("", response_model=list[RoadResponse])
def list_roads(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    return session.exec(select(Road)).all()


@router.post("/{road_id}/block", response_model=RoadBlockResponse)
def block_road(
    road_id: int,
    payload: BlockRoadRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.NDRF, RoleEnum.ZONE_ADMIN, RoleEnum.CENTRAL_COORDINATOR)),
):
    road = session.get(Road, road_id)
    if road is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Road not found")

    return road_service.block_road(
        session, road, current_user.id,
        reason=payload.reason, simulation_run_id=payload.simulation_run_id,
    )
