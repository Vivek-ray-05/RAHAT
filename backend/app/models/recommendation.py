from datetime import datetime

from sqlmodel import SQLModel, Field, Column, JSON

from app.core.enums import RecommendationStatus


class Recommendation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    simulation_run_id: int = Field(foreign_key="simulationrun.id")
    simulation_tick_id: int = Field(foreign_key="simulationtick.id")
    type: str
    payload_json: dict = Field(sa_column=Column(JSON, nullable=False))
    status: RecommendationStatus = Field(default=RecommendationStatus.PENDING_REVIEW)
    created_at: datetime
    expires_at: datetime | None = Field(default=None)