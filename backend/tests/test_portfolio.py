import uuid
from datetime import date

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample


@pytest.mark.asyncio
async def test_portfolio_metrics_empty_db(client, auth_headers):
    """Test metrics endpoint returns valid structure with empty database."""
    response = await client.get("/api/v1/portfolio/metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_buildings"] == 0
    assert data["risk_distribution"] == {"low": 0, "medium": 0, "high": 0, "critical": 0}
    assert data["completeness_avg"] == 0.0
    assert data["buildings_ready"] == 0
    assert data["buildings_not_ready"] == 0
    assert data["pollutant_prevalence"] == {"asbestos": 0, "pcb": 0, "lead": 0, "hap": 0, "radon": 0}
    assert data["actions_pending"] == 0
    assert data["actions_critical"] == 0
    assert data["recent_diagnostics"] == 0
    assert data["interventions_in_progress"] == 0


@pytest.mark.asyncio
async def test_portfolio_metrics_requires_auth(client):
    """Test metrics endpoint requires authentication."""
    response = await client.get("/api/v1/portfolio/metrics")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_portfolio_metrics_with_buildings(client, auth_headers, db_session, admin_user):
    """Test metrics endpoint with buildings and risk scores."""
    # Create buildings
    building1 = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    building2 = Building(
        id=uuid.uuid4(),
        address="Rue Test 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1975,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add_all([building1, building2])
    await db_session.flush()

    # Create risk scores
    risk1 = BuildingRiskScore(
        building_id=building1.id,
        asbestos_probability=0.85,
        pcb_probability=0.45,
        lead_probability=0.60,
        hap_probability=0.20,
        radon_probability=0.15,
        overall_risk_level="high",
        confidence=0.78,
        factors_json={},
        data_source="model",
    )
    risk2 = BuildingRiskScore(
        building_id=building2.id,
        asbestos_probability=0.30,
        pcb_probability=0.20,
        lead_probability=0.15,
        hap_probability=0.10,
        radon_probability=0.05,
        overall_risk_level="low",
        confidence=0.30,
        factors_json={},
        data_source="model",
    )
    db_session.add_all([risk1, risk2])
    await db_session.flush()

    # Create a diagnostic with a sample
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building1.id,
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="in_progress",
        diagnostician_id=admin_user.id,
        date_inspection=date(2024, 1, 15),
    )
    db_session.add(diag)
    await db_session.flush()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="ECH-001",
        material_category="hard",
        pollutant_type="asbestos",
        unit="percent_weight",
        threshold_exceeded=True,
        concentration=2.5,
    )
    db_session.add(sample)

    # Create an action
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building1.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Test action",
        priority="critical",
        status="open",
    )
    db_session.add(action)

    # Create an intervention
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building1.id,
        intervention_type="renovation",
        title="Test intervention",
        status="in_progress",
    )
    db_session.add(intervention)
    await db_session.commit()

    response = await client.get("/api/v1/portfolio/metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_buildings"] == 2
    assert data["risk_distribution"]["high"] == 1
    assert data["risk_distribution"]["low"] == 1
    assert data["completeness_avg"] > 0
    assert data["buildings_ready"] == 1  # building1 has confidence 0.78 >= 0.7
    assert data["buildings_not_ready"] == 1  # building2 has confidence 0.30 < 0.7
    assert data["pollutant_prevalence"]["asbestos"] == 1
    assert data["actions_pending"] == 1
    assert data["actions_critical"] == 1
    assert data["recent_diagnostics"] == 1
    assert data["interventions_in_progress"] == 1


@pytest.mark.asyncio
async def test_portfolio_metrics_response_structure(client, auth_headers):
    """Test that the response contains all expected fields."""
    response = await client.get("/api/v1/portfolio/metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    expected_keys = {
        "total_buildings",
        "risk_distribution",
        "completeness_avg",
        "buildings_ready",
        "buildings_not_ready",
        "pollutant_prevalence",
        "actions_pending",
        "actions_critical",
        "recent_diagnostics",
        "interventions_in_progress",
    }
    assert set(data.keys()) == expected_keys
