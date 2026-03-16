"""
SwissBuildingOS - Time Machine Service

Captures point-in-time snapshots of a building's passport/trust/readiness state,
enabling historical comparison and audit trails.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_snapshot import BuildingSnapshot
from app.services.passport_service import get_passport_summary


async def capture_snapshot(
    db: AsyncSession,
    building_id: UUID,
    snapshot_type: str = "manual",
    trigger_event: str | None = None,
    captured_by: UUID | None = None,
    notes: str | None = None,
) -> BuildingSnapshot:
    """Capture a point-in-time snapshot of the building's state.

    Collects:
    - Passport summary (via passport_service)
    - Trust score (from passport)
    - Readiness assessments (from passport)
    - Evidence counts (from passport)
    """
    passport = await get_passport_summary(db, building_id)

    passport_state = None
    trust_state = None
    readiness_state = None
    evidence_counts = None
    passport_grade = None
    overall_trust = None
    completeness_score = None

    if passport is not None:
        passport_state = passport
        trust_state = passport.get("knowledge_state")
        readiness_state = passport.get("readiness")
        evidence_counts = passport.get("evidence_coverage")
        passport_grade = passport.get("passport_grade")
        overall_trust = trust_state.get("overall_trust") if trust_state else None
        completeness_info = passport.get("completeness")
        completeness_score = completeness_info.get("overall_score") if completeness_info else None

    snapshot = BuildingSnapshot(
        building_id=building_id,
        snapshot_type=snapshot_type,
        trigger_event=trigger_event,
        passport_state_json=passport_state,
        trust_state_json=trust_state,
        readiness_state_json=readiness_state,
        evidence_counts_json=evidence_counts,
        passport_grade=passport_grade,
        overall_trust=overall_trust,
        completeness_score=completeness_score,
        captured_by=captured_by,
        notes=notes,
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def compare_snapshots(
    db: AsyncSession,
    building_id: UUID,
    snapshot_id_a: UUID,
    snapshot_id_b: UUID,
) -> dict | None:
    """Compare two snapshots and return a diff.

    Returns None if either snapshot is not found.
    """
    result_a = await db.execute(
        select(BuildingSnapshot).where(
            BuildingSnapshot.id == snapshot_id_a,
            BuildingSnapshot.building_id == building_id,
        )
    )
    snap_a = result_a.scalar_one_or_none()

    result_b = await db.execute(
        select(BuildingSnapshot).where(
            BuildingSnapshot.id == snapshot_id_b,
            BuildingSnapshot.building_id == building_id,
        )
    )
    snap_b = result_b.scalar_one_or_none()

    if snap_a is None or snap_b is None:
        return None

    trust_a = snap_a.overall_trust or 0.0
    trust_b = snap_b.overall_trust or 0.0
    completeness_a = snap_a.completeness_score or 0.0
    completeness_b = snap_b.completeness_score or 0.0

    grade_a = snap_a.passport_grade
    grade_b = snap_b.passport_grade
    grade_change = None
    if grade_a and grade_b and grade_a != grade_b:
        grade_change = f"{grade_a}\u2192{grade_b}"

    # Readiness changes
    readiness_a = snap_a.readiness_state_json or {}
    readiness_b = snap_b.readiness_state_json or {}
    readiness_changes = []
    all_types = set(list(readiness_a.keys()) + list(readiness_b.keys()))
    for rt in sorted(all_types):
        status_a = readiness_a.get(rt, {}).get("status") if isinstance(readiness_a.get(rt), dict) else None
        status_b = readiness_b.get(rt, {}).get("status") if isinstance(readiness_b.get(rt), dict) else None
        if status_a != status_b:
            readiness_changes.append({"type": rt, "from": status_a, "to": status_b})

    # Contradiction counts from passport state
    passport_a = snap_a.passport_state_json or {}
    passport_b = snap_b.passport_state_json or {}
    contradictions_a = passport_a.get("contradictions", {}).get("unresolved", 0) if isinstance(passport_a, dict) else 0
    contradictions_b = passport_b.get("contradictions", {}).get("unresolved", 0) if isinstance(passport_b, dict) else 0

    new_contradictions = max(0, contradictions_b - contradictions_a)
    resolved_contradictions = max(0, contradictions_a - contradictions_b)

    return {
        "building_id": str(building_id),
        "snapshot_a": {
            "id": str(snap_a.id),
            "captured_at": snap_a.captured_at.isoformat() if snap_a.captured_at else None,
            "passport_grade": grade_a,
            "overall_trust": trust_a,
            "completeness_score": completeness_a,
        },
        "snapshot_b": {
            "id": str(snap_b.id),
            "captured_at": snap_b.captured_at.isoformat() if snap_b.captured_at else None,
            "passport_grade": grade_b,
            "overall_trust": trust_b,
            "completeness_score": completeness_b,
        },
        "changes": {
            "trust_delta": round(trust_b - trust_a, 4),
            "completeness_delta": round(completeness_b - completeness_a, 4),
            "grade_change": grade_change,
            "readiness_changes": readiness_changes,
            "new_contradictions": new_contradictions,
            "resolved_contradictions": resolved_contradictions,
        },
    }


async def list_snapshots(
    db: AsyncSession,
    building_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[BuildingSnapshot]:
    """List snapshots for a building, newest first."""
    result = await db.execute(
        select(BuildingSnapshot)
        .where(BuildingSnapshot.building_id == building_id)
        .order_by(BuildingSnapshot.captured_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())
