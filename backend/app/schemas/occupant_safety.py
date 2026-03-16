"""Pydantic v2 schemas for the Occupant Safety Evaluator."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SafetyLevel(StrEnum):
    safe = "safe"
    caution = "caution"
    warning = "warning"
    danger = "danger"


class ExposurePathway(StrEnum):
    inhalation = "inhalation"
    ingestion = "ingestion"
    contact = "contact"


class PopulationType(StrEnum):
    residents = "residents"
    workers = "workers"
    children = "children"
    visitors = "visitors"


class RecommendationUrgency(StrEnum):
    immediate = "immediate"
    short_term = "short_term"
    long_term = "long_term"


class ZonePollutantExposure(BaseModel):
    """A single pollutant exposure within a zone."""

    pollutant_type: str
    material_state: str | None = None
    concentration: float | None = None
    unit: str | None = None
    pathways: list[ExposurePathway]
    exposed_populations: list[PopulationType]
    estimated_daily_hours: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class ZoneSafetyAssessment(BaseModel):
    """Safety assessment for a single zone."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    floor_number: int | None = None
    safety_level: SafetyLevel
    score: float = Field(ge=0.0, le=1.0)
    pollutant_count: int = 0
    dominant_risk: str | None = None
    details: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class OccupantSafetyAssessment(BaseModel):
    """Global safety assessment for a building's occupants."""

    building_id: UUID
    overall_safety_level: SafetyLevel
    overall_score: float = Field(ge=0.0, le=1.0)
    zones: list[ZoneSafetyAssessment]
    total_zones: int = 0
    zones_at_risk: int = 0
    critical_findings: list[str] = []
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZoneExposureRisk(BaseModel):
    """Exposure risk details for a single zone."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    exposures: list[ZonePollutantExposure]
    overall_risk_level: SafetyLevel
    is_habitable_zone: bool = False

    model_config = ConfigDict(from_attributes=True)


class BuildingExposureRisk(BaseModel):
    """Exposure risk for all zones in a building."""

    building_id: UUID
    zones: list[ZoneExposureRisk]
    total_exposures: int = 0
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SafetyRecommendation(BaseModel):
    """A single safety recommendation."""

    zone_id: UUID
    zone_name: str
    urgency: RecommendationUrgency
    category: str
    description: str
    pollutant_type: str | None = None
    estimated_cost_chf: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BuildingSafetyRecommendations(BaseModel):
    """All safety recommendations for a building."""

    building_id: UUID
    recommendations: list[SafetyRecommendation]
    immediate_count: int = 0
    short_term_count: int = 0
    long_term_count: int = 0
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingSafetySummary(BaseModel):
    """Safety summary for a single building in portfolio view."""

    building_id: UUID
    address: str
    city: str
    safety_level: SafetyLevel
    zones_at_risk: int = 0
    requires_immediate_action: bool = False

    model_config = ConfigDict(from_attributes=True)


class PortfolioSafetyOverview(BaseModel):
    """Portfolio-level safety overview for an organization."""

    organization_id: UUID
    total_buildings: int = 0
    distribution: dict[str, int] = {}
    buildings_requiring_action: list[BuildingSafetySummary] = []
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
