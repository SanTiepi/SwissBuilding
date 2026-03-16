"""Digital vault schemas for building record integrity tracking."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CustodyEvent(BaseModel):
    """Single event in a document's chain of custody."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    event_type: str  # upload, access, modify, verify, export
    actor: str | None = None
    details: str | None = None


class SuspiciousEntry(BaseModel):
    """An entry flagged as suspicious during integrity checks."""

    model_config = ConfigDict(from_attributes=True)

    entry_id: UUID
    record_type: str
    issue: str
    severity: str  # low, medium, high, critical


class VaultEntry(BaseModel):
    """Single vault entry representing a tracked building record."""

    model_config = ConfigDict(from_attributes=True)

    entry_id: UUID
    document_id: UUID | None = None
    record_type: str  # diagnostic_report, sample_result, action_record, intervention_record, compliance_certificate
    created_at: datetime
    created_by: UUID | None = None
    integrity_hash: str
    verification_status: str  # verified, unverified, tampered, expired


class BuildingVaultSummary(BaseModel):
    """Summary of a building's digital vault status."""

    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    total_entries: int
    verified_count: int
    unverified_count: int
    integrity_score: float  # 0.0 - 1.0
    last_verified_at: datetime | None = None
    generated_at: datetime


class DocumentTrustVerification(BaseModel):
    """Trust verification result for a single document."""

    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    file_name: str
    document_type: str | None = None
    original_hash: str
    current_hash: str
    is_intact: bool
    upload_date: datetime | None = None
    last_verified: datetime
    chain_of_custody: list[CustodyEvent]


class VaultIntegrityReport(BaseModel):
    """Full integrity report for a building's vault."""

    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    total_documents: int
    verified_documents: int
    integrity_percentage: float
    suspicious_entries: list[SuspiciousEntry]
    recommendations: list[str]
    generated_at: datetime


class PortfolioVaultStatus(BaseModel):
    """Vault status aggregated across an organization's portfolio."""

    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings: int
    total_vault_entries: int
    average_integrity_score: float
    buildings_with_issues: int
    by_record_type: dict[str, int]
    generated_at: datetime
