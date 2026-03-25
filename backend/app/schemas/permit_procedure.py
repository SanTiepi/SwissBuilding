"""BatiConnect — Permit Procedure schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProcedureCreate(BaseModel):
    procedure_type: str  # construction_permit | demolition_permit | suva_notification | cantonal_declaration | communal_authorization | other
    title: str
    description: str | None = None
    authority_name: str | None = None
    authority_type: str | None = None
    assigned_org_id: UUID | None = None
    assigned_user_id: UUID | None = None
    source_type: str | None = None
    confidence: str | None = None
    source_ref: str | None = None


class StepRead(BaseModel):
    id: UUID
    procedure_id: UUID
    step_type: str
    title: str
    description: str | None
    status: str
    assigned_org_id: UUID | None
    assigned_user_id: UUID | None
    due_date: date | None
    completed_at: datetime | None
    required_documents: list | None
    compliance_artefact_id: UUID | None
    notes: str | None
    step_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthorityRequestCreate(BaseModel):
    step_id: UUID | None = None
    request_type: str  # complement_request | information_request | clarification | correction
    from_authority: bool = True
    subject: str
    body: str
    response_due_date: date | None = None
    linked_document_ids: list | None = None


class AuthorityRequestRead(BaseModel):
    id: UUID
    procedure_id: UUID
    step_id: UUID | None
    request_type: str
    from_authority: bool
    subject: str
    body: str
    response_due_date: date | None
    status: str
    response_body: str | None
    responded_at: datetime | None
    linked_document_ids: list | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthorityRequestRespond(BaseModel):
    response_body: str


class ProcedureRead(BaseModel):
    id: UUID
    building_id: UUID
    procedure_type: str
    title: str
    description: str | None
    authority_name: str | None
    authority_type: str | None
    status: str
    submitted_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    expires_at: datetime | None
    reference_number: str | None
    assigned_org_id: UUID | None
    assigned_user_id: UUID | None
    source_type: str | None
    confidence: str | None
    source_ref: str | None
    created_at: datetime
    updated_at: datetime
    steps: list[StepRead] = []
    authority_requests: list[AuthorityRequestRead] = []

    model_config = ConfigDict(from_attributes=True)


class ProcedureListRead(BaseModel):
    id: UUID
    building_id: UUID
    procedure_type: str
    title: str
    status: str
    authority_name: str | None
    submitted_at: datetime | None
    reference_number: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcedureBlockerRead(BaseModel):
    procedure_id: UUID
    procedure_type: str
    title: str
    status: str
    blocker_reason: str
