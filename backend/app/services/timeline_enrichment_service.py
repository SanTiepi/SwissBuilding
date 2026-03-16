from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.timeline import TimelineEntryRead
from app.schemas.timeline_enrichment import (
    EnrichedTimeline,
    EnrichedTimelineEntry,
    TimelineLink,
)
from app.services.timeline_service import get_building_timeline


def _assign_lifecycle_phase(entry: TimelineEntryRead) -> str | None:
    """Map event_type + metadata to a lifecycle phase."""
    meta = entry.metadata or {}

    if entry.event_type == "construction":
        return None

    if entry.event_type == "diagnostic":
        status = meta.get("status", "")
        if status in ("draft", "in_progress"):
            return "discovery"
        if status in ("completed", "validated"):
            return "assessment"
        return "discovery"

    if entry.event_type == "sample":
        return "discovery"

    if entry.event_type == "document":
        return None

    if entry.event_type == "intervention":
        status = meta.get("status", "")
        if status == "planned":
            return "remediation"
        if status == "in_progress":
            return "remediation"
        if status == "completed":
            return "verification"
        if status == "cancelled":
            return "closed"
        return "remediation"

    if entry.event_type == "plan":
        return "remediation"

    if entry.event_type == "risk_change":
        return "assessment"

    if entry.event_type == "event":
        return None

    return None


def _assign_importance(entry: TimelineEntryRead) -> str:
    """Assign importance level based on event_type + metadata."""
    meta = entry.metadata or {}

    if entry.event_type == "risk_change":
        return "high"

    if entry.event_type == "sample":
        if meta.get("threshold_exceeded"):
            return "critical"
        risk_level = meta.get("risk_level", "")
        if risk_level in ("high", "critical"):
            return "high"
        return "medium"

    if entry.event_type == "diagnostic":
        status = meta.get("status", "")
        if status == "validated":
            return "high"
        return "medium"

    if entry.event_type == "intervention":
        return "medium"

    if entry.event_type == "construction":
        return "low"

    if entry.event_type == "document":
        return "low"

    if entry.event_type == "plan":
        return "low"

    if entry.event_type == "event":
        return "low"

    return "low"


def _generate_links(entries: list[EnrichedTimelineEntry]) -> list[TimelineLink]:
    """Detect causal relationships between timeline entries."""
    links: list[TimelineLink] = []

    # Index entries by source_type and source_id for quick lookup
    diagnostics = [e for e in entries if e.event_type == "diagnostic"]
    samples = [e for e in entries if e.event_type == "sample"]
    interventions = [e for e in entries if e.event_type == "intervention"]
    risk_changes = [e for e in entries if e.event_type == "risk_change"]

    # Samples are caused_by their diagnostic.
    # We link each sample to the closest diagnostic by date.
    for sample in samples:
        best_diag = None
        best_diff = None
        for diag in diagnostics:
            diff = abs((sample.date - diag.date).total_seconds())
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_diag = diag
        if best_diag:
            links.append(
                TimelineLink(
                    source_event_id=sample.id,
                    target_event_id=best_diag.id,
                    link_type="caused_by",
                )
            )

    # Interventions follow diagnostics (intervention date after diagnostic date)
    for intv in interventions:
        best_diag = None
        best_diff = None
        for diag in diagnostics:
            if diag.date <= intv.date:
                diff = (intv.date - diag.date).total_seconds()
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_diag = diag
        if best_diag:
            links.append(
                TimelineLink(
                    source_event_id=intv.id,
                    target_event_id=best_diag.id,
                    link_type="followed_by",
                )
            )

    # Risk changes after interventions → triggered
    for risk in risk_changes:
        best_intv = None
        best_diff = None
        for intv in interventions:
            if intv.date <= risk.date:
                diff = (risk.date - intv.date).total_seconds()
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_intv = intv
        if best_intv:
            links.append(
                TimelineLink(
                    source_event_id=risk.id,
                    target_event_id=best_intv.id,
                    link_type="triggered",
                )
            )

    return links


def _enrich_entries(raw_entries: list[TimelineEntryRead]) -> list[EnrichedTimelineEntry]:
    """Convert raw timeline entries to enriched entries with lifecycle phase and importance."""
    enriched = []
    for entry in raw_entries:
        enriched.append(
            EnrichedTimelineEntry(
                id=entry.id,
                date=entry.date,
                event_type=entry.event_type,
                title=entry.title,
                description=entry.description,
                icon_hint=entry.icon_hint,
                metadata=entry.metadata,
                source_id=entry.source_id,
                source_type=entry.source_type,
                lifecycle_phase=_assign_lifecycle_phase(entry),
                importance=_assign_importance(entry),
            )
        )
    return enriched


async def get_enriched_timeline(
    db: AsyncSession,
    building_id: UUID,
    page: int = 1,
    size: int = 50,
    event_type_filter: str | None = None,
) -> EnrichedTimeline:
    """Get enriched timeline with lifecycle phases, importance, and links."""
    # Get all entries (unpaginated) so we can generate links across the full set
    all_items, total = await get_building_timeline(
        db, building_id, page=1, size=10000, event_type_filter=event_type_filter
    )

    enriched = _enrich_entries(all_items)
    links = _generate_links(enriched)

    # Attach links to individual entries
    link_index: dict[str, list[TimelineLink]] = {}
    for link in links:
        link_index.setdefault(link.source_event_id, []).append(link)
        link_index.setdefault(link.target_event_id, []).append(link)
    for entry in enriched:
        entry.links = link_index.get(entry.id, [])

    # Build lifecycle summary from ALL entries (before pagination)
    lifecycle_summary: dict[str, int] = {}
    for entry in enriched:
        if entry.lifecycle_phase:
            lifecycle_summary[entry.lifecycle_phase] = lifecycle_summary.get(entry.lifecycle_phase, 0) + 1

    # Apply pagination
    start = (page - 1) * size
    end = start + size
    paginated = enriched[start:end]

    return EnrichedTimeline(
        entries=paginated,
        total=total,
        links=links,
        lifecycle_summary=lifecycle_summary,
    )


async def get_lifecycle_summary(db: AsyncSession, building_id: UUID) -> dict[str, int]:
    """Count entries per lifecycle phase for a building."""
    all_items, _ = await get_building_timeline(db, building_id, page=1, size=10000)
    enriched = _enrich_entries(all_items)
    summary: dict[str, int] = {}
    for entry in enriched:
        if entry.lifecycle_phase:
            summary[entry.lifecycle_phase] = summary.get(entry.lifecycle_phase, 0) + 1
    return summary
