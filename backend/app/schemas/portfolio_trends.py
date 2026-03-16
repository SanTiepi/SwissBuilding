import uuid
from datetime import date

from pydantic import BaseModel


class RiskDataPoint(BaseModel):
    date: date
    risk_score: float
    risk_level: str
    building_count: int


class BuildingRiskTrajectory(BaseModel):
    building_id: uuid.UUID
    address: str | None
    data_points: list[RiskDataPoint]
    current_risk_score: float | None
    trend_direction: str  # improving | stable | deteriorating
    change_rate: float | None  # score change per month


class PortfolioRiskTrend(BaseModel):
    total_buildings: int
    period_start: date
    period_end: date
    data_points: list[RiskDataPoint]
    avg_risk_score: float | None
    trend_direction: str
    buildings_improving: int
    buildings_deteriorating: int
    buildings_stable: int


class RiskDistribution(BaseModel):
    risk_level: str
    count: int
    percentage: float


class PortfolioRiskSnapshot(BaseModel):
    date: date
    distribution: list[RiskDistribution]
    avg_score: float | None
    median_score: float | None
    worst_building_id: uuid.UUID | None
    best_building_id: uuid.UUID | None


class RiskHotspot(BaseModel):
    building_id: uuid.UUID
    address: str | None
    risk_score: float
    risk_level: str
    days_at_high_risk: int
    signal_count: int


class PortfolioRiskReport(BaseModel):
    portfolio_trend: PortfolioRiskTrend
    current_snapshot: PortfolioRiskSnapshot
    hotspots: list[RiskHotspot]
    at_risk_count: int
    high_risk_buildings: list[uuid.UUID]
