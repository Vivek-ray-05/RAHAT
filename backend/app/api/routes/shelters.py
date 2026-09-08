from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.shelter import Shelter
from app.models.user import User
from app.schemas.shelter import ShelterResponse

router = APIRouter(prefix="/shelters", tags=["shelters"])


@router.get("", response_model=list[ShelterResponse])
def list_shelters(
    zone_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Shelter)
    if zone_id is not None:
        query = query.where(Shelter.zone_id == zone_id)
    return session.exec(query).all()
