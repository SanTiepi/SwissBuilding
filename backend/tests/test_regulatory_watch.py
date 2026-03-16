"""Tests for the Regulatory Watch service and API."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.regulatory_watch_service import (
    assess_regulatory_impact,
    get_active_regulations,
    get_portfolio_regulatory_exposure,
    simulate_threshold_change,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db: AsyncSession, name: str = "TestOrg") -> Organization:
    org = Organization(id=uuid.uuid4(), name=name, type="diagnostic_lab")
    db.add(org)
    await db.flush()
    return org


async def _create_user(db: AsyncSession, org_id=None) -> User:
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=f"u-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_building(db: AsyncSession, user_id, canton="VD", address="Rue Test 1") -> Building:
    building = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        construction_year=1965,
        building_type="residential",
        created_by=user_id,
        status="active",
    )
    db.add(building)
    await db.flush()
    return building


async def _create_diagnostic(db: AsyncSession, building_id) -> Diagnostic:
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="full",
        status="completed",
    )
    db.add(diag)
    await db.flush()
    return diag


async def _create_sample(
    db: AsyncSession,
    diagnostic_id,
    pollutant_type: str,
    concentration: float,
    unit: str = "mg_per_kg",
) -> Sample:
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit=unit,
    )
    db.add(sample)
    await db.flush()
    return sample


# ===========================================================================
# FN1: get_active_regulations
# ===========================================================================


@pytest.mark.asyncio
async def test_get_active_regulations_returns_all_for_known_canton(db_session):
    regs = await get_active_regulations("VD", db_session)
    assert len(regs) >= 9
    assert all("regulation_name" in r for r in regs)
    assert all("reference" in r for r in regs)
    assert all("domain" in r for r in regs)
    assert all("enforcement_level" in r for r in regs)


@pytest.mark.asyncio
async def test_get_active_regulations_unknown_canton_returns_federal(db_session):
    """Unknown canton still gets federal regs (cantons=None means all)."""
    regs = await get_active_regulations("XX", db_session)
    assert len(regs) >= 9


@pytest.mark.asyncio
async def test_get_active_regulations_case_insensitive(db_session):
    regs_lower = await get_active_regulations("vd", db_session)
    regs_upper = await get_active_regulations("VD", db_session)
    assert len(regs_lower) == len(regs_upper)


@pytest.mark.asyncio
async def test_get_active_regulations_has_correct_domains(db_session):
    regs = await get_active_regulations("VD", db_session)
    domains = {r["domain"] for r in regs}
    assert "asbestos" in domains
    assert "pcb" in domains
    assert "lead" in domains
    assert "radon" in domains


@pytest.mark.asyncio
async def test_get_active_regulations_has_effective_dates(db_session):
    regs = await get_active_regulations("GE", db_session)
    for r in regs:
        assert r["effective_date"] is not None


# ===========================================================================
# FN2: assess_regulatory_impact
# ===========================================================================


@pytest.mark.asyncio
async def test_assess_regulatory_impact_clean_building(db_session):
    """Building with no samples → no gaps."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    await db_session.commit()

    result = await assess_regulatory_impact(building.id, db_session)
    assert result["building_id"] == building.id
    assert result["compliance_gaps"] == []
    assert result["overall_exposure"] == "low"
    assert result["estimated_compliance_cost"] == 0.0


@pytest.mark.asyncio
async def test_assess_regulatory_impact_nonexistent_building(db_session):
    with pytest.raises(ValueError, match="not found"):
        await assess_regulatory_impact(uuid.uuid4(), db_session)


@pytest.mark.asyncio
async def test_assess_regulatory_impact_with_exceeding_sample(db_session):
    """Building with asbestos sample above threshold → gaps detected."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    # Asbestos material_content threshold is 1.0 percent_weight
    await _create_sample(db_session, diag.id, "asbestos", 2.5, "percent_weight")
    await db_session.commit()

    result = await assess_regulatory_impact(building.id, db_session)
    assert len(result["compliance_gaps"]) > 0
    assert result["overall_exposure"] in ("medium", "high")
    assert result["estimated_compliance_cost"] > 0


@pytest.mark.asyncio
async def test_assess_regulatory_impact_below_threshold(db_session):
    """Building with asbestos sample below threshold → no gaps for that reg."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, "asbestos", 0.5, "percent_weight")
    await db_session.commit()

    result = await assess_regulatory_impact(building.id, db_session)
    # Should have applicable regs but no gaps
    assert result["estimated_compliance_cost"] == 0.0
    assert result["overall_exposure"] == "low"


@pytest.mark.asyncio
async def test_assess_regulatory_impact_multi_pollutant(db_session):
    """Multiple pollutants exceeding → high exposure."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, "asbestos", 2.0, "percent_weight")
    await _create_sample(db_session, diag.id, "pcb", 100.0, "mg_per_kg")
    await _create_sample(db_session, diag.id, "lead", 8000.0, "mg_per_kg")
    await db_session.commit()

    result = await assess_regulatory_impact(building.id, db_session)
    assert result["overall_exposure"] == "high"
    assert len(result["compliance_gaps"]) >= 3


@pytest.mark.asyncio
async def test_assess_regulatory_impact_has_applicable_regulations(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, "radon", 500.0, "bq_per_m3")
    await db_session.commit()

    result = await assess_regulatory_impact(building.id, db_session)
    assert len(result["applicable_regulations"]) > 0


# ===========================================================================
# FN3: simulate_threshold_change
# ===========================================================================


@pytest.mark.asyncio
async def test_simulate_threshold_change_no_samples(db_session):
    """Building without samples → compliant both ways."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    await db_session.commit()

    result = await simulate_threshold_change(building.id, "asbestos", 0.5, db_session)
    assert result["currently_compliant"] is True
    assert result["would_be_compliant"] is True
    assert result["affected_samples"] == []
    assert result["additional_remediation_needed"] is False
    assert result["cost_delta"] == 0.0


@pytest.mark.asyncio
async def test_simulate_threshold_change_nonexistent_building(db_session):
    with pytest.raises(ValueError, match="not found"):
        await simulate_threshold_change(uuid.uuid4(), "asbestos", 0.5, db_session)


@pytest.mark.asyncio
async def test_simulate_threshold_tightening_loses_compliance(db_session):
    """Threshold lowered → building goes from compliant to non-compliant."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    # Asbestos threshold=1.0, sample=0.8 → currently compliant
    await _create_sample(db_session, diag.id, "asbestos", 0.8, "percent_weight")
    await db_session.commit()

    # Tighten threshold to 0.5 → now non-compliant
    result = await simulate_threshold_change(building.id, "asbestos", 0.5, db_session)
    assert result["currently_compliant"] is True
    assert result["would_be_compliant"] is False
    assert result["additional_remediation_needed"] is True
    assert result["cost_delta"] > 0


@pytest.mark.asyncio
async def test_simulate_threshold_relaxing_gains_compliance(db_session):
    """Threshold raised → building goes from non-compliant to compliant."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    # Asbestos threshold=1.0, sample=1.5 → currently non-compliant
    await _create_sample(db_session, diag.id, "asbestos", 1.5, "percent_weight")
    await db_session.commit()

    # Relax threshold to 2.0 → now compliant
    result = await simulate_threshold_change(building.id, "asbestos", 2.0, db_session)
    assert result["currently_compliant"] is False
    assert result["would_be_compliant"] is True
    assert result["additional_remediation_needed"] is False
    assert result["cost_delta"] == 0.0


@pytest.mark.asyncio
async def test_simulate_threshold_change_returns_affected_samples(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    s1 = await _create_sample(db_session, diag.id, "pcb", 40.0, "mg_per_kg")
    s2 = await _create_sample(db_session, diag.id, "pcb", 60.0, "mg_per_kg")
    await db_session.commit()

    # Tighten PCB from 50 to 30 → both affected
    result = await simulate_threshold_change(building.id, "pcb", 30.0, db_session)
    sample_ids = {s["sample_id"] for s in result["affected_samples"]}
    assert s1.id in sample_ids
    assert s2.id in sample_ids


@pytest.mark.asyncio
async def test_simulate_threshold_change_different_pollutant(db_session):
    """Simulate change for pollutant with no samples → stays compliant."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, "asbestos", 2.0, "percent_weight")
    await db_session.commit()

    result = await simulate_threshold_change(building.id, "lead", 1000.0, db_session)
    assert result["currently_compliant"] is True
    assert result["would_be_compliant"] is True
    assert result["affected_samples"] == []


@pytest.mark.asyncio
async def test_simulate_threshold_change_pollutant_type_normalized(db_session):
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, "asbestos", 2.0, "percent_weight")
    await db_session.commit()

    result = await simulate_threshold_change(building.id, "ASBESTOS", 0.5, db_session)
    assert result["pollutant_type"] == "asbestos"
    assert result["would_be_compliant"] is False


# ===========================================================================
# FN4: get_portfolio_regulatory_exposure
# ===========================================================================


@pytest.mark.asyncio
async def test_portfolio_exposure_empty_org(db_session):
    """Org with no buildings → zeros."""
    org = await _create_org(db_session)
    await db_session.commit()

    result = await get_portfolio_regulatory_exposure(org.id, db_session)
    assert result["org_id"] == org.id
    assert result["buildings_with_gaps"] == 0
    assert result["total_compliance_cost"] == 0.0
    assert result["most_impacted_buildings"] == []


@pytest.mark.asyncio
async def test_portfolio_exposure_with_clean_buildings(db_session):
    """Org with buildings but no samples → no gaps."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)
    await _create_building(db_session, user.id)
    await _create_building(db_session, user.id, address="Rue Test 2")
    await db_session.commit()

    result = await get_portfolio_regulatory_exposure(org.id, db_session)
    assert result["buildings_with_gaps"] == 0
    assert result["total_compliance_cost"] == 0.0


@pytest.mark.asyncio
async def test_portfolio_exposure_with_non_compliant_building(db_session):
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, "asbestos", 5.0, "percent_weight")
    await db_session.commit()

    result = await get_portfolio_regulatory_exposure(org.id, db_session)
    assert result["buildings_with_gaps"] >= 1
    assert result["total_compliance_cost"] > 0
    assert len(result["most_impacted_buildings"]) >= 1


@pytest.mark.asyncio
async def test_portfolio_exposure_regulations_tracked(db_session):
    org = await _create_org(db_session)
    await db_session.commit()

    result = await get_portfolio_regulatory_exposure(org.id, db_session)
    assert result["regulations_tracked"] >= 9


@pytest.mark.asyncio
async def test_portfolio_exposure_by_domain(db_session):
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)
    building = await _create_building(db_session, user.id)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, "asbestos", 5.0, "percent_weight")
    await _create_sample(db_session, diag.id, "pcb", 100.0, "mg_per_kg")
    await db_session.commit()

    result = await get_portfolio_regulatory_exposure(org.id, db_session)
    domains = {e["domain"] for e in result["exposure_by_domain"]}
    assert "asbestos" in domains
    assert "pcb" in domains


@pytest.mark.asyncio
async def test_portfolio_most_impacted_sorted_by_gap_count(db_session):
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    # Building 1: 1 pollutant issue
    b1 = await _create_building(db_session, user.id, address="Rue A 1")
    d1 = await _create_diagnostic(db_session, b1.id)
    await _create_sample(db_session, d1.id, "asbestos", 3.0, "percent_weight")

    # Building 2: 2 pollutant issues
    b2 = await _create_building(db_session, user.id, address="Rue B 2")
    d2 = await _create_diagnostic(db_session, b2.id)
    await _create_sample(db_session, d2.id, "asbestos", 3.0, "percent_weight")
    await _create_sample(db_session, d2.id, "pcb", 100.0, "mg_per_kg")
    await db_session.commit()

    result = await get_portfolio_regulatory_exposure(org.id, db_session)
    impacted = result["most_impacted_buildings"]
    assert len(impacted) >= 2
    # First entry should have more gaps than second
    assert impacted[0]["gap_count"] >= impacted[1]["gap_count"]


# ===========================================================================
# API endpoint tests
# ===========================================================================


@pytest.mark.asyncio
async def test_api_list_regulations(client, auth_headers):
    resp = await client.get("/api/v1/regulatory-watch/regulations?canton=VD", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["canton"] == "VD"
    assert len(data["regulations"]) >= 9


@pytest.mark.asyncio
async def test_api_list_regulations_missing_canton(client, auth_headers):
    resp = await client.get("/api/v1/regulatory-watch/regulations", headers=auth_headers)
    assert resp.status_code == 422  # validation error


@pytest.mark.asyncio
async def test_api_building_impact_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/regulatory-watch/buildings/{fake_id}/impact", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_simulate_threshold_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/regulatory-watch/buildings/{fake_id}/simulate?pollutant_type=asbestos&new_threshold=0.5",
        headers=auth_headers,
    )
    assert resp.status_code == 404
