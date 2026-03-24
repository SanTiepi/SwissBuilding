"""BatiConnect — Contract Ops Summary schema."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ContractOpsSummary(BaseModel):
    building_id: UUID
    total_contracts: int
    active_contracts: int
    annual_cost_chf: float
    expiring_90d: int
    auto_renewal_count: int

    model_config = ConfigDict(from_attributes=True)
