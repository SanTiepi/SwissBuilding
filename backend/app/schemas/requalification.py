"""Pydantic schemas for the requalification replay timeline."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RequalificationEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    entry_type: str  # "signal" | "snapshot" | "grade_change" | "intervention"
    title: str
    description: str | None = None
    severity: str | None = None
    signal_type: str | None = None
    grade_before: str | None = None
    grade_after: str | None = None
    metadata: dict | None = None


class RequalificationTimeline(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    entries: list[RequalificationEntry]
    current_grade: str | None = None
    grade_history: list[dict]


# ── Trigger detection schemas ──────────────────────────────────────


class TriggerType(StrEnum):
    grade_degradation = "grade_degradation"
    stale_diagnostic = "stale_diagnostic"
    high_severity_accumulation = "high_severity_accumulation"
    post_intervention = "post_intervention"
    trust_score_drop = "trust_score_drop"


class TriggerUrgency(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RequalificationTrigger(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trigger_type: TriggerType
    severity: TriggerUrgency
    title: str
    description: str
    detected_at: datetime
    metadata: dict | None = None


class RequalificationRecommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    priority: int
    action: str
    reason: str
    trigger_type: TriggerType


class RequalificationTriggerReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: UUID
    triggers: list[RequalificationTrigger]
    needs_requalification: bool
    urgency: TriggerUrgency
    recommendations: list[RequalificationRecommendation]
