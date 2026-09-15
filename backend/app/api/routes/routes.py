from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.deps import require_role
from app.core.roles import RoleEnum
from app.db.session import get_session
from app.models.route_option import RouteOption
from app.models.simulation import SimulationRun, SimulationTick
from app.models.user import User
from app.schemas.route_option import RouteOptionResponse

router = APIRouter(prefix="/routes", tags=["routes"])

_operational_roles = require_role(RoleEnum.NDRF, RoleEnum.ZONE_ADMIN, RoleEnum.CENTRAL_COORDINATOR)


@router.get("", response_model=list[RouteOptionResponse])
def list_routes(
    simulation_run_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(_operational_roles),
):
    """The latest RouteOption per zone for a run -- the map's route
    layer. Defaults to the most recently started run if none is given,
    same "don't require the caller to already know an id" spirit as
    the report page's usual entry point."""
    run_id = simulation_run_id
    if run_id is None:
        latest_run = session.exec(select(SimulationRun).order_by(SimulationRun.started_at.desc())).first()
        if latest_run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No simulation runs exist yet")
        run_id = latest_run.id

    rows = session.exec(
        select(RouteOption)
        .join(SimulationTick, RouteOption.simulation_tick_id == SimulationTick.id)
        .where(SimulationTick.simulation_run_id == run_id)
        .order_by(SimulationTick.timestamp.desc())
    ).all()

    latest_by_zone: dict[int, RouteOption] = {}
    for route in rows:
        latest_by_zone.setdefault(route.from_zone_id, route)
    return list(latest_by_zone.values())
