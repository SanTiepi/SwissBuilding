"""Tests for permit tracking service and API."""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.services.permit_tracking_service import (
    _determine_required_permits,
    get_permit_dependencies,
    get_portfolio_permit_overview,
    get_required_permits,
    track_permit_status,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
async def building_with_asbestos(db_session, admin_user):
    """Building with asbestos samples and an intervention."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue de l'Amiante 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        concentration=None,
        unit=None,
        location_floor="1er",
    )
    db_session.add(s1)

    interv = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="remediation",
        title="Désamiantage prévu",
        status="planned",
        description="Désamiantage",
        date_start=date(2026, 6, 1),
    )
    db_session.add(interv)
    await db_session.commit()
    return building


@pytest.fixture
async def building_with_pcb(db_session, admin_user):
    """Building with PCB > 50 mg/kg."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue du PCB 12",
        postal_code="1200",
        city="Genève",
        canton="GE",
        construction_year=1970,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="pcb",
        concentration=120.0,
        unit="mg/kg",
    )
    db_session.add(s1)
    await db_session.commit()
    return building


@pytest.fixture
async def clean_building(db_session, admin_user):
    """Building with no pollutants and no interventions."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Propre 1",
        postal_code="3000",
        city="Bern",
        canton="BE",
        construction_year=2020,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    return building


@pytest.fixture
async def building_with_suva_notification(db_session, admin_user):
    """Building with asbestos and SUVA notification date set."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Notifiée 8",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1955,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="full",
        status="completed",
        suva_notification_required=True,
        suva_notification_date=date(2026, 1, 15),
    )
    db_session.add(diag)
    await db_session.flush()

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        concentration=None,
        unit=None,
    )
    db_session.add(s1)

    interv = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type="remediation",
        title="Désamiantage notifié",
        status="planned",
        description="Désamiantage",
    )
    db_session.add(interv)
    await db_session.commit()
    return building


@pytest.fixture
async def org_with_buildings(db_session, admin_user):
    """Organization with buildings for portfolio test."""
    org = Organization(
        id=uuid.uuid4(),
        name="Régie Test SA",
        type="property_management",
    )
    db_session.add(org)
    await db_session.flush()

    # Attach admin_user to org
    admin_user.organization_id = org.id
    await db_session.flush()

    # Building 1: with asbestos
    b1 = Building(
        id=uuid.uuid4(),
        address="Rue Portfolio 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b1)
    await db_session.flush()

    diag1 = Diagnostic(
        id=uuid.uuid4(),
        building_id=b1.id,
        diagnostic_type="full",
        status="completed",
    )
    db_session.add(diag1)
    await db_session.flush()

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag1.id,
        sample_number="S001",
        pollutant_type="asbestos",
    )
    db_session.add(s1)

    interv1 = Intervention(
        id=uuid.uuid4(),
        building_id=b1.id,
        intervention_type="remediation",
        title="Désamiantage portfolio",
        status="planned",
        description="Désamiantage",
    )
    db_session.add(interv1)

    # Building 2: clean
    b2 = Building(
        id=uuid.uuid4(),
        address="Rue Portfolio 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2020,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b2)
    await db_session.commit()
    return org, b1, b2


# ── Unit tests: _determine_required_permits ───────────────────────────


class TestDetermineRequiredPermits:
    def test_asbestos_triggers_suva_and_pollutant_and_waste(self):
        """Asbestos samples should trigger SUVA, cantonal pollutant, and waste permits."""
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="S001",
            pollutant_type="asbestos",
        )
        building = Building(
            id=uuid.uuid4(),
            address="Test",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=uuid.uuid4(),
        )
        permits = _determine_required_permits([sample], True, building)
        types = {p.permit_type for p in permits}
        assert "suva_work_authorization" in types
        assert "cantonal_pollutant_handling" in types
        assert "waste_transport_permit" in types

    def test_pcb_above_threshold_triggers_pollutant_and_waste(self):
        """PCB > 50 mg/kg should trigger cantonal and waste permits."""
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="S001",
            pollutant_type="pcb",
            concentration=80.0,
            unit="mg/kg",
        )
        building = Building(
            id=uuid.uuid4(),
            address="Test",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=uuid.uuid4(),
        )
        permits = _determine_required_permits([sample], False, building)
        types = {p.permit_type for p in permits}
        assert "cantonal_pollutant_handling" in types
        assert "waste_transport_permit" in types
        assert "suva_work_authorization" not in types

    def test_pcb_below_threshold_no_special_permits(self):
        """PCB <= 50 mg/kg should not trigger special permits."""
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="S001",
            pollutant_type="pcb",
            concentration=30.0,
            unit="mg/kg",
        )
        building = Building(
            id=uuid.uuid4(),
            address="Test",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=uuid.uuid4(),
        )
        permits = _determine_required_permits([sample], False, building)
        types = {p.permit_type for p in permits}
        assert "cantonal_pollutant_handling" not in types
        assert "waste_transport_permit" not in types

    def test_lead_above_threshold(self):
        """Lead > 5000 mg/kg triggers special permits."""
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="S001",
            pollutant_type="lead",
            concentration=6000.0,
            unit="mg/kg",
        )
        building = Building(
            id=uuid.uuid4(),
            address="Test",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=uuid.uuid4(),
        )
        permits = _determine_required_permits([sample], False, building)
        types = {p.permit_type for p in permits}
        assert "cantonal_pollutant_handling" in types
        assert "waste_transport_permit" in types

    def test_no_samples_no_interventions_no_permits(self):
        """Clean building with no interventions needs no permits."""
        building = Building(
            id=uuid.uuid4(),
            address="Test",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=uuid.uuid4(),
        )
        permits = _determine_required_permits([], False, building)
        assert len(permits) == 0

    def test_interventions_only_triggers_construction_permit(self):
        """Interventions without pollutants trigger construction permit only."""
        building = Building(
            id=uuid.uuid4(),
            address="Test",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=uuid.uuid4(),
        )
        permits = _determine_required_permits([], True, building)
        types = {p.permit_type for p in permits}
        assert "construction_permit" in types
        assert len(types) == 1

    def test_hap_triggers_construction_permit(self):
        """HAP pollutant triggers construction permit but not SUVA."""
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="S001",
            pollutant_type="hap",
        )
        building = Building(
            id=uuid.uuid4(),
            address="Test",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=uuid.uuid4(),
        )
        permits = _determine_required_permits([sample], False, building)
        types = {p.permit_type for p in permits}
        assert "construction_permit" in types
        assert "suva_work_authorization" not in types

    def test_permit_has_required_documents(self):
        """Each permit should include required documents."""
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=uuid.uuid4(),
            sample_number="S001",
            pollutant_type="asbestos",
        )
        building = Building(
            id=uuid.uuid4(),
            address="Test",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=uuid.uuid4(),
        )
        permits = _determine_required_permits([sample], True, building)
        for permit in permits:
            assert len(permit.required_documents) > 0
            for doc in permit.required_documents:
                assert doc.name


# ── Service tests ─────────────────────────────────────────────────────


class TestGetRequiredPermits:
    @pytest.mark.asyncio
    async def test_asbestos_building(self, db_session, building_with_asbestos):
        result = await get_required_permits(db_session, building_with_asbestos.id)
        assert result.building_id == building_with_asbestos.id
        assert result.total_permits >= 4  # construction, demolition, suva, cantonal, waste
        types = {p.permit_type for p in result.permits}
        assert "suva_work_authorization" in types

    @pytest.mark.asyncio
    async def test_clean_building_no_permits(self, db_session, clean_building):
        result = await get_required_permits(db_session, clean_building.id)
        assert result.total_permits == 0
        assert result.permits == []

    @pytest.mark.asyncio
    async def test_nonexistent_building_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_required_permits(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_pcb_building(self, db_session, building_with_pcb):
        result = await get_required_permits(db_session, building_with_pcb.id)
        types = {p.permit_type for p in result.permits}
        assert "cantonal_pollutant_handling" in types
        assert "waste_transport_permit" in types


class TestTrackPermitStatus:
    @pytest.mark.asyncio
    async def test_all_not_started(self, db_session, building_with_asbestos):
        result = await track_permit_status(db_session, building_with_asbestos.id)
        assert result.building_id == building_with_asbestos.id
        assert result.overall_readiness == "blocked"
        for permit in result.permits:
            assert permit.status in ("not_started", "application_submitted")

    @pytest.mark.asyncio
    async def test_suva_submitted(self, db_session, building_with_suva_notification):
        result = await track_permit_status(db_session, building_with_suva_notification.id)
        suva = next((p for p in result.permits if p.permit_type == "suva_work_authorization"), None)
        assert suva is not None
        assert suva.status == "application_submitted"
        assert len(suva.timeline) > 0

    @pytest.mark.asyncio
    async def test_clean_building_ready(self, db_session, clean_building):
        result = await track_permit_status(db_session, clean_building.id)
        assert result.overall_readiness == "ready"
        assert len(result.permits) == 0

    @pytest.mark.asyncio
    async def test_nonexistent_building_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await track_permit_status(db_session, uuid.uuid4())


class TestGetPermitDependencies:
    @pytest.mark.asyncio
    async def test_asbestos_dependencies(self, db_session, building_with_asbestos):
        result = await get_permit_dependencies(db_session, building_with_asbestos.id)
        assert result.building_id == building_with_asbestos.id
        assert len(result.dependencies) > 0
        assert len(result.blocking_permits) > 0

    @pytest.mark.asyncio
    async def test_suva_blocks_remediation(self, db_session, building_with_asbestos):
        result = await get_permit_dependencies(db_session, building_with_asbestos.id)
        suva_dep = next(
            (d for d in result.dependencies if d.permit_type == "suva_work_authorization"),
            None,
        )
        assert suva_dep is not None
        assert "remediation" in suva_dep.blocks

    @pytest.mark.asyncio
    async def test_waste_blocks_transport(self, db_session, building_with_asbestos):
        result = await get_permit_dependencies(db_session, building_with_asbestos.id)
        waste_dep = next(
            (d for d in result.dependencies if d.permit_type == "waste_transport_permit"),
            None,
        )
        assert waste_dep is not None
        assert "waste_transport" in waste_dep.blocks

    @pytest.mark.asyncio
    async def test_demolition_depends_on_construction(self, db_session, building_with_asbestos):
        result = await get_permit_dependencies(db_session, building_with_asbestos.id)
        demo_dep = next(
            (d for d in result.dependencies if d.permit_type == "demolition_permit"),
            None,
        )
        assert demo_dep is not None
        assert "construction_permit" in demo_dep.blocked_by

    @pytest.mark.asyncio
    async def test_clean_building_no_dependencies(self, db_session, clean_building):
        result = await get_permit_dependencies(db_session, clean_building.id)
        assert len(result.dependencies) == 0
        assert len(result.blocking_permits) == 0


class TestGetPortfolioPermitOverview:
    @pytest.mark.asyncio
    async def test_org_overview(self, db_session, org_with_buildings):
        org, _b1, _b2 = org_with_buildings
        result = await get_portfolio_permit_overview(db_session, org.id)
        assert result.organization_id == org.id
        assert len(result.buildings) == 2
        assert result.total_permits_needed > 0
        assert result.buildings_blocked_count >= 1

    @pytest.mark.asyncio
    async def test_empty_org(self, db_session):
        org_id = uuid.uuid4()
        result = await get_portfolio_permit_overview(db_session, org_id)
        assert result.total_permits_needed == 0
        assert len(result.buildings) == 0
        assert result.approval_rate == 0.0

    @pytest.mark.asyncio
    async def test_approval_rate_zero_when_none_approved(self, db_session, org_with_buildings):
        org, _, _ = org_with_buildings
        result = await get_portfolio_permit_overview(db_session, org.id)
        # No permits are approved (all not_started), so rate should be 0
        assert result.approval_rate == 0.0


# ── API tests ─────────────────────────────────────────────────────────


class TestPermitTrackingAPI:
    @pytest.mark.asyncio
    async def test_get_required_permits_endpoint(self, client: AsyncClient, auth_headers, building_with_asbestos):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_asbestos.id}/permits/required",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(building_with_asbestos.id)
        assert data["total_permits"] >= 4

    @pytest.mark.asyncio
    async def test_get_permit_status_endpoint(self, client: AsyncClient, auth_headers, building_with_asbestos):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_asbestos.id}/permits/status",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_readiness" in data

    @pytest.mark.asyncio
    async def test_get_permit_dependencies_endpoint(self, client: AsyncClient, auth_headers, building_with_asbestos):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_asbestos.id}/permits/dependencies",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "dependencies" in data
        assert "blocking_permits" in data

    @pytest.mark.asyncio
    async def test_get_portfolio_overview_endpoint(self, client: AsyncClient, auth_headers, org_with_buildings):
        org, _, _ = org_with_buildings
        resp = await client.get(
            f"/api/v1/organizations/{org.id}/permits/overview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == str(org.id)

    @pytest.mark.asyncio
    async def test_404_nonexistent_building(self, client: AsyncClient, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/permits/required",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_auth(self, client: AsyncClient, building_with_asbestos):
        resp = await client.get(
            f"/api/v1/buildings/{building_with_asbestos.id}/permits/required",
        )
        assert resp.status_code == 401
