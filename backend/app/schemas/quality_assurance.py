"""Quality assurance schemas for comprehensive building QA checks."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QACheckResult(BaseModel):
    """Result of a single QA check."""

    check_id: str
    category: str
    name: str
    status: str  # pass, warn, fail
    detail: str
    fix_suggestion: str | None = None


class QARunResult(BaseModel):
    """Result of running all QA checks on a building."""

    building_id: uuid.UUID
    total_checks: int
    passed: int
    warnings: int
    failures: int
    checks: list[QACheckResult]
    run_at: datetime


class SubScore(BaseModel):
    """A weighted sub-score within the quality score."""

    name: str
    score: float
    weight: float
    grade: str
    detail: str


class QualityScoreResult(BaseModel):
    """Weighted quality score for a building."""

    building_id: uuid.UUID
    overall_score: float
    grade: str
    sub_scores: list[SubScore]
    computed_at: datetime


class QualityTrendPoint(BaseModel):
    """A single point in the quality trend timeline."""

    date: str
    score: float
    event: str | None = None


class QualityTrendsResult(BaseModel):
    """Quality score history for a building."""

    building_id: uuid.UUID
    current_score: float
    trajectory: str  # improving, stable, declining
    trend_points: list[QualityTrendPoint]


class PortfolioBuildingSummary(BaseModel):
    """Quality summary for a single building in a portfolio."""

    building_id: uuid.UUID
    address: str
    score: float
    grade: str

    model_config = ConfigDict(from_attributes=True)


class CommonIssue(BaseModel):
    """A common issue across the portfolio."""

    issue: str
    count: int
    impact: str


class ImprovementRecommendation(BaseModel):
    """A recommendation ranked by impact."""

    recommendation: str
    impact_score: float
    affected_buildings: int


class PortfolioQualityReport(BaseModel):
    """Organisation-level quality report."""

    organization_id: uuid.UUID
    total_buildings: int
    average_score: float
    average_grade: str
    score_distribution: dict[str, int]
    worst_buildings: list[PortfolioBuildingSummary]
    common_issues: list[CommonIssue]
    recommendations: list[ImprovementRecommendation]
