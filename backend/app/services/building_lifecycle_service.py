"""Building Lifecycle Service.

Derives lifecycle phases from diagnostic, intervention, and compliance artefact state:
  unknown → assessed → diagnosed → planned → in_remediation → cleared → monitored
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.post_works_state import PostWorksState

# Ordered lifecycle phases
PHASES = [
    "unknown",
    "assessed",
    "diagnosed",
    "planned",
    "in_remediation",
    "cleared",
    "monitored",
]

PHASE_LABELS = {
    "unknown": "Unknown",
    "assessed": "Assessed",
    "diagnosed": "Diagnosed",
    "planned": "Planned",
    "in_remediation": "In Remediation",
    "cleared": "Cleared",
    "monitored": "Monitored",
}


async def _building_exists(db: AsyncSession, building_id: UUID) -> bool:
    result = await db.execute(select(Building.id).where(Building.id == building_id))
    return result.scalar_one_or_none() is not None


async def _get_diagnostics(db: AsyncSession, building_id: UUID) -> list:
    result = await db.execute(
        select(Diagnostic).where(Diagnostic.building_id == building_id).order_by(Diagnostic.created_at)
    )
    return list(result.scalars().all())


async def _get_interventions(db: AsyncSession, building_id: UUID) -> list:
    result = await db.execute(
        select(Intervention).where(Intervention.building_id == building_id).order_by(Intervention.created_at)
    )
    return list(result.scalars().all())


async def _get_compliance_artefacts(db: AsyncSession, building_id: UUID) -> list:
    result = await db.execute(
        select(ComplianceArtefact)
        .where(ComplianceArtefact.building_id == building_id)
        .order_by(ComplianceArtefact.created_at)
    )
    return list(result.scalars().all())


async def _get_post_works(db: AsyncSession, building_id: UUID) -> list:
    result = await db.execute(
        select(PostWorksState).where(PostWorksState.building_id == building_id).order_by(PostWorksState.recorded_at)
    )
    return list(result.scalars().all())


def _derive_phase_and_transitions(
    diagnostics: list,
    interventions: list,
    artefacts: list,
    post_works: list,
    building_created_at: datetime | None,
) -> tuple[str, list[dict]]:
    """Derive the current phase and transition history from artefacts."""
    transitions: list[dict] = []
    now = datetime.now(UTC)

    # Start at unknown when building was created
    base_time = building_created_at or now
    transitions.append({"phase": "unknown", "entered_at": base_time, "trigger": "building_created"})

    # assessed: at least one diagnostic exists (any status)
    any_diag = [d for d in diagnostics if d.status in ("draft", "in_progress", "completed", "validated")]
    if any_diag:
        earliest = min(d.created_at for d in any_diag)
        transitions.append({"phase": "assessed", "entered_at": earliest, "trigger": "diagnostic_created"})

    # diagnosed: at least one diagnostic is completed or validated
    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed_diags:
        earliest = min(d.date_report or d.updated_at or d.created_at for d in completed_diags)
        transitions.append({"phase": "diagnosed", "entered_at": earliest, "trigger": "diagnostic_completed"})

    # planned: at least one intervention is planned
    planned_interventions = [i for i in interventions if i.status == "planned"]
    if planned_interventions:
        earliest = min(i.created_at for i in planned_interventions)
        transitions.append({"phase": "planned", "entered_at": earliest, "trigger": "intervention_planned"})

    # in_remediation: at least one intervention is in_progress
    active_interventions = [i for i in interventions if i.status == "in_progress"]
    if active_interventions:
        earliest = min(i.date_start or i.created_at for i in active_interventions)
        transitions.append({"phase": "in_remediation", "entered_at": earliest, "trigger": "intervention_started"})

    # cleared: all interventions completed + compliance artefact approved or post-works verified
    completed_interventions = [i for i in interventions if i.status == "completed"]
    approved_artefacts = [a for a in artefacts if a.status == "approved"]
    verified_post_works = [p for p in post_works if p.verified]

    if completed_interventions and (approved_artefacts or verified_post_works):
        timestamps = []
        if completed_interventions:
            timestamps.append(max(i.date_end or i.updated_at or i.created_at for i in completed_interventions))
        if approved_artefacts:
            timestamps.append(max(a.acknowledged_at or a.updated_at or a.created_at for a in approved_artefacts))
        if verified_post_works:
            timestamps.append(max(p.verified_at or p.recorded_at for p in verified_post_works))
        transitions.append(
            {
                "phase": "cleared",
                "entered_at": max(timestamps),
                "trigger": "remediation_cleared",
            }
        )

    # monitored: cleared + ongoing monitoring artefacts
    monitoring_artefacts = [a for a in artefacts if a.artefact_type == "monitoring_plan" and a.status == "active"]
    if len(transitions) > 0 and transitions[-1]["phase"] == "cleared" and monitoring_artefacts:
        earliest = min(a.created_at for a in monitoring_artefacts)
        transitions.append({"phase": "monitored", "entered_at": earliest, "trigger": "monitoring_started"})

    # Sort by entered_at
    transitions.sort(key=lambda t: t["entered_at"])

    current_phase = transitions[-1]["phase"] if transitions else "unknown"
    return current_phase, transitions


async def get_lifecycle_phase(db: AsyncSession, building_id: UUID) -> dict:
    """Get the current lifecycle phase for a building."""
    if not await _building_exists(db, building_id):
        return None

    building = (await db.execute(select(Building).where(Building.id == building_id))).scalar_one()
    diagnostics = await _get_diagnostics(db, building_id)
    interventions = await _get_interventions(db, building_id)
    artefacts = await _get_compliance_artefacts(db, building_id)
    post_works = await _get_post_works(db, building_id)

    current_phase, transitions = _derive_phase_and_transitions(
        diagnostics, interventions, artefacts, post_works, building.created_at
    )

    last_transition = transitions[-1] if transitions else None

    return {
        "building_id": building_id,
        "phase": current_phase,
        "phase_label": PHASE_LABELS.get(current_phase, current_phase),
        "entered_at": last_transition["entered_at"] if last_transition else None,
        "trigger": last_transition.get("trigger") if last_transition else None,
        "evaluated_at": datetime.now(UTC),
    }


async def get_lifecycle_timeline(db: AsyncSession, building_id: UUID) -> dict | None:
    """Get the full lifecycle timeline for a building."""
    if not await _building_exists(db, building_id):
        return None

    building = (await db.execute(select(Building).where(Building.id == building_id))).scalar_one()
    diagnostics = await _get_diagnostics(db, building_id)
    interventions = await _get_interventions(db, building_id)
    artefacts = await _get_compliance_artefacts(db, building_id)
    post_works = await _get_post_works(db, building_id)

    current_phase, transitions = _derive_phase_and_transitions(
        diagnostics, interventions, artefacts, post_works, building.created_at
    )

    now = datetime.now(UTC)
    enriched: list[dict] = []
    for i, t in enumerate(transitions):
        entered = t["entered_at"]
        exited = transitions[i + 1]["entered_at"] if i + 1 < len(transitions) else None
        ref = exited or now
        # Normalize to naive datetimes for duration calculation
        entered_naive = entered.replace(tzinfo=None) if hasattr(entered, "tzinfo") and entered.tzinfo else entered
        ref_naive = ref.replace(tzinfo=None) if hasattr(ref, "tzinfo") and ref.tzinfo else ref
        duration = (ref_naive - entered_naive).days

        enriched.append(
            {
                "phase": t["phase"],
                "entered_at": entered,
                "exited_at": exited,
                "duration_days": max(0, duration),
                "trigger": t.get("trigger"),
            }
        )

    total = sum(e["duration_days"] or 0 for e in enriched)

    return {
        "building_id": building_id,
        "current_phase": current_phase,
        "transitions": enriched,
        "total_days_tracked": total,
        "evaluated_at": now,
    }


async def predict_next_phase(db: AsyncSession, building_id: UUID) -> dict | None:
    """Predict the next lifecycle phase and what conditions must be met."""
    if not await _building_exists(db, building_id):
        return None

    building = (await db.execute(select(Building).where(Building.id == building_id))).scalar_one()
    diagnostics = await _get_diagnostics(db, building_id)
    interventions = await _get_interventions(db, building_id)
    artefacts = await _get_compliance_artefacts(db, building_id)
    post_works = await _get_post_works(db, building_id)

    current_phase, _ = _derive_phase_and_transitions(
        diagnostics, interventions, artefacts, post_works, building.created_at
    )

    phase_idx = PHASES.index(current_phase)
    next_phase = PHASES[phase_idx + 1] if phase_idx + 1 < len(PHASES) else None

    conditions: list[dict] = []
    estimated_days = None

    if current_phase == "unknown":
        has_diag = len(diagnostics) > 0
        conditions.append(
            {
                "condition": "Create at least one diagnostic",
                "met": has_diag,
                "details": f"{len(diagnostics)} diagnostic(s) exist" if has_diag else None,
            }
        )
        if not has_diag:
            estimated_days = 14

    elif current_phase == "assessed":
        completed = any(d.status in ("completed", "validated") for d in diagnostics)
        conditions.append(
            {
                "condition": "Complete or validate at least one diagnostic",
                "met": completed,
                "details": None,
            }
        )
        if not completed:
            estimated_days = 30

    elif current_phase == "diagnosed":
        has_planned = any(i.status == "planned" for i in interventions)
        conditions.append(
            {
                "condition": "Plan at least one intervention",
                "met": has_planned,
                "details": None,
            }
        )
        if not has_planned:
            estimated_days = 60

    elif current_phase == "planned":
        has_active = any(i.status == "in_progress" for i in interventions)
        conditions.append(
            {
                "condition": "Start at least one intervention",
                "met": has_active,
                "details": None,
            }
        )
        if not has_active:
            estimated_days = 30

    elif current_phase == "in_remediation":
        all_completed = all(i.status == "completed" for i in interventions) and len(interventions) > 0
        has_approval = any(a.status == "approved" for a in artefacts) or any(p.verified for p in post_works)
        conditions.append(
            {
                "condition": "Complete all interventions",
                "met": all_completed,
                "details": None,
            }
        )
        conditions.append(
            {
                "condition": "Obtain compliance approval or verified post-works",
                "met": has_approval,
                "details": None,
            }
        )
        if not (all_completed and has_approval):
            estimated_days = 90

    elif current_phase == "cleared":
        has_monitoring = any(a.artefact_type == "monitoring_plan" and a.status == "active" for a in artefacts)
        conditions.append(
            {
                "condition": "Establish active monitoring plan",
                "met": has_monitoring,
                "details": None,
            }
        )
        if not has_monitoring:
            estimated_days = 30

    elif current_phase == "monitored":
        # Terminal phase — no next
        pass

    met_count = sum(1 for c in conditions if c["met"])

    return {
        "building_id": building_id,
        "current_phase": current_phase,
        "next_phase": next_phase,
        "conditions": conditions,
        "conditions_met": met_count,
        "conditions_total": len(conditions),
        "estimated_days_to_transition": estimated_days,
        "evaluated_at": datetime.now(UTC),
    }


async def get_portfolio_lifecycle_distribution(db: AsyncSession, org_id: UUID) -> dict | None:
    """Get lifecycle distribution across buildings for an organization."""
    # Verify org exists
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if org is None:
        return None

    # Get buildings whose creator belongs to this org
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return {
            "organization_id": org_id,
            "total_buildings": 0,
            "distribution": [
                {"phase": p, "phase_label": PHASE_LABELS[p], "count": 0, "avg_days_in_phase": None} for p in PHASES
            ],
            "bottleneck_phase": None,
            "bottleneck_count": 0,
            "evaluated_at": datetime.now(UTC),
        }

    phase_counts: dict[str, int] = {p: 0 for p in PHASES}
    phase_days: dict[str, list[int]] = {p: [] for p in PHASES}

    for building in buildings:
        diagnostics = await _get_diagnostics(db, building.id)
        interventions = await _get_interventions(db, building.id)
        artefacts = await _get_compliance_artefacts(db, building.id)
        post_works = await _get_post_works(db, building.id)

        current_phase, transitions = _derive_phase_and_transitions(
            diagnostics, interventions, artefacts, post_works, building.created_at
        )
        phase_counts[current_phase] += 1

        # Track time in current phase
        if transitions:
            last = transitions[-1]
            entered = last["entered_at"]
            now = datetime.now(UTC)
            if hasattr(entered, "tzinfo") and entered.tzinfo is None:
                days = (now.replace(tzinfo=None) - entered).days
            else:
                days = (now - entered).days
            phase_days[current_phase].append(max(0, days))

    distribution = []
    for p in PHASES:
        avg = sum(phase_days[p]) / len(phase_days[p]) if phase_days[p] else None
        distribution.append(
            {
                "phase": p,
                "phase_label": PHASE_LABELS[p],
                "count": phase_counts[p],
                "avg_days_in_phase": round(avg, 1) if avg is not None else None,
            }
        )

    # Find bottleneck (phase with most buildings, excluding unknown and terminal)
    non_terminal = {p: c for p, c in phase_counts.items() if p not in ("unknown", "monitored") and c > 0}
    bottleneck_phase = max(non_terminal, key=non_terminal.get) if non_terminal else None
    bottleneck_count = non_terminal.get(bottleneck_phase, 0) if bottleneck_phase else 0

    return {
        "organization_id": org_id,
        "total_buildings": len(buildings),
        "distribution": distribution,
        "bottleneck_phase": bottleneck_phase,
        "bottleneck_count": bottleneck_count,
        "evaluated_at": datetime.now(UTC),
    }
