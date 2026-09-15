from pydantic import BaseModel


class ShelterResponse(BaseModel):
    id: int
    code: str
    name: str
    zone_id: int
    capacity: int
    current_occupancy: int
    has_medical: bool
    lat: float | None
    lon: float | None


class UpdateShelterOccupancyRequest(BaseModel):
    current_occupancy: int


class NearestShelterResponse(BaseModel):
    source: str
    shelter: ShelterResponse
    distance_km: float | None
