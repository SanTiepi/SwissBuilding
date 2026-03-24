"""BatiConnect — Workspace membership schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class AccessScope(BaseModel):
    """Fine-grained access scope for a workspace membership."""

    documents: bool = True
    diagnostics: bool = True
    financial: bool = False
    interventions: bool = False
    contracts: bool = False
    leases: bool = False
    ownership: bool = False


class WorkspaceMembershipCreate(BaseModel):
    organization_id: UUID | None = None
    user_id: UUID | None = None
    role: str  # owner | manager | diagnostician | architect | authority | contractor | viewer
    access_scope: AccessScope | None = None
    expires_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_org_or_user(self) -> WorkspaceMembershipCreate:
        if self.organization_id is None and self.user_id is None:
            msg = "Either organization_id or user_id must be provided"
            raise ValueError(msg)
        return self


class WorkspaceMembershipUpdate(BaseModel):
    role: str | None = None
    access_scope: AccessScope | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None
    notes: str | None = None


class WorkspaceMembershipRead(BaseModel):
    id: UUID
    building_id: UUID
    organization_id: UUID | None
    user_id: UUID | None
    role: str
    access_scope: dict | None
    granted_by_user_id: UUID
    granted_at: datetime
    expires_at: datetime | None
    is_active: bool
    notes: str | None

    # Enriched display fields
    organization_name: str | None = None
    user_display_name: str | None = None
    granted_by_display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
