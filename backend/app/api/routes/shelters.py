from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.deps import authorize_shelter_zone_access, get_current_user, require_role
from app.core.roles import RoleEnum
from app.db.session import get_session
from app.models.shelter import Shelter
from app.models.user import User
from app.schemas.shelter import NearestShelterResponse, ShelterResponse, UpdateShelterOccupancyRequest
from app.services import audit_service, shelter_service

router = APIRouter(prefix="/shelters", tags=["shelters"])

_occupancy_editors = require_role(RoleEnum.ZONE_ADMIN, RoleEnum.CENTRAL_COORDINATOR)


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


@router.patch("/{shelter_id}", response_model=ShelterResponse)
def update_occupancy(
    shelter_id: int,
    payload: UpdateShelterOccupancyRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(_occupancy_editors),
):
    """Person-count only -- how many people are actually at a shelter
    right now, nothing else. Clamped to the shelter's real capacity,
    same clamp-not-reject precedent as recommendation_service.execute()."""
    shelter = session.get(Shelter, shelter_id)
    if shelter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelter not found")
    authorize_shelter_zone_access(shelter, current_user)

    if payload.current_occupancy < 0 or payload.current_occupancy > shelter.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"current_occupancy must be between 0 and this shelter's capacity ({shelter.capacity})",
        )

    before = {"current_occupancy": shelter.current_occupancy}
    shelter.current_occupancy = payload.current_occupancy
    session.add(shelter)
    session.commit()
    session.refresh(shelter)

    audit_service.write_event(
        session, current_user.id, "shelter_occupancy_updated",
        "shelter", shelter.id, before=before, after={"current_occupancy": shelter.current_occupancy},
    )
    return shelter
