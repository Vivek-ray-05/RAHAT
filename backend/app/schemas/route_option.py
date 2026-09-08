from pydantic import BaseModel

from app.core.enums import RouteStatus


class RouteOptionResponse(BaseModel):
    id: int
    simulation_tick_id: int
    from_zone_id: int
    to_shelter_id: int
    path_json: dict
    eta: float
    status: RouteStatus
