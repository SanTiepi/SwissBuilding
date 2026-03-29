"""Pydantic v2 schemas for Portfolio Risk Overview."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BuildingRiskPointRead(BaseModel):
    """Minimal building data for map rendering."""

    building_id: str
    address: str
    city: str
    canton: str
    latitude: float | None = None
    longitude: float | None = None
    score: int
    grade: str
    risk_level: str
    open_actions_count: int = 0
    critical_actions_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class RiskDistributionRead(BaseModel):
    """Count of buildings per evidence grade."""

    grade_a: int = 0
    grade_b: int = 0
    grade_c: int = 0
    grade_d: int = 0
    grade_f: int = 0

    model_config = ConfigDict(from_attributes=True)


class PortfolioRiskOverviewRead(BaseModel):
    """Full portfolio risk overview with summary stats."""

    total_buildings: int
    avg_evidence_score: float
    buildings_at_risk: int
    buildings_ok: int
    worst_building_id: str | None = None
    distribution: RiskDistributionRead
    buildings: list[BuildingRiskPointRead]

    model_config = ConfigDict(from_attributes=True)
