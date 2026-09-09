from datetime import datetime, timezone

from sqlmodel import SQLModel, Field

from app.core.enums import NotificationChannel, NotificationStatus


class Notification(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    channel: NotificationChannel
    subject: str
    body: str
    status: NotificationStatus = Field(default=NotificationStatus.PENDING)
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = Field(default=None)
