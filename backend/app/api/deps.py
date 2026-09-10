from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlmodel import Session

from app.core.roles import RoleEnum
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.recommendation import Recommendation
from app.models.user import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = session.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def require_role(*allowed_roles: RoleEnum):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker


def authorize_recommendation_zone_access(rec: Recommendation, current_user: User) -> None:
    """A zone admin only ever sees/acts on their own zone's recommendations
    -- read-only access is gated the same as approve/modify/reject, since a
    recommendation's payload (reasoning, population, shelter assignment) is
    zone-admin/coordinator planning data, not something every authenticated
    role should be able to read by guessing an ID. A coordinator (no
    zone_id) can access any of them."""
    if current_user.role == RoleEnum.ZONE_ADMIN and rec.zone_id != current_user.zone_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This recommendation belongs to a different zone.",
        )