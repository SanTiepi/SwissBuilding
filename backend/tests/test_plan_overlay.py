"""Tests for the Plan Overlay Service (Programme G)."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.zone import Zone
from app.services.plan_overlay_service import (
    generate_intervention_overlay,
    generate_pollutant_overlay,
    generate_trust_overlay,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(db_session, *, building_id=None, created_by=None):
    b = Building(
        id=building_id or uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=created_by,
        status="active",
    )
    db_session.add(b)
    return b


def _make_plan(db_session, building_id, *, plan_id=None):
    p = TechnicalPlan(
        id=plan_id or uuid.uuid4(),
        building_id=building_id,
        plan_type="floor_plan",
        title="Ground Floor",
        file_path="/plans/gf.pdf",
        file_name="gf.pdf",
    )
    db_session.add(p)
    return p


def _make_zone(
    db_session,
    building_id,
    *,
    zone_id=None,
    name="Zone A",
    floor_number=None,
    surface_area_m2=None,
    description=None,
    usage_type=None,
):
    z = Zone(
        id=zone_id or uuid.uuid4(),
        building_id=building_id,
        name=name,
        zone_type="room",
        floor_number=floor_number,
        surface_area_m2=surface_area_m2,
        description=description,
        usage_type=usage_type,
    )
    db_session.add(z)
    return z


def _make_diagnostic(db_session, building_id, *, diagnostic_id=None):
    d = Diagnostic(
        id=diagnostic_id or uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(d)
    return d


def _make_sample(
    db_session,
    diagnostic_id,
    *,
    sample_id=None,
    pollutant_type="asbestos",
    concentration=None,
    threshold_exceeded=False,
    risk_level="low",
    location_floor=None,
):
    s = Sample(
        id=sample_id or uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        threshold_exceeded=threshold_exceeded,
        risk_level=risk_level,
        location_floor=location_floor,
    )
    db_session.add(s)
    return s


def _make_intervention(
    db_session, building_id, *, intervention_type="removal", status="completed", zones_affected=None, date_start=None
):
    i = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=intervention_type,
        title=f"Intervention {uuid.uuid4().hex[:6]}",
        status=status,
        zones_affected=zones_affected,
        date_start=date_start,
    )
    db_session.add(i)
    return i


# ---------------------------------------------------------------------------
# Pollutant overlay tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pollutant_overlay_empty_plan(db_session, admin_user):
    """Plan with no zones returns empty overlay."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    await db_session.commit()

    result = await generate_pollutant_overlay(db_session, plan.id)
    assert result["zones"] == []
    assert result["samples"] == []
    assert result["legend"] == []


@pytest.mark.asyncio
async def test_pollutant_overlay_nonexistent_plan(db_session):
    """Nonexistent plan returns empty overlay."""
    result = await generate_pollutant_overlay(db_session, uuid.uuid4())
    assert result["zones"] == []
    assert result["samples"] == []
    assert result["legend"] == []


@pytest.mark.asyncio
async def test_pollutant_overlay_zones_without_samples(db_session, admin_user):
    """Zones without any samples get 'unknown' status."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    _make_zone(db_session, building.id, name="Zone A")
    _make_zone(db_session, building.id, name="Zone B")
    await db_session.commit()

    result = await generate_pollutant_overlay(db_session, plan.id)
    assert len(result["zones"]) == 2
    assert all(z["pollutant_status"] == "unknown" for z in result["zones"])
    assert all(z["color"] == "#808080" for z in result["zones"])
    assert len(result["legend"]) == 1
    assert result["legend"][0]["status"] == "unknown"
    assert result["legend"][0]["count"] == 2


@pytest.mark.asyncio
async def test_pollutant_overlay_confirmed_status(db_session, admin_user):
    """Zone with positive sample gets 'confirmed' status (red)."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    _make_zone(db_session, building.id, name="Zone A", floor_number=0)
    diag = _make_diagnostic(db_session, building.id)
    _make_sample(
        db_session,
        diag.id,
        concentration=1200.0,
        threshold_exceeded=True,
        location_floor="0",
    )
    await db_session.commit()

    result = await generate_pollutant_overlay(db_session, plan.id)
    assert len(result["zones"]) == 1
    assert result["zones"][0]["pollutant_status"] == "confirmed"
    assert result["zones"][0]["color"] == "#FF0000"
    assert result["zones"][0]["confidence"] == 0.9
    # Sample should also appear
    assert len(result["samples"]) == 1
    assert result["samples"][0]["result"] == "positive"


@pytest.mark.asyncio
async def test_pollutant_overlay_negative_status(db_session, admin_user):
    """Zone with negative sample gets 'negative' status (green)."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    _make_zone(db_session, building.id, name="Zone A", floor_number=1)
    diag = _make_diagnostic(db_session, building.id)
    _make_sample(
        db_session,
        diag.id,
        concentration=10.0,
        threshold_exceeded=False,
        risk_level="low",
        location_floor="1",
    )
    await db_session.commit()

    result = await generate_pollutant_overlay(db_session, plan.id)
    assert len(result["zones"]) == 1
    assert result["zones"][0]["pollutant_status"] == "negative"
    assert result["zones"][0]["color"] == "#00FF00"


@pytest.mark.asyncio
async def test_pollutant_overlay_legend_counts(db_session, admin_user):
    """Legend contains correct counts per status."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    _make_zone(db_session, building.id, name="Zone A", floor_number=0)
    _make_zone(db_session, building.id, name="Zone B", floor_number=1)
    _make_zone(db_session, building.id, name="Zone C")  # no floor => unknown
    diag = _make_diagnostic(db_session, building.id)
    _make_sample(db_session, diag.id, threshold_exceeded=True, location_floor="0")
    _make_sample(db_session, diag.id, concentration=5.0, threshold_exceeded=False, location_floor="1")
    await db_session.commit()

    result = await generate_pollutant_overlay(db_session, plan.id)
    legend_map = {item["status"]: item["count"] for item in result["legend"]}
    assert legend_map.get("confirmed", 0) == 1
    assert legend_map.get("negative", 0) == 1
    assert legend_map.get("unknown", 0) == 1


# ---------------------------------------------------------------------------
# Trust overlay tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trust_overlay_empty_plan(db_session, admin_user):
    """Plan with no zones returns empty trust overlay."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    await db_session.commit()

    result = await generate_trust_overlay(db_session, plan.id)
    assert result["zones"] == []
    assert result["overall_trust"] == 0.0


@pytest.mark.asyncio
async def test_trust_overlay_zone_with_full_data(db_session, admin_user):
    """Zone with diagnostics, samples, and metadata gets high trust."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    zone = _make_zone(
        db_session,
        building.id,
        name="Well documented",
        floor_number=0,
        surface_area_m2=45.0,
        description="Living room",
        usage_type="residential",
    )
    diag = _make_diagnostic(db_session, building.id)
    _make_sample(db_session, diag.id, concentration=120.0, location_floor="0")
    _make_intervention(
        db_session,
        building.id,
        zones_affected=[str(zone.id)],
        date_start=date(2024, 1, 15),
    )
    await db_session.commit()

    result = await generate_trust_overlay(db_session, plan.id)
    assert len(result["zones"]) == 1
    zone_data = result["zones"][0]
    # 30 (diag) + 30 (samples) + 10 (lab) + 15 (intervention) + 5 (surface) + 5 (desc) + 5 (usage) = 100
    assert zone_data["trust_score"] == 100.0
    assert zone_data["missing_info"] == []
    assert result["overall_trust"] == 100.0


@pytest.mark.asyncio
async def test_trust_overlay_zone_with_gaps(db_session, admin_user):
    """Zone missing data shows lower trust and lists missing info."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    _make_zone(db_session, building.id, name="Sparse zone")
    await db_session.commit()

    result = await generate_trust_overlay(db_session, plan.id)
    assert len(result["zones"]) == 1
    zone_data = result["zones"][0]
    # No diagnostics, no samples, no interventions, no metadata
    assert zone_data["trust_score"] == 0.0
    assert "no_diagnostics" in zone_data["missing_info"]
    assert "no_samples" in zone_data["missing_info"]
    assert "no_interventions" in zone_data["missing_info"]


# ---------------------------------------------------------------------------
# Intervention overlay tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervention_overlay_empty(db_session, admin_user):
    """Plan with no interventions returns empty list and 0% coverage."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    await db_session.commit()

    result = await generate_intervention_overlay(db_session, plan.id)
    assert result["interventions"] == []
    assert result["coverage_pct"] == 0.0


@pytest.mark.asyncio
async def test_intervention_overlay_with_interventions(db_session, admin_user):
    """Interventions are listed with correct colour coding by status."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    zone = _make_zone(db_session, building.id, name="Zone A")

    _make_intervention(
        db_session,
        building.id,
        intervention_type="removal",
        status="completed",
        zones_affected=[str(zone.id)],
        date_start=date(2024, 6, 1),
    )
    _make_intervention(
        db_session,
        building.id,
        intervention_type="encapsulation",
        status="planned",
        zones_affected=[],
    )
    await db_session.commit()

    result = await generate_intervention_overlay(db_session, plan.id)
    assert len(result["interventions"]) == 2

    by_status = {i["status"]: i for i in result["interventions"]}
    assert by_status["completed"]["color"] == "#2E7D32"
    assert by_status["planned"]["color"] == "#1565C0"

    # Coverage: 1 zone covered out of 1
    assert result["coverage_pct"] == 100.0


@pytest.mark.asyncio
async def test_intervention_overlay_partial_coverage(db_session, admin_user):
    """Coverage is proportional to zones with interventions."""
    building = _make_building(db_session, created_by=admin_user.id)
    plan = _make_plan(db_session, building.id)
    zone_a = _make_zone(db_session, building.id, name="Zone A")
    _make_zone(db_session, building.id, name="Zone B")

    _make_intervention(
        db_session,
        building.id,
        status="completed",
        zones_affected=[str(zone_a.id)],
    )
    await db_session.commit()

    result = await generate_intervention_overlay(db_session, plan.id)
    assert result["coverage_pct"] == 50.0
