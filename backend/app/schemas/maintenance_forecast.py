"""Pydantic v2 schemas for the Maintenance Forecast service."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MaintenanceItem(BaseModel):
    """A single maintenance forecast item."""

    id: str
    building_id: UUID
    item_type: (
        str  # diagnostic_renewal | intervention_followup | element_replacement | compliance_check | inspection_due
    )
    title: str
    description: str
    estimated_date: date | None = None
    priority: str  # high | medium | low
    estimated_cost_chf: float | None = None
    confidence: float  # 0.0-1.0
    metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class MaintenanceForecast(BaseModel):
    """Full maintenance forecast for a building."""

    building_id: UUID
    items: list[MaintenanceItem]
    total_items: int
    next_12_months: int
    total_estimated_cost: float | None = None
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaintenanceBudget(BaseModel):
    """Yearly budget breakdown for maintenance."""

    building_id: UUID
    yearly_forecasts: list[dict]  # {year: int, items: int, estimated_cost: float}
    total_3_year: float | None = None
    total_5_year: float | None = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioMaintenanceForecast(BaseModel):
    """Aggregate maintenance forecast across a portfolio."""

    total_buildings: int
    total_items: int
    by_type: dict[str, int]
    by_priority: dict[str, int]
    total_estimated_cost: float | None = None
    top_buildings: list[dict]  # {building_id, address, item_count, cost}

    model_config = ConfigDict(from_attributes=True)
