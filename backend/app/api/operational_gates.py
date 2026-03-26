"""BatiConnect - Operational Gates API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.operational_gate import (
    BuildingGateStatus,
    GateEvaluation,
    GateOverrideRequest,
    OperationalGateList,
    OperationalGateRead,
)
from app.services import operational_gate_service as svc

router = APIRouter()


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# GET /buildings/{building_id}/gates
# ---------------------------------------------------------------------------
@router.get(
    "/buildings/{building_id}/gates",
    response_model=OperationalGateList,
)
async def list_gates(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all operational gates for a building with current status."""
    await _get_building_or_404(db, building_id)
    gates = await svc.ensure_building_gates(db, building_id)
    gate_reads = []
    for g in gates:
        prereqs = svc._parse_prerequisites(g.prerequisites or [])
        gate_reads.append(svc._gate_to_read(g, prereqs))
    return OperationalGateList(
        building_id=building_id,
        gates=gate_reads,
        total=len(gate_reads),
    )


# ---------------------------------------------------------------------------
# GET /buildings/{building_id}/gates/evaluate
# ---------------------------------------------------------------------------
@router.get(
    "/buildings/{building_id}/gates/evaluate",
    response_model=GateEvaluation,
)
async def evaluate_gates(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate all gates for a building (triggers prerequisite checks)."""
    await _get_building_or_404(db, building_id)
    return await svc.evaluate_gates(db, building_id)


# ---------------------------------------------------------------------------
# GET /buildings/{building_id}/gates/blocking
# ---------------------------------------------------------------------------
@router.get(
    "/buildings/{building_id}/gates/blocking",
    response_model=list[OperationalGateRead],
)
async def get_blocking_gates(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get only blocked/conditions_pending gates."""
    await _get_building_or_404(db, building_id)
    gates = await svc.get_blocking_gates(db, building_id)
    result = []
    for g in gates:
        prereqs = svc._parse_prerequisites(g.prerequisites or [])
        result.append(svc._gate_to_read(g, prereqs))
    return result


# ---------------------------------------------------------------------------
# GET /buildings/{building_id}/gates/status
# ---------------------------------------------------------------------------
@router.get(
    "/buildings/{building_id}/gates/status",
    response_model=BuildingGateStatus,
)
async def get_gate_status(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Summary of gate status for a building."""
    await _get_building_or_404(db, building_id)
    return await svc.get_gate_status(db, building_id)


# ---------------------------------------------------------------------------
# POST /gates/{gate_id}/override
# ---------------------------------------------------------------------------
@router.post(
    "/gates/{gate_id}/override",
    response_model=OperationalGateRead,
)
async def override_gate(
    gate_id: UUID,
    data: GateOverrideRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Override a blocked gate with reason (admin only). Creates audit trail."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can override gates")
    try:
        gate = await svc.override_gate(db, gate_id, current_user.id, data.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    prereqs = svc._parse_prerequisites(gate.prerequisites or [])
    return svc._gate_to_read(gate, prereqs)


# ---------------------------------------------------------------------------
# POST /gates/{gate_id}/clear
# ---------------------------------------------------------------------------
@router.post(
    "/gates/{gate_id}/clear",
    response_model=OperationalGateRead,
)
async def clear_gate(
    gate_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Clear a gate when all prerequisites are satisfied."""
    try:
        gate = await svc.clear_gate(db, gate_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    prereqs = svc._parse_prerequisites(gate.prerequisites or [])
    return svc._gate_to_read(gate, prereqs)
