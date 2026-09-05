from sqlmodel import SQLModel, Field


class Shelter(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    zone_id: int = Field(foreign_key="zone.id")
    capacity: int
    current_occupancy: int = Field(default=0)
    has_medical: bool = Field(default=False)