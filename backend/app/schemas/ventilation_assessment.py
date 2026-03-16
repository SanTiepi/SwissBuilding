"""Pydantic v2 schemas for the Ventilation Assessment service."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VentilationRequirement(BaseModel):
    """Ventilation requirement for a single zone."""

    zone_id: UUID | None = None
    zone_name: str
    pollutant_type: str  # asbestos | pcb | lead | hap | radon
    ventilation_type: str  # natural | forced | negative_pressure
    air_changes_per_hour: float
    filtration: str | None = None  # HEPA | activated_carbon | none
    monitoring_frequency: str  # continuous | daily | weekly | monthly
    rationale: str

    model_config = ConfigDict(from_attributes=True)


class VentilationAssessment(BaseModel):
    """Per-zone ventilation requirements for a building."""

    building_id: UUID
    requirements: list[VentilationRequirement]
    total_zones_assessed: int
    zones_needing_upgrade: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RadonMitigationRecommendation(BaseModel):
    """Radon mitigation recommendation for a single zone/sample."""

    zone_name: str
    current_level_bq_m3: float
    threshold_bq_m3: float  # 300 reference, 1000 limit
    mitigation_method: str  # sub_slab_depressurization | forced_ventilation | sealing | combined
    expected_reduction_pct: float  # 0-100
    estimated_cost_chf: float
    priority: str  # critical | high | medium | low

    model_config = ConfigDict(from_attributes=True)


class RadonVentilationEvaluation(BaseModel):
    """Radon-specific ventilation adequacy evaluation."""

    building_id: UUID
    total_zones_measured: int
    zones_above_reference: int  # > 300 Bq/m3
    zones_above_limit: int  # > 1000 Bq/m3
    recommendations: list[RadonMitigationRecommendation]
    total_estimated_cost_chf: float
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonitoringPoint(BaseModel):
    """A single air quality monitoring point."""

    location: str
    parameter: str  # fiber_count | radon_level | pcb_concentration | voc_level
    frequency: str  # continuous | hourly | daily | weekly
    threshold_value: float
    threshold_unit: str
    alarm_trigger: float
    documentation_required: str

    model_config = ConfigDict(from_attributes=True)


class AirQualityMonitoringPlan(BaseModel):
    """Air quality monitoring requirements during and after remediation."""

    building_id: UUID
    monitoring_points: list[MonitoringPoint]
    total_points: int
    during_works: bool
    post_remediation: bool
    estimated_duration_days: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingVentilationStatus(BaseModel):
    """Ventilation status for a single building within portfolio view."""

    building_id: UUID
    address: str
    needs_ventilation_upgrade: bool
    radon_priority: str  # critical | high | medium | low | none
    zones_requiring_action: int
    estimated_cost_chf: float
    orap_compliant: bool  # ORaP Art. 110 compliance

    model_config = ConfigDict(from_attributes=True)


class PortfolioVentilationStatus(BaseModel):
    """Org-level ventilation status across all buildings."""

    organization_id: UUID
    total_buildings: int
    buildings_needing_upgrade: int
    radon_mitigation_priority_list: list[BuildingVentilationStatus]
    total_estimated_cost_chf: float
    orap_compliance_rate: float  # 0.0-1.0
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
