"""
Sends real email via Brevo's transactional email API and always
persists a Notification row -- whether or not Brevo is configured --
so notification history exists and is inspectable even before real
credentials are set. A send failure is captured on the row and never
raised to the caller: a notification going out is never allowed to
block the real state change (e.g. a recommendation being created)
that triggered it.
"""
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.config import settings
from app.core.enums import NotificationChannel, NotificationStatus
from app.models.notification import Notification
from app.models.user import User

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


class NotificationError(Exception):
    pass


def _send_email_via_brevo(to_email: str, to_name: str, subject: str, body: str) -> None:
    if not settings.BREVO_API_KEY:
        raise NotificationError("Brevo is not configured (BREVO_API_KEY unset).")
    if not settings.BREVO_FROM_EMAIL:
        raise NotificationError("Brevo is not configured (BREVO_FROM_EMAIL unset).")

    response = httpx.post(
        BREVO_SEND_URL,
        headers={"api-key": settings.BREVO_API_KEY, "Content-Type": "application/json"},
        json={
            "sender": {"email": settings.BREVO_FROM_EMAIL, "name": "RAHAT"},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "textContent": body,
        },
        timeout=10.0,
    )
    if response.status_code >= 400:
        raise NotificationError(f"Brevo rejected the email: {response.status_code} {response.text}")


def notify_user(session: Session, user: User, subject: str, body: str) -> Notification | None:
    """Email-only for now -- every role that would receive a
    notification (zone_admin, central_coordinator) logs in with an
    email, unlike citizen/NDRF's phone+OTP. Returns None (and writes
    nothing) if the user has no email to send to."""
    if not user.email:
        return None

    notification = Notification(
        user_id=user.id, channel=NotificationChannel.EMAIL,
        subject=subject, body=body, status=NotificationStatus.PENDING,
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)

    try:
        _send_email_via_brevo(user.email, user.name, subject, body)
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(timezone.utc)
    except NotificationError as e:
        notification.status = NotificationStatus.FAILED
        notification.error = str(e)

    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification
