"""Pydantic schemas for audience-bounded sharing links."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SharedLinkCreate(BaseModel):
    resource_type: str  # building, diagnostic, passport, authority_pack
    resource_id: uuid.UUID
    audience_type: str  # buyer, insurer, lender, authority, contractor, tenant
    audience_email: str | None = None
    expires_in_days: int = 30
    max_views: int | None = None
    allowed_sections: list[str] | None = None


class SharedLinkRead(BaseModel):
    id: uuid.UUID
    token: str
    resource_type: str
    resource_id: uuid.UUID
    created_by: uuid.UUID
    organization_id: uuid.UUID | None
    audience_type: str
    audience_email: str | None
    expires_at: datetime
    max_views: int | None
    view_count: int
    allowed_sections: list[str] | None
    is_active: bool
    created_at: datetime
    last_accessed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SharedLinkValidation(BaseModel):
    is_valid: bool
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    allowed_sections: list[str] | None = None
    audience_type: str | None = None


class SharedLinkList(BaseModel):
    items: list[SharedLinkRead]
    count: int


class SharedPassportResponse(BaseModel):
    """Public passport data returned via a valid shared link."""

    building_address: str
    building_city: str
    building_canton: str
    building_postal_code: str
    passport: dict
    shared_by_org: str | None = None
    expires_at: datetime
    audience_type: str
