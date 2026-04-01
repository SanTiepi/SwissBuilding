"""Pydantic schemas for Proactive Alert endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class AlertRead(BaseModel):
    alert_type: str
    severity: str
    title: str
    message: str
    building_id: str
    entity_type: str | None = None
    entity_id: str | None = None
    recommended_action: str
    notification_id: str | None = None


class AlertSummaryRead(BaseModel):
    total_alerts: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    buildings_with_alerts: int


class PortfolioAlertSummaryRead(BaseModel):
    total_alerts: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    buildings_with_alerts: int
    alerts: list[AlertRead] = []
