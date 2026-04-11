"""BatiConnect — Commitment & Caveat service.

Makes promises, obligations, exclusions, and caveats first-class objects.
Caveats are auto-generated from unknowns, contradictions, and low-confidence claims.
"""

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commitment import Caveat, Commitment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Commitment CRUD
# ---------------------------------------------------------------------------


async def create_commitment(
    db: AsyncSession,
    building_id: uuid.UUID,
    data: dict,
) -> Commitment:
    """Create a new commitment for a building."""
    commitment = Commitment(
        building_id=building_id,
        **data,
    )
    db.add(commitment)
    await db.flush()
    return commitment


async def get_building_commitments(
    db: AsyncSession,
    building_id: uuid.UUID,
    status: str | None = "active",
) -> list[Commitment]:
    """List commitments for a building, optionally filtered by status."""
    stmt = select(Commitment).where(Commitment.building_id == building_id)
    if status:
        stmt = stmt.where(Commitment.status == status)
    stmt = stmt.order_by(Commitment.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def check_expiring_commitments(
    db: AsyncSession,
    building_id: uuid.UUID,
    horizon_days: int = 90,
) -> list[dict]:
    """Find commitments expiring within the given horizon.

    Returns commitment objects augmented with days_until_expiry.
    """
    today = date.today()
    horizon_date = today + timedelta(days=horizon_days)

    stmt = (
        select(Commitment)
        .where(
            Commitment.building_id == building_id,
            Commitment.status == "active",
            Commitment.end_date.isnot(None),
            Commitment.end_date >= today,
            Commitment.end_date <= horizon_date,
        )
        .order_by(Commitment.end_date.asc())
    )
    result = await db.execute(stmt)
    commitments = result.scalars().all()

    items = []
    for c in commitments:
        days = (c.end_date - today).days if c.end_date else None
        items.append({"commitment": c, "days_until_expiry": days})
    return items


async def get_commitment(db: AsyncSession, commitment_id: uuid.UUID) -> Commitment | None:
    """Fetch a single commitment by ID."""
    result = await db.execute(select(Commitment).where(Commitment.id == commitment_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Caveat CRUD
# ---------------------------------------------------------------------------


async def create_caveat(
    db: AsyncSession,
    building_id: uuid.UUID,
    data: dict,
) -> Caveat:
    """Create a caveat for a building."""
    caveat = Caveat(
        building_id=building_id,
        **data,
    )
    db.add(caveat)
    await db.flush()
    return caveat


async def get_building_caveats(
    db: AsyncSession,
    building_id: uuid.UUID,
    active_only: bool = True,
) -> list[Caveat]:
    """List caveats for a building."""
    stmt = select(Caveat).where(Caveat.building_id == building_id)
    if active_only:
        stmt = stmt.where(Caveat.active.is_(True))
    stmt = stmt.order_by(Caveat.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_caveats_for_pack(
    db: AsyncSession,
    building_id: uuid.UUID,
    pack_type: str,
) -> list[Caveat]:
    """Get all active caveats applicable to a specific pack type.

    Matches caveats where applies_to_pack_types is NULL (applies to all)
    or contains the requested pack_type.
    """
    # Fetch all active caveats for building, then filter in Python
    # (JSON column filtering varies by DB; Python filter is portable)
    stmt = (
        select(Caveat)
        .where(
            Caveat.building_id == building_id,
            Caveat.active.is_(True),
        )
        .order_by(Caveat.severity.desc(), Caveat.created_at.desc())
    )
    result = await db.execute(stmt)
    all_caveats = result.scalars().all()

    matched = []
    for c in all_caveats:
        if c.applies_to_pack_types is None or pack_type in (c.applies_to_pack_types or []):
            matched.append(c)
    return matched


# ---------------------------------------------------------------------------
# Auto-generate caveats
# ---------------------------------------------------------------------------


async def auto_generate_caveats(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> list[Caveat]:
    """Auto-generate caveats from unknowns, contradictions, and low-confidence claims.

    Idempotent: skips caveats that already exist for the same subject+type.
    """
    generated: list[Caveat] = []

    # Existing caveats for dedup
    existing = await get_building_caveats(db, building_id, active_only=True)
    existing_keys = {(c.caveat_type, c.subject) for c in existing}

    # 1. From unknowns ledger (open entries)
    try:
        from app.models.unknowns_ledger import UnknownEntry

        stmt = select(UnknownEntry).where(
            UnknownEntry.building_id == building_id,
            UnknownEntry.status.in_(["open", "investigating"]),
        )
        result = await db.execute(stmt)
        unknowns = result.scalars().all()

        for u in unknowns:
            key = ("coverage_gap", u.subject)
            if key in existing_keys:
                continue
            severity = "warning" if u.severity in ("critical", "high") else "info"
            caveat = Caveat(
                building_id=building_id,
                caveat_type="coverage_gap",
                subject=u.subject,
                description=f"Inconnu non resolu: {u.description or u.subject}",
                severity=severity,
                applies_to_pack_types=u.blocks_pack_types,
                source_type="system_generated",
                source_id=u.id,
                active=True,
            )
            db.add(caveat)
            generated.append(caveat)
            existing_keys.add(key)
    except Exception as e:
        logger.warning("Failed to generate caveats from unknowns for %s: %s", building_id, e)

    # 2. From contradictions (unresolved data quality issues)
    try:
        from app.models.data_quality_issue import DataQualityIssue

        stmt = select(DataQualityIssue).where(
            DataQualityIssue.building_id == building_id,
            DataQualityIssue.issue_type == "contradiction",
            DataQualityIssue.status != "resolved",
        )
        result = await db.execute(stmt)
        contradictions = result.scalars().all()

        for c in contradictions:
            subject = f"Contradiction: {c.field_name or 'donnee'}"
            key = ("data_quality_warning", subject)
            if key in existing_keys:
                continue
            severity = "warning" if c.severity in ("critical", "high") else "info"
            caveat = Caveat(
                building_id=building_id,
                caveat_type="data_quality_warning",
                subject=subject,
                description=c.description,
                severity=severity,
                source_type="system_generated",
                source_id=c.id,
                active=True,
            )
            db.add(caveat)
            generated.append(caveat)
            existing_keys.add(key)
    except Exception as e:
        logger.warning("Failed to generate caveats from contradictions for %s: %s", building_id, e)

    # 3. From low-confidence claims
    try:
        from app.models.building_claim import BuildingClaim

        stmt = select(BuildingClaim).where(
            BuildingClaim.building_id == building_id,
            BuildingClaim.status == "asserted",
            BuildingClaim.confidence.isnot(None),
            BuildingClaim.confidence < 0.5,
        )
        result = await db.execute(stmt)
        low_claims = result.scalars().all()

        for claim in low_claims:
            subject = f"Affirmation non verifiee: {claim.subject}"
            key = ("unverified_claim", subject)
            if key in existing_keys:
                continue
            confidence_pct = round((claim.confidence or 0) * 100)
            caveat = Caveat(
                building_id=building_id,
                caveat_type="unverified_claim",
                subject=subject,
                description=(f"Affirmation avec confiance faible ({confidence_pct}%): {claim.assertion[:200]}"),
                severity="warning",
                source_type="claim",
                source_id=claim.id,
                active=True,
            )
            db.add(caveat)
            generated.append(caveat)
            existing_keys.add(key)
    except Exception as e:
        logger.warning("Failed to generate caveats from claims for %s: %s", building_id, e)

    if generated:
        await db.flush()

    return generated


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


async def get_commitment_caveat_summary(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> dict:
    """Summary: active commitments, expiring soon, active caveats by type."""
    today = date.today()
    horizon = today + timedelta(days=90)

    # All commitments
    stmt = select(Commitment).where(Commitment.building_id == building_id)
    result = await db.execute(stmt)
    all_commitments = result.scalars().all()

    active = [c for c in all_commitments if c.status == "active"]
    expiring = [c for c in active if c.end_date and today <= c.end_date <= horizon]
    expired = [c for c in all_commitments if c.status == "expired"]
    fulfilled = [c for c in all_commitments if c.status == "fulfilled"]
    breached = [c for c in all_commitments if c.status == "breached"]

    # All active caveats
    stmt = select(Caveat).where(
        Caveat.building_id == building_id,
        Caveat.active.is_(True),
    )
    result = await db.execute(stmt)
    caveats = result.scalars().all()

    caveats_by_severity: dict[str, int] = {}
    caveats_by_type: dict[str, int] = {}
    for cav in caveats:
        caveats_by_severity[cav.severity] = caveats_by_severity.get(cav.severity, 0) + 1
        caveats_by_type[cav.caveat_type] = caveats_by_type.get(cav.caveat_type, 0) + 1

    return {
        "building_id": building_id,
        "active_commitments": len(active),
        "expiring_soon": len(expiring),
        "expired_commitments": len(expired),
        "fulfilled_commitments": len(fulfilled),
        "breached_commitments": len(breached),
        "active_caveats": len(caveats),
        "caveats_by_severity": caveats_by_severity,
        "caveats_by_type": caveats_by_type,
    }
