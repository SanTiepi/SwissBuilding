"""Tests for the Access Control service and API."""

import uuid

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.material import Material
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.access_control import AccessLevel, SUVACertLevel
from app.services.access_control_service import (
    _determine_access_level,
    _get_ppe_for_zone,
    _get_signage_for_zone,
    _get_suva_cert_level,
    _get_training_requirements,
    generate_access_permit_requirements,
    generate_access_restrictions,
    get_portfolio_access_status,
    get_safe_zones,
)

# ---------------------------------------------------------------------------
# Pure logic unit tests
# ---------------------------------------------------------------------------


class TestDetermineAccessLevel:
    def test_no_pollutants_unrestricted(self):
        level, _ = _determine_access_level([], "room")
        assert level == AccessLevel.unrestricted

    def test_friable_asbestos_habitable_prohibited(self):
        pollutants = [{"pollutant_type": "asbestos", "material_state": "friable", "concentration": None}]
        level, reason = _determine_access_level(pollutants, "room")
        assert level == AccessLevel.prohibited
        assert "interdit" in reason.lower()

    def test_friable_asbestos_technical_restricted_authorized(self):
        pollutants = [{"pollutant_type": "asbestos", "material_state": "friable", "concentration": None}]
        level, _ = _determine_access_level(pollutants, "technical_room")
        assert level == AccessLevel.restricted_authorized

    def test_non_friable_asbestos_habitable_restricted_ppe(self):
        pollutants = [{"pollutant_type": "asbestos", "material_state": "encapsulated", "concentration": None}]
        level, _ = _determine_access_level(pollutants, "room")
        assert level == AccessLevel.restricted_ppe

    def test_non_friable_asbestos_technical_unrestricted(self):
        pollutants = [{"pollutant_type": "asbestos", "material_state": "encapsulated", "concentration": None}]
        level, _ = _determine_access_level(pollutants, "technical_room")
        assert level == AccessLevel.unrestricted

    def test_radon_above_1000_prohibited(self):
        pollutants = [{"pollutant_type": "radon", "material_state": None, "concentration": 1200.0}]
        level, _ = _determine_access_level(pollutants, "basement")
        assert level == AccessLevel.prohibited

    def test_radon_above_300_restricted_ppe(self):
        pollutants = [{"pollutant_type": "radon", "material_state": None, "concentration": 450.0}]
        level, _ = _determine_access_level(pollutants, "basement")
        assert level == AccessLevel.restricted_ppe

    def test_radon_below_300_unrestricted(self):
        pollutants = [{"pollutant_type": "radon", "material_state": None, "concentration": 150.0}]
        level, _ = _determine_access_level(pollutants, "room")
        assert level == AccessLevel.unrestricted

    def test_pcb_above_50_habitable_restricted_authorized(self):
        pollutants = [{"pollutant_type": "pcb", "material_state": None, "concentration": 80.0}]
        level, _ = _determine_access_level(pollutants, "room")
        assert level == AccessLevel.restricted_authorized

    def test_pcb_above_50_technical_restricted_ppe(self):
        pollutants = [{"pollutant_type": "pcb", "material_state": None, "concentration": 80.0}]
        level, _ = _determine_access_level(pollutants, "technical_room")
        assert level == AccessLevel.restricted_ppe

    def test_lead_above_5000_habitable_restricted_authorized(self):
        pollutants = [{"pollutant_type": "lead", "material_state": None, "concentration": 6000.0}]
        level, _ = _determine_access_level(pollutants, "room")
        assert level == AccessLevel.restricted_authorized

    def test_multiple_pollutants_worst_wins(self):
        pollutants = [
            {"pollutant_type": "lead", "material_state": None, "concentration": 6000.0},
            {"pollutant_type": "asbestos", "material_state": "friable", "concentration": None},
        ]
        level, _ = _determine_access_level(pollutants, "room")
        assert level == AccessLevel.prohibited


class TestPPERequirements:
    def test_unrestricted_no_ppe(self):
        ppe = _get_ppe_for_zone([], AccessLevel.unrestricted)
        assert ppe is None

    def test_friable_asbestos_full_protection(self):
        pollutants = [{"pollutant_type": "asbestos", "material_state": "friable"}]
        ppe = _get_ppe_for_zone(pollutants, AccessLevel.restricted_authorized)
        assert ppe is not None
        assert ppe.mask_type == "full_face_p3"
        assert ppe.gloves_required is True
        assert ppe.safety_goggles is True

    def test_pcb_gloves_and_goggles(self):
        pollutants = [{"pollutant_type": "pcb", "material_state": None}]
        ppe = _get_ppe_for_zone(pollutants, AccessLevel.restricted_ppe)
        assert ppe is not None
        assert ppe.gloves_required is True
        assert ppe.safety_goggles is True


class TestSignage:
    def test_unrestricted_no_signage(self):
        signage = _get_signage_for_zone([], AccessLevel.unrestricted)
        assert signage == []

    def test_prohibited_danger_sign(self):
        pollutants = [{"pollutant_type": "asbestos", "material_state": "friable"}]
        signage = _get_signage_for_zone(pollutants, AccessLevel.prohibited)
        assert any(s.sign_type == "danger" for s in signage)

    def test_asbestos_specific_signage(self):
        pollutants = [{"pollutant_type": "asbestos", "material_state": "friable"}]
        signage = _get_signage_for_zone(pollutants, AccessLevel.restricted_authorized)
        texts = [s.text_fr for s in signage]
        assert any("AMIANTE" in t for t in texts)


class TestSUVACertLevel:
    def test_unrestricted_no_cert(self):
        cert = _get_suva_cert_level([], AccessLevel.unrestricted)
        assert cert == SUVACertLevel.none

    def test_friable_asbestos_specialist(self):
        pollutants = [
            {"pollutant_type": "asbestos", "material_state": "friable", "cfst_work_category": None},
        ]
        cert = _get_suva_cert_level(pollutants, AccessLevel.restricted_authorized)
        assert cert == SUVACertLevel.specialist

    def test_major_cfst_specialist(self):
        pollutants = [
            {"pollutant_type": "asbestos", "material_state": "encapsulated", "cfst_work_category": "major"},
        ]
        cert = _get_suva_cert_level(pollutants, AccessLevel.restricted_ppe)
        assert cert == SUVACertLevel.specialist

    def test_medium_cfst_advanced(self):
        pollutants = [
            {"pollutant_type": "asbestos", "material_state": "encapsulated", "cfst_work_category": "medium"},
        ]
        cert = _get_suva_cert_level(pollutants, AccessLevel.restricted_ppe)
        assert cert == SUVACertLevel.advanced

    def test_restricted_authorized_non_asbestos(self):
        pollutants = [
            {"pollutant_type": "pcb", "material_state": None, "cfst_work_category": None},
        ]
        cert = _get_suva_cert_level(pollutants, AccessLevel.restricted_authorized)
        assert cert == SUVACertLevel.advanced


class TestTrainingRequirements:
    def test_unrestricted_no_training(self):
        reqs = _get_training_requirements([], AccessLevel.unrestricted)
        assert reqs == []

    def test_friable_asbestos_suva_training(self):
        pollutants = [{"pollutant_type": "asbestos", "material_state": "friable"}]
        reqs = _get_training_requirements(pollutants, AccessLevel.restricted_authorized)
        assert any("SUVA" in r for r in reqs)

    def test_ppe_training_included(self):
        pollutants = [{"pollutant_type": "lead", "material_state": None}]
        reqs = _get_training_requirements(pollutants, AccessLevel.restricted_ppe)
        assert any("EPI" in r for r in reqs)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building_with_zones(db_session, admin_user):
    """Building with zones containing pollutants at various levels."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Danger 10",
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

    # Zone 1: habitable room with friable asbestos -> prohibited
    zone_room = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="room",
        name="Salon",
        floor_number=1,
    )
    db_session.add(zone_room)
    await db_session.flush()

    element = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone_room.id,
        element_type="coating",
        name="Flocage plafond",
        condition="degraded",
    )
    db_session.add(element)
    await db_session.flush()

    material_asbestos = Material(
        id=uuid.uuid4(),
        element_id=element.id,
        material_type="insulation",
        name="Flocage amiante",
        contains_pollutant=True,
        pollutant_type="asbestos",
        source="friable",
    )
    db_session.add(material_asbestos)

    # Zone 2: basement with radon > 300
    zone_basement = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="basement",
        name="Cave",
        floor_number=-1,
    )
    db_session.add(zone_basement)
    await db_session.flush()

    # Zone 3: technical room, safe (no pollutants)
    zone_tech = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="technical_room",
        name="Local technique",
        floor_number=0,
    )
    db_session.add(zone_tech)
    await db_session.flush()

    # Diagnostic with radon sample for basement
    diagnostic = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="radon",
        status="completed",
    )
    db_session.add(diagnostic)
    await db_session.flush()

    sample_radon = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number="R-001",
        location_floor="Cave",
        pollutant_type="radon",
        concentration=450.0,
        unit="Bq/m3",
        risk_level="medium",
    )
    db_session.add(sample_radon)
    await db_session.commit()

    return building, [zone_room, zone_basement, zone_tech]


@pytest.fixture
async def org_with_buildings(db_session, admin_user):
    """Organization with buildings for portfolio tests."""
    org = Organization(
        id=uuid.uuid4(),
        name="Regie Test SA",
        type="property_management",
    )
    db_session.add(org)
    await db_session.flush()

    admin_user.organization_id = org.id
    db_session.add(admin_user)
    await db_session.flush()

    # Building 1: safe (no zones/pollutants)
    b1 = Building(
        id=uuid.uuid4(),
        address="Rue Safe 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2020,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    # Building 2: with danger
    b2 = Building(
        id=uuid.uuid4(),
        address="Rue Danger 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1955,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add_all([b1, b2])
    await db_session.flush()

    # Add danger zone to b2
    zone = Zone(
        id=uuid.uuid4(),
        building_id=b2.id,
        zone_type="room",
        name="Chambre",
        floor_number=1,
    )
    db_session.add(zone)
    await db_session.flush()

    elem = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone.id,
        element_type="insulation",
        name="Calorifugeage",
        condition="degraded",
    )
    db_session.add(elem)
    await db_session.flush()

    mat = Material(
        id=uuid.uuid4(),
        element_id=elem.id,
        material_type="insulation",
        name="Amiante friable",
        contains_pollutant=True,
        pollutant_type="asbestos",
        source="friable",
    )
    db_session.add(mat)
    await db_session.commit()

    return org, [b1, b2]


# ---------------------------------------------------------------------------
# Service integration tests (with DB)
# ---------------------------------------------------------------------------


class TestGenerateAccessRestrictions:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await generate_access_restrictions(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_safe_building_no_zones(self, db_session, sample_building):
        result = await generate_access_restrictions(db_session, sample_building.id)
        assert result.total_zones == 0
        assert result.restricted_zones == 0
        assert result.prohibited_zones == 0

    @pytest.mark.asyncio
    async def test_building_with_friable_asbestos(self, db_session, building_with_zones):
        building, _zones = building_with_zones
        result = await generate_access_restrictions(db_session, building.id)
        assert result.prohibited_zones >= 1
        # Room with friable asbestos should be prohibited
        room_zones = [z for z in result.zones if z.zone_name == "Salon"]
        assert len(room_zones) == 1
        assert room_zones[0].access_level == AccessLevel.prohibited

    @pytest.mark.asyncio
    async def test_ppe_attached_to_restricted_zones(self, db_session, building_with_zones):
        building, _ = building_with_zones
        result = await generate_access_restrictions(db_session, building.id)
        restricted = [z for z in result.zones if z.access_level in (AccessLevel.restricted_ppe, AccessLevel.prohibited)]
        for z in restricted:
            # PPE may be present for restricted zones
            if z.access_level != AccessLevel.unrestricted:
                assert z.ppe is not None or z.access_level == AccessLevel.restricted_ppe

    @pytest.mark.asyncio
    async def test_signage_on_prohibited(self, db_session, building_with_zones):
        building, _ = building_with_zones
        result = await generate_access_restrictions(db_session, building.id)
        prohibited = [z for z in result.zones if z.access_level == AccessLevel.prohibited]
        for z in prohibited:
            assert len(z.signage) > 0

    @pytest.mark.asyncio
    async def test_zone_count_matches(self, db_session, building_with_zones):
        building, zones = building_with_zones
        result = await generate_access_restrictions(db_session, building.id)
        assert result.total_zones == len(zones)


class TestGetSafeZones:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_safe_zones(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_safe_building_all_safe(self, db_session, sample_building):
        result = await get_safe_zones(db_session, sample_building.id)
        assert result.restricted_zones_count == 0
        assert result.safe_ratio == 1.0

    @pytest.mark.asyncio
    async def test_building_with_pollutants(self, db_session, building_with_zones):
        building, _zones = building_with_zones
        result = await get_safe_zones(db_session, building.id)
        # Technical room should be safe (no pollutants)
        safe_names = [z.zone_name for z in result.safe_zones]
        assert "Local technique" in safe_names
        # Room with asbestos should NOT be in safe list
        assert "Salon" not in safe_names
        assert result.restricted_zones_count >= 1
        assert result.safe_ratio < 1.0


class TestGenerateAccessPermitRequirements:
    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await generate_access_permit_requirements(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_safe_building_no_permits(self, db_session, sample_building):
        result = await generate_access_permit_requirements(db_session, sample_building.id)
        assert result.zones_requiring_permits == 0
        assert result.max_suva_cert_level == SUVACertLevel.none
        assert result.any_medical_clearance is False

    @pytest.mark.asyncio
    async def test_friable_asbestos_specialist_cert(self, db_session, building_with_zones):
        building, _ = building_with_zones
        result = await generate_access_permit_requirements(db_session, building.id)
        assert result.zones_requiring_permits >= 1
        # Friable asbestos requires specialist
        assert result.max_suva_cert_level == SUVACertLevel.specialist
        assert result.any_medical_clearance is True

    @pytest.mark.asyncio
    async def test_escort_for_prohibited_zones(self, db_session, building_with_zones):
        building, _ = building_with_zones
        result = await generate_access_permit_requirements(db_session, building.id)
        prohibited_permits = [z for z in result.zones if z.access_level == AccessLevel.prohibited]
        for z in prohibited_permits:
            assert z.escort_required is True

    @pytest.mark.asyncio
    async def test_training_requirements_present(self, db_session, building_with_zones):
        building, _ = building_with_zones
        result = await generate_access_permit_requirements(db_session, building.id)
        restricted = [z for z in result.zones if z.suva_cert_level != SUVACertLevel.none]
        for z in restricted:
            assert len(z.training_requirements) > 0


class TestPortfolioAccessStatus:
    @pytest.mark.asyncio
    async def test_org_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_portfolio_access_status(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_portfolio_with_restrictions(self, db_session, org_with_buildings):
        org, _buildings = org_with_buildings
        result = await get_portfolio_access_status(db_session, org.id)
        assert result.total_buildings == 2
        assert result.buildings_with_restrictions >= 1
        assert result.buildings_fully_accessible >= 1
        assert result.total_restricted_zones >= 1
        assert result.access_compliance_rate < 1.0

    @pytest.mark.asyncio
    async def test_portfolio_buildings_listed(self, db_session, org_with_buildings):
        org, _ = org_with_buildings
        result = await get_portfolio_access_status(db_session, org.id)
        assert len(result.buildings) == 2
        # Buildings with restrictions should come first
        if len(result.buildings) >= 2:
            assert result.buildings[0].fully_accessible is False


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestAccessControlAPI:
    @pytest.mark.asyncio
    async def test_get_access_restrictions_404(self, client, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/buildings/{fake_id}/access-restrictions", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_access_restrictions_ok(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/access-restrictions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "zones" in data
        assert data["total_zones"] == 0

    @pytest.mark.asyncio
    async def test_get_safe_zones_404(self, client, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/buildings/{fake_id}/safe-zones", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_safe_zones_ok(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/safe-zones",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "safe_zones" in data

    @pytest.mark.asyncio
    async def test_get_access_permits_404(self, client, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/buildings/{fake_id}/access-permits", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_access_permits_ok(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/access-permits",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "zones" in data
        assert data["zones_requiring_permits"] == 0

    @pytest.mark.asyncio
    async def test_get_access_status_404(self, client, auth_headers):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/organizations/{fake_id}/access-status", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_403(self, client):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/buildings/{fake_id}/access-restrictions")
        assert resp.status_code == 403
