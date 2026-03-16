"""
SwissBuildingOS - Diagnostic Service

CRUD operations for diagnostics with event tracking.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.diagnostic import Diagnostic
from app.models.event import Event
from app.schemas.diagnostic import DiagnosticCreate, DiagnosticUpdate


async def create_diagnostic(
    db: AsyncSession,
    building_id: UUID,
    data: DiagnosticCreate,
    diagnostician_id: UUID,
) -> Diagnostic:
    """
    Create a new diagnostic for a building, create a related Event, and commit.
    """
    diagnostic = Diagnostic(
        building_id=building_id,
        diagnostic_type=data.diagnostic_type,
        diagnostic_context=data.diagnostic_context,
        diagnostician_id=data.diagnostician_id or diagnostician_id,
        laboratory=data.laboratory,
        date_inspection=data.date_inspection,
        methodology=data.methodology,
        summary=data.summary,
        status="draft",
    )
    db.add(diagnostic)
    await db.flush()

    event = Event(
        building_id=building_id,
        event_type="diagnostic_created",
        date=data.date_inspection or date.today(),
        title=f"Diagnostic {data.diagnostic_type} created",
        description=f"New {data.diagnostic_type} diagnostic initiated (context: {data.diagnostic_context})",
        created_by=diagnostician_id,
        metadata_json={"diagnostic_id": str(diagnostic.id)},
    )
    db.add(event)

    await db.commit()

    # Re-fetch with eager-loaded samples
    stmt = select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.id == diagnostic.id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_diagnostic(db: AsyncSession, diagnostic_id: UUID) -> Diagnostic | None:
    """Get a single diagnostic by ID with eager-loaded samples."""
    stmt = select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.id == diagnostic_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_diagnostics(db: AsyncSession, building_id: UUID) -> list[Diagnostic]:
    """List all diagnostics for a building, ordered by inspection date descending."""
    stmt = (
        select(Diagnostic)
        .options(selectinload(Diagnostic.samples))
        .where(Diagnostic.building_id == building_id)
        .order_by(Diagnostic.date_inspection.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_diagnostic(db: AsyncSession, diagnostic_id: UUID, data: DiagnosticUpdate) -> Diagnostic | None:
    """
    Partially update a diagnostic. Only fields with non-None values are applied.
    Returns the updated Diagnostic or None if not found.
    """
    stmt = select(Diagnostic).where(Diagnostic.id == diagnostic_id)
    result = await db.execute(stmt)
    diagnostic = result.scalar_one_or_none()

    if diagnostic is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(diagnostic, field, value)

    await db.commit()

    # Re-fetch with eager-loaded samples
    stmt = select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.id == diagnostic_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def validate_diagnostic(db: AsyncSession, diagnostic_id: UUID) -> Diagnostic | None:
    """
    Set diagnostic status to 'validated' and create a validation Event.
    Returns the updated Diagnostic or None if not found.
    """
    stmt = select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.id == diagnostic_id)
    result = await db.execute(stmt)
    diagnostic = result.scalar_one_or_none()

    if diagnostic is None:
        return None

    diagnostic.status = "validated"
    await db.flush()

    event = Event(
        building_id=diagnostic.building_id,
        event_type="diagnostic_validated",
        date=date.today(),
        title=f"Diagnostic {diagnostic.diagnostic_type} validated",
        description=f"Diagnostic {diagnostic.id} has been validated",
        metadata_json={
            "diagnostic_id": str(diagnostic.id),
            "diagnostic_type": diagnostic.diagnostic_type,
        },
    )
    db.add(event)

    await db.commit()

    # Re-fetch with eager-loaded samples
    stmt = select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.id == diagnostic.id)
    result = await db.execute(stmt)
    return result.scalar_one()
