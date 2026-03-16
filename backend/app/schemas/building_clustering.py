"""Schemas for building clustering service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Shared ───────────────────────────────────────────────────────


class ClusterBuilding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    address: str


# ── FN1: Risk Profile Clusters ──────────────────────────────────


class RiskProfileCluster(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cluster_id: str
    risk_signature: dict[str, str] = Field(description="Pollutant → risk level mapping defining this cluster")
    buildings: list[ClusterBuilding]
    cluster_size: int
    dominant_risk: str = Field(description="Most severe pollutant in this cluster")


class RiskProfileClusterResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    clusters: list[RiskProfileCluster]
    total_buildings_analyzed: int
    generated_at: datetime


# ── FN2: Construction Era Clusters ──────────────────────────────


class EraCluster(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    era_label: str = Field(description="pre_1950 | 1950_1975 | 1975_1991 | post_1991")
    building_count: int
    buildings: list[ClusterBuilding]
    common_pollutant_risks: list[str]
    recommended_actions: list[str]


class EraClusterResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    era_clusters: list[EraCluster]
    total_buildings_analyzed: int
    generated_at: datetime


# ── FN3: Outlier Buildings ──────────────────────────────────────


class OutlierBuilding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outlier_id: UUID
    building_address: str
    deviation_type: str = Field(
        description="risk_higher_than_peers | unusual_pollutant_mix | missing_diagnostics_vs_peers"
    )
    severity: float = Field(ge=0.0, le=1.0)
    explanation: str


class OutlierBuildingResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    outliers: list[OutlierBuilding]
    total_buildings_analyzed: int
    generated_at: datetime


# ── FN4: Cluster Summary ────────────────────────────────────────


class ClusterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    total_buildings: int
    total_clusters: int
    largest_cluster_size: int
    most_common_risk_pattern: str
    buildings_without_cluster: int
    diversity_score: float = Field(ge=0.0, le=1.0)
    generated_at: datetime
