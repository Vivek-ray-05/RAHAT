from sqlmodel import SQLModel, Field, Column, JSON

from app.core.enums import RouteStatus


class RouteOption(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    simulation_tick_id: int = Field(foreign_key="simulationtick.id")
    from_zone_id: int = Field(foreign_key="zone.id")
    to_shelter_id: int = Field(foreign_key="shelter.id")
    path_json: dict = Field(sa_column=Column(JSON, nullable=False))
    eta: float
    status: RouteStatus