"""Pydantic v2 schemas for the Renovation Sequencer service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PhaseDependency(BaseModel):
    """A dependency between two renovation phases."""

    phase_id: str
    depends_on: str
    reason: str

    model_config = ConfigDict(from_attributes=True)


class RenovationPhase(BaseModel):
    """A single phase in the renovation sequence."""

    phase_id: str
    order: int
    title: str
    description: str
    pollutant: str | None = None
    zone: str | None = None
    priority: str  # critical | high | medium | low
    estimated_duration_weeks: int
    depends_on: list[str] = []
    can_parallel: bool = False

    model_config = ConfigDict(from_attributes=True)


class RenovationSequence(BaseModel):
    """Optimal ordered sequence of renovation phases for a building."""

    building_id: UUID
    phases: list[RenovationPhase]
    dependencies: list[PhaseDependency]
    total_phases: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GanttPhase(BaseModel):
    """A phase with timeline information for Gantt chart rendering."""

    phase_id: str
    title: str
    start_week: int
    end_week: int
    duration_weeks: int
    depends_on: list[str] = []
    is_critical_path: bool = False
    pollutant: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RenovationTimeline(BaseModel):
    """Gantt-chart-ready renovation timeline."""

    building_id: UUID
    phases: list[GanttPhase]
    critical_path: list[str]
    total_duration_weeks: int
    lab_analysis_buffer_weeks: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParallelTrack(BaseModel):
    """A group of works that can run simultaneously."""

    track_id: str
    phases: list[str]
    reason: str
    time_savings_weeks: int

    model_config = ConfigDict(from_attributes=True)


class ParallelTracksResult(BaseModel):
    """Parallel work opportunities for a building renovation."""

    building_id: UUID
    tracks: list[ParallelTrack]
    total_potential_savings_weeks: int
    sequential_duration_weeks: int
    optimized_duration_weeks: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RenovationBlocker(BaseModel):
    """Something preventing renovation start."""

    blocker_id: str
    category: str  # missing_diagnostic | pending_approval | compliance_gap | missing_contractor
    title: str
    description: str
    severity: str  # critical | high | medium
    resolution_path: str
    estimated_resolution_weeks: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ReadinessBlockersResult(BaseModel):
    """All blockers preventing renovation start."""

    building_id: UUID
    blockers: list[RenovationBlocker]
    total_blockers: int
    critical_blockers: int
    is_ready: bool
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
