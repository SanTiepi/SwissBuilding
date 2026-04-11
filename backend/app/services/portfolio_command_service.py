"""BatiConnect -- Portfolio Command Center service.

Director-level cockpit for managing an entire portfolio of buildings.
Answers: "Where should I invest my attention and budget across all my buildings?"

Uses efficient aggregate queries -- never per-building service calls for the
main overview. Passport grades are computed per-building only for the
top_priorities ranking (capped at total buildings count).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.readiness_assessment import ReadinessAssessment
from app.services.passport_service import _compute_passport_grade


def _today() -> date:
    return datetime.now(UTC).date()


def _active_filter(org_id: UUID | None):
    conds = [Building.status == "active"]
    if org_id is not None:
        conds.append(Building.organization_id == org_id)
    return conds


# ---------------------------------------------------------------------------
# Per-building row builder (single pass, no N+1)
# ---------------------------------------------------------------------------


async def get_portfolio_overview(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> dict:
    """Generate a director-level portfolio overview."""

    today = _today()
    filters = _active_filter(org_id)

    # ----- 1. Load buildings -----
    bld_result = await db.execute(select(Building).where(*filters))
    buildings = list(bld_result.scalars().all())
    building_map = {b.id: b for b in buildings}
    building_ids = list(building_map.keys())

    if not building_ids:
        return _empty_overview()

    # ----- 2. Latest trust score per building -----
    trust_subq = (
        select(
            BuildingTrustScore.building_id,
            func.max(BuildingTrustScore.assessed_at).label("latest"),
        )
        .where(BuildingTrustScore.building_id.in_(building_ids))
        .group_by(BuildingTrustScore.building_id)
        .subquery()
    )
    trust_result = await db.execute(
        select(BuildingTrustScore).join(
            trust_subq,
            and_(
                BuildingTrustScore.building_id == trust_subq.c.building_id,
                BuildingTrustScore.assessed_at == trust_subq.c.latest,
            ),
        )
    )
    trust_map: dict[UUID, BuildingTrustScore] = {t.building_id: t for t in trust_result.scalars().all()}

    # ----- 3. Risk scores -----
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id.in_(building_ids)))
    risk_map: dict[UUID, BuildingRiskScore] = {r.building_id: r for r in risk_result.scalars().all()}

    # ----- 4. Readiness assessments -----
    ra_result = await db.execute(select(ReadinessAssessment).where(ReadinessAssessment.building_id.in_(building_ids)))
    readiness_map: dict[UUID, list[ReadinessAssessment]] = {}
    for ra in ra_result.scalars().all():
        readiness_map.setdefault(ra.building_id, []).append(ra)

    # ----- 5. Actions (open / in_progress) -----
    action_result = await db.execute(
        select(ActionItem).where(
            and_(
                ActionItem.building_id.in_(building_ids),
                ActionItem.status.in_(["open", "in_progress"]),
            )
        )
    )
    actions_by_bld: dict[UUID, list[ActionItem]] = {}
    for a in action_result.scalars().all():
        actions_by_bld.setdefault(a.building_id, []).append(a)

    # ----- 6. Diagnostics (completed, for expiry check) -----
    diag_result = await db.execute(
        select(Diagnostic).where(
            and_(
                Diagnostic.building_id.in_(building_ids),
                Diagnostic.status == "completed",
            )
        )
    )
    diags_by_bld: dict[UUID, list[Diagnostic]] = {}
    for d in diag_result.scalars().all():
        diags_by_bld.setdefault(d.building_id, []).append(d)

    # ----- 7. Planned interventions -----
    interv_result = await db.execute(
        select(Intervention).where(
            and_(
                Intervention.building_id.in_(building_ids),
                Intervention.status.in_(["planned", "in_progress"]),
            )
        )
    )
    interv_by_bld: dict[UUID, list[Intervention]] = {}
    for iv in interv_result.scalars().all():
        interv_by_bld.setdefault(iv.building_id, []).append(iv)

    # ----- 8. Build per-building rows + aggregates -----
    rows: list[dict] = []
    grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0, "unknown": 0}
    readiness_dist = {"ready": 0, "partial": 0, "not_ready": 0}
    total_open = 0
    total_overdue = 0
    total_expiring = 0
    total_planned = 0
    sum_completeness = 0.0
    sum_trust = 0.0
    count_completeness = 0
    count_trust = 0
    needing_attention = 0

    for bid, bld in building_map.items():
        # Trust
        ts = trust_map.get(bid)
        trust_pct = round((ts.overall_score or 0.0) * 100, 1) if ts else 0.0

        # Completeness (use confidence from risk score as proxy, same as portfolio.py)
        rs = risk_map.get(bid)
        completeness_pct = round(float(rs.confidence or 0) * 100, 1) if rs else 0.0

        # Passport grade
        ra_list = readiness_map.get(bid, [])
        blockers = sum(len(ra.blockers_json) if ra.blockers_json else 0 for ra in ra_list)
        passport_grade = _compute_passport_grade(
            trust=(ts.overall_score or 0.0) if ts else 0.0,
            completeness=(rs.confidence or 0.0) if rs else 0.0,
            blockers=blockers,
            unresolved_contradictions=0,  # skip heavy query, conservative
        )

        # Readiness status
        ready_count = sum(1 for ra in ra_list if ra.status == "ready")
        total_ra = len(ra_list)
        if total_ra == 0:
            readiness_status = "not_ready"
        elif ready_count == total_ra:
            readiness_status = "ready"
        elif ready_count > 0:
            readiness_status = "partial"
        else:
            readiness_status = "not_ready"

        # Actions
        bld_actions = actions_by_bld.get(bid, [])
        open_count = len(bld_actions)
        overdue_count = sum(1 for a in bld_actions if a.due_date and a.due_date < today)

        # Expiring diagnostics (within 90 days of 3-year validity)
        bld_diags = diags_by_bld.get(bid, [])
        expiring_count = 0
        for d in bld_diags:
            rd = d.date_report
            if not rd:
                continue
            if isinstance(rd, datetime):
                expiry = rd + timedelta(days=3 * 365)
                expiry_d = expiry.date()
            else:
                expiry_d = rd + timedelta(days=3 * 365)
            days_left = (expiry_d - today).days
            if 0 <= days_left <= 90:
                expiring_count += 1

        # Planned interventions
        bld_intervs = interv_by_bld.get(bid, [])
        planned_count = len(bld_intervs)
        est_cost = sum(iv.cost_chf or 0 for iv in bld_intervs) or None

        # Risk level
        risk_level = rs.overall_risk_level if rs else "unknown"

        # Last activity (use building updated_at as proxy)
        last_activity = bld.updated_at

        rows.append(
            {
                "id": str(bid),
                "name": bld.address or "—",
                "address": f"{bld.address}, {bld.postal_code} {bld.city}",
                "municipality": bld.city,
                "canton": bld.canton,
                "passport_grade": passport_grade,
                "completeness_pct": completeness_pct,
                "trust_pct": trust_pct,
                "readiness_status": readiness_status,
                "open_actions_count": open_count,
                "overdue_actions_count": overdue_count,
                "expiring_diagnostics_count": expiring_count,
                "planned_interventions_count": planned_count,
                "estimated_cost_pending": est_cost,
                "risk_level": risk_level,
                "last_activity": last_activity.isoformat() if last_activity else None,
            }
        )

        # Aggregates
        if passport_grade in grade_dist:
            grade_dist[passport_grade] += 1
        else:
            grade_dist["unknown"] += 1

        readiness_dist[readiness_status] = readiness_dist.get(readiness_status, 0) + 1

        total_open += open_count
        total_overdue += overdue_count
        total_expiring += expiring_count
        total_planned += planned_count

        sum_completeness += completeness_pct
        count_completeness += 1
        sum_trust += trust_pct
        count_trust += 1

        if overdue_count > 0 or risk_level == "critical":
            needing_attention += 1

    avg_completeness = round(sum_completeness / count_completeness, 1) if count_completeness else 0.0
    avg_trust = round(sum_trust / count_trust, 1) if count_trust else 0.0

    # ----- 9. Top priorities (score = overdue*10 + critical_risk*20 + expiring*3 + (100-completeness)) -----
    for row in rows:
        score = 0.0
        score += row["overdue_actions_count"] * 10
        if row["risk_level"] == "critical":
            score += 20
        elif row["risk_level"] == "high":
            score += 10
        score += row["expiring_diagnostics_count"] * 3
        score += 100 - row["completeness_pct"]
        row["_priority_score"] = score

    sorted_rows = sorted(rows, key=lambda r: r["_priority_score"], reverse=True)
    top_priorities = []
    for r in sorted_rows[:5]:
        reasons = []
        if r["overdue_actions_count"] > 0:
            reasons.append(f"{r['overdue_actions_count']} actions en retard")
        if r["risk_level"] == "critical":
            reasons.append("risque critique")
        elif r["risk_level"] == "high":
            reasons.append("risque eleve")
        if r["expiring_diagnostics_count"] > 0:
            reasons.append(f"{r['expiring_diagnostics_count']} diagnostics expirant")
        if r["completeness_pct"] < 50:
            reasons.append(f"completude faible ({r['completeness_pct']}%)")
        if not reasons:
            reasons.append("score global bas")

        top_priorities.append(
            {
                "building_id": r["id"],
                "building_name": r["name"],
                "reason": ", ".join(reasons),
                "priority_score": round(r["_priority_score"], 1),
            }
        )

    # Clean internal field
    for r in rows:
        r.pop("_priority_score", None)

    # ----- 10. Budget horizon -----
    all_intervs = []
    for ivs in interv_by_bld.values():
        all_intervs.extend(ivs)

    budget_horizon = _compute_budget_horizon(all_intervs, today)

    return {
        "buildings": rows,
        "aggregates": {
            "total_buildings": len(buildings),
            "grade_distribution": grade_dist,
            "readiness_distribution": readiness_dist,
            "avg_completeness": avg_completeness,
            "avg_trust": avg_trust,
            "total_open_actions": total_open,
            "total_overdue": total_overdue,
            "total_expiring_90d": total_expiring,
            "total_planned_interventions": total_planned,
            "buildings_needing_attention": needing_attention,
        },
        "top_priorities": top_priorities,
        "budget_horizon": budget_horizon,
    }


def _compute_budget_horizon(interventions: list, today: date) -> dict:
    """Compute budget windows at 30d / 90d / 365d."""
    windows = {
        "next_30d": {"days": 30, "buildings": set(), "cost": 0.0},
        "next_90d": {"days": 90, "buildings": set(), "cost": 0.0},
        "next_365d": {"days": 365, "buildings": set(), "cost": 0.0},
    }
    for iv in interventions:
        start = iv.date_start
        if not start:
            # No start date => include in all windows
            for w in windows.values():
                w["buildings"].add(iv.building_id)
                w["cost"] += iv.cost_chf or 0
            continue
        if isinstance(start, datetime):
            start = start.date()
        days_until = (start - today).days
        for _key, w in windows.items():
            if days_until <= w["days"]:
                w["buildings"].add(iv.building_id)
                w["cost"] += iv.cost_chf or 0

    return {
        key: {
            "buildings_with_work": len(w["buildings"]),
            "estimated_cost": round(w["cost"], 2) if w["cost"] > 0 else None,
        }
        for key, w in windows.items()
    }


async def get_portfolio_heatmap(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> dict:
    """Return data for a readiness heatmap.

    Each building mapped to: grade, completeness, trust, readiness -- for visual matrix.
    """
    filters = _active_filter(org_id)

    bld_result = await db.execute(select(Building).where(*filters))
    buildings = list(bld_result.scalars().all())
    building_ids = [b.id for b in buildings]

    if not building_ids:
        return {"buildings": []}

    # Trust
    trust_subq = (
        select(
            BuildingTrustScore.building_id,
            func.max(BuildingTrustScore.assessed_at).label("latest"),
        )
        .where(BuildingTrustScore.building_id.in_(building_ids))
        .group_by(BuildingTrustScore.building_id)
        .subquery()
    )
    trust_result = await db.execute(
        select(BuildingTrustScore).join(
            trust_subq,
            and_(
                BuildingTrustScore.building_id == trust_subq.c.building_id,
                BuildingTrustScore.assessed_at == trust_subq.c.latest,
            ),
        )
    )
    trust_map = {t.building_id: t for t in trust_result.scalars().all()}

    # Risk (for completeness proxy)
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id.in_(building_ids)))
    risk_map = {r.building_id: r for r in risk_result.scalars().all()}

    # Readiness
    ra_result = await db.execute(select(ReadinessAssessment).where(ReadinessAssessment.building_id.in_(building_ids)))
    readiness_map: dict[UUID, list[ReadinessAssessment]] = {}
    for ra in ra_result.scalars().all():
        readiness_map.setdefault(ra.building_id, []).append(ra)

    points = []
    for bld in buildings:
        bid = bld.id
        ts = trust_map.get(bid)
        rs = risk_map.get(bid)
        ra_list = readiness_map.get(bid, [])

        trust_pct = round((ts.overall_score or 0.0) * 100, 1) if ts else 0.0
        completeness_pct = round(float(rs.confidence or 0) * 100, 1) if rs else 0.0

        blockers = sum(len(ra.blockers_json) if ra.blockers_json else 0 for ra in ra_list)
        grade = _compute_passport_grade(
            trust=(ts.overall_score or 0.0) if ts else 0.0,
            completeness=(rs.confidence or 0.0) if rs else 0.0,
            blockers=blockers,
            unresolved_contradictions=0,
        )

        ready_count = sum(1 for ra in ra_list if ra.status == "ready")
        total_ra = len(ra_list)
        if total_ra == 0:
            readiness_status = "not_ready"
        elif ready_count == total_ra:
            readiness_status = "ready"
        elif ready_count > 0:
            readiness_status = "partial"
        else:
            readiness_status = "not_ready"

        points.append(
            {
                "building_id": str(bid),
                "building_name": bld.address or "—",
                "completeness_pct": completeness_pct,
                "trust_pct": trust_pct,
                "passport_grade": grade,
                "readiness_status": readiness_status,
            }
        )

    return {"buildings": points}


def _empty_overview() -> dict:
    return {
        "buildings": [],
        "aggregates": {
            "total_buildings": 0,
            "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0, "unknown": 0},
            "readiness_distribution": {"ready": 0, "partial": 0, "not_ready": 0},
            "avg_completeness": 0.0,
            "avg_trust": 0.0,
            "total_open_actions": 0,
            "total_overdue": 0,
            "total_expiring_90d": 0,
            "total_planned_interventions": 0,
            "buildings_needing_attention": 0,
        },
        "top_priorities": [],
        "budget_horizon": {
            "next_30d": {"buildings_with_work": 0, "estimated_cost": None},
            "next_90d": {"buildings_with_work": 0, "estimated_cost": None},
            "next_365d": {"buildings_with_work": 0, "estimated_cost": None},
        },
    }
