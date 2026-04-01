"""Pydantic v2 schemas for Proof of State export."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProofOfStateMetadata(BaseModel):
    """Metadata header for a proof-of-state export."""

    export_id: str
    generated_at: str
    generated_by: str
    format_version: str
    building_id: str
    summary_only: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class ProofOfStateIntegrity(BaseModel):
    """Integrity verification block."""

    algorithm: str
    hash: str

    model_config = ConfigDict(from_attributes=True)


class ProofOfStateRead(BaseModel):
    """Full proof-of-state export."""

    metadata: ProofOfStateMetadata
    building: dict | None = None
    evidence_score: dict | None = None
    passport: dict | None = None
    completeness: dict | None = None
    trust: dict | None = None
    diagnostics: list[dict] | None = None
    samples: list[dict] | None = None
    documents: list[dict] | None = None
    actions: list[dict] | None = None
    timeline: list[dict] | None = None
    readiness: dict | None = None
    unknowns: list[dict] | None = None
    contradictions: dict | None = None
    integrity: ProofOfStateIntegrity

    model_config = ConfigDict(from_attributes=True)


class ProofOfStateSummaryRead(BaseModel):
    """Compact proof-of-state summary."""

    metadata: ProofOfStateMetadata
    evidence_score: dict | None = None
    passport: dict | None = None
    readiness: dict | None = None
    integrity: ProofOfStateIntegrity

    model_config = ConfigDict(from_attributes=True)
