"""Service for generating standardized passport exchange documents."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.schemas.passport_exchange import (
    PassportExchangeDocument,
    PassportExchangeMetadata,
)
from app.services.passport_service import get_passport_summary

EXCHANGE_SCHEMA_VERSION = "1.0.0"


async def export_passport(
    db: AsyncSession,
    building_id: UUID,
    include_transfer: bool = False,
) -> PassportExchangeDocument | None:
    """Export a building's passport as a standardized exchange document.

    Returns None if the building does not exist.

    When *include_transfer* is True, diagnostics/interventions/actions summaries
    from the transfer package service are included in the document.
    """
    # Fetch building for identity fields
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # Get passport summary
    passport = await get_passport_summary(db, building_id)

    metadata = PassportExchangeMetadata(
        schema_version=EXCHANGE_SCHEMA_VERSION,
        exported_at=datetime.now(UTC),
    )

    # Extract passport sections (passport is guaranteed non-None here since building exists)
    knowledge_state = passport["knowledge_state"] if passport else None
    readiness = passport["readiness"] if passport else None
    completeness = passport["completeness"] if passport else None
    blind_spots = passport["blind_spots"] if passport else None
    contradictions = passport["contradictions"] if passport else None
    evidence_coverage = passport["evidence_coverage"] if passport else None
    passport_grade = passport["passport_grade"] if passport else None

    # Optional transfer package sections
    diagnostics_summary: dict | None = None
    interventions_summary: dict | None = None
    actions_summary: dict | None = None

    if include_transfer:
        from app.services.transfer_package_service import generate_transfer_package

        package = await generate_transfer_package(
            db,
            building_id,
            include_sections=["diagnostics", "interventions", "actions"],
        )
        if package is not None:
            diagnostics_summary = package.diagnostics_summary
            interventions_summary = package.interventions_summary
            actions_summary = package.actions_summary

    return PassportExchangeDocument(
        metadata=metadata,
        building_id=building.id,
        address=building.address,
        city=building.city,
        canton=building.canton,
        construction_year=building.construction_year,
        passport_grade=passport_grade,
        knowledge_state=knowledge_state,
        readiness=readiness,
        completeness=completeness,
        blind_spots=blind_spots,
        contradictions=contradictions,
        evidence_coverage=evidence_coverage,
        diagnostics_summary=diagnostics_summary,
        interventions_summary=interventions_summary,
        actions_summary=actions_summary,
    )
