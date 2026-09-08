from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.route_option import RouteOption
from app.models.simulation import SimulationTick
from app.models.zone import Zone
from app.models.user import User
from app.schemas.route_option import RouteOptionResponse
from app.schemas.zone import ZoneResponse

router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("", response_model=list[ZoneResponse])
def list_zones(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    return session.exec(select(Zone)).all()


@router.get("/{zone_id}/routes", response_model=RouteOptionResponse)
def latest_route_for_zone(
    zone_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """The most recent route computed out of this zone -- ordered by
    the tick it was computed on, not by RouteOption.id, since a zone
    can have routes from multiple simulation runs."""
    route = session.exec(
        select(RouteOption)
        .join(SimulationTick, RouteOption.simulation_tick_id == SimulationTick.id)
        .where(RouteOption.from_zone_id == zone_id)
        .order_by(SimulationTick.timestamp.desc())
    ).first()

    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No route found for this zone yet")
    return route
