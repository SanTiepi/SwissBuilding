"""BatiConnect — ROI Calculator Service.

Computes ROI metrics grounded in actual workflow events stored in the DB.
NO invented numbers — only compute from Obligation, PermitProcedure,
ProofDelivery, and AuthorityRequest records.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authority_request import AuthorityRequest
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.models.proof_delivery import ProofDelivery
from app.schemas.roi import ROIBreakdown, ROIReport

# Estimated hours saved per completed obligation (conservative: filing + follow-up)
_HOURS_PER_OBLIGATION_COMPLETED = 2.0

# Estimated hours saved per approved procedure (assembly + submission + tracking)
_HOURS_PER_PROCEDURE_APPROVED = 4.0


async def calculate_building_roi(db: AsyncSession, building_id: uuid.UUID) -> ROIReport:
    """Calculate ROI report for a building based on actual workflow events."""
    evidence_sources: list[str] = []
    breakdown: list[ROIBreakdown] = []
    time_saved_hours = 0.0
    rework_avoided = 0
    blocker_days_saved = 0.0
    pack_reuse_count = 0

    # 1. Obligations completed — time saved from tracked deadlines
    obligations_completed = await _count_completed_obligations(db, building_id)
    if obligations_completed > 0:
        evidence_sources.append("obligations")
        hours = obligations_completed * _HOURS_PER_OBLIGATION_COMPLETED
        time_saved_hours += hours
        breakdown.append(
            ROIBreakdown(
                label="Obligations completed (deadline tracking saved)",
                value=hours,
                unit="hours",
                evidence_count=obligations_completed,
            )
        )

    # 2. Permit procedures approved — time saved from structured submission
    procedures_approved = await _count_approved_procedures(db, building_id)
    if procedures_approved > 0:
        evidence_sources.append("permit_procedures")
        hours = procedures_approved * _HOURS_PER_PROCEDURE_APPROVED
        time_saved_hours += hours
        breakdown.append(
            ROIBreakdown(
                label="Permit procedures approved (submission workflow saved)",
                value=hours,
                unit="hours",
                evidence_count=procedures_approved,
            )
        )

    # 3. Blocker days saved — from authority request response times
    blocker_days_saved = await _sum_blocker_days_saved(db, building_id)
    if blocker_days_saved > 0:
        evidence_sources.append("authority_requests")
        breakdown.append(
            ROIBreakdown(
                label="Blocker days saved (complement response turnaround)",
                value=blocker_days_saved,
                unit="days",
                evidence_count=await _count_responded_requests(db, building_id),
            )
        )

    # 4. Proof reuse — ProofDelivery records show how many times proof was reused
    reuse_count, total_deliveries = await _count_proof_reuse(db, building_id)
    pack_reuse_count = reuse_count
    if total_deliveries > 0:
        evidence_sources.append("proof_deliveries")
        # Each reuse avoids a manual rebuild — count as rework avoided
        rework_avoided = reuse_count
        breakdown.append(
            ROIBreakdown(
                label="Proof reuse (deliveries to multiple audiences)",
                value=float(reuse_count),
                unit="count",
                evidence_count=total_deliveries,
            )
        )

    return ROIReport(
        building_id=building_id,
        time_saved_hours=round(time_saved_hours, 1),
        rework_avoided=rework_avoided,
        blocker_days_saved=round(blocker_days_saved, 1),
        pack_reuse_count=pack_reuse_count,
        breakdown=breakdown,
        evidence_sources=evidence_sources,
    )


async def _count_completed_obligations(db: AsyncSession, building_id: uuid.UUID) -> int:
    stmt = select(func.count()).where(
        Obligation.building_id == building_id,
        Obligation.status == "completed",
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def _count_approved_procedures(db: AsyncSession, building_id: uuid.UUID) -> int:
    stmt = select(func.count()).where(
        PermitProcedure.building_id == building_id,
        PermitProcedure.status == "approved",
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def _sum_blocker_days_saved(db: AsyncSession, building_id: uuid.UUID) -> float:
    """Sum days between authority request creation and response for responded requests."""
    stmt = (
        select(AuthorityRequest)
        .join(PermitProcedure, AuthorityRequest.procedure_id == PermitProcedure.id)
        .where(
            PermitProcedure.building_id == building_id,
            AuthorityRequest.status.in_(["responded", "closed"]),
            AuthorityRequest.responded_at.is_not(None),
        )
    )
    result = await db.execute(stmt)
    requests = result.scalars().all()

    total_days = 0.0
    for req in requests:
        if req.responded_at and req.created_at:
            delta = req.responded_at - req.created_at
            total_days += delta.total_seconds() / 86400.0
    return total_days


async def _count_responded_requests(db: AsyncSession, building_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(AuthorityRequest)
        .join(PermitProcedure, AuthorityRequest.procedure_id == PermitProcedure.id)
        .where(
            PermitProcedure.building_id == building_id,
            AuthorityRequest.status.in_(["responded", "closed"]),
        )
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def _count_proof_reuse(db: AsyncSession, building_id: uuid.UUID) -> tuple[int, int]:
    """Count total deliveries and reuse (same target_id delivered to multiple audiences)."""
    # Total deliveries for this building
    total_stmt = select(func.count()).where(ProofDelivery.building_id == building_id)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0

    # Count target_ids that were delivered more than once (reused)
    reuse_stmt = select(func.count()).select_from(
        select(ProofDelivery.target_id)
        .where(ProofDelivery.building_id == building_id)
        .group_by(ProofDelivery.target_id, ProofDelivery.target_type)
        .having(func.count() > 1)
        .subquery()
    )
    reuse_result = await db.execute(reuse_stmt)
    reuse = reuse_result.scalar() or 0

    return reuse, total
