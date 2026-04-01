"""Pydantic schemas for multi-audience pack builder."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PackSection(BaseModel):
    """A single section within a generated pack."""

    section_name: str
    section_type: str
    items: list[dict[str, Any]]
    completeness: float = Field(ge=0.0, le=1.0)
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PackTypeInfo(BaseModel):
    """Metadata about an available pack type."""

    pack_type: str
    name: str
    section_count: int
    includes_trust: bool
    includes_provenance: bool
    readiness: str  # ready | partial | not_ready
    readiness_score: float = Field(ge=0.0, le=1.0)


class PackGenerateRequest(BaseModel):
    """Request body for generating a pack."""

    language: str = "fr"
    redact_financials: bool = False


class PackConformanceResult(BaseModel):
    """Conformance check result attached to a generated pack."""

    profile: str
    result: str  # pass | fail | partial
    score: float = Field(ge=0.0, le=1.0)
    failed_checks: list[dict[str, Any]] = []


class PackResult(BaseModel):
    """Result of a pack generation."""

    pack_id: uuid.UUID
    building_id: uuid.UUID
    pack_type: str
    pack_name: str
    sections: list[PackSection]
    total_sections: int
    overall_completeness: float
    includes_trust: bool
    includes_provenance: bool
    generated_at: datetime
    warnings: list[str]
    caveats_count: int = 0
    pack_version: str = "1.0.0"
    sha256_hash: str | None = None
    financials_redacted: bool = False
    conformance: PackConformanceResult | None = None

    model_config = ConfigDict(from_attributes=True)


class AvailablePacksResponse(BaseModel):
    """Response listing all available pack types for a building."""

    building_id: uuid.UUID
    packs: list[PackTypeInfo]
