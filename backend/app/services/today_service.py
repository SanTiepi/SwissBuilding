"""BatiConnect -- Today feed service.

Generates the daily action queue for a user across their entire portfolio.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.audit_log import AuditLog
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.obligation import Obligation
from app.models.recurring_service import RecurringService, WarrantyRecord


def _today() -> date:
    return datetime.now(UTC).date()


def _row_to_building_ref(row: Building) -> dict:
    return {
        "building_id": str(row.id),
        "building_name": row.address or "—",
    }


# ---------------------------------------------------------------------------
# Priority ordering helper
# ---------------------------------------------------------------------------
_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _priority_sort_key(item: dict) -> tuple:
    return (_PRIORITY_ORDER.get(item.get("priority", "medium"), 9),)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def get_today_feed(
    db: AsyncSession,
    org_id: UUID | None,
    user_id: UUID,
) -> dict:
    """Build the daily action feed for *user_id* across all accessible buildings."""

    today = _today()
    end_of_week = today + timedelta(days=(6 - today.weekday()))  # Sunday
    horizon_30 = today + timedelta(days=30)
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)

    # ------------------------------------------------------------------
    # 1. Determine accessible buildings
    # ------------------------------------------------------------------
    bld_q = select(Building)
    if org_id:
        bld_q = bld_q.where(Building.organization_id == org_id)
    bld_result = await db.execute(bld_q)
    buildings = list(bld_result.scalars().all())
    building_map: dict[UUID, Building] = {b.id: b for b in buildings}
    building_ids = list(building_map.keys())

    if not building_ids:
        return _empty_feed()

    # ------------------------------------------------------------------
    # 2. Open / in-progress / blocked action items
    # ------------------------------------------------------------------
    action_q = select(ActionItem).where(
        and_(
            ActionItem.building_id.in_(building_ids),
            ActionItem.status.in_(["open", "in_progress", "blocked"]),
        )
    )
    action_result = await db.execute(action_q)
    actions = list(action_result.scalars().all())

    urgent: list[dict] = []
    this_week: list[dict] = []
    blocked: list[dict] = []

    for a in actions:
        bld = building_map.get(a.building_id)
        bld_ref = _row_to_building_ref(bld) if bld else {"building_id": str(a.building_id), "building_name": "—"}

        if a.status == "blocked":
            blocked.append(
                {
                    **bld_ref,
                    "action_id": str(a.id),
                    "blocker_description": a.title,
                    "blocked_since": a.updated_at.isoformat() if a.updated_at else None,
                    "impact": a.priority or "medium",
                }
            )
            continue

        entry = {
            **bld_ref,
            "type": a.source_type or "action",
            "title": a.title,
            "description": a.description,
            "deadline": a.due_date.isoformat() if a.due_date else None,
            "priority": a.priority or "medium",
            "source": a.action_type or "manual",
            "action_id": str(a.id),
        }

        if a.due_date and a.due_date <= today:
            urgent.append(entry)
        elif a.due_date and a.due_date <= end_of_week:
            this_week.append(entry)
        elif a.priority in ("critical", "high"):
            urgent.append(entry)
        else:
            this_week.append(entry)

    urgent.sort(key=_priority_sort_key)
    this_week.sort(key=_priority_sort_key)

    # ------------------------------------------------------------------
    # 3. Obligations with upcoming deadlines (30-day horizon)
    # ------------------------------------------------------------------
    obl_q = select(Obligation).where(
        and_(
            Obligation.building_id.in_(building_ids),
            Obligation.status.in_(["upcoming", "due_soon", "overdue"]),
            Obligation.due_date <= horizon_30,
        )
    )
    obl_result = await db.execute(obl_q)
    obligations = list(obl_result.scalars().all())

    upcoming_deadlines: list[dict] = []
    for o in obligations:
        bld = building_map.get(o.building_id)
        bld_ref = _row_to_building_ref(bld) if bld else {"building_id": str(o.building_id), "building_name": "—"}
        days_remaining = (o.due_date - today).days if o.due_date else 0
        upcoming_deadlines.append(
            {
                **bld_ref,
                "type": o.obligation_type or "obligation",
                "description": o.title,
                "deadline": o.due_date.isoformat() if o.due_date else None,
                "days_remaining": max(days_remaining, 0),
            }
        )
    upcoming_deadlines.sort(key=lambda x: x.get("days_remaining", 999))

    # Also add overdue obligations to urgent
    for o in obligations:
        if o.due_date and o.due_date <= today and o.status == "overdue":
            bld = building_map.get(o.building_id)
            bld_ref = _row_to_building_ref(bld) if bld else {"building_id": str(o.building_id), "building_name": "—"}
            urgent.append(
                {
                    **bld_ref,
                    "type": "obligation",
                    "title": o.title,
                    "description": o.description,
                    "deadline": o.due_date.isoformat() if o.due_date else None,
                    "priority": o.priority or "high",
                    "source": o.obligation_type or "obligation",
                    "action_id": None,
                }
            )

    # ------------------------------------------------------------------
    # 4. Diagnostics expiring within 90 days (completed_at + 3 years)
    # ------------------------------------------------------------------
    three_years_minus_90 = datetime.now(UTC) - timedelta(days=3 * 365 - 90)

    diag_q = select(Diagnostic).where(
        and_(
            Diagnostic.building_id.in_(building_ids),
            Diagnostic.status == "completed",
            or_(
                # date_report is a Date column -- compare with date
                and_(Diagnostic.date_report.isnot(None), Diagnostic.date_report <= three_years_minus_90),
            ),
        )
    )
    diag_result = await db.execute(diag_q)
    diagnostics = list(diag_result.scalars().all())

    expiring_soon: list[dict] = []
    for d in diagnostics:
        report_date = d.date_report
        if not report_date:
            continue
        if isinstance(report_date, datetime):
            expiry = report_date + timedelta(days=3 * 365)
        else:
            expiry = datetime.combine(report_date, datetime.min.time(), tzinfo=UTC) + timedelta(days=3 * 365)
        expiry_date = expiry.date() if isinstance(expiry, datetime) else expiry
        days_remaining = (expiry_date - today).days
        if days_remaining > 90:
            continue

        bld = building_map.get(d.building_id)
        bld_ref = _row_to_building_ref(bld) if bld else {"building_id": str(d.building_id), "building_name": "—"}
        expiring_soon.append(
            {
                **bld_ref,
                "document_type": d.diagnostic_type or "diagnostic",
                "expiry_date": expiry_date.isoformat(),
                "days_remaining": max(days_remaining, 0),
            }
        )
    expiring_soon.sort(key=lambda x: x.get("days_remaining", 999))

    # ------------------------------------------------------------------
    # 5. Recent activity (last 7 days from audit_logs)
    # ------------------------------------------------------------------
    audit_q = select(AuditLog).where(AuditLog.timestamp >= seven_days_ago).order_by(AuditLog.timestamp.desc()).limit(50)
    audit_result = await db.execute(audit_q)
    audit_logs = list(audit_result.scalars().all())

    recent_activity: list[dict] = []
    for log in audit_logs:
        # Try to link to a building via entity_type / details
        building_name = "—"
        building_id_str = None
        details = log.details or {}
        if isinstance(details, dict) and details.get("building_id"):
            bid = details["building_id"]
            try:
                from uuid import UUID as UUIDType

                bid_uuid = UUIDType(str(bid)) if not isinstance(bid, UUIDType) else bid
                bld = building_map.get(bid_uuid)
                if bld:
                    building_name = bld.address or "—"
                    building_id_str = str(bld.id)
            except (ValueError, AttributeError):
                pass

        recent_activity.append(
            {
                "building_name": building_name,
                "building_id": building_id_str,
                "action": log.action or "—",
                "actor": str(log.user_id) if log.user_id else "systeme",
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
        )

    # ------------------------------------------------------------------
    # 6. Critical freshness watch entries
    # ------------------------------------------------------------------
    freshness_alerts: list[dict] = []
    try:
        from app.services.freshness_watch_service import get_critical_for_today

        freshness_alerts = await get_critical_for_today(db)
    except Exception:
        pass  # Graceful degradation if table not yet created

    # ------------------------------------------------------------------
    # 7. Upcoming recurring services (30-day horizon)
    # ------------------------------------------------------------------
    svc_q = select(RecurringService).where(
        and_(
            RecurringService.building_id.in_(building_ids),
            RecurringService.status == "active",
            RecurringService.next_service_date.isnot(None),
            RecurringService.next_service_date <= horizon_30,
        )
    )
    svc_result = await db.execute(svc_q)
    upcoming_services_list = list(svc_result.scalars().all())

    upcoming_services: list[dict] = []
    for svc in upcoming_services_list:
        bld = building_map.get(svc.building_id)
        bld_ref = _row_to_building_ref(bld) if bld else {"building_id": str(svc.building_id), "building_name": "—"}
        days_rem = (svc.next_service_date - today).days if svc.next_service_date else 0
        upcoming_services.append(
            {
                **bld_ref,
                "type": "recurring_service",
                "service_type": svc.service_type,
                "provider": svc.provider_name,
                "next_date": svc.next_service_date.isoformat() if svc.next_service_date else None,
                "days_remaining": max(days_rem, 0),
                "frequency": svc.frequency,
            }
        )
        # Overdue services go into urgent
        if svc.next_service_date and svc.next_service_date <= today:
            urgent.append(
                {
                    **bld_ref,
                    "type": "recurring_service",
                    "title": f"Service en retard: {svc.service_type}",
                    "description": f"Prestataire: {svc.provider_name}",
                    "deadline": svc.next_service_date.isoformat(),
                    "priority": "high",
                    "source": "recurring_service",
                    "action_id": None,
                }
            )
    upcoming_services.sort(key=lambda x: x.get("days_remaining", 999))

    # ------------------------------------------------------------------
    # 8. Expiring warranties (90-day horizon)
    # ------------------------------------------------------------------
    horizon_90 = today + timedelta(days=90)
    war_q = select(WarrantyRecord).where(
        and_(
            WarrantyRecord.building_id.in_(building_ids),
            WarrantyRecord.status == "active",
            WarrantyRecord.end_date <= horizon_90,
            WarrantyRecord.end_date >= today,
        )
    )
    war_result = await db.execute(war_q)
    expiring_warranties_list = list(war_result.scalars().all())

    expiring_warranties: list[dict] = []
    for w in expiring_warranties_list:
        bld = building_map.get(w.building_id)
        bld_ref = _row_to_building_ref(bld) if bld else {"building_id": str(w.building_id), "building_name": "—"}
        days_rem = (w.end_date - today).days if w.end_date else 0
        expiring_warranties.append(
            {
                **bld_ref,
                "type": "warranty_expiry",
                "warranty_type": w.warranty_type,
                "subject": w.subject,
                "provider": w.provider_name,
                "end_date": w.end_date.isoformat() if w.end_date else None,
                "days_remaining": max(days_rem, 0),
            }
        )
    expiring_warranties.sort(key=lambda x: x.get("days_remaining", 999))

    # ------------------------------------------------------------------
    # 9. Stats
    # ------------------------------------------------------------------
    total_buildings = len(buildings)

    # "ready" = buildings with at least one completed diagnostic and 0 open critical/high actions
    buildings_with_completed_diag: set[UUID] = set()
    for d in diagnostics:
        if d.status == "completed":
            buildings_with_completed_diag.add(d.building_id)

    buildings_blocked: set[UUID] = set()
    for a in actions:
        if a.status == "blocked":
            buildings_blocked.add(a.building_id)

    buildings_with_critical_open: set[UUID] = set()
    for a in actions:
        if a.status in ("open", "in_progress") and a.priority in ("critical", "high"):
            buildings_with_critical_open.add(a.building_id)

    buildings_ready = len(buildings_with_completed_diag - buildings_blocked - buildings_with_critical_open)

    open_actions = sum(1 for a in actions if a.status in ("open", "in_progress"))
    overdue_actions = sum(
        1 for a in actions if a.due_date and a.due_date < today and a.status in ("open", "in_progress")
    )

    stats = {
        "total_buildings": total_buildings,
        "buildings_ready": buildings_ready,
        "buildings_blocked": len(buildings_blocked),
        "open_actions": open_actions,
        "overdue_actions": overdue_actions,
        "diagnostics_expiring_90d": len(expiring_soon),
        "upcoming_services_30d": len(upcoming_services),
        "expiring_warranties_90d": len(expiring_warranties),
    }

    # ------------------------------------------------------------------
    # 10. Weekly focus — operator clarity for the rituel hebdo
    # ------------------------------------------------------------------
    weekly_focus = _build_weekly_focus(
        actions=actions,
        building_map=building_map,
        today=today,
        end_of_week=end_of_week,
    )

    return {
        "urgent": urgent,
        "this_week": this_week,
        "upcoming_deadlines": upcoming_deadlines,
        "blocked": blocked,
        "expiring_soon": expiring_soon,
        "upcoming_services": upcoming_services,
        "expiring_warranties": expiring_warranties,
        "freshness_alerts": freshness_alerts,
        "recent_activity": recent_activity,
        "weekly_focus": weekly_focus,
        "stats": stats,
    }


def _build_weekly_focus(
    actions: list,
    building_map: dict,
    today: date,
    end_of_week: date,
) -> dict:
    """Build the weekly_focus section for operator clarity (rituel hebdo).

    Returns top-3 buildings needing attention, active dossier workflows,
    upcoming deadlines (7 days), and a pilot progress summary.
    """
    from collections import Counter

    # Count overdue actions per building
    overdue_per_building: Counter = Counter()
    for a in actions:
        if a.status in ("open", "in_progress") and a.due_date and a.due_date < today:
            overdue_per_building[a.building_id] += 1

    # Top 3 buildings with most overdue actions
    top3 = overdue_per_building.most_common(3)
    buildings_needing_attention = []
    for bid, count in top3:
        bld = building_map.get(bid)
        buildings_needing_attention.append(
            {
                "building_id": str(bid),
                "building_name": bld.address if bld else "---",
                "overdue_actions": count,
            }
        )

    # Active dossier workflows: buildings with high/critical open actions
    # from dossier_workflow source
    dossier_buildings: set = set()
    for a in actions:
        if a.status in ("open", "in_progress") and a.source_type == "dossier_workflow":
            dossier_buildings.add(a.building_id)

    dossiers_in_progress = []
    for bid in list(dossier_buildings)[:5]:
        bld = building_map.get(bid)
        dossiers_in_progress.append(
            {
                "building_id": str(bid),
                "building_name": bld.address if bld else "---",
            }
        )

    # Upcoming deadlines (next 7 days)
    seven_days = today + timedelta(days=7)
    upcoming = []
    for a in actions:
        if a.status in ("open", "in_progress") and a.due_date and today <= a.due_date <= seven_days:
            bld = building_map.get(a.building_id)
            upcoming.append(
                {
                    "building_id": str(a.building_id),
                    "building_name": bld.address if bld else "---",
                    "action_title": a.title,
                    "deadline": a.due_date.isoformat(),
                    "priority": a.priority,
                }
            )
    upcoming.sort(key=lambda x: x.get("deadline", ""))

    # Pilot progress summary
    completed_this_week = sum(
        1
        for a in actions
        if a.status == "done"
        and a.completed_at
        and hasattr(a.completed_at, "date")
        and a.completed_at.date() >= (today - timedelta(days=today.weekday()))
    )
    remaining = sum(1 for a in actions if a.status in ("open", "in_progress", "blocked"))

    return {
        "buildings_needing_attention": buildings_needing_attention,
        "dossiers_in_progress": dossiers_in_progress,
        "upcoming_deadlines": upcoming[:10],
        "pilot_progress": f"{completed_this_week} actions completees, {remaining} restantes cette semaine",
    }


def _empty_feed() -> dict:
    return {
        "urgent": [],
        "this_week": [],
        "upcoming_deadlines": [],
        "blocked": [],
        "expiring_soon": [],
        "upcoming_services": [],
        "expiring_warranties": [],
        "freshness_alerts": [],
        "recent_activity": [],
        "weekly_focus": {
            "buildings_needing_attention": [],
            "dossiers_in_progress": [],
            "upcoming_deadlines": [],
            "pilot_progress": "0 actions completees, 0 restantes cette semaine",
        },
        "stats": {
            "total_buildings": 0,
            "buildings_ready": 0,
            "buildings_blocked": 0,
            "open_actions": 0,
            "overdue_actions": 0,
            "diagnostics_expiring_90d": 0,
            "upcoming_services_30d": 0,
            "expiring_warranties_90d": 0,
        },
    }
