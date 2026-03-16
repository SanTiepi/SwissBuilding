"""Schemas for warranty obligations tracking."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WarrantyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    warranty_id: str
    intervention_id: UUID | None = None
    warranty_type: str  # defect_liability / material_guarantee / workmanship / regulatory_compliance
    start_date: date
    end_date: date
    duration_months: int
    contractor_name: str | None = None
    status: str  # active / expiring_soon / expired / claimed
    coverage_description: str


class BuildingWarrantyReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    warranties: list[WarrantyItem]
    total_active: int
    total_expiring_soon: int
    total_expired: int
    coverage_score: float  # 0.0 - 1.0
    generated_at: datetime


class RecurringObligation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    obligation_id: str
    obligation_type: str  # annual_inspection / air_monitoring / surface_testing / maintenance_check
    frequency_months: int
    last_performed: date | None = None
    next_due: date
    is_overdue: bool
    pollutant_type: str | None = None
    description: str


class BuildingObligationsSchedule(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    obligations: list[RecurringObligation]
    total_obligations: int
    overdue_count: int
    next_action_date: date | None = None
    generated_at: datetime


class DefectClaim(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    claim_id: str
    warranty_id: str
    defect_description: str
    reported_date: date
    severity: str  # minor / major / critical
    status: str  # reported / under_review / accepted / rejected / resolved


class BuildingDefectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    claims: list[DefectClaim]
    total_claims: int
    open_claims: int
    resolution_rate: float
    generated_at: datetime


class PortfolioWarrantyOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings: int
    total_active_warranties: int
    expiring_within_90_days: int
    total_overdue_obligations: int
    average_coverage_score: float
    generated_at: datetime
