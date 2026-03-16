from typing import Any

from pydantic import BaseModel


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
