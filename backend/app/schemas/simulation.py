"""SwissBuildingOS - Intervention Simulation Schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class SimulationInput(BaseModel):
    """A single hypothetical intervention to simulate."""

    intervention_type: str
    target_pollutant: str | None = None
    target_zone_id: uuid.UUID | None = None
    estimated_cost: float | None = None


class SimulationRequest(BaseModel):
    """Request body wrapping a list of hypothetical interventions."""

    interventions: list[SimulationInput]


class SimulationStateSnapshot(BaseModel):
    """Snapshot of building state metrics."""

    passport_grade: str
    trust_score: float
    completeness_score: float
    blocker_count: int
    open_actions_count: int

    model_config = ConfigDict(from_attributes=True)


class SimulationImpactSummary(BaseModel):
    """Impact summary comparing current vs projected state."""

    actions_resolved: int
    readiness_improvement: str
    trust_delta: float
    completeness_delta: float
    grade_change: str | None
    risk_reduction: dict[str, str]
    estimated_total_cost: float | None


class SimulationResult(BaseModel):
    """Full result of an intervention simulation."""

    current_state: SimulationStateSnapshot
    projected_state: SimulationStateSnapshot
    impact_summary: SimulationImpactSummary
    recommendations: list[str]
