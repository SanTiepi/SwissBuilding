from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_claim import BuildingClaim, BuildingDecision
from app.schemas.building_truth import BuildingClaimCreate, BuildingDecisionCreate
from app.services import ritual_service


async def create_claim(
    db: AsyncSession,
    building_id: UUID,
    data: BuildingClaimCreate,
    claimed_by_id: UUID,
    organization_id: UUID,
) -> BuildingClaim:
    """Create a new claim. Auto-checks for contradictions with existing claims."""
    claim = BuildingClaim(
        building_id=building_id,
        claimed_by_id=claimed_by_id,
        organization_id=organization_id,
        **data.model_dump(exclude_unset=True),
    )
    db.add(claim)
    await db.flush()

    # Auto-create review task for low-confidence claims
    try:
        from app.services.review_queue_service import auto_create_from_claim

        await auto_create_from_claim(
            db,
            building_id=building_id,
            organization_id=organization_id,
            claim_id=claim.id,
            claim_subject=claim.subject,
            confidence=claim.confidence,
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("review_queue failed after claim %s", claim.id)

    # Run consequence chain after truth change
    try:
        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        await engine.run_consequences(
            db, building_id, "claim_created", trigger_id=str(claim.id), triggered_by_id=claimed_by_id
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("consequence_engine failed after claim %s", claim.id)

    return claim


async def verify_claim(
    db: AsyncSession,
    claim_id: UUID,
    verified_by_id: UUID,
) -> BuildingClaim:
    """Expert verifies a claim."""
    result = await db.execute(select(BuildingClaim).where(BuildingClaim.id == claim_id))
    claim = result.scalar_one_or_none()
    if claim is None:
        raise ValueError("Claim not found")
    if claim.status not in ("asserted", "contested"):
        raise ValueError(f"Cannot verify claim with status '{claim.status}'")
    claim.status = "verified"
    claim.verified_by_id = verified_by_id
    claim.verified_at = datetime.now(UTC)
    await db.flush()

    # Record canonical ritual trace
    await ritual_service.validate(
        db,
        claim.building_id,
        "claim",
        claim.id,
        verified_by_id,
        claim.organization_id,
    )

    return claim


async def contest_claim(
    db: AsyncSession,
    claim_id: UUID,
    contested_by_id: UUID,
    reason: str,
) -> BuildingClaim:
    """Contest a claim. Creates visibility — never silent override."""
    result = await db.execute(select(BuildingClaim).where(BuildingClaim.id == claim_id))
    claim = result.scalar_one_or_none()
    if claim is None:
        raise ValueError("Claim not found")
    if claim.status in ("superseded", "withdrawn"):
        raise ValueError(f"Cannot contest claim with status '{claim.status}'")
    claim.status = "contested"
    claim.contested_by_id = contested_by_id
    claim.contestation_reason = reason
    await db.flush()
    return claim


async def supersede_claim(
    db: AsyncSession,
    old_claim_id: UUID,
    new_claim_id: UUID,
) -> BuildingClaim:
    """Mark old claim as superseded by new one."""
    old_result = await db.execute(select(BuildingClaim).where(BuildingClaim.id == old_claim_id))
    old_claim = old_result.scalar_one_or_none()
    if old_claim is None:
        raise ValueError("Old claim not found")

    new_result = await db.execute(select(BuildingClaim).where(BuildingClaim.id == new_claim_id))
    new_claim = new_result.scalar_one_or_none()
    if new_claim is None:
        raise ValueError("New claim not found")

    old_claim.status = "superseded"
    old_claim.superseded_by_id = new_claim_id
    old_claim.superseded_at = datetime.now(UTC)
    await db.flush()

    # Record canonical ritual trace
    await ritual_service.supersede(
        db,
        old_claim.building_id,
        "claim",
        old_claim.id,
        superseded_by_id=new_claim.claimed_by_id,
        org_id=old_claim.organization_id,
        new_target_id=new_claim.id,
    )

    return old_claim


async def withdraw_claim(
    db: AsyncSession,
    claim_id: UUID,
) -> BuildingClaim:
    """Withdraw a claim (author retracts)."""
    result = await db.execute(select(BuildingClaim).where(BuildingClaim.id == claim_id))
    claim = result.scalar_one_or_none()
    if claim is None:
        raise ValueError("Claim not found")
    if claim.status in ("superseded", "withdrawn"):
        raise ValueError(f"Cannot withdraw claim with status '{claim.status}'")
    claim.status = "withdrawn"
    await db.flush()
    return claim


async def list_claims(
    db: AsyncSession,
    building_id: UUID,
    status: str | None = None,
    claim_type: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[BuildingClaim], int]:
    """List claims for a building with optional filters."""
    query = select(BuildingClaim).where(BuildingClaim.building_id == building_id)
    count_query = select(func.count()).select_from(BuildingClaim).where(BuildingClaim.building_id == building_id)

    if status:
        query = query.where(BuildingClaim.status == status)
        count_query = count_query.where(BuildingClaim.status == status)
    if claim_type:
        query = query.where(BuildingClaim.claim_type == claim_type)
        count_query = count_query.where(BuildingClaim.claim_type == claim_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(BuildingClaim.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = list(result.scalars().all())
    return items, total


async def record_decision(
    db: AsyncSession,
    building_id: UUID,
    data: BuildingDecisionCreate,
    decision_maker_id: UUID,
    organization_id: UUID,
) -> BuildingDecision:
    """Record a decision with full provenance."""
    decision = BuildingDecision(
        building_id=building_id,
        decision_maker_id=decision_maker_id,
        organization_id=organization_id,
        **data.model_dump(exclude_unset=True),
    )
    db.add(decision)
    await db.flush()

    # Run consequence chain after truth change
    try:
        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        await engine.run_consequences(
            db, building_id, "decision_enacted", trigger_id=str(decision.id), triggered_by_id=decision_maker_id
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("consequence_engine failed after decision %s", decision.id)

    return decision


async def enact_decision(
    db: AsyncSession,
    decision_id: UUID,
) -> BuildingDecision:
    """Enact a pending decision."""
    result = await db.execute(select(BuildingDecision).where(BuildingDecision.id == decision_id))
    decision = result.scalar_one_or_none()
    if decision is None:
        raise ValueError("Decision not found")
    if decision.status != "pending":
        raise ValueError(f"Cannot enact decision with status '{decision.status}'")
    decision.status = "enacted"
    decision.enacted_at = datetime.now(UTC)
    await db.flush()
    return decision


async def reverse_decision(
    db: AsyncSession,
    decision_id: UUID,
    reversed_by_id: UUID,
    reason: str,
) -> BuildingDecision:
    """Reverse a decision. Records who and why."""
    result = await db.execute(select(BuildingDecision).where(BuildingDecision.id == decision_id))
    decision = result.scalar_one_or_none()
    if decision is None:
        raise ValueError("Decision not found")
    if decision.status not in ("pending", "enacted"):
        raise ValueError(f"Cannot reverse decision with status '{decision.status}'")
    if not decision.reversible:
        raise ValueError("Decision is marked as irreversible")
    decision.status = "reversed"
    decision.reversed_at = datetime.now(UTC)
    decision.reversed_by_id = reversed_by_id
    decision.reversal_reason = reason
    await db.flush()
    return decision


async def list_decisions(
    db: AsyncSession,
    building_id: UUID,
    status: str | None = None,
    decision_type: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[BuildingDecision], int]:
    """List decisions for a building with optional filters."""
    query = select(BuildingDecision).where(BuildingDecision.building_id == building_id)
    count_query = select(func.count()).select_from(BuildingDecision).where(BuildingDecision.building_id == building_id)

    if status:
        query = query.where(BuildingDecision.status == status)
        count_query = count_query.where(BuildingDecision.status == status)
    if decision_type:
        query = query.where(BuildingDecision.decision_type == decision_type)
        count_query = count_query.where(BuildingDecision.decision_type == decision_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(BuildingDecision.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = list(result.scalars().all())
    return items, total


async def get_truth_state(db: AsyncSession, building_id: UUID) -> dict:
    """Get the current truth state: active claims, recent decisions, contradictions."""
    # Active claims (asserted + verified)
    active_result = await db.execute(
        select(BuildingClaim)
        .where(
            BuildingClaim.building_id == building_id,
            BuildingClaim.status.in_(["asserted", "verified"]),
        )
        .order_by(BuildingClaim.created_at.desc())
        .limit(50)
    )
    active_claims = list(active_result.scalars().all())

    # Contested claims
    contested_result = await db.execute(
        select(BuildingClaim)
        .where(
            BuildingClaim.building_id == building_id,
            BuildingClaim.status == "contested",
        )
        .order_by(BuildingClaim.created_at.desc())
        .limit(50)
    )
    contested_claims = list(contested_result.scalars().all())

    # Recent decisions
    decisions_result = await db.execute(
        select(BuildingDecision)
        .where(BuildingDecision.building_id == building_id)
        .order_by(BuildingDecision.created_at.desc())
        .limit(20)
    )
    recent_decisions = list(decisions_result.scalars().all())

    # Summary counts
    count_result = await db.execute(
        select(BuildingClaim.status, func.count())
        .where(BuildingClaim.building_id == building_id)
        .group_by(BuildingClaim.status)
    )
    claim_counts = dict(count_result.all())

    dec_count_result = await db.execute(
        select(BuildingDecision.status, func.count())
        .where(BuildingDecision.building_id == building_id)
        .group_by(BuildingDecision.status)
    )
    decision_counts = dict(dec_count_result.all())

    return {
        "active_claims": active_claims,
        "contested_claims": contested_claims,
        "recent_decisions": recent_decisions,
        "summary": {
            "claims_by_status": claim_counts,
            "decisions_by_status": decision_counts,
            "total_active": len(active_claims),
            "total_contested": len(contested_claims),
        },
    }


async def get_claim_history(
    db: AsyncSession,
    building_id: UUID,
    subject: str | None = None,
) -> list[BuildingClaim]:
    """Get the history of claims about a building, optionally filtered by subject."""
    query = (
        select(BuildingClaim).where(BuildingClaim.building_id == building_id).order_by(BuildingClaim.created_at.desc())
    )
    if subject:
        query = query.where(BuildingClaim.subject.ilike(f"%{subject}%"))
    result = await db.execute(query)
    return list(result.scalars().all())
