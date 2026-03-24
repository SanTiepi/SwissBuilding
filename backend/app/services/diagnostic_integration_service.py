"""Diagnostic integration service — handles publications from Batiscan and mission orders."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.diagnostic_mission_order import DiagnosticMissionOrder
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.diagnostic_publication_version import DiagnosticPublicationVersion
from app.schemas.diagnostic_publication import (
    DiagnosticMissionOrderCreate,
    DiagnosticPublicationPackage,
)

logger = logging.getLogger(__name__)


async def _match_building(db: AsyncSession, identifiers: dict) -> tuple[str, str, UUID | None]:
    """Match a building by identifiers.

    Returns (match_state, match_key_type, building_id).
    Priority: egid > egrid > address.
    """
    # 1. Try egid
    egid = identifiers.get("egid")
    if egid is not None:
        result = await db.execute(select(Building).where(Building.egid == int(egid)))
        building = result.scalar_one_or_none()
        if building:
            return "auto_matched", "egid", building.id

    # 2. Try egrid
    egrid = identifiers.get("egrid")
    if egrid:
        result = await db.execute(select(Building).where(Building.egrid == str(egrid)))
        building = result.scalar_one_or_none()
        if building:
            return "auto_matched", "egrid", building.id

    # 3. Try address (partial match → needs_review)
    address = identifiers.get("address")
    if address:
        result = await db.execute(select(Building).where(Building.address.ilike(f"%{address}%")))
        buildings = result.scalars().all()
        if len(buildings) == 1:
            return "needs_review", "address", buildings[0].id
        elif len(buildings) > 1:
            return "needs_review", "address", None

    return "unmatched", "none", None


async def receive_publication(db: AsyncSession, package: DiagnosticPublicationPackage) -> DiagnosticReportPublication:
    """Receive a diagnostic report publication from an external system.

    1. Check idempotency: if same payload_hash exists, return existing (skip).
    2. Try to match building via egid/egrid/address.
    3. Check if publication for same source_mission_id exists:
       - If yes: increment version, archive old version.
       - If no: create new publication.
    4. Return the publication.
    """
    # Idempotency check
    existing = await db.execute(
        select(DiagnosticReportPublication).where(DiagnosticReportPublication.payload_hash == package.payload_hash)
    )
    found = existing.scalar_one_or_none()
    if found:
        logger.info(
            "Duplicate payload_hash %s — returning existing publication %s",
            package.payload_hash,
            found.id,
        )
        return found

    # Match building
    match_state, match_key_type, building_id = await _match_building(db, package.building_identifiers)
    match_key = _extract_match_key(package.building_identifiers, match_key_type)

    # Check for existing publication with same source_mission_id
    prev_result = await db.execute(
        select(DiagnosticReportPublication).where(
            DiagnosticReportPublication.source_mission_id == package.source_mission_id,
            DiagnosticReportPublication.source_system == package.source_system,
        )
    )
    prev_pub = prev_result.scalar_one_or_none()

    if prev_pub:
        # Archive current version
        version_record = DiagnosticPublicationVersion(
            publication_id=prev_pub.id,
            version=prev_pub.current_version,
            published_at=prev_pub.published_at,
            payload_hash=prev_pub.payload_hash,
            report_pdf_url=prev_pub.report_pdf_url,
            structured_summary=prev_pub.structured_summary,
            annexes=prev_pub.annexes,
        )
        db.add(version_record)

        # Update publication with new data
        prev_pub.current_version += 1
        prev_pub.payload_hash = package.payload_hash
        prev_pub.report_pdf_url = package.report_pdf_url
        prev_pub.structured_summary = package.structured_summary
        prev_pub.annexes = package.annexes or []
        prev_pub.published_at = package.published_at
        prev_pub.mission_type = package.mission_type
        if building_id:
            prev_pub.building_id = building_id
            prev_pub.match_state = match_state
            prev_pub.match_key = match_key
            prev_pub.match_key_type = match_key_type

        await db.flush()
        logger.info(
            "Updated publication %s to version %d",
            prev_pub.id,
            prev_pub.current_version,
        )
        return prev_pub

    # Create new publication
    publication = DiagnosticReportPublication(
        building_id=building_id,
        source_system=package.source_system,
        source_mission_id=package.source_mission_id,
        current_version=1,
        match_state=match_state,
        match_key=match_key,
        match_key_type=match_key_type,
        report_pdf_url=package.report_pdf_url,
        structured_summary=package.structured_summary,
        annexes=package.annexes or [],
        payload_hash=package.payload_hash,
        mission_type=package.mission_type,
        published_at=package.published_at,
        source_type="import",
        confidence="verified",
        source_ref=f"{package.source_system}:{package.source_mission_id}",
    )
    db.add(publication)
    await db.flush()
    logger.info("Created publication %s (match_state=%s)", publication.id, match_state)
    return publication


def _extract_match_key(identifiers: dict, match_key_type: str) -> str | None:
    """Extract the value used for matching from identifiers."""
    if match_key_type == "egid":
        return str(identifiers.get("egid"))
    if match_key_type == "egrid":
        return str(identifiers.get("egrid"))
    if match_key_type == "address":
        return str(identifiers.get("address"))
    return None


async def match_publication(db: AsyncSession, publication_id: UUID, building_id: UUID) -> DiagnosticReportPublication:
    """Manually match an unmatched/needs_review publication to a building.

    Updates match_state to 'manual_matched'.
    """
    result = await db.execute(
        select(DiagnosticReportPublication).where(DiagnosticReportPublication.id == publication_id)
    )
    publication = result.scalar_one_or_none()
    if not publication:
        msg = f"Publication {publication_id} not found"
        raise ValueError(msg)

    if publication.match_state not in ("unmatched", "needs_review"):
        msg = f"Publication {publication_id} is already matched (state={publication.match_state})"
        raise ValueError(msg)

    # Verify building exists
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if not building:
        msg = f"Building {building_id} not found"
        raise ValueError(msg)

    publication.building_id = building_id
    publication.match_state = "manual_matched"
    publication.match_key_type = "manual"
    publication.match_key = str(building_id)
    await db.flush()

    logger.info(
        "Manually matched publication %s to building %s",
        publication_id,
        building_id,
    )
    return publication


async def create_mission_order(db: AsyncSession, order: DiagnosticMissionOrderCreate) -> DiagnosticMissionOrder:
    """Create a new diagnostic mission order in draft status.

    Populates building_identifiers from the building record.
    """
    # Load building to capture identifiers
    bld_result = await db.execute(select(Building).where(Building.id == order.building_id))
    building = bld_result.scalar_one_or_none()
    if not building:
        msg = f"Building {order.building_id} not found"
        raise ValueError(msg)

    building_identifiers = {
        "egid": building.egid,
        "egrid": building.egrid,
        "official_id": building.official_id,
        "address": building.address,
    }

    mission = DiagnosticMissionOrder(
        building_id=order.building_id,
        requester_org_id=order.requester_org_id,
        mission_type=order.mission_type,
        status="draft",
        context_notes=order.context_notes,
        attachments=order.attachments or [],
        building_identifiers=building_identifiers,
    )
    db.add(mission)
    await db.flush()

    logger.info("Created mission order %s for building %s", mission.id, building.id)
    return mission


async def get_publications_for_building(db: AsyncSession, building_id: UUID) -> list[DiagnosticReportPublication]:
    """Get all publications matched to a building, ordered by published_at desc."""
    result = await db.execute(
        select(DiagnosticReportPublication)
        .where(DiagnosticReportPublication.building_id == building_id)
        .order_by(DiagnosticReportPublication.published_at.desc())
    )
    return list(result.scalars().all())


async def get_unmatched_publications(
    db: AsyncSession,
) -> list[DiagnosticReportPublication]:
    """Get all publications in needs_review or unmatched state."""
    result = await db.execute(
        select(DiagnosticReportPublication).where(
            DiagnosticReportPublication.match_state.in_(["needs_review", "unmatched"])
        )
    )
    return list(result.scalars().all())


async def get_publication_with_versions(db: AsyncSession, publication_id: UUID) -> DiagnosticReportPublication:
    """Get a publication with its version history."""
    result = await db.execute(
        select(DiagnosticReportPublication)
        .where(DiagnosticReportPublication.id == publication_id)
        .options(selectinload(DiagnosticReportPublication.versions))
    )
    publication = result.scalar_one_or_none()
    if not publication:
        msg = f"Publication {publication_id} not found"
        raise ValueError(msg)
    return publication


async def get_mission_orders_for_building(db: AsyncSession, building_id: UUID) -> list[DiagnosticMissionOrder]:
    """Get all mission orders for a building."""
    result = await db.execute(
        select(DiagnosticMissionOrder)
        .where(DiagnosticMissionOrder.building_id == building_id)
        .order_by(DiagnosticMissionOrder.created_at.desc())
    )
    return list(result.scalars().all())
