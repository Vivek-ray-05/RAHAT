from datetime import datetime , timezone 

from sqlmodel import SQLModel , Field

from app.core.roles import RoleEnum

class User ( SQLModel , table = True):
    id: int | None = Field(default= None , primary_key=True)
    phone: str | None = Field( default= None , index = True)
    email: str | None = Field( default= None , index = True)
    name: str 
    role: RoleEnum
    hashed_secret: str | None = Field(default=None)
    zone_id: int | None = Field(default=None, foreign_key="zone.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    