"""
BatiConnect - Building Genealogy Service

Models the building's history: transformation episodes, ownership changes,
historical claims. Merges with existing BuildingEvent from change grammar
to produce a unified genealogy timeline.

The declared-vs-observed comparison flags discrepancies between what is
historically claimed and what is currently observed.
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_change import BuildingEvent
from app.models.building_genealogy import (
    HistoricalClaim,
    OwnershipEpisode,
    TransformationEpisode,
)
from app.schemas.building_genealogy import (
    BuildingGenealogyResponse,
    DeclaredVsObservedDiscrepancy,
    DeclaredVsObservedResponse,
    GenealogyTimeline,
    GenealogyTimelineEntry,
    HistoricalClaimCreate,
    HistoricalClaimRead,
    OwnershipEpisodeCreate,
    OwnershipEpisodeRead,
    TransformationEpisodeCreate,
    TransformationEpisodeRead,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Full genealogy
# ---------------------------------------------------------------------------


async def get_building_genealogy(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingGenealogyResponse:
    """Get complete building genealogy: transformations, ownership, historical claims.

    Ordered chronologically within each category.
    """
    # Transformations
    t_result = await db.execute(
        select(TransformationEpisode)
        .where(TransformationEpisode.building_id == building_id)
        .order_by(TransformationEpisode.period_start.asc().nullslast())
    )
    transformations = list(t_result.scalars().all())

    # Ownership episodes
    o_result = await db.execute(
        select(OwnershipEpisode)
        .where(OwnershipEpisode.building_id == building_id)
        .order_by(OwnershipEpisode.period_start.asc().nullslast())
    )
    ownership_episodes = list(o_result.scalars().all())

    # Historical claims
    c_result = await db.execute(
        select(HistoricalClaim)
        .where(HistoricalClaim.building_id == building_id)
        .order_by(HistoricalClaim.reference_date.asc().nullslast())
    )
    claims = list(c_result.scalars().all())

    return BuildingGenealogyResponse(
        building_id=building_id,
        transformations=[TransformationEpisodeRead.model_validate(t) for t in transformations],
        ownership_episodes=[OwnershipEpisodeRead.model_validate(o) for o in ownership_episodes],
        historical_claims=[HistoricalClaimRead.model_validate(c) for c in claims],
    )


# ---------------------------------------------------------------------------
# Add transformation
# ---------------------------------------------------------------------------


async def add_transformation(
    db: AsyncSession,
    building_id: UUID,
    data: TransformationEpisodeCreate,
) -> TransformationEpisode:
    """Record a transformation episode."""
    episode = TransformationEpisode(
        building_id=building_id,
        episode_type=data.episode_type,
        title=data.title,
        description=data.description,
        period_start=data.period_start,
        period_end=data.period_end,
        approximate=data.approximate,
        evidence_basis=data.evidence_basis,
        evidence_ids=[str(eid) for eid in data.evidence_ids] if data.evidence_ids else None,
        spatial_scope=data.spatial_scope,
        state_before_summary=data.state_before_summary,
        state_after_summary=data.state_after_summary,
    )
    db.add(episode)
    await db.flush()
    return episode


# ---------------------------------------------------------------------------
# Add ownership episode
# ---------------------------------------------------------------------------


async def add_ownership_episode(
    db: AsyncSession,
    building_id: UUID,
    data: OwnershipEpisodeCreate,
) -> OwnershipEpisode:
    """Record an ownership episode."""
    episode = OwnershipEpisode(
        building_id=building_id,
        owner_name=data.owner_name,
        owner_type=data.owner_type,
        period_start=data.period_start,
        period_end=data.period_end,
        approximate=data.approximate,
        evidence_basis=data.evidence_basis,
        source_document_id=data.source_document_id,
        acquisition_type=data.acquisition_type,
    )
    db.add(episode)
    await db.flush()
    return episode


# ---------------------------------------------------------------------------
# Add historical claim
# ---------------------------------------------------------------------------


async def add_historical_claim(
    db: AsyncSession,
    building_id: UUID,
    data: HistoricalClaimCreate,
) -> HistoricalClaim:
    """Record a historical claim."""
    claim = HistoricalClaim(
        building_id=building_id,
        claim_type=data.claim_type,
        subject=data.subject,
        assertion=data.assertion,
        reference_date=data.reference_date,
        period_start=data.period_start,
        period_end=data.period_end,
        evidence_basis=data.evidence_basis,
        confidence=data.confidence,
        source_description=data.source_description,
        status=data.status,
    )
    db.add(claim)
    await db.flush()
    return claim


# ---------------------------------------------------------------------------
# Unified genealogy timeline
# ---------------------------------------------------------------------------


def _sort_key(entry: GenealogyTimelineEntry) -> date:
    """Return a date for sorting, defaulting to date.min when None."""
    return entry.occurred_at or entry.period_start or date.min


async def get_genealogy_timeline(
    db: AsyncSession,
    building_id: UUID,
    limit: int = 100,
) -> GenealogyTimeline:
    """Unified chronological timeline: transformations + ownership + claims + events.

    Merges with BuildingEvent from change grammar.
    """
    entries: list[GenealogyTimelineEntry] = []

    # ── Transformations ──────────────────────────────────────────
    t_result = await db.execute(select(TransformationEpisode).where(TransformationEpisode.building_id == building_id))
    for t in t_result.scalars().all():
        entries.append(
            GenealogyTimelineEntry(
                id=t.id,
                entry_type="transformation",
                occurred_at=t.period_start,
                period_start=t.period_start,
                period_end=t.period_end,
                title=t.title,
                description=t.description,
                evidence_basis=t.evidence_basis,
                metadata={
                    "episode_type": t.episode_type,
                    "approximate": t.approximate,
                },
            )
        )

    # ── Ownership ────────────────────────────────────────────────
    o_result = await db.execute(select(OwnershipEpisode).where(OwnershipEpisode.building_id == building_id))
    for o in o_result.scalars().all():
        owner_label = o.owner_name or "Propriétaire inconnu"
        entries.append(
            GenealogyTimelineEntry(
                id=o.id,
                entry_type="ownership",
                occurred_at=o.period_start,
                period_start=o.period_start,
                period_end=o.period_end,
                title=f"Propriété: {owner_label}",
                description=f"Acquisition par {o.acquisition_type}" if o.acquisition_type != "unknown" else None,
                evidence_basis=o.evidence_basis,
                metadata={
                    "owner_type": o.owner_type,
                    "acquisition_type": o.acquisition_type,
                    "approximate": o.approximate,
                },
            )
        )

    # ── Historical claims ────────────────────────────────────────
    c_result = await db.execute(select(HistoricalClaim).where(HistoricalClaim.building_id == building_id))
    for c in c_result.scalars().all():
        entries.append(
            GenealogyTimelineEntry(
                id=c.id,
                entry_type="claim",
                occurred_at=c.reference_date,
                period_start=c.period_start,
                period_end=c.period_end,
                title=f"Affirmation: {c.subject}",
                description=c.assertion,
                evidence_basis=c.evidence_basis,
                metadata={
                    "claim_type": c.claim_type,
                    "confidence": c.confidence,
                    "status": c.status,
                },
            )
        )

    # ── BuildingEvents from change grammar ───────────────────────
    e_result = await db.execute(select(BuildingEvent).where(BuildingEvent.building_id == building_id))
    for ev in e_result.scalars().all():
        ev_date = ev.occurred_at.date() if ev.occurred_at else None
        entries.append(
            GenealogyTimelineEntry(
                id=ev.id,
                entry_type="event",
                occurred_at=ev_date,
                title=ev.title,
                description=ev.description,
                metadata={
                    "event_type": ev.event_type,
                    "severity": ev.severity,
                },
            )
        )

    # ── Sort chronologically and limit ───────────────────────────
    entries.sort(key=_sort_key)
    total = len(entries)
    entries = entries[:limit]

    return GenealogyTimeline(
        building_id=building_id,
        entries=entries,
        total_entries=total,
    )


# ---------------------------------------------------------------------------
# Declared vs Observed comparison
# ---------------------------------------------------------------------------


async def compare_declared_vs_observed(
    db: AsyncSession,
    building_id: UUID,
) -> DeclaredVsObservedResponse:
    """Compare what is declared (historical claims) vs what is observed
    (current building state, diagnostics). Flag discrepancies.

    For each claim:
    - Check if status is already 'verified' or 'contested'
    - Check if any BuildingEvent or observation contradicts or confirms the claim
    - Flag unverified claims as potential discrepancies
    """
    # Fetch all claims
    c_result = await db.execute(select(HistoricalClaim).where(HistoricalClaim.building_id == building_id))
    claims = list(c_result.scalars().all())

    # Fetch building events for cross-reference
    e_result = await db.execute(select(BuildingEvent).where(BuildingEvent.building_id == building_id))
    events = list(e_result.scalars().all())

    # Build event lookup by type for quick matching
    event_titles_lower = {ev.title.lower() for ev in events if ev.title}

    discrepancies: list[DeclaredVsObservedDiscrepancy] = []
    verified_count = 0
    contested_count = 0
    unverified_count = 0

    for claim in claims:
        if claim.status == "verified":
            verified_count += 1
            continue

        if claim.status == "contested":
            contested_count += 1
            discrepancies.append(
                DeclaredVsObservedDiscrepancy(
                    claim_id=claim.id,
                    claim_subject=claim.subject,
                    claim_assertion=claim.assertion,
                    claim_basis=claim.evidence_basis,
                    discrepancy_type="contradiction",
                    explanation=f"Affirmation contestée: «{claim.assertion}» (confiance: {claim.confidence:.0%})",
                )
            )
            continue

        if claim.status == "superseded":
            # Superseded claims are not active discrepancies
            continue

        # Check if any event relates to this claim's subject
        subject_lower = claim.subject.lower()
        has_related_event = any(subject_lower in t for t in event_titles_lower)

        if has_related_event:
            # There's a related event but claim not yet verified — partial match
            discrepancies.append(
                DeclaredVsObservedDiscrepancy(
                    claim_id=claim.id,
                    claim_subject=claim.subject,
                    claim_assertion=claim.assertion,
                    claim_basis=claim.evidence_basis,
                    observed_source="building_event",
                    discrepancy_type="partial_match",
                    explanation=(
                        f"Un événement mentionne «{claim.subject}» mais l'affirmation "
                        f"«{claim.assertion}» n'est pas encore vérifiée."
                    ),
                )
            )
            unverified_count += 1
        elif claim.confidence < 0.5:
            # Low confidence + no corroborating evidence
            discrepancies.append(
                DeclaredVsObservedDiscrepancy(
                    claim_id=claim.id,
                    claim_subject=claim.subject,
                    claim_assertion=claim.assertion,
                    claim_basis=claim.evidence_basis,
                    discrepancy_type="unverified",
                    explanation=(
                        f"Affirmation non vérifiée avec confiance faible ({claim.confidence:.0%}): "
                        f"«{claim.assertion}». Aucune observation correspondante."
                    ),
                )
            )
            unverified_count += 1
        else:
            # Recorded but not verified, no related event
            discrepancies.append(
                DeclaredVsObservedDiscrepancy(
                    claim_id=claim.id,
                    claim_subject=claim.subject,
                    claim_assertion=claim.assertion,
                    claim_basis=claim.evidence_basis,
                    discrepancy_type="missing_observation",
                    explanation=(
                        f"Aucune observation ne corrobore l'affirmation «{claim.assertion}» "
                        f"(base: {claim.evidence_basis})."
                    ),
                )
            )
            unverified_count += 1

    return DeclaredVsObservedResponse(
        building_id=building_id,
        total_claims=len(claims),
        verified_count=verified_count,
        contested_count=contested_count,
        unverified_count=unverified_count,
        discrepancies=discrepancies,
    )
