from datetime import datetime

from sqlmodel import SQLModel, Field, Column, JSON


class SensorEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    simulation_run_id: int | None = Field(default=None, foreign_key="simulationrun.id")
    source_adapter: str
    zone_id: int = Field(foreign_key="zone.id")
    event_type: str
    value: float
    confidence: float
    provenance: dict = Field(sa_column=Column(JSON, nullable=False))
    received_at: datetime