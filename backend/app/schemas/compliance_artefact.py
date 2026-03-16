import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ComplianceArtefactCreate(BaseModel):
    artefact_type: str
    title: str
    description: str | None = None
    reference_number: str | None = None
    diagnostic_id: uuid.UUID | None = None
    intervention_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    authority_name: str | None = None
    authority_type: str | None = None
    expires_at: datetime | None = None
    legal_basis: str | None = None
    metadata_json: dict | None = None


class ComplianceArtefactUpdate(BaseModel):
    artefact_type: str | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    reference_number: str | None = None
    diagnostic_id: uuid.UUID | None = None
    intervention_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    authority_name: str | None = None
    authority_type: str | None = None
    expires_at: datetime | None = None
    legal_basis: str | None = None
    metadata_json: dict | None = None


class ComplianceArtefactRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    artefact_type: str
    status: str
    title: str
    description: str | None
    reference_number: str | None
    diagnostic_id: uuid.UUID | None
    intervention_id: uuid.UUID | None
    document_id: uuid.UUID | None
    authority_name: str | None
    authority_type: str | None
    submitted_at: datetime | None
    acknowledged_at: datetime | None
    expires_at: datetime | None
    legal_basis: str | None
    metadata_json: dict | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
