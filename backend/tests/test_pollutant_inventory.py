"""Tests for pollutant inventory service and API endpoints."""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.pollutant_inventory_service import (
    get_building_pollutant_inventory,
    get_pollutant_hotspots,
    get_pollutant_summary,
    get_portfolio_pollutant_overview,
)

# ── Helpers ──────────────────────────────────────────────────────────


async def _create_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="diagnostic_lab",
    )
    db.add(org)
    await db.flush()
    return org


async def _create_user_in_org(db: AsyncSession, org: Organization) -> User:
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_building(db: AsyncSession, user: User) -> Building:
    b = Building(
        id=uuid.uuid4(),
        address=f"Rue Test {uuid.uuid4().hex[:4]}",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(
    db: AsyncSession,
    building: Building,
    user: User,
    *,
    diag_type: str = "asbestos",
    status: str = "completed",
    date_report: date | None = None,
) -> Diagnostic:
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type=diag_type,
        status=status,
        diagnostician_id=user.id,
        date_report=date_report,
    )
    db.add(d)
    await db.flush()
    return d


async def _create_sample(
    db: AsyncSession,
    diagnostic: Diagnostic,
    *,
    pollutant_type: str | None = "asbestos",
    concentration: float | None = 1.5,
    unit: str | None = "%",
    threshold_exceeded: bool = False,
    risk_level: str | None = "medium",
    location_floor: str | None = "1er",
    location_room: str | None = "Cuisine",
    location_detail: str | None = None,
    material_category: str | None = "Flocage",
    sample_number: str | None = None,
) -> Sample:
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number=sample_number or f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit=unit,
        threshold_exceeded=threshold_exceeded,
        risk_level=risk_level,
        location_floor=location_floor,
        location_room=location_room,
        location_detail=location_detail,
        material_category=material_category,
    )
    db.add(s)
    await db.flush()
    return s


# ── get_building_pollutant_inventory ─────────────────────────────────


@pytest.mark.asyncio
async def test_inventory_empty_building(db_session, admin_user, sample_building):
    """Building with no diagnostics returns empty inventory."""
    result = await get_building_pollutant_inventory(db_session, sample_building.id)
    assert result.total_findings == 0
    assert result.items == []
    assert result.pollutant_types_found == []


@pytest.mark.asyncio
async def test_inventory_single_sample(db_session, admin_user, sample_building):
    """Single sample is correctly returned in inventory."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(db_session, diag, pollutant_type="asbestos", threshold_exceeded=True)
    await db_session.commit()

    result = await get_building_pollutant_inventory(db_session, sample_building.id)
    assert result.total_findings == 1
    assert result.pollutant_types_found == ["asbestos"]
    assert result.items[0].status == "confirmed"


@pytest.mark.asyncio
async def test_inventory_multiple_pollutants(db_session, admin_user, sample_building):
    """Multiple pollutant types across diagnostics are aggregated."""
    diag1 = await _create_diagnostic(db_session, sample_building, admin_user, diag_type="asbestos")
    diag2 = await _create_diagnostic(db_session, sample_building, admin_user, diag_type="pcb")
    await _create_sample(db_session, diag1, pollutant_type="asbestos")
    await _create_sample(db_session, diag2, pollutant_type="pcb")
    await _create_sample(db_session, diag2, pollutant_type="lead")
    await db_session.commit()

    result = await get_building_pollutant_inventory(db_session, sample_building.id)
    assert result.total_findings == 3
    assert sorted(result.pollutant_types_found) == ["asbestos", "lead", "pcb"]


@pytest.mark.asyncio
async def test_inventory_status_suspected(db_session, admin_user, sample_building):
    """Sample with concentration > 0 but not exceeding threshold is suspected."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(db_session, diag, pollutant_type="pcb", concentration=30.0, threshold_exceeded=False)
    await db_session.commit()

    result = await get_building_pollutant_inventory(db_session, sample_building.id)
    assert result.items[0].status == "suspected"


@pytest.mark.asyncio
async def test_inventory_status_cleared(db_session, admin_user, sample_building):
    """Sample with no pollutant_type is cleared."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(db_session, diag, pollutant_type=None, concentration=None)
    await db_session.commit()

    result = await get_building_pollutant_inventory(db_session, sample_building.id)
    assert result.items[0].status == "cleared"


@pytest.mark.asyncio
async def test_inventory_nonexistent_building(db_session):
    """Nonexistent building returns empty inventory (not an error)."""
    fake_id = uuid.uuid4()
    result = await get_building_pollutant_inventory(db_session, fake_id)
    assert result.total_findings == 0
    assert result.building_id == fake_id


# ── get_pollutant_summary ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_empty(db_session, admin_user, sample_building):
    """Empty building returns no summaries."""
    result = await get_pollutant_summary(db_session, sample_building.id)
    assert result.total_pollutant_types == 0
    assert result.summaries == []


@pytest.mark.asyncio
async def test_summary_single_type(db_session, admin_user, sample_building):
    """Summary correctly aggregates a single pollutant type."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user, date_report=date(2025, 6, 1))
    await _create_sample(db_session, diag, pollutant_type="asbestos", threshold_exceeded=True, risk_level="high")
    await _create_sample(
        db_session,
        diag,
        pollutant_type="asbestos",
        threshold_exceeded=False,
        risk_level="medium",
        location_room="Salon",
    )
    await db_session.commit()

    result = await get_pollutant_summary(db_session, sample_building.id)
    assert result.total_pollutant_types == 1
    s = result.summaries[0]
    assert s.pollutant_type == "asbestos"
    assert s.count == 2
    assert s.confirmed_count == 1
    assert s.suspected_count == 1
    assert s.worst_risk_level == "high"
    assert s.latest_diagnostic_date == date(2025, 6, 1)
    assert len(s.zones_affected) == 2  # Cuisine, Salon


@pytest.mark.asyncio
async def test_summary_multiple_types(db_session, admin_user, sample_building):
    """Summary groups by pollutant type correctly."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(db_session, diag, pollutant_type="asbestos")
    await _create_sample(db_session, diag, pollutant_type="lead")
    await _create_sample(db_session, diag, pollutant_type="lead")
    await db_session.commit()

    result = await get_pollutant_summary(db_session, sample_building.id)
    assert result.total_pollutant_types == 2
    types = {s.pollutant_type: s.count for s in result.summaries}
    assert types["asbestos"] == 1
    assert types["lead"] == 2


@pytest.mark.asyncio
async def test_summary_worst_risk_critical(db_session, admin_user, sample_building):
    """Worst risk level is correctly identified as critical."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(db_session, diag, pollutant_type="asbestos", risk_level="low")
    await _create_sample(db_session, diag, pollutant_type="asbestos", risk_level="critical")
    await db_session.commit()

    result = await get_pollutant_summary(db_session, sample_building.id)
    assert result.summaries[0].worst_risk_level == "critical"


@pytest.mark.asyncio
async def test_summary_max_concentration(db_session, admin_user, sample_building):
    """Max concentration is correctly reported."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(db_session, diag, pollutant_type="pcb", concentration=10.0)
    await _create_sample(db_session, diag, pollutant_type="pcb", concentration=500.0)
    await db_session.commit()

    result = await get_pollutant_summary(db_session, sample_building.id)
    assert result.summaries[0].max_concentration == 500.0


# ── get_portfolio_pollutant_overview ─────────────────────────────────


@pytest.mark.asyncio
async def test_portfolio_empty_org(db_session):
    """Org with no buildings returns empty overview."""
    org = await _create_org(db_session)
    await db_session.commit()

    result = await get_portfolio_pollutant_overview(db_session, org.id)
    assert result.total_buildings == 0
    assert result.buildings_with_pollutants == 0


@pytest.mark.asyncio
async def test_portfolio_buildings_no_pollutants(db_session):
    """Buildings without pollutant samples show zero findings."""
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    await _create_building(db_session, user)
    await db_session.commit()

    result = await get_portfolio_pollutant_overview(db_session, org.id)
    assert result.total_buildings == 1
    assert result.buildings_with_pollutants == 0


@pytest.mark.asyncio
async def test_portfolio_with_pollutants(db_session):
    """Portfolio correctly counts buildings with pollutants."""
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    b1 = await _create_building(db_session, user)
    b2 = await _create_building(db_session, user)
    diag1 = await _create_diagnostic(db_session, b1, user)
    await _create_sample(db_session, diag1, pollutant_type="asbestos", threshold_exceeded=True)
    # b2 has no samples
    await _create_diagnostic(db_session, b2, user)
    await db_session.commit()

    result = await get_portfolio_pollutant_overview(db_session, org.id)
    assert result.total_buildings == 2
    assert result.buildings_with_pollutants == 1
    assert result.pollutant_distribution["asbestos"] == 1


@pytest.mark.asyncio
async def test_portfolio_risk_distribution(db_session):
    """Risk distribution aggregates across buildings."""
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    b1 = await _create_building(db_session, user)
    b2 = await _create_building(db_session, user)
    diag1 = await _create_diagnostic(db_session, b1, user)
    diag2 = await _create_diagnostic(db_session, b2, user)
    await _create_sample(db_session, diag1, pollutant_type="asbestos", risk_level="high")
    await _create_sample(db_session, diag2, pollutant_type="pcb", risk_level="high")
    await _create_sample(db_session, diag2, pollutant_type="lead", risk_level="low")
    await db_session.commit()

    result = await get_portfolio_pollutant_overview(db_session, org.id)
    assert result.risk_distribution["high"] == 2
    assert result.risk_distribution["low"] == 1


@pytest.mark.asyncio
async def test_portfolio_building_stats_worst_risk(db_session):
    """Per-building stats show worst risk level."""
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    b = await _create_building(db_session, user)
    diag = await _create_diagnostic(db_session, b, user)
    await _create_sample(db_session, diag, pollutant_type="asbestos", risk_level="low")
    await _create_sample(db_session, diag, pollutant_type="pcb", risk_level="critical")
    await db_session.commit()

    result = await get_portfolio_pollutant_overview(db_session, org.id)
    stats = result.buildings[0]
    assert stats.worst_risk_level == "critical"
    assert sorted(stats.pollutant_types) == ["asbestos", "pcb"]


# ── get_pollutant_hotspots ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_hotspots_empty(db_session, admin_user, sample_building):
    """Building with no samples returns no hotspots."""
    result = await get_pollutant_hotspots(db_session, sample_building.id)
    assert result.hotspots == []


@pytest.mark.asyncio
async def test_hotspots_single_location(db_session, admin_user, sample_building):
    """Single location with one sample creates one hotspot."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(db_session, diag, pollutant_type="asbestos", risk_level="high", concentration=5.0)
    await db_session.commit()

    result = await get_pollutant_hotspots(db_session, sample_building.id)
    assert len(result.hotspots) == 1
    h = result.hotspots[0]
    assert h.pollutant_types == ["asbestos"]
    assert h.worst_risk_level == "high"
    assert h.max_concentration == 5.0


@pytest.mark.asyncio
async def test_hotspots_multi_pollutant_location(db_session, admin_user, sample_building):
    """Location with multiple pollutants gets higher risk score."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(
        db_session,
        diag,
        pollutant_type="asbestos",
        risk_level="high",
        location_floor="1er",
        location_room="Cuisine",
    )
    await _create_sample(
        db_session,
        diag,
        pollutant_type="pcb",
        risk_level="medium",
        location_floor="1er",
        location_room="Cuisine",
    )
    await db_session.commit()

    result = await get_pollutant_hotspots(db_session, sample_building.id)
    assert len(result.hotspots) == 1
    h = result.hotspots[0]
    assert h.pollutant_count == 2
    assert sorted(h.pollutant_types) == ["asbestos", "pcb"]
    assert h.findings_count == 2


@pytest.mark.asyncio
async def test_hotspots_ranked_by_risk_score(db_session, admin_user, sample_building):
    """Hotspots are ranked by risk score descending."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    # Low risk location
    await _create_sample(
        db_session,
        diag,
        pollutant_type="lead",
        risk_level="low",
        location_floor="RDC",
        location_room="Hall",
    )
    # High risk multi-pollutant location
    await _create_sample(
        db_session,
        diag,
        pollutant_type="asbestos",
        risk_level="critical",
        location_floor="2e",
        location_room="Chaufferie",
    )
    await _create_sample(
        db_session,
        diag,
        pollutant_type="pcb",
        risk_level="high",
        location_floor="2e",
        location_room="Chaufferie",
    )
    await db_session.commit()

    result = await get_pollutant_hotspots(db_session, sample_building.id)
    assert len(result.hotspots) == 2
    assert result.hotspots[0].location_key == "2e / Chaufferie"
    assert result.hotspots[0].risk_score > result.hotspots[1].risk_score


@pytest.mark.asyncio
async def test_hotspots_excludes_cleared(db_session, admin_user, sample_building):
    """Cleared samples (pollutant_type=None) are not included in hotspots."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(db_session, diag, pollutant_type=None)
    await db_session.commit()

    result = await get_pollutant_hotspots(db_session, sample_building.id)
    assert result.hotspots == []


@pytest.mark.asyncio
async def test_hotspots_concentration_factor(db_session, admin_user, sample_building):
    """High concentration increases risk score."""
    diag = await _create_diagnostic(db_session, sample_building, admin_user)
    await _create_sample(
        db_session,
        diag,
        pollutant_type="pcb",
        risk_level="medium",
        concentration=5000.0,
        location_floor="1er",
        location_room="Bureau",
    )
    await _create_sample(
        db_session,
        diag,
        pollutant_type="pcb",
        risk_level="medium",
        concentration=1.0,
        location_floor="2e",
        location_room="Archive",
    )
    await db_session.commit()

    result = await get_pollutant_hotspots(db_session, sample_building.id)
    assert len(result.hotspots) == 2
    # Bureau has higher concentration so higher score
    bureau = next(h for h in result.hotspots if "Bureau" in h.location_key)
    archive = next(h for h in result.hotspots if "Archive" in h.location_key)
    assert bureau.risk_score > archive.risk_score


# ── API endpoint tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_pollutant_inventory(client, admin_user, sample_building, auth_headers):
    """GET /buildings/{id}/pollutant-inventory returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/pollutant-inventory",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["total_findings"] == 0


@pytest.mark.asyncio
async def test_api_pollutant_summary(client, admin_user, sample_building, auth_headers):
    """GET /buildings/{id}/pollutant-summary returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/pollutant-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_pollutant_hotspots(client, admin_user, sample_building, auth_headers):
    """GET /buildings/{id}/pollutant-hotspots returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/pollutant-hotspots",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["hotspots"] == []


@pytest.mark.asyncio
async def test_api_unauthenticated(client, sample_building):
    """Endpoints require authentication."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/pollutant-inventory",
    )
    assert resp.status_code in (401, 403)
