"""Pydantic v2 schemas for Procedure OS (templates + instances)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# ProcedureTemplate
# ---------------------------------------------------------------------------


class ProcedureTemplateRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    procedure_type: str
    scope: str
    canton: str | None
    jurisdiction_id: uuid.UUID | None
    steps: list[dict] | None
    required_artifacts: list[dict] | None
    authority_name: str | None
    authority_route: str | None
    filing_channel: str | None
    form_template_ids: list[str] | None
    applicable_work_families: list[str] | None
    typical_duration_days: int | None
    advance_notice_days: int | None
    legal_basis: str | None
    source_url: str | None
    version: str | None
    active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# ProcedureInstance
# ---------------------------------------------------------------------------


class ProcedureInstanceCreate(BaseModel):
    template_id: uuid.UUID
    case_id: uuid.UUID | None = None


class ProcedureInstanceRead(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    building_id: uuid.UUID
    case_id: uuid.UUID | None
    organization_id: uuid.UUID
    created_by_id: uuid.UUID
    status: str
    current_step: str | None
    completed_steps: list[dict] | None
    collected_artifacts: list[str] | None
    missing_artifacts: list[dict] | None
    submitted_at: datetime | None
    submission_reference: str | None
    authority_response: str | None
    complement_requested_at: datetime | None
    complement_details: str | None
    resolved_at: datetime | None
    resolution: str | None
    blockers: list[dict] | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ProcedureAdvanceStep(BaseModel):
    step_name: str


class ProcedureSubmit(BaseModel):
    submission_reference: str | None = None


class ProcedureComplement(BaseModel):
    complement_details: str


class ProcedureResolve(BaseModel):
    resolution: str  # approved | rejected | expired


class ProcedureBlockerRead(BaseModel):
    description: str
    severity: str
    since: str | None = None


class ApplicableProcedureRead(BaseModel):
    """A procedure template that applies to a given building/work context."""

    template: ProcedureTemplateRead
    reason: str  # why it applies

    model_config = ConfigDict(from_attributes=True)
