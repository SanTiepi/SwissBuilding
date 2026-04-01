"""Schemas for climate exposure profiles and opportunity windows."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Climate Exposure Profile
# ---------------------------------------------------------------------------


class ClimateExposureProfileRead(BaseModel):
    """Read schema for climate exposure profile."""

    id: UUID
    building_id: UUID

    radon_zone: str | None = None
    noise_exposure_day_db: float | None = None
    noise_exposure_night_db: float | None = None
    solar_potential_kwh: float | None = None
    natural_hazard_zones: list[dict[str, Any]] | None = None
    groundwater_zone: str | None = None
    contaminated_site: bool | None = None
    heritage_status: str | None = None

    heating_degree_days: float | None = None
    avg_annual_precipitation_mm: float | None = None
    freeze_thaw_cycles_per_year: int | None = None
    wind_exposure: str | None = None
    altitude_m: float | None = None

    moisture_stress: str = "unknown"
    thermal_stress: str = "unknown"
    uv_exposure: str = "unknown"

    data_sources: list[dict[str, Any]] | None = None
    last_updated: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ClimateExposureRefreshResponse(BaseModel):
    """Response after building/refreshing a climate exposure profile."""

    profile: ClimateExposureProfileRead
    layers_merged: int = 0
    message: str = "Profil d'exposition mis a jour"


# ---------------------------------------------------------------------------
# Opportunity Window
# ---------------------------------------------------------------------------


class OpportunityWindowRead(BaseModel):
    """Read schema for an opportunity window."""

    id: UUID
    building_id: UUID
    case_id: UUID | None = None

    window_type: str
    title: str
    description: str | None = None

    window_start: date
    window_end: date
    optimal_date: date | None = None

    advantage: str | None = None
    expiry_risk: str = "low"
    cost_of_missing: str | None = None

    detected_by: str = "system"
    confidence: float | None = None
    status: str = "active"

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class OpportunityWindowsResponse(BaseModel):
    """Response containing active opportunity windows."""

    windows: list[OpportunityWindowRead] = []
    total: int = 0
    active_count: int = 0


class OpportunityDetectResponse(BaseModel):
    """Response after detecting opportunity windows."""

    detected: int = 0
    new: int = 0
    expired: int = 0
    windows: list[OpportunityWindowRead] = []


class BestTimingResponse(BaseModel):
    """Recommended timing for a work type."""

    work_type: str
    recommended_period: str | None = None
    recommended_start: date | None = None
    recommended_end: date | None = None
    reason: str | None = None
    matching_windows: list[OpportunityWindowRead] = []
    warnings: list[str] = Field(default_factory=list)
