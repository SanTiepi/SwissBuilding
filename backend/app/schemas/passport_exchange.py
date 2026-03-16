"""Building Passport Exchange Schema — standardized export format."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PassportExchangeMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    schema_version: str = "1.0.0"
    exported_at: datetime
    exported_by: str | None = None
    source_system: str = "SwissBuildingOS"


class PassportExchangeDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metadata: PassportExchangeMetadata
    building_id: UUID
    address: str
    city: str
    canton: str
    construction_year: int | None = None
    passport_grade: str | None = None
    # Full passport summary sections
    knowledge_state: dict | None = None
    readiness: dict | None = None
    completeness: dict | None = None
    blind_spots: dict | None = None
    contradictions: dict | None = None
    evidence_coverage: dict | None = None
    # Optional transfer package sections
    diagnostics_summary: dict | None = None
    interventions_summary: dict | None = None
    actions_summary: dict | None = None
