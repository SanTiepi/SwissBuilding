"""BatiConnect — Schemas for Demo Scenarios, Pilot Scorecards, and Case Study Templates."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---- Demo Scenario ----


class DemoRunbookStepRead(BaseModel):
    id: UUID
    scenario_id: UUID
    step_order: int
    title: str
    description: str | None
    expected_ui_state: str | None
    fallback_notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DemoScenarioRead(BaseModel):
    id: UUID
    scenario_code: str
    title: str
    persona_target: str
    starting_state_description: str
    reveal_surfaces: list[str]
    proof_moment: str | None
    action_moment: str | None
    seed_key: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DemoScenarioWithRunbook(DemoScenarioRead):
    runbook_steps: list[DemoRunbookStepRead] = []


# ---- Pilot Scorecard ----


class PilotMetricCreate(BaseModel):
    dimension: str
    target_value: float | None = None
    current_value: float | None = None
    evidence_source: str | None = None
    notes: str | None = None
    measured_at: datetime


class PilotMetricRead(BaseModel):
    id: UUID
    scorecard_id: UUID
    dimension: str
    target_value: float | None
    current_value: float | None
    evidence_source: str | None
    notes: str | None
    measured_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PilotScorecardRead(BaseModel):
    id: UUID
    pilot_name: str
    pilot_code: str
    status: str
    start_date: date
    end_date: date | None
    target_buildings: int | None
    target_users: int | None
    exit_state: str | None
    exit_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PilotScorecardWithMetrics(PilotScorecardRead):
    metrics: list[PilotMetricRead] = []


# ---- Case Study Template ----


class CaseStudyTemplateRead(BaseModel):
    id: UUID
    template_code: str
    title: str
    persona_target: str
    workflow_type: str
    narrative_structure: dict
    evidence_requirements: list[dict]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
