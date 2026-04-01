"""
BatiConnect - Proactive Alert Service

Orchestrates all detection engines and creates notifications for findings.
Connects predictive_readiness_service, change_signal_generator, evidence scoring,
and action monitoring to the notification system.

Alerts are created as Notification records (reuses existing notification model).
Deduplication: identical alert (type + entity_id + building_id) not duplicated
if an unread notification already exists.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.notification import Notification
from app.services.evidence_score_service import compute_evidence_score
from app.services.predictive_readiness_service import scan_building as scan_predictive

logger = logging.getLogger(__name__)


def _ensure_aware(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is timezone-aware (UTC). Handles naive datetimes from SQLite."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NOTIFICATION_TYPE_ALERT = "alert"

# Overdue thresholds (days)
OVERDUE_CRITICAL_DAYS = 30
OVERDUE_HIGH_DAYS = 60

# Stale building threshold
STALE_MONTHS = 6

# Evidence score degradation threshold
EVIDENCE_SCORE_DROP_THRESHOLD = 10

# Low evidence score for portfolio alerts
LOW_EVIDENCE_SCORE_THRESHOLD = 40

# Diagnostic expiry window for portfolio alerts
PORTFOLIO_DIAG_EXPIRY_DAYS = 90


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


async def _notification_exists(
    db: AsyncSession,
    user_id: UUID,
    alert_type: str,
    entity_id: str | None,
    building_id: str,
) -> bool:
    """Check if an unread notification with same alert fingerprint exists."""
    # Encode fingerprint in link field: "alert:{alert_type}:{building_id}:{entity_id}"
    fingerprint = f"alert:{alert_type}:{building_id}:{entity_id or 'none'}"
    result = await db.execute(
        select(func.count()).where(
            and_(
                Notification.user_id == user_id,
                Notification.status == "unread",
                Notification.link == fingerprint,
            )
        )
    )
    count = result.scalar() or 0
    return count > 0


def _make_fingerprint(alert_type: str, building_id: str, entity_id: str | None) -> str:
    return f"alert:{alert_type}:{building_id}:{entity_id or 'none'}"


# ---------------------------------------------------------------------------
# Alert creators
# ---------------------------------------------------------------------------


async def _create_notification(
    db: AsyncSession,
    user_id: UUID,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    building_id: str,
    entity_type: str | None,
    entity_id: str | None,
    recommended_action: str,
) -> dict[str, Any] | None:
    """Create a notification if no duplicate unread notification exists.

    Returns alert dict if created, None if deduplicated.
    """
    fingerprint = _make_fingerprint(alert_type, building_id, entity_id)

    if await _notification_exists(db, user_id, alert_type, entity_id, building_id):
        return None

    body = f"[{severity.upper()}] {message}\n\nAction recommandee: {recommended_action}"

    notification = Notification(
        user_id=user_id,
        type=NOTIFICATION_TYPE_ALERT,
        title=title,
        body=body,
        link=fingerprint,
        status="unread",
    )
    db.add(notification)

    return {
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "building_id": building_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "recommended_action": recommended_action,
        "notification_id": str(notification.id),
    }


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------


async def _detect_overdue_actions(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """Detect overdue actions: critical > 30d, high > 60d."""
    alerts: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    # Use naive cutoff for SQL comparison (SQLite stores naive datetimes)
    now_naive = now.replace(tzinfo=None)

    # Critical actions overdue > 30 days
    critical_cutoff = now_naive - timedelta(days=OVERDUE_CRITICAL_DAYS)
    result = await db.execute(
        select(ActionItem).where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == "open",
                ActionItem.priority == "critical",
                ActionItem.created_at < critical_cutoff,
            )
        )
    )
    for action in result.scalars().all():
        created = _ensure_aware(action.created_at)
        days_open = (now - created).days if created else 0
        alerts.append(
            {
                "alert_type": "overdue_action",
                "severity": "critical",
                "title": f"Action critique en retard ({days_open}j): {action.title}",
                "message": f"L'action critique « {action.title} » est ouverte depuis {days_open} jours.",
                "building_id": str(building_id),
                "entity_type": "action_item",
                "entity_id": str(action.id),
                "recommended_action": f"Traiter l'action « {action.title} » en priorite",
            }
        )

    # High actions overdue > 60 days
    high_cutoff = now_naive - timedelta(days=OVERDUE_HIGH_DAYS)
    result = await db.execute(
        select(ActionItem).where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == "open",
                ActionItem.priority == "high",
                ActionItem.created_at < high_cutoff,
            )
        )
    )
    for action in result.scalars().all():
        created = _ensure_aware(action.created_at)
        days_open = (now - created).days if created else 0
        alerts.append(
            {
                "alert_type": "overdue_action",
                "severity": "warning",
                "title": f"Action haute priorite en retard ({days_open}j): {action.title}",
                "message": f"L'action haute priorite « {action.title} » est ouverte depuis {days_open} jours.",
                "building_id": str(building_id),
                "entity_type": "action_item",
                "entity_id": str(action.id),
                "recommended_action": f"Traiter l'action « {action.title} »",
            }
        )

    return alerts


async def _detect_stale_building(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """Detect building with no activity in > 6 months."""
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(days=STALE_MONTHS * 30)

    # Check latest diagnostic date
    diag_result = await db.execute(select(func.max(Diagnostic.created_at)).where(Diagnostic.building_id == building_id))
    latest_diag = diag_result.scalar()

    # Check latest document date
    doc_result = await db.execute(select(func.max(Document.created_at)).where(Document.building_id == building_id))
    latest_doc = doc_result.scalar()

    # Check latest action date
    action_result = await db.execute(
        select(func.max(ActionItem.created_at)).where(ActionItem.building_id == building_id)
    )
    latest_action = action_result.scalar()

    dates = [d for d in [latest_diag, latest_doc, latest_action] if d is not None]
    if not dates:
        # No activity at all — stale
        return [
            {
                "alert_type": "stale_building",
                "severity": "info",
                "title": "Batiment sans activite",
                "message": "Aucune activite enregistree pour ce batiment.",
                "building_id": str(building_id),
                "entity_type": "building",
                "entity_id": str(building_id),
                "recommended_action": "Verifier l'etat du dossier et planifier une mise a jour",
            }
        ]

    latest = max(dates)
    # Ensure timezone-aware comparison
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)

    if latest < stale_cutoff:
        days_since = (now - latest).days
        return [
            {
                "alert_type": "stale_building",
                "severity": "warning",
                "title": f"Batiment inactif depuis {days_since} jours",
                "message": f"Aucune activite sur ce batiment depuis {days_since} jours ({days_since // 30} mois).",
                "building_id": str(building_id),
                "entity_type": "building",
                "entity_id": str(building_id),
                "recommended_action": "Mettre a jour le dossier du batiment",
            }
        ]

    return []


async def _detect_missing_documents(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """Detect completed diagnostics without uploaded report document."""
    alerts: list[dict[str, Any]] = []

    diags_result = await db.execute(
        select(Diagnostic).where(
            and_(
                Diagnostic.building_id == building_id,
                Diagnostic.status.in_(["completed", "validated"]),
            )
        )
    )
    diagnostics = list(diags_result.scalars().all())

    for diag in diagnostics:
        # Check if any document references this diagnostic
        doc_result = await db.execute(
            select(func.count()).where(
                and_(
                    Document.building_id == building_id,
                    Document.document_type == "diagnostic_report",
                )
            )
        )
        doc_count = doc_result.scalar() or 0
        if doc_count == 0:
            alerts.append(
                {
                    "alert_type": "missing_document",
                    "severity": "warning",
                    "title": f"Rapport manquant: diagnostic {diag.diagnostic_type}",
                    "message": (
                        f"Le diagnostic {diag.diagnostic_type} est termine mais aucun rapport n'a ete telecharge."
                    ),
                    "building_id": str(building_id),
                    "entity_type": "diagnostic",
                    "entity_id": str(diag.id),
                    "recommended_action": "Telecharger le rapport de diagnostic",
                }
            )
            # Only one alert per building for missing docs (avoid noise)
            break

    return alerts


async def _detect_evidence_score_degradation(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """Detect evidence score below threshold (simplified — no historical comparison yet)."""
    score_result = await compute_evidence_score(db, building_id)
    if score_result is None:
        return []

    score = score_result.get("score", 100)
    if score < LOW_EVIDENCE_SCORE_THRESHOLD:
        return [
            {
                "alert_type": "evidence_score_low",
                "severity": "warning",
                "title": f"Score de preuve faible: {score}/100",
                "message": (
                    f"Le score de preuve du batiment est de {score}/100, "
                    f"en dessous du seuil de {LOW_EVIDENCE_SCORE_THRESHOLD}."
                ),
                "building_id": str(building_id),
                "entity_type": "building",
                "entity_id": str(building_id),
                "recommended_action": "Completer le dossier: ajouter diagnostics, documents, preuves",
            }
        ]

    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def scan_and_alert(
    db: AsyncSession,
    building_id: UUID,
    user_id: UUID,
) -> list[dict[str, Any]]:
    """Run all detection engines and create notifications for a single building.

    Returns list of newly created alert dicts.
    """
    # Verify building exists
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return []

    all_raw_alerts: list[dict[str, Any]] = []

    # 1. Predictive readiness alerts (from existing service)
    try:
        predictive = await scan_predictive(db, building_id)
        for pa in predictive.get("alerts", []):
            all_raw_alerts.append(
                {
                    "alert_type": pa.get("alert_type", "predictive"),
                    "severity": pa.get("severity", "info"),
                    "title": pa.get("title", "Alerte predictive"),
                    "message": pa.get("description", ""),
                    "building_id": str(building_id),
                    "entity_type": "building",
                    "entity_id": str(building_id),
                    "recommended_action": pa.get("recommended_action", "Verifier le dossier"),
                }
            )
    except Exception:
        logger.warning("Failed to run predictive scan for building %s", building_id, exc_info=True)

    # 2. Overdue actions
    try:
        all_raw_alerts.extend(await _detect_overdue_actions(db, building_id))
    except Exception:
        logger.warning("Failed to detect overdue actions for building %s", building_id, exc_info=True)

    # 3. Stale building
    try:
        all_raw_alerts.extend(await _detect_stale_building(db, building_id))
    except Exception:
        logger.warning("Failed to detect stale building %s", building_id, exc_info=True)

    # 4. Missing documents
    try:
        all_raw_alerts.extend(await _detect_missing_documents(db, building_id))
    except Exception:
        logger.warning("Failed to detect missing documents for building %s", building_id, exc_info=True)

    # 5. Evidence score degradation
    try:
        all_raw_alerts.extend(await _detect_evidence_score_degradation(db, building_id))
    except Exception:
        logger.warning("Failed to detect evidence score degradation for building %s", building_id, exc_info=True)

    # Create notifications with deduplication
    created: list[dict[str, Any]] = []
    for raw in all_raw_alerts:
        result = await _create_notification(
            db=db,
            user_id=user_id,
            alert_type=raw["alert_type"],
            severity=raw["severity"],
            title=raw["title"],
            message=raw["message"],
            building_id=raw["building_id"],
            entity_type=raw.get("entity_type"),
            entity_id=raw.get("entity_id"),
            recommended_action=raw["recommended_action"],
        )
        if result is not None:
            created.append(result)

    if created:
        await db.flush()
        logger.info("Created %d proactive alerts for building %s", len(created), building_id)

    return created


async def scan_portfolio_alerts(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
) -> list[dict[str, Any]]:
    """Scan all buildings in org + generate portfolio-level alerts."""
    bld_result = await db.execute(
        select(Building).where(
            and_(
                Building.organization_id == org_id,
                Building.status == "active",
            )
        )
    )
    buildings = list(bld_result.scalars().all())

    if not buildings:
        return []

    all_alerts: list[dict[str, Any]] = []

    # Per-building scan
    low_evidence_count = 0
    expiring_diag_count = 0

    for building in buildings:
        building_alerts = await scan_and_alert(db, building.id, user_id)
        all_alerts.extend(building_alerts)

        # Gather portfolio metrics
        try:
            score_result = await compute_evidence_score(db, building.id)
            if score_result and score_result.get("score", 100) < LOW_EVIDENCE_SCORE_THRESHOLD:
                low_evidence_count += 1
        except Exception:
            pass

        try:
            predictive = await scan_predictive(db, building.id)
            for pa in predictive.get("alerts", []):
                if (
                    pa.get("alert_type") == "diagnostic_expiring"
                    and pa.get("days_remaining") is not None
                    and pa["days_remaining"] <= PORTFOLIO_DIAG_EXPIRY_DAYS
                ):
                    expiring_diag_count += 1
        except Exception:
            pass

    # Portfolio-level alerts
    if low_evidence_count > 0:
        result = await _create_notification(
            db=db,
            user_id=user_id,
            alert_type="portfolio_low_evidence",
            severity="warning",
            title=f"{low_evidence_count} batiment(s) avec score de preuve < {LOW_EVIDENCE_SCORE_THRESHOLD}",
            message=(
                f"{low_evidence_count} batiment(s) dans votre portfolio ont un score "
                f"de preuve inferieur a {LOW_EVIDENCE_SCORE_THRESHOLD}/100."
            ),
            building_id="portfolio",
            entity_type="portfolio",
            entity_id=str(org_id),
            recommended_action="Prioriser la completion des dossiers les plus faibles",
        )
        if result:
            all_alerts.append(result)

    if expiring_diag_count > 0:
        result = await _create_notification(
            db=db,
            user_id=user_id,
            alert_type="portfolio_expiring_diagnostics",
            severity="warning" if expiring_diag_count < 5 else "critical",
            title=f"{expiring_diag_count} diagnostic(s) expirant dans 90 jours",
            message=(
                f"{expiring_diag_count} diagnostic(s) a travers votre portfolio expirent dans les 90 prochains jours."
            ),
            building_id="portfolio",
            entity_type="portfolio",
            entity_id=str(org_id),
            recommended_action="Planifier le renouvellement des diagnostics",
        )
        if result:
            all_alerts.append(result)

    if all_alerts:
        await db.flush()

    return all_alerts


async def get_alert_summary(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    """Return alert summary for the user's unread alert notifications."""
    # Count unread alert notifications
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.type == NOTIFICATION_TYPE_ALERT,
                Notification.status == "unread",
            )
        )
    )
    notifications = list(result.scalars().all())

    by_severity: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
    by_type: dict[str, int] = {}
    buildings_with_alerts: set[str] = set()

    for n in notifications:
        # Parse fingerprint from link: "alert:{type}:{building_id}:{entity_id}"
        if n.link and n.link.startswith("alert:"):
            parts = n.link.split(":")
            if len(parts) >= 3:
                alert_type = parts[1]
                bid = parts[2]
                by_type[alert_type] = by_type.get(alert_type, 0) + 1
                if bid != "portfolio":
                    buildings_with_alerts.add(bid)

        # Parse severity from body: "[CRITICAL] ..." or "[WARNING] ..." or "[INFO] ..."
        if n.body:
            for sev in ("critical", "warning", "info"):
                if n.body.startswith(f"[{sev.upper()}]"):
                    by_severity[sev] = by_severity.get(sev, 0) + 1
                    break

    return {
        "total_alerts": len(notifications),
        "by_severity": by_severity,
        "by_type": by_type,
        "buildings_with_alerts": len(buildings_with_alerts),
    }
