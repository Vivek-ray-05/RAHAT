from datetime import datetime

from pydantic import BaseModel

from app.core.enums import SimulationStatus


class StartSimulationRequest(BaseModel):
    scenario_id: int


class SimulationRunResponse(BaseModel):
    id: int
    scenario_id: int
    status: SimulationStatus
    started_at: datetime
    ended_at: datetime | None


class TickResponse(BaseModel):
    id: int
    tick_number: int
    timestamp: datetime
    raw_state_json: dict


class SimulationRunListItem(BaseModel):
    id: int
    scenario_id: int
    scenario_name: str
    status: SimulationStatus
    started_by_name: str | None
    started_at: datetime
    ended_at: datetime | None
