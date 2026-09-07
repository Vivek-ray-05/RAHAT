from sqlmodel import SQLModel, Field


class Road(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    from_zone_id: int = Field(foreign_key="zone.id")
    to_zone_id: int = Field(foreign_key="zone.id")
    capacity: int | None = Field(default=None)
    distance_km: float | None = Field(default=None)
    is_blocked: bool = Field(default=False)
    blocked_by_user_id: int | None = Field(default=None, foreign_key="user.id")