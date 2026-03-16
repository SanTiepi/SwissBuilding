from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExportJobCreate(BaseModel):
    type: str  # building_dossier, handoff_pack, audit_pack
    building_id: UUID | None = None
    organization_id: UUID | None = None


class ExportJobRead(BaseModel):
    id: UUID
    type: str
    building_id: UUID | None
    organization_id: UUID | None
    status: str
    requested_by: UUID
    file_path: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
