from sqlmodel import SQLModel, Field, Column, JSON


class Scenario(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    scenario_type: str
    config_json: dict = Field(sa_column=Column(JSON, nullable=False))