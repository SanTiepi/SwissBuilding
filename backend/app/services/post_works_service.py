"""
SwissBuildingOS - Post-Works State Service

Lifecycle logic for post-works states: auto-generation from completed
interventions, before/after comparison, verification, and summaries.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.post_works_state import PostWorksState
from app.models.sample import Sample

logger = logging.getLogger(__name__)

# Mapping from intervention_type to the resulting state_type
_INTERVENTION_TYPE_TO_STATE: dict[str, str] = {
    "asbestos_removal": "removed",
    "desamiantage": "removed",
    "removal": "removed",
    "encapsulation": "encapsulated",
    "encapsulage": "encapsulated",
    "remediation": "treated",
    "assainissement": "treated",
}


async def generate_post_works_states(
    db: AsyncSession,
    building_id: UUID,
    intervention_id: UUID,
    recorded_by: UUID | None = None,
) -> list[PostWorksState]:
    """Generate PostWorksState records from a completed intervention.

    Examines positive samples in the building's diagnostics and creates one
    PostWorksState per positive sample/pollutant combination that doesn't
    already have a record for this intervention.
    """
    # 1. Load and validate intervention
    intervention = await db.get(Intervention, intervention_id)
    if intervention is None:
        raise ValueError(f"Intervention {intervention_id} not found")
    if intervention.building_id != building_id:
        raise ValueError(f"Intervention {intervention_id} does not belong to building {building_id}")
    if intervention.status != "completed":
        raise ValueError(f"Intervention {intervention_id} is not completed (status={intervention.status})")

    # 2. Determine state_type from intervention_type
    state_type = _INTERVENTION_TYPE_TO_STATE.get(intervention.intervention_type, "recheck_needed")

    # 3. Load positive samples from all building diagnostics
    stmt = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            and_(
                Diagnostic.building_id == building_id,
                Sample.threshold_exceeded.is_(True),
            )
        )
    )
    result = await db.execute(stmt)
    positive_samples = result.scalars().all()

    if not positive_samples:
        logger.info(
            "No positive samples found for building %s — no post-works states generated",
            building_id,
        )
        return []

    # 4. Load existing post-works states for this intervention to avoid duplicates
    existing_stmt = select(PostWorksState).where(
        and_(
            PostWorksState.building_id == building_id,
            PostWorksState.intervention_id == intervention_id,
        )
    )
    existing_result = await db.execute(existing_stmt)
    existing_states = existing_result.scalars().all()
    existing_keys = {(s.pollutant_type, s.title) for s in existing_states}

    # 5. Create new states
    created: list[PostWorksState] = []
    for sample in positive_samples:
        pollutant = sample.pollutant_type
        title = f"{state_type.replace('_', ' ').title()} — {pollutant or 'unknown'} — {sample.location_room or sample.sample_number}"
        key = (pollutant, title)
        if key in existing_keys:
            continue

        pws = PostWorksState(
            building_id=building_id,
            intervention_id=intervention_id,
            state_type=state_type,
            pollutant_type=pollutant,
            title=title,
            description=f"Auto-generated from intervention '{intervention.title}' for sample {sample.sample_number}",
            verified=False,
            recorded_by=recorded_by,
            recorded_at=datetime.now(UTC),
        )
        db.add(pws)
        created.append(pws)
        existing_keys.add(key)

    await db.flush()
    logger.info(
        "Generated %d post-works states for building %s, intervention %s",
        len(created),
        building_id,
        intervention_id,
    )
    return created


async def compare_before_after(
    db: AsyncSession,
    building_id: UUID,
    intervention_id: UUID | None = None,
) -> dict:
    """Return a before/after comparison for a building (optionally scoped to an intervention)."""
    # --- BEFORE: positive samples ---
    sample_stmt = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            and_(
                Diagnostic.building_id == building_id,
                Sample.threshold_exceeded.is_(True),
            )
        )
    )
    sample_result = await db.execute(sample_stmt)
    positive_samples = sample_result.scalars().all()

    before_by_pollutant: dict[str, int] = {}
    risk_areas: list[dict] = []
    for s in positive_samples:
        p = s.pollutant_type or "unknown"
        before_by_pollutant[p] = before_by_pollutant.get(p, 0) + 1
        risk_areas.append(
            {
                "pollutant": p,
                "location": s.location_room or s.location_detail or s.sample_number,
                "risk_level": s.risk_level or "unknown",
            }
        )

    # --- AFTER: post-works states ---
    pws_filters = [PostWorksState.building_id == building_id]
    if intervention_id is not None:
        pws_filters.append(PostWorksState.intervention_id == intervention_id)

    pws_stmt = select(PostWorksState).where(and_(*pws_filters))
    pws_result = await db.execute(pws_stmt)
    post_works = pws_result.scalars().all()

    state_types = [
        "removed",
        "remaining",
        "encapsulated",
        "treated",
        "unknown_after_intervention",
        "recheck_needed",
    ]
    after_counts: dict[str, int] = {st: 0 for st in state_types}
    after_by_pollutant: dict[str, dict[str, int]] = {}
    verified_count = 0

    for pw in post_works:
        st = pw.state_type
        if st in after_counts:
            after_counts[st] += 1
        p = pw.pollutant_type or "unknown"
        if p not in after_by_pollutant:
            after_by_pollutant[p] = {s: 0 for s in state_types}
        if st in after_by_pollutant[p]:
            after_by_pollutant[p][st] += 1
        if pw.verified:
            verified_count += 1

    total_pws = len(post_works)
    remediated = after_counts["removed"] + after_counts["treated"] + after_counts["encapsulated"]
    total_before = len(positive_samples)

    return {
        "building_id": str(building_id),
        "intervention_id": str(intervention_id) if intervention_id else None,
        "before": {
            "total_positive_samples": total_before,
            "by_pollutant": before_by_pollutant,
            "risk_areas": risk_areas,
        },
        "after": {
            **after_counts,
            "by_pollutant": after_by_pollutant,
        },
        "summary": {
            "remediation_rate": (remediated / total_before) if total_before > 0 else 0.0,
            "verification_rate": (verified_count / total_pws) if total_pws > 0 else 0.0,
            "residual_risk_count": (
                after_counts["remaining"] + after_counts["unknown_after_intervention"] + after_counts["recheck_needed"]
            ),
        },
    }


async def verify_post_works_state(
    db: AsyncSession,
    state_id: UUID,
    verified_by: UUID,
    notes: str | None = None,
) -> PostWorksState:
    """Mark a PostWorksState as verified."""
    state = await db.get(PostWorksState, state_id)
    if state is None:
        raise ValueError(f"PostWorksState {state_id} not found")

    state.verified = True
    state.verified_by = verified_by
    state.verified_at = datetime.now(UTC)
    if notes is not None:
        state.notes = notes

    await db.flush()
    logger.info("Verified PostWorksState %s by user %s", state_id, verified_by)
    return state


async def get_post_works_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Return an aggregated summary of all post-works states for a building."""
    stmt = select(PostWorksState).where(PostWorksState.building_id == building_id)
    result = await db.execute(stmt)
    states = result.scalars().all()

    by_state_type: dict[str, int] = {}
    by_pollutant: dict[str, int] = {}
    verified = 0
    intervention_ids: set[UUID] = set()

    for s in states:
        by_state_type[s.state_type] = by_state_type.get(s.state_type, 0) + 1
        p = s.pollutant_type or "unknown"
        by_pollutant[p] = by_pollutant.get(p, 0) + 1
        if s.verified:
            verified += 1
        if s.intervention_id is not None:
            intervention_ids.add(s.intervention_id)

    total = len(states)
    unverified = total - verified

    return {
        "building_id": str(building_id),
        "total_states": total,
        "by_state_type": by_state_type,
        "by_pollutant": by_pollutant,
        "verification_progress": {
            "verified": verified,
            "unverified": unverified,
            "rate": (verified / total) if total > 0 else 0.0,
        },
        "interventions_covered": len(intervention_ids),
    }
