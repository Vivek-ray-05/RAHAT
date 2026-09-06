from datetime import datetime, timezone

from sqlmodel import SQLModel, Field

from app.core.enums import CitizenReportStatus


class CitizenReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    zone_id: int = Field(foreign_key="zone.id")
    description: str
    media_url: str | None = Field(default=None)
    status: CitizenReportStatus = Field(default=CitizenReportStatus.NEW)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))