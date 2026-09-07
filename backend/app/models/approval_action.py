from datetime import datetime

from sqlmodel import SQLModel, Field, Column, JSON

from app.core.enums import ApprovalActionType


class ApprovalAction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recommendation_id: int = Field(foreign_key="recommendation.id")
    reviewed_by_user_id: int = Field(foreign_key="user.id")
    action: ApprovalActionType
    modified_payload_json: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    reason: str | None = Field(default=None)
    created_at: datetime