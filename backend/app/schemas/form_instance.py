import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FormTemplateRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    form_type: str
    jurisdiction_id: uuid.UUID | None
    canton: str | None
    fields_schema: list[dict] | None
    required_attachments: list[str] | None
    version: str | None
    source_url: str | None
    active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ApplicableFormTemplate(BaseModel):
    """A form template with its applicability reason."""

    template: FormTemplateRead
    reason: str


class FormInstanceCreate(BaseModel):
    intervention_id: uuid.UUID | None = None


class FormInstanceUpdate(BaseModel):
    field_values: dict[str, dict] | None = None
    attached_document_ids: list[str] | None = None


class FormInstanceRead(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    building_id: uuid.UUID
    organization_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    intervention_id: uuid.UUID | None
    status: str
    field_values: dict[str, dict] | None
    attached_document_ids: list[str] | None
    missing_fields: list[str] | None
    missing_attachments: list[str] | None
    prefill_confidence: float | None
    submitted_at: datetime | None
    submission_reference: str | None
    complement_details: str | None
    acknowledged_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    # Joined template info for display
    template_name: str | None = None
    template_form_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FormSubmitRequest(BaseModel):
    submission_reference: str | None = None


class FormComplementRequest(BaseModel):
    complement_details: str = Field(..., min_length=1)
