from datetime import datetime

from sqlmodel import SQLModel, Field , Column, JSON

from app.core.enums import SimulationStatus


class SimulationRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenario.id")
    started_by_user_id: int = Field(foreign_key="user.id")
    status: SimulationStatus = Field(default=SimulationStatus.RUNNING)
    started_at: datetime
    ended_at: datetime | None = Field(default=None)


class SimulationTick(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    simulation_run_id: int = Field(foreign_key="simulationrun.id")
    tick_number: int
    timestamp: datetime
    raw_state_json: dict = Field(sa_column=Column(JSON, nullable=False))