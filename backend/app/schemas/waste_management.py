"""Schemas for OLED-compliant waste management."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WasteClassificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sample_id: UUID | None = None
    material_id: UUID | None = None
    pollutant_type: str | None = None
    concentration: float | None = None
    unit: str | None = None
    waste_category: str  # type_b, type_e, special
    classification_basis: str
    location: str | None = None


class BuildingWasteClassification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    items: list[WasteClassificationItem] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)  # category → count
    generated_at: datetime


class DisposalRoute(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    waste_category: str
    disposal_method: str
    authorized_facility_type: str
    transport_requirements: list[str] = Field(default_factory=list)
    documentation_required: list[str] = Field(default_factory=list)
    estimated_cost_chf_per_ton: float = 0.0


class WastePlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    disposal_routes: list[DisposalRoute] = Field(default_factory=list)
    total_estimated_cost_chf: float = 0.0
    regulatory_references: list[str] = Field(default_factory=list)
    generated_at: datetime


class WasteVolumeEstimate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    waste_category: str
    volume_m3: float = 0.0
    weight_tons: float = 0.0
    density_factor: float = 1.0
    packaging_requirement: str = "standard"
    container_type: str = "open_top"


class BuildingWasteVolumes(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    estimates: list[WasteVolumeEstimate] = Field(default_factory=list)
    total_volume_m3: float = 0.0
    total_weight_tons: float = 0.0
    generated_at: datetime


class BuildingWasteForecastEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    total_volume_m3: float = 0.0
    total_cost_chf: float = 0.0
    planned_intervention_date: str | None = None


class PortfolioWasteForecast(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    buildings: list[BuildingWasteForecastEntry] = Field(default_factory=list)
    total_volumes_by_category: dict[str, float] = Field(default_factory=dict)
    total_disposal_cost_chf: float = 0.0
    regulatory_filing_requirements: list[str] = Field(default_factory=list)
    generated_at: datetime
