"""Pydantic v2 schemas for stakeholder-specific dashboard views."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------


class BuildingAttentionItem(BaseModel):
    """A building that needs attention with a reason."""

    building_id: UUID
    address: str
    city: str
    risk_level: str | None = None
    reason: str

    model_config = ConfigDict(from_attributes=True)


class UpcomingDeadline(BaseModel):
    """An action item with an upcoming due date."""

    action_id: UUID
    building_id: UUID
    title: str
    due_date: date
    priority: str

    model_config = ConfigDict(from_attributes=True)


class InterventionSummaryItem(BaseModel):
    """Lightweight intervention reference for contractor view."""

    intervention_id: UUID
    building_id: UUID
    title: str
    status: str
    date_start: date | None = None
    date_end: date | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN1 — Owner dashboard
# ---------------------------------------------------------------------------


class OwnerDashboard(BaseModel):
    """Property owner dashboard view."""

    buildings_count: int = 0
    overall_risk_status: str | None = None  # low | medium | high | critical
    upcoming_deadlines: list[UpcomingDeadline] = []
    pending_actions: int = 0
    total_estimated_cost: float = 0.0
    buildings_needing_attention: list[BuildingAttentionItem] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN2 — Diagnostician dashboard
# ---------------------------------------------------------------------------


class DiagnosticianDashboard(BaseModel):
    """Diagnostician dashboard view."""

    assigned_buildings: int = 0
    diagnostics_in_progress: int = 0
    completed_this_month: int = 0
    quality_score_avg: float | None = None
    pending_validations: int = 0
    workload_forecast: int = 0  # draft diagnostics not yet started

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN3 — Authority dashboard
# ---------------------------------------------------------------------------


class AuthorityDashboard(BaseModel):
    """Authority dashboard view."""

    buildings_in_jurisdiction: int = 0
    pending_submissions: int = 0
    overdue_compliance_items: int = 0
    buildings_with_critical_risk: int = 0
    approval_queue: int = 0

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# FN4 — Contractor dashboard
# ---------------------------------------------------------------------------


class ContractorDashboard(BaseModel):
    """Contractor dashboard view."""

    assigned_interventions: int = 0
    in_progress_works: int = 0
    completed_this_month: int = 0
    upcoming_starts: list[InterventionSummaryItem] = []
    required_certifications: int = 0  # acknowledgments pending
    acknowledgment_status: dict[str, int] = {}  # status → count

    model_config = ConfigDict(from_attributes=True)
