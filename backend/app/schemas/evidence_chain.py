"""Pydantic schemas for Evidence Chain validation and analysis."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BrokenLink(BaseModel):
    """A broken link in the evidence chain."""

    entity_type: str
    entity_id: uuid.UUID
    issue: str
    severity: str  # critical, high, medium, low


class ChainValidationResult(BaseModel):
    """Result of evidence chain validation."""

    building_id: uuid.UUID
    integrity_score: int  # 0-100
    total_checks: int
    passed_checks: int
    broken_links: list[BrokenLink]
    validated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProvenanceGap(BaseModel):
    """A gap in evidence provenance."""

    entity_type: str
    entity_id: uuid.UUID
    gap_type: str
    severity: str  # critical, high, medium, low
    description: str
    fix_recommendation: str


class ProvenanceGapsResult(BaseModel):
    """Result of provenance gap analysis."""

    building_id: uuid.UUID
    total_gaps: int
    gaps: list[ProvenanceGap]
    analysed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceTimelineEvent(BaseModel):
    """A single event in the evidence timeline."""

    event_type: str  # diagnostic_created, sample_collected, document_uploaded, etc.
    entity_type: str
    entity_id: uuid.UUID
    date: datetime
    title: str
    actor_id: uuid.UUID | None = None
    actor_name: str | None = None
    details: str | None = None


class EvidenceTimelineResult(BaseModel):
    """Chronological evidence trail."""

    building_id: uuid.UUID
    events: list[EvidenceTimelineEvent]
    total_events: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PollutantEvidenceStrength(BaseModel):
    """Evidence strength assessment for a single pollutant."""

    pollutant_type: str
    claim: str  # detected, not_detected, unknown
    strength: str  # strong, moderate, weak, insufficient
    sample_count: int
    most_recent_sample_date: datetime | None = None
    has_lab_reference: bool
    zone_coverage_pct: float  # 0.0 - 100.0
    details: str


class EvidenceStrengthResult(BaseModel):
    """Per-pollutant evidence strength assessment."""

    building_id: uuid.UUID
    pollutants: list[PollutantEvidenceStrength]
    overall_strength: str  # strong, moderate, weak, insufficient
    assessed_at: datetime

    model_config = ConfigDict(from_attributes=True)
