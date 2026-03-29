"""Tests for the Recommendation Engine."""

import uuid

import pytest

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_PRIORITY_HIGH,
    ACTION_PRIORITY_LOW,
    ACTION_PRIORITY_MEDIUM,
    ACTION_SOURCE_DIAGNOSTIC,
    ACTION_STATUS_DONE,
    ACTION_STATUS_OPEN,
    ACTION_TYPE_DOCUMENTATION,
    ACTION_TYPE_REMEDIATION,
)
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.readiness_assessment import ReadinessAssessment
from app.models.unknown_issue import UnknownIssue
from app.services.recommendation_engine import generate_recommendations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_action(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "source_type": ACTION_SOURCE_DIAGNOSTIC,
        "action_type": ACTION_TYPE_REMEDIATION,
        "title": "Asbestos remediation required",
        "priority": ACTION_PRIORITY_HIGH,
        "status": ACTION_STATUS_OPEN,
        "metadata_json": {"pollutant_type": "asbestos"},
    }
    defaults.update(kwargs)
    a = ActionItem(**defaults)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def _make_unknown(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "unknown_type": "missing_diagnostic",
        "severity": "high",
        "status": "open",
        "title": "Missing PCB diagnostic",
        "blocks_readiness": True,
    }
    defaults.update(kwargs)
    u = UnknownIssue(**defaults)
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _make_readiness(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "readiness_type": "safe_to_start",
        "status": "blocked",
        "checks_json": [
            {
                "id": "completed_diagnostic",
                "label": "Completed diagnostic",
                "status": "fail",
                "detail": "No completed diagnostic found",
                "legal_basis": "OTConst Art. 60a",
            }
        ],
        "blockers_json": ["No completed diagnostic found"],
    }
    defaults.update(kwargs)
    r = ReadinessAssessment(**defaults)
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def _make_trust_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "overall_score": 0.4,
        "percent_proven": 0.2,
        "percent_inferred": 0.1,
        "percent_declared": 0.4,
        "percent_obsolete": 0.2,
        "percent_contradictory": 0.1,
        "total_data_points": 20,
        "proven_count": 4,
        "inferred_count": 2,
        "declared_count": 8,
        "obsolete_count": 4,
        "contradictory_count": 2,
    }
    defaults.update(kwargs)
    t = BuildingTrustScore(**defaults)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_building_returns_no_recommendations(db_session, admin_user):
    """A building with no data should return an empty list."""
    building = await _make_building(db_session, admin_user.id)
    recs = await generate_recommendations(db_session, building.id)
    assert recs == []


@pytest.mark.asyncio
async def test_nonexistent_building_returns_empty(db_session):
    """A non-existent building returns empty list."""
    recs = await generate_recommendations(db_session, uuid.uuid4())
    assert recs == []


@pytest.mark.asyncio
async def test_open_actions_generate_recommendations(db_session, admin_user):
    """Open actions should produce recommendations."""
    building = await _make_building(db_session, admin_user.id)
    await _make_action(db_session, building.id)

    recs = await generate_recommendations(db_session, building.id)
    assert len(recs) == 1
    assert recs[0]["source"] == "action_generator"
    assert recs[0]["priority"] == 2  # high → 2
    assert recs[0]["category"] == "remediation"
    assert recs[0]["cost_estimate"] is not None
    assert recs[0]["cost_estimate"]["min"] == 15000
    assert recs[0]["cost_estimate"]["currency"] == "CHF"


@pytest.mark.asyncio
async def test_done_actions_not_included(db_session, admin_user):
    """Done actions should not appear in recommendations."""
    building = await _make_building(db_session, admin_user.id)
    await _make_action(db_session, building.id, status=ACTION_STATUS_DONE)

    recs = await generate_recommendations(db_session, building.id)
    assert len(recs) == 0


@pytest.mark.asyncio
async def test_blocked_readiness_generates_recommendations(db_session, admin_user):
    """Blocked readiness checks should generate compliance recommendations."""
    building = await _make_building(db_session, admin_user.id)
    await _make_readiness(db_session, building.id)

    recs = await generate_recommendations(db_session, building.id)
    assert len(recs) >= 1
    readiness_recs = [r for r in recs if r["source"] == "readiness_reasoner"]
    assert len(readiness_recs) == 1
    assert readiness_recs[0]["category"] == "compliance"
    assert "OTConst" in readiness_recs[0]["why"]


@pytest.mark.asyncio
async def test_open_unknowns_generate_recommendations(db_session, admin_user):
    """Open unknowns should generate investigation recommendations."""
    building = await _make_building(db_session, admin_user.id)
    await _make_unknown(db_session, building.id)

    recs = await generate_recommendations(db_session, building.id)
    assert len(recs) >= 1
    unknown_recs = [r for r in recs if r["source"] == "unknown_generator"]
    assert len(unknown_recs) == 1
    assert unknown_recs[0]["category"] == "investigation"
    assert unknown_recs[0]["urgency_days"] == 14  # blocks readiness


@pytest.mark.asyncio
async def test_trust_weak_dimensions_generate_recommendations(db_session, admin_user):
    """Weak trust dimensions should generate recommendations."""
    building = await _make_building(db_session, admin_user.id)
    await _make_trust_score(db_session, building.id)

    recs = await generate_recommendations(db_session, building.id)
    # Expect: declared (40%), obsolete (20%), contradictory (10%), low overall (0.4)
    assert len(recs) == 4
    sources = {r["source"] for r in recs}
    assert sources == {"trust_score"}


@pytest.mark.asyncio
async def test_sorting_priority_asc_impact_desc(db_session, admin_user):
    """Recommendations should be sorted: priority ASC, impact DESC."""
    building = await _make_building(db_session, admin_user.id)

    # Critical action
    await _make_action(
        db_session,
        building.id,
        title="Critical remediation",
        priority=ACTION_PRIORITY_CRITICAL,
    )
    # Low action
    await _make_action(
        db_session,
        building.id,
        title="Upload document",
        priority=ACTION_PRIORITY_LOW,
        action_type=ACTION_TYPE_DOCUMENTATION,
        metadata_json={},
    )
    # High unknown
    await _make_unknown(db_session, building.id)

    recs = await generate_recommendations(db_session, building.id)
    assert len(recs) >= 3
    # Critical should be first
    assert recs[0]["priority"] == 1
    # Low should be last
    assert recs[-1]["priority"] == 4


@pytest.mark.asyncio
async def test_limit_parameter(db_session, admin_user):
    """Limit parameter should cap the number of recommendations."""
    building = await _make_building(db_session, admin_user.id)
    for i in range(5):
        await _make_action(
            db_session,
            building.id,
            title=f"Action {i}",
            priority=ACTION_PRIORITY_MEDIUM,
            metadata_json={},
        )

    recs = await generate_recommendations(db_session, building.id, limit=3)
    assert len(recs) == 3


@pytest.mark.asyncio
async def test_cost_estimate_for_pollutant_actions(db_session, admin_user):
    """Pollutant-specific actions should have correct cost ranges."""
    building = await _make_building(db_session, admin_user.id)
    await _make_action(
        db_session,
        building.id,
        title="PCB decontamination",
        metadata_json={"pollutant_type": "pcb"},
    )

    recs = await generate_recommendations(db_session, building.id)
    assert len(recs) == 1
    cost = recs[0]["cost_estimate"]
    assert cost is not None
    assert cost["min"] == 20000
    assert cost["max"] == 100000


@pytest.mark.asyncio
async def test_all_sources_combined(db_session, admin_user):
    """All 4 sources should appear in combined output."""
    building = await _make_building(db_session, admin_user.id)
    await _make_action(db_session, building.id)
    await _make_readiness(db_session, building.id)
    await _make_unknown(db_session, building.id)
    await _make_trust_score(db_session, building.id)

    recs = await generate_recommendations(db_session, building.id, limit=50)
    sources = {r["source"] for r in recs}
    assert "action_generator" in sources
    assert "readiness_reasoner" in sources
    assert "unknown_generator" in sources
    assert "trust_score" in sources


@pytest.mark.asyncio
async def test_each_recommendation_has_required_fields(db_session, admin_user):
    """Every recommendation must have all required fields."""
    building = await _make_building(db_session, admin_user.id)
    await _make_action(db_session, building.id)
    await _make_unknown(db_session, building.id)

    recs = await generate_recommendations(db_session, building.id)
    required_fields = {"id", "priority", "category", "title", "description", "why", "impact_score", "source"}
    for rec in recs:
        for field in required_fields:
            assert field in rec, f"Missing field: {field}"
        assert 1 <= rec["priority"] <= 4
        assert 0.0 <= rec["impact_score"] <= 1.0
