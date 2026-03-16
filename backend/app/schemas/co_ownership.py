"""Pydantic v2 schemas for co-ownership governance (PPE)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CoOwner(BaseModel):
    """A co-owner in a PPE building."""

    owner_id: str
    name: str
    share_percentage: float
    contact_email: str | None = None
    role: str  # president / member / tenant_representative / property_manager
    voting_rights: bool

    model_config = ConfigDict(from_attributes=True)


class BuildingCoOwnershipInfo(BaseModel):
    """Co-ownership structure for a building."""

    building_id: UUID
    ownership_type: str  # ppe / sole_owner / cooperative
    co_owners: list[CoOwner]
    total_shares: float
    decision_quorum_pct: float
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CostAllocation(BaseModel):
    """Cost allocation for a single co-owner."""

    owner_id: str
    owner_name: str
    share_percentage: float
    allocated_amount: float
    status: str  # pending / invoiced / paid

    model_config = ConfigDict(from_attributes=True)


class RemediationCostSplit(BaseModel):
    """Remediation cost split across co-owners."""

    building_id: UUID
    total_remediation_cost: float
    allocations: list[CostAllocation]
    allocation_method: str  # by_share / equal / by_affected_area
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DecisionItem(BaseModel):
    """A decision item in the co-ownership decision log."""

    decision_id: str
    title: str
    description: str
    decision_type: str  # remediation_approval / contractor_selection / budget_allocation / timeline_change
    status: str  # proposed / voted / approved / rejected / deferred
    votes_for: int
    votes_against: int
    votes_abstain: int
    quorum_reached: bool
    decided_date: date | None = None

    model_config = ConfigDict(from_attributes=True)


class BuildingDecisionLog(BaseModel):
    """Decision log for a building's co-ownership."""

    building_id: UUID
    decisions: list[DecisionItem]
    total_decisions: int
    pending_decisions: int
    approval_rate: float
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioCoOwnershipSummary(BaseModel):
    """Portfolio-level co-ownership summary for an organization."""

    organization_id: UUID
    total_ppe_buildings: int
    total_sole_owner_buildings: int
    buildings_with_pending_decisions: int
    average_decision_approval_rate: float
    total_pending_cost_allocations: float
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
