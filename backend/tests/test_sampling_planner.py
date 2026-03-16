"""Tests for the sampling_planner service."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.material import Material
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.unknown_issue import UnknownIssue
from app.models.zone import Zone
from app.services.sampling_planner import plan_sampling

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, *, construction_year=1970):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building, *, status="completed", inspection_date=None):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status=status,
        date_inspection=inspection_date or date(2025, 1, 15),
    )
    db.add(d)
    await db.flush()
    return d


async def _create_sample(
    db,
    diagnostic,
    *,
    pollutant_type="asbestos",
    concentration=500.0,
    unit="mg/kg",
):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit=unit,
    )
    db.add(s)
    await db.flush()
    return s


async def _create_zone(db, building, admin_user, *, name="Rez-de-chaussée"):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="floor",
        name=name,
        created_by=admin_user.id,
    )
    db.add(z)
    await db.flush()
    return z


async def _create_element(db, zone, admin_user, *, name="Mur salon"):
    e = BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone.id,
        element_type="wall",
        name=name,
        created_by=admin_user.id,
    )
    db.add(e)
    await db.flush()
    return e


async def _create_material(db, element, admin_user, *, contains_pollutant=None):
    m = Material(
        id=uuid.uuid4(),
        element_id=element.id,
        material_type="coating",
        name="Enduit",
        contains_pollutant=contains_pollutant,
        created_by=admin_user.id,
    )
    db.add(m)
    await db.flush()
    return m


async def _create_plan(db, building, admin_user, *, plan_type="floor_plan"):
    p = TechnicalPlan(
        id=uuid.uuid4(),
        building_id=building.id,
        plan_type=plan_type,
        title="Plan RDC",
        file_path="/plans/rdc.pdf",
        file_name="rdc.pdf",
        uploaded_by=admin_user.id,
    )
    db.add(p)
    await db.flush()
    return p


def _action_types(plan):
    return [r.action_type for r in plan.recommendations]


def _priorities(plan):
    return [r.priority for r in plan.recommendations]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_building_no_diagnostics_recommends_pollutant_sampling(db_session, admin_user):
    """Building with no diagnostics should get sample_pollutant recommendations."""
    building = await _create_building(db_session, admin_user, construction_year=1970)
    plan = await plan_sampling(db_session, building.id)

    assert plan is not None
    pollutant_recs = [r for r in plan.recommendations if r.action_type == "sample_pollutant"]
    # 1970 building: asbestos, pcb, lead, hap, radon all applicable
    assert len(pollutant_recs) >= 5
    pollutants_recommended = {r.pollutant for r in pollutant_recs if r.pollutant}
    assert "asbestos" in pollutants_recommended
    assert "radon" in pollutants_recommended


@pytest.mark.asyncio
async def test_uninspected_zones_generate_recommendations(db_session, admin_user):
    """Building with uninspected zones should get visual_inspection or sample_zone."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    await _create_zone(db_session, building, admin_user, name="Sous-sol")
    await _create_zone(db_session, building, admin_user, name="Grenier")

    plan = await plan_sampling(db_session, building.id)

    zone_recs = [r for r in plan.recommendations if r.action_type in ("visual_inspection", "sample_zone")]
    assert len(zone_recs) >= 2
    descriptions = " ".join(r.description for r in zone_recs)
    assert "Sous-sol" in descriptions
    assert "Grenier" in descriptions


@pytest.mark.asyncio
async def test_unconfirmed_materials_generate_confirm_material(db_session, admin_user):
    """Building with unconfirmed materials → confirm_material recommendations."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    mat_id = uuid.uuid4()
    # Pre-seed an unconfirmed_material unknown so the planner picks it up
    unknown = UnknownIssue(
        id=uuid.uuid4(),
        building_id=building.id,
        unknown_type="unconfirmed_material",
        severity="medium",
        status="open",
        title="Unconfirmed material: Enduit",
        description="Material 'Enduit' has not been evaluated for pollutant content.",
        entity_type="material",
        entity_id=mat_id,
        blocks_readiness=False,
        detected_by="unknown_generator",
    )
    db_session.add(unknown)
    await db_session.flush()

    # Patch generate_unknowns to not auto-resolve pre-seeded unknowns
    with patch(
        "app.services.sampling_planner.unknown_generator.generate_unknowns",
        new_callable=AsyncMock,
        return_value=[unknown],
    ):
        plan = await plan_sampling(db_session, building.id)

    confirm_recs = [r for r in plan.recommendations if r.action_type == "confirm_material"]
    assert len(confirm_recs) >= 1
    assert confirm_recs[0].entity_type == "material"


@pytest.mark.asyncio
async def test_samples_missing_lab_results_generate_lab_analysis(db_session, admin_user):
    """Samples without concentration → lab_analysis recommendations."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    diag = await _create_diagnostic(db_session, building)
    await _create_sample(db_session, diag, concentration=None, unit=None)

    plan = await plan_sampling(db_session, building.id)

    lab_recs = [r for r in plan.recommendations if r.action_type == "lab_analysis"]
    assert len(lab_recs) >= 1
    assert lab_recs[0].entity_type == "sample"


@pytest.mark.asyncio
async def test_blocks_readiness_unknowns_get_high_priority(db_session, admin_user):
    """Unknowns that block readiness should get critical or high priority."""
    building = await _create_building(db_session, admin_user, construction_year=1970)
    plan = await plan_sampling(db_session, building.id)

    # missing_diagnostic blocks readiness → should be critical/high
    blocking_recs = [r for r in plan.recommendations if r.impact_score >= 0.9]
    assert len(blocking_recs) > 0
    for rec in blocking_recs:
        assert rec.priority in ("critical", "high")


@pytest.mark.asyncio
async def test_impact_score_in_valid_range(db_session, admin_user):
    """All impact scores should be between 0.0 and 1.0."""
    building = await _create_building(db_session, admin_user, construction_year=1970)
    plan = await plan_sampling(db_session, building.id)

    assert plan.total_recommendations > 0
    for rec in plan.recommendations:
        assert 0.0 <= rec.impact_score <= 1.0


@pytest.mark.asyncio
async def test_recommendations_sorted_by_impact_descending(db_session, admin_user):
    """Recommendations should be sorted by impact_score descending."""
    building = await _create_building(db_session, admin_user, construction_year=1970)
    await _create_zone(db_session, building, admin_user, name="Zone A")

    plan = await plan_sampling(db_session, building.id)

    scores = [r.impact_score for r in plan.recommendations]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_empty_building_gets_appropriate_recommendations(db_session, admin_user):
    """A building with no data should still get meaningful recommendations."""
    building = await _create_building(db_session, admin_user, construction_year=1970)
    plan = await plan_sampling(db_session, building.id)

    assert plan is not None
    assert plan.total_recommendations > 0
    assert plan.building_id == building.id
    assert plan.planned_at is not None


@pytest.mark.asyncio
async def test_complete_building_fewer_recommendations(db_session, admin_user):
    """Building with complete data should have fewer recommendations."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    diag = await _create_diagnostic(db_session, building, status="completed")
    # Add samples for all applicable pollutants (hap, radon for post-2006)
    await _create_sample(db_session, diag, pollutant_type="hap")
    await _create_sample(db_session, diag, pollutant_type="radon")

    plan = await plan_sampling(db_session, building.id)

    # Should have very few or no sample_pollutant recommendations
    pollutant_recs = [r for r in plan.recommendations if r.action_type == "sample_pollutant"]
    assert len(pollutant_recs) == 0


@pytest.mark.asyncio
async def test_coverage_gaps_correctly_identified(db_session, admin_user):
    """Zones with no elements should appear in coverage_gaps."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    zone1 = await _create_zone(db_session, building, admin_user, name="Zone vide")
    zone2 = await _create_zone(db_session, building, admin_user, name="Zone remplie")
    await _create_element(db_session, zone2, admin_user)

    plan = await plan_sampling(db_session, building.id)

    assert str(zone1.id) in plan.coverage_gaps
    assert str(zone2.id) not in plan.coverage_gaps


@pytest.mark.asyncio
async def test_priority_breakdown_correct(db_session, admin_user):
    """Priority breakdown should match actual recommendation counts."""
    building = await _create_building(db_session, admin_user, construction_year=1970)
    plan = await plan_sampling(db_session, building.id)

    # Count priorities manually
    counted = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for rec in plan.recommendations:
        counted[rec.priority] += 1

    assert plan.priority_breakdown == counted


@pytest.mark.asyncio
async def test_api_returns_200(client, admin_user, auth_headers, db_session):
    """GET /buildings/{id}/sampling-plan returns 200 with valid plan."""
    building = await _create_building(db_session, admin_user, construction_year=1970)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/sampling-plan",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(building.id)
    assert "recommendations" in data
    assert "total_recommendations" in data
    assert "priority_breakdown" in data


@pytest.mark.asyncio
async def test_api_returns_404_nonexistent_building(client, admin_user, auth_headers):
    """GET /buildings/{id}/sampling-plan returns 404 for unknown building."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/sampling-plan",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_nonexistent_building_returns_none(db_session, admin_user):
    """plan_sampling returns None for a non-existent building."""
    result = await plan_sampling(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_estimated_completeness_after_is_valid(db_session, admin_user):
    """estimated_completeness_after should be between 0.0 and 1.0."""
    building = await _create_building(db_session, admin_user, construction_year=1970)
    plan = await plan_sampling(db_session, building.id)

    assert 0.0 <= plan.estimated_completeness_after <= 1.0


@pytest.mark.asyncio
async def test_upload_plan_recommendation_for_zones_without_plan(db_session, admin_user):
    """Building with zones but no floor plan → upload_plan recommendation."""
    building = await _create_building(db_session, admin_user, construction_year=2010)
    await _create_zone(db_session, building, admin_user)

    plan = await plan_sampling(db_session, building.id)

    upload_recs = [r for r in plan.recommendations if r.action_type == "upload_plan"]
    assert len(upload_recs) >= 1
