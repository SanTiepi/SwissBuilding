"""Decision Replay Service — preserves and analyzes building decision history.

Includes the Decision Replay Layer (Bloc 8): replayable snapshots of decisions
with basis tracking, staleness detection, and validity checks.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_claim import BuildingClaim, BuildingDecision
from app.models.decision_record import DecisionRecord
from app.models.decision_replay import DecisionReplay
from app.models.user import User
from app.schemas.decision_replay import (
    BasisValidityCheck,
    DecisionContext,
    DecisionImpactAnalysis,
    DecisionPattern,
    DecisionRecordCreate,
    DecisionRecordRead,
    DecisionRecordUpdate,
    DecisionTimeline,
    StaleDecisionRead,
)

logger = logging.getLogger(__name__)


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


# ---------------------------------------------------------------------------
# Decision Replay Layer — basis snapshots & staleness detection
# ---------------------------------------------------------------------------


async def _capture_basis_snapshot(db: AsyncSession, decision: BuildingDecision) -> dict:
    """Capture claims and evidence referenced by the decision at snapshot time."""
    snapshot: dict = {
        "decision_type": decision.decision_type,
        "title": decision.title,
        "outcome": decision.outcome,
        "rationale": decision.rationale,
        "authority_level": decision.authority_level,
        "basis_claims": decision.basis_claims or [],
        "basis_evidence": decision.basis_evidence or [],
        "claims_detail": [],
        "decision_status": decision.status,
        "enacted_at": str(decision.enacted_at) if decision.enacted_at else None,
    }

    # Load claim details if referenced
    if decision.basis_claims:
        claim_ids = []
        for cid in decision.basis_claims:
            try:
                claim_ids.append(UUID(str(cid)))
            except (ValueError, AttributeError):
                continue
        if claim_ids:
            result = await db.execute(select(BuildingClaim).where(BuildingClaim.id.in_(claim_ids)))
            claims = list(result.scalars().all())
            snapshot["claims_detail"] = [
                {
                    "id": str(c.id),
                    "claim_type": c.claim_type,
                    "subject": c.subject,
                    "assertion": c.assertion,
                    "status": c.status,
                    "confidence": c.confidence,
                    "basis_type": c.basis_type,
                }
                for c in claims
            ]

    return snapshot


async def _capture_trust_state(db: AsyncSession, building_id: UUID) -> dict:
    """Capture current trust state for a building."""
    trust_state: dict = {"overall_trust": None, "trust_details": {}}
    try:
        from app.models.building_trust_score_v2 import BuildingTrustScore

        result = await db.execute(
            select(BuildingTrustScore)
            .where(BuildingTrustScore.building_id == building_id)
            .order_by(BuildingTrustScore.computed_at.desc())
            .limit(1)
        )
        trust = result.scalar_one_or_none()
        if trust:
            trust_state["overall_trust"] = trust.overall_score
            trust_state["trust_details"] = {
                "evidence_score": getattr(trust, "evidence_score", None),
                "completeness_score": getattr(trust, "completeness_score", None),
                "freshness_score": getattr(trust, "freshness_score", None),
                "computed_at": str(trust.computed_at) if trust.computed_at else None,
            }
    except Exception:
        logger.debug("Could not capture trust state for building %s", building_id)

    return trust_state


async def _capture_completeness(db: AsyncSession, building_id: UUID) -> float | None:
    """Capture current completeness score."""
    try:
        from app.services.completeness_engine import compute_completeness

        result = await compute_completeness(db, building_id)
        return result.get("overall_score") if isinstance(result, dict) else None
    except Exception:
        logger.debug("Could not capture completeness for building %s", building_id)
        return None


async def _capture_readiness(db: AsyncSession, building_id: UUID) -> dict | None:
    """Capture current readiness state."""
    try:
        from app.models.readiness_assessment import ReadinessAssessment

        result = await db.execute(
            select(ReadinessAssessment)
            .where(ReadinessAssessment.building_id == building_id)
            .order_by(ReadinessAssessment.assessed_at.desc())
            .limit(1)
        )
        ra = result.scalar_one_or_none()
        if ra:
            return {
                "readiness_type": getattr(ra, "readiness_type", None),
                "verdict": getattr(ra, "verdict", None),
                "assessed_at": str(ra.assessed_at) if ra.assessed_at else None,
            }
    except Exception:
        logger.debug("Could not capture readiness for building %s", building_id)
    return None


async def _get_changes_since_decision(db: AsyncSession, building_id: UUID, since: datetime) -> list[dict]:
    """Get changes from the change timeline since the decision was made."""
    changes: list[dict] = []
    try:
        from app.services.change_tracker_service import get_change_timeline

        timeline = await get_change_timeline(db, building_id, since=since, limit=100)
        for entry in timeline:
            changes.append(
                {
                    "change_type": entry.change_type,
                    "title": entry.title,
                    "description": entry.description,
                    "occurred_at": str(entry.occurred_at),
                    "severity": entry.severity,
                }
            )
    except Exception:
        logger.debug("Could not get change timeline for building %s", building_id)
    return changes


def _assess_replay_status(
    basis_snapshot: dict,
    changes_since: list[dict],
    current_claims_changed: bool,
) -> tuple[str, bool, list[dict], str]:
    """Determine replay status based on changes since decision.

    Returns (status, basis_still_valid, invalidated_by, summary).
    """
    invalidated_by: list[dict] = []
    num_changes = len(changes_since)

    # Check for claim status changes
    if current_claims_changed:
        invalidated_by.append(
            {
                "reason": "claims_changed",
                "label_fr": "Les assertions de base ont change de statut",
            }
        )

    # Check for high-severity changes
    severe_changes = [c for c in changes_since if c.get("severity") in ("critical", "high")]
    if severe_changes:
        invalidated_by.append(
            {
                "reason": "severe_changes",
                "label_fr": f"{len(severe_changes)} changement(s) critique(s) depuis la decision",
                "details": [c["title"] for c in severe_changes[:5]],
            }
        )

    # Determine status
    if invalidated_by:
        status = "invalidated"
        basis_valid = False
        summary = f"Base invalidee: {len(invalidated_by)} raison(s). {num_changes} changement(s) depuis la decision."
    elif num_changes > 10:
        status = "stale"
        basis_valid = False
        summary = f"Base obsolete: {num_changes} changements depuis la decision."
    elif num_changes > 0:
        status = "partially_stale"
        basis_valid = True
        summary = f"Base partiellement a jour: {num_changes} changement(s) mineur(s) depuis la decision."
    else:
        status = "current"
        basis_valid = True
        summary = "Base actuelle: aucun changement detecte depuis la decision."

    return status, basis_valid, invalidated_by, summary


async def create_replay(
    db: AsyncSession,
    decision_id: UUID,
) -> DecisionReplay:
    """Create a replay snapshot for a BuildingDecision.

    Captures: the decision's basis claims/evidence, trust state at the time,
    completeness, readiness. Then compares with current state to detect changes.
    """
    result = await db.execute(select(BuildingDecision).where(BuildingDecision.id == decision_id))
    decision = result.scalar_one_or_none()
    if decision is None:
        raise ValueError("Decision introuvable")

    building_id = decision.building_id

    # Capture basis snapshot
    basis_snapshot = await _capture_basis_snapshot(db, decision)
    trust_state = await _capture_trust_state(db, building_id)
    completeness = await _capture_completeness(db, building_id)
    readiness = await _capture_readiness(db, building_id)

    # Get changes since decision was created
    since = decision.enacted_at or decision.created_at or datetime.now(UTC)
    changes_since = await _get_changes_since_decision(db, building_id, since)

    # Check if basis claims have changed
    claims_changed = False
    if decision.basis_claims:
        claim_ids = []
        for cid in decision.basis_claims:
            try:
                claim_ids.append(UUID(str(cid)))
            except (ValueError, AttributeError):
                continue
        if claim_ids:
            current_result = await db.execute(select(BuildingClaim).where(BuildingClaim.id.in_(claim_ids)))
            current_claims = list(current_result.scalars().all())
            snapshot_claims = {c["id"]: c["status"] for c in basis_snapshot.get("claims_detail", [])}
            for claim in current_claims:
                old_status = snapshot_claims.get(str(claim.id))
                if old_status and old_status != claim.status:
                    claims_changed = True
                    break

    status, basis_valid, invalidated_by, summary = _assess_replay_status(basis_snapshot, changes_since, claims_changed)

    now = datetime.now(UTC)
    replay = DecisionReplay(
        building_id=building_id,
        decision_id=decision_id,
        basis_snapshot=basis_snapshot,
        trust_state_at_decision=trust_state,
        completeness_at_decision=completeness,
        readiness_at_decision=readiness,
        changes_since=changes_since,
        basis_still_valid=basis_valid,
        invalidated_by=invalidated_by if invalidated_by else None,
        replay_status=status,
        replay_summary=summary,
        replayed_at=now,
        created_at=now,
    )
    db.add(replay)
    await db.flush()

    logger.info(
        "Created replay %s for decision %s (status=%s)",
        replay.id,
        decision_id,
        status,
    )
    return replay


async def check_basis_validity(
    db: AsyncSession,
    replay_id: UUID,
) -> BasisValidityCheck:
    """Re-check if the original basis is still valid.

    Compare basis_snapshot with current state.
    Flag what changed.
    """
    result = await db.execute(select(DecisionReplay).where(DecisionReplay.id == replay_id))
    replay = result.scalar_one_or_none()
    if replay is None:
        raise ValueError("Replay introuvable")

    # Re-fetch the decision
    dec_result = await db.execute(select(BuildingDecision).where(BuildingDecision.id == replay.decision_id))
    decision = dec_result.scalar_one_or_none()
    if decision is None:
        raise ValueError("Decision introuvable")

    building_id = replay.building_id

    # Get fresh changes since decision
    since = decision.enacted_at or decision.created_at or datetime.now(UTC)
    changes_since = await _get_changes_since_decision(db, building_id, since)

    # Check claims
    claims_changed = False
    invalidation_reasons: list[str] = []
    changes_detected: list[dict] = []

    if decision.basis_claims:
        claim_ids = []
        for cid in decision.basis_claims:
            try:
                claim_ids.append(UUID(str(cid)))
            except (ValueError, AttributeError):
                continue
        if claim_ids:
            current_result = await db.execute(select(BuildingClaim).where(BuildingClaim.id.in_(claim_ids)))
            current_claims = list(current_result.scalars().all())
            snapshot_claims = {c["id"]: c["status"] for c in (replay.basis_snapshot or {}).get("claims_detail", [])}
            for claim in current_claims:
                old_status = snapshot_claims.get(str(claim.id))
                if old_status and old_status != claim.status:
                    claims_changed = True
                    changes_detected.append(
                        {
                            "type": "claim_status_change",
                            "claim_id": str(claim.id),
                            "old_status": old_status,
                            "new_status": claim.status,
                            "label_fr": f"Assertion '{claim.subject}': {old_status} -> {claim.status}",
                        }
                    )
                    invalidation_reasons.append(f"Assertion '{claim.subject}' a change: {old_status} -> {claim.status}")

    # Check for severe timeline changes
    severe_changes = [c for c in changes_since if c.get("severity") in ("critical", "high")]
    if severe_changes:
        for sc in severe_changes[:5]:
            changes_detected.append(
                {
                    "type": "severe_change",
                    "title": sc.get("title", ""),
                    "severity": sc.get("severity", ""),
                    "label_fr": f"Changement critique: {sc.get('title', '')}",
                }
            )
            invalidation_reasons.append(f"Changement critique: {sc.get('title', '')}")

    # Add minor changes
    for ch in changes_since:
        if ch.get("severity") not in ("critical", "high"):
            changes_detected.append(
                {
                    "type": "change",
                    "title": ch.get("title", ""),
                    "change_type": ch.get("change_type", ""),
                }
            )

    # Determine new status
    status, basis_valid, _, summary = _assess_replay_status(replay.basis_snapshot or {}, changes_since, claims_changed)

    # Update replay record
    replay.changes_since = changes_since
    replay.basis_still_valid = basis_valid
    replay.invalidated_by = [{"reason": r} for r in invalidation_reasons] if invalidation_reasons else None
    replay.replay_status = status
    replay.replay_summary = summary
    replay.replayed_at = datetime.now(UTC)
    await db.flush()

    return BasisValidityCheck(
        replay_id=replay.id,
        decision_id=replay.decision_id,
        basis_still_valid=basis_valid,
        replay_status=status,
        changes_detected=changes_detected,
        invalidation_reasons=invalidation_reasons,
        replay_summary=summary,
    )


async def get_decision_replays(
    db: AsyncSession,
    building_id: UUID,
) -> list[DecisionReplay]:
    """Get all replays for a building's decisions."""
    result = await db.execute(
        select(DecisionReplay)
        .where(DecisionReplay.building_id == building_id)
        .order_by(DecisionReplay.created_at.desc())
    )
    return list(result.scalars().all())


async def get_replay_for_decision(
    db: AsyncSession,
    decision_id: UUID,
) -> DecisionReplay | None:
    """Get the most recent replay for a specific decision."""
    result = await db.execute(
        select(DecisionReplay)
        .where(DecisionReplay.decision_id == decision_id)
        .order_by(DecisionReplay.replayed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_stale_decisions(
    db: AsyncSession,
    building_id: UUID,
) -> list[StaleDecisionRead]:
    """Find decisions whose basis has changed since they were made."""
    # Get all replays that are not current
    result = await db.execute(
        select(DecisionReplay)
        .where(
            DecisionReplay.building_id == building_id,
            DecisionReplay.replay_status.in_(["partially_stale", "stale", "invalidated"]),
        )
        .order_by(DecisionReplay.replayed_at.desc())
    )
    stale_replays = list(result.scalars().all())

    if not stale_replays:
        return []

    # Load related decisions
    decision_ids = [r.decision_id for r in stale_replays]
    dec_result = await db.execute(select(BuildingDecision).where(BuildingDecision.id.in_(decision_ids)))
    decisions_map = {d.id: d for d in dec_result.scalars().all()}

    stale_decisions: list[StaleDecisionRead] = []
    for replay in stale_replays:
        decision = decisions_map.get(replay.decision_id)
        if not decision:
            continue

        changes_count = len(replay.changes_since) if replay.changes_since else 0
        invalidation_reasons = None
        if replay.invalidated_by:
            invalidation_reasons = [item.get("reason", item.get("label_fr", "")) for item in replay.invalidated_by]

        stale_decisions.append(
            StaleDecisionRead(
                decision_id=decision.id,
                decision_type=decision.decision_type,
                title=decision.title,
                outcome=decision.outcome,
                decided_at=decision.enacted_at or decision.created_at,
                replay_status=replay.replay_status,
                replay_summary=replay.replay_summary,
                changes_count=changes_count,
                invalidation_reasons=invalidation_reasons,
            )
        )

    return stale_decisions
