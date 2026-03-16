"""Decision Replay Service — preserves and analyzes building decision history."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.decision_record import DecisionRecord
from app.models.user import User
from app.schemas.decision_replay import (
    DecisionContext,
    DecisionImpactAnalysis,
    DecisionPattern,
    DecisionRecordCreate,
    DecisionRecordRead,
    DecisionRecordUpdate,
    DecisionTimeline,
)


async def _capture_building_context(db: AsyncSession, building_id: UUID) -> dict:
    """Capture current building state as a context dict."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return {}

    # Count open actions
    from app.models.action_item import ActionItem

    action_count_result = await db.execute(
        select(func.count())
        .select_from(ActionItem)
        .where(
            ActionItem.building_id == building_id,
            ActionItem.status.in_(["open", "in_progress"]),
        )
    )
    open_actions_count = action_count_result.scalar() or 0

    # Get risk level from risk scores
    risk_level = "unknown"
    from app.models.building_risk_score import BuildingRiskScore

    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_score = risk_result.scalar_one_or_none()
    if risk_score and hasattr(risk_score, "overall_risk"):
        risk_level = risk_score.overall_risk or "unknown"

    return {
        "risk_level": risk_level,
        "grade": None,
        "trust_score": None,
        "completeness": None,
        "open_actions_count": open_actions_count,
    }


def _enrich_with_name(record: DecisionRecord, user: User | None) -> DecisionRecordRead:
    """Convert a DecisionRecord to DecisionRecordRead with decided_by_name."""
    name = None
    if user:
        name = f"{user.first_name} {user.last_name}"
    return DecisionRecordRead(
        id=record.id,
        building_id=record.building_id,
        decision_type=record.decision_type,
        title=record.title,
        rationale=record.rationale,
        alternatives_considered=record.alternatives_considered,
        decided_by=record.decided_by,
        decided_at=record.decided_at,
        context_snapshot=record.context_snapshot,
        outcome=record.outcome,
        outcome_notes=record.outcome_notes,
        entity_type=record.entity_type,
        entity_id=record.entity_id,
        decided_by_name=name,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def record_decision(
    db: AsyncSession,
    user_id: UUID,
    data: DecisionRecordCreate,
) -> DecisionRecord:
    """Create a new decision record with auto-captured context."""
    context = data.context_snapshot
    if context is None:
        context = await _capture_building_context(db, data.building_id)

    record = DecisionRecord(
        building_id=data.building_id,
        decision_type=data.decision_type,
        title=data.title,
        rationale=data.rationale,
        alternatives_considered=data.alternatives_considered,
        decided_by=user_id,
        decided_at=datetime.now(UTC),
        context_snapshot=context,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_decision_timeline(
    db: AsyncSession,
    building_id: UUID,
    limit: int = 50,
    decision_type: str | None = None,
) -> DecisionTimeline:
    """Return chronological decision history for a building."""
    query = select(DecisionRecord).where(DecisionRecord.building_id == building_id)
    if decision_type:
        query = query.where(DecisionRecord.decision_type == decision_type)
    query = query.order_by(DecisionRecord.decided_at.desc()).limit(limit)

    result = await db.execute(query)
    records = list(result.scalars().all())

    # Get total count
    count_query = select(func.count()).select_from(DecisionRecord).where(DecisionRecord.building_id == building_id)
    if decision_type:
        count_query = count_query.where(DecisionRecord.decision_type == decision_type)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Enrich with user names
    user_ids = {r.decided_by for r in records}
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {u.id: u for u in users_result.scalars().all()}

    decisions = [_enrich_with_name(r, users_map.get(r.decided_by)) for r in records]

    return DecisionTimeline(
        building_id=building_id,
        decisions=decisions,
        total_decisions=total,
    )


async def get_decision_detail(
    db: AsyncSession,
    decision_id: UUID,
) -> DecisionRecordRead | None:
    """Return a single decision with enriched decided_by_name."""
    result = await db.execute(select(DecisionRecord).where(DecisionRecord.id == decision_id))
    record = result.scalar_one_or_none()
    if not record:
        return None

    user_result = await db.execute(select(User).where(User.id == record.decided_by))
    user = user_result.scalar_one_or_none()

    return _enrich_with_name(record, user)


async def update_decision_outcome(
    db: AsyncSession,
    decision_id: UUID,
    update: DecisionRecordUpdate,
) -> DecisionRecord | None:
    """Update outcome and notes after a decision has played out."""
    result = await db.execute(select(DecisionRecord).where(DecisionRecord.id == decision_id))
    record = result.scalar_one_or_none()
    if not record:
        return None

    if update.outcome is not None:
        record.outcome = update.outcome
    if update.outcome_notes is not None:
        record.outcome_notes = update.outcome_notes
    if update.rationale is not None:
        record.rationale = update.rationale

    await db.commit()
    await db.refresh(record)
    return record


async def get_decision_patterns(
    db: AsyncSession,
    building_id: UUID,
) -> list[DecisionPattern]:
    """Analyze decision patterns — frequency by type, average interval, common outcomes."""
    result = await db.execute(
        select(DecisionRecord).where(DecisionRecord.building_id == building_id).order_by(DecisionRecord.decided_at)
    )
    records = list(result.scalars().all())

    if not records:
        return []

    # Group by type
    by_type: dict[str, list[DecisionRecord]] = {}
    for r in records:
        by_type.setdefault(r.decision_type, []).append(r)

    patterns = []
    for dtype, recs in by_type.items():
        count = len(recs)

        # Average days between decisions of this type
        avg_days = None
        if count >= 2:
            deltas = []
            for i in range(1, len(recs)):
                if recs[i].decided_at and recs[i - 1].decided_at:
                    delta = (recs[i].decided_at - recs[i - 1].decided_at).total_seconds() / 86400
                    deltas.append(delta)
            if deltas:
                avg_days = round(sum(deltas) / len(deltas), 1)

        # Most common outcome
        outcomes = [r.outcome for r in recs if r.outcome]
        most_common = None
        if outcomes:
            counter = Counter(outcomes)
            most_common = counter.most_common(1)[0][0]

        patterns.append(
            DecisionPattern(
                decision_type=dtype,
                count=count,
                avg_days_between=avg_days,
                most_common_outcome=most_common,
            )
        )

    return patterns


async def get_decision_context(
    db: AsyncSession,
    decision_id: UUID,
) -> DecisionContext | None:
    """Compare the building state at decision time vs current state."""
    result = await db.execute(select(DecisionRecord).where(DecisionRecord.id == decision_id))
    record = result.scalar_one_or_none()
    if not record:
        return None

    at_decision_time = record.context_snapshot or {}
    current_state = await _capture_building_context(db, record.building_id)

    state_changed = at_decision_time != current_state

    return DecisionContext(
        building_id=record.building_id,
        at_decision_time=at_decision_time,
        current_state=current_state,
        state_changed=state_changed,
    )


async def get_decision_impact(
    db: AsyncSession,
    building_id: UUID,
    limit: int = 10,
) -> list[DecisionImpactAnalysis]:
    """For recent decisions, compare state before and after to estimate impact."""
    result = await db.execute(
        select(DecisionRecord)
        .where(DecisionRecord.building_id == building_id)
        .order_by(DecisionRecord.decided_at.desc())
        .limit(limit)
    )
    records = list(result.scalars().all())

    current_state = await _capture_building_context(db, building_id)
    now = datetime.now(UTC)

    impacts = []
    for record in records:
        before_state = record.context_snapshot or {}
        if record.decided_at:
            decided = record.decided_at
            if decided.tzinfo is None:
                decided = decided.replace(tzinfo=UTC)
            days_since = (now - decided).days
        else:
            days_since = 0

        # Simple impact summary
        impact_summary = None
        if record.outcome:
            impact_summary = f"Outcome: {record.outcome}"

        impacts.append(
            DecisionImpactAnalysis(
                decision_id=record.id,
                decision_type=record.decision_type,
                title=record.title,
                before_state=before_state,
                after_state=current_state,
                impact_summary=impact_summary,
                days_since_decision=days_since,
            )
        )

    return impacts


async def search_decisions(
    db: AsyncSession,
    building_id: UUID | None = None,
    decision_type: str | None = None,
    decided_by: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
) -> list[DecisionRecordRead]:
    """Search/filter decisions across buildings."""
    query = select(DecisionRecord)

    if building_id:
        query = query.where(DecisionRecord.building_id == building_id)
    if decision_type:
        query = query.where(DecisionRecord.decision_type == decision_type)
    if decided_by:
        query = query.where(DecisionRecord.decided_by == decided_by)
    if date_from:
        query = query.where(DecisionRecord.decided_at >= date_from)
    if date_to:
        query = query.where(DecisionRecord.decided_at <= date_to)

    query = query.order_by(DecisionRecord.decided_at.desc()).limit(limit)

    result = await db.execute(query)
    records = list(result.scalars().all())

    # Enrich with user names
    user_ids = {r.decided_by for r in records}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u for u in users_result.scalars().all()}
    else:
        users_map = {}

    return [_enrich_with_name(r, users_map.get(r.decided_by)) for r in records]
