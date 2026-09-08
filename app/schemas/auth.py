"""DTOs auth — validation des entrées/sorties."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.auth.models import PlatformConnectionStatus


# ── User ──
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def truncate_password(cls, v: str) -> str:
        return v[:72]


class UserLogin(BaseModel):
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def truncate_password(cls, v: str) -> str:
        return v[:72]


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── JWT ──
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Platform Connection ──
class PlatformConnectRequest(BaseModel):
    platform_name: str = Field(min_length=2, max_length=100)
    api_key: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)


class PlatformStatusResponse(BaseModel):
    platform_name: str
    status: PlatformConnectionStatus
    last_health_check: Optional[datetime] = None

    model_config = {"from_attributes": True}
