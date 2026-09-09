from datetime import datetime

from pydantic import BaseModel


class RoadResponse(BaseModel):
    id: int
    from_zone_id: int
    to_zone_id: int
    capacity: int | None
    distance_km: float | None
    is_blocked: bool
    blocked_by_user_id: int | None


class BlockRoadRequest(BaseModel):
    reason: str | None = None
    simulation_run_id: int | None = None


class RoadBlockResponse(BaseModel):
    id: int
    road_id: int
    blocked_by_user_id: int
    reason: str | None
    created_at: datetime
    cleared_at: datetime | None
