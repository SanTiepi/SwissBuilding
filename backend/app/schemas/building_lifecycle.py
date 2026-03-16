"""Pydantic v2 schemas for Building Lifecycle service."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LifecyclePhaseResponse(BaseModel):
    """Current lifecycle phase of a building."""

    building_id: UUID
    phase: str  # unknown|assessed|diagnosed|planned|in_remediation|cleared|monitored
    phase_label: str
    entered_at: datetime | None = None
    trigger: str | None = None
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PhaseTransition(BaseModel):
    """A single phase transition in the lifecycle timeline."""

    phase: str
    entered_at: datetime
    exited_at: datetime | None = None
    duration_days: int | None = None
    trigger: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LifecycleTimelineResponse(BaseModel):
    """Full lifecycle timeline for a building."""

    building_id: UUID
    current_phase: str
    transitions: list[PhaseTransition]
    total_days_tracked: int
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LifecycleBlocker(BaseModel):
    """A condition that must be met to advance phase."""

    condition: str
    met: bool
    details: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LifecyclePredictionResponse(BaseModel):
    """Prediction for next lifecycle phase."""

    building_id: UUID
    current_phase: str
    next_phase: str | None = None
    conditions: list[LifecycleBlocker]
    conditions_met: int
    conditions_total: int
    estimated_days_to_transition: int | None = None
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PhaseDistributionEntry(BaseModel):
    """Count of buildings in a single lifecycle phase."""

    phase: str
    phase_label: str
    count: int
    avg_days_in_phase: float | None = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioLifecycleDistributionResponse(BaseModel):
    """Portfolio-level lifecycle distribution."""

    organization_id: UUID
    total_buildings: int
    distribution: list[PhaseDistributionEntry]
    bottleneck_phase: str | None = None
    bottleneck_count: int = 0
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
