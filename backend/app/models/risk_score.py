from sqlmodel import SQLModel, Field

from app.core.enums import RiskLevel


class RiskScore(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    simulation_tick_id: int = Field(foreign_key="simulationtick.id")
    zone_id: int = Field(foreign_key="zone.id")
    score: float
    risk_level: RiskLevel
    confidence: float
    reason: str