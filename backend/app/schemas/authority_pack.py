"""Pydantic schemas for authority pack generation."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuthorityPackSection(BaseModel):
    """A single section within an authority pack."""

    section_name: str
    section_type: str  # building_identity, diagnostic_summary, sample_results,
    # compliance_status, action_plan, risk_assessment, intervention_history, document_inventory
    items: list[dict[str, Any]]
    completeness: float = Field(ge=0.0, le=1.0)
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuthorityPackConfig(BaseModel):
    """Configuration for generating an authority pack."""

    building_id: uuid.UUID | None = None  # auto-filled from path param
    canton: str | None = None  # auto-detect from building if None
    include_sections: list[str] | None = None  # all sections if None
    include_photos: bool = True
    language: str = "fr"
    redact_financials: bool = False


class AuthorityPackResult(BaseModel):
    """Result of an authority pack generation."""

    pack_id: uuid.UUID
    building_id: uuid.UUID
    canton: str
    sections: list[AuthorityPackSection]
    total_sections: int
    overall_completeness: float
    generated_at: datetime
    warnings: list[str]
    caveats_count: int = 0
    pack_version: str = "1.0.0"
    sha256_hash: str | None = None
    financials_redacted: bool = False

    model_config = ConfigDict(from_attributes=True)


class AuthorityPackListItem(BaseModel):
    """Summary item for listing authority packs."""

    pack_id: uuid.UUID
    building_id: uuid.UUID
    canton: str
    overall_completeness: float
    generated_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)
