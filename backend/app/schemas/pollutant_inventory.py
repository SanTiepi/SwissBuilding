"""Schemas for the Pollutant Inventory service."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PollutantInventoryItem(BaseModel):
    """A single pollutant finding within a building."""

    model_config = ConfigDict(from_attributes=True)

    sample_id: uuid.UUID
    diagnostic_id: uuid.UUID
    pollutant_type: str
    pollutant_subtype: str | None = None
    status: str  # confirmed, suspected, cleared
    concentration: float | None = None
    unit: str | None = None
    threshold_exceeded: bool = False
    risk_level: str | None = None
    location_floor: str | None = None
    location_room: str | None = None
    location_detail: str | None = None
    material_category: str | None = None
    material_description: str | None = None
    zone_name: str | None = None
    zone_type: str | None = None
    diagnostic_date: date | None = None
    diagnostic_status: str | None = None


class BuildingPollutantInventory(BaseModel):
    """Complete pollutant inventory for a building."""

    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    total_findings: int
    items: list[PollutantInventoryItem]
    pollutant_types_found: list[str]
    generated_at: datetime


class PollutantTypeSummary(BaseModel):
    """Summary for a single pollutant type within a building."""

    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    count: int
    confirmed_count: int
    suspected_count: int
    cleared_count: int
    worst_risk_level: str | None = None
    zones_affected: list[str]
    latest_diagnostic_date: date | None = None
    max_concentration: float | None = None
    unit: str | None = None


class BuildingPollutantSummary(BaseModel):
    """Summary of all pollutants for a building."""

    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    summaries: list[PollutantTypeSummary]
    total_pollutant_types: int
    generated_at: datetime


class BuildingPollutantStats(BaseModel):
    """Stats for a single building in a portfolio view."""

    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    address: str
    city: str
    pollutant_types: list[str]
    total_findings: int
    confirmed_count: int
    worst_risk_level: str | None = None


class PortfolioPollutantOverview(BaseModel):
    """Pollutant distribution across all buildings in an organization."""

    model_config = ConfigDict(from_attributes=True)

    organization_id: uuid.UUID
    total_buildings: int
    buildings_with_pollutants: int
    pollutant_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    buildings: list[BuildingPollutantStats]
    generated_at: datetime


class PollutantHotspot(BaseModel):
    """A zone with high concentration or multiple pollutants."""

    model_config = ConfigDict(from_attributes=True)

    zone_name: str | None = None
    zone_type: str | None = None
    location_key: str
    pollutant_types: list[str]
    pollutant_count: int
    max_concentration: float | None = None
    worst_risk_level: str | None = None
    findings_count: int
    risk_score: float


class BuildingPollutantHotspots(BaseModel):
    """Hotspots for a building, ranked by risk."""

    model_config = ConfigDict(from_attributes=True)

    building_id: uuid.UUID
    hotspots: list[PollutantHotspot]
    generated_at: datetime
