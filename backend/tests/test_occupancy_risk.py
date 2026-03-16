"""Tests for the Occupancy Risk Service (renovation exposure assessment)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.material import Material
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.schemas.occupancy_risk import (
    CommunicationPhase,
    OccupancyRiskLevel,
    RelocationUrgency,
)
from app.services.occupancy_risk_service import (
    assess_occupancy_risk,
    evaluate_temporary_relocation,
    generate_occupant_communication,
    get_portfolio_occupancy_risk,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db: AsyncSession, org_id=None, role="admin"):
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:8]}@test.ch",
        password_hash="$2b$12$LJ3m4ys3LzgJJyPCBLLPhepGqhFoBnod/sxeU1PmfMcHqnH7kPgPa",
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_building(db: AsyncSession, user_id, canton="VD", building_type="residential", **kwargs):
    building = Building(
        id=uuid.uuid4(),
        address=kwargs.get("address", "Rue Test 1"),
        postal_code="1000",
        city=kwargs.get("city", "Lausanne"),
        canton=canton,
        construction_year=kwargs.get("construction_year", 1965),
        building_type=building_type,
        created_by=user_id,
        status="active",
        floors_above=kwargs.get("floors_above", 3),
    )
    db.add(building)
    await db.flush()
    return building


async def _create_zone(db: AsyncSession, building_id, zone_type="room", name="Salon", floor_number=1, user_id=None):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type=zone_type,
        name=name,
        floor_number=floor_number,
        created_by=user_id,
    )
    db.add(zone)
    await db.flush()
    return zone


async def _create_element(db: AsyncSession, zone_id, element_type="wall"):
    elem = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone_id,
        element_type=element_type,
        name=f"{element_type} element",
    )
    db.add(elem)
    await db.flush()
    return elem


async def _create_material(
    db: AsyncSession,
    element_id,
    pollutant_type=None,
    contains_pollutant=False,
    source=None,
):
    mat = Material(
        id=uuid.uuid4(),
        element_id=element_id,
        material_type="coating",
        name=f"Material {uuid.uuid4().hex[:4]}",
        contains_pollutant=contains_pollutant,
        pollutant_type=pollutant_type,
        source=source,
    )
    db.add(mat)
    await db.flush()
    return mat


async def _create_diagnostic(db: AsyncSession, building_id, user_id):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostician_id=user_id,
        diagnostic_type="amiante",
        status="completed",
    )
    db.add(diag)
    await db.flush()
    return diag


async def _create_sample(
    db: AsyncSession,
    diagnostic_id,
    pollutant_type="asbestos",
    concentration=None,
    threshold_exceeded=False,
    material_state=None,
    location_floor=None,
):
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        threshold_exceeded=threshold_exceeded,
        material_state=material_state,
        location_floor=location_floor,
    )
    db.add(sample)
    await db.flush()
    return sample


async def _create_org(db: AsyncSession, name="Test Org"):
    org = Organization(
        id=uuid.uuid4(),
        name=name,
        type="property_management",
    )
    db.add(org)
    await db.flush()
    return org


# ---------------------------------------------------------------------------
# FN1: assess_occupancy_risk
# ---------------------------------------------------------------------------


class TestAssessOccupancyRisk:
    """Tests for assess_occupancy_risk."""

    @pytest.mark.asyncio
    async def test_building_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await assess_occupancy_risk(uuid.uuid4(), db_session)

    @pytest.mark.asyncio
    async def test_no_samples_no_zones(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.low
        assert result.risk_factors == []
        assert result.occupant_count_estimate >= 1

    @pytest.mark.asyncio
    async def test_no_samples_with_zones(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        await _create_zone(db_session, building.id, "room", "Chambre 1")
        await _create_zone(db_session, building.id, "room", "Chambre 2")
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.low
        assert result.occupant_count_estimate > 0

    @pytest.mark.asyncio
    async def test_friable_asbestos_critical(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            material_state="friable",
            threshold_exceeded=True,
        )
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.critical
        assert len(result.risk_factors) >= 1
        assert any(
            "amiante" in f.description.lower() or "friable" in f.description.lower() for f in result.risk_factors
        )

    @pytest.mark.asyncio
    async def test_confirmed_asbestos_high(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            threshold_exceeded=True,
            material_state="good",
        )
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.high

    @pytest.mark.asyncio
    async def test_radon_above_1000_critical(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="radon",
            concentration=1200.0,
        )
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.critical

    @pytest.mark.asyncio
    async def test_radon_above_300_high(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="radon",
            concentration=500.0,
        )
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.high

    @pytest.mark.asyncio
    async def test_pcb_above_threshold_high(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="pcb",
            concentration=80.0,
        )
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.high

    @pytest.mark.asyncio
    async def test_lead_above_threshold(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="lead",
            concentration=6000.0,
        )
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.high

    @pytest.mark.asyncio
    async def test_hap_low_risk(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="hap",
            threshold_exceeded=False,
        )
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.low

    @pytest.mark.asyncio
    async def test_material_with_pollutant(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        zone = await _create_zone(db_session, building.id, "room", "Salon")
        elem = await _create_element(db_session, zone.id)
        await _create_material(
            db_session,
            elem.id,
            pollutant_type="asbestos",
            contains_pollutant=True,
            source="friable",
        )
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.critical
        assert len(result.risk_factors) >= 1

    @pytest.mark.asyncio
    async def test_mixed_pollutants_worst_wins(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(db_session, diag.id, pollutant_type="hap", threshold_exceeded=False)
        await _create_sample(db_session, diag.id, pollutant_type="asbestos", material_state="friable")
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert result.risk_level == OccupancyRiskLevel.critical

    @pytest.mark.asyncio
    async def test_mitigation_recommendations_present(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(db_session, diag.id, pollutant_type="asbestos", material_state="friable")
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        assert len(result.mitigation_recommendations) > 0

    @pytest.mark.asyncio
    async def test_occupant_estimate_with_zones(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id, building_type="residential")
        for i in range(3):
            await _create_zone(db_session, building.id, "room", f"Room {i}")
        await db_session.commit()

        result = await assess_occupancy_risk(building.id, db_session)
        # 3 habitable zones * 4 (residential density) = 12
        assert result.occupant_count_estimate == 12


# ---------------------------------------------------------------------------
# FN2: evaluate_temporary_relocation
# ---------------------------------------------------------------------------


class TestEvaluateTemporaryRelocation:
    """Tests for evaluate_temporary_relocation."""

    @pytest.mark.asyncio
    async def test_no_relocation_clean_building(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        await db_session.commit()

        result = await evaluate_temporary_relocation(building.id, db_session)
        assert result.relocation_needed is False
        assert result.urgency == RelocationUrgency.not_required
        assert result.estimated_duration_days == 0

    @pytest.mark.asyncio
    async def test_immediate_relocation_friable_asbestos(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        await _create_zone(db_session, building.id, "room", "Salon")
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            material_state="friable",
            location_floor="Salon",
        )
        await db_session.commit()

        result = await evaluate_temporary_relocation(building.id, db_session)
        assert result.relocation_needed is True
        assert result.urgency == RelocationUrgency.immediate
        assert result.estimated_duration_days == 30
        assert len(result.regulatory_basis) > 0

    @pytest.mark.asyncio
    async def test_planned_relocation_high_risk(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        await _create_zone(db_session, building.id, "room", "Chambre")
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            threshold_exceeded=True,
            material_state="good",
            location_floor="Chambre",
        )
        await db_session.commit()

        result = await evaluate_temporary_relocation(building.id, db_session)
        assert result.relocation_needed is True
        assert result.urgency == RelocationUrgency.planned
        assert result.estimated_duration_days == 14

    @pytest.mark.asyncio
    async def test_cost_estimate_positive_when_relocation_needed(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        await _create_zone(db_session, building.id, "room", "Salon")
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            material_state="friable",
            location_floor="Salon",
        )
        await db_session.commit()

        result = await evaluate_temporary_relocation(building.id, db_session)
        assert result.cost_estimate_range.min_chf > 0
        assert result.cost_estimate_range.max_chf > result.cost_estimate_range.min_chf

    @pytest.mark.asyncio
    async def test_regulatory_basis_asbestos(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        await _create_zone(db_session, building.id, "room", "Room")
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            material_state="friable",
            location_floor="Room",
        )
        await db_session.commit()

        result = await evaluate_temporary_relocation(building.id, db_session)
        assert any("OTConst" in r for r in result.regulatory_basis)
        assert any("CFST" in r for r in result.regulatory_basis)

    @pytest.mark.asyncio
    async def test_no_cost_when_no_relocation(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        await db_session.commit()

        result = await evaluate_temporary_relocation(building.id, db_session)
        assert result.cost_estimate_range.min_chf == 0.0
        assert result.cost_estimate_range.max_chf == 0.0

    @pytest.mark.asyncio
    async def test_building_not_found_relocation(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await evaluate_temporary_relocation(uuid.uuid4(), db_session)


# ---------------------------------------------------------------------------
# FN3: generate_occupant_communication
# ---------------------------------------------------------------------------


class TestGenerateOccupantCommunication:
    """Tests for generate_occupant_communication."""

    @pytest.mark.asyncio
    async def test_basic_communication_plan(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id, canton="VD")
        await db_session.commit()

        result = await generate_occupant_communication(building.id, db_session)
        assert result.building_id == building.id
        assert len(result.notification_timeline) > 0
        assert len(result.key_messages) > 0
        assert len(result.affected_parties) > 0
        assert "FR" in result.language_requirements

    @pytest.mark.asyncio
    async def test_language_german_canton(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id, canton="ZH")
        await db_session.commit()

        result = await generate_occupant_communication(building.id, db_session)
        assert "DE" in result.language_requirements

    @pytest.mark.asyncio
    async def test_language_italian_canton(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id, canton="TI")
        await db_session.commit()

        result = await generate_occupant_communication(building.id, db_session)
        assert "IT" in result.language_requirements

    @pytest.mark.asyncio
    async def test_bilingual_canton(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id, canton="FR")
        await db_session.commit()

        result = await generate_occupant_communication(building.id, db_session)
        assert "FR" in result.language_requirements
        assert "DE" in result.language_requirements

    @pytest.mark.asyncio
    async def test_critical_risk_urgent_timeline(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        diag = await _create_diagnostic(db_session, building.id, user.id)
        await _create_sample(db_session, diag.id, pollutant_type="asbestos", material_state="friable")
        await db_session.commit()

        result = await generate_occupant_communication(building.id, db_session)
        assert any("J-0" in t for t in result.notification_timeline)
        assert any(m.phase == CommunicationPhase.before for m in result.key_messages)
        assert any(m.phase == CommunicationPhase.during for m in result.key_messages)
        assert any(m.phase == CommunicationPhase.after for m in result.key_messages)

    @pytest.mark.asyncio
    async def test_low_risk_simple_timeline(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id)
        await db_session.commit()

        result = await generate_occupant_communication(building.id, db_session)
        assert any("J-7" in t for t in result.notification_timeline)

    @pytest.mark.asyncio
    async def test_commercial_building_parties(self, db_session):
        user = await _create_user(db_session)
        building = await _create_building(db_session, user.id, building_type="commercial")
        await db_session.commit()

        result = await generate_occupant_communication(building.id, db_session)
        assert "Commercants" in result.affected_parties

    @pytest.mark.asyncio
    async def test_building_not_found_communication(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await generate_occupant_communication(uuid.uuid4(), db_session)


# ---------------------------------------------------------------------------
# FN4: get_portfolio_occupancy_risk
# ---------------------------------------------------------------------------


class TestGetPortfolioOccupancyRisk:
    """Tests for get_portfolio_occupancy_risk."""

    @pytest.mark.asyncio
    async def test_org_not_found(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_portfolio_occupancy_risk(uuid.uuid4(), db_session)

    @pytest.mark.asyncio
    async def test_empty_org(self, db_session):
        org = await _create_org(db_session)
        await db_session.commit()

        result = await get_portfolio_occupancy_risk(org.id, db_session)
        assert result.total_affected_occupants == 0
        assert result.relocation_needs_count == 0
        assert result.high_priority_buildings == []

    @pytest.mark.asyncio
    async def test_all_clear_buildings(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org_id=org.id)
        await _create_building(db_session, user.id, address="Rue A 1")
        await _create_building(db_session, user.id, address="Rue B 2")
        await db_session.commit()

        result = await get_portfolio_occupancy_risk(org.id, db_session)
        assert result.buildings_by_risk_level["low"] == 2
        assert result.buildings_by_risk_level["critical"] == 0
        assert result.high_priority_buildings == []

    @pytest.mark.asyncio
    async def test_mixed_risk_portfolio(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org_id=org.id)

        # Clean building
        await _create_building(db_session, user.id, address="Clean 1")

        # Critical building
        b2 = await _create_building(db_session, user.id, address="Critical 1")
        diag = await _create_diagnostic(db_session, b2.id, user.id)
        await _create_sample(db_session, diag.id, pollutant_type="asbestos", material_state="friable")
        await db_session.commit()

        result = await get_portfolio_occupancy_risk(org.id, db_session)
        assert result.buildings_by_risk_level["low"] >= 1
        assert result.buildings_by_risk_level["critical"] >= 1
        assert len(result.high_priority_buildings) >= 1
        assert result.total_affected_occupants > 0

    @pytest.mark.asyncio
    async def test_multi_canton_portfolio(self, db_session):
        """Portfolio with buildings in different cantons."""
        org = await _create_org(db_session)
        user = await _create_user(db_session, org_id=org.id)

        b_vd = await _create_building(db_session, user.id, canton="VD", address="VD Building")
        b_zh = await _create_building(db_session, user.id, canton="ZH", address="ZH Building", city="Zurich")

        diag_vd = await _create_diagnostic(db_session, b_vd.id, user.id)
        await _create_sample(db_session, diag_vd.id, pollutant_type="asbestos", material_state="friable")

        diag_zh = await _create_diagnostic(db_session, b_zh.id, user.id)
        await _create_sample(db_session, diag_zh.id, pollutant_type="pcb", concentration=80.0)
        await db_session.commit()

        result = await get_portfolio_occupancy_risk(org.id, db_session)
        assert len(result.high_priority_buildings) >= 2
        assert result.total_affected_occupants > 0
