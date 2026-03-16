"""
Tests for Insurance Risk Assessment service and API endpoints.
"""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.schemas.insurance_risk_assessment import InsuranceRiskTier
from app.services.insurance_risk_assessment_service import (
    assess_building_insurance_risk,
    compare_insurance_profiles,
    get_liability_exposure,
    get_portfolio_insurance_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, construction_year=1965, address="Rue Test 1"):
    building = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return building


async def _create_diagnostic(db, building_id, status="completed"):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status=status,
    )
    db.add(diag)
    await db.commit()
    await db.refresh(diag)
    return diag


async def _create_sample(
    db,
    diagnostic_id,
    pollutant_type="asbestos",
    risk_level="high",
    concentration=None,
    material_state=None,
    threshold_exceeded=False,
    unit=None,
):
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        risk_level=risk_level,
        concentration=concentration,
        material_state=material_state,
        threshold_exceeded=threshold_exceeded,
        unit=unit,
    )
    db.add(sample)
    await db.commit()
    await db.refresh(sample)
    return sample


async def _create_intervention(db, building_id, intervention_type="remediation", status="completed"):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=intervention_type,
        title="Remediation",
        status=status,
    )
    db.add(intervention)
    await db.commit()
    await db.refresh(intervention)
    return intervention


async def _create_org_with_user(db):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)

    user = User(
        id=uuid.uuid4(),
        email=f"org-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lg2VEODhCFKJce/jBMNIzfnqrSJGCOyBHMr.3jL.GpnnW",
        first_name="Org",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return org, user


# ---------------------------------------------------------------------------
# Service tests: assess_building_insurance_risk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_standard_tier_clean_building(db_session, admin_user):
    """New building with no pollutants → standard tier."""
    building = await _create_building(db_session, admin_user, construction_year=2020)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", risk_level="low")

    result = await assess_building_insurance_risk(db_session, building.id)
    assert result.risk_tier == InsuranceRiskTier.standard
    assert result.premium_impact_multiplier == 1.0
    assert result.has_diagnostic is True


@pytest.mark.asyncio
async def test_elevated_tier_pre1991_no_diagnostic(db_session, admin_user):
    """Pre-1991 building with no diagnostic → elevated."""
    building = await _create_building(db_session, admin_user, construction_year=1975)

    result = await assess_building_insurance_risk(db_session, building.id)
    assert result.risk_tier == InsuranceRiskTier.elevated
    assert result.premium_impact_multiplier == 1.5
    assert result.has_diagnostic is False


@pytest.mark.asyncio
async def test_uninsurable_friable_asbestos(db_session, admin_user):
    """Friable asbestos → uninsurable."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="asbestos",
        risk_level="critical",
        material_state="friable",
    )

    result = await assess_building_insurance_risk(db_session, building.id)
    assert result.risk_tier == InsuranceRiskTier.uninsurable
    assert result.premium_impact_multiplier == 3.0
    assert len(result.coverage_restrictions) > 0
    assert len(result.required_mitigations) > 0


@pytest.mark.asyncio
async def test_elevated_pcb_above_50(db_session, admin_user):
    """PCB > 50 mg/kg → elevated minimum."""
    building = await _create_building(db_session, admin_user, construction_year=2000)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="pcb",
        risk_level="medium",
        concentration=80.0,
        unit="mg/kg",
    )

    result = await assess_building_insurance_risk(db_session, building.id)
    assert result.risk_tier in (InsuranceRiskTier.elevated, InsuranceRiskTier.high)
    assert result.premium_impact_multiplier >= 1.8


@pytest.mark.asyncio
async def test_high_radon_above_1000(db_session, admin_user):
    """Radon > 1000 Bq/m³ → high risk."""
    building = await _create_building(db_session, admin_user, construction_year=2000)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="radon",
        risk_level="high",
        concentration=1200.0,
        unit="Bq/m3",
    )

    result = await assess_building_insurance_risk(db_session, building.id)
    assert result.risk_tier == InsuranceRiskTier.high
    assert result.premium_impact_multiplier >= 2.2


@pytest.mark.asyncio
async def test_multiple_pollutants_cumulative(db_session, admin_user):
    """Multiple pollutants with issues → cumulative impact."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="asbestos",
        risk_level="high",
        threshold_exceeded=True,
    )
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="pcb",
        risk_level="high",
        concentration=80.0,
        threshold_exceeded=True,
    )
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="lead",
        risk_level="high",
        threshold_exceeded=True,
    )

    result = await assess_building_insurance_risk(db_session, building.id)
    assert result.risk_tier == InsuranceRiskTier.high
    assert result.premium_impact_multiplier >= 2.5


@pytest.mark.asyncio
async def test_post_remediation_returns_standard(db_session, admin_user):
    """Post-remediation with no remaining high risk → standard."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="asbestos",
        risk_level="low",
    )
    await _create_intervention(db_session, building.id)

    result = await assess_building_insurance_risk(db_session, building.id)
    assert result.risk_tier == InsuranceRiskTier.standard
    assert result.premium_impact_multiplier == 1.0


@pytest.mark.asyncio
async def test_building_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await assess_building_insurance_risk(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_critical_risk_level_pollutant(db_session, admin_user):
    """Critical risk level on any pollutant → at least elevated."""
    building = await _create_building(db_session, admin_user, construction_year=2000)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="lead",
        risk_level="critical",
    )

    result = await assess_building_insurance_risk(db_session, building.id)
    assert result.risk_tier in (InsuranceRiskTier.elevated, InsuranceRiskTier.high)
    assert result.premium_impact_multiplier >= 1.7


@pytest.mark.asyncio
async def test_post_1991_no_diagnostic_standard(db_session, admin_user):
    """Post-1991 building without diagnostic → standard (not elevated)."""
    building = await _create_building(db_session, admin_user, construction_year=2005)

    result = await assess_building_insurance_risk(db_session, building.id)
    assert result.risk_tier == InsuranceRiskTier.standard
    assert result.premium_impact_multiplier == 1.0


# ---------------------------------------------------------------------------
# Service tests: get_liability_exposure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_liability_four_categories(db_session, admin_user):
    """Liability exposure returns all 4 categories."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", risk_level="high")

    result = await get_liability_exposure(db_session, building.id)
    category_names = {c.category for c in result.categories}
    assert category_names == {"occupant_health", "worker_safety", "environmental_contamination", "remediation_cost"}


@pytest.mark.asyncio
async def test_liability_friable_asbestos_high_occupant(db_session, admin_user):
    """Friable asbestos → high occupant health score."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="asbestos",
        risk_level="critical",
        material_state="friable",
    )

    result = await get_liability_exposure(db_session, building.id)
    occupant = next(c for c in result.categories if c.category == "occupant_health")
    assert occupant.score >= 0.9
    assert "asbestos" in occupant.contributing_pollutants


@pytest.mark.asyncio
async def test_liability_pcb_environmental(db_session, admin_user):
    """High PCB → high environmental contamination score."""
    building = await _create_building(db_session, admin_user, construction_year=2000)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(
        db_session,
        diag.id,
        pollutant_type="pcb",
        risk_level="high",
        concentration=100.0,
        threshold_exceeded=True,
    )

    result = await get_liability_exposure(db_session, building.id)
    env = next(c for c in result.categories if c.category == "environmental_contamination")
    assert env.score >= 0.8
    assert "pcb" in env.contributing_pollutants


@pytest.mark.asyncio
async def test_liability_clean_building_low_scores(db_session, admin_user):
    """Clean building → low scores across all categories."""
    building = await _create_building(db_session, admin_user, construction_year=2020)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", risk_level="low")

    result = await get_liability_exposure(db_session, building.id)
    for cat in result.categories:
        assert cat.score <= 0.2


@pytest.mark.asyncio
async def test_liability_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await get_liability_exposure(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_liability_remediation_cost_multiple_pollutants(db_session, admin_user):
    """Multiple problematic pollutants → high remediation cost score."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", risk_level="high", threshold_exceeded=True)
    await _create_sample(
        db_session, diag.id, pollutant_type="pcb", risk_level="high", concentration=80.0, threshold_exceeded=True
    )
    await _create_sample(db_session, diag.id, pollutant_type="lead", risk_level="high", threshold_exceeded=True)

    result = await get_liability_exposure(db_session, building.id)
    remediation = next(c for c in result.categories if c.category == "remediation_cost")
    assert remediation.score >= 0.8


# ---------------------------------------------------------------------------
# Service tests: compare_insurance_profiles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_profiles(db_session, admin_user):
    """Compare two buildings with different risk levels."""
    b1 = await _create_building(db_session, admin_user, construction_year=2020, address="Rue A 1")
    diag1 = await _create_diagnostic(db_session, b1.id)
    await _create_sample(db_session, diag1.id, pollutant_type="asbestos", risk_level="low")

    b2 = await _create_building(db_session, admin_user, construction_year=1970, address="Rue B 2")
    diag2 = await _create_diagnostic(db_session, b2.id)
    await _create_sample(
        db_session,
        diag2.id,
        pollutant_type="asbestos",
        risk_level="critical",
        material_state="friable",
    )

    result = await compare_insurance_profiles(db_session, [b1.id, b2.id])
    assert len(result.profiles) == 2
    assert result.best_tier == InsuranceRiskTier.standard
    assert result.worst_tier == InsuranceRiskTier.uninsurable


@pytest.mark.asyncio
async def test_compare_empty_list(db_session):
    """Empty list → empty response."""
    result = await compare_insurance_profiles(db_session, [])
    assert len(result.profiles) == 0


@pytest.mark.asyncio
async def test_compare_nonexistent_building_skipped(db_session, admin_user):
    """Non-existent building IDs are skipped."""
    b1 = await _create_building(db_session, admin_user, construction_year=2020)
    diag = await _create_diagnostic(db_session, b1.id)
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", risk_level="low")

    result = await compare_insurance_profiles(db_session, [b1.id, uuid.uuid4()])
    assert len(result.profiles) == 1


# ---------------------------------------------------------------------------
# Service tests: get_portfolio_insurance_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_summary(db_session):
    """Portfolio summary with mixed risk buildings."""
    org, user = await _create_org_with_user(db_session)

    # Standard building
    b1 = Building(
        id=uuid.uuid4(),
        address="Rue A",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=2020,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db_session.add(b1)
    await db_session.commit()

    diag1 = await _create_diagnostic(db_session, b1.id)
    await _create_sample(db_session, diag1.id, pollutant_type="asbestos", risk_level="low")

    # High risk building
    b2 = Building(
        id=uuid.uuid4(),
        address="Rue B",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db_session.add(b2)
    await db_session.commit()

    diag2 = await _create_diagnostic(db_session, b2.id)
    await _create_sample(
        db_session,
        diag2.id,
        pollutant_type="radon",
        risk_level="high",
        concentration=1500.0,
    )

    result = await get_portfolio_insurance_summary(db_session, org.id)
    assert result.total_buildings == 2
    assert result.assessed_buildings == 2
    assert result.tier_distribution.high >= 1
    assert result.average_premium_multiplier > 1.0


@pytest.mark.asyncio
async def test_portfolio_summary_empty_org(db_session):
    """Empty org → zero buildings."""
    org = Organization(
        id=uuid.uuid4(),
        name="Empty Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()

    result = await get_portfolio_insurance_summary(db_session, org.id)
    assert result.total_buildings == 0
    assert result.average_premium_multiplier == 1.0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_insurance_risk(client, auth_headers, sample_building, db_session):
    """GET /buildings/{id}/insurance-risk returns assessment."""
    # Create a diagnostic + sample so the building has data
    diag = await _create_diagnostic(db_session, sample_building.id)
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", risk_level="low")

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/insurance-risk",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_tier"] == "standard"
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_insurance_risk_not_found(client, auth_headers):
    """GET /buildings/{id}/insurance-risk → 404 for unknown building."""
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/insurance-risk",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_liability_exposure(client, auth_headers, sample_building, db_session):
    """GET /buildings/{id}/liability-exposure returns 4 categories."""
    diag = await _create_diagnostic(db_session, sample_building.id)
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", risk_level="high")

    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/liability-exposure",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["categories"]) == 4


@pytest.mark.asyncio
async def test_api_compare(client, auth_headers, sample_building):
    """POST /insurance/compare returns profiles."""
    resp = await client.post(
        "/api/v1/insurance/compare",
        headers=auth_headers,
        json={"building_ids": [str(sample_building.id)]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["profiles"]) == 1


@pytest.mark.asyncio
async def test_api_unauthorized(client):
    """Endpoints require authentication."""
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/insurance-risk")
    assert resp.status_code == 403
