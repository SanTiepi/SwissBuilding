"""Pydantic schemas for the notification rules engine."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TriggerResult(BaseModel):
    """A single triggered notification rule."""

    model_config = ConfigDict(from_attributes=True)

    trigger_type: str  # overdue_diagnostics, expiring_compliance, high_risk_unaddressed, incomplete_dossier, stale_data
    severity: str  # info, warning, critical
    message: str
    affected_entity_id: UUID | None = None
    recommended_action: str


class BuildingTriggersResponse(BaseModel):
    building_id: UUID
    triggers: list[TriggerResult]
    total: int


class NotificationPreferencesResponse(BaseModel):
    user_id: UUID
    enabled_triggers: list[str]
    frequency: str  # immediate, daily_digest, weekly_digest
    channels: list[str]  # in_app, email
    quiet_hours_start: str | None = None  # HH:MM
    quiet_hours_end: str | None = None


class DigestGroup(BaseModel):
    severity: str
    count: int
    items: list[TriggerResult]


class DigestResponse(BaseModel):
    user_id: UUID
    period: str
    groups: list[DigestGroup]
    total_count: int
    summary: str


class OrgAlertBuilding(BaseModel):
    building_id: UUID
    address: str
    alert_count: int


class OrgAlertSummary(BaseModel):
    org_id: UUID
    total_active_alerts: int
    by_severity: dict[str, int]
    top_triggered_rules: list[str]
    buildings_with_most_alerts: list[OrgAlertBuilding]
    trend: str  # increasing, decreasing, stable
