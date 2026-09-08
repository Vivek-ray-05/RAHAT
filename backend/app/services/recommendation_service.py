"""
Turns a DecisionGovernor plan into Recommendation rows a zone admin can
review -- creating these never changes anything else in the system.
Only execute() (called after approval, from approval_service.py)
applies a real effect.
"""
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.core.enums import RecommendationStatus
from app.models.recommendation import Recommendation
from app.models.shelter import Shelter

RECOMMENDATION_TTL_MINUTES = 30


def create_from_plan(session: Session, simulation_run_id: int, simulation_tick_id: int, plan: dict) -> list[Recommendation]:
    """One Recommendation per zone entry in the plan's evacuation
    sequence. Every one starts pending_review -- nothing here is
    applied to the city's state."""
    now = datetime.now(timezone.utc)
    created = []

    for entry in plan["evacuation_sequence"]:
        rec = Recommendation(
            simulation_run_id=simulation_run_id,
            simulation_tick_id=simulation_tick_id,
            zone_id=entry["zone_id"],
            type="evacuation_assignment",
            payload_json=entry,
            status=RecommendationStatus.PENDING_REVIEW,
            created_at=now,
            expires_at=now + timedelta(minutes=RECOMMENDATION_TTL_MINUTES),
        )
        session.add(rec)
        created.append(rec)

    session.commit()
    for rec in created:
        session.refresh(rec)
    return created


def get_pending(
    session: Session, simulation_run_id: int | None = None, zone_id: int | None = None,
) -> list[Recommendation]:
    query = select(Recommendation).where(Recommendation.status == RecommendationStatus.PENDING_REVIEW)
    if simulation_run_id is not None:
        query = query.where(Recommendation.simulation_run_id == simulation_run_id)
    if zone_id is not None:
        query = query.where(Recommendation.zone_id == zone_id)
    return session.exec(query).all()


def execute(session: Session, recommendation: Recommendation, payload: dict | None = None) -> Recommendation:
    """Apply a recommendation's real effect. Called only after approval
    (or approval-with-modification) -- approval_service.py owns that
    gate, this function just does the work once told to."""
    data = payload or recommendation.payload_json

    shelter_id = data.get("assigned_shelter_id")
    assigned_population = data.get("assigned_population", 0)

    if shelter_id and assigned_population:
        shelter = session.get(Shelter, shelter_id)
        if shelter:
            shelter.current_occupancy += assigned_population
            session.add(shelter)

    recommendation.status = RecommendationStatus.EXECUTED
    session.add(recommendation)
    session.commit()
    session.refresh(recommendation)
    return recommendation


def expire_stale(session: Session, simulation_run_id: int | None = None) -> list[Recommendation]:
    """Move any pending recommendation whose expires_at has passed to
    expired. Meant to be called once per tick."""
    now = datetime.now(timezone.utc)
    query = select(Recommendation).where(
        Recommendation.status == RecommendationStatus.PENDING_REVIEW,
        Recommendation.expires_at < now,
    )
    if simulation_run_id is not None:
        query = query.where(Recommendation.simulation_run_id == simulation_run_id)

    stale = session.exec(query).all()
    for rec in stale:
        rec.status = RecommendationStatus.EXPIRED
        session.add(rec)
    session.commit()
    return stale