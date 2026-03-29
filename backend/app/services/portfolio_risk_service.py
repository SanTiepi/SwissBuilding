"""Portfolio Risk Service.

Provides portfolio-level risk overview and heatmap data by aggregating
evidence scores and action counts for all buildings in an organization.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.user import User
from app.services.evidence_score_service import compute_evidence_score


def _grade_to_risk_level(grade: str) -> str:
    """Map evidence grade to a risk level label."""
    return {
        "A": "low",
        "B": "low",
        "C": "medium",
        "D": "high",
        "F": "critical",
    }.get(grade, "unknown")


async def _load_org_building_ids(db: AsyncSession, org_id: UUID) -> list[UUID]:
    """Return IDs of all active buildings belonging to an organization."""
    # Direct org_id on building takes precedence; fall back to created_by user.
    stmt = select(Building.id).where(
        and_(
            Building.status == "active",
            Building.organization_id == org_id,
        )
    )
    result = await db.execute(stmt)
    ids = [row[0] for row in result.all()]
    if ids:
        return ids

    # Fallback: buildings created by users in the org
    user_stmt = select(User.id).where(User.organization_id == org_id)
    user_result = await db.execute(user_stmt)
    user_ids = [row[0] for row in user_result.all()]
    if not user_ids:
        return []

    stmt2 = select(Building.id).where(
        and_(
            Building.status == "active",
            Building.created_by.in_(user_ids),
        )
    )
    result2 = await db.execute(stmt2)
    return [row[0] for row in result2.all()]


async def _action_counts(db: AsyncSession, building_id: UUID) -> tuple[int, int]:
    """Return (open_actions_count, critical_actions_count) for a building."""
    open_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == "open",
            )
        )
    )
    open_count = open_result.scalar() or 0

    critical_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == "open",
                ActionItem.priority == "critical",
            )
        )
    )
    critical_count = critical_result.scalar() or 0

    return open_count, critical_count


async def get_portfolio_risk_overview(db: AsyncSession, org_id: UUID) -> dict:
    """Build a full portfolio risk overview for the given organization.

    Returns dict matching PortfolioRiskOverviewRead schema.
    """
    building_ids = await _load_org_building_ids(db, org_id)

    if not building_ids:
        return {
            "total_buildings": 0,
            "avg_evidence_score": 0.0,
            "buildings_at_risk": 0,
            "buildings_ok": 0,
            "worst_building_id": None,
            "distribution": {
                "grade_a": 0,
                "grade_b": 0,
                "grade_c": 0,
                "grade_d": 0,
                "grade_f": 0,
            },
            "buildings": [],
        }

    # Load building details
    stmt = select(Building).where(Building.id.in_(building_ids))
    result = await db.execute(stmt)
    buildings = list(result.scalars().all())

    points: list[dict] = []
    scores: list[int] = []
    distribution = {"grade_a": 0, "grade_b": 0, "grade_c": 0, "grade_d": 0, "grade_f": 0}
    worst_id: str | None = None
    worst_score: int = 101

    for b in buildings:
        ev = await compute_evidence_score(db, b.id)
        score = ev["score"] if ev else 0
        grade = ev["grade"] if ev else "F"

        open_count, critical_count = await _action_counts(db, b.id)

        risk_level = _grade_to_risk_level(grade)

        point = {
            "building_id": str(b.id),
            "address": b.address or "",
            "city": b.city or "",
            "canton": b.canton or "",
            "latitude": b.latitude,
            "longitude": b.longitude,
            "score": score,
            "grade": grade,
            "risk_level": risk_level,
            "open_actions_count": open_count,
            "critical_actions_count": critical_count,
        }
        points.append(point)
        scores.append(score)

        dist_key = f"grade_{grade.lower()}"
        if dist_key in distribution:
            distribution[dist_key] += 1

        if score < worst_score:
            worst_score = score
            worst_id = str(b.id)

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    at_risk = sum(1 for s in scores if s < 40)
    ok_count = sum(1 for s in scores if s >= 70)

    return {
        "total_buildings": len(buildings),
        "avg_evidence_score": avg_score,
        "buildings_at_risk": at_risk,
        "buildings_ok": ok_count,
        "worst_building_id": worst_id,
        "distribution": distribution,
        "buildings": points,
    }


async def get_risk_heatmap_data(db: AsyncSession, org_id: UUID) -> list[dict]:
    """Return minimal data points for map rendering.

    Each item: {lat, lng, building_id, score, grade, risk_level, address}
    """
    building_ids = await _load_org_building_ids(db, org_id)
    if not building_ids:
        return []

    stmt = select(Building).where(Building.id.in_(building_ids))
    result = await db.execute(stmt)
    buildings = list(result.scalars().all())

    points: list[dict] = []
    for b in buildings:
        if b.latitude is None or b.longitude is None:
            continue

        ev = await compute_evidence_score(db, b.id)
        score = ev["score"] if ev else 0
        grade = ev["grade"] if ev else "F"

        points.append(
            {
                "lat": b.latitude,
                "lng": b.longitude,
                "building_id": str(b.id),
                "score": score,
                "grade": grade,
                "risk_level": _grade_to_risk_level(grade),
                "address": b.address or "",
            }
        )

    return points
