"""Pydantic v2 schemas for BatiConnect Certificates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CertificateGenerateRequest(BaseModel):
    """Request body for certificate generation."""

    certificate_type: str = "standard"

    model_config = ConfigDict(from_attributes=True)


class CertificateRead(BaseModel):
    """Full certificate content returned after generation or lookup."""

    certificate_id: str
    certificate_number: str
    certificate_type: str
    version: str
    issued_at: str
    valid_until: str
    building: dict | None = None
    evidence_score: dict | None = None
    passport_grade: str | None = None
    completeness: float | None = None
    trust_score: float | None = None
    readiness_summary: dict | None = None
    key_findings: list[str] | None = None
    document_coverage: dict | None = None
    certification_chain: dict | None = None
    verification_url: str | None = None
    verification_qr_data: str | None = None
    issuer: str | None = None
    disclaimer: str | None = None
    integrity_hash: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CertificateVerifyRead(BaseModel):
    """Result of certificate verification."""

    valid: bool
    certificate: dict | None = None
    reason: str

    model_config = ConfigDict(from_attributes=True)


class CertificateListItem(BaseModel):
    """Summary item for certificate list."""

    id: str
    certificate_number: str
    building_id: str
    certificate_type: str
    evidence_score: int | None = None
    passport_grade: str | None = None
    integrity_hash: str | None = None
    issued_at: str | None = None
    valid_until: str | None = None
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CertificateListRead(BaseModel):
    """Paginated list of certificates."""

    items: list[CertificateListItem]
    total: int
    page: int
    size: int

    model_config = ConfigDict(from_attributes=True)
