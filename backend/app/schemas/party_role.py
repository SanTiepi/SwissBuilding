from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PartyRoleAssignmentCreate(BaseModel):
    party_type: str  # contact | user | organization
    party_id: UUID
    entity_type: str  # building | unit | portfolio | lease | contract | intervention | diagnostic
    entity_id: UUID
    role: str  # legal_owner | co_owner | tenant | manager | insurer | contractor | notary | trustee | syndic | architect | diagnostician | reviewer
    share_pct: float | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    is_primary: bool = False
    notes: str | None = None


class PartyRoleAssignmentUpdate(BaseModel):
    role: str | None = None
    share_pct: float | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    is_primary: bool | None = None
    notes: str | None = None


class PartyRoleAssignmentRead(BaseModel):
    id: UUID
    party_type: str
    party_id: UUID
    entity_type: str
    entity_id: UUID
    role: str
    share_pct: float | None
    valid_from: date | None
    valid_until: date | None
    is_primary: bool
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartyRoleAssignmentListRead(BaseModel):
    id: UUID
    party_type: str
    party_id: UUID
    entity_type: str
    entity_id: UUID
    role: str
    share_pct: float | None
    is_primary: bool
    valid_from: date | None
    valid_until: date | None

    model_config = ConfigDict(from_attributes=True)
