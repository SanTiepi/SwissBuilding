"""BatiConnect — Commitment & Caveat schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Commitment
# ---------------------------------------------------------------------------


class CommitmentCreate(BaseModel):
    commitment_type: str  # guarantee | warranty | undertaking | promise | obligation | condition | reservation
    committed_by_type: str  # contractor | owner | authority | insurer | seller | buyer
    committed_by_name: str
    committed_by_id: UUID | None = None
    subject: str
    description: str | None = None
    case_id: UUID | None = None
    organization_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_months: int | None = None
    source_document_id: UUID | None = None
    source_extraction_id: UUID | None = None


class CommitmentRead(BaseModel):
    id: UUID
    building_id: UUID
    case_id: UUID | None
    organization_id: UUID | None
    commitment_type: str
    committed_by_type: str
    committed_by_name: str
    committed_by_id: UUID | None
    subject: str
    description: str | None
    start_date: date | None
    end_date: date | None
    duration_months: int | None
    status: str
    source_document_id: UUID | None
    source_extraction_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Caveat
# ---------------------------------------------------------------------------


class CaveatCreate(BaseModel):
    caveat_type: str
    subject: str
    description: str | None = None
    severity: str = "info"  # info | warning | critical
    case_id: UUID | None = None
    applies_to_pack_types: list[str] | None = None
    applies_to_audiences: list[str] | None = None
    source_type: str = "manual"
    source_id: UUID | None = None


class CaveatRead(BaseModel):
    id: UUID
    building_id: UUID
    case_id: UUID | None
    caveat_type: str
    subject: str
    description: str | None
    severity: str
    applies_to_pack_types: list[str] | None
    applies_to_audiences: list[str] | None
    source_type: str
    source_id: UUID | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class ExpiringCommitmentRead(CommitmentRead):
    """Commitment with days_until_expiry for the expiring endpoint."""

    days_until_expiry: int | None = None


class CommitmentCaveatSummary(BaseModel):
    building_id: UUID
    active_commitments: int
    expiring_soon: int
    expired_commitments: int
    fulfilled_commitments: int
    breached_commitments: int
    active_caveats: int
    caveats_by_severity: dict[str, int]
    caveats_by_type: dict[str, int]


class AutoGenerateCaveatsResult(BaseModel):
    generated: int
    caveats: list[CaveatRead]
