"""Pydantic v2 schemas for stakeholder-targeted notifications."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# FN1: Owner briefing
# ---------------------------------------------------------------------------


class OwnerObligation(BaseModel):
    """Upcoming obligation for an owner."""

    title: str
    due_date: str | None = None
    regulation: str | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OwnerDecision(BaseModel):
    """Recommended decision for an owner."""

    title: str
    rationale: str
    priority: str  # low | medium | high | critical

    model_config = ConfigDict(from_attributes=True)


class OwnerBriefing(BaseModel):
    """Owner-focused briefing with simple language."""

    building_id: UUID
    generated_at: datetime
    risk_overview: str  # plain language summary
    upcoming_obligations: list[OwnerObligation]
    cost_forecast: float  # estimated CHF
    recommended_decisions: list[OwnerDecision]
    urgency_level: str  # routine | attention_needed | urgent | critical

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN2: Diagnostician brief
# ---------------------------------------------------------------------------


class PendingAnalysis(BaseModel):
    """A pending analysis for a diagnostician."""

    diagnostic_id: UUID
    diagnostic_type: str
    status: str
    building_address: str

    model_config = ConfigDict(from_attributes=True)


class SampleCoverageGap(BaseModel):
    """Coverage gap: pollutant type not sampled in a zone."""

    pollutant_type: str
    uncovered_zone: str  # zone name or description

    model_config = ConfigDict(from_attributes=True)


class PriorityArea(BaseModel):
    """High-priority area requiring attention."""

    area: str
    reason: str
    risk_level: str

    model_config = ConfigDict(from_attributes=True)


class DiagnosticianBrief(BaseModel):
    """Diagnostician-focused brief for fieldwork planning."""

    building_id: UUID
    generated_at: datetime
    pending_analyses: list[PendingAnalysis]
    sample_coverage_gaps: list[SampleCoverageGap]
    equipment_needed: list[str]
    estimated_fieldwork_hours: float
    priority_areas: list[PriorityArea]

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN3: Authority report
# ---------------------------------------------------------------------------


class RegulatoryViolation(BaseModel):
    """A specific regulatory violation."""

    regulation: str
    violation: str
    severity: str  # low | medium | high | critical

    model_config = ConfigDict(from_attributes=True)


class RemediationAction(BaseModel):
    """Required remediation action for authority."""

    title: str
    priority: str
    status: str
    due_date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BuildingIdentification(BaseModel):
    """Building identification for authority report."""

    building_id: UUID
    egid: int | None = None
    address: str
    canton: str

    model_config = ConfigDict(from_attributes=True)


class AuthorityNotificationReport(BaseModel):
    """Authority-focused compliance report."""

    building_id: UUID
    generated_at: datetime
    compliance_status_summary: str
    regulatory_violations: list[RegulatoryViolation]
    required_remediation_actions: list[RemediationAction]
    deadline_status: str
    building_identification: BuildingIdentification

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN4: Stakeholder digest
# ---------------------------------------------------------------------------


class DigestNotification(BaseModel):
    """A single notification in a stakeholder digest."""

    building_id: UUID
    building_address: str
    category: str  # risk | compliance | action | fieldwork
    message: str
    priority: str  # low | medium | high | critical

    model_config = ConfigDict(from_attributes=True)


class StakeholderDigest(BaseModel):
    """Role-filtered digest of notifications across org buildings."""

    organization_id: UUID
    role: str
    generated_at: datetime
    notifications: list[DigestNotification]
    total_buildings: int
    total_notifications: int

    model_config = ConfigDict(from_attributes=True)
