from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.shelter import Shelter
from app.models.user import User
from app.schemas.shelter import NearestShelterResponse, ShelterResponse
from app.services import shelter_service

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


@router.get("/nearest", response_model=NearestShelterResponse)
def nearest_shelter(
    zone_id: int = Query(),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Directions for a citizen (or anyone) picking a zone: the
    official evacuation assignment for that zone if one exists, else
    the nearest shelter with room, by real straight-line distance."""
    try:
        result = shelter_service.find_nearest_shelter(session, zone_id)
    except shelter_service.NoShelterAvailableError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return result
