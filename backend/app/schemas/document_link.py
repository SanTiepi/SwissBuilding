from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentLinkCreate(BaseModel):
    document_id: UUID
    entity_type: str  # building | diagnostic | intervention | lease | contract | insurance_policy | claim | compliance_artefact | evidence_pack
    entity_id: UUID
    link_type: str  # attachment | report | proof | reference | invoice | certificate


class DocumentLinkRead(BaseModel):
    id: UUID
    document_id: UUID
    entity_type: str
    entity_id: UUID
    link_type: str
    created_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentLinkListRead(BaseModel):
    id: UUID
    document_id: UUID
    entity_type: str
    entity_id: UUID
    link_type: str

    model_config = ConfigDict(from_attributes=True)
