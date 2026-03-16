from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrganizationCreate(BaseModel):
    name: str
    type: str  # diagnostic_lab, architecture_firm, property_management, authority, contractor
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    canton: str | None = None
    phone: str | None = None
    email: str | None = None
    suva_recognized: bool = False
    fach_approved: bool = False


class OrganizationUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    canton: str | None = None
    phone: str | None = None
    email: str | None = None
    suva_recognized: bool | None = None
    fach_approved: bool | None = None


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    type: str
    address: str | None
    postal_code: str | None
    city: str | None
    canton: str | None
    phone: str | None
    email: str | None
    suva_recognized: bool
    fach_approved: bool
    created_at: datetime
    member_count: int = 0

    model_config = ConfigDict(from_attributes=True)
