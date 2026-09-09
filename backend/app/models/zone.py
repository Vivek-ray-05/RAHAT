from sqlmodel import SQLModel , Field, Column, JSON

from app.core.enums import ElevationTier

class Zone ( SQLModel , table = True):
    id: int | None = Field(default= None , primary_key=True)
    name: str
    elevation_tier: ElevationTier
    code: str= Field(index= True, unique= True)
    population: int
    elderly_pct: float
    population_density: int | None = Field(default=None)
    elevation_m: int | None = Field(default=None)
    area_km2: float | None = Field(default=None)
    hospital_count: int = Field(default=0)
    flood_risk_base: float | None = Field(default=None)
    # Per-field provenance: {"population": {"quality": "estimated"|"real"|"derived"|"unavailable", "note": "..."}, ...}
    # -- so a coordinator can see which numbers are real (SRTM elevation,
    # OSM hospital counts) versus estimated (building-derived population,
    # a single citywide elderly_pct) until a real institutional data
    # partnership replaces the estimates.
    data_quality_json: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))

