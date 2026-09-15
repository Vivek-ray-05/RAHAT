from pydantic import BaseModel


class ScenarioResponse(BaseModel):
    id: int
    name: str
    scenario_type: str
    config_json: dict
