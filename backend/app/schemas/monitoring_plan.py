"""Pydantic v2 schemas for the Monitoring Plan service."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MonitoringItem(BaseModel):
    """A single item to monitor (encapsulated asbestos, sealed PCB, radon level, etc.)."""

    id: str
    pollutant_type: str  # asbestos | pcb | lead | hap | radon
    location: str
    monitoring_method: str  # visual_inspection | air_sampling | wipe_test | radon_measurement
    frequency: str  # quarterly | biannual | annual
    responsible_party: str | None = None
    cost_per_cycle_chf: float
    next_due: date | None = None
    last_performed: date | None = None
    metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class MonitoringPlan(BaseModel):
    """Auto-generated monitoring plan for a building."""

    building_id: UUID
    items: list[MonitoringItem]
    total_items: int
    annual_cost_chf: float
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduledCheck(BaseModel):
    """A single scheduled or overdue check."""

    item_id: str
    pollutant_type: str
    location: str
    monitoring_method: str
    scheduled_date: date
    is_overdue: bool = False
    cost_chf: float

    model_config = ConfigDict(from_attributes=True)


class MonitoringSchedule(BaseModel):
    """Next 12 months of monitoring checks for a building."""

    building_id: UUID
    scheduled_checks: list[ScheduledCheck]
    overdue_checks: list[ScheduledCheck]
    total_scheduled: int
    total_overdue: int
    cost_forecast_chf: float
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceGap(BaseModel):
    """A gap in monitoring compliance."""

    item_id: str
    pollutant_type: str
    location: str
    expected_checks: int
    performed_checks: int
    missed_checks: int
    last_performed: date | None = None

    model_config = ConfigDict(from_attributes=True)


class MonitoringCompliance(BaseModel):
    """Compliance evaluation for monitoring obligations."""

    building_id: UUID
    compliance_score: int  # 0-100
    total_required: int
    total_performed: int
    total_overdue: int
    gaps: list[ComplianceGap]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingMonitoringStatus(BaseModel):
    """Monitoring status for a single building within portfolio view."""

    building_id: UUID
    address: str
    has_active_plan: bool
    compliance_score: int
    overdue_checks: int
    annual_cost_chf: float
    needs_new_plan: bool

    model_config = ConfigDict(from_attributes=True)


class PortfolioMonitoringStatus(BaseModel):
    """Org-level monitoring status across all buildings."""

    organization_id: UUID
    total_buildings: int
    buildings_with_plans: int
    compliance_rate: float  # 0.0-1.0
    total_overdue_checks: int
    total_annual_cost_chf: float
    buildings_needing_plans: int
    buildings: list[BuildingMonitoringStatus]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
