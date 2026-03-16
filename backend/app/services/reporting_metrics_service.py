"""
SwissBuildingOS - Reporting Metrics Service

Provides KPI dashboards, operational metrics, periodic structured reports,
and benchmark comparisons at the organization level. Metrics are computed
from diagnostics, samples, interventions, actions, and documents.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.schemas.reporting_metrics import (
    BenchmarkComparison,
    BenchmarkMetric,
    KPIDashboard,
    OperationalMetrics,
    PeriodicReport,
    TrendValue,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PERIOD_DAYS = {
    "monthly": 30,
    "quarterly": 90,
    "annual": 365,
}


async def _verify_org(db: AsyncSession, org_id: UUID) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise ValueError(f"Organization {org_id} not found")
    return org


async def _org_building_ids(db: AsyncSession, org_id: UUID) -> list[UUID]:
    buildings = await load_org_buildings(db, org_id)
    return [b.id for b in buildings]


def _trend(current: float, previous: float) -> TrendValue:
    if previous > 0:
        change = ((current - previous) / previous) * 100.0
    elif current > 0:
        change = 100.0
    else:
        change = 0.0

    if change > 1.0:
        direction = "up"
    elif change < -1.0:
        direction = "down"
    else:
        direction = "stable"

    return TrendValue(
        current=round(current, 2),
        previous=round(previous, 2),
        change_pct=round(change, 2),
        direction=direction,
    )


def _percentile(org_value: float, all_values: list[float]) -> float:
    """Compute the percentile rank of org_value within all_values."""
    if not all_values:
        return 50.0
    below = sum(1 for v in all_values if v < org_value)
    equal = sum(1 for v in all_values if v == org_value)
    return round((below + equal * 0.5) / len(all_values) * 100.0, 1)


# ---------------------------------------------------------------------------
# FN1 — KPI Dashboard
# ---------------------------------------------------------------------------


async def get_kpi_dashboard(db: AsyncSession, org_id: UUID) -> KPIDashboard:
    """Key performance indicators with trend vs previous period (30 days)."""
    await _verify_org(db, org_id)
    building_ids = await _org_building_ids(db, org_id)

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=30)

    total_buildings = len(building_ids)

    if not building_ids:
        empty_trend = TrendValue()
        return KPIDashboard(
            organization_id=org_id,
            buildings_assessed_pct=empty_trend,
            compliance_rate_pct=empty_trend,
            avg_risk_score=empty_trend,
            avg_quality_score=empty_trend,
            remediation_progress_pct=empty_trend,
            active_interventions_count=empty_trend,
            total_estimated_chf=0.0,
            total_spent_chf=0.0,
            generated_at=now,
        )

    # Buildings assessed = buildings with at least one completed/validated diagnostic
    assessed_stmt = select(func.count(func.distinct(Diagnostic.building_id))).where(
        Diagnostic.building_id.in_(building_ids),
        Diagnostic.status.in_(["completed", "validated"]),
    )
    assessed_result = await db.execute(assessed_stmt)
    assessed_count = assessed_result.scalar() or 0

    # Previous period assessed
    prev_assessed_stmt = select(func.count(func.distinct(Diagnostic.building_id))).where(
        Diagnostic.building_id.in_(building_ids),
        Diagnostic.status.in_(["completed", "validated"]),
        Diagnostic.created_at < cutoff,
    )
    prev_assessed_result = await db.execute(prev_assessed_stmt)
    prev_assessed = prev_assessed_result.scalar() or 0

    assessed_pct = (assessed_count / total_buildings * 100) if total_buildings > 0 else 0
    prev_assessed_pct = (prev_assessed / total_buildings * 100) if total_buildings > 0 else 0

    # Compliance: buildings with no threshold_exceeded samples (among assessed)
    non_compliant_stmt = (
        select(func.count(func.distinct(Diagnostic.building_id)))
        .join(Sample, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id.in_(building_ids),
            Diagnostic.status.in_(["completed", "validated"]),
            Sample.threshold_exceeded.is_(True),
        )
    )
    non_compliant_result = await db.execute(non_compliant_stmt)
    non_compliant = non_compliant_result.scalar() or 0
    compliant = max(assessed_count - non_compliant, 0)
    compliance_pct = (compliant / assessed_count * 100) if assessed_count > 0 else 0

    # Risk scores
    risk_stmt = select(
        func.avg(
            (
                BuildingRiskScore.asbestos_probability
                + BuildingRiskScore.pcb_probability
                + BuildingRiskScore.lead_probability
                + BuildingRiskScore.hap_probability
                + BuildingRiskScore.radon_probability
            )
            / 5.0
        )
    ).where(BuildingRiskScore.building_id.in_(building_ids))
    risk_result = await db.execute(risk_stmt)
    avg_risk = risk_result.scalar() or 0.0

    # Quality score: use action completion as proxy
    total_actions_stmt = select(func.count(ActionItem.id)).where(ActionItem.building_id.in_(building_ids))
    total_actions_result = await db.execute(total_actions_stmt)
    total_actions = total_actions_result.scalar() or 0

    completed_actions_stmt = select(func.count(ActionItem.id)).where(
        ActionItem.building_id.in_(building_ids), ActionItem.status == "completed"
    )
    completed_actions_result = await db.execute(completed_actions_stmt)
    completed_actions = completed_actions_result.scalar() or 0

    quality_score = (completed_actions / total_actions * 100) if total_actions > 0 else 0

    # Remediation progress: completed interventions / total
    total_interv_stmt = select(func.count(Intervention.id)).where(Intervention.building_id.in_(building_ids))
    total_interv_result = await db.execute(total_interv_stmt)
    total_interv = total_interv_result.scalar() or 0

    completed_interv_stmt = select(func.count(Intervention.id)).where(
        Intervention.building_id.in_(building_ids), Intervention.status == "completed"
    )
    completed_interv_result = await db.execute(completed_interv_stmt)
    completed_interv = completed_interv_result.scalar() or 0

    remediation_pct = (completed_interv / total_interv * 100) if total_interv > 0 else 0

    # Active interventions
    active_interv_stmt = select(func.count(Intervention.id)).where(
        Intervention.building_id.in_(building_ids), Intervention.status == "in_progress"
    )
    active_interv_result = await db.execute(active_interv_stmt)
    active_interv = active_interv_result.scalar() or 0

    # Budget
    spent_stmt = select(func.coalesce(func.sum(Intervention.cost_chf), 0.0)).where(
        Intervention.building_id.in_(building_ids), Intervention.status == "completed"
    )
    spent_result = await db.execute(spent_stmt)
    total_spent = spent_result.scalar() or 0.0

    estimated_stmt = select(func.coalesce(func.sum(Intervention.cost_chf), 0.0)).where(
        Intervention.building_id.in_(building_ids)
    )
    estimated_result = await db.execute(estimated_stmt)
    total_estimated = estimated_result.scalar() or 0.0

    return KPIDashboard(
        organization_id=org_id,
        buildings_assessed_pct=_trend(assessed_pct, prev_assessed_pct),
        compliance_rate_pct=_trend(compliance_pct, compliance_pct),
        avg_risk_score=_trend(avg_risk, avg_risk),
        avg_quality_score=_trend(quality_score, quality_score),
        remediation_progress_pct=_trend(remediation_pct, remediation_pct),
        active_interventions_count=_trend(float(active_interv), float(active_interv)),
        total_estimated_chf=round(total_estimated, 2),
        total_spent_chf=round(total_spent, 2),
        generated_at=now,
    )


# ---------------------------------------------------------------------------
# FN2 — Operational Metrics
# ---------------------------------------------------------------------------


async def get_operational_metrics(db: AsyncSession, org_id: UUID) -> OperationalMetrics:
    """Operational stats: diagnostic speed, sample throughput, action completion."""
    await _verify_org(db, org_id)
    building_ids = await _org_building_ids(db, org_id)

    now = datetime.now(UTC)

    if not building_ids:
        return OperationalMetrics(organization_id=org_id, generated_at=now)

    # Avg diagnostic completion time (days between created_at and date_report)
    diag_stmt = select(Diagnostic).where(
        Diagnostic.building_id.in_(building_ids),
        Diagnostic.status.in_(["completed", "validated"]),
        Diagnostic.date_report.isnot(None),
    )
    diag_result = await db.execute(diag_stmt)
    diagnostics = diag_result.scalars().all()

    completion_days: list[float] = []
    for d in diagnostics:
        if d.created_at and d.date_report:
            created_date = d.created_at.date() if isinstance(d.created_at, datetime) else d.created_at
            delta = (d.date_report - created_date).days
            if delta >= 0:
                completion_days.append(float(delta))

    avg_completion = sum(completion_days) / len(completion_days) if completion_days else 0.0

    # Avg time from diagnostic to remediation
    diag_to_remed_days: list[float] = []
    for d in diagnostics:
        if d.date_report:
            interv_stmt = (
                select(Intervention.date_start)
                .where(
                    Intervention.building_id == d.building_id,
                    Intervention.intervention_type.in_(["remediation", "removal", "encapsulation"]),
                    Intervention.date_start.isnot(None),
                )
                .order_by(Intervention.date_start)
                .limit(1)
            )
            interv_result = await db.execute(interv_stmt)
            first_interv = interv_result.scalar_one_or_none()
            if first_interv:
                delta = (first_interv - d.date_report).days
                if delta >= 0:
                    diag_to_remed_days.append(float(delta))

    avg_diag_to_remed = sum(diag_to_remed_days) / len(diag_to_remed_days) if diag_to_remed_days else 0.0

    # Sample throughput per month
    total_samples_stmt = select(func.count(Sample.id)).join(Diagnostic).where(Diagnostic.building_id.in_(building_ids))
    total_samples_result = await db.execute(total_samples_stmt)
    total_samples = total_samples_result.scalar() or 0

    # Estimate months of activity
    oldest_diag_stmt = select(func.min(Diagnostic.created_at)).where(Diagnostic.building_id.in_(building_ids))
    oldest_result = await db.execute(oldest_diag_stmt)
    oldest_date = oldest_result.scalar()

    if oldest_date and total_samples > 0:
        if isinstance(oldest_date, datetime):
            # Normalize timezone: make both aware or both naive
            if oldest_date.tzinfo is None:
                oldest_aware = oldest_date.replace(tzinfo=UTC)
            else:
                oldest_aware = oldest_date
            months_active = max((now - oldest_aware).days / 30.0, 1.0)
        else:
            months_active = max((now.date() - oldest_date).days / 30.0, 1.0)
        sample_throughput = total_samples / months_active
    else:
        sample_throughput = 0.0

    # Document upload rate
    total_docs_stmt = select(func.count(Document.id)).where(Document.building_id.in_(building_ids))
    total_docs_result = await db.execute(total_docs_stmt)
    total_docs = total_docs_result.scalar() or 0

    if oldest_date and total_docs > 0:
        doc_rate = total_docs / max(months_active, 1.0)
    else:
        doc_rate = 0.0
        months_active = 1.0

    # Action completion rate
    total_actions_stmt = select(func.count(ActionItem.id)).where(ActionItem.building_id.in_(building_ids))
    total_actions_result = await db.execute(total_actions_stmt)
    total_actions = total_actions_result.scalar() or 0

    completed_actions_stmt = select(func.count(ActionItem.id)).where(
        ActionItem.building_id.in_(building_ids), ActionItem.status == "completed"
    )
    completed_actions_result = await db.execute(completed_actions_stmt)
    completed_actions = completed_actions_result.scalar() or 0

    action_rate = (completed_actions / total_actions * 100) if total_actions > 0 else 0.0

    # Total diagnostics
    total_diag_stmt = select(func.count(Diagnostic.id)).where(Diagnostic.building_id.in_(building_ids))
    total_diag_result = await db.execute(total_diag_stmt)
    total_diag = total_diag_result.scalar() or 0

    return OperationalMetrics(
        organization_id=org_id,
        avg_diagnostic_completion_days=round(avg_completion, 1),
        avg_diagnostic_to_remediation_days=round(avg_diag_to_remed, 1),
        sample_throughput_per_month=round(sample_throughput, 1),
        document_upload_rate_per_month=round(doc_rate, 1),
        action_completion_rate_pct=round(action_rate, 1),
        total_diagnostics=total_diag,
        total_samples=total_samples,
        total_documents=total_docs,
        total_actions=total_actions,
        generated_at=now,
    )


# ---------------------------------------------------------------------------
# FN3 — Periodic Report
# ---------------------------------------------------------------------------


async def generate_periodic_report(db: AsyncSession, org_id: UUID, period: str = "monthly") -> PeriodicReport:
    """Generate structured report data for monthly/quarterly/annual period."""
    await _verify_org(db, org_id)
    building_ids = await _org_building_ids(db, org_id)

    now = datetime.now(UTC)
    days = _PERIOD_DAYS.get(period, 30)
    period_start = now - timedelta(days=days)
    period_end = now

    if not building_ids:
        return PeriodicReport(
            organization_id=org_id,
            period=period,
            period_start=period_start,
            period_end=period_end,
            summary=f"No buildings found for this organization in the {period} period.",
            generated_at=now,
        )

    total_buildings = len(building_ids)

    # New diagnostics in period
    new_diag_stmt = select(func.count(Diagnostic.id)).where(
        Diagnostic.building_id.in_(building_ids),
        Diagnostic.created_at >= period_start,
    )
    new_diag_result = await db.execute(new_diag_stmt)
    new_diagnostics = new_diag_result.scalar() or 0

    # Completed diagnostics in period
    completed_diag_stmt = select(func.count(Diagnostic.id)).where(
        Diagnostic.building_id.in_(building_ids),
        Diagnostic.status.in_(["completed", "validated"]),
        Diagnostic.created_at >= period_start,
    )
    completed_diag_result = await db.execute(completed_diag_stmt)
    completed_diagnostics = completed_diag_result.scalar() or 0

    # New risks identified: samples with threshold_exceeded created in period
    new_risks_stmt = (
        select(func.count(Sample.id))
        .join(Diagnostic)
        .where(
            Diagnostic.building_id.in_(building_ids),
            Sample.threshold_exceeded.is_(True),
            Sample.created_at >= period_start,
        )
    )
    new_risks_result = await db.execute(new_risks_stmt)
    new_risks = new_risks_result.scalar() or 0

    # High risk buildings
    high_risk_stmt = select(func.count(BuildingRiskScore.id)).where(
        BuildingRiskScore.building_id.in_(building_ids),
        BuildingRiskScore.overall_risk_level.in_(["high", "critical"]),
    )
    high_risk_result = await db.execute(high_risk_stmt)
    high_risk_buildings = high_risk_result.scalar() or 0

    # Interventions
    completed_interv_stmt = select(func.count(Intervention.id)).where(
        Intervention.building_id.in_(building_ids),
        Intervention.status == "completed",
        Intervention.created_at >= period_start,
    )
    completed_interv_result = await db.execute(completed_interv_stmt)
    interventions_completed = completed_interv_result.scalar() or 0

    in_progress_interv_stmt = select(func.count(Intervention.id)).where(
        Intervention.building_id.in_(building_ids),
        Intervention.status == "in_progress",
    )
    in_progress_result = await db.execute(in_progress_interv_stmt)
    interventions_in_progress = in_progress_result.scalar() or 0

    total_interv_stmt = select(func.count(Intervention.id)).where(Intervention.building_id.in_(building_ids))
    total_interv_result = await db.execute(total_interv_stmt)
    total_interv = total_interv_result.scalar() or 0

    all_completed_interv_stmt = select(func.count(Intervention.id)).where(
        Intervention.building_id.in_(building_ids), Intervention.status == "completed"
    )
    all_completed_result = await db.execute(all_completed_interv_stmt)
    all_completed_interv = all_completed_result.scalar() or 0

    remediation_pct = (all_completed_interv / total_interv * 100) if total_interv > 0 else 0.0

    # Compliance improvements: actions completed in period
    compliance_improvements_stmt = select(func.count(ActionItem.id)).where(
        ActionItem.building_id.in_(building_ids),
        ActionItem.status == "completed",
        ActionItem.completed_at >= period_start,
    )
    compliance_result = await db.execute(compliance_improvements_stmt)
    compliance_improvements = compliance_result.scalar() or 0

    # Budget
    spent_stmt = select(func.coalesce(func.sum(Intervention.cost_chf), 0.0)).where(
        Intervention.building_id.in_(building_ids), Intervention.status == "completed"
    )
    spent_result = await db.execute(spent_stmt)
    budget_spent = spent_result.scalar() or 0.0

    estimated_stmt = select(func.coalesce(func.sum(Intervention.cost_chf), 0.0)).where(
        Intervention.building_id.in_(building_ids)
    )
    estimated_result = await db.execute(estimated_stmt)
    budget_estimated = estimated_result.scalar() or 0.0

    budget_util = (budget_spent / budget_estimated * 100) if budget_estimated > 0 else 0.0

    # Key changes
    key_changes: list[str] = []
    if new_diagnostics > 0:
        key_changes.append(f"{new_diagnostics} new diagnostic(s) initiated")
    if interventions_completed > 0:
        key_changes.append(f"{interventions_completed} intervention(s) completed")
    if new_risks > 0:
        key_changes.append(f"{new_risks} new risk(s) identified from samples")
    if compliance_improvements > 0:
        key_changes.append(f"{compliance_improvements} action(s) completed")

    summary = (
        f"{period.capitalize()} report for {total_buildings} building(s): "
        f"{new_diagnostics} new diagnostics, {interventions_completed} interventions completed, "
        f"remediation at {remediation_pct:.0f}%."
    )

    return PeriodicReport(
        organization_id=org_id,
        period=period,
        period_start=period_start,
        period_end=period_end,
        summary=summary,
        buildings_count=total_buildings,
        new_diagnostics=new_diagnostics,
        completed_diagnostics=completed_diagnostics,
        new_risks_identified=new_risks,
        high_risk_buildings=high_risk_buildings,
        remediation_progress_pct=round(remediation_pct, 1),
        interventions_completed=interventions_completed,
        interventions_in_progress=interventions_in_progress,
        compliance_improvements=compliance_improvements,
        budget_estimated_chf=round(budget_estimated, 2),
        budget_spent_chf=round(budget_spent, 2),
        budget_utilization_pct=round(budget_util, 1),
        key_changes=key_changes,
        generated_at=now,
    )


# ---------------------------------------------------------------------------
# FN4 — Benchmark Comparison
# ---------------------------------------------------------------------------


async def get_benchmark_comparison(db: AsyncSession, org_id: UUID) -> BenchmarkComparison:
    """Compare this org to system-wide averages with percentile ranking."""
    await _verify_org(db, org_id)

    now = datetime.now(UTC)

    # Gather all orgs for system-wide comparison
    all_orgs_stmt = select(Organization.id)
    all_orgs_result = await db.execute(all_orgs_stmt)
    all_org_ids = [row[0] for row in all_orgs_result.all()]

    # Compute per-org metrics for benchmarking
    org_compliance_rates: dict[UUID, float] = {}
    org_risk_scores: dict[UUID, float] = {}
    org_quality_scores: dict[UUID, float] = {}
    org_diag_speeds: dict[UUID, float] = {}
    org_action_rates: dict[UUID, float] = {}

    for oid in all_org_ids:
        o_buildings = await load_org_buildings(db, oid)
        if not o_buildings:
            continue

        o_bldg_ids = [b.id for b in o_buildings]
        if not o_bldg_ids:
            continue

        # Compliance rate
        assessed_stmt = select(func.count(func.distinct(Diagnostic.building_id))).where(
            Diagnostic.building_id.in_(o_bldg_ids),
            Diagnostic.status.in_(["completed", "validated"]),
        )
        assessed_r = await db.execute(assessed_stmt)
        assessed = assessed_r.scalar() or 0

        if assessed > 0:
            nc_stmt = (
                select(func.count(func.distinct(Diagnostic.building_id)))
                .join(Sample, Sample.diagnostic_id == Diagnostic.id)
                .where(
                    Diagnostic.building_id.in_(o_bldg_ids),
                    Diagnostic.status.in_(["completed", "validated"]),
                    Sample.threshold_exceeded.is_(True),
                )
            )
            nc_r = await db.execute(nc_stmt)
            nc = nc_r.scalar() or 0
            org_compliance_rates[oid] = max(assessed - nc, 0) / assessed * 100
        else:
            org_compliance_rates[oid] = 0.0

        # Risk score
        risk_stmt = select(
            func.avg(
                (
                    BuildingRiskScore.asbestos_probability
                    + BuildingRiskScore.pcb_probability
                    + BuildingRiskScore.lead_probability
                    + BuildingRiskScore.hap_probability
                    + BuildingRiskScore.radon_probability
                )
                / 5.0
            )
        ).where(BuildingRiskScore.building_id.in_(o_bldg_ids))
        risk_r = await db.execute(risk_stmt)
        org_risk_scores[oid] = risk_r.scalar() or 0.0

        # Quality (action completion)
        ta_stmt = select(func.count(ActionItem.id)).where(ActionItem.building_id.in_(o_bldg_ids))
        ta_r = await db.execute(ta_stmt)
        ta = ta_r.scalar() or 0
        ca_stmt = select(func.count(ActionItem.id)).where(
            ActionItem.building_id.in_(o_bldg_ids), ActionItem.status == "completed"
        )
        ca_r = await db.execute(ca_stmt)
        ca = ca_r.scalar() or 0
        org_quality_scores[oid] = (ca / ta * 100) if ta > 0 else 0.0

        # Diagnostic speed
        diag_stmt = select(Diagnostic).where(
            Diagnostic.building_id.in_(o_bldg_ids),
            Diagnostic.status.in_(["completed", "validated"]),
            Diagnostic.date_report.isnot(None),
        )
        diag_r = await db.execute(diag_stmt)
        diags = diag_r.scalars().all()
        speeds: list[float] = []
        for d in diags:
            if d.created_at and d.date_report:
                cd = d.created_at.date() if isinstance(d.created_at, datetime) else d.created_at
                delta = (d.date_report - cd).days
                if delta >= 0:
                    speeds.append(float(delta))
        org_diag_speeds[oid] = sum(speeds) / len(speeds) if speeds else 0.0

        # Action completion rate
        org_action_rates[oid] = org_quality_scores[oid]

    # Org's own values
    my_compliance = org_compliance_rates.get(org_id, 0.0)
    my_risk = org_risk_scores.get(org_id, 0.0)
    my_quality = org_quality_scores.get(org_id, 0.0)
    my_speed = org_diag_speeds.get(org_id, 0.0)
    my_action_rate = org_action_rates.get(org_id, 0.0)

    all_compliance = list(org_compliance_rates.values())
    all_risk = list(org_risk_scores.values())
    all_quality = list(org_quality_scores.values())
    all_speed = list(org_diag_speeds.values())
    all_action = list(org_action_rates.values())

    sys_avg_compliance = sum(all_compliance) / len(all_compliance) if all_compliance else 0.0
    sys_avg_risk = sum(all_risk) / len(all_risk) if all_risk else 0.0
    sys_avg_quality = sum(all_quality) / len(all_quality) if all_quality else 0.0
    sys_avg_speed = sum(all_speed) / len(all_speed) if all_speed else 0.0
    sys_avg_action = sum(all_action) / len(all_action) if all_action else 0.0

    def _make_metric(name: str, org_val: float, sys_avg: float, all_vals: list[float]) -> BenchmarkMetric:
        return BenchmarkMetric(
            metric_name=name,
            org_value=round(org_val, 2),
            system_avg=round(sys_avg, 2),
            difference=round(org_val - sys_avg, 2),
            percentile=_percentile(org_val, all_vals),
            is_above_avg=org_val > sys_avg,
        )

    compliance_metric = _make_metric("compliance_rate", my_compliance, sys_avg_compliance, all_compliance)
    risk_metric = _make_metric("avg_risk_score", my_risk, sys_avg_risk, all_risk)
    quality_metric = _make_metric("avg_quality_score", my_quality, sys_avg_quality, all_quality)
    speed_metric = _make_metric("avg_diagnostic_speed_days", my_speed, sys_avg_speed, all_speed)
    action_metric = _make_metric("action_completion_rate", my_action_rate, sys_avg_action, all_action)

    overall = (compliance_metric.percentile + quality_metric.percentile + action_metric.percentile) / 3.0

    return BenchmarkComparison(
        organization_id=org_id,
        compliance_rate=compliance_metric,
        avg_risk_score=risk_metric,
        avg_quality_score=quality_metric,
        avg_diagnostic_speed_days=speed_metric,
        action_completion_rate=action_metric,
        overall_percentile=round(overall, 1),
        generated_at=now,
    )
