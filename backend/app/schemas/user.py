from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    first_name: str
    last_name: str
    role: str
    organization_id: UUID | None = None
    language: str = "fr"


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None
    organization_id: UUID | None = None
    language: str | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    organization_id: UUID | None
    language: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
