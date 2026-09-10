from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import require_role
from app.core.roles import RoleEnum
from app.db.session import get_session
from app.models.road import Road
from app.models.user import User
from app.schemas.road import BlockRoadRequest, RoadBlockResponse, RoadResponse
from app.services import road_service

router = APIRouter(prefix="/roads", tags=["roads"])

# Road capacity/blockage is operational routing data for the roles that
# act on it -- no citizen-facing UI reads this, so it's scoped the same
# as blocking a road already was, rather than left open to any authenticated role.
_operational_roles = require_role(RoleEnum.NDRF, RoleEnum.ZONE_ADMIN, RoleEnum.CENTRAL_COORDINATOR)


@router.get("", response_model=list[RoadResponse])
def list_roads(session: Session = Depends(get_session), current_user: User = Depends(_operational_roles)):
    return session.exec(select(Road)).all()


@router.post("/{road_id}/block", response_model=RoadBlockResponse)
def block_road(
    road_id: int,
    payload: BlockRoadRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(_operational_roles),
):
    road = session.get(Road, road_id)
    if road is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Road not found")

    return road_service.block_road(
        session, road, current_user.id,
        reason=payload.reason, simulation_run_id=payload.simulation_run_id,
    )
