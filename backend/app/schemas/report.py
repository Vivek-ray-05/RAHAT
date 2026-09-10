from datetime import datetime

from pydantic import BaseModel

from app.core.enums import ApprovalActionType, RecommendationStatus, SimulationStatus


class ReviewSummary(BaseModel):
    action: ApprovalActionType
    reviewed_by_name: str | None
    reason: str | None
    created_at: datetime


class RecommendationSummary(BaseModel):
    id: int
    zone_id: int
    zone_name: str | None
    type: str
    status: RecommendationStatus
    reason: str | None
    created_at: datetime
    review: ReviewSummary | None


class AuditEventSummary(BaseModel):
    id: int
    event_type: str
    entity_type: str
    entity_id: int
    actor_name: str | None
    created_at: datetime


class PostEventReport(BaseModel):
    run_id: int
    scenario_name: str
    status: SimulationStatus
    started_by_name: str | None
    started_at: datetime
    ended_at: datetime | None
    tick_count: int
    status_counts: dict[str, int]
    recommendations: list[RecommendationSummary]
    audit_trail: list[AuditEventSummary]
