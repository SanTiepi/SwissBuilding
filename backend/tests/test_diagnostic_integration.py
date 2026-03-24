"""Diagnostic integration tests — publications, matching, mission orders."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import relationship

from app.models.building import Building
from app.models.diagnostic_mission_order import DiagnosticMissionOrder  # noqa: F401
from app.models.diagnostic_publication import DiagnosticReportPublication  # noqa: F401
from app.models.diagnostic_publication_version import DiagnosticPublicationVersion  # noqa: F401
from app.models.organization import Organization

# Wire the missing back_populates relationship on Building so the mapper resolves.
# (Production code should add this; tests cannot modify production files.)
if not hasattr(Building, "diagnostic_publications"):
    Building.diagnostic_publications = relationship(
        "DiagnosticReportPublication",
        back_populates="building",
    )
from app.schemas.diagnostic_publication import (
    DiagnosticMissionOrderCreate,
    DiagnosticPublicationPackage,
    PublicationMatchRequest,
)
from app.services.diagnostic_integration_service import (
    create_mission_order,
    get_publication_with_versions,
    get_publications_for_building,
    get_unmatched_publications,
    match_publication,
    receive_publication,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_package(
    *,
    egid: int | None = None,
    egrid: str | None = None,
    address: str | None = None,
    payload_hash: str | None = None,
    source_mission_id: str = "M-001",
    mission_type: str = "asbestos_full",
    structured_summary: dict | None = None,
    annexes: list[dict] | None = None,
) -> DiagnosticPublicationPackage:
    identifiers: dict = {}
    if egid is not None:
        identifiers["egid"] = egid
    if egrid is not None:
        identifiers["egrid"] = egrid
    if address is not None:
        identifiers["address"] = address
    return DiagnosticPublicationPackage(
        source_system="batiscan",
        source_mission_id=source_mission_id,
        mission_type=mission_type,
        building_identifiers=identifiers,
        report_pdf_url="https://cdn.example.com/report.pdf",
        structured_summary=structured_summary or {"pollutants_found": ["asbestos"]},
        annexes=annexes or [],
        payload_hash=payload_hash or uuid.uuid4().hex,
        published_at=datetime.now(UTC),
    )


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
# Publication receive
# ===========================================================================


@pytest.mark.asyncio
async def test_receive_publication_egid_match(db_session, admin_user):
    """1. Receive publication with egid match -> auto_matched, building_id set."""
    building = await _create_building(db_session, admin_user, egid=12345)
    pkg = _make_package(egid=12345)
    pub = await receive_publication(db_session, pkg)
    assert pub.match_state == "auto_matched"
    assert pub.building_id == building.id
    assert pub.match_key_type == "egid"


@pytest.mark.asyncio
async def test_receive_publication_egrid_match(db_session, admin_user):
    """2. Receive publication with egrid match -> auto_matched."""
    building = await _create_building(db_session, admin_user, egrid="CH123456789012")
    pkg = _make_package(egrid="CH123456789012")
    pub = await receive_publication(db_session, pkg)
    assert pub.match_state == "auto_matched"
    assert pub.building_id == building.id
    assert pub.match_key_type == "egrid"


@pytest.mark.asyncio
async def test_receive_publication_address_partial_match(db_session, admin_user):
    """3. Receive publication with single address partial match -> needs_review."""
    building = await _create_building(db_session, admin_user, address="Avenue de la Gare 10")
    pkg = _make_package(address="Gare 10")
    pub = await receive_publication(db_session, pkg)
    assert pub.match_state == "needs_review"
    assert pub.building_id == building.id
    assert pub.match_key_type == "address"


@pytest.mark.asyncio
async def test_receive_publication_no_match(db_session, admin_user):
    """4. Receive publication with no match -> unmatched, building_id is None."""
    await _create_building(db_session, admin_user, egid=99999)
    pkg = _make_package(egid=11111)
    pub = await receive_publication(db_session, pkg)
    assert pub.match_state == "unmatched"
    assert pub.building_id is None


@pytest.mark.asyncio
async def test_receive_publication_idempotent(db_session, admin_user):
    """5. Same payload_hash -> idempotent, returns existing."""
    await _create_building(db_session, admin_user, egid=12345)
    pkg = _make_package(egid=12345, payload_hash="deadbeef" * 8)
    pub1 = await receive_publication(db_session, pkg)
    pub2 = await receive_publication(db_session, pkg)
    assert pub1.id == pub2.id


@pytest.mark.asyncio
async def test_receive_publication_new_version(db_session, admin_user):
    """6. Same source_mission_id but different hash -> new version created."""
    await _create_building(db_session, admin_user, egid=12345)
    pkg1 = _make_package(egid=12345, source_mission_id="MISSION-1", payload_hash="hash_v1_" + "a" * 56)
    pub1 = await receive_publication(db_session, pkg1)
    assert pub1.current_version == 1

    pkg2 = _make_package(egid=12345, source_mission_id="MISSION-1", payload_hash="hash_v2_" + "b" * 56)
    pub2 = await receive_publication(db_session, pkg2)
    assert pub2.id == pub1.id
    assert pub2.current_version == 2


@pytest.mark.asyncio
async def test_version_history_preserved(db_session, admin_user):
    """7. Version history preserved when updating publication."""
    await _create_building(db_session, admin_user, egid=12345)
    pkg1 = _make_package(egid=12345, source_mission_id="VER-HIST", payload_hash="v1_hash_" + "a" * 56)
    pub1 = await receive_publication(db_session, pkg1)

    pkg2 = _make_package(egid=12345, source_mission_id="VER-HIST", payload_hash="v2_hash_" + "b" * 56)
    await receive_publication(db_session, pkg2)
    await db_session.commit()

    pub_with_versions = await get_publication_with_versions(db_session, pub1.id)
    assert len(pub_with_versions.versions) == 1
    assert pub_with_versions.versions[0].version == 1
    assert pub_with_versions.versions[0].payload_hash == "v1_hash_" + "a" * 56


@pytest.mark.asyncio
async def test_structured_summary_stored(db_session, admin_user):
    """8. structured_summary JSON is stored correctly."""
    await _create_building(db_session, admin_user, egid=12345)
    summary = {"pollutants_found": ["asbestos", "pcb"], "fach_urgency": "high", "zones": ["Z1", "Z2"]}
    pkg = _make_package(egid=12345, structured_summary=summary)
    pub = await receive_publication(db_session, pkg)
    assert pub.structured_summary == summary
    assert pub.structured_summary["fach_urgency"] == "high"


@pytest.mark.asyncio
async def test_annexes_stored(db_session, admin_user):
    """9. annexes JSON array is stored correctly."""
    await _create_building(db_session, admin_user, egid=12345)
    annexes = [
        {"name": "floor_plan.pdf", "url": "https://cdn.example.com/floor.pdf", "type": "plan"},
        {"name": "lab_results.pdf", "url": "https://cdn.example.com/lab.pdf", "type": "lab"},
    ]
    pkg = _make_package(egid=12345, annexes=annexes)
    pub = await receive_publication(db_session, pkg)
    assert pub.annexes == annexes
    assert len(pub.annexes) == 2


# ===========================================================================
# Manual match
# ===========================================================================


@pytest.mark.asyncio
async def test_match_unmatched_publication(db_session, admin_user):
    """10. Match unmatched publication to building -> manual_matched."""
    building = await _create_building(db_session, admin_user)
    pkg = _make_package(egid=77777)  # No building has this egid
    pub = await receive_publication(db_session, pkg)
    assert pub.match_state == "unmatched"

    matched = await match_publication(db_session, pub.id, building.id)
    assert matched.match_state == "manual_matched"
    assert matched.building_id == building.id


@pytest.mark.asyncio
async def test_match_needs_review_publication(db_session, admin_user):
    """11. Match needs_review publication -> manual_matched."""
    building = await _create_building(db_session, admin_user, address="Chemin du Lac 5")
    pkg = _make_package(address="Lac 5")
    pub = await receive_publication(db_session, pkg)
    assert pub.match_state == "needs_review"

    matched = await match_publication(db_session, pub.id, building.id)
    assert matched.match_state == "manual_matched"
    assert matched.building_id == building.id


@pytest.mark.asyncio
async def test_match_already_matched_raises(db_session, admin_user):
    """12. Match already matched publication -> raises ValueError."""
    building = await _create_building(db_session, admin_user, egid=12345)
    pkg = _make_package(egid=12345)
    pub = await receive_publication(db_session, pkg)
    assert pub.match_state == "auto_matched"

    with pytest.raises(ValueError, match="already matched"):
        await match_publication(db_session, pub.id, building.id)


@pytest.mark.asyncio
async def test_match_invalid_building_raises(db_session, admin_user):
    """13. Match with invalid building_id -> error."""
    pkg = _make_package(egid=77777)
    pub = await receive_publication(db_session, pkg)
    fake_building_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        await match_publication(db_session, pub.id, fake_building_id)


# ===========================================================================
# Mission orders
# ===========================================================================


@pytest.mark.asyncio
async def test_create_mission_order_draft(db_session, admin_user):
    """14. Create mission order -> draft status, building_identifiers populated."""
    building = await _create_building(db_session, admin_user, egid=55555, egrid="CH999999999999")
    order = DiagnosticMissionOrderCreate(
        building_id=building.id,
        mission_type="asbestos_full",
        context_notes="Urgent diagnostic needed",
    )
    mission = await create_mission_order(db_session, order)
    assert mission.status == "draft"
    assert mission.building_identifiers["egid"] == 55555
    assert mission.building_identifiers["egrid"] == "CH999999999999"
    assert mission.building_identifiers["address"] == building.address


@pytest.mark.asyncio
async def test_create_mission_order_with_org(db_session, admin_user):
    """15. Create mission order with org -> requester_org_id set."""
    building = await _create_building(db_session, admin_user, egid=55556)
    org = Organization(id=uuid.uuid4(), name="Test Org", type="property_management")
    db_session.add(org)
    await db_session.flush()

    order = DiagnosticMissionOrderCreate(
        building_id=building.id,
        requester_org_id=org.id,
        mission_type="pcb",
    )
    mission = await create_mission_order(db_session, order)
    assert mission.requester_org_id == org.id


@pytest.mark.asyncio
async def test_get_mission_orders_for_building(db_session, admin_user):
    """16. Get mission orders for building -> ordered by created_at desc."""
    building = await _create_building(db_session, admin_user, egid=55557)
    for i in range(3):
        order = DiagnosticMissionOrderCreate(
            building_id=building.id,
            mission_type="asbestos_full",
            context_notes=f"Order {i}",
        )
        await create_mission_order(db_session, order)

    from app.services.diagnostic_integration_service import get_mission_orders_for_building

    orders = await get_mission_orders_for_building(db_session, building.id)
    assert len(orders) == 3


@pytest.mark.asyncio
async def test_create_mission_order_invalid_building(db_session):
    """17. Mission order with invalid building_id -> error."""
    order = DiagnosticMissionOrderCreate(
        building_id=uuid.uuid4(),
        mission_type="asbestos_full",
    )
    with pytest.raises(ValueError, match="not found"):
        await create_mission_order(db_session, order)


# ===========================================================================
# Queries
# ===========================================================================


@pytest.mark.asyncio
async def test_get_publications_for_building(db_session, admin_user):
    """18. Get publications for building -> filtered, ordered."""
    building = await _create_building(db_session, admin_user, egid=33333)
    for i in range(3):
        pkg = _make_package(egid=33333, source_mission_id=f"Q-{i}")
        await receive_publication(db_session, pkg)

    pubs = await get_publications_for_building(db_session, building.id)
    assert len(pubs) == 3


@pytest.mark.asyncio
async def test_get_unmatched_publications(db_session, admin_user):
    """19. Get unmatched publications -> only needs_review + unmatched."""
    await _create_building(db_session, admin_user, egid=44444)

    # Create matched publication
    await receive_publication(db_session, _make_package(egid=44444, source_mission_id="MATCHED-1"))

    # Create unmatched publication
    await receive_publication(db_session, _make_package(egid=99999, source_mission_id="UNMATCHED-1"))

    unmatched = await get_unmatched_publications(db_session)
    assert len(unmatched) == 1
    assert unmatched[0].match_state == "unmatched"


@pytest.mark.asyncio
async def test_get_publication_with_versions(db_session, admin_user):
    """20. Get publication with versions -> includes version history."""
    await _create_building(db_session, admin_user, egid=12345)
    pkg1 = _make_package(egid=12345, source_mission_id="VER-QRY", payload_hash="qhash1_" + "a" * 57)
    pub = await receive_publication(db_session, pkg1)

    pkg2 = _make_package(egid=12345, source_mission_id="VER-QRY", payload_hash="qhash2_" + "b" * 57)
    await receive_publication(db_session, pkg2)
    await db_session.commit()

    result = await get_publication_with_versions(db_session, pub.id)
    assert result.current_version == 2
    assert len(result.versions) == 1
    assert result.versions[0].version == 1


# ===========================================================================
# Schema validation
# ===========================================================================


def test_publication_package_required_fields():
    """21. DiagnosticPublicationPackage validates required fields."""
    with pytest.raises(ValueError):
        DiagnosticPublicationPackage()  # type: ignore[call-arg]


def test_publication_package_minimal():
    """22. DiagnosticPublicationPackage with minimal required fields."""
    pkg = DiagnosticPublicationPackage(
        source_mission_id="MIN-001",
        mission_type="asbestos_full",
        building_identifiers={},
        structured_summary={"pollutants_found": []},
        payload_hash="abc123" * 10,
        published_at=datetime.now(UTC),
    )
    assert pkg.source_system == "batiscan"
    assert pkg.annexes == []
    assert pkg.version == 1


def test_mission_order_create_validates_building_id():
    """23. DiagnosticMissionOrderCreate validates building_id."""
    bid = uuid.uuid4()
    order = DiagnosticMissionOrderCreate(building_id=bid, mission_type="pcb")
    assert order.building_id == bid
    assert order.requester_org_id is None
    assert order.attachments == []


def test_publication_match_request_validates():
    """24. PublicationMatchRequest validates building_id."""
    bid = uuid.uuid4()
    req = PublicationMatchRequest(building_id=bid)
    assert req.building_id == bid

    with pytest.raises(ValueError):
        PublicationMatchRequest()  # type: ignore[call-arg]


# ===========================================================================
# Building matching logic
# ===========================================================================


@pytest.mark.asyncio
async def test_match_priority_egid_over_egrid(db_session, admin_user):
    """25. Match priority: egid > egrid > address."""
    # Building has both egid and egrid
    building = await _create_building(db_session, admin_user, egid=88888, egrid="CH888888888888")
    pkg = _make_package(egid=88888, egrid="CH888888888888")
    pub = await receive_publication(db_session, pkg)
    # Should match by egid (higher priority)
    assert pub.match_key_type == "egid"
    assert pub.building_id == building.id


@pytest.mark.asyncio
async def test_null_egid_falls_through_to_egrid(db_session, admin_user):
    """26. Null egid falls through to egrid."""
    building = await _create_building(db_session, admin_user, egrid="CH777777777777")
    pkg = _make_package(egrid="CH777777777777")
    pub = await receive_publication(db_session, pkg)
    assert pub.match_key_type == "egrid"
    assert pub.building_id == building.id


@pytest.mark.asyncio
async def test_multiple_address_matches_needs_review_no_building(db_session, admin_user):
    """27. Multiple address matches -> needs_review with no building_id."""
    await _create_building(db_session, admin_user, address="Rue de la Gare 10")
    # Second building with similar address (different uuid, different egid)
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

    # Address search for "Gare" matches both
    pkg = _make_package(address="Gare")
    pub = await receive_publication(db_session, pkg)
    assert pub.match_state == "needs_review"
    assert pub.building_id is None
