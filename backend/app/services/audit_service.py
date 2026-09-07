"""
Every state-changing action in this system writes one AuditEvent.
Nothing here decides whether an action should happen -- it just
records that it did.
"""
from datetime import datetime, timezone

from sqlmodel import Session

from app.models.audit_event import AuditEvent


def write_event(
    session: Session, actor_user_id: int | None, event_type: str,
    entity_type: str, entity_id: int, before: dict | None = None, after: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before,
        after_json=after,
        created_at=datetime.now(timezone.utc),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event