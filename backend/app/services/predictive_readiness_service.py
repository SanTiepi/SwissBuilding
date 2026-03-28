"""
BatiConnect - Predictive Readiness Service

Proactively scans buildings for upcoming readiness risks:
  - Diagnostics expiring (completed_at + 3 years)
  - Planned interventions with incomplete readiness
  - Obligations with approaching deadlines
  - Compliance artefacts needing renewal
  - Readiness degradation projections

Returns actionable alerts with recommended next steps.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.insurance_policy import InsurancePolicy
from app.models.intervention import Intervention
from app.models.obligation import Obligation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Swiss standard: diagnostic validity is 3 years
DIAGNOSTIC_VALIDITY_YEARS = 3
DIAGNOSTIC_VALIDITY_DAYS = DIAGNOSTIC_VALIDITY_YEARS * 365

# Alert windows
WINDOW_30D = 30
WINDOW_90D = 90
WINDOW_365D = 365

# Lead times (days)
LEAD_TIME_DIAGNOSTIC_ORDER = 45
LEAD_TIME_AUTHORITY_SUBMISSION = 14
LEAD_TIME_INSURANCE_RENEWAL = 60

# Severity thresholds
CRITICAL_DAYS = 30
WARNING_DAYS = 90

# Source type for generated actions
SOURCE_TYPE_PREDICTIVE = "predictive_readiness"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alert_id(*parts: str) -> str:
    """Generate a deterministic alert ID from parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _severity_for_days(days: int) -> str:
    if days <= CRITICAL_DAYS:
        return "critical"
    if days <= WARNING_DAYS:
        return "warning"
    return "info"


def _diagnostic_expiry_date(diag: Diagnostic) -> date | None:
    """Compute expiry date for a completed diagnostic."""
    ref = diag.date_inspection
    if ref is None and diag.created_at is not None:
        ref = diag.created_at.date() if hasattr(diag.created_at, "date") else diag.created_at
    if ref is None:
        return None
    if hasattr(ref, "date"):
        ref = ref.date()
    return ref + timedelta(days=DIAGNOSTIC_VALIDITY_DAYS)


def _readiness_status(diags: list[Diagnostic], today: date) -> str:
    """Determine simple readiness status based on diagnostic coverage."""
    completed = [d for d in diags if d.status in ("completed", "validated")]
    if not completed:
        return "not_ready"
    for d in completed:
        exp = _diagnostic_expiry_date(d)
        if exp and exp > today:
            return "ready"
    return "not_ready"


def _projected_readiness(diags: list[Diagnostic], today: date, days_ahead: int) -> str:
    """Project readiness status N days into the future."""
    future_date = today + timedelta(days=days_ahead)
    completed = [d for d in diags if d.status in ("completed", "validated")]
    if not completed:
        return "not_ready"
    for d in completed:
        exp = _diagnostic_expiry_date(d)
        if exp and exp > future_date:
            return "ready"
    # Some diagnostics exist but all will be expired
    any_valid_now = any(_diagnostic_expiry_date(d) and _diagnostic_expiry_date(d) > today for d in completed)
    if any_valid_now:
        return "partial"
    return "not_ready"


# ---------------------------------------------------------------------------
# Alert detectors
# ---------------------------------------------------------------------------


def _detect_expiring_diagnostics(
    building: Building,
    diagnostics: list[Diagnostic],
    today: date,
) -> list[dict[str, Any]]:
    """Detect diagnostics expiring within 30/90/365 days."""
    alerts: list[dict[str, Any]] = []
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]

    for diag in completed:
        exp = _diagnostic_expiry_date(diag)
        if exp is None:
            continue
        days_remaining = (exp - today).days
        if days_remaining < 0:
            # Already expired
            alerts.append(
                {
                    "id": _alert_id("diag_expired", str(building.id), str(diag.id)),
                    "severity": "critical",
                    "building_id": str(building.id),
                    "building_name": f"{building.address}, {building.city}",
                    "alert_type": "diagnostic_expiring",
                    "title": f"Diagnostic {diag.diagnostic_type} expiré",
                    "description": (
                        f"Le diagnostic {diag.diagnostic_type} a expiré il y a "
                        f"{abs(days_remaining)} jours. Un nouveau diagnostic est nécessaire."
                    ),
                    "deadline": exp.isoformat(),
                    "days_remaining": days_remaining,
                    "recommended_action": "Commander un nouveau diagnostic polluants",
                    "estimated_lead_time_days": LEAD_TIME_DIAGNOSTIC_ORDER,
                }
            )
        elif days_remaining <= WINDOW_365D:
            alerts.append(
                {
                    "id": _alert_id("diag_expiring", str(building.id), str(diag.id)),
                    "severity": _severity_for_days(days_remaining),
                    "building_id": str(building.id),
                    "building_name": f"{building.address}, {building.city}",
                    "alert_type": "diagnostic_expiring",
                    "title": f"Diagnostic {diag.diagnostic_type} expire dans {days_remaining} jours",
                    "description": (
                        f"Le diagnostic {diag.diagnostic_type} du bâtiment "
                        f"{building.address} expire le {exp.isoformat()}."
                    ),
                    "deadline": exp.isoformat(),
                    "days_remaining": days_remaining,
                    "recommended_action": "Commander un nouveau diagnostic polluants",
                    "estimated_lead_time_days": LEAD_TIME_DIAGNOSTIC_ORDER,
                }
            )

    return alerts


def _detect_intervention_readiness_gaps(
    building: Building,
    diagnostics: list[Diagnostic],
    interventions: list[Intervention],
    today: date,
) -> list[dict[str, Any]]:
    """Detect buildings with planned interventions but expired/missing diagnostics."""
    alerts: list[dict[str, Any]] = []
    planned = [i for i in interventions if i.status in ("planned", "in_progress")]
    if not planned:
        return alerts

    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]
    has_valid_diag = any(_diagnostic_expiry_date(d) and _diagnostic_expiry_date(d) > today for d in completed_diags)

    if not has_valid_diag:
        earliest_start = min(
            (i.date_start for i in planned if i.date_start),
            default=None,
        )
        days_until = (earliest_start - today).days if earliest_start else None
        alerts.append(
            {
                "id": _alert_id("intervention_unready", str(building.id)),
                "severity": "critical" if (days_until and days_until < 90) else "warning",
                "building_id": str(building.id),
                "building_name": f"{building.address}, {building.city}",
                "alert_type": "intervention_unready",
                "title": f"{len(planned)} intervention(s) prévue(s) sans diagnostic valide",
                "description": (
                    f"Le bâtiment {building.address} a {len(planned)} intervention(s) "
                    f"planifiée(s) mais aucun diagnostic polluants valide. "
                    f"Les travaux ne peuvent pas démarrer en toute sécurité."
                ),
                "deadline": earliest_start.isoformat() if earliest_start else None,
                "days_remaining": days_until,
                "recommended_action": "Commander un diagnostic polluants en urgence avant le début des travaux",
                "estimated_lead_time_days": LEAD_TIME_DIAGNOSTIC_ORDER,
            }
        )

    return alerts


def _detect_obligation_deadlines(
    building: Building,
    obligations: list[Obligation],
    today: date,
) -> list[dict[str, Any]]:
    """Detect obligations with approaching deadlines."""
    alerts: list[dict[str, Any]] = []

    for obl in obligations:
        if obl.status in ("completed", "cancelled"):
            continue
        if obl.due_date is None:
            continue
        days_remaining = (obl.due_date - today).days
        if days_remaining > WINDOW_365D:
            continue

        alerts.append(
            {
                "id": _alert_id("obligation_due", str(building.id), str(obl.id)),
                "severity": _severity_for_days(max(days_remaining, 0)),
                "building_id": str(building.id),
                "building_name": f"{building.address}, {building.city}",
                "alert_type": "obligation_due",
                "title": f"Obligation: {obl.title}",
                "description": (
                    f"L'obligation « {obl.title} » ({obl.obligation_type}) "
                    f"est due le {obl.due_date.isoformat()} "
                    f"({'en retard' if days_remaining < 0 else f'dans {days_remaining} jours'})."
                ),
                "deadline": obl.due_date.isoformat(),
                "days_remaining": days_remaining,
                "recommended_action": f"Traiter l'obligation « {obl.title} » avant l'échéance",
                "estimated_lead_time_days": obl.reminder_days_before or 30,
            }
        )

    return alerts


def _detect_artefact_renewals(
    building: Building,
    artefacts: list[ComplianceArtefact],
    today: date,
) -> list[dict[str, Any]]:
    """Detect compliance artefacts needing renewal."""
    alerts: list[dict[str, Any]] = []

    for art in artefacts:
        if art.expires_at is None:
            continue
        exp_date = art.expires_at.date() if hasattr(art.expires_at, "date") else art.expires_at
        days_remaining = (exp_date - today).days
        if days_remaining > WINDOW_365D:
            continue

        alerts.append(
            {
                "id": _alert_id("artefact_renewal", str(building.id), str(art.id)),
                "severity": _severity_for_days(max(days_remaining, 0)),
                "building_id": str(building.id),
                "building_name": f"{building.address}, {building.city}",
                "alert_type": "coverage_gap",
                "title": f"Artefact de conformité « {art.title} » à renouveler",
                "description": (f"L'artefact « {art.title} » ({art.artefact_type}) expire le {exp_date.isoformat()}."),
                "deadline": exp_date.isoformat(),
                "days_remaining": days_remaining,
                "recommended_action": f"Renouveler l'artefact « {art.title} » auprès de {art.authority_name or 'l autorite competente'}",
                "estimated_lead_time_days": LEAD_TIME_AUTHORITY_SUBMISSION,
            }
        )

    return alerts


def _detect_insurance_renewals(
    building: Building,
    policies: list[InsurancePolicy],
    today: date,
) -> list[dict[str, Any]]:
    """Detect insurance policies needing renewal."""
    alerts: list[dict[str, Any]] = []

    for pol in policies:
        if pol.status in ("cancelled", "expired"):
            continue
        if pol.date_end is None:
            continue
        days_remaining = (pol.date_end - today).days
        if days_remaining > WINDOW_365D:
            continue

        alerts.append(
            {
                "id": _alert_id("insurance_renewal", str(building.id), str(pol.id)),
                "severity": _severity_for_days(max(days_remaining, 0)),
                "building_id": str(building.id),
                "building_name": f"{building.address}, {building.city}",
                "alert_type": "coverage_gap",
                "title": f"Police d'assurance {pol.policy_type} à renouveler",
                "description": (
                    f"La police d'assurance « {pol.policy_number} » ({pol.policy_type}) "
                    f"expire le {pol.date_end.isoformat()}."
                ),
                "deadline": pol.date_end.isoformat(),
                "days_remaining": days_remaining,
                "recommended_action": f"Renouveler la police d'assurance {pol.policy_type} auprès de {pol.insurer_name}",
                "estimated_lead_time_days": LEAD_TIME_INSURANCE_RENEWAL,
            }
        )

    return alerts


def _detect_readiness_degradation(
    building: Building,
    diagnostics: list[Diagnostic],
    today: date,
) -> list[dict[str, Any]]:
    """Detect buildings where readiness will degrade if no action is taken."""
    alerts: list[dict[str, Any]] = []

    current = _readiness_status(diagnostics, today)
    proj_30 = _projected_readiness(diagnostics, today, WINDOW_30D)
    proj_90 = _projected_readiness(diagnostics, today, WINDOW_90D)

    if current == "ready" and proj_90 != "ready":
        # Find the diagnostic that will expire
        completed = [d for d in diagnostics if d.status in ("completed", "validated")]
        soonest_expiry = None
        for d in completed:
            exp = _diagnostic_expiry_date(d)
            if exp and exp > today and (soonest_expiry is None or exp < soonest_expiry):
                soonest_expiry = exp

        days_until_degrade = (soonest_expiry - today).days if soonest_expiry else None
        severity = "critical" if proj_30 != "ready" else "warning"

        alerts.append(
            {
                "id": _alert_id("readiness_degradation", str(building.id)),
                "severity": severity,
                "building_id": str(building.id),
                "building_name": f"{building.address}, {building.city}",
                "alert_type": "readiness_degradation",
                "title": f"Readiness va se dégrader dans {days_until_degrade or '?'} jours",
                "description": (
                    f"Le bâtiment {building.address} passera de « prêt » à "
                    f"« {'partiellement prêt' if proj_90 == 'partial' else 'non prêt'} » "
                    f"d'ici 90 jours si aucune action n'est prise."
                ),
                "deadline": soonest_expiry.isoformat() if soonest_expiry else None,
                "days_remaining": days_until_degrade,
                "recommended_action": "Commander un nouveau diagnostic pour maintenir la readiness",
                "estimated_lead_time_days": LEAD_TIME_DIAGNOSTIC_ORDER,
            }
        )

    return alerts


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


async def _load_building_context(db: AsyncSession, building_id: UUID) -> dict[str, Any] | None:
    """Load all data needed for predictive readiness scanning."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    interv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(interv_result.scalars().all())

    obl_result = await db.execute(select(Obligation).where(Obligation.building_id == building_id))
    obligations = list(obl_result.scalars().all())

    art_result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = list(art_result.scalars().all())

    pol_result = await db.execute(select(InsurancePolicy).where(InsurancePolicy.building_id == building_id))
    policies = list(pol_result.scalars().all())

    return {
        "building": building,
        "diagnostics": diagnostics,
        "interventions": interventions,
        "obligations": obligations,
        "artefacts": artefacts,
        "policies": policies,
    }


def _scan_building_data(ctx: dict[str, Any], today: date) -> dict[str, Any]:
    """Run all detectors on a single building's data. Pure function."""
    building = ctx["building"]
    diagnostics = ctx["diagnostics"]
    interventions = ctx["interventions"]
    obligations = ctx["obligations"]
    artefacts = ctx["artefacts"]
    policies = ctx["policies"]

    alerts: list[dict[str, Any]] = []
    alerts.extend(_detect_expiring_diagnostics(building, diagnostics, today))
    alerts.extend(_detect_intervention_readiness_gaps(building, diagnostics, interventions, today))
    alerts.extend(_detect_obligation_deadlines(building, obligations, today))
    alerts.extend(_detect_artefact_renewals(building, artefacts, today))
    alerts.extend(_detect_insurance_renewals(building, policies, today))
    alerts.extend(_detect_readiness_degradation(building, diagnostics, today))

    # Sort by severity then days_remaining
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: (severity_order.get(a["severity"], 3), a.get("days_remaining") or 9999))

    # Build projection
    current = _readiness_status(diagnostics, today)
    proj_30 = _projected_readiness(diagnostics, today, WINDOW_30D)
    proj_90 = _projected_readiness(diagnostics, today, WINDOW_90D)

    degradation_reason = None
    if current != proj_90:
        completed = [d for d in diagnostics if d.status in ("completed", "validated")]
        expiring_types = []
        future_90 = today + timedelta(days=WINDOW_90D)
        for d in completed:
            exp = _diagnostic_expiry_date(d)
            if exp and exp <= future_90:
                expiring_types.append(d.diagnostic_type or "unknown")
        if expiring_types:
            degradation_reason = f"Diagnostic(s) expirant: {', '.join(expiring_types)}"
        else:
            degradation_reason = "Couverture diagnostique insuffisante"

    projection = {
        "building_id": str(building.id),
        "building_name": f"{building.address}, {building.city}",
        "current_readiness": current,
        "projected_readiness_30d": proj_30,
        "projected_readiness_90d": proj_90,
        "degradation_reason": degradation_reason,
    }

    return {"alerts": alerts, "projection": projection}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def scan_building(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Scan a single building for upcoming readiness risks.

    Returns dict with alerts, summary, and projections.
    """
    ctx = await _load_building_context(db, building_id)
    if ctx is None:
        return {
            "alerts": [],
            "summary": {"critical": 0, "warning": 0, "info": 0, "buildings_at_risk": 0, "diagnostics_expiring_90d": 0},
            "projections": [],
        }

    today = datetime.now(UTC).date()
    result = _scan_building_data(ctx, today)

    alerts = result["alerts"]
    summary = {
        "critical": sum(1 for a in alerts if a["severity"] == "critical"),
        "warning": sum(1 for a in alerts if a["severity"] == "warning"),
        "info": sum(1 for a in alerts if a["severity"] == "info"),
        "buildings_at_risk": 1 if any(a["severity"] in ("critical", "warning") for a in alerts) else 0,
        "diagnostics_expiring_90d": sum(
            1
            for a in alerts
            if a["alert_type"] == "diagnostic_expiring"
            and a.get("days_remaining") is not None
            and a["days_remaining"] <= WINDOW_90D
        ),
    }

    return {
        "alerts": alerts,
        "summary": summary,
        "projections": [result["projection"]],
    }


async def scan_portfolio(db: AsyncSession, org_id: UUID) -> dict[str, Any]:
    """Scan all buildings in an organization for upcoming readiness risks.

    Returns dict with alerts, summary, and projections.
    """
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
        return {
            "alerts": [],
            "summary": {"critical": 0, "warning": 0, "info": 0, "buildings_at_risk": 0, "diagnostics_expiring_90d": 0},
            "projections": [],
        }

    today = datetime.now(UTC).date()
    all_alerts: list[dict[str, Any]] = []
    all_projections: list[dict[str, Any]] = []
    buildings_at_risk = set()

    for building in buildings:
        ctx = await _load_building_context(db, building.id)
        if ctx is None:
            continue
        result = _scan_building_data(ctx, today)
        all_alerts.extend(result["alerts"])
        all_projections.append(result["projection"])
        if any(a["severity"] in ("critical", "warning") for a in result["alerts"]):
            buildings_at_risk.add(str(building.id))

    # Sort all alerts
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_alerts.sort(key=lambda a: (severity_order.get(a["severity"], 3), a.get("days_remaining") or 9999))

    summary = {
        "critical": sum(1 for a in all_alerts if a["severity"] == "critical"),
        "warning": sum(1 for a in all_alerts if a["severity"] == "warning"),
        "info": sum(1 for a in all_alerts if a["severity"] == "info"),
        "buildings_at_risk": len(buildings_at_risk),
        "diagnostics_expiring_90d": sum(
            1
            for a in all_alerts
            if a["alert_type"] == "diagnostic_expiring"
            and a.get("days_remaining") is not None
            and a["days_remaining"] <= WINDOW_90D
        ),
    }

    return {
        "alerts": all_alerts,
        "summary": summary,
        "projections": all_projections,
    }


async def generate_predictive_actions(db: AsyncSession, org_id: UUID) -> list[dict[str, Any]]:
    """Generate ActionItems for predicted risks. Idempotent.

    Creates actions like:
    - 'Commander un diagnostic amiante' (90 days before expiry)
    - 'Renouveler la police d'assurance' (60 days before expiry)
    - 'Préparer le dossier autorité' (when intervention is planned)

    Returns list of created action dicts.
    """
    scan_result = await scan_portfolio(db, org_id)
    alerts = scan_result["alerts"]

    # Only generate actions for critical and warning alerts
    actionable = [a for a in alerts if a["severity"] in ("critical", "warning")]
    created: list[dict[str, Any]] = []

    for alert in actionable:
        building_id = alert["building_id"]

        # Build an idempotent key from alert type + building
        action_title = alert["recommended_action"]

        # Check if action already exists (idempotent)
        existing = await db.execute(
            select(ActionItem).where(
                and_(
                    ActionItem.building_id == building_id,
                    ActionItem.source_type == SOURCE_TYPE_PREDICTIVE,
                    ActionItem.title == action_title,
                    ActionItem.status.in_(["open", "in_progress"]),
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        # Determine priority from severity
        priority = "high" if alert["severity"] == "critical" else "medium"

        # Determine due date
        due_date = None
        if alert.get("deadline"):
            try:
                deadline = date.fromisoformat(alert["deadline"])
                lead_time = alert.get("estimated_lead_time_days") or 30
                due_date = deadline - timedelta(days=lead_time)
                # Don't set due date in the past
                today = datetime.now(UTC).date()
                if due_date < today:
                    due_date = today
            except (ValueError, TypeError):
                pass

        action = ActionItem(
            building_id=building_id,
            source_type=SOURCE_TYPE_PREDICTIVE,
            action_type=alert["alert_type"],
            title=action_title,
            description=alert["description"],
            priority=priority,
            status="open",
            due_date=due_date,
            metadata_json={
                "alert_id": alert["id"],
                "alert_type": alert["alert_type"],
                "days_remaining": alert.get("days_remaining"),
            },
        )
        db.add(action)
        created.append(
            {
                "building_id": building_id,
                "title": action_title,
                "priority": priority,
                "due_date": due_date.isoformat() if due_date else None,
                "alert_type": alert["alert_type"],
            }
        )

    if created:
        await db.flush()
        logger.info("Created %d predictive actions for org %s", len(created), org_id)

    return created
