"""Configurable notification rules engine for building events."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.notification_rules import (
    BuildingTriggersResponse,
    DigestGroup,
    DigestResponse,
    NotificationPreferencesResponse,
    OrgAlertBuilding,
    OrgAlertSummary,
    TriggerResult,
)

# Default trigger types
ALL_TRIGGER_TYPES = [
    "overdue_diagnostics",
    "expiring_compliance",
    "high_risk_unaddressed",
    "incomplete_dossier",
    "stale_data",
]

_STALE_THRESHOLD_DAYS = 180  # 6 months


async def evaluate_building_triggers(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingTriggersResponse:
    """Evaluate all notification rules against a building's current state."""
    from app.models.action_item import ActionItem
    from app.models.building import Building
    from app.models.building_risk_score import BuildingRiskScore
    from app.models.diagnostic import Diagnostic

    # Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return BuildingTriggersResponse(building_id=building_id, triggers=[], total=0)

    triggers: list[TriggerResult] = []

    # 1. Overdue diagnostics — diagnostics still in draft/in_progress
    diag_result = await db.execute(
        select(Diagnostic).where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["draft", "in_progress"]),
        )
    )
    overdue_diags = diag_result.scalars().all()
    for diag in overdue_diags:
        triggers.append(
            TriggerResult(
                trigger_type="overdue_diagnostics",
                severity="warning",
                message=f"Diagnostic {diag.diagnostic_type} is still in '{diag.status}' status",
                affected_entity_id=diag.id,
                recommended_action="Complete and validate the diagnostic",
            )
        )

    # 2. Expiring compliance — completed diagnostics older than 5 years
    five_years_ago = datetime.now(UTC) - timedelta(days=5 * 365)
    exp_result = await db.execute(
        select(Diagnostic).where(
            Diagnostic.building_id == building_id,
            Diagnostic.status == "completed",
            Diagnostic.date_report.isnot(None),
        )
    )
    for diag in exp_result.scalars().all():
        if diag.date_report and diag.date_report < five_years_ago.date():
            triggers.append(
                TriggerResult(
                    trigger_type="expiring_compliance",
                    severity="critical",
                    message=f"Diagnostic {diag.diagnostic_type} report from {diag.date_report} may be expired",
                    affected_entity_id=diag.id,
                    recommended_action="Schedule a new diagnostic assessment",
                )
            )

    # 3. High risk unaddressed — high/critical risk with open actions
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_score = risk_result.scalar_one_or_none()
    if risk_score and risk_score.overall_risk_level in ("high", "critical"):
        open_actions_result = await db.execute(
            select(func.count())
            .select_from(ActionItem)
            .where(
                ActionItem.building_id == building_id,
                ActionItem.status == "open",
            )
        )
        open_count = open_actions_result.scalar() or 0
        if open_count > 0:
            triggers.append(
                TriggerResult(
                    trigger_type="high_risk_unaddressed",
                    severity="critical",
                    message=f"Building has {risk_score.overall_risk_level} risk with {open_count} open action(s)",
                    affected_entity_id=building_id,
                    recommended_action="Address open action items to mitigate risk",
                )
            )

    # 4. Incomplete dossier — no diagnostics at all
    total_diag_result = await db.execute(
        select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id)
    )
    total_diag = total_diag_result.scalar() or 0
    if total_diag == 0:
        triggers.append(
            TriggerResult(
                trigger_type="incomplete_dossier",
                severity="info",
                message="Building has no diagnostics — dossier is incomplete",
                affected_entity_id=building_id,
                recommended_action="Schedule an initial diagnostic assessment",
            )
        )

    # 5. Stale data — building not updated in > 6 months
    if building.updated_at:
        updated_at = building.updated_at
        if not hasattr(updated_at, "tzinfo") or updated_at.tzinfo is None:
            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=_STALE_THRESHOLD_DAYS)
        else:
            cutoff = datetime.now(UTC) - timedelta(days=_STALE_THRESHOLD_DAYS)
        if updated_at < cutoff:
            triggers.append(
                TriggerResult(
                    trigger_type="stale_data",
                    severity="info",
                    message="Building data has not been updated in over 6 months",
                    affected_entity_id=building_id,
                    recommended_action="Review and update building information",
                )
            )

    return BuildingTriggersResponse(
        building_id=building_id,
        triggers=triggers,
        total=len(triggers),
    )


async def get_notification_preferences(
    user_id: UUID,
    db: AsyncSession,
) -> NotificationPreferencesResponse:
    """Return a user's notification rule preferences."""
    from app.models.notification import NotificationPreferenceExtended

    result = await db.execute(
        select(NotificationPreferenceExtended).where(NotificationPreferenceExtended.user_id == user_id)
    )
    pref = result.scalar_one_or_none()

    if pref and pref.preferences_json:
        try:
            data = json.loads(pref.preferences_json)
        except (json.JSONDecodeError, TypeError):
            data = {}
    else:
        data = {}

    return NotificationPreferencesResponse(
        user_id=user_id,
        enabled_triggers=data.get("enabled_triggers", ALL_TRIGGER_TYPES),
        frequency=data.get("frequency", "immediate"),
        channels=data.get("channels", ["in_app"]),
        quiet_hours_start=data.get("quiet_hours_start"),
        quiet_hours_end=data.get("quiet_hours_end"),
    )


async def generate_digest(
    user_id: UUID,
    db: AsyncSession,
    period: str = "daily",
) -> DigestResponse:
    """Compile a digest of triggered notifications for the user's buildings/org."""
    from app.models.building import Building
    from app.models.user import User

    # Get user and their buildings
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return DigestResponse(
            user_id=user_id,
            period=period,
            groups=[],
            total_count=0,
            summary="User not found",
        )

    # Get preferences to filter triggers
    prefs = await get_notification_preferences(user_id, db)

    # Find buildings associated with user (created_by or owner)
    buildings_result = await db.execute(
        select(Building).where((Building.created_by == user_id) | (Building.owner_id == user_id))
    )
    buildings = buildings_result.scalars().all()

    # If user belongs to an org, also include buildings from org members
    if user.organization_id:
        org_users_result = await db.execute(select(User.id).where(User.organization_id == user.organization_id))
        org_user_ids = [row[0] for row in org_users_result.all()]
        if org_user_ids:
            org_buildings_result = await db.execute(
                select(Building).where(
                    Building.created_by.in_(org_user_ids),
                    Building.id.notin_([b.id for b in buildings]),
                )
            )
            buildings.extend(org_buildings_result.scalars().all())

    # Evaluate triggers for all buildings
    all_triggers: list[TriggerResult] = []
    for building in buildings:
        result = await evaluate_building_triggers(building.id, db)
        # Filter by user preferences
        for trigger in result.triggers:
            if trigger.trigger_type in prefs.enabled_triggers:
                all_triggers.append(trigger)

    # Group by severity
    severity_order = ["critical", "warning", "info"]
    groups: list[DigestGroup] = []
    for severity in severity_order:
        items = [t for t in all_triggers if t.severity == severity]
        if items:
            groups.append(DigestGroup(severity=severity, count=len(items), items=items))

    total = len(all_triggers)
    summary = f"{total} alert(s) across {len(buildings)} building(s) — {period} digest"

    return DigestResponse(
        user_id=user_id,
        period=period,
        groups=groups,
        total_count=total,
        summary=summary,
    )


async def get_org_alert_summary(
    org_id: UUID,
    db: AsyncSession,
) -> OrgAlertSummary:
    """Generate an org-wide alert summary for the dashboard."""
    from app.services.building_data_loader import load_org_buildings

    # Get all buildings created by org members
    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return OrgAlertSummary(
            org_id=org_id,
            total_active_alerts=0,
            by_severity={},
            top_triggered_rules=[],
            buildings_with_most_alerts=[],
            trend="stable",
        )

    # Evaluate triggers per building
    by_severity: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
    rule_counts: dict[str, int] = {}
    building_alerts: list[OrgAlertBuilding] = []

    for building in buildings:
        result = await evaluate_building_triggers(building.id, db)
        if result.total > 0:
            building_alerts.append(
                OrgAlertBuilding(
                    building_id=building.id,
                    address=building.address,
                    alert_count=result.total,
                )
            )
        for trigger in result.triggers:
            by_severity[trigger.severity] = by_severity.get(trigger.severity, 0) + 1
            rule_counts[trigger.trigger_type] = rule_counts.get(trigger.trigger_type, 0) + 1

    total = sum(by_severity.values())

    # Top triggered rules sorted by count descending
    top_rules = sorted(rule_counts, key=rule_counts.get, reverse=True)[:5]  # type: ignore[arg-type]

    # Sort buildings by alert count descending, take top 5
    building_alerts.sort(key=lambda b: b.alert_count, reverse=True)
    top_buildings = building_alerts[:5]

    return OrgAlertSummary(
        org_id=org_id,
        total_active_alerts=total,
        by_severity=by_severity,
        top_triggered_rules=top_rules,
        buildings_with_most_alerts=top_buildings,
        trend="stable",
    )
