from pydantic import BaseModel

from app.core.enums import ElevationTier


class ZoneResponse(BaseModel):
    id: int
    code: str
    name: str
    population: int
    elderly_pct: float
    population_density: int | None
    elevation_tier: ElevationTier
    elevation_m: int | None
    area_km2: float | None
    hospital_count: int
    flood_risk_base: float | None
    data_quality_json: dict
