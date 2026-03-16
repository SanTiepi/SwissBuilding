"""Comprehensive quality assurance service for building data."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.zone import Zone


def _grade_from_score(score: float) -> str:
    """Convert a 0-100 score to a letter grade."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    if score >= 50:
        return "E"
    return "F"


def _check(
    check_id: str,
    category: str,
    name: str,
    status: str,
    detail: str,
    fix_suggestion: str | None = None,
) -> dict:
    return {
        "check_id": check_id,
        "category": category,
        "name": name,
        "status": status,
        "detail": detail,
        "fix_suggestion": fix_suggestion,
    }


async def run_quality_checks(db: AsyncSession, building_id: UUID) -> dict:
    """Run 15+ comprehensive QA checks on a building.

    Categories: structural, temporal, coverage, regulatory.
    Each check: pass/warn/fail + detail + fix suggestion.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    checks: list[dict] = []

    # ── STRUCTURAL checks (model refs valid) ─────────────────────────────

    # S1: Building has EGID
    checks.append(
        _check(
            "S1",
            "structural",
            "EGID present",
            "pass" if building.egid else "warn",
            f"EGID: {building.egid}" if building.egid else "No EGID assigned",
            None if building.egid else "Add the federal building identifier (EGID)",
        )
    )

    # S2: Building has coordinates
    has_coords = building.latitude is not None and building.longitude is not None
    checks.append(
        _check(
            "S2",
            "structural",
            "Coordinates present",
            "pass" if has_coords else "warn",
            "Coordinates available" if has_coords else "Missing lat/lng",
            None if has_coords else "Geocode the building address",
        )
    )

    # S3: Construction year plausible
    if building.construction_year:
        year_ok = 1400 <= building.construction_year <= datetime.now(UTC).year
        checks.append(
            _check(
                "S3",
                "structural",
                "Construction year plausible",
                "pass" if year_ok else "fail",
                f"Year: {building.construction_year}",
                None if year_ok else "Verify construction year — value seems implausible",
            )
        )
    else:
        checks.append(
            _check(
                "S3",
                "structural",
                "Construction year plausible",
                "warn",
                "No construction year",
                "Add construction year for risk assessment accuracy",
            )
        )

    # S4: Surface area present
    checks.append(
        _check(
            "S4",
            "structural",
            "Surface area defined",
            "pass" if building.surface_area_m2 else "warn",
            f"{building.surface_area_m2} m²" if building.surface_area_m2 else "Missing",
            None if building.surface_area_m2 else "Record the building surface area",
        )
    )

    # ── TEMPORAL checks (dates logical) ───────────────────────────────────

    # T1: Diagnostics have inspection dates
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    diags_without_date = [d for d in diagnostics if d.date_inspection is None]
    if diagnostics:
        checks.append(
            _check(
                "T1",
                "temporal",
                "Diagnostic inspection dates",
                "pass" if not diags_without_date else "warn",
                f"{len(diagnostics) - len(diags_without_date)}/{len(diagnostics)} have dates",
                (None if not diags_without_date else "Add inspection dates to all diagnostics"),
            )
        )
    else:
        checks.append(
            _check(
                "T1",
                "temporal",
                "Diagnostic inspection dates",
                "fail",
                "No diagnostics found",
                "Create at least one diagnostic for this building",
            )
        )

    # T2: Renovation year after construction year
    if building.renovation_year and building.construction_year:
        reno_ok = building.renovation_year >= building.construction_year
        checks.append(
            _check(
                "T2",
                "temporal",
                "Renovation after construction",
                "pass" if reno_ok else "fail",
                f"Built {building.construction_year}, renovated {building.renovation_year}",
                None if reno_ok else "Renovation year cannot precede construction year",
            )
        )
    else:
        checks.append(
            _check(
                "T2",
                "temporal",
                "Renovation after construction",
                "pass",
                "No renovation year or no construction year to compare",
            )
        )

    # T3: Diagnostic report date after inspection date
    diags_bad_dates = [
        d for d in diagnostics if d.date_inspection and d.date_report and d.date_report < d.date_inspection
    ]
    checks.append(
        _check(
            "T3",
            "temporal",
            "Report date after inspection",
            "pass" if not diags_bad_dates else "fail",
            (
                f"{len(diags_bad_dates)} diagnostic(s) with report before inspection"
                if diags_bad_dates
                else "All report dates are after inspection dates"
            ),
            ("Fix report/inspection date ordering" if diags_bad_dates else None),
        )
    )

    # T4: Data freshness — most recent diagnostic within 5 years
    if diagnostics:
        recent_dates = [d.date_inspection for d in diagnostics if d.date_inspection]
        if recent_dates:
            most_recent = max(recent_dates)
            five_years_ago = (datetime.now(UTC) - timedelta(days=5 * 365)).date()
            fresh = most_recent >= five_years_ago
            checks.append(
                _check(
                    "T4",
                    "temporal",
                    "Data freshness (< 5 years)",
                    "pass" if fresh else "warn",
                    f"Most recent inspection: {most_recent}",
                    None if fresh else "Consider scheduling a new diagnostic",
                )
            )
        else:
            checks.append(
                _check(
                    "T4",
                    "temporal",
                    "Data freshness (< 5 years)",
                    "warn",
                    "No inspection dates available",
                    "Add inspection dates to diagnostics",
                )
            )
    else:
        checks.append(
            _check(
                "T4",
                "temporal",
                "Data freshness (< 5 years)",
                "fail",
                "No diagnostics",
                "Create a diagnostic",
            )
        )

    # ── COVERAGE checks (zones sampled) ───────────────────────────────────

    # C1: Zones defined
    zone_result = await db.execute(select(func.count()).select_from(Zone).where(Zone.building_id == building_id))
    zone_count = zone_result.scalar() or 0
    checks.append(
        _check(
            "C1",
            "coverage",
            "Zones defined",
            "pass" if zone_count >= 3 else ("warn" if zone_count > 0 else "fail"),
            f"{zone_count} zone(s)",
            None if zone_count >= 3 else "Define building zones for complete coverage",
        )
    )

    # C2: Samples exist for diagnostics
    sample_count_result = await db.execute(
        select(func.count())
        .select_from(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    sample_count = sample_count_result.scalar() or 0
    checks.append(
        _check(
            "C2",
            "coverage",
            "Samples collected",
            "pass" if sample_count >= 5 else ("warn" if sample_count > 0 else "fail"),
            f"{sample_count} sample(s)",
            None if sample_count >= 5 else "Collect more samples for better coverage",
        )
    )

    # C3: Documents uploaded
    doc_count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.building_id == building_id)
    )
    doc_count = doc_count_result.scalar() or 0
    checks.append(
        _check(
            "C3",
            "coverage",
            "Documents uploaded",
            "pass" if doc_count >= 2 else ("warn" if doc_count > 0 else "fail"),
            f"{doc_count} document(s)",
            None if doc_count >= 2 else "Upload supporting documents",
        )
    )

    # C4: Technical plans available
    plan_count_result = await db.execute(
        select(func.count()).select_from(TechnicalPlan).where(TechnicalPlan.building_id == building_id)
    )
    plan_count = plan_count_result.scalar() or 0
    checks.append(
        _check(
            "C4",
            "coverage",
            "Technical plans available",
            "pass" if plan_count >= 1 else "warn",
            f"{plan_count} plan(s)",
            None if plan_count >= 1 else "Upload at least one technical plan",
        )
    )

    # ── REGULATORY checks (thresholds applied correctly) ──────────────────

    # R1: All samples have risk level assigned
    samples_result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    samples = list(samples_result.scalars().all())
    samples_no_risk = [s for s in samples if not s.risk_level]
    if samples:
        checks.append(
            _check(
                "R1",
                "regulatory",
                "Samples have risk levels",
                "pass" if not samples_no_risk else "warn",
                f"{len(samples) - len(samples_no_risk)}/{len(samples)} classified",
                (None if not samples_no_risk else "Assign risk levels to all samples"),
            )
        )
    else:
        checks.append(
            _check(
                "R1",
                "regulatory",
                "Samples have risk levels",
                "warn",
                "No samples to evaluate",
                "Add samples with risk level classification",
            )
        )

    # R2: Actions generated for high-risk samples
    high_risk_samples = [s for s in samples if s.risk_level in ("high", "critical")]
    action_count_result = await db.execute(
        select(func.count()).select_from(ActionItem).where(ActionItem.building_id == building_id)
    )
    action_count = action_count_result.scalar() or 0
    if high_risk_samples:
        checks.append(
            _check(
                "R2",
                "regulatory",
                "Actions for high-risk findings",
                "pass" if action_count >= len(high_risk_samples) else "warn",
                f"{action_count} action(s) for {len(high_risk_samples)} high-risk sample(s)",
                (None if action_count >= len(high_risk_samples) else "Generate actions for all high-risk findings"),
            )
        )
    else:
        checks.append(
            _check(
                "R2",
                "regulatory",
                "Actions for high-risk findings",
                "pass",
                "No high-risk samples",
            )
        )

    # R3: Evidence links exist
    evidence_count_result = await db.execute(
        select(func.count())
        .select_from(EvidenceLink)
        .where(EvidenceLink.source_type == "building")
        .where(EvidenceLink.source_id == building_id)
    )
    evidence_count = evidence_count_result.scalar() or 0
    checks.append(
        _check(
            "R3",
            "regulatory",
            "Evidence chain links",
            "pass" if evidence_count >= 1 else "warn",
            f"{evidence_count} evidence link(s)",
            None if evidence_count >= 1 else "Create evidence links for traceability",
        )
    )

    # R4: Completed diagnostics have conclusions
    completed_no_conclusion = [d for d in diagnostics if d.status == "completed" and not d.conclusion]
    checks.append(
        _check(
            "R4",
            "regulatory",
            "Completed diagnostics have conclusions",
            "pass" if not completed_no_conclusion else "fail",
            (
                f"{len(completed_no_conclusion)} completed without conclusion"
                if completed_no_conclusion
                else "All completed diagnostics have conclusions"
            ),
            ("Add conclusions to completed diagnostics" if completed_no_conclusion else None),
        )
    )

    passed = sum(1 for c in checks if c["status"] == "pass")
    warnings = sum(1 for c in checks if c["status"] == "warn")
    failures = sum(1 for c in checks if c["status"] == "fail")

    return {
        "building_id": building_id,
        "total_checks": len(checks),
        "passed": passed,
        "warnings": warnings,
        "failures": failures,
        "checks": checks,
        "run_at": datetime.now(UTC),
    }


async def get_quality_score(db: AsyncSession, building_id: UUID) -> dict | None:
    """Compute a weighted quality score 0-100 with sub-scores and grade."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    # ── data_completeness (30%) ───────────────────────────────────────────
    completeness_points = 0
    completeness_max = 7
    if building.egid:
        completeness_points += 1
    if building.address:
        completeness_points += 1
    if building.construction_year:
        completeness_points += 1
    if building.latitude and building.longitude:
        completeness_points += 1
    if building.surface_area_m2:
        completeness_points += 1

    diag_count_r = await db.execute(
        select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id)
    )
    diag_count = diag_count_r.scalar() or 0
    if diag_count >= 1:
        completeness_points += 1
    zone_count_r = await db.execute(select(func.count()).select_from(Zone).where(Zone.building_id == building_id))
    zone_count = zone_count_r.scalar() or 0
    if zone_count >= 1:
        completeness_points += 1

    completeness_score = round(completeness_points / completeness_max * 100, 1)

    # ── data_consistency (25%) ────────────────────────────────────────────
    consistency_checks = 0
    consistency_total = 4

    # Construction year plausible
    if building.construction_year and 1400 <= building.construction_year <= datetime.now(UTC).year:
        consistency_checks += 1
    elif not building.construction_year:
        consistency_checks += 1  # no data = no inconsistency

    # Renovation after construction
    if building.renovation_year and building.construction_year:
        if building.renovation_year >= building.construction_year:
            consistency_checks += 1
    else:
        consistency_checks += 1

    # Diagnostic dates logical
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    bad_dates = [d for d in diagnostics if d.date_inspection and d.date_report and d.date_report < d.date_inspection]
    if not bad_dates:
        consistency_checks += 1

    # Completed diags have conclusions
    incomplete_conclusions = [d for d in diagnostics if d.status == "completed" and not d.conclusion]
    if not incomplete_conclusions:
        consistency_checks += 1

    consistency_score = round(consistency_checks / consistency_total * 100, 1)

    # ── data_freshness (20%) ──────────────────────────────────────────────
    freshness_score = 0.0
    if diagnostics:
        recent_dates = [d.date_inspection for d in diagnostics if d.date_inspection]
        if recent_dates:
            most_recent = max(recent_dates)
            days_old = (datetime.now(UTC).date() - most_recent).days
            if days_old <= 365:
                freshness_score = 100.0
            elif days_old <= 365 * 3:
                freshness_score = 70.0
            elif days_old <= 365 * 5:
                freshness_score = 40.0
            else:
                freshness_score = 10.0
        else:
            freshness_score = 20.0
    else:
        freshness_score = 0.0

    # ── regulatory_compliance (15%) ───────────────────────────────────────
    reg_points = 0
    reg_total = 3

    sample_r = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    samples = list(sample_r.scalars().all())
    # All samples have risk levels
    if (samples and all(s.risk_level for s in samples)) or not samples:
        reg_points += 1

    # Actions exist for high-risk
    high_risk = [s for s in samples if s.risk_level in ("high", "critical")]
    action_r = await db.execute(
        select(func.count()).select_from(ActionItem).where(ActionItem.building_id == building_id)
    )
    action_count = action_r.scalar() or 0
    if not high_risk or action_count >= len(high_risk):
        reg_points += 1

    # At least one completed diagnostic
    completed = [d for d in diagnostics if d.status == "completed"]
    if completed:
        reg_points += 1

    regulatory_score = round(reg_points / reg_total * 100, 1)

    # ── documentation (10%) ───────────────────────────────────────────────
    doc_points = 0
    doc_total = 3

    doc_r = await db.execute(select(func.count()).select_from(Document).where(Document.building_id == building_id))
    doc_count = doc_r.scalar() or 0
    if doc_count >= 1:
        doc_points += 1

    plan_r = await db.execute(
        select(func.count()).select_from(TechnicalPlan).where(TechnicalPlan.building_id == building_id)
    )
    plan_count = plan_r.scalar() or 0
    if plan_count >= 1:
        doc_points += 1

    ev_r = await db.execute(
        select(func.count())
        .select_from(EvidenceLink)
        .where(EvidenceLink.source_type == "building")
        .where(EvidenceLink.source_id == building_id)
    )
    ev_count = ev_r.scalar() or 0
    if ev_count >= 1:
        doc_points += 1

    documentation_score = round(doc_points / doc_total * 100, 1)

    # ── Overall weighted score ────────────────────────────────────────────
    weights = {
        "data_completeness": 0.30,
        "data_consistency": 0.25,
        "data_freshness": 0.20,
        "regulatory_compliance": 0.15,
        "documentation": 0.10,
    }
    scores = {
        "data_completeness": completeness_score,
        "data_consistency": consistency_score,
        "data_freshness": freshness_score,
        "regulatory_compliance": regulatory_score,
        "documentation": documentation_score,
    }
    overall = round(sum(scores[k] * weights[k] for k in weights), 1)

    sub_scores = [
        {
            "name": k,
            "score": scores[k],
            "weight": weights[k],
            "grade": _grade_from_score(scores[k]),
            "detail": f"{scores[k]}/100",
        }
        for k in weights
    ]

    return {
        "building_id": building_id,
        "overall_score": overall,
        "grade": _grade_from_score(overall),
        "sub_scores": sub_scores,
        "computed_at": datetime.now(UTC),
    }


async def get_quality_trends(db: AsyncSession, building_id: UUID) -> dict | None:
    """Compute quality score history simulated from data timestamps."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    # Gather timestamped events that affect quality
    events: list[tuple[datetime, str, float]] = []

    # Building creation
    if building.created_at:
        events.append((building.created_at, "Building created", 20.0))

    # Diagnostics
    diag_r = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    for d in diag_r.scalars().all():
        ts = d.created_at or building.created_at
        if ts:
            events.append((ts, f"Diagnostic added ({d.diagnostic_type})", 10.0))
        if d.status == "completed" and d.updated_at:
            events.append((d.updated_at, "Diagnostic completed", 5.0))

    # Zones
    zone_r = await db.execute(select(Zone).where(Zone.building_id == building_id))
    for z in zone_r.scalars().all():
        ts = z.created_at if hasattr(z, "created_at") and z.created_at else building.created_at
        if ts:
            events.append((ts, "Zone defined", 3.0))

    # Documents
    doc_r = await db.execute(select(Document).where(Document.building_id == building_id))
    for doc in doc_r.scalars().all():
        ts = doc.created_at or building.created_at
        if ts:
            events.append((ts, "Document uploaded", 4.0))

    # Interventions
    int_r = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    for interv in int_r.scalars().all():
        ts = interv.created_at if hasattr(interv, "created_at") and interv.created_at else building.created_at
        if ts:
            events.append((ts, f"Intervention recorded ({interv.intervention_type})", 5.0))

    # Sort by timestamp
    events.sort(key=lambda e: e[0])

    # Build cumulative trend
    trend_points: list[dict] = []
    cumulative = 0.0
    max_score = 100.0

    for ts, event_desc, delta in events:
        cumulative = min(max_score, cumulative + delta)
        date_str = ts.strftime("%Y-%m-%d") if ts else "unknown"
        trend_points.append({"date": date_str, "score": round(cumulative, 1), "event": event_desc})

    # Determine trajectory
    current_score = cumulative
    if len(trend_points) >= 2:
        mid = len(trend_points) // 2
        first_half_avg = sum(p["score"] for p in trend_points[:mid]) / mid
        second_half_avg = sum(p["score"] for p in trend_points[mid:]) / (len(trend_points) - mid)
        if second_half_avg > first_half_avg + 5:
            trajectory = "improving"
        elif second_half_avg < first_half_avg - 5:
            trajectory = "declining"
        else:
            trajectory = "stable"
    else:
        trajectory = "stable"

    return {
        "building_id": building_id,
        "current_score": current_score,
        "trajectory": trajectory,
        "trend_points": trend_points,
    }


async def get_portfolio_quality_report(db: AsyncSession, org_id: UUID) -> dict | None:
    """Organisation-level quality report across all buildings."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return {
            "organization_id": org_id,
            "total_buildings": 0,
            "average_score": 0.0,
            "average_grade": "F",
            "score_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0},
            "worst_buildings": [],
            "common_issues": [],
            "recommendations": [],
        }

    # Compute scores for each building
    scored_buildings: list[dict] = []
    issue_counter: dict[str, int] = {}
    distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}

    for b in buildings:
        score_data = await get_quality_score(db, b.id)
        if not score_data:
            continue
        score = score_data["overall_score"]
        grade = score_data["grade"]
        distribution[grade] = distribution.get(grade, 0) + 1

        scored_buildings.append(
            {
                "building_id": b.id,
                "address": b.address,
                "score": score,
                "grade": grade,
            }
        )

        # Track common issues from sub-scores
        for sub in score_data["sub_scores"]:
            if sub["score"] < 50:
                label = f"Low {sub['name'].replace('_', ' ')}"
                issue_counter[label] = issue_counter.get(label, 0) + 1

    total = len(scored_buildings)
    avg_score = round(sum(b["score"] for b in scored_buildings) / total, 1) if total else 0.0
    avg_grade = _grade_from_score(avg_score)

    # Worst buildings (lowest score, up to 5)
    sorted_buildings = sorted(scored_buildings, key=lambda x: x["score"])
    worst = sorted_buildings[:5]

    # Common issues ranked by count
    common_issues = [
        {"issue": k, "count": v, "impact": "high" if v > total * 0.5 else "medium"}
        for k, v in sorted(issue_counter.items(), key=lambda x: -x[1])
    ][:5]

    # Recommendations
    recommendations: list[dict] = []
    if issue_counter:
        for issue, count in sorted(issue_counter.items(), key=lambda x: -x[1])[:3]:
            recommendations.append(
                {
                    "recommendation": f"Improve {issue.lower()} across the portfolio",
                    "impact_score": round(count / total * 100, 1) if total else 0.0,
                    "affected_buildings": count,
                }
            )

    return {
        "organization_id": org_id,
        "total_buildings": total,
        "average_score": avg_score,
        "average_grade": avg_grade,
        "score_distribution": distribution,
        "worst_buildings": worst,
        "common_issues": common_issues,
        "recommendations": recommendations,
    }
