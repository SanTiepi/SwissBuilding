"""BatiConnect - Memory Transfer schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MemoryTransferCreate(BaseModel):
    transfer_type: (
        str  # sale | refinance | management_change | work_cycle | insurance_renewal | regulatory_update | succession
    )
    building_id: uuid.UUID
    transfer_label: str | None = None
    from_org_id: uuid.UUID | None = None
    from_user_id: uuid.UUID | None = None
    to_org_id: uuid.UUID | None = None
    to_user_id: uuid.UUID | None = None


class MemoryTransferRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    transfer_type: str
    transfer_label: str
    from_org_id: uuid.UUID | None
    from_user_id: uuid.UUID | None
    to_org_id: uuid.UUID | None
    to_user_id: uuid.UUID | None
    status: str
    memory_snapshot_id: uuid.UUID | None
    transfer_package_hash: str | None
    memory_sections: dict | None
    sections_count: int
    documents_count: int
    engagements_count: int
    timeline_events_count: int
    integrity_verified: bool
    integrity_verified_at: datetime | None
    accepted_at: datetime | None
    accepted_by_id: uuid.UUID | None
    acceptance_comment: str | None
    contested_at: datetime | None
    contested_by_id: uuid.UUID | None
    contest_comment: str | None
    initiated_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class MemoryTransferList(BaseModel):
    items: list[MemoryTransferRead]
    count: int


class MemoryCompilation(BaseModel):
    """The compiled memory snapshot: sections with counts, integrity hash, completeness."""

    transfer_id: uuid.UUID
    building_id: uuid.UUID
    sections: dict  # Section name -> section data
    sections_count: int
    documents_count: int
    engagements_count: int
    timeline_events_count: int
    content_hash: str  # SHA-256
    completeness_score: float | None
    passport_grade: str | None
    overall_trust: float | None
    compiled_at: datetime


class TransferReadiness(BaseModel):
    """Can this building's memory be transferred? Missing sections, incomplete engagements, open gates."""

    building_id: uuid.UUID
    is_ready: bool
    readiness_score: float  # 0.0 - 1.0
    checks: list[dict]  # [{name, status, detail}]
    blockers: list[str]  # French descriptions of blocking issues
    warnings: list[str]  # French descriptions of non-blocking issues


class MemoryContinuityScore(BaseModel):
    """How complete is the building's memory across its lifecycle."""

    building_id: uuid.UUID
    total_transfers: int
    completed_transfers: int
    accepted_transfers: int
    contested_transfers: int
    continuity_score: float  # 0.0 - 1.0
    integrity_coverage: float  # % of transfers with verified hash
    gaps: list[dict]  # [{period, description}]
    lifecycle_coverage: float  # % of building life with active memory


class MemoryTransferAccept(BaseModel):
    comment: str | None = None


class MemoryTransferContest(BaseModel):
    comment: str
