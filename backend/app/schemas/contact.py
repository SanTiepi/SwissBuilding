from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ContactCreate(BaseModel):
    organization_id: UUID | None = None
    contact_type: str  # person | company | authority | notary | insurer | syndic | supplier
    name: str
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    canton: str | None = None
    external_ref: str | None = None
    linked_user_id: UUID | None = None
    notes: str | None = None
    is_active: bool = True
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class ContactUpdate(BaseModel):
    contact_type: str | None = None
    name: str | None = None
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    canton: str | None = None
    external_ref: str | None = None
    linked_user_id: UUID | None = None
    notes: str | None = None
    is_active: bool | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class ContactRead(BaseModel):
    id: UUID
    organization_id: UUID | None
    contact_type: str
    name: str
    company_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    postal_code: str | None
    city: str | None
    canton: str | None
    external_ref: str | None
    linked_user_id: UUID | None
    notes: str | None
    is_active: bool
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactListRead(BaseModel):
    id: UUID
    contact_type: str
    name: str
    company_name: str | None
    email: str | None
    phone: str | None
    city: str | None
    canton: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
