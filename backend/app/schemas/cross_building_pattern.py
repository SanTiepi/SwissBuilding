"""Schemas for cross-building pattern detection."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Pattern Detection ─────────────────────────────────────────────


class AffectedBuilding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    canton: str
    construction_year: int | None = None


class CrossBuildingPattern(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pattern_type: str = Field(description="systemic_pollutant | contractor_quality | geographic")
    label: str
    description: str
    affected_buildings: list[AffectedBuilding]
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: str


class PatternDetectionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    patterns: list[CrossBuildingPattern]
    total_buildings_analyzed: int
    generated_at: datetime


# ── Similar Buildings ─────────────────────────────────────────────


class SimilarBuilding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    canton: str
    construction_year: int | None = None
    similarity_score: float = Field(ge=0.0, le=1.0)
    shared_traits: list[str]


class SimilarBuildingsResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference_building_id: UUID
    similar_buildings: list[SimilarBuilding]
    generated_at: datetime


# ── Geographic Clusters ───────────────────────────────────────────


class ClusterBuilding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str
    latitude: float | None = None
    longitude: float | None = None


class GeographicCluster(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cluster_id: str
    label: str
    risk_factor: str
    center_lat: float | None = None
    center_lon: float | None = None
    radius_km: float | None = None
    buildings: list[ClusterBuilding]
    avg_risk_level: str | None = None


class GeographicClusterResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    clusters: list[GeographicCluster]
    total_buildings: int
    generated_at: datetime


# ── Undiscovered Pollutant Prediction ─────────────────────────────


class PollutantPrediction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pollutant_type: str
    probability: float = Field(ge=0.0, le=1.0)
    basis: str = Field(description="Why this pollutant is predicted")
    peer_count: int = Field(description="Number of similar buildings with this pollutant")
    recommendation: str


class UndiscoveredPollutantResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    predictions: list[PollutantPrediction]
    peer_buildings_used: int
    generated_at: datetime
