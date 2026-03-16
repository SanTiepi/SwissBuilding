"""Portfolio Risk Trends Service.

Tracks risk evolution over time across a portfolio of buildings,
enabling time-series analysis, trend detection, and risk trajectory forecasting.
"""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.models.change_signal import ChangeSignal
from app.schemas.portfolio_trends import (
    BuildingRiskTrajectory,
    PortfolioRiskReport,
    PortfolioRiskSnapshot,
    PortfolioRiskTrend,
    RiskDataPoint,
    RiskDistribution,
    RiskHotspot,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RISK_LEVEL_SCORES = {
    "low": 0.2,
    "medium": 0.5,
    "high": 0.8,
    "critical": 1.0,
    "unknown": 0.0,
}

HIGH_RISK_LEVELS = {"high", "critical"}


def _score_from_level(level: str | None) -> float:
    """Convert a risk level string to a numeric score."""
    return RISK_LEVEL_SCORES.get(level or "unknown", 0.0)


def _level_from_score(score: float) -> str:
    """Convert a numeric risk score to a risk level string."""
    if score >= 0.9:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    if score > 0.0:
        return "low"
    return "unknown"


def _detect_trend(data_points: list[RiskDataPoint]) -> tuple[str, float | None]:
    """Determine trend direction and change rate (per month) from data points."""
    if len(data_points) < 2:
        return "stable", None

    first = data_points[0]
    last = data_points[-1]
    days = (last.date - first.date).days
    if days <= 0:
        return "stable", None

    score_delta = last.risk_score - first.risk_score
    months = days / 30.0
    change_rate = round(score_delta / months, 4) if months > 0 else None

    if change_rate is None:
        return "stable", None
    if change_rate < -0.01:
        return "improving", change_rate
    if change_rate > 0.01:
        return "deteriorating", change_rate
    return "stable", change_rate


def _apply_org_filter(query, organization_id: UUID | None):
    """Apply organization filter via building owner when provided."""
    # The Building model doesn't have organization_id directly,
    # but we filter by owner_id when organization_id is given.
    # For now, we use a pass-through — the org filter is a placeholder
    # until multi-org ownership is fully modeled.
    return query


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_portfolio_risk_trend(
    db: AsyncSession,
    months: int = 12,
    organization_id: UUID | None = None,
) -> PortfolioRiskTrend:
    """Compute portfolio-level risk trend over past N months.

    Uses BuildingSnapshots to reconstruct historical risk levels.
    Groups by month.
    """
    period_end = date.today()
    period_start = period_end - timedelta(days=months * 30)

    # Count active buildings
    bq = select(func.count()).select_from(Building).where(Building.status == "active")
    bq = _apply_org_filter(bq, organization_id)
    total_result = await db.execute(bq)
    total_buildings = total_result.scalar() or 0

    # Fetch snapshots in period
    snap_q = (
        select(BuildingSnapshot)
        .join(Building, Building.id == BuildingSnapshot.building_id)
        .where(Building.status == "active", BuildingSnapshot.captured_at >= period_start)
        .order_by(BuildingSnapshot.captured_at)
    )
    snap_q = _apply_org_filter(snap_q, organization_id)
    result = await db.execute(snap_q)
    snapshots = result.scalars().all()

    # Group snapshots by month
    monthly: dict[date, list[BuildingSnapshot]] = {}
    for snap in snapshots:
        month_key = date(snap.captured_at.year, snap.captured_at.month, 1)
        monthly.setdefault(month_key, []).append(snap)

    data_points: list[RiskDataPoint] = []
    for month_key in sorted(monthly.keys()):
        month_snaps = monthly[month_key]
        scores = [_score_from_level(s.passport_grade) for s in month_snaps]
        # Use overall_trust as a risk proxy if available, otherwise passport_grade
        trust_scores = [s.overall_trust for s in month_snaps if s.overall_trust is not None]
        if trust_scores:
            avg_score = sum(trust_scores) / len(trust_scores)
        elif scores:
            avg_score = sum(scores) / len(scores)
        else:
            avg_score = 0.0

        building_ids = {s.building_id for s in month_snaps}
        data_points.append(
            RiskDataPoint(
                date=month_key,
                risk_score=round(avg_score, 4),
                risk_level=_level_from_score(avg_score),
                building_count=len(building_ids),
            )
        )

    trend_direction, _ = _detect_trend(data_points)

    # Per-building trajectory directions
    building_snaps: dict[UUID, list[BuildingSnapshot]] = {}
    for snap in snapshots:
        building_snaps.setdefault(snap.building_id, []).append(snap)

    improving = 0
    deteriorating = 0
    stable = 0
    for _bid, bsnaps in building_snaps.items():
        bsnaps.sort(key=lambda s: s.captured_at)
        b_points = [
            RiskDataPoint(
                date=date(s.captured_at.year, s.captured_at.month, s.captured_at.day),
                risk_score=s.overall_trust if s.overall_trust is not None else _score_from_level(s.passport_grade),
                risk_level=_level_from_score(
                    s.overall_trust if s.overall_trust is not None else _score_from_level(s.passport_grade)
                ),
                building_count=1,
            )
            for s in bsnaps
        ]
        direction, _ = _detect_trend(b_points)
        if direction == "improving":
            improving += 1
        elif direction == "deteriorating":
            deteriorating += 1
        else:
            stable += 1

    # Buildings without snapshots are stable
    stable += max(0, total_buildings - len(building_snaps))

    avg_risk_score = None
    if data_points:
        avg_risk_score = round(sum(dp.risk_score for dp in data_points) / len(data_points), 4)

    return PortfolioRiskTrend(
        total_buildings=total_buildings,
        period_start=period_start,
        period_end=period_end,
        data_points=data_points,
        avg_risk_score=avg_risk_score,
        trend_direction=trend_direction,
        buildings_improving=improving,
        buildings_deteriorating=deteriorating,
        buildings_stable=stable,
    )


async def get_building_risk_trajectory(
    db: AsyncSession,
    building_id: UUID,
    months: int = 12,
) -> BuildingRiskTrajectory:
    """Compute per-building risk trajectory from snapshots."""
    cutoff = date.today() - timedelta(days=months * 30)

    # Get building address
    b_result = await db.execute(select(Building).where(Building.id == building_id))
    building = b_result.scalar_one_or_none()
    address = building.address if building else None

    # Get current risk score
    rs_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_score_row = rs_result.scalar_one_or_none()
    current_risk_score = risk_score_row.confidence if risk_score_row else None

    # Fetch snapshots
    snap_q = (
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id, BuildingSnapshot.captured_at >= cutoff)
        .order_by(BuildingSnapshot.captured_at)
    )
    result = await db.execute(snap_q)
    snapshots = result.scalars().all()

    data_points: list[RiskDataPoint] = []
    for snap in snapshots:
        score = snap.overall_trust if snap.overall_trust is not None else _score_from_level(snap.passport_grade)
        data_points.append(
            RiskDataPoint(
                date=date(snap.captured_at.year, snap.captured_at.month, snap.captured_at.day),
                risk_score=round(score, 4),
                risk_level=_level_from_score(score),
                building_count=1,
            )
        )

    trend_direction, change_rate = _detect_trend(data_points)

    return BuildingRiskTrajectory(
        building_id=building_id,
        address=address,
        data_points=data_points,
        current_risk_score=current_risk_score,
        trend_direction=trend_direction,
        change_rate=change_rate,
    )


async def get_portfolio_risk_snapshot(
    db: AsyncSession,
    organization_id: UUID | None = None,
) -> PortfolioRiskSnapshot:
    """Current-state risk distribution across all buildings."""
    query = (
        select(Building.id, BuildingRiskScore.overall_risk_level, BuildingRiskScore.confidence)
        .outerjoin(BuildingRiskScore, Building.id == BuildingRiskScore.building_id)
        .where(Building.status == "active")
    )
    query = _apply_org_filter(query, organization_id)
    result = await db.execute(query)
    rows = result.all()

    # Distribution
    level_counts: dict[str, int] = {}
    scores: list[float] = []
    worst_id: UUID | None = None
    best_id: UUID | None = None
    worst_score = -1.0
    best_score = 2.0

    for building_id, risk_level, confidence in rows:
        level = risk_level or "unknown"
        level_counts[level] = level_counts.get(level, 0) + 1
        score = float(confidence) if confidence is not None else 0.0
        scores.append(score)
        if score > worst_score:
            worst_score = score
            worst_id = building_id
        if score < best_score:
            best_score = score
            best_id = building_id

    total = len(rows)
    distribution = [
        RiskDistribution(
            risk_level=level,
            count=count,
            percentage=round(count / total * 100, 2) if total > 0 else 0.0,
        )
        for level, count in sorted(level_counts.items())
    ]

    avg_score = round(sum(scores) / len(scores), 4) if scores else None
    median_score = None
    if scores:
        sorted_scores = sorted(scores)
        mid = len(sorted_scores) // 2
        if len(sorted_scores) % 2 == 0:
            median_score = round((sorted_scores[mid - 1] + sorted_scores[mid]) / 2, 4)
        else:
            median_score = round(sorted_scores[mid], 4)

    return PortfolioRiskSnapshot(
        date=date.today(),
        distribution=distribution,
        avg_score=avg_score,
        median_score=median_score,
        worst_building_id=worst_id if total > 0 else None,
        best_building_id=best_id if total > 0 else None,
    )


async def get_risk_hotspots(
    db: AsyncSession,
    limit: int = 10,
    organization_id: UUID | None = None,
) -> list[RiskHotspot]:
    """Identify buildings that have been at high/critical risk the longest."""
    # Get buildings with high/critical risk
    query = (
        select(Building.id, Building.address, BuildingRiskScore.overall_risk_level, BuildingRiskScore.confidence)
        .join(BuildingRiskScore, Building.id == BuildingRiskScore.building_id)
        .where(
            Building.status == "active",
            BuildingRiskScore.overall_risk_level.in_(["high", "critical"]),
        )
    )
    query = _apply_org_filter(query, organization_id)
    result = await db.execute(query)
    rows = result.all()

    hotspots: list[RiskHotspot] = []
    for building_id, address, risk_level, confidence in rows:
        # Count high-risk snapshots to estimate days at high risk
        snap_q = (
            select(func.count())
            .select_from(BuildingSnapshot)
            .where(
                BuildingSnapshot.building_id == building_id,
            )
        )
        await db.execute(snap_q)

        # Count change signals for this building
        sig_q = (
            select(func.count())
            .select_from(ChangeSignal)
            .where(
                ChangeSignal.building_id == building_id,
            )
        )
        sig_result = await db.execute(sig_q)
        signal_count = sig_result.scalar() or 0

        # Estimate days at high risk from earliest snapshot
        earliest_q = select(func.min(BuildingSnapshot.captured_at)).where(BuildingSnapshot.building_id == building_id)
        earliest_result = await db.execute(earliest_q)
        earliest = earliest_result.scalar()
        if earliest:
            days_at_high_risk = (date.today() - date(earliest.year, earliest.month, earliest.day)).days
        else:
            days_at_high_risk = 0

        hotspots.append(
            RiskHotspot(
                building_id=building_id,
                address=address,
                risk_score=round(float(confidence) if confidence else 0.0, 4),
                risk_level=risk_level,
                days_at_high_risk=days_at_high_risk,
                signal_count=signal_count,
            )
        )

    # Sort by risk_score desc, then days at high risk desc
    hotspots.sort(key=lambda h: (-h.risk_score, -h.days_at_high_risk))
    return hotspots[:limit]


async def get_portfolio_risk_report(
    db: AsyncSession,
    months: int = 12,
    organization_id: UUID | None = None,
) -> PortfolioRiskReport:
    """Full report combining trend, current snapshot, and hotspots."""
    trend = await get_portfolio_risk_trend(db, months=months, organization_id=organization_id)
    snapshot = await get_portfolio_risk_snapshot(db, organization_id=organization_id)
    hotspots = await get_risk_hotspots(db, limit=10, organization_id=organization_id)

    high_risk_buildings = [h.building_id for h in hotspots]
    at_risk_count = len(high_risk_buildings)

    return PortfolioRiskReport(
        portfolio_trend=trend,
        current_snapshot=snapshot,
        hotspots=hotspots,
        at_risk_count=at_risk_count,
        high_risk_buildings=high_risk_buildings,
    )


async def compare_portfolio_risk_periods(
    db: AsyncSession,
    period1_start: date,
    period1_end: date,
    period2_start: date,
    period2_end: date,
    organization_id: UUID | None = None,
) -> dict:
    """Compare risk metrics between two time periods."""

    async def _period_stats(start: date, end: date) -> dict:
        snap_q = (
            select(BuildingSnapshot)
            .join(Building, Building.id == BuildingSnapshot.building_id)
            .where(
                Building.status == "active",
                BuildingSnapshot.captured_at >= start,
                BuildingSnapshot.captured_at <= end,
            )
        )
        snap_q = _apply_org_filter(snap_q, organization_id)
        result = await db.execute(snap_q)
        snapshots = result.scalars().all()

        if not snapshots:
            return {
                "avg_risk_score": None,
                "building_count": 0,
                "high_risk_count": 0,
            }

        scores = []
        building_ids: set[UUID] = set()
        high_risk = 0
        for snap in snapshots:
            score = snap.overall_trust if snap.overall_trust is not None else _score_from_level(snap.passport_grade)
            scores.append(score)
            building_ids.add(snap.building_id)
            if _level_from_score(score) in HIGH_RISK_LEVELS:
                high_risk += 1

        return {
            "avg_risk_score": round(sum(scores) / len(scores), 4) if scores else None,
            "building_count": len(building_ids),
            "high_risk_count": high_risk,
        }

    p1 = await _period_stats(period1_start, period1_end)
    p2 = await _period_stats(period2_start, period2_end)

    score_delta = None
    if p1["avg_risk_score"] is not None and p2["avg_risk_score"] is not None:
        score_delta = round(p2["avg_risk_score"] - p1["avg_risk_score"], 4)

    return {
        "period1": {"start": period1_start.isoformat(), "end": period1_end.isoformat(), **p1},
        "period2": {"start": period2_start.isoformat(), "end": period2_end.isoformat(), **p2},
        "score_delta": score_delta,
        "improvement": score_delta is not None and score_delta < 0,
    }
