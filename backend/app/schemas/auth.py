from pydantic import BaseModel

from app.core.roles import RoleEnum


class LoginRequest(BaseModel):
    email: str
    password: str
    role: RoleEnum


class OtpRequestRequest(BaseModel):
    phone: str


class OtpVerifyRequest(BaseModel):
    phone: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: RoleEnum
    zone_id: int | None = None