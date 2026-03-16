"""Schemas for execution quality module."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkQualityCheck(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    check_id: UUID
    intervention_id: UUID
    check_type: str  # visual_inspection / lab_verification / air_measurement / surface_test
    status: str  # pending / passed / failed / waived
    checked_by: str | None = None
    checked_at: datetime | None = None
    notes: str | None = None


class InterventionQualityReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    intervention_id: UUID
    intervention_type: str
    overall_status: str  # pending / acceptable / unacceptable / requires_rework
    quality_checks: list[WorkQualityCheck]
    pass_rate: float
    generated_at: datetime


class AcceptanceCriteria(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    threshold_value: float
    unit: str
    regulation_ref: str
    description: str


class BuildingAcceptanceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    acceptance_rate: float
    pending_checks: int


class BuildingAcceptanceReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    interventions_total: int
    interventions_accepted: int
    interventions_pending: int
    interventions_rejected: int
    acceptance_rate: float
    by_pollutant: dict[str, float]
    generated_at: datetime


class QualityTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: str
    pass_rate: float
    total_checks: int
    failed_checks: int


class PortfolioQualityDashboard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_interventions: int
    overall_acceptance_rate: float
    by_building: list[BuildingAcceptanceSummary]
    trends: list[QualityTrend]
    generated_at: datetime
