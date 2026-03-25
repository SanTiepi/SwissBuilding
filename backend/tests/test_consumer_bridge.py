"""Consumer Bridge v1 tests — fetch, validate, ingest, domain events."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import relationship

from app.models.building import Building
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.diagnostic_publication_version import DiagnosticPublicationVersion  # noqa: F401
from app.models.domain_event import DomainEvent

# Wire the missing back_populates relationship on Building so the mapper resolves.
if not hasattr(Building, "diagnostic_publications"):
    Building.diagnostic_publications = relationship(
        "DiagnosticReportPublication",
        back_populates="building",
    )

from app.services.batiscan_client import (
    BatiscanClientBase,
    BridgeAuthError,
    BridgeNotFoundError,
    BridgeValidationError,
)
from app.services.diagnostic_integration_service import (
    fetch_and_ingest,
    map_v4_payload_to_package,
    validate_contract,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_v4_payload(
    *,
    source_mission_id: str = "DOS-001",
    egid: int | None = None,
    egrid: str | None = None,
    address: str | None = None,
    payload_hash: str | None = None,
    schema_version: str = "v1",
    mission_type: str = "asbestos_full",
    include_ai: bool = True,
    include_remediation: bool = True,
) -> dict:
    """Build a realistic V4 producer payload."""
    identifiers: dict = {}
    if egid is not None:
        identifiers["egid"] = egid
    if egrid is not None:
        identifiers["egrid"] = egrid
    if address is not None:
        identifiers["address"] = address

    payload = {
        "source_system": "batiscan",
        "source_mission_id": source_mission_id,
        "object_id": source_mission_id,
        "mission_type": mission_type,
        "schema_version": schema_version,
        "building_match_keys": identifiers,
        "report_pdf_url": "https://cdn.example.com/report.pdf",
        "publication_snapshot": {"pollutants_found": ["asbestos"], "fach_urgency": "medium"},
        "annexes": [{"name": "lab.pdf", "url": "https://cdn.example.com/lab.pdf"}],
        "payload_hash": payload_hash or uuid.uuid4().hex,
        "published_at": datetime.now(UTC).isoformat(),
        "snapshot_version": 1,
    }

    if include_ai:
        payload["publication_snapshot"]["ai_analysis"] = {"confidence": 0.92}
    if include_remediation:
        payload["publication_snapshot"]["remediation_forms"] = [{"zone": "Z1", "method": "encapsulation"}]

    return payload


class MockBatiscanClient(BatiscanClientBase):
    """Mock client that returns configured responses."""

    def __init__(self, response: dict | None = None, error: Exception | None = None):
        self._response = response
        self._error = error

    async def send_mission_order(self, order_data: dict) -> dict:
        return {}

    async def check_mission_status(self, external_mission_id: str) -> dict:
        return {}

    async def fetch_diagnostic_package(self, dossier_ref: str) -> dict:
        if self._error:
            raise self._error
        return self._response or {}


async def _create_building(db, admin_user, *, egid=None, egrid=None, address="Rue Test 1"):
    building = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        egid=egid,
        egrid=egrid,
    )
    db.add(building)
    await db.flush()
    return building


# ===========================================================================
# Fetch & Ingest
# ===========================================================================


@pytest.mark.asyncio
async def test_fetch_200_ingests_correctly(db_session, admin_user):
    """Fetch 200 -> ingests and sets consumer_state."""
    await _create_building(db_session, admin_user, egid=12345)
    payload = _make_v4_payload(egid=12345)
    client = MockBatiscanClient(response=payload)

    result = await fetch_and_ingest(db_session, client, "DOS-001", user_id=admin_user.id)
    assert result["consumer_state"] == "matched"
    assert "publication_id" in result


@pytest.mark.asyncio
async def test_fetch_401_returns_auth_error(db_session, admin_user):
    """Fetch 401 -> auth_error state."""
    client = MockBatiscanClient(error=BridgeAuthError("Authentication failed"))
    result = await fetch_and_ingest(db_session, client, "DOS-FAIL")
    assert result["consumer_state"] == "auth_error"
    assert "error" in result


@pytest.mark.asyncio
async def test_fetch_404_returns_not_found(db_session, admin_user):
    """Fetch 404 -> not_found state."""
    client = MockBatiscanClient(error=BridgeNotFoundError("Not found"))
    result = await fetch_and_ingest(db_session, client, "DOS-MISSING")
    assert result["consumer_state"] == "not_found"
    assert "error" in result


@pytest.mark.asyncio
async def test_fetch_422_returns_rejected_source(db_session, admin_user):
    """Fetch 422 -> rejected_source state."""
    client = MockBatiscanClient(error=BridgeValidationError("Package not eligible"))
    result = await fetch_and_ingest(db_session, client, "DOS-INVALID")
    assert result["consumer_state"] == "rejected_source"


@pytest.mark.asyncio
async def test_idempotent_replay_no_duplicate(db_session, admin_user):
    """Same payload_hash fetched twice -> no duplicate, same publication."""
    await _create_building(db_session, admin_user, egid=12345)
    fixed_hash = "deadbeef" * 8
    payload = _make_v4_payload(egid=12345, payload_hash=fixed_hash)
    client = MockBatiscanClient(response=payload)

    r1 = await fetch_and_ingest(db_session, client, "DOS-001", user_id=admin_user.id)
    r2 = await fetch_and_ingest(db_session, client, "DOS-001", user_id=admin_user.id)
    assert r1["publication_id"] == r2["publication_id"]


@pytest.mark.asyncio
async def test_new_version_increments(db_session, admin_user):
    """Same source_mission_id but different hash -> new version."""
    await _create_building(db_session, admin_user, egid=12345)
    p1 = _make_v4_payload(egid=12345, payload_hash="hash_v1_" + "a" * 56)
    client1 = MockBatiscanClient(response=p1)
    r1 = await fetch_and_ingest(db_session, client1, "DOS-001", user_id=admin_user.id)

    p2 = _make_v4_payload(egid=12345, payload_hash="hash_v2_" + "b" * 56)
    client2 = MockBatiscanClient(response=p2)
    r2 = await fetch_and_ingest(db_session, client2, "DOS-001", user_id=admin_user.id)

    # Same publication, version incremented
    assert r1["publication_id"] == r2["publication_id"]
    pub_result = await db_session.execute(
        select(DiagnosticReportPublication).where(DiagnosticReportPublication.id == uuid.UUID(r1["publication_id"]))
    )
    pub = pub_result.scalar_one()
    assert pub.current_version == 2


@pytest.mark.asyncio
async def test_partial_package_no_ai_accepted(db_session, admin_user):
    """Package without AI analysis -> accepted (tolerant parsing)."""
    await _create_building(db_session, admin_user, egid=12345)
    payload = _make_v4_payload(egid=12345, include_ai=False)
    client = MockBatiscanClient(response=payload)
    result = await fetch_and_ingest(db_session, client, "DOS-NOAI", user_id=admin_user.id)
    assert result["consumer_state"] == "matched"


@pytest.mark.asyncio
async def test_partial_package_no_remediation_accepted(db_session, admin_user):
    """Package without remediation forms -> accepted (tolerant parsing)."""
    await _create_building(db_session, admin_user, egid=12345)
    payload = _make_v4_payload(egid=12345, include_remediation=False)
    client = MockBatiscanClient(response=payload)
    result = await fetch_and_ingest(db_session, client, "DOS-NOREM", user_id=admin_user.id)
    assert result["consumer_state"] == "matched"


@pytest.mark.asyncio
async def test_ambiguous_matching_review_required(db_session, admin_user):
    """Ambiguous address match -> review_required consumer_state."""
    await _create_building(db_session, admin_user, address="Rue de la Gare 10")
    b2 = Building(
        id=uuid.uuid4(),
        address="Rue de la Gare 12",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b2)
    await db_session.flush()

    payload = _make_v4_payload(address="Gare")
    # Remove egid/egrid identifiers to force address matching
    payload["building_match_keys"] = {"address": "Gare"}
    client = MockBatiscanClient(response=payload)
    result = await fetch_and_ingest(db_session, client, "DOS-AMB", user_id=admin_user.id)
    assert result["consumer_state"] == "review_required"


# ===========================================================================
# Contract validation
# ===========================================================================


def test_contract_validation_missing_fields():
    """Missing required fields -> invalid."""
    result = validate_contract({"source_system": "batiscan"})
    assert not result.valid
    assert any("source_mission_id" in e for e in result.errors)
    assert any("payload_hash" in e for e in result.errors)


def test_contract_validation_wrong_source_system():
    """Wrong source_system -> invalid."""
    payload = {
        "source_system": "unknown_system",
        "source_mission_id": "M-001",
        "mission_type": "asbestos_full",
        "payload_hash": "abc123",
        "published_at": datetime.now(UTC).isoformat(),
    }
    result = validate_contract(payload)
    assert not result.valid
    assert any("Unknown source_system" in e for e in result.errors)


def test_contract_validation_unsupported_version():
    """Unsupported schema_version -> invalid."""
    payload = {
        "source_system": "batiscan",
        "source_mission_id": "M-001",
        "mission_type": "asbestos_full",
        "payload_hash": "abc123",
        "published_at": datetime.now(UTC).isoformat(),
        "schema_version": "v99",
    }
    result = validate_contract(payload)
    assert not result.valid
    assert any("Unsupported schema_version" in e for e in result.errors)


def test_contract_validation_valid_payload():
    """Valid payload -> passes."""
    payload = {
        "source_system": "batiscan",
        "source_mission_id": "M-001",
        "mission_type": "asbestos_full",
        "payload_hash": "abc123",
        "published_at": datetime.now(UTC).isoformat(),
        "schema_version": "v1",
    }
    result = validate_contract(payload)
    assert result.valid
    assert result.errors == []


@pytest.mark.asyncio
async def test_contract_validation_error_from_fetch(db_session, admin_user):
    """Fetch returns payload failing contract validation -> validation_error."""
    # Payload with wrong source_system
    bad_payload = _make_v4_payload()
    bad_payload["source_system"] = "not_batiscan"
    client = MockBatiscanClient(response=bad_payload)
    result = await fetch_and_ingest(db_session, client, "DOS-BAD")
    assert result["consumer_state"] == "validation_error"
    assert "errors" in result


# ===========================================================================
# Domain events
# ===========================================================================


@pytest.mark.asyncio
async def test_domain_events_emitted_on_receive(db_session, admin_user):
    """Domain event emitted when publication is received."""
    await _create_building(db_session, admin_user, egid=12345)
    payload = _make_v4_payload(egid=12345)
    client = MockBatiscanClient(response=payload)
    await fetch_and_ingest(db_session, client, "DOS-EVT", user_id=admin_user.id)
    await db_session.flush()

    events = (
        (
            await db_session.execute(
                select(DomainEvent).where(DomainEvent.event_type == "diagnostic_publication_received")
            )
        )
        .scalars()
        .all()
    )
    assert len(events) >= 1
    assert events[-1].aggregate_type == "diagnostic_report_publication"


@pytest.mark.asyncio
async def test_domain_events_emitted_on_match(db_session, admin_user):
    """Domain event emitted when publication is matched to a building."""
    await _create_building(db_session, admin_user, egid=12345)
    payload = _make_v4_payload(egid=12345)
    client = MockBatiscanClient(response=payload)
    await fetch_and_ingest(db_session, client, "DOS-MATCH-EVT", user_id=admin_user.id)
    await db_session.flush()

    events = (
        (
            await db_session.execute(
                select(DomainEvent).where(DomainEvent.event_type == "diagnostic_publication_matched")
            )
        )
        .scalars()
        .all()
    )
    assert len(events) >= 1
    assert "building_id" in events[-1].payload


# ===========================================================================
# Payload mapping
# ===========================================================================


def test_map_v4_payload_tolerant_parsing():
    """map_v4_payload_to_package handles missing optional fields gracefully."""
    minimal = {
        "source_system": "batiscan",
        "source_mission_id": "M-MINIMAL",
        "mission_type": "asbestos_full",
        "payload_hash": "abc123",
        "published_at": datetime.now(UTC).isoformat(),
    }
    package = map_v4_payload_to_package(minimal)
    assert package.source_system == "batiscan"
    assert package.source_mission_id == "M-MINIMAL"
    assert package.mission_type == "asbestos_full"
    assert package.building_identifiers == {}
    assert package.annexes == []
    assert package.structured_summary == {}


def test_map_v4_payload_wrapped_format():
    """map_v4_payload_to_package handles wrapped payload format."""
    inner = {
        "source_system": "batiscan",
        "source_mission_id": "M-WRAPPED",
        "mission_type": "pcb",
        "payload_hash": "wrapped_hash",
        "published_at": datetime.now(UTC).isoformat(),
        "building_match_keys": {"egid": 99999},
    }
    wrapped = {"payload": inner, "metadata": {"version": "v1"}}
    package = map_v4_payload_to_package(wrapped)
    assert package.source_mission_id == "M-WRAPPED"
    assert package.building_identifiers == {"egid": 99999}
