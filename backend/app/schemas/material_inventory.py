"""Schemas for Material Inventory service."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# --- FN1: Material Inventory ---


class MaterialInventoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    material_id: uuid.UUID
    material_type: str
    name: str
    description: str | None = None
    manufacturer: str | None = None
    installation_year: int | None = None
    contains_pollutant: bool
    pollutant_type: str | None = None
    pollutant_confirmed: bool
    sample_id: uuid.UUID | None = None
    condition: str | None = None
    zone_id: uuid.UUID | None = None
    zone_name: str | None = None
    zone_type: str | None = None
    element_id: uuid.UUID | None = None
    element_name: str | None = None
    element_type: str | None = None
    age_estimate_years: int | None = None


class MaterialTypeGroup(BaseModel):
    material_type: str
    count: int
    items: list[MaterialInventoryItem]
    pollutant_count: int


class BuildingMaterialInventory(BaseModel):
    building_id: uuid.UUID
    total_materials: int
    groups: list[MaterialTypeGroup]
    generated_at: datetime


# --- FN2: Material Risk Assessment ---


class MaterialRiskItem(BaseModel):
    material_id: uuid.UUID
    material_type: str
    name: str
    zone_name: str | None = None
    condition: str | None = None
    age_estimate_years: int | None = None
    contains_pollutant: bool
    pollutant_type: str | None = None
    risk_score: float
    risk_level: str
    risk_factors: list[str]
    intervention_priority: int


class BuildingMaterialRisk(BaseModel):
    building_id: uuid.UUID
    assessed_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    materials: list[MaterialRiskItem]
    generated_at: datetime


# --- FN3: Material Lifecycle ---


class MaterialLifecycleItem(BaseModel):
    material_id: uuid.UUID
    material_type: str
    name: str
    zone_name: str | None = None
    installation_year: int | None = None
    age_estimate_years: int | None = None
    expected_lifespan_years: int | None = None
    remaining_years: int | None = None
    end_of_life: bool
    degradation_status: str
    next_maintenance_year: int | None = None
    notes: str | None = None


class BuildingMaterialLifecycle(BaseModel):
    building_id: uuid.UUID
    total_materials: int
    end_of_life_count: int
    approaching_end_count: int
    healthy_count: int
    materials: list[MaterialLifecycleItem]
    generated_at: datetime


# --- FN4: Portfolio Material Overview ---


class MaterialTypeDistribution(BaseModel):
    material_type: str
    count: int
    pollutant_count: int
    pollutant_percentage: float


class HighRiskMaterial(BaseModel):
    material_id: uuid.UUID
    material_type: str
    name: str
    building_id: uuid.UUID
    building_address: str
    risk_score: float
    risk_level: str


class PortfolioMaterialOverview(BaseModel):
    organization_id: uuid.UUID
    total_buildings: int
    total_materials: int
    pollutant_material_count: int
    pollutant_percentage: float
    type_distribution: list[MaterialTypeDistribution]
    highest_risk_materials: list[HighRiskMaterial]
    generated_at: datetime
