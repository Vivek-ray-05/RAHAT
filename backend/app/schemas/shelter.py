from pydantic import BaseModel


class ShelterResponse(BaseModel):
    id: int
    code: str
    name: str
    zone_id: int
    capacity: int
    current_occupancy: int
    has_medical: bool
