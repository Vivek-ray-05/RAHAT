from datetime import datetime

from sqlmodel import SQLModel, Field, Column, JSON


class AuditEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    actor_user_id: int | None = Field(default=None, foreign_key="user.id")
    event_type: str
    entity_type: str
    entity_id: int
    before_json: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    after_json: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime