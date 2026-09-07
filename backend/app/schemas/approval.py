from pydantic import BaseModel


class ModifyRequest(BaseModel):
    modified_payload: dict
    reason: str | None = None


class RejectRequest(BaseModel):
    reason: str