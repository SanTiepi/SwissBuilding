"""
SwissBuildingOS - Bulk Operations Service

Provides batch execution of generators and evaluators across multiple buildings.
Each operation processes buildings individually with error isolation — a failure
on one building does not prevent the others from completing.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.schemas.bulk_operations import BulkBuildingResult, BulkOperationResult
from app.services import (
    action_generator,
    readiness_reasoner,
    trust_score_calculator,
    unknown_generator,
)
from app.services.dossier_completion_agent import run_dossier_completion

logger = logging.getLogger(__name__)

MAX_BUILDINGS = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _validate_building_ids(
    db: AsyncSession,
    building_ids: list[UUID],
) -> dict[UUID, Building | None]:
    """Return a mapping of building_id → Building (or None if missing)."""
    result = await db.execute(select(Building).where(Building.id.in_(building_ids)))
    buildings = {b.id: b for b in result.scalars().all()}
    return {bid: buildings.get(bid) for bid in building_ids}


# ---------------------------------------------------------------------------
# Bulk generate actions
# ---------------------------------------------------------------------------


async def bulk_generate_actions(
    db: AsyncSession,
    building_ids: list[UUID],
    user_id: UUID,
) -> BulkOperationResult:
    """Generate actions from all diagnostics for each building."""
    started_at = datetime.now(UTC)
    building_map = await _validate_building_ids(db, building_ids)
    results: list[BulkBuildingResult] = []
    succeeded = failed = skipped = 0

    for bid, building in building_map.items():
        if building is None:
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="skipped",
                    message="Building not found",
                )
            )
            skipped += 1
            continue

        try:
            diag_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == bid))
            diagnostic_ids = list(diag_result.scalars().all())
            total_created = 0
            for diag_id in diagnostic_ids:
                actions = await action_generator.generate_actions_from_diagnostic(db, bid, diag_id)
                total_created += len(actions)
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="success",
                    message=f"Processed {len(diagnostic_ids)} diagnostics",
                    items_created=total_created,
                )
            )
            succeeded += 1
        except Exception as exc:
            logger.exception("bulk_generate_actions failed for building %s", bid)
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="failed",
                    message=str(exc),
                )
            )
            failed += 1

    return BulkOperationResult(
        operation_type="generate_actions",
        total_buildings=len(building_ids),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=results,
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Bulk generate unknowns
# ---------------------------------------------------------------------------


async def bulk_generate_unknowns(
    db: AsyncSession,
    building_ids: list[UUID],
) -> BulkOperationResult:
    """Generate unknown issues for each building."""
    started_at = datetime.now(UTC)
    building_map = await _validate_building_ids(db, building_ids)
    results: list[BulkBuildingResult] = []
    succeeded = failed = skipped = 0

    for bid, building in building_map.items():
        if building is None:
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="skipped",
                    message="Building not found",
                )
            )
            skipped += 1
            continue

        try:
            unknowns = await unknown_generator.generate_unknowns(db, bid)
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="success",
                    message=f"Generated {len(unknowns)} unknowns",
                    items_created=len(unknowns),
                )
            )
            succeeded += 1
        except Exception as exc:
            logger.exception("bulk_generate_unknowns failed for building %s", bid)
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="failed",
                    message=str(exc),
                )
            )
            failed += 1

    return BulkOperationResult(
        operation_type="generate_unknowns",
        total_buildings=len(building_ids),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=results,
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Bulk evaluate readiness
# ---------------------------------------------------------------------------


async def bulk_evaluate_readiness(
    db: AsyncSession,
    building_ids: list[UUID],
) -> BulkOperationResult:
    """Evaluate safe_to_start readiness for each building."""
    started_at = datetime.now(UTC)
    building_map = await _validate_building_ids(db, building_ids)
    results: list[BulkBuildingResult] = []
    succeeded = failed = skipped = 0

    for bid, building in building_map.items():
        if building is None:
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="skipped",
                    message="Building not found",
                )
            )
            skipped += 1
            continue

        try:
            assessment = await readiness_reasoner.evaluate_readiness(db, bid, "safe_to_start")
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="success",
                    message=f"Readiness status: {assessment.status}",
                    items_created=1,
                )
            )
            succeeded += 1
        except Exception as exc:
            logger.exception("bulk_evaluate_readiness failed for building %s", bid)
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="failed",
                    message=str(exc),
                )
            )
            failed += 1

    return BulkOperationResult(
        operation_type="evaluate_readiness",
        total_buildings=len(building_ids),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=results,
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Bulk calculate trust
# ---------------------------------------------------------------------------


async def bulk_calculate_trust(
    db: AsyncSession,
    building_ids: list[UUID],
) -> BulkOperationResult:
    """Calculate trust scores for each building."""
    started_at = datetime.now(UTC)
    building_map = await _validate_building_ids(db, building_ids)
    results: list[BulkBuildingResult] = []
    succeeded = failed = skipped = 0

    for bid, building in building_map.items():
        if building is None:
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="skipped",
                    message="Building not found",
                )
            )
            skipped += 1
            continue

        try:
            trust_obj = await trust_score_calculator.calculate_trust_score(db, bid)
            score = trust_obj.overall_score if trust_obj else 0.0
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="success",
                    message=f"Trust score: {score:.2f}",
                    items_created=1,
                )
            )
            succeeded += 1
        except Exception as exc:
            logger.exception("bulk_calculate_trust failed for building %s", bid)
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="failed",
                    message=str(exc),
                )
            )
            failed += 1

    return BulkOperationResult(
        operation_type="calculate_trust",
        total_buildings=len(building_ids),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=results,
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Bulk run dossier agent
# ---------------------------------------------------------------------------


async def bulk_run_dossier_agent(
    db: AsyncSession,
    building_ids: list[UUID],
) -> BulkOperationResult:
    """Run dossier completion agent for each building."""
    started_at = datetime.now(UTC)
    building_map = await _validate_building_ids(db, building_ids)
    results: list[BulkBuildingResult] = []
    succeeded = failed = skipped = 0

    for bid, building in building_map.items():
        if building is None:
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="skipped",
                    message="Building not found",
                )
            )
            skipped += 1
            continue

        try:
            report = await run_dossier_completion(db, bid)
            status_msg = report.overall_status if report else "no_report"
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="success",
                    message=f"Dossier status: {status_msg}",
                    items_created=1,
                )
            )
            succeeded += 1
        except Exception as exc:
            logger.exception("bulk_run_dossier_agent failed for building %s", bid)
            results.append(
                BulkBuildingResult(
                    building_id=str(bid),
                    status="failed",
                    message=str(exc),
                )
            )
            failed += 1

    return BulkOperationResult(
        operation_type="run_dossier_agent",
        total_buildings=len(building_ids),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=results,
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )
