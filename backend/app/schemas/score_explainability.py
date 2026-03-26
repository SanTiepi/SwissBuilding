"""
BatiConnect — Score Explainability Schemas

Every metric in indispensability reports carries its full proof trail:
the list of concrete items (documents, contradictions, evidence links,
enrichment sources) that compose it.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ScoreLineItem(BaseModel):
    """One atomic piece of evidence backing a score."""

    item_type: str  # "document" | "contradiction" | "evidence_link" | "enrichment_source" | "obligation" | "action" | "snapshot" | "custody_event" | "procedure"
    item_id: UUID
    label: str  # French human-readable label
    detail: str  # French explanation of what this item contributes
    contribution: str  # What it adds: "+1 source unifiée", "+4h économisées", etc.
    link: str  # Frontend deep-link path: "/buildings/{id}/documents/{doc_id}"
    source_class: str | None = None  # official/documentary/observed/commercial/derived
    timestamp: datetime | None = None


class ExplainedScore(BaseModel):
    """A score with its full proof trail."""

    metric_name: str  # "sources_unified", "contradictions_resolved", etc.
    metric_label: str  # French display name
    value: float
    unit: str  # "sources", "contradictions", "heures", "CHF", etc.
    methodology: str  # French explanation of how this number is computed
    line_items: list[ScoreLineItem]
    confidence: str  # "exact" | "estimated" | "heuristic"


class ExplainedReport(BaseModel):
    """Full explainability report for a building."""

    building_id: UUID
    generated_at: datetime
    scores: list[ExplainedScore]
    total_line_items: int
    methodology_summary: str  # French paragraph explaining the overall approach
