"""
BatiConnect — Value Ledger Schemas

Pydantic v2 schemas for the cumulative value accumulation system.
Tracks every unit of value BatiConnect delivers to an organization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ValueTrend(BaseModel):
    last_30_days_value: float
    previous_30_days_value: float
    direction: Literal["growing", "stable", "declining"]


class ValueLedger(BaseModel):
    organization_id: UUID
    sources_unified_total: int
    contradictions_resolved_total: int
    proof_chains_created_total: int
    documents_secured_total: int
    decisions_backed_total: int
    hours_saved_estimate: float
    value_chf_estimate: float
    days_active: int
    value_per_day: float
    trend: Literal["growing", "stable", "declining"]
    trend_detail: ValueTrend


class ValueEvent(BaseModel):
    event_type: str
    building_id: UUID | None = None
    delta_description: str
    created_at: datetime


class IndispensabilitySection(BaseModel):
    title: str
    narrative: str
    metrics: dict[str, float | int | str]


class IndispensabilityExport(BaseModel):
    title: str
    generated_at: datetime
    generated_by: str
    executive_summary: str
    fragmentation_section: IndispensabilitySection
    defensibility_section: IndispensabilitySection
    counterfactual_section: IndispensabilitySection
    value_ledger_section: IndispensabilitySection
    recommendation: str


class PortfolioIndispensabilityExport(BaseModel):
    title: str
    generated_at: datetime
    generated_by: str
    executive_summary: str
    buildings_count: int
    fragmentation_section: IndispensabilitySection
    defensibility_section: IndispensabilitySection
    counterfactual_section: IndispensabilitySection
    value_ledger_section: IndispensabilitySection
    recommendation: str
