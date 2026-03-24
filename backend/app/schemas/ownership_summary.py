"""BatiConnect — Ownership Ops Summary schema."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OwnershipOpsSummary(BaseModel):
    building_id: UUID
    total_records: int
    active_records: int
    total_share_pct: float
    owner_count: int
    co_ownership: bool

    model_config = ConfigDict(from_attributes=True)
