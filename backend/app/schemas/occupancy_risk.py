"""Pydantic v2 schemas for the Occupancy Risk Service (renovation exposure)."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OccupancyRiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RelocationUrgency(StrEnum):
    immediate = "immediate"
    planned = "planned"
    not_required = "not_required"


class CommunicationPhase(StrEnum):
    before = "before"
    during = "during"
    after = "after"


# --- FN1: assess_occupancy_risk ---


class OccupancyRiskFactor(BaseModel):
    """A single risk factor contributing to occupancy risk during renovation."""

    factor_name: str
    severity: OccupancyRiskLevel
    description: str
    affected_zones: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class OccupancyRiskAssessment(BaseModel):
    """Overall occupancy risk assessment for a building during renovation."""

    building_id: UUID
    risk_level: OccupancyRiskLevel
    risk_factors: list[OccupancyRiskFactor] = []
    mitigation_recommendations: list[str] = []
    occupant_count_estimate: int = 0
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FN2: evaluate_temporary_relocation ---


class AffectedUnit(BaseModel):
    """A unit (zone) affected by relocation."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    floor_number: int | None = None
    reason: str

    model_config = ConfigDict(from_attributes=True)


class CostEstimateRange(BaseModel):
    """Cost estimate range in CHF."""

    min_chf: float = 0.0
    max_chf: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class TemporaryRelocationAssessment(BaseModel):
    """Assessment of whether temporary relocation is needed during renovation."""

    building_id: UUID
    relocation_needed: bool = False
    urgency: RelocationUrgency = RelocationUrgency.not_required
    estimated_duration_days: int = 0
    affected_units: list[AffectedUnit] = []
    cost_estimate_range: CostEstimateRange = Field(default_factory=CostEstimateRange)
    regulatory_basis: list[str] = []
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FN3: generate_occupant_communication ---


class KeyMessage(BaseModel):
    """A key message for a specific renovation phase."""

    phase: CommunicationPhase
    message: str
    priority: int = 0

    model_config = ConfigDict(from_attributes=True)


class OccupantCommunicationPlan(BaseModel):
    """Structured communication plan for building occupants during renovation."""

    building_id: UUID
    notification_timeline: list[str] = []
    key_messages: list[KeyMessage] = []
    affected_parties: list[str] = []
    language_requirements: list[str] = []
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FN4: get_portfolio_occupancy_risk ---


class HighPriorityBuilding(BaseModel):
    """A building flagged as high priority in portfolio occupancy risk."""

    building_id: UUID
    address: str
    city: str
    risk_level: OccupancyRiskLevel
    occupant_count_estimate: int = 0
    relocation_needed: bool = False

    model_config = ConfigDict(from_attributes=True)


class PortfolioOccupancyRisk(BaseModel):
    """Portfolio-level occupancy risk overview for an organization."""

    organization_id: UUID
    buildings_by_risk_level: dict[str, int] = {}
    total_affected_occupants: int = 0
    relocation_needs_count: int = 0
    high_priority_buildings: list[HighPriorityBuilding] = []
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
