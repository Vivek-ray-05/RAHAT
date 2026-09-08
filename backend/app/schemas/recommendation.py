from datetime import datetime

from pydantic import BaseModel

from app.core.enums import RecommendationStatus


class RecommendationResponse(BaseModel):
    id: int
    simulation_run_id: int
    simulation_tick_id: int
    zone_id: int
    type: str
    payload_json: dict
    status: RecommendationStatus
    created_at: datetime
    expires_at: datetime | None