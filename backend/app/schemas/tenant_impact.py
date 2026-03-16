"""Pydantic v2 schemas for the Tenant Impact Service."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DisplacementNeed(StrEnum):
    none = "none"
    temporary = "temporary"
    permanent = "permanent"


class TenantType(StrEnum):
    residential = "residential"
    commercial = "commercial"
    mixed = "mixed"


class CommunicationType(StrEnum):
    initial_notice = "initial_notice"
    work_start = "work_start"
    progress_update = "progress_update"
    reentry_clearance = "reentry_clearance"


# --- FN1: assess_tenant_impact ---


class ZoneTenantImpact(BaseModel):
    """Tenant impact assessment for a single zone."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    displacement_needed: DisplacementNeed
    estimated_duration_days: int = 0
    alternative_accommodation_cost_chf: float = 0.0
    rent_reduction_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    notice_period_days: int = 30
    reason: str = ""

    model_config = ConfigDict(from_attributes=True)


class TenantImpactAssessment(BaseModel):
    """Overall tenant impact assessment for a building."""

    building_id: UUID
    building_type: str | None = None
    zones: list[ZoneTenantImpact]
    total_zones: int = 0
    zones_requiring_displacement: int = 0
    total_estimated_cost_chf: float = 0.0
    max_duration_days: int = 0
    swiss_law_reference: str = "CO Art. 259a-259i (defauts de la chose louee)"
    assessed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FN2: generate_tenant_communication_plan ---


class CommunicationTemplate(BaseModel):
    """A single communication in the tenant notification timeline."""

    step: int
    communication_type: CommunicationType
    title: str
    description: str
    days_before_work: int | None = None
    days_after_start: int | None = None
    required: bool = True
    recipients: str = "all_tenants"
    template_sections: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class TenantCommunicationPlan(BaseModel):
    """Timeline of required tenant notifications for a building."""

    building_id: UUID
    communications: list[CommunicationTemplate]
    total_communications: int = 0
    earliest_notice_days_before: int = 0
    swiss_law_reference: str = "CO Art. 256-256b (obligations du bailleur)"
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FN3: estimate_displacement_costs ---


class ZoneDisplacementCost(BaseModel):
    """Displacement cost breakdown for a single zone."""

    zone_id: UUID
    zone_name: str
    zone_type: str
    tenant_type: TenantType
    temporary_relocation_chf: float = 0.0
    rent_loss_chf: float = 0.0
    moving_costs_chf: float = 0.0
    business_interruption_chf: float = 0.0
    subtotal_chf: float = 0.0
    duration_days: int = 0

    model_config = ConfigDict(from_attributes=True)


class DisplacementCostEstimate(BaseModel):
    """Financial impact of tenant displacement for a building."""

    building_id: UUID
    zones: list[ZoneDisplacementCost]
    total_temporary_relocation_chf: float = 0.0
    total_rent_loss_chf: float = 0.0
    total_moving_costs_chf: float = 0.0
    total_business_interruption_chf: float = 0.0
    grand_total_chf: float = 0.0
    estimated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FN4: get_portfolio_tenant_exposure ---


class BuildingTenantSummary(BaseModel):
    """Tenant exposure summary for a single building in portfolio view."""

    building_id: UUID
    address: str
    city: str
    zones_requiring_displacement: int = 0
    estimated_cost_chf: float = 0.0
    max_duration_days: int = 0
    requires_tenant_action: bool = False

    model_config = ConfigDict(from_attributes=True)


class PortfolioTenantExposure(BaseModel):
    """Organization-level tenant exposure overview."""

    organization_id: UUID
    total_buildings: int = 0
    buildings_requiring_action: int = 0
    total_tenants_affected_zones: int = 0
    total_displacement_cost_chf: float = 0.0
    buildings: list[BuildingTenantSummary] = []
    timeline_pressure_days: int = 0
    assessed_at: datetime

    model_config = ConfigDict(from_attributes=True)
