from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.zone import Zone
from app.models.user import User
from app.schemas.zone import ZoneResponse

router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("", response_model=list[ZoneResponse])
def list_zones(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    return session.exec(select(Zone)).all()
