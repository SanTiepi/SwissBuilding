"""
BatiConnect — Value Ledger Service

Running ledger that tracks cumulative value BatiConnect has delivered to an
organization. All metrics are computed from real data, not estimates.

The hours/CHF estimates use conservative heuristics:
- 2h saved per source unified (vs manual cross-referencing)
- 4h saved per contradiction resolved (vs discovery during incident)
- 1h saved per proof chain created (vs reconstructing provenance)
- 0.5h saved per document secured (vs manual hashing/archiving)
- 1h saved per decision backed with evidence (vs verbal justification)
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.document import Document
from app.models.domain_event import DomainEvent
from app.models.evidence_link import EvidenceLink
from app.schemas.value_ledger import ValueEvent, ValueLedger, ValueTrend

logger = logging.getLogger(__name__)

# Cost heuristics (conservative CHF/hour rate for property management)
_RATE_CHF_PER_HOUR = 150.0
_HOURS_PER_SOURCE = 2.0
_HOURS_PER_CONTRADICTION = 4.0
_HOURS_PER_PROOF_CHAIN = 1.0
_HOURS_PER_DOC_SECURED = 0.5
_HOURS_PER_DECISION_BACKED = 1.0


async def get_value_ledger(db: AsyncSession, org_id: UUID) -> ValueLedger | None:
    """Compute the cumulative value ledger for an organization.

    Returns None if the organization has no buildings.
    """
    # Get all building IDs for the org
    building_ids_result = await db.execute(
        select(Building.id, Building.created_at).where(Building.organization_id == org_id)
    )
    building_rows = list(building_ids_result.all())
    if not building_rows:
        return None

    building_ids = [r[0] for r in building_rows]
    earliest_created = min(r[1] for r in building_rows if r[1] is not None) if building_rows else datetime.utcnow()

    # 1. Sources unified: distinct source_dataset values across buildings
    sources_result = await db.execute(
        select(func.count(func.distinct(Building.source_dataset))).where(
            and_(
                Building.organization_id == org_id,
                Building.source_dataset.isnot(None),
            )
        )
    )
    sources_unified_total = (sources_result.scalar() or 0) + len(building_ids)  # each building = at least 1 source

    # 2. Contradictions resolved
    contradictions_resolved_total = 0
    for bid in building_ids:
        count = (
            await db.execute(
                select(func.count())
                .select_from(DataQualityIssue)
                .where(
                    and_(
                        DataQualityIssue.building_id == bid,
                        DataQualityIssue.issue_type == "contradiction",
                        DataQualityIssue.status == "resolved",
                    )
                )
            )
        ).scalar() or 0
        contradictions_resolved_total += count

    # 3. Proof chains: evidence links + custody events across org buildings
    proof_chains_created_total = 0
    for bid in building_ids:
        # Evidence links referencing this building or its entities
        link_count = (
            await db.execute(
                select(func.count())
                .select_from(EvidenceLink)
                .where((EvidenceLink.source_id == bid) | (EvidenceLink.target_id == bid))
            )
        ).scalar() or 0
        proof_chains_created_total += link_count

    # 4. Documents secured (with content_hash)
    documents_secured_total = 0
    for bid in building_ids:
        doc_count = (
            await db.execute(
                select(func.count())
                .select_from(Document)
                .where(
                    and_(
                        Document.building_id == bid,
                        Document.content_hash.isnot(None),
                    )
                )
            )
        ).scalar() or 0
        documents_secured_total += doc_count

    # 5. Decisions backed with evidence links
    decisions_backed_total = 0
    for bid in building_ids:
        # ActionItems that have at least one evidence link
        action_ids_result = await db.execute(select(ActionItem.id).where(ActionItem.building_id == bid))
        action_ids = [r[0] for r in action_ids_result.all()]
        for aid in action_ids:
            has_evidence = (
                await db.execute(
                    select(func.count())
                    .select_from(EvidenceLink)
                    .where((EvidenceLink.source_id == aid) | (EvidenceLink.target_id == aid))
                )
            ).scalar() or 0
            if has_evidence > 0:
                decisions_backed_total += 1

    # Hours saved estimate
    hours_saved = (
        sources_unified_total * _HOURS_PER_SOURCE
        + contradictions_resolved_total * _HOURS_PER_CONTRADICTION
        + proof_chains_created_total * _HOURS_PER_PROOF_CHAIN
        + documents_secured_total * _HOURS_PER_DOC_SECURED
        + decisions_backed_total * _HOURS_PER_DECISION_BACKED
    )

    value_chf = hours_saved * _RATE_CHF_PER_HOUR

    # Days active
    now = datetime.utcnow()
    if earliest_created and earliest_created.tzinfo is None:
        days_active = max(1, (now.replace(tzinfo=None) - earliest_created).days)
    else:
        days_active = max(1, (now - earliest_created).days) if earliest_created else 1

    value_per_day = round(value_chf / days_active, 2)

    # Trend: compare last 30 days vs previous 30 days of value events
    trend_detail = await _compute_trend(db, org_id, now)

    return ValueLedger(
        organization_id=org_id,
        sources_unified_total=sources_unified_total,
        contradictions_resolved_total=contradictions_resolved_total,
        proof_chains_created_total=proof_chains_created_total,
        documents_secured_total=documents_secured_total,
        decisions_backed_total=decisions_backed_total,
        hours_saved_estimate=round(hours_saved, 1),
        value_chf_estimate=round(value_chf, 2),
        days_active=days_active,
        value_per_day=value_per_day,
        trend=trend_detail.direction,
        trend_detail=trend_detail,
    )


async def _compute_trend(db: AsyncSession, org_id: UUID, now: datetime) -> ValueTrend:
    """Compare value events in last 30 days vs previous 30 days."""
    cutoff_30 = now - timedelta(days=30)
    cutoff_60 = now - timedelta(days=60)

    # Count value events in last 30 days
    last_30 = (
        await db.execute(
            select(func.count())
            .select_from(DomainEvent)
            .where(
                and_(
                    DomainEvent.event_type == "value_accumulated",
                    DomainEvent.aggregate_type == "organization",
                    DomainEvent.aggregate_id == org_id,
                    DomainEvent.occurred_at >= cutoff_30,
                )
            )
        )
    ).scalar() or 0

    # Count value events in previous 30 days
    prev_30 = (
        await db.execute(
            select(func.count())
            .select_from(DomainEvent)
            .where(
                and_(
                    DomainEvent.event_type == "value_accumulated",
                    DomainEvent.aggregate_type == "organization",
                    DomainEvent.aggregate_id == org_id,
                    DomainEvent.occurred_at >= cutoff_60,
                    DomainEvent.occurred_at < cutoff_30,
                )
            )
        )
    ).scalar() or 0

    last_30_value = float(last_30)
    prev_30_value = float(prev_30)

    if last_30_value > prev_30_value * 1.1:
        direction = "growing"
    elif last_30_value < prev_30_value * 0.9:
        direction = "declining"
    else:
        direction = "stable"

    return ValueTrend(
        last_30_days_value=last_30_value,
        previous_30_days_value=prev_30_value,
        direction=direction,
    )


async def record_value_event(
    db: AsyncSession,
    org_id: UUID,
    event_type: str,
    building_id: UUID | None,
    delta_description: str,
) -> None:
    """Create a DomainEvent of type 'value_accumulated' with delta metadata."""
    event = DomainEvent(
        id=_uuid.uuid4(),
        event_type="value_accumulated",
        aggregate_type="organization",
        aggregate_id=org_id,
        payload={
            "sub_type": event_type,
            "building_id": str(building_id) if building_id else None,
            "delta": delta_description,
        },
        occurred_at=datetime.utcnow(),
    )
    db.add(event)
    await db.flush()
    logger.info(
        "Value event recorded for org %s: %s — %s",
        org_id,
        event_type,
        delta_description,
    )


async def get_value_events(
    db: AsyncSession,
    org_id: UUID,
    limit: int = 20,
) -> list[ValueEvent]:
    """Get recent value events for an organization."""
    result = await db.execute(
        select(DomainEvent)
        .where(
            and_(
                DomainEvent.event_type == "value_accumulated",
                DomainEvent.aggregate_type == "organization",
                DomainEvent.aggregate_id == org_id,
            )
        )
        .order_by(DomainEvent.occurred_at.desc())
        .limit(limit)
    )
    events = list(result.scalars().all())

    return [
        ValueEvent(
            event_type=e.payload.get("sub_type", "unknown") if e.payload else "unknown",
            building_id=_uuid.UUID(e.payload["building_id"]) if e.payload and e.payload.get("building_id") else None,
            delta_description=e.payload.get("delta", "") if e.payload else "",
            created_at=e.occurred_at,
        )
        for e in events
    ]
