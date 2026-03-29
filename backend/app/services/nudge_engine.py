"""
SwissBuildingOS - Compliance Nudge Engine

Behavioral nudge engine that reframes compliance messages to drive ACTION.
Based on loss aversion (Kahneman): show what owners LOSE by inaction,
not what they gain by acting.

Sources:
  1. Diagnostics (expiry, missing SUVA notification)
  2. Samples (positive asbestos without remediation)
  3. Evidence score (incomplete dossier)
  4. ActionItems (overdue critical actions)
  5. Trust score (low verification level)
  6. Portfolio-level risk aggregation
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_STATUS_OPEN,
)
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIAGNOSTIC_VALIDITY_YEARS = 5
DIAGNOSTIC_EXPIRY_WARNING_DAYS = 365  # warn when < 1 year left

NUDGE_SEVERITY_CRITICAL = "critical"
NUDGE_SEVERITY_WARNING = "warning"
NUDGE_SEVERITY_INFO = "info"

_SEVERITY_ORDER = {NUDGE_SEVERITY_CRITICAL: 0, NUDGE_SEVERITY_WARNING: 1, NUDGE_SEVERITY_INFO: 2}

# Swiss market social proof (hardcoded for now, later from usage stats)
_SOCIAL_PROOF = {
    "diagnostic_renewal": "87% of similar buildings in your canton have up-to-date diagnostics.",
    "asbestos_remediation": "92% of owners who discover asbestos begin remediation within 6 months.",
    "dossier_completeness": "Top-performing property managers maintain dossier scores above 80%.",
    "action_compliance": "78% of regulated buildings have zero overdue critical actions.",
    "trust_verification": "Buildings with verified data sell 15% faster in Swiss markets.",
    "suva_notification": "99% of compliant owners file SUVA notifications before works begin.",
    "portfolio_compliance": "Leading gérances address portfolio-wide risk 40% more cost-effectively.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stable_id(*parts: str) -> str:
    """Generate a stable short ID from key parts."""
    raw = ":".join(parts)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _days_until(target: date) -> int:
    """Days from today until target date."""
    return (target - date.today()).days


def _format_for_context(
    headline: str,
    loss: str,
    gain: str,
    context: str,
) -> dict[str, str]:
    """Adjust text verbosity based on context."""
    if context == "dashboard":
        return {
            "headline": headline,
            "loss_framing": loss[:200] if len(loss) > 200 else loss,
            "gain_framing": gain[:150] if len(gain) > 150 else gain,
        }
    if context == "email":
        return {
            "headline": f"⚠ {headline}",
            "loss_framing": loss,
            "gain_framing": gain,
        }
    # "detail" — full text
    return {
        "headline": headline,
        "loss_framing": loss,
        "gain_framing": gain,
    }


def _sort_key(nudge: dict) -> tuple:
    """Sort: severity ASC, deadline_pressure ASC (nulls last)."""
    sev = _SEVERITY_ORDER.get(nudge["severity"], 2)
    deadline = nudge.get("deadline_pressure")
    deadline_sort = deadline if deadline is not None else 999999
    return (sev, deadline_sort)


# ---------------------------------------------------------------------------
# Nudge generators
# ---------------------------------------------------------------------------


async def _expiring_diagnostic_nudges(
    db: AsyncSession,
    building_id: UUID,
    context: str,
) -> list[dict]:
    """Diagnostic > 4 years old or approaching expiry."""
    stmt = select(Diagnostic).where(
        and_(
            Diagnostic.building_id == building_id,
            Diagnostic.status == "completed",
            Diagnostic.date_report.isnot(None),
        )
    )
    result = await db.execute(stmt)
    diagnostics = list(result.scalars().all())

    nudges = []

    for diag in diagnostics:
        if diag.date_report is None:
            continue

        expiry_date = date(
            diag.date_report.year + DIAGNOSTIC_VALIDITY_YEARS,
            diag.date_report.month,
            diag.date_report.day,
        )
        days_left = _days_until(expiry_date)

        if days_left > DIAGNOSTIC_EXPIRY_WARNING_DAYS:
            continue

        severity = NUDGE_SEVERITY_CRITICAL if days_left <= 90 else NUDGE_SEVERITY_WARNING

        texts = _format_for_context(
            headline=f"Diagnostic expires in {max(0, days_left)} days",
            loss=(
                f"Your {diag.diagnostic_type} diagnostic expires on {expiry_date.isoformat()}. "
                "After expiry, you cannot legally start any works. "
                "Emergency re-diagnostics cost 2-3x more than planned renewals. "
                "Insurance coverage may lapse for known hazards."
            ),
            gain=("Renewing now ensures uninterrupted legal compliance and access to planned renovation timelines."),
            context=context,
        )

        nudges.append(
            {
                "id": _stable_id("expiring_diagnostic", str(diag.id)),
                "nudge_type": "expiring_diagnostic",
                "severity": severity,
                **texts,
                "cost_of_inaction": {
                    "description": "Emergency re-diagnostic surcharge",
                    "estimated_chf_min": 4000,
                    "estimated_chf_max": 16000,
                    "confidence": "market_data",
                },
                "deadline_pressure": max(0, days_left),
                "social_proof": _SOCIAL_PROOF["diagnostic_renewal"],
                "call_to_action": "Schedule diagnostic renewal",
                "related_entity": {
                    "entity_type": "diagnostic",
                    "entity_id": str(diag.id),
                },
            }
        )

    return nudges


async def _unaddressed_asbestos_nudges(
    db: AsyncSession,
    building_id: UUID,
    context: str,
) -> list[dict]:
    """Positive asbestos samples with no remediation started."""
    # Find positive asbestos samples
    sample_stmt = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            and_(
                Diagnostic.building_id == building_id,
                Diagnostic.diagnostic_type == "asbestos",
                Sample.threshold_exceeded.is_(True),
            )
        )
    )
    sample_result = await db.execute(sample_stmt)
    positive_samples = list(sample_result.scalars().all())

    if not positive_samples:
        return []

    # Check if any asbestos intervention exists
    interv_stmt = (
        select(func.count())
        .select_from(Intervention)
        .where(
            and_(
                Intervention.building_id == building_id,
                Intervention.intervention_type.in_(["asbestos_removal", "asbestos_encapsulation", "removal"]),
            )
        )
    )
    interv_result = await db.execute(interv_stmt)
    interv_count = interv_result.scalar() or 0

    if interv_count > 0:
        return []

    texts = _format_for_context(
        headline=f"{len(positive_samples)} asbestos finding(s) — no remediation started",
        loss=(
            "Every month of delay exposes occupants to asbestos fibers. "
            "Insurance may deny claims on known but unaddressed hazards. "
            "SUVA fines for non-compliance start at CHF 10,000. "
            "Owner criminal liability applies under OTConst Art. 60a."
        ),
        gain=(
            "Starting remediation planning now protects occupants, "
            "preserves insurance coverage, and avoids regulatory penalties."
        ),
        context=context,
    )

    return [
        {
            "id": _stable_id("unaddressed_asbestos", str(building_id)),
            "nudge_type": "unaddressed_asbestos",
            "severity": NUDGE_SEVERITY_CRITICAL,
            **texts,
            "cost_of_inaction": {
                "description": "SUVA fine + potential liability",
                "estimated_chf_min": 10000,
                "estimated_chf_max": 100000,
                "confidence": "regulatory",
            },
            "deadline_pressure": None,
            "social_proof": _SOCIAL_PROOF["asbestos_remediation"],
            "call_to_action": "Plan asbestos remediation",
            "related_entity": {
                "entity_type": "building",
                "entity_id": str(building_id),
            },
        }
    ]


async def _incomplete_dossier_nudges(
    db: AsyncSession,
    building_id: UUID,
    context: str,
) -> list[dict]:
    """Evidence score < 50 → dossier incompleteness nudge."""
    from app.services.evidence_score_service import compute_evidence_score

    score_data = await compute_evidence_score(db, building_id)
    if score_data is None:
        return []

    score = score_data["score"]
    if score >= 50:
        return []

    severity = NUDGE_SEVERITY_CRITICAL if score < 30 else NUDGE_SEVERITY_WARNING
    gap_pct = 100 - score

    texts = _format_for_context(
        headline=f"Building dossier only {score}% complete",
        loss=(
            f"Your building dossier is {score}% complete — {gap_pct}% of critical data is missing. "
            "Banks require ≥80% completeness for renovation loans. "
            "Property value drops ~5% per year of missing documentation. "
            "Incomplete dossiers are inadmissible for authority submissions."
        ),
        gain=(
            "A complete dossier unlocks financing options, "
            "increases property value, and accelerates authority approvals."
        ),
        context=context,
    )

    return [
        {
            "id": _stable_id("incomplete_dossier", str(building_id)),
            "nudge_type": "incomplete_dossier",
            "severity": severity,
            **texts,
            "cost_of_inaction": {
                "description": "Estimated property value loss per year",
                "estimated_chf_min": 5000,
                "estimated_chf_max": 50000,
                "confidence": "estimated",
            },
            "deadline_pressure": None,
            "social_proof": _SOCIAL_PROOF["dossier_completeness"],
            "call_to_action": "Complete building dossier",
            "related_entity": {
                "entity_type": "building",
                "entity_id": str(building_id),
            },
        }
    ]


async def _overdue_actions_nudges(
    db: AsyncSession,
    building_id: UUID,
    context: str,
) -> list[dict]:
    """Critical actions overdue > 30 days."""
    today = date.today()

    stmt = select(ActionItem).where(
        and_(
            ActionItem.building_id == building_id,
            ActionItem.status == ACTION_STATUS_OPEN,
            ActionItem.priority == ACTION_PRIORITY_CRITICAL,
            ActionItem.due_date.isnot(None),
        )
    )
    result = await db.execute(stmt)
    actions = list(result.scalars().all())

    overdue = [a for a in actions if a.due_date and (today - a.due_date).days > 30]

    if not overdue:
        return []

    max_overdue_days = max((today - a.due_date).days for a in overdue)

    texts = _format_for_context(
        headline=f"{len(overdue)} critical action(s) overdue by up to {max_overdue_days} days",
        loss=(
            f"{len(overdue)} critical actions are overdue. "
            "Regulatory authorities can mandate immediate building closure. "
            "Average remediation cost doubles when imposed vs. planned. "
            "Owner liability increases with documented inaction period."
        ),
        gain=("Resolving overdue actions restores compliance status and avoids escalation to mandatory enforcement."),
        context=context,
    )

    return [
        {
            "id": _stable_id("overdue_actions", str(building_id)),
            "nudge_type": "overdue_actions",
            "severity": NUDGE_SEVERITY_CRITICAL,
            **texts,
            "cost_of_inaction": {
                "description": "Cost multiplier for imposed vs. planned remediation",
                "estimated_chf_min": 20000,
                "estimated_chf_max": 200000,
                "confidence": "estimated",
            },
            "deadline_pressure": 0,
            "social_proof": _SOCIAL_PROOF["action_compliance"],
            "call_to_action": "Review overdue actions",
            "related_entity": {
                "entity_type": "building",
                "entity_id": str(building_id),
            },
        }
    ]


async def _low_trust_score_nudges(
    db: AsyncSession,
    building_id: UUID,
    context: str,
) -> list[dict]:
    """Trust score < 0.4 → data verification nudge."""
    from app.models.building_trust_score_v2 import BuildingTrustScore

    stmt = (
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    trust = result.scalar_one_or_none()

    if trust is None or trust.overall_score >= 0.4:
        return []

    pct = int(trust.overall_score * 100)

    texts = _format_for_context(
        headline=f"Only {pct}% of building data is verified",
        loss=(
            f"Only {pct}% of your building data is verified. "
            "Unverified data is inadmissible in legal proceedings. "
            "Low trust scores block authority submissions. "
            "Transaction counterparties will demand independent re-verification."
        ),
        gain=("Verified data strengthens legal position, accelerates transactions, and unlocks authority submissions."),
        context=context,
    )

    return [
        {
            "id": _stable_id("low_trust_score", str(building_id)),
            "nudge_type": "low_trust_score",
            "severity": NUDGE_SEVERITY_WARNING,
            **texts,
            "cost_of_inaction": {
                "description": "Re-verification cost when demanded by third party",
                "estimated_chf_min": 3000,
                "estimated_chf_max": 15000,
                "confidence": "estimated",
            },
            "deadline_pressure": None,
            "social_proof": _SOCIAL_PROOF["trust_verification"],
            "call_to_action": "Upload verification documents",
            "related_entity": {
                "entity_type": "building",
                "entity_id": str(building_id),
            },
        }
    ]


async def _missing_suva_notification_nudges(
    db: AsyncSession,
    building_id: UUID,
    context: str,
) -> list[dict]:
    """SUVA notification required but not done."""
    stmt = select(Diagnostic).where(
        and_(
            Diagnostic.building_id == building_id,
            Diagnostic.suva_notification_required.is_(True),
            Diagnostic.suva_notification_date.is_(None),
        )
    )
    result = await db.execute(stmt)
    diagnostics = list(result.scalars().all())

    if not diagnostics:
        return []

    texts = _format_for_context(
        headline="SUVA notification missing — legally required",
        loss=(
            "SUVA notification is legally required before ANY asbestos work begins. "
            "Non-compliance triggers criminal liability for the building owner. "
            "Works performed without notification may be invalidated. "
            "Workers' compensation claims will be denied."
        ),
        gain=("Filing the SUVA notification takes minutes and is a prerequisite for legal remediation works."),
        context=context,
    )

    return [
        {
            "id": _stable_id("missing_suva", str(building_id)),
            "nudge_type": "missing_suva_notification",
            "severity": NUDGE_SEVERITY_CRITICAL,
            **texts,
            "cost_of_inaction": {
                "description": "Criminal liability + invalidated works",
                "estimated_chf_min": 10000,
                "estimated_chf_max": 500000,
                "confidence": "regulatory",
            },
            "deadline_pressure": 0,
            "social_proof": _SOCIAL_PROOF["suva_notification"],
            "call_to_action": "File SUVA notification now",
            "related_entity": {
                "entity_type": "diagnostic",
                "entity_id": str(diagnostics[0].id),
            },
        }
    ]


# ---------------------------------------------------------------------------
# Portfolio-level nudge
# ---------------------------------------------------------------------------


async def _portfolio_risk_nudges(
    db: AsyncSession,
    organization_id: UUID,
    context: str,
) -> list[dict]:
    """>30% of org buildings at risk → portfolio nudge."""
    # Count total buildings
    total_stmt = select(func.count()).select_from(Building).where(Building.organization_id == organization_id)
    total_result = await db.execute(total_stmt)
    total_count = total_result.scalar() or 0

    if total_count == 0:
        return []

    # Count buildings with open critical actions
    at_risk_stmt = (
        select(func.count(func.distinct(ActionItem.building_id)))
        .select_from(ActionItem)
        .join(Building, ActionItem.building_id == Building.id)
        .where(
            and_(
                Building.organization_id == organization_id,
                ActionItem.status == ACTION_STATUS_OPEN,
                ActionItem.priority == ACTION_PRIORITY_CRITICAL,
            )
        )
    )
    at_risk_result = await db.execute(at_risk_stmt)
    at_risk_count = at_risk_result.scalar() or 0

    risk_pct = at_risk_count / total_count
    if risk_pct <= 0.3:
        return []

    texts = _format_for_context(
        headline=f"{at_risk_count} of {total_count} buildings need immediate attention",
        loss=(
            f"{int(risk_pct * 100)}% of your portfolio has critical compliance gaps. "
            "Portfolio-wide regulatory enforcement is more severe than individual cases. "
            "Institutional investors and insurers flag portfolios with >30% non-compliance. "
            "Individual building-by-building remediation costs 40% more than coordinated programs."
        ),
        gain=(
            "A portfolio-wide compliance program reduces total cost by ~40% "
            "and demonstrates systematic due diligence to authorities."
        ),
        context=context,
    )

    return [
        {
            "id": _stable_id("portfolio_risk", str(organization_id)),
            "nudge_type": "portfolio_risk",
            "severity": NUDGE_SEVERITY_CRITICAL,
            **texts,
            "cost_of_inaction": {
                "description": "Portfolio-wide compliance gap premium",
                "estimated_chf_min": 50000,
                "estimated_chf_max": 500000,
                "confidence": "estimated",
            },
            "deadline_pressure": None,
            "social_proof": _SOCIAL_PROOF["portfolio_compliance"],
            "call_to_action": "Launch portfolio compliance program",
            "related_entity": {
                "entity_type": "organization",
                "entity_id": str(organization_id),
            },
        }
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_nudges(
    db: AsyncSession,
    building_id: UUID,
    context: str = "dashboard",
) -> list[dict]:
    """Generate behavioral nudges for a building.

    Context controls verbosity:
      - "dashboard": short headlines
      - "detail": full text
      - "email": formatted for notification

    Returns empty list if building not found.
    """
    # Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return []

    # Collect nudges from all generators
    nudges: list[dict] = []

    generators = [
        _expiring_diagnostic_nudges,
        _unaddressed_asbestos_nudges,
        _incomplete_dossier_nudges,
        _overdue_actions_nudges,
        _low_trust_score_nudges,
        _missing_suva_notification_nudges,
    ]

    for gen in generators:
        try:
            result_nudges = await gen(db, building_id, context)
            nudges.extend(result_nudges)
        except Exception:
            logger.exception("Nudge generator %s failed for building %s", gen.__name__, building_id)

    nudges.sort(key=_sort_key)
    return nudges


async def generate_portfolio_nudges(
    db: AsyncSession,
    organization_id: UUID,
    context: str = "dashboard",
) -> list[dict]:
    """Generate portfolio-level nudges for an organization.

    Returns empty list if organization has no buildings.
    """
    nudges: list[dict] = []

    try:
        portfolio_nudges = await _portfolio_risk_nudges(db, organization_id, context)
        nudges.extend(portfolio_nudges)
    except Exception:
        logger.exception("Portfolio nudge generator failed for org %s", organization_id)

    nudges.sort(key=_sort_key)
    return nudges
