from datetime import datetime, timezone

from sqlmodel import SQLModel, Field


class RoadBlock(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    road_id: int = Field(foreign_key="road.id")
    blocked_by_user_id: int = Field(foreign_key="user.id")
    reason: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cleared_at: datetime | None = Field(default=None)
