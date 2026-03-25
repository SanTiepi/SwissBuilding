"""
SwissBuildingOS - Risk Communication Tests

Tests for the risk communication service and API endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.risk_communication_service import (
    _communication_log,
    generate_occupant_notice,
    generate_stakeholder_notification,
    generate_worker_safety_briefing,
    get_communication_log,
)


@pytest.fixture
async def building_with_samples(db_session, admin_user):
    """Building with diagnostics and positive asbestos + lead samples."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Risque 42",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="avant_travaux",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    samples = [
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="E-001",
            location_floor="2eme etage",
            location_room="Salon",
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="medium",
            material_category="dalles de sol",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="E-002",
            location_floor="1er etage",
            location_room="Cuisine",
            pollutant_type="lead",
            concentration=8000.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            material_category="peinture",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="E-003",
            location_floor="2eme etage",
            location_room="Chambre",
            pollutant_type="pcb",
            concentration=10.0,
            unit="mg_per_kg",
            threshold_exceeded=False,
            risk_level="low",
        ),
    ]
    for s in samples:
        db_session.add(s)
    await db_session.commit()
    await db_session.refresh(building)

    return building


@pytest.fixture
async def building_no_samples(db_session, admin_user):
    """Building without diagnostics or samples."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Propre 10",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        construction_year=2010,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture(autouse=True)
def clear_communication_log():
    """Clear communication log before each test."""
    _communication_log.clear()
    yield
    _communication_log.clear()


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestGenerateOccupantNotice:
    async def test_notice_with_pollutants(self, db_session, building_with_samples):
        result = await generate_occupant_notice(db_session, building_with_samples.id)
        assert result.building_id == building_with_samples.id
        assert result.overall_risk_level == "high"
        assert "amiante" in result.situation
        assert "plomb" in result.situation
        assert len(result.sections) == 5
        assert len(result.precautions) > 0
        assert any("amiante" in p for p in result.precautions)

    async def test_notice_without_pollutants(self, db_session, building_no_samples):
        result = await generate_occupant_notice(db_session, building_no_samples.id)
        assert result.building_id == building_no_samples.id
        assert result.overall_risk_level == "unknown"
        assert "Aucune substance" in result.situation
        assert "Aucune precaution" in result.precautions[0]

    async def test_notice_nonexistent_building(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await generate_occupant_notice(db_session, uuid.uuid4())

    async def test_notice_records_communication(self, db_session, building_with_samples):
        await generate_occupant_notice(db_session, building_with_samples.id)
        key = str(building_with_samples.id)
        assert len(_communication_log[key]) == 1
        assert _communication_log[key][0]["communication_type"] == "occupant_notice"


class TestGenerateWorkerSafetyBriefing:
    async def test_briefing_with_pollutants(self, db_session, building_with_samples):
        result = await generate_worker_safety_briefing(db_session, building_with_samples.id)
        assert result.building_id == building_with_samples.id
        assert result.cfst_reference == "CFST 6503"
        assert result.overall_work_category == "medium"
        assert len(result.zones) >= 1
        assert len(result.emergency_procedures) > 0
        assert len(result.decontamination_steps) == 7
        assert len(result.general_ppe) > 0

    async def test_briefing_without_pollutants(self, db_session, building_no_samples):
        result = await generate_worker_safety_briefing(db_session, building_no_samples.id)
        assert result.overall_work_category == "minor"
        assert len(result.zones) == 1
        assert result.zones[0].zone == "Batiment entier"

    async def test_briefing_ppe_escalation(self, db_session, building_with_samples):
        result = await generate_worker_safety_briefing(db_session, building_with_samples.id)
        # Medium category should have more PPE than minor
        assert len(result.general_ppe) >= 4

    async def test_briefing_nonexistent_building(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await generate_worker_safety_briefing(db_session, uuid.uuid4())


class TestGenerateStakeholderNotification:
    async def test_owner_notification(self, db_session, building_with_samples):
        result = await generate_stakeholder_notification(db_session, building_with_samples.id, "owner")
        assert result.audience == "owner"
        assert result.detail_level == "detailed"
        assert "proprietaire" in result.implications[0].lower()
        assert len(result.required_actions) >= 1
        assert result.timeline is not None

    async def test_tenant_notification(self, db_session, building_with_samples):
        result = await generate_stakeholder_notification(db_session, building_with_samples.id, "tenant")
        assert result.audience == "tenant"
        assert result.detail_level == "brief"
        assert len(result.implications) >= 1

    async def test_authority_notification(self, db_session, building_with_samples):
        result = await generate_stakeholder_notification(db_session, building_with_samples.id, "authority")
        assert result.audience == "authority"
        assert result.detail_level == "detailed"
        assert any("SUVA" in i for i in result.implications)

    async def test_insurer_notification(self, db_session, building_with_samples):
        result = await generate_stakeholder_notification(db_session, building_with_samples.id, "insurer")
        assert result.audience == "insurer"
        assert result.detail_level == "standard"

    async def test_invalid_audience(self, db_session, building_with_samples):
        with pytest.raises(ValueError, match="Invalid audience"):
            await generate_stakeholder_notification(db_session, building_with_samples.id, "hacker")

    async def test_notification_no_pollutants(self, db_session, building_no_samples):
        result = await generate_stakeholder_notification(db_session, building_no_samples.id, "owner")
        assert "Aucun polluant" in result.summary

    async def test_notification_nonexistent_building(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await generate_stakeholder_notification(db_session, uuid.uuid4(), "owner")


class TestGetCommunicationLog:
    async def test_empty_log(self, db_session, building_no_samples):
        result = await get_communication_log(db_session, building_no_samples.id)
        assert result.total_count == 0
        assert result.entries == []

    async def test_log_after_multiple_communications(self, db_session, building_with_samples):
        await generate_occupant_notice(db_session, building_with_samples.id)
        await generate_worker_safety_briefing(db_session, building_with_samples.id)
        await generate_stakeholder_notification(db_session, building_with_samples.id, "owner")

        result = await get_communication_log(db_session, building_with_samples.id)
        assert result.total_count == 3
        types = [e.communication_type for e in result.entries]
        assert "occupant_notice" in types
        assert "worker_safety_briefing" in types
        assert "stakeholder_notification" in types

    async def test_log_nonexistent_building(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_communication_log(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


class TestRiskCommunicationAPI:
    async def test_occupant_notice_endpoint(self, client: AsyncClient, auth_headers, building_with_samples):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/risk-communication/occupant-notice",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_risk_level"] == "high"
        assert len(data["sections"]) == 5

    async def test_worker_briefing_endpoint(self, client: AsyncClient, auth_headers, building_with_samples):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/risk-communication/worker-briefing",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cfst_reference"] == "CFST 6503"
        assert data["overall_work_category"] == "medium"

    async def test_stakeholder_notification_endpoint(self, client: AsyncClient, auth_headers, building_with_samples):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/risk-communication/stakeholder-notification",
            params={"audience": "owner"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["audience"] == "owner"
        assert data["detail_level"] == "detailed"

    async def test_stakeholder_invalid_audience_endpoint(
        self, client: AsyncClient, auth_headers, building_with_samples
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/risk-communication/stakeholder-notification",
            params={"audience": "invalid"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_communication_log_endpoint(self, client: AsyncClient, auth_headers, building_with_samples):
        # Generate some communications first
        await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/risk-communication/occupant-notice",
            headers=auth_headers,
        )
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/risk-communication/log",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] >= 1

    async def test_404_nonexistent_building(self, client: AsyncClient, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/risk-communication/occupant-notice",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_401_no_auth(self, client: AsyncClient, building_with_samples):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_samples.id}/risk-communication/occupant-notice",
        )
        assert resp.status_code == 401
