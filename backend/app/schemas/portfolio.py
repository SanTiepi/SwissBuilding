from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PortfolioMetrics(BaseModel):
    total_buildings: int
    risk_distribution: dict[str, int]
    completeness_avg: float
    buildings_ready: int
    buildings_not_ready: int
    pollutant_prevalence: dict[str, int]
    actions_pending: int
    actions_critical: int
    recent_diagnostics: int
    interventions_in_progress: int


class MapBuildingFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class MapBuildingsGeoJSON(BaseModel):
    type: str = "FeatureCollection"
    features: list[MapBuildingFeature]


# --- BatiConnect canonical Portfolio CRUD schemas ---


class PortfolioCreate(BaseModel):
    organization_id: UUID
    name: str
    description: str | None = None
    portfolio_type: str | None = None  # management | ownership | diagnostic | campaign | custom
    is_default: bool = False


class PortfolioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    portfolio_type: str | None = None
    is_default: bool | None = None


class PortfolioRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    portfolio_type: str | None
    is_default: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioListRead(BaseModel):
    id: UUID
    name: str
    portfolio_type: str | None
    is_default: bool
    organization_id: UUID

    model_config = ConfigDict(from_attributes=True)


class BuildingPortfolioCreate(BaseModel):
    building_id: UUID
    portfolio_id: UUID


class BuildingPortfolioRead(BaseModel):
    id: UUID
    building_id: UUID
    portfolio_id: UUID
    added_at: datetime
    added_by: UUID | None

    model_config = ConfigDict(from_attributes=True)
