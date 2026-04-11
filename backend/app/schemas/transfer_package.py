"""Pydantic v2 schemas for the Building Memory Transfer Package."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransferPackageRequest(BaseModel):
    """Optional request body for transfer package generation."""

    include_sections: list[str] | None = None
    redact_financials: bool = False

    model_config = ConfigDict(from_attributes=True)


class TransferPackageResponse(BaseModel):
    """Full transfer package structure."""

    package_id: UUID
    building_id: UUID
    generated_at: datetime
    schema_version: str
    building_summary: dict
    passport: dict | None = None
    diagnostics_summary: dict | None = None
    documents_summary: dict | None = None
    interventions_summary: dict | None = None
    actions_summary: dict | None = None
    evidence_coverage: dict | None = None
    contradictions: dict | None = None
    unknowns: dict | None = None
    snapshots: list[dict] | None = None
    completeness: dict | None = None
    readiness: dict | None = None
    eco_clauses: dict | None = None
    diagnostic_publications: list[dict] | None = None
    financials_redacted: bool = False
    metadata: dict

    model_config = ConfigDict(from_attributes=True)
