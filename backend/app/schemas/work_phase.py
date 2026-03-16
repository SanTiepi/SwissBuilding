"""Pydantic v2 schemas for the Work Phase service."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkPhase(BaseModel):
    """A single work phase in the renovation plan."""

    phase_id: str
    phase_name: str
    phase_type: str  # preparation | containment | removal | decontamination | restoration | verification
    duration_days: int
    dependencies: list[str] = []
    cfst_category: str  # minor | medium | major
    required_equipment: list[str] = []
    safety_measures: list[str] = []
    pollutant: str | None = None
    order: int = 0

    model_config = ConfigDict(from_attributes=True)


class WorkPhasePlan(BaseModel):
    """Full work phase plan for a building renovation."""

    building_id: UUID
    phases: list[WorkPhase]
    total_phases: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimelinePhase(BaseModel):
    """A phase with start/end dates for Gantt-style rendering."""

    phase_id: str
    phase_name: str
    phase_type: str
    start_date: date
    end_date: date
    duration_days: int
    is_critical_path: bool = False
    parallel_possible: bool = False

    model_config = ConfigDict(from_attributes=True)


class PhaseTimeline(BaseModel):
    """Gantt-style timeline with critical path information."""

    building_id: UUID
    total_duration_days: int
    start_date: date
    end_date: date
    phases: list[TimelinePhase]
    critical_path: list[str]
    parallel_possible: list[str]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PhaseRequirements(BaseModel):
    """Detailed requirements for a specific phase type."""

    building_id: UUID
    phase_type: str
    regulatory_references: list[str] = []
    qualified_personnel: list[str] = []
    permits_needed: list[str] = []
    waste_management_plan: str | None = None
    air_monitoring_required: bool = False
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CfstCategoryCount(BaseModel):
    """Count of buildings per CFST category."""

    category: str
    count: int

    model_config = ConfigDict(from_attributes=True)


class PortfolioWorkOverview(BaseModel):
    """Organization-wide work overview."""

    organization_id: UUID
    buildings_with_planned_work: int
    total_phases_pending: int
    estimated_total_duration_days: int
    buildings_by_cfst_category: list[CfstCategoryCount]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
