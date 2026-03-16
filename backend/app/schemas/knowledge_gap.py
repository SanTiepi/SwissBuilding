"""Pydantic v2 schemas for the Knowledge Gap service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class KnowledgeGap(BaseModel):
    """A single identified knowledge gap."""

    id: str
    gap_type: str  # undiagnosed_pollutant, unsampled_zone, outdated_diagnostic, conflicting_results, missing_document
    severity: str  # low, medium, high, critical
    description: str
    location: str | None = None
    recommended_action: str

    model_config = ConfigDict(from_attributes=True)


class KnowledgeGapResult(BaseModel):
    """All knowledge gaps for a building."""

    building_id: UUID
    gaps: list[KnowledgeGap]
    total_gaps: int
    critical_count: int
    high_count: int
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationPriority(BaseModel):
    """A single investigation priority with ROI estimate."""

    rank: int
    gap_type: str
    description: str
    location: str | None = None
    estimated_cost_chf: float
    risk_reduction_value: float  # 0.0-1.0
    roi_score: float  # risk_reduction_value / estimated_cost_chf * 1000

    model_config = ConfigDict(from_attributes=True)


class InvestigationPriorityResult(BaseModel):
    """Ranked investigation priorities for a building."""

    building_id: UUID
    priorities: list[InvestigationPriority]
    total_estimated_cost_chf: float
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PollutantSubScore(BaseModel):
    """Knowledge sub-score for a single pollutant."""

    pollutant: str
    score: float  # 0-100
    has_diagnostic: bool
    has_samples: bool
    samples_recent: bool

    model_config = ConfigDict(from_attributes=True)


class ZoneSubScore(BaseModel):
    """Knowledge sub-score for a single zone."""

    zone_id: UUID | None = None
    zone_name: str
    score: float  # 0-100
    has_samples: bool

    model_config = ConfigDict(from_attributes=True)


class DocumentSubScore(BaseModel):
    """Knowledge sub-score for a document type."""

    document_type: str
    score: float  # 0 or 100
    present: bool

    model_config = ConfigDict(from_attributes=True)


class RadarChartAxis(BaseModel):
    """A single axis for a radar chart."""

    axis: str
    value: float  # 0-100

    model_config = ConfigDict(from_attributes=True)


class KnowledgeCompletenessResult(BaseModel):
    """Overall knowledge completeness for a building."""

    building_id: UUID
    overall_score: float  # 0-100
    pollutant_scores: list[PollutantSubScore]
    zone_scores: list[ZoneSubScore]
    document_scores: list[DocumentSubScore]
    radar_chart: list[RadarChartAxis]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingKnowledgeSummary(BaseModel):
    """Summary of knowledge completeness for a single building in portfolio view."""

    building_id: UUID
    address: str
    completeness_score: float  # 0-100
    gap_count: int
    critical_gap_count: int

    model_config = ConfigDict(from_attributes=True)


class PortfolioKnowledgeOverview(BaseModel):
    """Organisation-level knowledge overview."""

    organization_id: UUID
    building_count: int
    avg_completeness: float  # 0-100
    worst_buildings: list[BuildingKnowledgeSummary]
    most_common_gaps: list[str]
    estimated_cost_to_80: float
    estimated_cost_to_90: float
    estimated_cost_to_100: float
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
