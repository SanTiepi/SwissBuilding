"""BatiConnect — Lease Ops Summary schema."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LeaseOpsSummary(BaseModel):
    building_id: UUID
    total_leases: int
    active_leases: int
    monthly_rent_chf: float
    monthly_charges_chf: float
    expiring_90d: int
    disputed_count: int

    model_config = ConfigDict(from_attributes=True)
