"""Tests for the Environmental Impact service and API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.environmental_impact_service import (
    assess_environmental_impact,
    calculate_green_building_score,
    estimate_remediation_environmental_footprint,
    get_portfolio_environmental_report,
)

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def env_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="envtest@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lz0YKMm0F5x0aO9GQH2VG1J5E5E0Uu7yFn5K6AKz5cXS",
        first_name="Env",
        last_name="Tester",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def env_headers(env_user):
    payload = {
        "sub": str(env_user.id),
        "email": env_user.email,
        "role": env_user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def env_building(db_session, env_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Verte 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=env_user.id,
        status="active",
        surface_area_m2=500.0,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def env_diagnostic(db_session, env_building, env_user):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=env_building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=env_user.id,
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(diag)
    return diag


@pytest.fixture
async def positive_samples(db_session, env_diagnostic):
    samples = []
    for pt in ["asbestos", "pcb", "lead"]:
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=env_diagnostic.id,
            sample_number=f"S-{pt[:3].upper()}-001",
            pollutant_type=pt,
            threshold_exceeded=True,
            risk_level="high",
        )
        db_session.add(s)
        samples.append(s)
    await db_session.commit()
    for s in samples:
        await db_session.refresh(s)
    return samples


@pytest.fixture
async def negative_samples(db_session, env_diagnostic):
    samples = []
    for pt in ["asbestos", "pcb"]:
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=env_diagnostic.id,
            sample_number=f"S-{pt[:3].upper()}-NEG",
            pollutant_type=pt,
            threshold_exceeded=False,
            risk_level="low",
        )
        db_session.add(s)
        samples.append(s)
    await db_session.commit()
    for s in samples:
        await db_session.refresh(s)
    return samples


@pytest.fixture
async def completed_remediation(db_session, env_building, env_user):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=env_building.id,
        intervention_type="asbestos_removal",
        title="Asbestos removal phase 1",
        status="completed",
        date_end=datetime.now(UTC).date(),
        created_by=env_user.id,
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(intervention)
    return intervention


@pytest.fixture
async def env_org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Green Corp",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


# ---------------------------------------------------------------------------
# Service-level tests: assess_environmental_impact
# ---------------------------------------------------------------------------


async def test_assess_no_pollutants(db_session, env_building):
    result = await assess_environmental_impact(db_session, env_building.id)
    assert result.building_id == env_building.id
    assert result.overall_level == "low"
    assert result.soil_contamination.level == "low"
    assert result.water_table_risk.level == "low"


async def test_assess_with_pollutants(db_session, env_building, positive_samples):
    result = await assess_environmental_impact(db_session, env_building.id)
    assert result.building_id == env_building.id
    # With asbestos, pcb, lead detected, air quality should be significant
    assert result.air_quality_impact.score > 0.0
    assert result.overall_level in ("medium", "high")


async def test_assess_building_not_found(db_session):
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        await assess_environmental_impact(db_session, fake_id)


async def test_assess_categories_have_justification(db_session, env_building, positive_samples):
    result = await assess_environmental_impact(db_session, env_building.id)
    for cat in [
        result.soil_contamination,
        result.water_table_risk,
        result.air_quality_impact,
        result.neighborhood_exposure,
    ]:
        assert len(cat.justification) > 0


# ---------------------------------------------------------------------------
# Service-level tests: estimate_remediation_environmental_footprint
# ---------------------------------------------------------------------------


async def test_footprint_no_samples(db_session, env_building):
    result = await estimate_remediation_environmental_footprint(db_session, env_building.id)
    assert result.building_id == env_building.id
    assert result.total_remediation_co2_kg == 0.0
    assert result.dust_fiber_release_risk == "low"


async def test_footprint_with_positive_samples(db_session, env_building, positive_samples):
    result = await estimate_remediation_environmental_footprint(db_session, env_building.id)
    assert result.total_remediation_co2_kg > 0.0
    assert result.waste_transport_co2_kg > 0.0
    assert result.disposal_emissions_co2_kg > 0.0
    assert result.dust_fiber_release_risk == "high"  # asbestos present
    assert result.temporary_contamination_risk == "medium"  # 3 samples


async def test_footprint_net_balance(db_session, env_building, positive_samples):
    result = await estimate_remediation_environmental_footprint(db_session, env_building.id)
    expected_net = result.avoided_long_term_co2_kg - result.total_remediation_co2_kg
    assert abs(result.net_environmental_balance_co2_kg - expected_net) < 0.01


async def test_footprint_emission_details(db_session, env_building, positive_samples):
    result = await estimate_remediation_environmental_footprint(db_session, env_building.id)
    assert len(result.emission_details) == 2
    sources = {d.source for d in result.emission_details}
    assert "waste_transport" in sources
    assert "waste_disposal" in sources


# ---------------------------------------------------------------------------
# Service-level tests: calculate_green_building_score
# ---------------------------------------------------------------------------


async def test_green_score_clean_building(db_session, env_building):
    result = await calculate_green_building_score(db_session, env_building.id)
    assert result.building_id == env_building.id
    assert 0 <= result.overall_score <= 100
    assert result.grade in ("A", "B", "C", "D", "E")


async def test_green_score_with_pollutants(db_session, env_building, positive_samples):
    result = await calculate_green_building_score(db_session, env_building.id)
    # All samples positive => low pollutant score
    pollutant_sub = next(s for s in result.sub_categories if s.name == "pollutant_free_status")
    assert pollutant_sub.score == 0.0


async def test_green_score_with_remediation(db_session, env_building, positive_samples, completed_remediation):
    result = await calculate_green_building_score(db_session, env_building.id)
    remediation_sub = next(s for s in result.sub_categories if s.name == "completed_remediations")
    assert remediation_sub.score > 0.0


async def test_green_score_subcategories_count(db_session, env_building):
    result = await calculate_green_building_score(db_session, env_building.id)
    assert len(result.sub_categories) == 4


async def test_green_score_recommendations_polluted(db_session, env_building, positive_samples):
    result = await calculate_green_building_score(db_session, env_building.id)
    assert any("remediation" in r.lower() for r in result.recommendations)


async def test_green_score_negative_samples(db_session, env_building, negative_samples):
    result = await calculate_green_building_score(db_session, env_building.id)
    pollutant_sub = next(s for s in result.sub_categories if s.name == "pollutant_free_status")
    assert pollutant_sub.score == 100.0  # all clean


# ---------------------------------------------------------------------------
# Service-level tests: get_portfolio_environmental_report
# ---------------------------------------------------------------------------


async def test_portfolio_report_empty(db_session):
    org_id = uuid.uuid4()
    result = await get_portfolio_environmental_report(db_session, org_id)
    assert result.total_buildings == 0
    assert result.avg_green_score == 0.0


async def test_portfolio_report_all_buildings(db_session, env_building):
    result = await get_portfolio_environmental_report(db_session, None)
    assert result.total_buildings >= 1
    assert result.avg_green_score > 0.0


async def test_portfolio_report_grade_distribution(db_session, env_building):
    result = await get_portfolio_environmental_report(db_session, None)
    assert isinstance(result.grade_distribution, dict)
    total_in_dist = sum(result.grade_distribution.values())
    assert total_in_dist == result.total_buildings


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


async def test_api_environmental_impact(client, env_headers, env_building):
    resp = await client.get(f"/api/v1/buildings/{env_building.id}/environmental-impact", headers=env_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(env_building.id)
    assert "soil_contamination" in data


async def test_api_environmental_impact_404(client, env_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/environmental-impact", headers=env_headers)
    assert resp.status_code == 404


async def test_api_remediation_footprint(client, env_headers, env_building):
    resp = await client.get(f"/api/v1/buildings/{env_building.id}/remediation-footprint", headers=env_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(env_building.id)
    assert "total_remediation_co2_kg" in data


async def test_api_green_score(client, env_headers, env_building):
    resp = await client.get(f"/api/v1/buildings/{env_building.id}/green-score", headers=env_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(env_building.id)
    assert "overall_score" in data
    assert "sub_categories" in data


async def test_api_portfolio_environmental_report(client, env_headers, env_building):
    resp = await client.get("/api/v1/portfolio/environmental-report", headers=env_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_buildings"] >= 1


async def test_api_portfolio_with_org_filter(client, env_headers):
    org_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/portfolio/environmental-report?org_id={org_id}", headers=env_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_buildings"] == 0


async def test_api_unauthenticated(client, env_building):
    resp = await client.get(f"/api/v1/buildings/{env_building.id}/environmental-impact")
    assert resp.status_code in (401, 403)
