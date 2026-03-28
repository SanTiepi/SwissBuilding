"""Pydantic v2 schemas for CounterfactualScenario CRUD."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ScenarioCreate(BaseModel):
    scenario_type: str
    title: str
    description: str | None = None
    case_id: uuid.UUID | None = None
    assumptions: dict | None = None


class ScenarioRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    case_id: uuid.UUID | None
    organization_id: uuid.UUID
    created_by_id: uuid.UUID

    scenario_type: str
    title: str
    description: str | None
    assumptions: dict | None

    projected_grade: str | None
    projected_completeness: float | None
    projected_readiness: dict | None
    projected_cost_chf: float | None
    projected_risk_level: str | None
    projected_timeline_months: int | None

    baseline_grade: str | None
    baseline_cost_chf: float | None

    advantages: list[str] | None
    disadvantages: list[str] | None
    risk_tradeoffs: list[dict] | None

    optimal_window_start: date | None
    optimal_window_end: date | None
    window_reason: str | None

    status: str
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ScenarioCompareRequest(BaseModel):
    scenario_ids: list[uuid.UUID]


class ScenarioCompareItem(BaseModel):
    """One scenario in a comparison matrix."""

    id: uuid.UUID
    title: str
    scenario_type: str
    projected_grade: str | None
    projected_completeness: float | None
    projected_cost_chf: float | None
    projected_risk_level: str | None
    projected_timeline_months: int | None
    advantages: list[str] | None
    disadvantages: list[str] | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class ScenarioCompareResponse(BaseModel):
    building_id: uuid.UUID
    baseline_grade: str | None
    baseline_cost_chf: float | None
    scenarios: list[ScenarioCompareItem]
    recommendation: str | None = None


class ScenarioEvaluateResponse(BaseModel):
    """Response after evaluating a scenario — returns the full scenario read."""

    scenario: ScenarioRead
    evaluation_summary: str
