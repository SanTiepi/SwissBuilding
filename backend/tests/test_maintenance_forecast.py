"""Tests for the Maintenance Forecast service and API."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.zone import Zone
from app.services.maintenance_forecast_service import (
    forecast_building_maintenance,
    forecast_portfolio_maintenance,
    get_maintenance_budget,
    get_upcoming_maintenance,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_intervention(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "asbestos_removal",
        "title": "Test Intervention",
        "status": "completed",
    }
    defaults.update(kwargs)
    i = Intervention(**defaults)
    db.add(i)
    await db.flush()
    return i


async def _create_zone(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "zone_type": "room",
        "name": "Room 1",
    }
    defaults.update(kwargs)
    z = Zone(**defaults)
    db.add(z)
    await db.flush()
    return z


async def _create_element(db, zone_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "zone_id": zone_id,
        "element_type": "wall",
        "name": "Test Wall",
        "condition": "good",
    }
    defaults.update(kwargs)
    e = BuildingElement(**defaults)
    db.add(e)
    await db.flush()
    return e


async def _create_risk_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "overall_risk_level": "low",
    }
    defaults.update(kwargs)
    r = BuildingRiskScore(**defaults)
    db.add(r)
    await db.flush()
    return r


# ── Service Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_minimal_building_no_data(db_session, admin_user):
    """Building with no elements/diagnostics returns minimal forecast."""
    b = await _create_building(db_session, admin_user, construction_year=2010)
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    assert forecast.building_id == b.id
    # 2010 building: no asbestos/PCB renewal needed, but inspection_due (no diagnostics)
    types = {i.item_type for i in forecast.items}
    assert "inspection_due" in types
    assert forecast.total_items == len(forecast.items)


@pytest.mark.asyncio
async def test_nonexistent_building(db_session):
    """Nonexistent building returns empty forecast."""
    forecast = await forecast_building_maintenance(db_session, uuid.uuid4())
    assert forecast.total_items == 0
    assert forecast.items == []


@pytest.mark.asyncio
async def test_diagnostic_renewal_asbestos_pre1991(db_session, admin_user):
    """Pre-1991 building generates asbestos diagnostic renewal item."""
    b = await _create_building(db_session, admin_user, construction_year=1975)
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    asbestos_items = [
        i
        for i in forecast.items
        if i.item_type == "diagnostic_renewal" and i.metadata and i.metadata.get("pollutant") == "asbestos"
    ]
    assert len(asbestos_items) == 1
    item = asbestos_items[0]
    assert item.priority == "high"  # overdue (no previous diagnostic)
    assert item.estimated_cost_chf == 3500.0


@pytest.mark.asyncio
async def test_diagnostic_renewal_pcb_era(db_session, admin_user):
    """Building from 1955-1975 generates PCB diagnostic renewal item."""
    b = await _create_building(db_session, admin_user, construction_year=1965)
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    pcb_items = [
        i
        for i in forecast.items
        if i.item_type == "diagnostic_renewal" and i.metadata and i.metadata.get("pollutant") == "pcb"
    ]
    assert len(pcb_items) == 1
    assert pcb_items[0].estimated_cost_chf == 4000.0


@pytest.mark.asyncio
async def test_diagnostic_renewal_with_recent_diagnostic(db_session, admin_user):
    """Recent asbestos diagnostic sets future renewal date."""
    b = await _create_building(db_session, admin_user, construction_year=1980)
    recent_date = date.today() - timedelta(days=365)
    await _create_diagnostic(db_session, b.id, diagnostic_type="asbestos", date_report=recent_date)
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    asbestos_items = [
        i
        for i in forecast.items
        if i.item_type == "diagnostic_renewal" and i.metadata and i.metadata.get("pollutant") == "asbestos"
    ]
    assert len(asbestos_items) == 1
    item = asbestos_items[0]
    # Next due: recent_date + 3 years -> future
    assert item.estimated_date > date.today()
    assert item.priority == "medium"  # not overdue


@pytest.mark.asyncio
async def test_intervention_followup(db_session, admin_user):
    """Completed intervention generates followup inspection item."""
    b = await _create_building(db_session, admin_user)
    end_date = date.today() - timedelta(days=180)
    await _create_intervention(db_session, b.id, status="completed", date_end=end_date)
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    followup = [i for i in forecast.items if i.item_type == "intervention_followup"]
    assert len(followup) == 1
    assert followup[0].estimated_cost_chf == 1000.0
    assert followup[0].estimated_date == end_date + timedelta(days=365)


@pytest.mark.asyncio
async def test_intervention_planned_no_followup(db_session, admin_user):
    """Planned (not completed) interventions do not generate followup."""
    b = await _create_building(db_session, admin_user)
    await _create_intervention(db_session, b.id, status="planned")
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    followup = [i for i in forecast.items if i.item_type == "intervention_followup"]
    assert len(followup) == 0


@pytest.mark.asyncio
async def test_element_replacement_poor_condition(db_session, admin_user):
    """Element in poor condition generates replacement item."""
    b = await _create_building(db_session, admin_user)
    z = await _create_zone(db_session, b.id)
    await _create_element(db_session, z.id, condition="poor", element_type="pipe", name="Old Pipe")
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    replacement = [i for i in forecast.items if i.item_type == "element_replacement"]
    assert len(replacement) == 1
    assert replacement[0].priority == "high"
    assert replacement[0].estimated_cost_chf == 5000.0  # non-structural


@pytest.mark.asyncio
async def test_element_replacement_structural_cost(db_session, admin_user):
    """Structural elements in poor condition get higher cost estimate."""
    b = await _create_building(db_session, admin_user)
    z = await _create_zone(db_session, b.id)
    await _create_element(db_session, z.id, condition="poor", element_type="structural", name="Load-bearing wall")
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    replacement = [i for i in forecast.items if i.item_type == "element_replacement"]
    assert len(replacement) == 1
    assert replacement[0].estimated_cost_chf == 20000.0


@pytest.mark.asyncio
async def test_element_good_condition_no_replacement(db_session, admin_user):
    """Elements in good condition do not generate replacement items."""
    b = await _create_building(db_session, admin_user)
    z = await _create_zone(db_session, b.id)
    await _create_element(db_session, z.id, condition="good")
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    replacement = [i for i in forecast.items if i.item_type == "element_replacement"]
    assert len(replacement) == 0


@pytest.mark.asyncio
async def test_compliance_check_high_risk(db_session, admin_user):
    """High-risk building generates annual compliance check."""
    b = await _create_building(db_session, admin_user)
    await _create_risk_score(db_session, b.id, overall_risk_level="high")
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    compliance = [i for i in forecast.items if i.item_type == "compliance_check"]
    assert len(compliance) == 1
    assert compliance[0].priority == "medium"
    assert compliance[0].estimated_cost_chf == 1500.0


@pytest.mark.asyncio
async def test_compliance_check_critical_risk(db_session, admin_user):
    """Critical-risk building generates high-priority compliance check."""
    b = await _create_building(db_session, admin_user)
    await _create_risk_score(db_session, b.id, overall_risk_level="critical")
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    compliance = [i for i in forecast.items if i.item_type == "compliance_check"]
    assert len(compliance) == 1
    assert compliance[0].priority == "high"


@pytest.mark.asyncio
async def test_compliance_check_low_risk_none(db_session, admin_user):
    """Low-risk building does not generate compliance check."""
    b = await _create_building(db_session, admin_user)
    await _create_risk_score(db_session, b.id, overall_risk_level="low")
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    compliance = [i for i in forecast.items if i.item_type == "compliance_check"]
    assert len(compliance) == 0


@pytest.mark.asyncio
async def test_inspection_due_no_diagnostic(db_session, admin_user):
    """Building with no diagnostics triggers inspection_due."""
    b = await _create_building(db_session, admin_user, construction_year=2010)
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    inspection = [i for i in forecast.items if i.item_type == "inspection_due"]
    assert len(inspection) == 1
    assert inspection[0].estimated_cost_chf == 3000.0


@pytest.mark.asyncio
async def test_inspection_not_due_recent_diagnostic(db_session, admin_user):
    """Building with recent diagnostic does not trigger inspection_due."""
    b = await _create_building(db_session, admin_user, construction_year=2010)
    await _create_diagnostic(db_session, b.id, date_report=date.today() - timedelta(days=365))
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    inspection = [i for i in forecast.items if i.item_type == "inspection_due"]
    assert len(inspection) == 0


@pytest.mark.asyncio
async def test_cost_estimation_aggregation(db_session, admin_user):
    """Total estimated cost sums all items."""
    b = await _create_building(db_session, admin_user, construction_year=1965)
    await _create_risk_score(db_session, b.id, overall_risk_level="high")
    await db_session.commit()

    forecast = await forecast_building_maintenance(db_session, b.id)
    individual_sum = sum(i.estimated_cost_chf for i in forecast.items if i.estimated_cost_chf)
    assert forecast.total_estimated_cost == individual_sum
    assert forecast.total_estimated_cost > 0


@pytest.mark.asyncio
async def test_budget_yearly_grouping(db_session, admin_user):
    """Budget groups items by year correctly."""
    b = await _create_building(db_session, admin_user, construction_year=2010)
    await db_session.commit()

    budget = await get_maintenance_budget(db_session, b.id, years=3)
    assert budget.building_id == b.id
    assert len(budget.yearly_forecasts) == 3
    for yf in budget.yearly_forecasts:
        assert "year" in yf
        assert "items" in yf
        assert "estimated_cost" in yf


@pytest.mark.asyncio
async def test_budget_3_and_5_year_totals(db_session, admin_user):
    """Budget computes 3-year and 5-year totals."""
    b = await _create_building(db_session, admin_user, construction_year=1965)
    await db_session.commit()

    budget = await get_maintenance_budget(db_session, b.id, years=5)
    assert len(budget.yearly_forecasts) == 5
    # total_5_year should be >= total_3_year
    if budget.total_3_year and budget.total_5_year:
        assert budget.total_5_year >= budget.total_3_year


@pytest.mark.asyncio
async def test_portfolio_aggregation(db_session, admin_user):
    """Portfolio forecast aggregates across multiple buildings."""
    await _create_building(db_session, admin_user, construction_year=1965)
    await _create_building(db_session, admin_user, construction_year=2010, address="Rue Test 2")
    await db_session.commit()

    portfolio = await forecast_portfolio_maintenance(db_session)
    assert portfolio.total_buildings >= 2
    assert portfolio.total_items > 0
    assert len(portfolio.by_type) > 0
    assert len(portfolio.by_priority) > 0


@pytest.mark.asyncio
async def test_upcoming_maintenance_filter(db_session, admin_user):
    """Upcoming maintenance filters to items within N months."""
    b = await _create_building(db_session, admin_user, construction_year=1965)
    await db_session.commit()

    # Get items for next 6 months
    upcoming = await get_upcoming_maintenance(db_session, b.id, months=6)
    cutoff = date.today() + timedelta(days=180)
    for item in upcoming:
        assert item.estimated_date is not None
        assert item.estimated_date <= cutoff

    # Items should be sorted by date
    dates = [i.estimated_date for i in upcoming]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_upcoming_all_12_months(db_session, admin_user):
    """Default 12-month upcoming returns relevant items."""
    b = await _create_building(db_session, admin_user, construction_year=1980)
    await db_session.commit()

    upcoming = await get_upcoming_maintenance(db_session, b.id)
    # Should include at least the overdue asbestos renewal + inspection_due
    assert len(upcoming) >= 1


# ── API Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_maintenance_forecast(client, auth_headers, sample_building):
    """GET /buildings/{id}/maintenance-forecast returns forecast."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/maintenance-forecast",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "items" in data
    assert "total_items" in data
    assert "next_12_months" in data
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_api_maintenance_budget(client, auth_headers, sample_building):
    """GET /buildings/{id}/maintenance-budget returns budget."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/maintenance-budget?years=3",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert len(data["yearly_forecasts"]) == 3


@pytest.mark.asyncio
async def test_api_portfolio_maintenance(client, auth_headers, sample_building):
    """GET /portfolio/maintenance-forecast returns portfolio aggregate."""
    resp = await client.get(
        "/api/v1/portfolio/maintenance-forecast",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_buildings" in data
    assert "total_items" in data
    assert "by_type" in data
    assert "by_priority" in data


@pytest.mark.asyncio
async def test_api_upcoming_maintenance(client, auth_headers, sample_building):
    """GET /buildings/{id}/upcoming-maintenance returns items list."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/upcoming-maintenance?months=6",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_api_unauthorized(client, sample_building):
    """Endpoints require authentication."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/maintenance-forecast",
    )
    assert resp.status_code == 401
