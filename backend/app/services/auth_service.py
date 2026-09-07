"""
Login/OTP business logic. Replaces the old prototype's backend/auth.py.
"""
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.config import settings
from app.core.roles import RoleEnum
from app.core.security import create_access_token, verify_secret
from app.models.user import User

OTP_TTL_MINUTES = 10
DEV_OTP_CODE = "1234"

# phone -> (code, expires_at). In-memory only -- fine for local dev,
# revisit once a real OTP provider is wired in (Phase 6).
_otp_store: dict[str, tuple[str, datetime]] = {}


class AuthError(Exception):
    """Raised for any login failure the API layer should turn into a 401."""


def request_otp(phone: str) -> str:
    if not settings.DEV_MODE:
        raise NotImplementedError(
            "No OTP provider configured. Set DEV_MODE=true for local "
            "testing, or wire a real provider in services/notification_service.py."
        )
    code = DEV_OTP_CODE
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)
    _otp_store[phone] = (code, expires_at)
    return code


def verify_otp(session: Session, phone: str, code: str) -> User:
    stored = _otp_store.get(phone)
    if stored is None:
        raise AuthError("No OTP was requested for this phone number.")

    stored_code, expires_at = stored
    if datetime.now(timezone.utc) > expires_at:
        del _otp_store[phone]
        raise AuthError("OTP has expired. Request a new one.")

    if code != stored_code:
        raise AuthError("Incorrect OTP.")

    del _otp_store[phone]

    user = session.exec(select(User).where(User.phone == phone)).first()
    if user is None:
        user = User(phone=phone, name=phone, role=RoleEnum.CITIZEN)
        session.add(user)
        session.commit()
        session.refresh(user)

    return user


def authenticate_password(
    session: Session, email: str, password: str, role: RoleEnum
) -> User:
    user = session.exec(
        select(User).where(User.email == email, User.role == role)
    ).first()

    if user is None or user.hashed_secret is None:
        raise AuthError("Invalid email or password.")

    if not verify_secret(password, user.hashed_secret):
        raise AuthError("Invalid email or password.")

    return user


def issue_token(user: User) -> str:
    return create_access_token(user.id, user.role.value)