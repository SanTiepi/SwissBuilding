"""Tests for the passport exchange schema and export endpoint."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.user import User
from app.services.passport_exchange_service import export_passport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def exchange_building(db_session: AsyncSession, admin_user: User) -> Building:
    """Building with diagnostics, samples, and interventions for exchange tests."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Exchange 7",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        egid=55555,
        construction_year=1972,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="asbestos",
        status="completed",
        date_report=date.today() - timedelta(days=60),
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="EX001",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)

    interv = Intervention(
        id=uuid.uuid4(),
        building_id=b.id,
        intervention_type="encapsulation",
        title="Asbestos encapsulation",
        status="planned",
    )
    db_session.add(interv)

    await db_session.commit()
    await db_session.refresh(b)
    return b


# ---------------------------------------------------------------------------
# Service: export_passport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_passport_returns_valid_document(db_session: AsyncSession, exchange_building: Building):
    doc = await export_passport(db_session, exchange_building.id)
    assert doc is not None
    assert doc.building_id == exchange_building.id
    assert doc.address == "Rue Exchange 7"
    assert doc.city == "Lausanne"
    assert doc.canton == "VD"
    assert doc.construction_year == 1972
    assert doc.passport_grade is not None
    assert doc.knowledge_state is not None
    assert doc.readiness is not None
    assert doc.completeness is not None
    assert doc.blind_spots is not None
    assert doc.contradictions is not None
    assert doc.evidence_coverage is not None


@pytest.mark.asyncio
async def test_export_passport_schema_version(db_session: AsyncSession, exchange_building: Building):
    doc = await export_passport(db_session, exchange_building.id)
    assert doc is not None
    assert doc.metadata.schema_version == "1.0.0"
    assert doc.metadata.source_system == "SwissBuildingOS"
    assert doc.metadata.exported_at is not None


@pytest.mark.asyncio
async def test_export_passport_not_found(db_session: AsyncSession):
    result = await export_passport(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_export_passport_with_transfer(db_session: AsyncSession, exchange_building: Building):
    doc = await export_passport(db_session, exchange_building.id, include_transfer=True)
    assert doc is not None
    assert doc.diagnostics_summary is not None
    assert doc.interventions_summary is not None
    assert doc.actions_summary is not None


@pytest.mark.asyncio
async def test_export_passport_without_transfer(db_session: AsyncSession, exchange_building: Building):
    doc = await export_passport(db_session, exchange_building.id, include_transfer=False)
    assert doc is not None
    assert doc.diagnostics_summary is None
    assert doc.interventions_summary is None
    assert doc.actions_summary is None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_passport_exchange_200(client: AsyncClient, auth_headers: dict, sample_building: Building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/passport/export",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["schema_version"] == "1.0.0"
    assert data["metadata"]["source_system"] == "SwissBuildingOS"
    assert data["building_id"] == str(sample_building.id)
    assert "passport_grade" in data


@pytest.mark.asyncio
async def test_api_passport_exchange_404(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/passport/export",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_passport_exchange_with_format(client: AsyncClient, auth_headers: dict, sample_building: Building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/passport/export",
        params={"format": "json"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_passport_exchange_include_transfer(
    client: AsyncClient, auth_headers: dict, sample_building: Building
):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/passport/export",
        params={"include_transfer": "true"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Transfer sections should be present (may be empty dicts or have content)
    assert "diagnostics_summary" in data
    assert "interventions_summary" in data
    assert "actions_summary" in data


@pytest.mark.asyncio
async def test_api_passport_exchange_unauthenticated(client: AsyncClient, sample_building: Building):
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/passport/export",
    )
    assert resp.status_code == 401
