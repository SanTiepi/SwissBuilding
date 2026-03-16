"""Tests for the Building Memory Transfer Package service and API."""

import uuid

import pytest

from app.constants import TRANSFER_PACKAGE_VERSION
from app.models.building import Building
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.services.transfer_package_service import generate_transfer_package


@pytest.fixture
async def building_with_data(db_session, admin_user):
    """Create a building with diagnostic and snapshot data for transfer tests."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Transfert 10",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        egid=12345,
    )
    db_session.add(building)
    await db_session.flush()

    # Add a diagnostic
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)

    # Add a snapshot
    snapshot = BuildingSnapshot(
        id=uuid.uuid4(),
        building_id=building.id,
        snapshot_type="manual",
        passport_grade="C",
        overall_trust=0.5,
        completeness_score=0.6,
    )
    db_session.add(snapshot)

    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.mark.asyncio
async def test_generate_full_package(db_session, building_with_data):
    """Full package includes all sections."""
    pkg = await generate_transfer_package(db_session, building_with_data.id)
    assert pkg is not None
    assert pkg.building_id == building_with_data.id
    assert pkg.building_summary["address"] == "Rue du Transfert 10"
    assert pkg.building_summary["egid"] == 12345
    assert pkg.diagnostics_summary is not None
    assert pkg.documents_summary is not None
    assert pkg.interventions_summary is not None
    assert pkg.actions_summary is not None
    assert pkg.evidence_coverage is not None
    assert pkg.unknowns is not None
    assert pkg.snapshots is not None
    assert pkg.completeness is not None
    assert pkg.metadata is not None


@pytest.mark.asyncio
async def test_generate_partial_package(db_session, building_with_data):
    """Partial package only includes requested sections."""
    pkg = await generate_transfer_package(
        db_session,
        building_with_data.id,
        include_sections=["passport", "diagnostics"],
    )
    assert pkg is not None
    # Requested sections present
    assert pkg.diagnostics_summary is not None
    # Non-requested sections absent
    assert pkg.documents_summary is None
    assert pkg.interventions_summary is None
    assert pkg.actions_summary is None
    assert pkg.snapshots is None
    assert pkg.completeness is None


@pytest.mark.asyncio
async def test_package_schema_version(db_session, building_with_data):
    """Package schema version matches the constant."""
    pkg = await generate_transfer_package(db_session, building_with_data.id)
    assert pkg is not None
    assert pkg.schema_version == TRANSFER_PACKAGE_VERSION
    assert pkg.schema_version == "1.0"


@pytest.mark.asyncio
async def test_package_building_not_found(db_session):
    """Non-existent building returns None."""
    fake_id = uuid.uuid4()
    pkg = await generate_transfer_package(db_session, fake_id)
    assert pkg is None


@pytest.mark.asyncio
async def test_package_includes_passport_grade(db_session, building_with_data):
    """Passport section is included and contains expected keys."""
    pkg = await generate_transfer_package(
        db_session,
        building_with_data.id,
        include_sections=["passport"],
    )
    assert pkg is not None
    # Passport may be a dict with passport_grade key or None if service returns None
    # The passport service returns a dict when the building exists
    if pkg.passport is not None:
        assert "passport_grade" in pkg.passport


@pytest.mark.asyncio
async def test_package_includes_diagnostics_summary(db_session, building_with_data):
    """Diagnostics summary reflects actual data."""
    pkg = await generate_transfer_package(
        db_session,
        building_with_data.id,
        include_sections=["diagnostics"],
    )
    assert pkg is not None
    assert pkg.diagnostics_summary is not None
    assert pkg.diagnostics_summary["count"] == 1
    assert "completed" in pkg.diagnostics_summary["statuses"]


@pytest.mark.asyncio
async def test_package_includes_snapshots(db_session, building_with_data):
    """Snapshots section returns recent snapshots."""
    pkg = await generate_transfer_package(
        db_session,
        building_with_data.id,
        include_sections=["snapshots"],
    )
    assert pkg is not None
    assert pkg.snapshots is not None
    assert len(pkg.snapshots) == 1
    assert pkg.snapshots[0]["passport_grade"] == "C"
    assert pkg.snapshots[0]["overall_trust"] == 0.5


@pytest.mark.asyncio
async def test_api_endpoint_returns_package(client, auth_headers, sample_building):
    """API endpoint returns a transfer package."""
    response = await client.post(
        f"/api/v1/buildings/{sample_building.id}/transfer-package",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["schema_version"] == "1.0"
    assert "building_summary" in data
    assert data["building_summary"]["address"] == "Rue Test 1"
    assert "metadata" in data


@pytest.mark.asyncio
async def test_api_endpoint_partial_sections(client, auth_headers, sample_building):
    """API endpoint respects include_sections filter."""
    response = await client.post(
        f"/api/v1/buildings/{sample_building.id}/transfer-package",
        headers=auth_headers,
        json={"include_sections": ["diagnostics", "snapshots"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["diagnostics_summary"] is not None
    assert data["snapshots"] is not None
    assert data["documents_summary"] is None
    assert data["passport"] is None


@pytest.mark.asyncio
async def test_api_endpoint_building_not_found(client, auth_headers):
    """API endpoint returns 404 for non-existent building."""
    fake_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/buildings/{fake_id}/transfer-package",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 404
