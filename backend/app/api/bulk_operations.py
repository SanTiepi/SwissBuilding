"""Bulk operations API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.bulk_operations import (
    BulkOperationRequest,
    BulkOperationResult,
    BulkOperationType,
)
from app.services import bulk_operations_service

router = APIRouter()


@router.post("/bulk-operations/execute", response_model=BulkOperationResult)
async def execute_bulk_operation(
    body: BulkOperationRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Execute a bulk operation across multiple buildings."""
    building_uuids: list[UUID] = []
    for bid_str in body.building_ids:
        try:
            building_uuids.append(UUID(bid_str))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid building ID: {bid_str}",
            ) from None

    op = body.operation_type

    if op == BulkOperationType.generate_actions:
        return await bulk_operations_service.bulk_generate_actions(db, building_uuids, current_user.id)
    elif op == BulkOperationType.generate_unknowns:
        return await bulk_operations_service.bulk_generate_unknowns(db, building_uuids)
    elif op == BulkOperationType.evaluate_readiness:
        return await bulk_operations_service.bulk_evaluate_readiness(db, building_uuids)
    elif op == BulkOperationType.calculate_trust:
        return await bulk_operations_service.bulk_calculate_trust(db, building_uuids)
    elif op == BulkOperationType.run_dossier_agent:
        return await bulk_operations_service.bulk_run_dossier_agent(db, building_uuids)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {op}")
