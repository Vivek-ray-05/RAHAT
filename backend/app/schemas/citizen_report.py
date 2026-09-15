from datetime import datetime

from pydantic import BaseModel

from app.core.enums import CitizenReportStatus


class CitizenReportCreate(BaseModel):
    zone_id: int
    description: str
    media_url: str | None = None
    is_sos: bool = False


class CitizenReportResponse(BaseModel):
    id: int
    user_id: int
    zone_id: int
    description: str
    media_url: str | None
    is_sos: bool
    status: CitizenReportStatus
    created_at: datetime
