"""Tests for the Tenant Impact Service — 4 endpoints, ≥20 tests."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="Regie Test SA",
        type="property_management",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_admin(db_session, org):
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email="orgadmin@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="Admin",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def building_residential(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue du Lac 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def building_commercial(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Avenue du Commerce 5",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1975,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def zone_habitable(db_session, building_residential, admin_user):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building_residential.id,
        zone_type="room",
        name="Salon 1er etage",
        floor_number=1,
        surface_area_m2=35.0,
        created_by=admin_user.id,
    )
    db_session.add(z)
    await db_session.commit()
    await db_session.refresh(z)
    return z


@pytest.fixture
async def zone_technical(db_session, building_residential, admin_user):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building_residential.id,
        zone_type="technical_room",
        name="Chaufferie sous-sol",
        floor_number=-1,
        surface_area_m2=20.0,
        created_by=admin_user.id,
    )
    db_session.add(z)
    await db_session.commit()
    await db_session.refresh(z)
    return z


@pytest.fixture
async def zone_commercial(db_session, building_commercial, admin_user):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building_commercial.id,
        zone_type="room",
        name="Bureau principal",
        floor_number=0,
        surface_area_m2=80.0,
        created_by=admin_user.id,
    )
    db_session.add(z)
    await db_session.commit()
    await db_session.refresh(z)
    return z


@pytest.fixture
async def diagnostic_with_asbestos(db_session, building_residential, admin_user, zone_habitable):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_residential.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        location_floor="Salon 1er etage",
        material_description="Flocage plafond",
        material_state="friable",
        pollutant_type="asbestos",
        concentration=None,
        risk_level="critical",
        cfst_work_category="major",
    )
    db_session.add(sample)
    await db_session.commit()
    return diag


@pytest.fixture
async def diagnostic_with_pcb(db_session, building_residential, admin_user, zone_habitable):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_residential.id,
        diagnostic_type="pcb",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-002",
        location_floor="Salon 1er etage",
        material_description="Joint fenetre",
        material_state="intact",
        pollutant_type="pcb",
        concentration=80.0,
        unit="mg/kg",
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()
    return diag


# ---------------------------------------------------------------------------
# FN1: assess_tenant_impact
# ---------------------------------------------------------------------------


class TestAssessTenantImpact:
    @pytest.mark.anyio
    async def test_no_zones_returns_empty(self, client: AsyncClient, auth_headers, building_residential):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/tenant-impact",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_zones"] == 0
        assert data["zones_requiring_displacement"] == 0
        assert data["total_estimated_cost_chf"] == 0.0

    @pytest.mark.anyio
    async def test_zone_without_pollutants(
        self, client: AsyncClient, auth_headers, building_residential, zone_habitable
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/tenant-impact",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_zones"] == 1
        assert data["zones_requiring_displacement"] == 0
        assert data["zones"][0]["displacement_needed"] == "none"

    @pytest.mark.anyio
    async def test_friable_asbestos_requires_displacement(
        self,
        client: AsyncClient,
        auth_headers,
        building_residential,
        zone_habitable,
        diagnostic_with_asbestos,
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/tenant-impact",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["zones_requiring_displacement"] >= 1
        zone = data["zones"][0]
        assert zone["displacement_needed"] == "temporary"
        assert zone["estimated_duration_days"] > 0
        assert zone["alternative_accommodation_cost_chf"] > 0
        assert zone["rent_reduction_percent"] == 100.0

    @pytest.mark.anyio
    async def test_notice_period_residential(
        self, client: AsyncClient, auth_headers, building_residential, zone_habitable
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/tenant-impact",
            headers=auth_headers,
        )
        data = resp.json()
        if data["zones"]:
            assert data["zones"][0]["notice_period_days"] == 30

    @pytest.mark.anyio
    async def test_notice_period_commercial(
        self, client: AsyncClient, auth_headers, building_commercial, zone_commercial
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_commercial.id}/tenant-impact",
            headers=auth_headers,
        )
        data = resp.json()
        if data["zones"]:
            assert data["zones"][0]["notice_period_days"] == 60

    @pytest.mark.anyio
    async def test_building_not_found(self, client: AsyncClient, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/tenant-impact",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_swiss_law_reference_present(self, client: AsyncClient, auth_headers, building_residential):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/tenant-impact",
            headers=auth_headers,
        )
        data = resp.json()
        assert "CO Art." in data["swiss_law_reference"]


# ---------------------------------------------------------------------------
# FN2: generate_tenant_communication_plan
# ---------------------------------------------------------------------------


class TestTenantCommunicationPlan:
    @pytest.mark.anyio
    async def test_basic_plan_no_displacement(
        self, client: AsyncClient, auth_headers, building_residential, zone_habitable
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/tenant-communication-plan",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_communications"] >= 2  # initial + reentry at minimum
        types = [c["communication_type"] for c in data["communications"]]
        assert "initial_notice" in types
        assert "reentry_clearance" in types

    @pytest.mark.anyio
    async def test_plan_with_displacement_includes_relogement(
        self,
        client: AsyncClient,
        auth_headers,
        building_residential,
        zone_habitable,
        diagnostic_with_asbestos,
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/tenant-communication-plan",
            headers=auth_headers,
        )
        data = resp.json()
        # Should have displacement notice
        assert data["total_communications"] >= 3
        descriptions = [c["description"] for c in data["communications"]]
        has_relogement = any("relogement" in d.lower() for d in descriptions)
        assert has_relogement

    @pytest.mark.anyio
    async def test_plan_has_template_sections(
        self, client: AsyncClient, auth_headers, building_residential, zone_habitable
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/tenant-communication-plan",
            headers=auth_headers,
        )
        data = resp.json()
        for comm in data["communications"]:
            assert len(comm["template_sections"]) > 0

    @pytest.mark.anyio
    async def test_building_not_found_comm_plan(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            f"/api/v1/buildings/{uuid.uuid4()}/tenant-communication-plan",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_earliest_notice_days(self, client: AsyncClient, auth_headers, building_residential, zone_habitable):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/tenant-communication-plan",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["earliest_notice_days_before"] == 30


# ---------------------------------------------------------------------------
# FN3: estimate_displacement_costs
# ---------------------------------------------------------------------------


class TestDisplacementCosts:
    @pytest.mark.anyio
    async def test_no_displacement_zero_costs(
        self, client: AsyncClient, auth_headers, building_residential, zone_habitable
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/displacement-costs",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["grand_total_chf"] == 0.0

    @pytest.mark.anyio
    async def test_displacement_has_costs(
        self,
        client: AsyncClient,
        auth_headers,
        building_residential,
        zone_habitable,
        diagnostic_with_asbestos,
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/displacement-costs",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["grand_total_chf"] > 0
        assert data["total_temporary_relocation_chf"] > 0
        assert data["total_rent_loss_chf"] > 0
        assert data["total_moving_costs_chf"] > 0

    @pytest.mark.anyio
    async def test_commercial_has_business_interruption(
        self,
        client: AsyncClient,
        auth_headers,
        building_commercial,
        zone_commercial,
        db_session,
        admin_user,
    ):
        # Add a diagnostic with critical asbestos to commercial building
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building_commercial.id,
            diagnostic_type="asbestos",
            status="completed",
            diagnostician_id=admin_user.id,
        )
        db_session.add(diag)
        await db_session.flush()
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S-C01",
            location_floor="Bureau principal",
            material_state="friable",
            pollutant_type="asbestos",
            risk_level="critical",
            cfst_work_category="major",
        )
        db_session.add(sample)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/buildings/{building_commercial.id}/displacement-costs",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["total_business_interruption_chf"] > 0

    @pytest.mark.anyio
    async def test_per_zone_breakdown(
        self,
        client: AsyncClient,
        auth_headers,
        building_residential,
        zone_habitable,
        zone_technical,
        diagnostic_with_asbestos,
    ):
        resp = await client.get(
            f"/api/v1/buildings/{building_residential.id}/displacement-costs",
            headers=auth_headers,
        )
        data = resp.json()
        assert len(data["zones"]) == 2

    @pytest.mark.anyio
    async def test_building_not_found_costs(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            f"/api/v1/buildings/{uuid.uuid4()}/displacement-costs",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# FN4: get_portfolio_tenant_exposure
# ---------------------------------------------------------------------------


class TestPortfolioTenantExposure:
    @pytest.mark.anyio
    async def test_empty_org(self, client: AsyncClient, auth_headers, org):
        resp = await client.get(
            f"/api/v1/organizations/{org.id}/tenant-exposure",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_buildings"] == 0

    @pytest.mark.anyio
    async def test_org_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            f"/api/v1/organizations/{uuid.uuid4()}/tenant-exposure",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_org_with_buildings(
        self,
        client: AsyncClient,
        auth_headers,
        org,
        org_admin,
        db_session,
    ):
        # Create building owned by org member
        b = Building(
            id=uuid.uuid4(),
            address="Rue Test 99",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1965,
            building_type="residential",
            created_by=org_admin.id,
            status="active",
        )
        db_session.add(b)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/organizations/{org.id}/tenant-exposure",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["total_buildings"] == 1
        assert data["buildings_requiring_action"] == 0

    @pytest.mark.anyio
    async def test_org_with_affected_building(
        self,
        client: AsyncClient,
        auth_headers,
        org,
        org_admin,
        db_session,
    ):
        # Building with asbestos zone
        b = Building(
            id=uuid.uuid4(),
            address="Rue Danger 1",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1955,
            building_type="residential",
            created_by=org_admin.id,
            status="active",
        )
        db_session.add(b)
        await db_session.flush()

        z = Zone(
            id=uuid.uuid4(),
            building_id=b.id,
            zone_type="room",
            name="Chambre principale",
            floor_number=1,
            created_by=org_admin.id,
        )
        db_session.add(z)
        await db_session.flush()

        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=b.id,
            diagnostic_type="asbestos",
            status="completed",
            diagnostician_id=org_admin.id,
        )
        db_session.add(diag)
        await db_session.flush()

        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S-P01",
            location_floor="Chambre principale",
            material_state="friable",
            pollutant_type="asbestos",
            risk_level="critical",
            cfst_work_category="major",
        )
        db_session.add(sample)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/organizations/{org.id}/tenant-exposure",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["total_buildings"] == 1
        assert data["buildings_requiring_action"] == 1
        assert data["total_displacement_cost_chf"] > 0
        assert data["timeline_pressure_days"] > 0
        assert len(data["buildings"]) == 1

    @pytest.mark.anyio
    async def test_unauthenticated(self, client: AsyncClient, org):
        resp = await client.get(
            f"/api/v1/organizations/{org.id}/tenant-exposure",
        )
        assert resp.status_code in (401, 403)
