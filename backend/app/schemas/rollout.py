"""Adoption Loops — Rollout schemas (grants, audit, tenant boundaries)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# --- TenantBoundary ---


class TenantBoundaryCreate(BaseModel):
    organization_id: UUID
    boundary_name: str
    allowed_building_ids: list[str] | None = None
    max_users: int | None = None
    max_external_viewers: int | None = None


class TenantBoundaryRead(BaseModel):
    id: UUID
    organization_id: UUID
    boundary_name: str
    allowed_building_ids: list[str] | None
    max_users: int | None
    max_external_viewers: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- DelegatedAccessGrant ---


class GrantCreate(BaseModel):
    granted_to_org_id: UUID | None = None
    granted_to_email: str | None = None
    grant_type: str  # viewer | contributor | temporary_admin | support
    scope: dict | None = None
    expires_at: datetime | None = None
    notes: str | None = None


class GrantRead(BaseModel):
    id: UUID
    building_id: UUID
    granted_to_org_id: UUID | None
    granted_to_email: str | None
    grant_type: str
    scope: dict | None
    granted_by_user_id: UUID
    granted_at: datetime
    expires_at: datetime | None
    is_active: bool
    revoked_at: datetime | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


# --- PrivilegedAccessEvent ---


class PrivilegedAccessEventRead(BaseModel):
    id: UUID
    user_id: UUID
    building_id: UUID | None
    action_type: str
    target_entity_type: str | None
    target_entity_id: UUID | None
    details: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
