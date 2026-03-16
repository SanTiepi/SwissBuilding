"""Schemas for regulatory deadline tracking."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class RegulatoryDeadline(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    deadline_type: str
    pollutant_type: str | None = None
    due_date: date
    status: str  # overdue | critical | warning | upcoming | ok
    source_diagnostic_id: uuid.UUID | None = None
    description: str
    legal_reference: str


class BuildingDeadlines(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    deadlines: list[RegulatoryDeadline]
    overdue_count: int
    critical_count: int
    next_30_days: int
    next_90_days: int


class BuildingAtRisk(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    address: str
    overdue_count: int
    next_deadline: date | None = None


class PortfolioDeadlineReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_buildings: int
    total_overdue: int
    total_critical: int
    upcoming_by_month: dict[str, int]
    buildings_at_risk: list[BuildingAtRisk]


class MonthDeadlines(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month: int
    deadlines: list[RegulatoryDeadline]


class DeadlineCalendar(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    year: int
    months: list[MonthDeadlines]


class ExpiringCompliance(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    artefact_id: uuid.UUID
    artefact_type: str
    expires_at: date
    days_remaining: int
    status: str  # overdue | critical | warning | upcoming | ok
