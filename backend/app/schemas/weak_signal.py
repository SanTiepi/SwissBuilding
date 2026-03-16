"""Weak signal watchtower schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WeakSignal(BaseModel):
    """A single weak signal detected for a building."""

    signal_id: str
    building_id: UUID
    signal_type: str = Field(
        ...,
        pattern=r"^(trust_erosion|completeness_decay|diagnostic_aging|intervention_stall|evidence_gap_widening|grade_risk|unknown_accumulation)$",
    )
    severity: str = Field(..., pattern=r"^(watch|advisory|warning)$")
    title: str
    description: str
    detected_at: datetime
    confidence: float = Field(..., ge=0.0, le=1.0)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class WeakSignalReport(BaseModel):
    """Weak signal report for a single building."""

    building_id: UUID
    signals: list[WeakSignal]
    total_signals: int
    highest_severity: str
    risk_trajectory: str = Field(..., pattern=r"^(stable|declining|critical_path)$")

    model_config = ConfigDict(from_attributes=True)


class PortfolioWatchReport(BaseModel):
    """Aggregated weak signal report across a portfolio."""

    total_buildings_scanned: int
    buildings_with_signals: int
    signals_by_type: dict[str, int]
    signals_by_severity: dict[str, int]
    top_risk_buildings: list[dict[str, Any]]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WatchRule(BaseModel):
    """A detection rule used by the watchtower."""

    rule_id: str
    rule_type: str
    description: str
    threshold: float | None = None
    enabled: bool = True

    model_config = ConfigDict(from_attributes=True)
