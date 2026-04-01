"""Building Life Service — lifecycle calendar for ongoing building operations.

Aggregates deadlines from obligations, insurance policies, contracts, leases,
interventions, diagnostics, compliance artefacts, and form instances into a
unified calendar with summary and monthly grouping.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DIAGNOSTIC_VALIDITY_YEARS
from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.contract import Contract
from app.models.diagnostic import Diagnostic
from app.models.form_instance import FormInstance
from app.models.insurance_policy import InsurancePolicy
from app.models.intervention import Intervention
from app.models.lease import Lease
from app.models.obligation import Obligation
from app.models.recurring_service import RecurringService, WarrantyRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EVENT_TYPE_LABELS = {
    "obligation": "Obligation",
    "insurance": "Assurance",
    "contract": "Contrat",
    "lease": "Bail",
    "diagnostic_expiry": "Expiration diagnostic",
    "intervention": "Intervention",
    "form": "Formulaire",
    "compliance": "Conformite",
    "recurring_service": "Service recurrent",
    "warranty_expiry": "Expiration garantie",
}

EVENT_TYPE_ACTIONS = {
    "obligation": "Verifier",
    "insurance": "Renouveler",
    "contract": "Renouveler",
    "lease": "Renouveler",
    "diagnostic_expiry": "Commander",
    "intervention": "Planifier",
    "form": "Soumettre",
    "compliance": "Soumettre",
    "recurring_service": "Planifier le service",
    "warranty_expiry": "Verifier la couverture",
}


def _status_and_priority(event_date: date, today: date, completed: bool = False) -> tuple[str, str, int]:
    """Return (status, priority, days_remaining)."""
    if completed:
        return "completed", "low", 0
    days = (event_date - today).days
    if days < 0:
        return "overdue", "critical", days
    if days <= 7:
        return "due_soon", "critical", days
    if days <= 30:
        return "due_soon", "high", days
    if days <= 90:
        return "upcoming", "medium", days
    return "upcoming", "low", days


def _make_event(
    *,
    event_id: str,
    event_date: date,
    event_type: str,
    title: str,
    description: str,
    building_id: UUID,
    source_id: UUID | None,
    source_type: str,
    today: date,
    completed: bool = False,
    action_override: str | None = None,
) -> dict:
    status, priority, days_remaining = _status_and_priority(event_date, today, completed)
    return {
        "id": event_id,
        "date": event_date.isoformat(),
        "type": event_type,
        "title": title,
        "description": description,
        "building_id": str(building_id),
        "source_id": str(source_id) if source_id else None,
        "source_type": source_type,
        "status": status,
        "days_remaining": days_remaining,
        "action_required": action_override or EVENT_TYPE_ACTIONS.get(event_type),
        "priority": priority,
    }


def _safe_date(val) -> date | None:
    """Extract a date from a date, datetime, or None."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None


# ---------------------------------------------------------------------------
# Collectors — each returns a list of event dicts
# ---------------------------------------------------------------------------


async def _collect_obligations(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(select(Obligation).where(Obligation.building_id == building_id))
    obligations = list(result.scalars().all())
    events = []
    for ob in obligations:
        d = _safe_date(ob.due_date)
        if d is None:
            continue
        if d > horizon and ob.status not in ("overdue",):
            continue
        completed = ob.status in ("completed", "cancelled")
        events.append(
            _make_event(
                event_id=f"obl-{ob.id}",
                event_date=d,
                event_type="obligation",
                title=ob.title,
                description=ob.description or f"Obligation {ob.obligation_type}",
                building_id=building_id,
                source_id=ob.id,
                source_type="obligation",
                today=today,
                completed=completed,
                action_override=EVENT_TYPE_ACTIONS.get("obligation"),
            )
        )
    return events


async def _collect_insurance(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(select(InsurancePolicy).where(InsurancePolicy.building_id == building_id))
    policies = list(result.scalars().all())
    events = []
    for pol in policies:
        end = _safe_date(pol.date_end)
        if end is None:
            continue
        if end > horizon and pol.status not in ("expired",):
            continue
        completed = pol.status in ("expired", "cancelled")
        events.append(
            _make_event(
                event_id=f"ins-{pol.id}",
                event_date=end,
                event_type="insurance",
                title=f"Renouvellement assurance: {pol.policy_type}",
                description=f"Police {pol.policy_number} — {pol.insurer_name}",
                building_id=building_id,
                source_id=pol.id,
                source_type="insurance_policy",
                today=today,
                completed=completed,
            )
        )
    return events


async def _collect_contracts(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(select(Contract).where(Contract.building_id == building_id))
    contracts = list(result.scalars().all())
    events = []
    for c in contracts:
        end = _safe_date(c.date_end)
        if end is None:
            continue
        if end > horizon and c.status not in ("expired",):
            continue
        completed = c.status in ("terminated", "expired")
        action = "Renouveler" if c.auto_renewal else "Decider du renouvellement"
        # Also generate a notice-period reminder if applicable
        if c.notice_period_months and not completed:
            notice_date = end - timedelta(days=c.notice_period_months * 30)
            if notice_date >= today or notice_date >= today - timedelta(days=30):
                events.append(
                    _make_event(
                        event_id=f"ctr-notice-{c.id}",
                        event_date=notice_date,
                        event_type="contract",
                        title=f"Preavis de resiliation: {c.title}",
                        description=f"Delai de preavis de {c.notice_period_months} mois avant echeance du contrat",
                        building_id=building_id,
                        source_id=c.id,
                        source_type="contract",
                        today=today,
                        completed=completed,
                        action_override="Notifier la resiliation ou confirmer le renouvellement",
                    )
                )
        events.append(
            _make_event(
                event_id=f"ctr-{c.id}",
                event_date=end,
                event_type="contract",
                title=f"Echeance contrat: {c.title}",
                description=f"Contrat {c.contract_type} — ref. {c.reference_code}",
                building_id=building_id,
                source_id=c.id,
                source_type="contract",
                today=today,
                completed=completed,
                action_override=action,
            )
        )
    return events


async def _collect_leases(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(select(Lease).where(Lease.building_id == building_id))
    leases = list(result.scalars().all())
    events = []
    for le in leases:
        end = _safe_date(le.date_end)
        if end is None:
            continue
        if end > horizon and le.status not in ("expired",):
            continue
        completed = le.status in ("terminated", "expired")
        # Notice period reminder
        if le.notice_period_months and not completed:
            notice_date = end - timedelta(days=le.notice_period_months * 30)
            if notice_date >= today or notice_date >= today - timedelta(days=30):
                events.append(
                    _make_event(
                        event_id=f"lea-notice-{le.id}",
                        event_date=notice_date,
                        event_type="lease",
                        title=f"Preavis bail: {le.reference_code}",
                        description=f"Delai de preavis de {le.notice_period_months} mois avant echeance du bail",
                        building_id=building_id,
                        source_id=le.id,
                        source_type="lease",
                        today=today,
                        completed=completed,
                        action_override="Notifier le conge ou confirmer la reconduction",
                    )
                )
        events.append(
            _make_event(
                event_id=f"lea-{le.id}",
                event_date=end,
                event_type="lease",
                title=f"Echeance bail: {le.reference_code}",
                description=f"Bail {le.lease_type}",
                building_id=building_id,
                source_id=le.id,
                source_type="lease",
                today=today,
                completed=completed,
            )
        )
    return events


async def _collect_diagnostics(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(result.scalars().all())
    events = []
    for diag in diagnostics:
        diag_date = _safe_date(diag.date_report) or _safe_date(getattr(diag, "date_inspection", None))
        if diag_date is None:
            continue
        validity = DIAGNOSTIC_VALIDITY_YEARS.get(diag.diagnostic_type, 5)
        try:
            exp = date(diag_date.year + validity, diag_date.month, diag_date.day)
        except ValueError:
            exp = date(diag_date.year + validity, diag_date.month, 28)
        if exp > horizon and exp >= today:
            continue
        completed = diag.status == "validated" and exp > today
        events.append(
            _make_event(
                event_id=f"diag-exp-{diag.id}",
                event_date=exp,
                event_type="diagnostic_expiry",
                title=f"Expiration diagnostic {diag.diagnostic_type}",
                description=f"Diagnostic du {diag_date.isoformat()} — validite {validity} ans",
                building_id=building_id,
                source_id=diag.id,
                source_type="diagnostic",
                today=today,
                completed=completed,
                action_override="Commander un nouveau diagnostic",
            )
        )
    return events


async def _collect_interventions(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(result.scalars().all())
    events = []
    for intv in interventions:
        completed = intv.status == "completed"
        start = _safe_date(intv.date_start)
        end = _safe_date(intv.date_end)
        if start and (start <= horizon or start < today):
            events.append(
                _make_event(
                    event_id=f"intv-start-{intv.id}",
                    event_date=start,
                    event_type="intervention",
                    title=f"Debut intervention: {intv.title}",
                    description=f"Intervention {intv.intervention_type}",
                    building_id=building_id,
                    source_id=intv.id,
                    source_type="intervention",
                    today=today,
                    completed=completed,
                    action_override="Preparer le chantier",
                )
            )
        if end and (end <= horizon or end < today):
            events.append(
                _make_event(
                    event_id=f"intv-end-{intv.id}",
                    event_date=end,
                    event_type="intervention",
                    title=f"Fin intervention: {intv.title}",
                    description=f"Intervention {intv.intervention_type}",
                    building_id=building_id,
                    source_id=intv.id,
                    source_type="intervention",
                    today=today,
                    completed=completed,
                    action_override="Verifier les travaux",
                )
            )
    return events


async def _collect_compliance(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = list(result.scalars().all())
    events = []
    for art in artefacts:
        exp = _safe_date(getattr(art, "expires_at", None))
        if exp and (exp <= horizon or exp < today):
            completed = art.status in ("approved", "acknowledged")
            events.append(
                _make_event(
                    event_id=f"comp-exp-{art.id}",
                    event_date=exp,
                    event_type="compliance",
                    title=f"Expiration artefact: {art.title}",
                    description=f"Artefact {art.artefact_type} — autorite {art.authority_name or 'N/A'}",
                    building_id=building_id,
                    source_id=art.id,
                    source_type="compliance_artefact",
                    today=today,
                    completed=completed,
                    action_override="Renouveler la soumission",
                )
            )
    return events


async def _collect_forms(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(select(FormInstance).where(FormInstance.building_id == building_id))
    forms = list(result.scalars().all())
    events = []
    for fi in forms:
        if fi.status in ("submitted", "acknowledged", "rejected"):
            continue
        # Use created_at + 30d as a soft deadline for pending forms
        created = _safe_date(fi.created_at)
        if created is None:
            continue
        soft_deadline = created + timedelta(days=30)
        if soft_deadline > horizon and soft_deadline >= today:
            continue
        events.append(
            _make_event(
                event_id=f"form-{fi.id}",
                event_date=soft_deadline,
                event_type="form",
                title=f"Formulaire en attente (statut: {fi.status})",
                description=f"Formulaire cree le {created.isoformat()}",
                building_id=building_id,
                source_id=fi.id,
                source_type="form_instance",
                today=today,
                completed=False,
                action_override="Completer et soumettre",
            )
        )
    return events


async def _collect_recurring_services(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(
        select(RecurringService).where(
            RecurringService.building_id == building_id,
            RecurringService.status == "active",
        )
    )
    services = list(result.scalars().all())
    events = []
    for svc in services:
        next_d = _safe_date(svc.next_service_date)
        if next_d is None:
            continue
        if next_d > horizon:
            continue
        events.append(
            _make_event(
                event_id=f"svc-{svc.id}",
                event_date=next_d,
                event_type="recurring_service",
                title=f"Service: {svc.service_type} — {svc.provider_name}",
                description=f"Frequence: {svc.frequency}"
                + (f" | Ref: {svc.contract_reference}" if svc.contract_reference else ""),
                building_id=building_id,
                source_id=svc.id,
                source_type="recurring_service",
                today=today,
                completed=False,
            )
        )
    return events


async def _collect_warranty_expiry(db: AsyncSession, building_id: UUID, today: date, horizon: date) -> list[dict]:
    result = await db.execute(
        select(WarrantyRecord).where(
            WarrantyRecord.building_id == building_id,
            WarrantyRecord.status == "active",
        )
    )
    warranties = list(result.scalars().all())
    events = []
    for w in warranties:
        end = _safe_date(w.end_date)
        if end is None:
            continue
        if end > horizon and end >= today:
            continue
        events.append(
            _make_event(
                event_id=f"war-exp-{w.id}",
                event_date=end,
                event_type="warranty_expiry",
                title=f"Expiration garantie: {w.subject}",
                description=f"Garantie {w.warranty_type} — {w.provider_name}",
                building_id=building_id,
                source_id=w.id,
                source_type="warranty_record",
                today=today,
                completed=False,
            )
        )
    return events


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------


async def get_building_calendar(
    db: AsyncSession,
    building_id: UUID,
    horizon_days: int = 365,
) -> dict | None:
    """Generate a calendar of upcoming events for a building."""
    # Verify building exists
    result = await db.execute(select(Building.id).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        return None

    today = date.today()
    horizon = today + timedelta(days=horizon_days)

    # Collect from all sources
    all_events: list[dict] = []
    all_events.extend(await _collect_obligations(db, building_id, today, horizon))
    all_events.extend(await _collect_insurance(db, building_id, today, horizon))
    all_events.extend(await _collect_contracts(db, building_id, today, horizon))
    all_events.extend(await _collect_leases(db, building_id, today, horizon))
    all_events.extend(await _collect_diagnostics(db, building_id, today, horizon))
    all_events.extend(await _collect_interventions(db, building_id, today, horizon))
    all_events.extend(await _collect_compliance(db, building_id, today, horizon))
    all_events.extend(await _collect_forms(db, building_id, today, horizon))
    all_events.extend(await _collect_recurring_services(db, building_id, today, horizon))
    all_events.extend(await _collect_warranty_expiry(db, building_id, today, horizon))

    # Sort by date
    all_events.sort(key=lambda e: e["date"])

    # Summary
    overdue_count = sum(1 for e in all_events if e["status"] == "overdue")
    due_30d = sum(1 for e in all_events if e["status"] in ("due_soon", "overdue") and e["days_remaining"] <= 30)
    due_90d = sum(
        1 for e in all_events if e["status"] in ("due_soon", "upcoming", "overdue") and e["days_remaining"] <= 90
    )
    due_365d = sum(1 for e in all_events if e["status"] != "completed")

    # Group by month
    by_month: dict[str, list[dict]] = defaultdict(list)
    for ev in all_events:
        month_key = ev["date"][:7]  # "YYYY-MM"
        by_month[month_key].append(ev)

    return {
        "events": all_events,
        "summary": {
            "total_events": len(all_events),
            "overdue": overdue_count,
            "due_30d": due_30d,
            "due_90d": due_90d,
            "due_365d": due_365d,
        },
        "by_month": dict(sorted(by_month.items())),
    }


async def get_annual_review(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Generate an annual building review summary."""
    result = await db.execute(select(Building.id).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        return None

    today = date.today()
    year_start = date(today.year, 1, 1)
    year_end = date(today.year, 12, 31)

    # Diagnostics status
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    diag_summary = {"valid": 0, "expiring": 0, "expired": 0}
    for diag in diagnostics:
        diag_date = _safe_date(diag.date_report) or _safe_date(getattr(diag, "date_inspection", None))
        if diag_date is None:
            continue
        validity = DIAGNOSTIC_VALIDITY_YEARS.get(diag.diagnostic_type, 5)
        try:
            exp = date(diag_date.year + validity, diag_date.month, diag_date.day)
        except ValueError:
            exp = date(diag_date.year + validity, diag_date.month, 28)
        if exp < today:
            diag_summary["expired"] += 1
        elif exp <= year_end:
            diag_summary["expiring"] += 1
        else:
            diag_summary["valid"] += 1

    # Interventions completed this year
    intv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intv_result.scalars().all())
    completed_this_year = [
        i
        for i in interventions
        if i.status == "completed"
        and i.date_end
        and _safe_date(i.date_end)
        and year_start <= _safe_date(i.date_end) <= year_end
    ]

    # Open obligations
    ob_result = await db.execute(
        select(Obligation).where(
            Obligation.building_id == building_id,
            Obligation.status.in_(["upcoming", "due_soon", "overdue"]),
        )
    )
    open_obligations = list(ob_result.scalars().all())

    # Insurance coverage
    ins_result = await db.execute(
        select(InsurancePolicy).where(
            InsurancePolicy.building_id == building_id,
            InsurancePolicy.status == "active",
        )
    )
    active_policies = list(ins_result.scalars().all())
    policies_expiring = [
        p for p in active_policies if p.date_end and _safe_date(p.date_end) and _safe_date(p.date_end) <= year_end
    ]

    # Contracts renewing
    ctr_result = await db.execute(
        select(Contract).where(
            Contract.building_id == building_id,
            Contract.status == "active",
        )
    )
    active_contracts = list(ctr_result.scalars().all())
    contracts_ending = [
        c for c in active_contracts if c.date_end and _safe_date(c.date_end) and _safe_date(c.date_end) <= year_end
    ]

    # Recommendations
    recommendations: list[str] = []
    if diag_summary["expired"] > 0:
        recommendations.append(f"Commander {diag_summary['expired']} diagnostic(s) expire(s)")
    if diag_summary["expiring"] > 0:
        recommendations.append(
            f"Planifier le renouvellement de {diag_summary['expiring']} diagnostic(s) expirant cette annee"
        )
    if len(open_obligations) > 0:
        overdue_obs = [o for o in open_obligations if o.status == "overdue"]
        if overdue_obs:
            recommendations.append(f"Traiter {len(overdue_obs)} obligation(s) en retard en priorite")
    if policies_expiring:
        recommendations.append(f"Renouveler {len(policies_expiring)} police(s) d'assurance avant echeance")
    if contracts_ending:
        recommendations.append(f"Decider du renouvellement de {len(contracts_ending)} contrat(s)")
    if not recommendations:
        recommendations.append("Aucune action urgente — le batiment est bien gere")

    return {
        "building_id": str(building_id),
        "year": today.year,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "diagnostics": diag_summary,
        "interventions_completed": len(completed_this_year),
        "open_obligations": len(open_obligations),
        "overdue_obligations": sum(1 for o in open_obligations if o.status == "overdue"),
        "insurance_coverage": {
            "active_policies": len(active_policies),
            "expiring_this_year": len(policies_expiring),
        },
        "contracts": {
            "active": len(active_contracts),
            "ending_this_year": len(contracts_ending),
        },
        "recommendations": recommendations,
    }
