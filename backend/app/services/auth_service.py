"""
Login/OTP business logic. Replaces the old prototype's backend/auth.py.
"""
from sqlmodel import Session, select

from app.config import settings
from app.core.redis_client import redis_client
from app.core.roles import RoleEnum
from app.core.security import create_access_token, verify_secret
from app.models.user import User

OTP_TTL_SECONDS = 10 * 60
DEV_OTP_CODE = "1234"


def _otp_key(phone: str) -> str:
    return f"otp:{phone}"


class AuthError(Exception):
    """Raised for any login failure the API layer should turn into a 401."""


def request_otp(phone: str) -> str:
    if not settings.DEV_MODE:
        raise NotImplementedError(
            "No OTP provider configured. Set DEV_MODE=true for local "
            "testing, or wire a real provider in services/notification_service.py."
        )
    code = DEV_OTP_CODE
    # Redis's own TTL does the expiry -- no manual expires_at bookkeeping,
    # and (unlike an in-process dict) this is visible to every backend
    # worker/container, not just whichever one handled this request.
    redis_client.set(_otp_key(phone), code, ex=OTP_TTL_SECONDS)
    return code


def verify_otp(session: Session, phone: str, code: str) -> User:
    stored_code = redis_client.get(_otp_key(phone))
    if stored_code is None:
        raise AuthError("No OTP was requested for this phone number, or it expired.")

    if code != stored_code:
        raise AuthError("Incorrect OTP.")

    redis_client.delete(_otp_key(phone))

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