"""Portfolio triage service — read model for organization-level building urgency.

Classifies each building in an org portfolio by urgency level:
  critical (red), action_needed (orange), monitored (yellow), under_control (green).

Pure read — no new persistent entities.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_snapshot import BuildingSnapshot
from app.schemas.portfolio_triage import (
    BuildingBenchmark,
    BuildingCluster,
    BuildingTrend,
    PortfolioBenchmark,
    PortfolioKPI,
    PortfolioPattern,
    PortfolioTrends,
    PortfolioTriageBuilding,
    PortfolioTriageResult,
)

logger = logging.getLogger(__name__)


def _classify_building(
    passport_grade: str,
    blockers_count: int,
    trust: float,
) -> str:
    """Classify a building into a triage status based on passport + blockers + trust."""
    if blockers_count > 0 or passport_grade == "F":
        return "critical"
    if passport_grade in ("D", "E") or trust < 0.3:
        return "action_needed"
    if passport_grade == "C" or trust < 0.6:
        return "monitored"
    return "under_control"


_STATUS_ORDER = {"critical": 0, "action_needed": 1, "monitored": 2, "under_control": 3}


async def get_portfolio_triage(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioTriageResult:
    """Build a portfolio triage for all buildings in an organization.

    For each building: computes a lightweight instant card summary
    (passport grade + blockers count + trust) and classifies.
    """
    # Fetch org buildings
    result = await db.execute(select(Building).where(Building.organization_id == org_id))
    buildings = list(result.scalars().all())

    triage_buildings: list[PortfolioTriageBuilding] = []

    for building in buildings:
        passport_grade = "F"
        overall_trust = 0.0
        blockers_count = 0
        top_blocker: str | None = None
        next_action: str | None = None
        risk_score = 0.0

        # Get passport summary (lightweight)
        try:
            from app.services.passport_service import get_passport_summary

            passport = await get_passport_summary(db, building.id)
            if passport:
                passport_grade = passport.get("passport_grade", "F")
                overall_trust = passport.get("knowledge_state", {}).get("overall_trust", 0.0)
                blind_spots = passport.get("blind_spots", {})
                blockers_count = blind_spots.get("blocking", 0)

                # Risk score: inverse of completeness * trust
                completeness = passport.get("completeness", {}).get("overall_score", 0.0)
                risk_score = round(1.0 - (overall_trust * 0.5 + completeness * 0.5), 2)
        except Exception:
            logger.debug("Passport unavailable for building %s", building.id, exc_info=True)

        # Get top blocker from decision view
        try:
            from app.services.decision_view_service import get_building_decision_view

            dv = await get_building_decision_view(db, building.id)
            if dv and dv.blockers:
                blockers_count = max(blockers_count, len(dv.blockers))
                top_blocker = dv.blockers[0].title
        except Exception:
            logger.debug("Decision view unavailable for building %s", building.id, exc_info=True)

        # Get next action from readiness advisor
        try:
            from app.services.readiness_advisor_service import get_suggestions

            suggestions = await get_suggestions(db, building.id)
            if suggestions:
                next_action = suggestions[0].recommended_action or suggestions[0].title
        except Exception:
            logger.debug("Suggestions unavailable for building %s", building.id, exc_info=True)

        status = _classify_building(passport_grade, blockers_count, overall_trust)
        address = f"{building.address}, {building.postal_code} {building.city}"

        triage_buildings.append(
            PortfolioTriageBuilding(
                id=building.id,
                address=address,
                status=status,
                top_blocker=top_blocker,
                risk_score=risk_score,
                next_action=next_action,
                passport_grade=passport_grade,
            )
        )

    # Sort by urgency
    triage_buildings.sort(key=lambda b: (_STATUS_ORDER.get(b.status, 99), -b.risk_score))

    # Count by status
    counts = {"critical": 0, "action_needed": 0, "monitored": 0, "under_control": 0}
    for b in triage_buildings:
        if b.status in counts:
            counts[b.status] += 1

    return PortfolioTriageResult(
        org_id=org_id,
        critical_count=counts["critical"],
        action_needed_count=counts["action_needed"],
        monitored_count=counts["monitored"],
        under_control_count=counts["under_control"],
        buildings=triage_buildings,
    )


# ── Helpers ──────────────────────────────────────────────────────────

_GRADE_NUMERIC = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 0}


def _grade_to_numeric(grade: str) -> int:
    return _GRADE_NUMERIC.get(grade, 0)


def _numeric_to_grade(value: float) -> str:
    for letter, num in sorted(_GRADE_NUMERIC.items(), key=lambda x: -x[1]):
        if value >= num - 0.5:
            return letter
    return "F"


def _trust_band(trust: float) -> str:
    if trust >= 0.7:
        return "high"
    if trust >= 0.4:
        return "medium"
    return "low"


def _percentile_rank(value: float, all_values: list[float]) -> float:
    """Compute percentile rank (0-100) of value within all_values."""
    if not all_values:
        return 0.0
    count_below = sum(1 for v in all_values if v < value)
    return round(count_below / len(all_values) * 100, 1)


# ── Portfolio Benchmark ──────────────────────────────────────────────


async def get_portfolio_benchmark(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioBenchmark:
    """Cross-building benchmarking for all buildings in an organization.

    Computes percentile ranks, KPIs, clusters, worst-first list, and patterns.
    """
    result = await db.execute(select(Building).where(Building.organization_id == org_id))
    buildings = list(result.scalars().all())

    if not buildings:
        return PortfolioBenchmark(
            org_id=org_id,
            kpis=PortfolioKPI(),
            buildings=[],
            worst_first=[],
            clusters=[],
            patterns=[],
        )

    # ── 1. Gather per-building metrics ───────────────────────────────
    building_data: list[dict] = []
    blocker_tracker: dict[str, list[UUID]] = {}  # blocker_title -> [building_ids]
    unknown_tracker: dict[str, list[UUID]] = {}  # unknown_type -> [building_ids]
    proof_gap_tracker: dict[str, list[UUID]] = {}  # gap_desc -> [building_ids]
    buildings_with_blockers = 0
    total_proof_coverage = 0.0

    for building in buildings:
        passport_grade = "F"
        overall_trust = 0.0
        completeness = 0.0
        risk_score = 0.0
        blockers_count = 0
        proof_cov = 0.0

        try:
            from app.services.passport_service import get_passport_summary

            passport = await get_passport_summary(db, building.id)
            if passport:
                passport_grade = passport.get("passport_grade", "F")
                overall_trust = passport.get("knowledge_state", {}).get("overall_trust", 0.0)
                completeness = passport.get("completeness", {}).get("overall_score", 0.0)
                risk_score = round(1.0 - (overall_trust * 0.5 + completeness * 0.5), 2)

                blind_spots = passport.get("blind_spots", {})
                blockers_count = blind_spots.get("blocking", 0)

                # Evidence coverage as proof coverage proxy
                ev = passport.get("evidence_coverage", {})
                covered = sum(1 for v in ev.values() if isinstance(v, int) and v > 0)
                total_keys = max(len(ev), 1)
                proof_cov = covered / total_keys

                # Track pollutant proof gaps
                pollutant_cov = passport.get("pollutant_coverage", {})
                for pollutant, is_covered in pollutant_cov.items():
                    if not is_covered:
                        proof_gap_tracker.setdefault(f"missing_{pollutant}_diagnostic", []).append(building.id)
        except Exception:
            logger.debug("Passport unavailable for building %s", building.id, exc_info=True)

        if blockers_count > 0:
            buildings_with_blockers += 1

        total_proof_coverage += proof_cov

        # Track blockers
        try:
            from app.services.decision_view_service import get_building_decision_view

            dv = await get_building_decision_view(db, building.id)
            if dv and dv.blockers:
                for blocker in dv.blockers:
                    blocker_tracker.setdefault(blocker.title, []).append(building.id)
        except Exception:
            logger.debug("Decision view unavailable for building %s", building.id, exc_info=True)

        # Track unknowns
        try:
            from app.models.unknown_issue import UnknownIssue

            unknown_result = await db.execute(
                select(UnknownIssue).where(
                    UnknownIssue.building_id == building.id,
                    UnknownIssue.status == "open",
                )
            )
            for ui in unknown_result.scalars().all():
                unknown_tracker.setdefault(ui.unknown_type, []).append(building.id)
        except Exception:
            logger.debug("Unknowns unavailable for building %s", building.id, exc_info=True)

        address = f"{building.address}, {building.postal_code} {building.city}"
        building_data.append(
            {
                "id": building.id,
                "address": address,
                "passport_grade": passport_grade,
                "trust_score": overall_trust,
                "completeness": completeness,
                "risk_score": risk_score,
            }
        )

    # ── 2. Compute percentile ranks ─────────────────────────────────
    grade_values = [_grade_to_numeric(d["passport_grade"]) for d in building_data]
    trust_values = [d["trust_score"] for d in building_data]
    completeness_values = [d["completeness"] for d in building_data]
    risk_values = [d["risk_score"] for d in building_data]

    benchmarks: list[BuildingBenchmark] = []
    for d in building_data:
        grade_pct = _percentile_rank(_grade_to_numeric(d["passport_grade"]), grade_values)
        trust_pct = _percentile_rank(d["trust_score"], trust_values)
        completeness_pct = _percentile_rank(d["completeness"], completeness_values)
        # For risk: invert so higher percentile = lower risk (better)
        risk_pct = _percentile_rank(1.0 - d["risk_score"], [1.0 - r for r in risk_values])
        # Urgency: weighted composite (higher = more urgent)
        urgency = round(
            d["risk_score"] * 0.4 + (1.0 - d["trust_score"]) * 0.3 + (1.0 - d["completeness"]) * 0.3,
            3,
        )
        benchmarks.append(
            BuildingBenchmark(
                id=d["id"],
                address=d["address"],
                passport_grade=d["passport_grade"],
                trust_score=d["trust_score"],
                completeness=d["completeness"],
                risk_score=d["risk_score"],
                grade_percentile=grade_pct,
                trust_percentile=trust_pct,
                completeness_percentile=completeness_pct,
                risk_percentile=risk_pct,
                urgency_score=urgency,
            )
        )

    # ── 3. KPIs ──────────────────────────────────────────────────────
    n = len(buildings)
    avg_grade_num = sum(grade_values) / n if n else 0
    kpis = PortfolioKPI(
        avg_grade=_numeric_to_grade(avg_grade_num),
        avg_trust=round(sum(trust_values) / n, 3) if n else 0.0,
        avg_completeness=round(sum(completeness_values) / n, 3) if n else 0.0,
        buildings_with_blockers_pct=round(buildings_with_blockers / n * 100, 1) if n else 0.0,
        proof_coverage_pct=round(total_proof_coverage / n * 100, 1) if n else 0.0,
        total_buildings=n,
    )

    # ── 4. Clusters (same grade + same trust band) ───────────────────
    cluster_map: dict[str, list[BuildingBenchmark]] = {}
    for bm in benchmarks:
        band = _trust_band(bm.trust_score)
        key = f"{bm.passport_grade}/{band}"
        cluster_map.setdefault(key, []).append(bm)

    clusters: list[BuildingCluster] = []
    for key, members in sorted(cluster_map.items(), key=lambda x: -len(x[1])):
        grade, band = key.split("/")
        avg_risk = round(sum(m.risk_score for m in members) / len(members), 3)
        clusters.append(
            BuildingCluster(
                cluster_label=f"Grade-{grade} / Trust-{band}",
                grade=grade,
                trust_band=band,
                building_ids=[m.id for m in members],
                count=len(members),
                avg_risk_score=avg_risk,
            )
        )

    # ── 5. Worst-first list ──────────────────────────────────────────
    worst_first = sorted(benchmarks, key=lambda b: -b.urgency_score)

    # ── 6. Pattern detection ─────────────────────────────────────────
    patterns: list[PortfolioPattern] = []

    # Common blockers (appearing in 2+ buildings)
    for title, bids in sorted(blocker_tracker.items(), key=lambda x: -len(x[1])):
        if len(bids) >= 2:
            patterns.append(
                PortfolioPattern(
                    pattern_type="common_blocker",
                    description=title,
                    affected_building_ids=bids,
                    frequency=len(bids),
                )
            )

    # Recurring unknowns (appearing in 2+ buildings)
    for utype, bids in sorted(unknown_tracker.items(), key=lambda x: -len(x[1])):
        if len(bids) >= 2:
            patterns.append(
                PortfolioPattern(
                    pattern_type="recurring_unknown",
                    description=f"Unknown type: {utype}",
                    affected_building_ids=bids,
                    frequency=len(bids),
                )
            )

    # Shared proof gaps (appearing in 2+ buildings)
    for gap, bids in sorted(proof_gap_tracker.items(), key=lambda x: -len(x[1])):
        if len(bids) >= 2:
            patterns.append(
                PortfolioPattern(
                    pattern_type="shared_proof_gap",
                    description=gap.replace("_", " ").title(),
                    affected_building_ids=bids,
                    frequency=len(bids),
                )
            )

    return PortfolioBenchmark(
        org_id=org_id,
        kpis=kpis,
        buildings=benchmarks,
        worst_first=worst_first,
        clusters=clusters,
        patterns=patterns,
    )


# ── Portfolio Trends ─────────────────────────────────────────────────

_GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}


async def get_portfolio_trends(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioTrends:
    """Compute trend indicators for each building in the org portfolio.

    Compares current passport state against the most recent BuildingSnapshot.
    """
    result = await db.execute(select(Building).where(Building.organization_id == org_id))
    buildings = list(result.scalars().all())

    building_trends: list[BuildingTrend] = []
    improved = 0
    stable = 0
    degraded = 0

    for building in buildings:
        address = f"{building.address}, {building.postal_code} {building.city}"

        # Current state
        current_grade = "F"
        current_trust = 0.0
        try:
            from app.services.passport_service import get_passport_summary

            passport = await get_passport_summary(db, building.id)
            if passport:
                current_grade = passport.get("passport_grade", "F")
                current_trust = passport.get("knowledge_state", {}).get("overall_trust", 0.0)
        except Exception:
            logger.debug("Passport unavailable for building %s", building.id, exc_info=True)

        # Previous state from latest snapshot
        previous_grade: str | None = None
        previous_trust: float | None = None
        snapshot_date: str | None = None

        try:
            snap_result = await db.execute(
                select(BuildingSnapshot)
                .where(BuildingSnapshot.building_id == building.id)
                .order_by(BuildingSnapshot.captured_at.desc())
                .limit(1)
            )
            snap = snap_result.scalar_one_or_none()
            if snap:
                previous_grade = snap.passport_grade
                previous_trust = snap.overall_trust
                snapshot_date = snap.captured_at.isoformat() if snap.captured_at else None
        except Exception:
            logger.debug("Snapshot unavailable for building %s", building.id, exc_info=True)

        # Determine direction
        direction = "stable"
        if previous_grade is not None and previous_trust is not None:
            cur_g = _GRADE_ORDER.get(current_grade, 5)
            prev_g = _GRADE_ORDER.get(previous_grade, 5)
            grade_delta = prev_g - cur_g  # positive = improved
            trust_delta = current_trust - previous_trust

            if grade_delta > 0 or (grade_delta == 0 and trust_delta > 0.05):
                direction = "improved"
            elif grade_delta < 0 or (grade_delta == 0 and trust_delta < -0.05):
                direction = "degraded"

        if direction == "improved":
            improved += 1
        elif direction == "degraded":
            degraded += 1
        else:
            stable += 1

        building_trends.append(
            BuildingTrend(
                id=building.id,
                address=address,
                direction=direction,
                current_grade=current_grade,
                previous_grade=previous_grade,
                current_trust=current_trust,
                previous_trust=previous_trust,
                snapshot_date=snapshot_date,
            )
        )

    # Overall direction
    if improved > degraded:
        overall = "improved"
    elif degraded > improved:
        overall = "degraded"
    else:
        overall = "stable"

    return PortfolioTrends(
        org_id=org_id,
        overall_direction=overall,
        improved_count=improved,
        stable_count=stable,
        degraded_count=degraded,
        buildings=building_trends,
    )
