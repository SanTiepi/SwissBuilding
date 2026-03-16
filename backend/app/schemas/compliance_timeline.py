"""Pydantic v2 schemas for the Compliance Timeline service."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ComplianceEvent(BaseModel):
    """A single event in the compliance timeline."""

    timestamp: datetime
    event_type: str  # diagnostic_completed, intervention_done, regulation_change, deadline_approaching, compliance_gap_detected, compliance_restored
    title: str
    description: str | None = None
    severity: str  # info, warning, critical
    metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class ComplianceDeadline(BaseModel):
    """An upcoming or overdue compliance deadline."""

    deadline_date: date
    regulation_ref: str | None = None
    description: str
    status: str  # upcoming, overdue, met
    days_remaining: int | None = None
    related_diagnostic_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CompliancePeriod(BaseModel):
    """A period of compliance or non-compliance."""

    start_date: date | None = None
    end_date: date | None = None
    status: str  # compliant, non_compliant, partially_compliant, unknown
    reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PollutantComplianceState(BaseModel):
    """Per-pollutant compliance status."""

    pollutant: str
    compliant: bool
    last_diagnostic_date: date | None = None
    diagnostic_age_days: int | None = None
    has_active_intervention: bool
    requires_action: bool
    detail: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ComplianceTimeline(BaseModel):
    """Full compliance timeline for a building."""

    building_id: UUID
    events: list[ComplianceEvent]
    deadlines: list[ComplianceDeadline]
    compliance_periods: list[CompliancePeriod]
    current_status: str  # compliant, non_compliant, partially_compliant, unknown
    pollutant_states: list[PollutantComplianceState]

    model_config = ConfigDict(from_attributes=True)


class ComplianceGapAnalysis(BaseModel):
    """Gap analysis identifying missing or expired compliance items."""

    building_id: UUID
    gaps: list[dict]  # each with pollutant, gap_type, description, severity
    total_gaps: int
    critical_gaps: int
    recommended_actions: list[str]

    model_config = ConfigDict(from_attributes=True)
