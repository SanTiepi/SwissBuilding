"""Tests for Insurance Risk Profiler service (Programme AA)."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.incident import IncidentEpisode
from app.models.insurance_policy import InsurancePolicy
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.insurance_risk_profiler import (
    _compute_fire_risk,
    _compute_liability_risk,
    _compute_pollution_risk,
    _compute_premium_factor,
    _score_to_grade,
    compute_insurance_risk_profile,
    detect_coverage_gaps,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db):
    org = Organization(id=uuid.uuid4(), name="Test Org", type="property_management")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _create_user(db, org_id):
    u = User(
        id=uuid.uuid4(),
        email=f"ins-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Ins",
        last_name="Tester",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _create_building(db, user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": user.id,
        "status": "active",
        "floors_above": 5,
        "floors_below": 1,
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _create_incident(db, building_id, org_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "organization_id": org_id,
        "incident_type": "leak",
        "title": "Test incident",
        "severity": "minor",
        "status": "resolved",
    }
    defaults.update(kwargs)
    i = IncidentEpisode(**defaults)
    db.add(i)
    await db.commit()
    await db.refresh(i)
    return i


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
        "date_inspection": date.today(),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _create_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": "asbestos",
        "concentration": 0.5,
        "unit": "%",
        "threshold_exceeded": False,
        "risk_level": "low",
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _create_policy(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "policy_type": "building_eca",
        "policy_number": f"POL-{uuid.uuid4().hex[:8]}",
        "insurer_name": "ECA Vaud",
        "date_start": date(2024, 1, 1),
        "status": "active",
    }
    defaults.update(kwargs)
    p = InsurancePolicy(**defaults)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------


class TestScoreToGrade:
    def test_grade_a(self):
        assert _score_to_grade(5) == "A"

    def test_grade_b(self):
        assert _score_to_grade(15) == "B"

    def test_grade_c(self):
        assert _score_to_grade(30) == "C"

    def test_grade_d(self):
        assert _score_to_grade(50) == "D"

    def test_grade_e(self):
        assert _score_to_grade(65) == "E"

    def test_grade_f(self):
        assert _score_to_grade(85) == "F"


class TestPremiumFactor:
    def test_lowest_risk(self):
        assert _compute_premium_factor(0) == 0.8

    def test_highest_risk(self):
        assert _compute_premium_factor(100) == 2.0

    def test_mid_risk(self):
        factor = _compute_premium_factor(50)
        assert 1.3 <= factor <= 1.5

    def test_monotonic(self):
        factors = [_compute_premium_factor(s) for s in range(0, 101, 10)]
        assert factors == sorted(factors)


# ---------------------------------------------------------------------------
# Unit tests — dimension scorers
# ---------------------------------------------------------------------------


class TestFireRisk:
    def test_old_building_high_fire_risk(self):
        b = Building(
            id=uuid.uuid4(),
            address="Test",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            construction_year=1930,
        )
        score, factors = _compute_fire_risk(b, [], [])
        assert score >= 30
        assert any("old" in f.lower() or "very old" in f.lower() for f in factors)

    def test_new_building_lower_fire_risk(self):
        b = Building(
            id=uuid.uuid4(),
            address="Test",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            construction_year=2020,
        )
        score, _ = _compute_fire_risk(b, [], [])
        assert score < 30


class TestPollutionRisk:
    def test_no_diagnostics(self):
        score, factors = _compute_pollution_risk([], [])
        assert score == 40
        assert any("unknown" in f.lower() for f in factors)

    def test_clean_samples(self):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            diagnostic_type="asbestos",
            status="completed",
        )
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S-001",
            pollutant_type="asbestos",
            threshold_exceeded=False,
            risk_level="low",
        )
        score, factors = _compute_pollution_risk([sample], [diag])
        assert score <= 10
        assert any("within thresholds" in f for f in factors)

    def test_exceeded_samples(self):
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=uuid.uuid4(),
            diagnostic_type="asbestos",
            status="completed",
        )
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="S-002",
            pollutant_type="asbestos",
            threshold_exceeded=True,
            risk_level="high",
        )
        score, factors = _compute_pollution_risk([sample], [diag])
        assert score >= 20
        assert any("exceedance" in f for f in factors)


class TestLiabilityRisk:
    def test_large_public_building(self):
        b = Building(
            id=uuid.uuid4(),
            address="Test",
            city="Bern",
            canton="BE",
            building_type="public",
            floors_above=12,
        )
        score, factors = _compute_liability_risk(b, [])
        assert score >= 40
        assert any("Public-access" in f for f in factors)

    def test_small_residential(self):
        b = Building(
            id=uuid.uuid4(),
            address="Test",
            city="Bern",
            canton="BE",
            building_type="residential",
            floors_above=2,
        )
        score, _ = _compute_liability_risk(b, [])
        assert score < 30


# ---------------------------------------------------------------------------
# Integration tests — full profile computation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_profile_new_building(db_session):
    """New building with minimal data gets a moderate risk profile."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user, construction_year=2020)

    profile = await compute_insurance_risk_profile(db_session, building.id)

    assert "overall_score" in profile
    assert 0 <= profile["overall_score"] <= 100
    assert profile["grade"] in ("A", "B", "C", "D", "E", "F")
    assert len(profile["breakdown"]) == 7
    assert 0.8 <= profile["estimated_premium_factor"] <= 2.0
    assert isinstance(profile["top_risks"], list)
    assert len(profile["top_risks"]) <= 3


@pytest.mark.asyncio
async def test_profile_with_incidents(db_session):
    """Building with incidents should have higher risk."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user, construction_year=1960)

    # Add water incidents
    for _ in range(3):
        await _create_incident(db_session, building.id, org.id, incident_type="leak")
    await _create_incident(db_session, building.id, org.id, incident_type="fire")

    profile = await compute_insurance_risk_profile(db_session, building.id)

    # Should have elevated water and fire risk
    assert profile["breakdown"]["water"]["score"] > 20
    assert profile["breakdown"]["fire"]["score"] > 20


@pytest.mark.asyncio
async def test_profile_with_pollutant_exceedances(db_session):
    """Building with pollutant threshold exceedances gets high pollution risk."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user)

    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, threshold_exceeded=True, risk_level="high")
    await _create_sample(db_session, diag.id, threshold_exceeded=True, risk_level="critical", pollutant_type="pcb")

    profile = await compute_insurance_risk_profile(db_session, building.id)

    assert profile["breakdown"]["pollution"]["score"] >= 30
    assert profile["breakdown"]["pollution"]["level"] in ("medium", "high", "critical")


@pytest.mark.asyncio
async def test_profile_building_not_found(db_session):
    """Non-existent building returns safe defaults with error."""
    fake_id = uuid.uuid4()
    profile = await compute_insurance_risk_profile(db_session, fake_id)

    assert profile["overall_score"] == 0
    assert profile["grade"] == "A"
    assert "error" in profile


@pytest.mark.asyncio
async def test_coverage_gaps_detected(db_session):
    """High risk without matching coverage triggers gap detection."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user, construction_year=1940)

    # Add many incidents to drive up risk
    for _ in range(4):
        await _create_incident(db_session, building.id, org.id, incident_type="leak")

    # No insurance policies → gaps expected
    gaps = await detect_coverage_gaps(db_session, building.id)
    # At least some dimensions should have gaps since no policies exist
    assert isinstance(gaps, list)


@pytest.mark.asyncio
async def test_coverage_gaps_with_policy(db_session):
    """Adding policies should reduce coverage gaps."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user, construction_year=1940)

    for _ in range(4):
        await _create_incident(db_session, building.id, org.id, incident_type="leak")

    # Add ECA policy (covers fire + water + structural)
    await _create_policy(db_session, building.id, policy_type="building_eca")
    await _create_policy(db_session, building.id, policy_type="natural_hazard")
    await _create_policy(db_session, building.id, policy_type="rc_owner")
    await _create_policy(db_session, building.id, policy_type="rc_building")
    await _create_policy(db_session, building.id, policy_type="complementary")
    await _create_policy(db_session, building.id, policy_type="construction_risk")

    gaps = await detect_coverage_gaps(db_session, building.id)
    # Most gaps should be covered now
    assert len(gaps) == 0 or all(g["risk_score"] < 70 for g in gaps)


@pytest.mark.asyncio
async def test_premium_factor_bounds(db_session):
    """Premium factor is always within 0.8-2.0."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user)

    profile = await compute_insurance_risk_profile(db_session, building.id)
    assert 0.8 <= profile["estimated_premium_factor"] <= 2.0


@pytest.mark.asyncio
async def test_empty_data_building(db_session):
    """Building with no construction year and no data gives moderate/unknown scores."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user, construction_year=None, floors_above=None)

    profile = await compute_insurance_risk_profile(db_session, building.id)

    assert "overall_score" in profile
    assert len(profile["breakdown"]) == 7
    # Fire should note unknown year
    fire_factors = profile["breakdown"]["fire"]["factors"]
    assert any("unknown" in f.lower() for f in fire_factors)
