from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building_risk_score import BuildingRiskScore
from app.models.organization import Organization
from app.schemas.multi_org_dashboard import (
    MultiOrgComparison,
    MultiOrgDashboard,
    OrgComparisonItem,
    OrgSummary,
)
from app.services.building_data_loader import load_org_buildings

AVAILABLE_METRICS = ["building_count", "completeness_avg", "actions_pending", "actions_critical"]


async def _get_org_summary(db: AsyncSession, org: Organization) -> OrgSummary:
    """Build an OrgSummary for a single organization."""
    org_id = org.id

    # Buildings belonging to users in this org (active only)
    all_buildings = await load_org_buildings(db, org_id)
    active_buildings = [b for b in all_buildings if b.status == "active"]
    active_building_ids = [b.id for b in active_buildings]

    # Building count
    building_count = len(active_buildings)

    # Risk distribution
    risk_result = await db.execute(
        select(BuildingRiskScore.overall_risk_level, func.count())
        .where(BuildingRiskScore.building_id.in_(active_building_ids))
        .group_by(BuildingRiskScore.overall_risk_level)
    )
    risk_distribution: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for level, count in risk_result.all():
        if level in risk_distribution:
            risk_distribution[level] = count

    # Completeness average (confidence as proxy)
    comp_result = await db.execute(
        select(func.avg(BuildingRiskScore.confidence)).where(BuildingRiskScore.building_id.in_(active_building_ids))
    )
    completeness_avg = round(float(comp_result.scalar() or 0.0), 2)

    # Actions pending
    pending_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            ActionItem.building_id.in_(active_building_ids),
            ActionItem.status.in_(["open", "in_progress"]),
        )
    )
    actions_pending = pending_result.scalar() or 0

    # Actions critical
    critical_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            ActionItem.building_id.in_(active_building_ids),
            ActionItem.priority == "critical",
            ActionItem.status.in_(["open", "in_progress"]),
        )
    )
    actions_critical = critical_result.scalar() or 0

    return OrgSummary(
        org_id=org_id,
        org_name=org.name,
        org_type=org.type,
        building_count=building_count,
        risk_distribution=risk_distribution,
        completeness_avg=completeness_avg,
        actions_pending=actions_pending,
        actions_critical=actions_critical,
    )


async def get_multi_org_dashboard(db: AsyncSession, org_ids: list[UUID] | None = None) -> MultiOrgDashboard:
    """Aggregate metrics across organizations."""
    query = select(Organization)
    if org_ids:
        query = query.where(Organization.id.in_(org_ids))

    result = await db.execute(query.order_by(Organization.name))
    orgs = result.scalars().all()

    summaries: list[OrgSummary] = []
    for org in orgs:
        summaries.append(await _get_org_summary(db, org))

    # Global aggregates
    total_buildings = sum(s.building_count for s in summaries)
    global_risk: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for s in summaries:
        for level in global_risk:
            global_risk[level] += s.risk_distribution.get(level, 0)

    if summaries:
        weighted_sum = sum(s.completeness_avg * s.building_count for s in summaries)
        global_completeness = round(weighted_sum / total_buildings, 2) if total_buildings > 0 else 0.0
    else:
        global_completeness = 0.0

    return MultiOrgDashboard(
        organizations=summaries,
        total_buildings=total_buildings,
        total_organizations=len(summaries),
        global_risk_distribution=global_risk,
        global_completeness_avg=global_completeness,
    )


async def compare_organizations(
    db: AsyncSession, org_ids: list[UUID], metrics: list[str] | None = None
) -> MultiOrgComparison:
    """Side-by-side comparison of selected metrics across organizations."""
    if metrics is None:
        metrics = list(AVAILABLE_METRICS)
    else:
        metrics = [m for m in metrics if m in AVAILABLE_METRICS]
        if not metrics:
            metrics = list(AVAILABLE_METRICS)

    result = await db.execute(select(Organization).where(Organization.id.in_(org_ids)))
    orgs = result.scalars().all()

    items: list[OrgComparisonItem] = []
    for org in orgs:
        summary = await _get_org_summary(db, org)
        for metric_name in metrics:
            value = float(getattr(summary, metric_name, 0))
            items.append(
                OrgComparisonItem(
                    org_id=org.id,
                    org_name=org.name,
                    metric_name=metric_name,
                    metric_value=value,
                )
            )

    return MultiOrgComparison(items=items, metric_names=metrics)
