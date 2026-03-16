"""Pydantic v2 schemas for the Building Certification service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MissingRequirement(BaseModel):
    """A single missing requirement for certification readiness."""

    id: str
    description: str
    category: str  # diagnostic, document, pollutant, evidence
    severity: str  # blocking, recommended

    model_config = ConfigDict(from_attributes=True)


class CertificationReadiness(BaseModel):
    """Readiness evaluation for a specific certification type."""

    building_id: UUID
    certification_type: str  # minergie, cecb, snbs, geak
    readiness_score: int  # 0-100
    missing_requirements: list[MissingRequirement]
    estimated_completion_effort: str  # low, medium, high
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CertificationEligibility(BaseModel):
    """Eligibility summary for a single certification."""

    certification_type: str
    label: str
    eligibility: str  # eligible, partial, ineligible
    readiness_percentage: int  # 0-100
    blockers: list[str]

    model_config = ConfigDict(from_attributes=True)


class AvailableCertifications(BaseModel):
    """All certifications a building could pursue."""

    building_id: UUID
    certifications: list[CertificationEligibility]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoadmapStep(BaseModel):
    """A single step in a certification roadmap."""

    step_number: int
    description: str
    estimated_duration_days: int
    dependencies: list[str]
    priority: str  # critical, high, medium, low

    model_config = ConfigDict(from_attributes=True)


class CertificationRoadmap(BaseModel):
    """Ordered steps to achieve a certification."""

    building_id: UUID
    certification_type: str
    steps: list[RoadmapStep]
    total_estimated_days: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CertificationDistributionItem(BaseModel):
    """Count per certification type."""

    certification_type: str
    count: int

    model_config = ConfigDict(from_attributes=True)


class PortfolioCertificationStatus(BaseModel):
    """Certification status summary across an organization's portfolio."""

    organization_id: UUID
    total_buildings: int
    certified_count: int
    in_progress_count: int
    eligible_count: int
    certification_distribution: list[CertificationDistributionItem]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
