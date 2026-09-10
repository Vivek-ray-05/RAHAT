"""
Assembles a read-only post-event report for one simulation run: what
was recommended, how each recommendation was reviewed (or wasn't),
and the full audit trail behind those decisions. Pure aggregation --
writes nothing, decides nothing. Existing state changes are recorded
by approval_service.py/audit_service.py as they happen; this just
reads them back in one shape for a human to review afterward.
"""
from collections import Counter

from sqlmodel import Session, func, select

from app.models.approval_action import ApprovalAction
from app.models.audit_event import AuditEvent
from app.models.recommendation import Recommendation
from app.models.scenario import Scenario
from app.models.simulation import SimulationRun, SimulationTick
from app.models.user import User
from app.models.zone import Zone
from app.schemas.report import AuditEventSummary, PostEventReport, RecommendationSummary, ReviewSummary


def build_report(session: Session, run: SimulationRun, zone_id: int | None = None) -> PostEventReport:
    """zone_id scopes the recommendations (and the audit trail that
    follows from them) to one zone -- the same scoping
    recommendations.py applies for a zone admin, since a report is
    just recommendations viewed in aggregate rather than one at a
    time."""
    scenario = session.get(Scenario, run.scenario_id)
    starter = session.get(User, run.started_by_user_id)

    tick_count = session.exec(
        select(func.count()).select_from(SimulationTick).where(SimulationTick.simulation_run_id == run.id)
    ).one()

    rec_query = select(Recommendation).where(Recommendation.simulation_run_id == run.id)
    if zone_id is not None:
        rec_query = rec_query.where(Recommendation.zone_id == zone_id)
    recommendations = session.exec(rec_query.order_by(Recommendation.created_at)).all()
    rec_ids = [r.id for r in recommendations]

    zones = {z.id: z for z in session.exec(select(Zone)).all()}
    users = {u.id: u for u in session.exec(select(User)).all()}

    actions_by_rec: dict[int, ApprovalAction] = {}
    if rec_ids:
        for action in session.exec(select(ApprovalAction).where(ApprovalAction.recommendation_id.in_(rec_ids))):
            # A recommendation leaves pending_review for good on its first
            # review (approval_service._require_pending), so there's at
            # most one ApprovalAction per recommendation.
            actions_by_rec[action.recommendation_id] = action

    status_counts: Counter[str] = Counter()
    rec_summaries = []
    for rec in recommendations:
        status_counts[rec.status.value] += 1
        action = actions_by_rec.get(rec.id)
        zone = zones.get(rec.zone_id)
        rec_summaries.append(RecommendationSummary(
            id=rec.id,
            zone_id=rec.zone_id,
            zone_name=zone.name if zone else None,
            type=rec.type,
            status=rec.status,
            reason=rec.payload_json.get("reason"),
            created_at=rec.created_at,
            review=ReviewSummary(
                action=action.action,
                reviewed_by_name=users[action.reviewed_by_user_id].name if action.reviewed_by_user_id in users else None,
                reason=action.reason,
                created_at=action.created_at,
            ) if action else None,
        ))

    audit_summaries = []
    if rec_ids:
        events = session.exec(
            select(AuditEvent)
            .where(AuditEvent.entity_type == "recommendation", AuditEvent.entity_id.in_(rec_ids))
            .order_by(AuditEvent.created_at)
        ).all()
        audit_summaries = [
            AuditEventSummary(
                id=e.id,
                event_type=e.event_type,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                actor_name=users[e.actor_user_id].name if e.actor_user_id in users else None,
                created_at=e.created_at,
            )
            for e in events
        ]

    return PostEventReport(
        run_id=run.id,
        scenario_name=scenario.name if scenario else f"Scenario {run.scenario_id}",
        status=run.status,
        started_by_name=starter.name if starter else None,
        started_at=run.started_at,
        ended_at=run.ended_at,
        tick_count=tick_count,
        status_counts=dict(status_counts),
        recommendations=rec_summaries,
        audit_trail=audit_summaries,
    )
