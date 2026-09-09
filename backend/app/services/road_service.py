"""
Persists a road block so it survives past the process that reported
it, and -- when the road belongs to a simulation that's currently
running -- applies it to that run's live routing graph right away
instead of waiting for the next tick to rebuild it.
"""
from datetime import datetime, timezone

from sqlmodel import Session

from app.models.road import Road
from app.models.road_block import RoadBlock
from app.services import simulation_service


class RoadServiceError(Exception):
    pass


def block_road(
    session: Session, road: Road, blocked_by_user_id: int,
    reason: str | None = None, simulation_run_id: int | None = None,
) -> RoadBlock:
    road.is_blocked = True
    road.blocked_by_user_id = blocked_by_user_id
    session.add(road)

    block = RoadBlock(
        road_id=road.id, blocked_by_user_id=blocked_by_user_id,
        reason=reason, created_at=datetime.now(timezone.utc),
    )
    session.add(block)
    session.commit()
    session.refresh(block)

    if simulation_run_id is not None:
        engine = simulation_service.get_active_mobility_engine(simulation_run_id)
        if engine is not None:
            engine.mark_road_blocked(road.from_zone_id, road.to_zone_id)

    return block
