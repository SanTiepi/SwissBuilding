"""Diagnostic integration service — handles publications from Batiscan and mission orders."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.diagnostic_mission_order import DiagnosticMissionOrder
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.diagnostic_publication_version import DiagnosticPublicationVersion
from app.models.domain_event import DomainEvent
from app.schemas.diagnostic_publication import (
    ContractValidationResult,
    DiagnosticMissionOrderCreate,
    DiagnosticPublicationPackage,
)
from app.services.batiscan_client import (
    BatiscanClientBase,
    BridgeAuthError,
    BridgeError,
    BridgeNotFoundError,
    BridgeValidationError,
)

logger = logging.getLogger(__name__)


async def _match_building(db: AsyncSession, identifiers: dict) -> tuple[str, str, UUID | None]:
    """Match a building by identifiers.

    Returns (match_state, match_key_type, building_id).
    Priority: egid > egrid > address.
    """
    if not identifiers:
        logger.warning("Empty building_identifiers — cannot match building")

    # 1. Try egid
    egid = identifiers.get("egid")
    if egid is not None:
        try:
            egid_int = int(egid)
        except (ValueError, TypeError):
            logger.warning("Malformed egid value: %r — skipping egid match", egid)
        else:
            result = await db.execute(select(Building).where(Building.egid == egid_int))
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


# ---------------------------------------------------------------------------
# Consumer Bridge v1
# ---------------------------------------------------------------------------


def validate_contract(payload: dict) -> ContractValidationResult:
    """Validate incoming package against expected contract."""
    errors: list[str] = []
    for field in ["source_system", "source_mission_id", "mission_type", "payload_hash", "published_at"]:
        if field not in payload or not payload[field]:
            errors.append(f"Missing required field: {field}")
    source = payload.get("source_system")
    if source and source != "batiscan":
        errors.append(f"Unknown source_system: {source}")
    # Warn on unexpected object_type but don't hard-fail (v1 compat)
    object_type = payload.get("object_type")
    if object_type and object_type not in ("diagnostic_report", "diagnostic_publication"):
        logger.warning("Unexpected object_type: %r — accepting for v1 compat", object_type)
    # Normalize schema_version: accept "1", "1.0", "v1" — store canonical "v1"
    schema_version = payload.get("schema_version")
    if schema_version and schema_version not in ("1", "1.0", "v1"):
        errors.append(f"Unsupported schema_version: {schema_version}")
    elif schema_version in ("1", "1.0"):
        payload["schema_version"] = "v1"
    return ContractValidationResult(valid=len(errors) == 0, errors=errors)


def _map_mission_type(payload: dict) -> str:
    """Derive mission_type from V4 payload, tolerant on naming."""
    mt = payload.get("mission_type")
    if mt:
        return str(mt)
    # Fallback: derive from object type or default
    return payload.get("type", "asbestos_full")


def map_v4_payload_to_package(raw: dict) -> DiagnosticPublicationPackage:
    """Map V4 producer format to BatiConnect consumer schema. Tolerant on optional fields."""
    payload = raw.get("payload", raw)  # Support both wrapped and flat formats
    published_at_raw = payload.get("published_at")
    if isinstance(published_at_raw, str):
        # Try ISO format parsing
        try:
            published_at = datetime.fromisoformat(published_at_raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            logger.warning("Malformed published_at value: %r — falling back to now()", published_at_raw)
            published_at = datetime.now(UTC)
    elif isinstance(published_at_raw, datetime):
        published_at = published_at_raw
    else:
        logger.warning("Missing published_at — falling back to now()")
        published_at = datetime.now(UTC)

    source_system = payload.get("source_system")
    if not source_system:
        logger.warning("Missing source_system — defaulting to 'batiscan'")
        source_system = "batiscan"

    payload_hash = payload.get("payload_hash", "")
    if not payload_hash:
        msg = "payload_hash is empty after mapping — cannot ingest"
        raise ValueError(msg)

    source_mission_id = payload.get("object_id") or payload.get("source_mission_id", "")
    if not source_mission_id:
        msg = "source_mission_id is empty after mapping — cannot ingest"
        raise ValueError(msg)

    return DiagnosticPublicationPackage(
        source_system=source_system,
        source_mission_id=source_mission_id,
        mission_type=_map_mission_type(payload),
        building_identifiers=payload.get("building_match_keys", payload.get("building_identifiers", {})),
        report_pdf_url=payload.get("report_pdf_url"),
        structured_summary=payload.get("publication_snapshot", payload.get("structured_summary", {})),
        annexes=payload.get("annexes", []),
        payload_hash=payload_hash,
        published_at=published_at,
        version=payload.get("snapshot_version", payload.get("version", 1)),
    )


async def fetch_and_ingest(
    db: AsyncSession,
    client: BatiscanClientBase,
    dossier_ref: str,
    user_id: UUID | None = None,
) -> dict:
    """Pull-mode: fetch package from V4, validate, ingest."""
    try:
        raw_payload = await client.fetch_diagnostic_package(dossier_ref)
    except BridgeAuthError:
        logger.warning("Bridge auth error fetching dossier %s", dossier_ref)
        return {"consumer_state": "auth_error", "error": "Authentication failed"}
    except BridgeNotFoundError:
        logger.warning("Dossier %s not found on producer", dossier_ref)
        return {"consumer_state": "not_found", "error": f"Dossier {dossier_ref} not found"}
    except BridgeValidationError as e:
        logger.warning("Producer rejected fetch for %s: %s", dossier_ref, e)
        return {"consumer_state": "rejected_source", "error": str(e)}
    except BridgeError as e:
        logger.warning("Bridge error fetching dossier %s: %s", dossier_ref, e)
        return {"consumer_state": "fetch_error", "error": str(e)}

    # Validate contract
    validation = validate_contract(raw_payload)
    if not validation.valid:
        return {"consumer_state": "validation_error", "errors": validation.errors}

    # Map to DiagnosticPublicationPackage schema
    try:
        package = map_v4_payload_to_package(raw_payload)
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("Payload mapping failed for %s: %s", dossier_ref, e)
        return {"consumer_state": "validation_error", "error": str(e)}

    # Use existing receive_publication (idempotent)
    try:
        publication = await receive_publication(db, package)
    except Exception as e:
        logger.exception("receive_publication failed for %s: %s", dossier_ref, e)
        return {"consumer_state": "ingest_error", "error": str(e)}

    # Detect idempotent replay: if publication already had a consumer_state and same payload_hash,
    # it was returned from the idempotency check — skip domain events
    is_replay = publication.consumer_state is not None and publication.payload_hash == package.payload_hash
    if is_replay:
        logger.info(
            "Idempotent replay for dossier %s — publication %s already ingested, skipping events",
            dossier_ref,
            publication.id,
        )

    # Update consumer_state
    if publication.building_id:
        publication.consumer_state = "matched"
    elif publication.match_state == "needs_review":
        publication.consumer_state = "review_required"
    else:
        publication.consumer_state = "ingested"
    publication.contract_version = raw_payload.get("schema_version", "v1")
    publication.fetched_at = datetime.now(UTC)
    publication.fetch_error = None  # Clear any previous fetch_error on success
    await db.flush()

    # Emit domain events only for new ingestions (not idempotent replays)
    if not is_replay:
        now = datetime.now(UTC)
        event = DomainEvent(
            event_type="diagnostic_publication_received",
            aggregate_type="diagnostic_report_publication",
            aggregate_id=publication.id,
            payload={"dossier_ref": dossier_ref, "consumer_state": publication.consumer_state},
            actor_user_id=user_id,
            occurred_at=now,
        )
        db.add(event)

        if publication.building_id:
            event2 = DomainEvent(
                event_type="diagnostic_publication_matched",
                aggregate_type="diagnostic_report_publication",
                aggregate_id=publication.id,
                payload={"building_id": str(publication.building_id), "match_state": publication.match_state},
                actor_user_id=user_id,
                occurred_at=now,
            )
            db.add(event2)

    return {"consumer_state": publication.consumer_state, "publication_id": str(publication.id)}
