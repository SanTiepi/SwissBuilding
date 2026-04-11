"""Pydantic v2 schemas for BuildingCase CRUD."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BuildingCaseCreate(BaseModel):
    case_type: str
    title: str
    description: str | None = None
    spatial_scope_ids: list[str] | None = None
    pollutant_scope: list[str] | None = None
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    intervention_id: uuid.UUID | None = None
    tender_id: uuid.UUID | None = None
    steps: list[dict] | None = None
    canton: str | None = None
    authority: str | None = None
    priority: str = "medium"


class BuildingCaseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    spatial_scope_ids: list[str] | None = None
    pollutant_scope: list[str] | None = None
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    steps: list[dict] | None = None
    canton: str | None = None
    authority: str | None = None
    priority: str | None = None


class BuildingCaseRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    organization_id: uuid.UUID
    created_by_id: uuid.UUID
    case_type: str
    title: str
    description: str | None
    state: str
    spatial_scope_ids: list[str] | None
    pollutant_scope: list[str] | None
    planned_start: datetime | None
    planned_end: datetime | None
    actual_start: datetime | None
    actual_end: datetime | None
    intervention_id: uuid.UUID | None
    tender_id: uuid.UUID | None
    steps: list[dict] | None
    canton: str | None
    authority: str | None
    priority: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class BuildingCaseAdvance(BaseModel):
    new_state: str


class BuildingCaseStepUpdate(BaseModel):
    step_name: str
    status: str = "completed"


class BuildingCaseLinkIntervention(BaseModel):
    intervention_id: uuid.UUID


class BuildingCaseLinkTender(BaseModel):
    tender_id: uuid.UUID
