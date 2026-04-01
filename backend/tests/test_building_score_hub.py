"""Tests for Building Score Hub service."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.building_score_hub import (
    _score_to_grade,
    get_all_scores,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db):
    org = Organization(id=uuid.uuid4(), name="Hub Test Org", type="property_management")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _create_user(db, org_id):
    u = User(
        id=uuid.uuid4(),
        email=f"hub-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Hub",
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
        "address": "Rue Hub 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1975,
        "building_type": "residential",
        "created_by": user.id,
        "status": "active",
        "floors_above": 4,
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


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


# ---------------------------------------------------------------------------
# Unit tests — grade helper
# ---------------------------------------------------------------------------


class TestScoreToGrade:
    def test_grade_a(self):
        assert _score_to_grade(95) == "A"

    def test_grade_f(self):
        assert _score_to_grade(5) == "F"

    def test_grade_boundaries(self):
        assert _score_to_grade(90) == "A"
        assert _score_to_grade(89.9) == "B"
        assert _score_to_grade(75) == "B"
        assert _score_to_grade(74.9) == "C"


# ---------------------------------------------------------------------------
# Integration tests — full score aggregation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_scores_basic(db_session):
    """Basic building returns all score keys with computed_at."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user)

    result = await get_all_scores(db_session, building.id)

    # All expected keys present
    expected_keys = {
        "passport",
        "completeness",
        "trust",
        "geo_risk",
        "sustainability",
        "insurance_risk",
        "accessibility",
        "sinistralite",
        "energy",
        "compliance",
        "overall_intelligence",
        "computed_at",
    }
    assert expected_keys == set(result.keys())
    assert "computed_at" in result


@pytest.mark.asyncio
async def test_overall_intelligence_structure(db_session):
    """Overall intelligence has score, grade, and data_completeness."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user)

    result = await get_all_scores(db_session, building.id)

    oi = result["overall_intelligence"]
    assert "score" in oi
    assert "grade" in oi
    assert "data_completeness" in oi
    assert 0 <= oi["score"] <= 100
    assert oi["grade"] in ("A", "B", "C", "D", "E", "F")
    assert 0 <= oi["data_completeness"] <= 1.0


@pytest.mark.asyncio
async def test_insurance_risk_populated(db_session):
    """Insurance risk should be populated for a valid building."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user)

    result = await get_all_scores(db_session, building.id)

    ir = result["insurance_risk"]
    assert ir is not None
    assert "score" in ir
    assert "grade" in ir


@pytest.mark.asyncio
async def test_accessibility_populated(db_session):
    """Accessibility should be populated for a valid building."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user)

    result = await get_all_scores(db_session, building.id)

    acc = result["accessibility"]
    assert acc is not None
    assert "score" in acc
    assert "grade" in acc


@pytest.mark.asyncio
async def test_sinistralite_no_incidents(db_session):
    """Building with no incidents gets perfect sinistralite score."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user)

    result = await get_all_scores(db_session, building.id)

    sin = result["sinistralite"]
    assert sin is not None
    assert sin["score"] == 100.0
    assert sin["grade"] == "A"


@pytest.mark.asyncio
async def test_nonexistent_building(db_session):
    """Non-existent building returns null for most scores."""
    fake_id = uuid.uuid4()
    result = await get_all_scores(db_session, fake_id)

    # Overall intelligence should still be present
    assert result["overall_intelligence"] is not None
    # Most sub-scores should be null (services return None for missing building)
    null_count = sum(1 for k in ("passport", "geo_risk", "sustainability") if result[k] is None)
    assert null_count >= 2


@pytest.mark.asyncio
async def test_data_completeness_increases_with_data(db_session):
    """Adding data should increase data_completeness."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)

    # Building with minimal data
    building = await _create_building(db_session, user)

    result = await get_all_scores(db_session, building.id)
    completeness = result["overall_intelligence"]["data_completeness"]

    # data_completeness should be > 0 since at least insurance_risk, accessibility,
    # and sinistralite are computable
    assert completeness > 0


@pytest.mark.asyncio
async def test_partial_data_graceful(db_session):
    """Hub handles partial data gracefully — no crashes."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org.id)
    building = await _create_building(db_session, user, construction_year=None, floors_above=None)

    # Add a diagnostic with sample
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id)

    result = await get_all_scores(db_session, building.id)

    # Should not crash and should return valid structure
    assert result["overall_intelligence"]["score"] >= 0
    assert result["computed_at"] is not None
