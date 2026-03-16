from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentProcessingMetadata(BaseModel):
    """Metadata from file processing pipeline (virus scan + OCR)."""

    virus_scan: dict | None = None
    ocr: dict | None = None


class DocumentRead(BaseModel):
    id: UUID
    building_id: UUID
    file_path: str
    file_name: str
    file_size_bytes: int | None
    mime_type: str | None
    document_type: str
    description: str | None
    uploaded_by: UUID
    processing_metadata: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
