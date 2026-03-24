"""BatiConnect — Obligation schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ObligationCreate(BaseModel):
    building_id: UUID | None = None  # optional: path param takes precedence
    title: str
    description: str | None = None
    obligation_type: str  # regulatory_inspection | insurance_renewal | contract_renewal | maintenance | authority_submission | diagnostic_followup | lease_milestone | custom
    due_date: date
    recurrence: str | None = None  # monthly | quarterly | semi_annual | annual | biennial | five_yearly
    priority: str = "medium"  # low | medium | high | critical
    responsible_org_id: UUID | None = None
    responsible_user_id: UUID | None = None
    linked_entity_type: str | None = None  # contract | lease | intervention | diagnostic | insurance_policy
    linked_entity_id: UUID | None = None
    reminder_days_before: int = 30
    notes: str | None = None


class ObligationUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    obligation_type: str | None = None
    due_date: date | None = None
    recurrence: str | None = None
    priority: str | None = None
    responsible_org_id: UUID | None = None
    responsible_user_id: UUID | None = None
    linked_entity_type: str | None = None
    linked_entity_id: UUID | None = None
    reminder_days_before: int | None = None
    notes: str | None = None


class ObligationRead(BaseModel):
    id: UUID
    building_id: UUID
    title: str
    description: str | None
    obligation_type: str
    due_date: date
    recurrence: str | None
    status: str
    priority: str
    responsible_org_id: UUID | None
    responsible_user_id: UUID | None
    completed_at: datetime | None
    completed_by_user_id: UUID | None
    linked_entity_type: str | None
    linked_entity_id: UUID | None
    reminder_days_before: int
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ObligationComplete(BaseModel):
    notes: str | None = None
