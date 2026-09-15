"""
Directions for a citizen to the nearest reachable shelter. Two
sources, in priority order: an official evacuation recommendation
already assigned to their zone (if one exists), or -- if there's no
active recommendation -- the nearest shelter with room, by real
straight-line distance between real coordinates. Not turn-by-turn
street routing (the mobility engine's own route data is zone-graph
abstract, same simplification as the rest of this project's route
handling -- see RouteOption.path_json's "zone:X"/"shelter:Y" tokens).
"""
import math

from sqlmodel import Session, select

from app.core.enums import RecommendationStatus
from app.models.recommendation import Recommendation
from app.models.shelter import Shelter
from app.models.zone import Zone

_ACTIVE_STATUSES = (
    RecommendationStatus.PENDING_REVIEW,
    RecommendationStatus.APPROVED,
    RecommendationStatus.MODIFIED,
    RecommendationStatus.EXECUTED,
)


class NoShelterAvailableError(Exception):
    pass


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_shelter(session: Session, zone_id: int) -> dict:
    zone = session.get(Zone, zone_id)
    if zone is None:
        raise NoShelterAvailableError(f"No zone with id {zone_id}")

    official = session.exec(
        select(Recommendation)
        .where(
            Recommendation.zone_id == zone_id,
            Recommendation.status.in_(_ACTIVE_STATUSES),
        )
        .order_by(Recommendation.created_at.desc())
    ).first()
    if official is not None:
        assigned_shelter_id = official.payload_json.get("assigned_shelter_id")
        if assigned_shelter_id is not None:
            shelter = session.get(Shelter, assigned_shelter_id)
            if shelter is not None:
                return {
                    "source": "official_recommendation",
                    "shelter": shelter,
                    "distance_km": (
                        _haversine_km(zone.center_lat, zone.center_lon, shelter.lat, shelter.lon)
                        if zone.center_lat is not None and shelter.lat is not None
                        else None
                    ),
                }

    if zone.center_lat is None or zone.center_lon is None:
        raise NoShelterAvailableError("This zone has no coordinates yet -- re-run the seed script")

    available = [s for s in session.exec(select(Shelter)).all() if s.current_occupancy < s.capacity and s.lat is not None]
    if not available:
        raise NoShelterAvailableError("No shelter currently has available capacity")

    nearest = min(available, key=lambda s: _haversine_km(zone.center_lat, zone.center_lon, s.lat, s.lon))
    return {
        "source": "nearest_available",
        "shelter": nearest,
        "distance_km": _haversine_km(zone.center_lat, zone.center_lon, nearest.lat, nearest.lon),
    }
