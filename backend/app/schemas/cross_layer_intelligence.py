"""Pydantic v2 schemas for the Cross-Layer Intelligence Engine."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class InsightEvidence(BaseModel):
    """Single evidence signal from one layer."""

    layer: str
    signal: str
    value: Any = None

    model_config = ConfigDict(from_attributes=True)


class CrossLayerInsightRead(BaseModel):
    """A cross-layer insight discovered by correlating multiple layers."""

    insight_id: str
    insight_type: str
    severity: str  # critical / warning / info / opportunity
    title: str
    description: str
    evidence: list[InsightEvidence] = []
    recommendation: str
    confidence: float  # 0-1
    estimated_impact: str

    model_config = ConfigDict(from_attributes=True)


class PortfolioInsightRead(BaseModel):
    """Portfolio-level insight (same shape, distinct type for clarity)."""

    insight_id: str
    insight_type: str
    severity: str
    title: str
    description: str
    evidence: list[InsightEvidence] = []
    recommendation: str
    confidence: float
    estimated_impact: str

    model_config = ConfigDict(from_attributes=True)


class IntelligenceSummaryRead(BaseModel):
    """Aggregated intelligence summary."""

    total_insights: int
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    top_critical: list[CrossLayerInsightRead] = []
    computed_at: str

    model_config = ConfigDict(from_attributes=True)
