"""Pydantic v2 schemas for the Incident Response Service."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentScenario(StrEnum):
    fiber_release = "fiber_release"
    spill = "spill"
    elevated_radon = "elevated_radon"


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ContactRole(StrEnum):
    building_owner = "building_owner"
    diagnostician = "diagnostician"
    contractor = "contractor"
    suva = "suva"
    cantonal_authority = "cantonal_authority"
    emergency_services = "emergency_services"


# --- Incident Plan ---


class IncidentAction(BaseModel):
    """A single action in an incident response scenario."""

    step: int
    description: str
    responsible: str
    timeframe: str

    model_config = ConfigDict(from_attributes=True)


class ScenarioResponse(BaseModel):
    """Response plan for a specific incident scenario."""

    scenario: IncidentScenario
    pollutant: str
    immediate_actions: list[IncidentAction]
    evacuation_zones: list[str]
    decontamination_steps: list[str]
    notification_chain: list[str]
    authority_reporting: list[str]

    model_config = ConfigDict(from_attributes=True)


class IncidentPlan(BaseModel):
    """Full emergency response plan for a building."""

    building_id: UUID
    address: str
    canton: str
    scenarios: list[ScenarioResponse]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Emergency Contacts ---


class EmergencyContact(BaseModel):
    """A single emergency contact entry."""

    role: ContactRole
    name: str
    organization: str | None = None
    phone: str | None = None
    email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EmergencyContactList(BaseModel):
    """Structured emergency contact list for a building."""

    building_id: UUID
    contacts: list[EmergencyContact]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Incident Probability ---


class ZoneIncidentRisk(BaseModel):
    """Incident probability assessment for a single zone."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    risk_level: RiskLevel
    probability_score: float = Field(ge=0.0, le=1.0)
    factors: list[str]
    pollutants_present: list[str]
    has_degraded_material: bool = False
    is_public_zone: bool = False
    has_active_intervention: bool = False

    model_config = ConfigDict(from_attributes=True)


class BuildingIncidentProbability(BaseModel):
    """Incident probability assessment for all zones in a building."""

    building_id: UUID
    zones: list[ZoneIncidentRisk]
    overall_risk_level: RiskLevel
    highest_risk_zone: str | None = None
    total_zones: int = 0
    high_risk_zones: int = 0
    assessed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Portfolio Readiness ---


class BuildingIncidentSummary(BaseModel):
    """Incident readiness summary for a single building."""

    building_id: UUID
    address: str
    city: str
    has_incident_plan: bool = False
    risk_level: RiskLevel = RiskLevel.low
    high_risk_zones: int = 0

    model_config = ConfigDict(from_attributes=True)


class PortfolioIncidentReadiness(BaseModel):
    """Organization-level incident readiness overview."""

    organization_id: UUID
    total_buildings: int = 0
    buildings_with_plans: int = 0
    buildings_high_risk: int = 0
    coverage_gaps: list[str] = []
    buildings_needing_plans: int = 0
    buildings: list[BuildingIncidentSummary] = []
    assessed_at: datetime

    model_config = ConfigDict(from_attributes=True)
