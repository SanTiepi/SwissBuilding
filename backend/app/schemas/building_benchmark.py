"""Schemas for building benchmark / peer comparison."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkDimension(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    building_value: float | None = None
    peer_avg: float | None = None
    peer_median: float | None = None
    percentile: float | None = Field(default=None, ge=0, le=100)
    better_than_peers: bool | None = None


class PeerGroup(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    criteria: dict
    peer_count: int
    building_ids: list[UUID]


class BuildingBenchmark(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    peer_group: PeerGroup
    dimensions: list[BenchmarkDimension]
    overall_percentile: float | None = None
    generated_at: datetime


class BenchmarkComparison(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    buildings: list[BuildingBenchmark]
    best_building_id: UUID | None = None
    worst_building_id: UUID | None = None


class BenchmarkCompareRequest(BaseModel):
    building_ids: list[UUID]


class CantonBenchmark(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    canton: str
    building_count: int
    avg_risk_score: float | None = None
    avg_completeness: float | None = None
    avg_trust: float | None = None
    grade_distribution: dict[str, int]
