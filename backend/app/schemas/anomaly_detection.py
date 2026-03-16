"""Pydantic v2 schemas for the Anomaly Detection service."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnomalyType(StrEnum):
    value_spike = "value_spike"
    missing_data = "missing_data"
    inconsistent_state = "inconsistent_state"
    temporal_gap = "temporal_gap"
    threshold_breach = "threshold_breach"
    pattern_deviation = "pattern_deviation"


class AnomalySeverity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


class Anomaly(BaseModel):
    id: str
    building_id: UUID
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    title: str
    description: str
    entity_type: str | None = None
    entity_id: UUID | None = None
    detected_at: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class AnomalyReport(BaseModel):
    building_id: UUID
    anomalies: list[Anomaly]
    total: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    scanned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalyTrend(BaseModel):
    period: str
    anomaly_counts: list[dict]  # [{date: ..., count: ...}]
    trend_direction: str  # improving | stable | worsening

    model_config = ConfigDict(from_attributes=True)
