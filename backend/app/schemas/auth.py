from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    first_name: str
    last_name: str
    role: str = "owner"  # Only owner can self-register
    language: str = "fr"


class ProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    language: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


# Resolve forward reference
from app.schemas.user import UserRead  # noqa: E402

TokenResponse.model_rebuild()
