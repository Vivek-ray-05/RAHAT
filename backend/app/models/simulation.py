from datetime import datetime

from sqlmodel import SQLModel, Field

from app.core.enums import SimulationStatus


class SimulationRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    started_by_user_id: int = Field(foreign_key="user.id")
    status: SimulationStatus = Field(default=SimulationStatus.RUNNING)
    started_at: datetime
    ended_at: datetime | None = Field(default=None)