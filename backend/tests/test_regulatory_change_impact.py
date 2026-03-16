"""Tests for the Regulatory Change Impact Analyzer."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.regulatory_change_impact_service import (
    analyze_regulation_impact,
    forecast_compliance_risk,
    get_regulatory_sensitivity,
    simulate_threshold_change,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def buildings_with_samples(db_session, admin_user):
    """Create 3 buildings with samples at various pollutant levels."""
    buildings = []
    for _i, (addr, city, canton) in enumerate(
        [
            ("Rue du Lac 1", "Lausanne", "VD"),
            ("Bahnhofstrasse 5", "Zurich", "ZH"),
            ("Route de Genève 10", "Nyon", "VD"),
        ]
    ):
        b = Building(
            id=uuid.uuid4(),
            address=addr,
            city=city,
            canton=canton,
            postal_code="1000",
            construction_year=1970,
            building_type="residential",
            created_by=admin_user.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)

    await db_session.flush()

    # Create diagnostics and samples
    samples_data = [
        # Building 0: PCB at 40 mg/kg (below 50 threshold), radon at 250 Bq/m3 (below 300)
        (buildings[0], "pcb", 40.0, "mg/kg"),
        (buildings[0], "radon", 250.0, "Bq/m3"),
        # Building 1: PCB at 60 mg/kg (above 50), radon at 280 Bq/m3 (below 300)
        (buildings[1], "pcb", 60.0, "mg/kg"),
        (buildings[1], "radon", 280.0, "Bq/m3"),
        # Building 2: PCB at 45 mg/kg (below 50), lead at 4500 mg/kg (below 5000)
        (buildings[2], "pcb", 45.0, "mg/kg"),
        (buildings[2], "lead", 4500.0, "mg/kg"),
    ]

    for building, pollutant, conc, unit in samples_data:
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="full",
            status="completed",
        )
        db_session.add(diag)
        await db_session.flush()

        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-{uuid.uuid4().hex[:6]}",
            pollutant_type=pollutant,
            concentration=conc,
            unit=unit,
        )
        db_session.add(sample)

    await db_session.commit()
    return buildings


# ---------------------------------------------------------------------------
# Service tests: simulate_threshold_change
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_simulate_threshold_no_change(db_session, buildings_with_samples):
    """When new threshold equals current, no new non-compliant buildings."""
    result = await simulate_threshold_change(db_session, pollutant="pcb", new_threshold=50.0)
    assert result["current_threshold"] == 50.0
    assert result["new_threshold"] == 50.0
    assert result["pollutant"] == "pcb"
    assert result["newly_non_compliant"] == 0


@pytest.mark.asyncio
async def test_simulate_threshold_stricter(db_session, buildings_with_samples):
    """Lowering PCB threshold from 50 to 42 should catch building 2 (45 mg/kg)."""
    result = await simulate_threshold_change(db_session, pollutant="pcb", new_threshold=42.0)
    assert result["currently_non_compliant"] == 1  # building 1 (60 mg/kg)
    assert result["newly_non_compliant"] == 1  # building 2 (45 mg/kg)
    assert result["total_non_compliant_after"] == 2


@pytest.mark.asyncio
async def test_simulate_threshold_very_strict(db_session, buildings_with_samples):
    """Lowering PCB to 30 should catch all 3 buildings."""
    result = await simulate_threshold_change(db_session, pollutant="pcb", new_threshold=30.0)
    assert result["total_non_compliant_after"] == 3
    assert result["newly_non_compliant"] == 2  # buildings 0 and 2


@pytest.mark.asyncio
async def test_simulate_threshold_looser(db_session, buildings_with_samples):
    """Raising threshold should not create new non-compliant buildings."""
    result = await simulate_threshold_change(db_session, pollutant="pcb", new_threshold=100.0)
    assert result["newly_non_compliant"] == 0
    assert result["total_non_compliant_after"] == 0


@pytest.mark.asyncio
async def test_simulate_threshold_radon(db_session, buildings_with_samples):
    """Lowering radon reference from 300 to 260 should catch building 1 (280)."""
    result = await simulate_threshold_change(
        db_session,
        pollutant="radon",
        new_threshold=260.0,
        measurement_type="reference_value",
    )
    assert result["newly_non_compliant"] == 1
    assert result["unit"] == "bq_per_m3"


@pytest.mark.asyncio
async def test_simulate_invalid_pollutant(db_session, buildings_with_samples):
    """Should raise ValueError for unknown pollutant/measurement_type combo."""
    with pytest.raises(ValueError, match="No threshold found"):
        await simulate_threshold_change(
            db_session,
            pollutant="unknown_stuff",
            new_threshold=10.0,
        )


@pytest.mark.asyncio
async def test_simulate_affected_buildings_details(db_session, buildings_with_samples):
    """Affected buildings should contain correct details."""
    result = await simulate_threshold_change(db_session, pollutant="pcb", new_threshold=42.0)
    affected = result["affected_buildings"]
    assert len(affected) >= 2
    for ab in affected:
        assert "building_id" in ab
        assert "address" in ab
        assert "margin_percent" in ab
        assert ab["current_threshold"] == 50.0
        assert ab["new_threshold"] == 42.0


@pytest.mark.asyncio
async def test_simulate_cost_estimation(db_session, buildings_with_samples):
    """Estimated cost should be positive when there are newly non-compliant buildings."""
    result = await simulate_threshold_change(db_session, pollutant="pcb", new_threshold=42.0)
    assert result["estimated_additional_remediation_cost_chf"] > 0


@pytest.mark.asyncio
async def test_simulate_no_samples(db_session, admin_user):
    """When no buildings have samples, result should be zero impact."""
    result = await simulate_threshold_change(db_session, pollutant="pcb", new_threshold=30.0)
    assert result["total_buildings_analyzed"] == 0
    assert result["newly_non_compliant"] == 0


# ---------------------------------------------------------------------------
# Service tests: analyze_regulation_impact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_change_single(db_session, buildings_with_samples):
    """Single change in multi-analysis should match single simulation."""
    result = await analyze_regulation_impact(
        db_session,
        [{"pollutant": "pcb", "new_threshold": 42.0}],
    )
    assert len(result["changes"]) == 1
    assert result["buildings_affected_by_any_change"] >= 2


@pytest.mark.asyncio
async def test_multi_change_combined(db_session, buildings_with_samples):
    """Two changes should report cross-impact correctly."""
    result = await analyze_regulation_impact(
        db_session,
        [
            {"pollutant": "pcb", "new_threshold": 42.0},
            {"pollutant": "radon", "new_threshold": 260.0, "measurement_type": "reference_value"},
        ],
    )
    assert len(result["changes"]) == 2
    assert result["total_estimated_cost_chf"] > 0
    assert result["buildings_affected_by_any_change"] >= 2


@pytest.mark.asyncio
async def test_multi_change_overlap(db_session, buildings_with_samples):
    """Buildings affected by multiple changes should be counted."""
    result = await analyze_regulation_impact(
        db_session,
        [
            {"pollutant": "pcb", "new_threshold": 30.0},
            {"pollutant": "radon", "new_threshold": 200.0, "measurement_type": "reference_value"},
        ],
    )
    # Building 1 has both PCB (60) and radon (280) — should be in multiple
    assert result["buildings_affected_by_multiple_changes"] >= 1


# ---------------------------------------------------------------------------
# Service tests: get_regulatory_sensitivity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sensitivity_existing_building(db_session, buildings_with_samples):
    """Sensitivity for a building with PCB at 40 (threshold 50)."""
    building = buildings_with_samples[0]
    result = await get_regulatory_sensitivity(db_session, building.id)

    assert result["building_id"] == building.id
    assert result["address"] == "Rue du Lac 1"
    assert len(result["sensitivities"]) > 0

    # Find PCB material_content sensitivity
    pcb_sens = next(
        (s for s in result["sensitivities"] if s["pollutant"] == "pcb" and s["measurement_type"] == "material_content"),
        None,
    )
    assert pcb_sens is not None
    assert pcb_sens["is_currently_compliant"] is True
    assert pcb_sens["margin_percent"] == 20.0  # (50-40)/50*100 = 20%
    # 10% drop: threshold becomes 45 → 40 < 45, still compliant
    assert pcb_sens["non_compliant_if_threshold_drops_10_pct"] is False
    # 20% drop: threshold becomes 40 → 40 >= 40, non-compliant
    assert pcb_sens["non_compliant_if_threshold_drops_20_pct"] is True


@pytest.mark.asyncio
async def test_sensitivity_non_compliant_building(db_session, buildings_with_samples):
    """Building 1 has PCB at 60 (above 50) — should show negative margin."""
    building = buildings_with_samples[1]
    result = await get_regulatory_sensitivity(db_session, building.id)

    pcb_sens = next(
        (s for s in result["sensitivities"] if s["pollutant"] == "pcb" and s["measurement_type"] == "material_content"),
        None,
    )
    assert pcb_sens is not None
    assert pcb_sens["is_currently_compliant"] is False
    assert pcb_sens["margin_percent"] < 0  # Already over threshold


@pytest.mark.asyncio
async def test_sensitivity_not_found(db_session, admin_user):
    """Should raise ValueError for non-existent building."""
    with pytest.raises(ValueError, match="not found"):
        await get_regulatory_sensitivity(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_sensitivity_overall_vulnerability(db_session, buildings_with_samples):
    """Overall vulnerability should be a valid level."""
    building = buildings_with_samples[0]
    result = await get_regulatory_sensitivity(db_session, building.id)
    assert result["overall_vulnerability"] in {"low", "medium", "high", "critical"}


# ---------------------------------------------------------------------------
# Service tests: forecast_compliance_risk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_basic(db_session, buildings_with_samples):
    """Forecast should list buildings ranked by vulnerability."""
    result = await forecast_compliance_risk(db_session)
    assert result["buildings_with_samples"] == 3
    assert result["currently_non_compliant"] >= 1  # Building 1 has PCB > 50
    assert len(result["vulnerable_buildings"]) == 3
    # Most vulnerable should be first
    scores = [vb["vulnerability_score"] for vb in result["vulnerable_buildings"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_forecast_risk_summary(db_session, buildings_with_samples):
    """Risk summary should have valid buckets."""
    result = await forecast_compliance_risk(db_session)
    assert set(result["risk_summary"].keys()) == {"low", "medium", "high", "critical"}
    total = sum(result["risk_summary"].values())
    assert total == len(result["vulnerable_buildings"])


@pytest.mark.asyncio
async def test_forecast_empty_portfolio(db_session, admin_user):
    """Empty portfolio should return zeros."""
    result = await forecast_compliance_risk(db_session)
    assert result["buildings_with_samples"] == 0
    assert result["currently_non_compliant"] == 0
    assert len(result["vulnerable_buildings"]) == 0


@pytest.mark.asyncio
async def test_forecast_vulnerability_score_range(db_session, buildings_with_samples):
    """Vulnerability scores should be between 0 and 100."""
    result = await forecast_compliance_risk(db_session)
    for vb in result["vulnerable_buildings"]:
        assert 0 <= vb["vulnerability_score"] <= 100


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_simulate_threshold(client, auth_headers, buildings_with_samples):
    """POST /api/v1/regulatory-impact/simulate-threshold should work."""
    resp = await client.post(
        "/api/v1/regulatory-impact/simulate-threshold",
        json={"pollutant": "pcb", "new_threshold": 42.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pollutant"] == "pcb"
    assert data["new_threshold"] == 42.0
    assert "affected_buildings" in data


@pytest.mark.asyncio
async def test_api_simulate_threshold_bad_pollutant(client, auth_headers):
    """POST with invalid pollutant should return 400."""
    resp = await client.post(
        "/api/v1/regulatory-impact/simulate-threshold",
        json={"pollutant": "kryptonite", "new_threshold": 10.0},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_multi_change(client, auth_headers, buildings_with_samples):
    """POST /api/v1/regulatory-impact/analyze-multi-change should work."""
    resp = await client.post(
        "/api/v1/regulatory-impact/analyze-multi-change",
        json={
            "changes": [
                {"pollutant": "pcb", "new_threshold": 42.0},
                {"pollutant": "radon", "measurement_type": "reference_value", "new_threshold": 260.0},
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["changes"]) == 2
    assert "total_estimated_cost_chf" in data


@pytest.mark.asyncio
async def test_api_sensitivity(client, auth_headers, buildings_with_samples):
    """GET /api/v1/buildings/{id}/regulatory-sensitivity should work."""
    building_id = str(buildings_with_samples[0].id)
    resp = await client.get(
        f"/api/v1/buildings/{building_id}/regulatory-sensitivity",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == building_id
    assert "sensitivities" in data


@pytest.mark.asyncio
async def test_api_sensitivity_not_found(client, auth_headers):
    """GET with non-existent building should return 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/buildings/{fake_id}/regulatory-sensitivity",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_compliance_forecast(client, auth_headers, buildings_with_samples):
    """GET /api/v1/regulatory-impact/compliance-forecast should work."""
    resp = await client.get(
        "/api/v1/regulatory-impact/compliance-forecast",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "vulnerable_buildings" in data
    assert "risk_summary" in data


@pytest.mark.asyncio
async def test_api_unauthenticated(client):
    """Endpoints should require auth."""
    resp = await client.get("/api/v1/regulatory-impact/compliance-forecast")
    assert resp.status_code == 403
