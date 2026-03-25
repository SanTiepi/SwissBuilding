"""BatiConnect — ROI Report schemas for workflow-event grounded ROI calculations."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ROIBreakdown(BaseModel):
    label: str
    value: float
    unit: str  # hours | count | days
    evidence_count: int  # how many workflow events contributed


class ROIReport(BaseModel):
    building_id: UUID
    time_saved_hours: float
    rework_avoided: int
    blocker_days_saved: float
    pack_reuse_count: int
    breakdown: list[ROIBreakdown]
    evidence_sources: list[str]  # table names that contributed data
