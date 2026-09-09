import httpx
import pytest

from app.core.enums import NotificationStatus
from app.services import notification_service


class _FakeUser:
    id = 1
    email = "admin@rahat.dev"
    name = "Zone Admin"


def test_not_configured_marks_notification_failed_without_raising(session, monkeypatch):
    monkeypatch.setattr(notification_service.settings, "BREVO_API_KEY", None)
    monkeypatch.setattr(notification_service.settings, "BREVO_FROM_EMAIL", None)

    from app.models.user import User
    from app.core.roles import RoleEnum
    from app.core.security import hash_secret
    user = User(email="admin@rahat.dev", name="Zone Admin", role=RoleEnum.ZONE_ADMIN, hashed_secret=hash_secret("pw"))
    session.add(user)
    session.commit()
    session.refresh(user)

    notification = notification_service.notify_user(session, user, subject="Test", body="Body")
    assert notification.status == NotificationStatus.FAILED
    assert "not configured" in notification.error


def test_configured_and_provider_accepts_marks_sent(session, monkeypatch):
    monkeypatch.setattr(notification_service.settings, "BREVO_API_KEY", "fake-key")
    monkeypatch.setattr(notification_service.settings, "BREVO_FROM_EMAIL", "no-reply@rahat.dev")

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return httpx.Response(201, json={"messageId": "abc"})

    monkeypatch.setattr(httpx, "post", fake_post)

    from app.models.user import User
    from app.core.roles import RoleEnum
    from app.core.security import hash_secret
    user = User(email="admin2@rahat.dev", name="Zone Admin Two", role=RoleEnum.ZONE_ADMIN, hashed_secret=hash_secret("pw"))
    session.add(user)
    session.commit()
    session.refresh(user)

    notification = notification_service.notify_user(session, user, subject="Test Subject", body="Test Body")

    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert captured["url"] == notification_service.BREVO_SEND_URL
    assert captured["headers"]["api-key"] == "fake-key"
    assert captured["json"]["sender"]["email"] == "no-reply@rahat.dev"
    assert captured["json"]["to"] == [{"email": "admin2@rahat.dev", "name": "Zone Admin Two"}]
    assert captured["json"]["subject"] == "Test Subject"


def test_provider_rejection_marks_failed_with_detail(session, monkeypatch):
    monkeypatch.setattr(notification_service.settings, "BREVO_API_KEY", "fake-key")
    monkeypatch.setattr(notification_service.settings, "BREVO_FROM_EMAIL", "no-reply@rahat.dev")

    def fake_post(url, headers=None, json=None, timeout=None):
        return httpx.Response(401, text="Unauthorized")

    monkeypatch.setattr(httpx, "post", fake_post)

    from app.models.user import User
    from app.core.roles import RoleEnum
    from app.core.security import hash_secret
    user = User(email="admin3@rahat.dev", name="Zone Admin Three", role=RoleEnum.ZONE_ADMIN, hashed_secret=hash_secret("pw"))
    session.add(user)
    session.commit()
    session.refresh(user)

    notification = notification_service.notify_user(session, user, subject="Test", body="Body")
    assert notification.status == NotificationStatus.FAILED
    assert "401" in notification.error


def test_user_with_no_email_is_skipped(session):
    from app.models.user import User
    from app.core.roles import RoleEnum
    user = User(phone="9999999999", name="Phone Only", role=RoleEnum.CITIZEN)
    session.add(user)
    session.commit()
    session.refresh(user)

    result = notification_service.notify_user(session, user, subject="Test", body="Body")
    assert result is None
