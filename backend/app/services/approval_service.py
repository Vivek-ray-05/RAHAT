"""
The actual human-in-the-loop gate: a zone admin approves, modifies, or
rejects a pending recommendation. Nothing in this system changes real
state on its own -- this is the only path that does.
"""
from datetime import datetime, timezone

from sqlmodel import Session

from app.core.enums import ApprovalActionType, RecommendationStatus
from app.models.approval_action import ApprovalAction
from app.models.recommendation import Recommendation
from app.services import audit_service, recommendation_service


class ApprovalError(Exception):
    pass


def _require_pending(recommendation: Recommendation) -> None:
    if recommendation.status != RecommendationStatus.PENDING_REVIEW:
        raise ApprovalError(
            f"Recommendation {recommendation.id} is {recommendation.status.value}, not pending_review."
        )


def approve(session: Session, recommendation: Recommendation, reviewed_by_user_id: int) -> Recommendation:
    _require_pending(recommendation)
    before = {"status": recommendation.status.value}

    session.add(ApprovalAction(
        recommendation_id=recommendation.id, reviewed_by_user_id=reviewed_by_user_id,
        action=ApprovalActionType.APPROVE, created_at=datetime.now(timezone.utc),
    ))
    recommendation.status = RecommendationStatus.APPROVED
    session.add(recommendation)
    session.commit()

    recommendation_service.execute(session, recommendation)

    audit_service.write_event(
        session, reviewed_by_user_id, "recommendation_approved",
        "recommendation", recommendation.id, before=before,
        after={"status": recommendation.status.value},
    )
    return recommendation


def modify(
    session: Session, recommendation: Recommendation, reviewed_by_user_id: int,
    modified_payload: dict, reason: str | None = None,
) -> Recommendation:
    _require_pending(recommendation)
    before = {"status": recommendation.status.value, "payload": recommendation.payload_json}

    session.add(ApprovalAction(
        recommendation_id=recommendation.id, reviewed_by_user_id=reviewed_by_user_id,
        action=ApprovalActionType.MODIFY, modified_payload_json=modified_payload,
        reason=reason, created_at=datetime.now(timezone.utc),
    ))
    recommendation.status = RecommendationStatus.MODIFIED
    session.add(recommendation)
    session.commit()

    recommendation_service.execute(session, recommendation, payload=modified_payload)

    audit_service.write_event(
        session, reviewed_by_user_id, "recommendation_modified",
        "recommendation", recommendation.id, before=before,
        after={"status": recommendation.status.value, "payload": modified_payload},
    )
    return recommendation


def reject(
    session: Session, recommendation: Recommendation, reviewed_by_user_id: int, reason: str,
) -> Recommendation:
    _require_pending(recommendation)
    before = {"status": recommendation.status.value}

    session.add(ApprovalAction(
        recommendation_id=recommendation.id, reviewed_by_user_id=reviewed_by_user_id,
        action=ApprovalActionType.REJECT, reason=reason, created_at=datetime.now(timezone.utc),
    ))
    recommendation.status = RecommendationStatus.REJECTED
    session.add(recommendation)
    session.commit()

    audit_service.write_event(
        session, reviewed_by_user_id, "recommendation_rejected",
        "recommendation", recommendation.id, before=before,
        after={"status": recommendation.status.value, "reason": reason},
    )
    return recommendation