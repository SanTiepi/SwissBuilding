"""Tests for the Building Comparison Service and API."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.readiness_assessment import ReadinessAssessment
from app.models.unknown_issue import UnknownIssue
from app.services.building_comparison_service import compare_buildings

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
        "owner_id": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_trust_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "overall_score": 0.5,
        "percent_proven": 0.4,
        "percent_inferred": 0.1,
        "percent_declared": 0.3,
        "percent_obsolete": 0.1,
        "percent_contradictory": 0.1,
        "total_data_points": 10,
        "proven_count": 4,
        "inferred_count": 1,
        "declared_count": 3,
        "obsolete_count": 1,
        "contradictory_count": 1,
        "trend": "stable",
        "assessed_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    ts = BuildingTrustScore(**defaults)
    db.add(ts)
    await db.flush()
    return ts


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
        "date_inspection": date(2025, 1, 15),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_readiness(db, building_id, readiness_type, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "readiness_type": readiness_type,
        "status": "blocked",
        "score": 0.5,
        "checks_json": [],
        "blockers_json": [],
        "conditions_json": [],
        "assessed_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    ra = ReadinessAssessment(**defaults)
    db.add(ra)
    await db.flush()
    return ra


async def _create_action(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "source_type": "diagnostic",
        "action_type": "remediation",
        "title": "Test Action",
        "priority": "medium",
        "status": "open",
    }
    defaults.update(kwargs)
    a = ActionItem(**defaults)
    db.add(a)
    await db.flush()
    return a


async def _create_unknown(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "unknown_type": "missing_data",
        "severity": "medium",
        "status": "open",
        "title": "Unknown test issue",
    }
    defaults.update(kwargs)
    u = UnknownIssue(**defaults)
    db.add(u)
    await db.flush()
    return u


async def _create_contradiction(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "issue_type": "contradiction",
        "severity": "medium",
        "status": "open",
        "description": "Contradictory data",
    }
    defaults.update(kwargs)
    dqi = DataQualityIssue(**defaults)
    db.add(dqi)
    await db.flush()
    return dqi


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compare_two_buildings(db_session, admin_user):
    """Compare 2 buildings returns entries for both with correct structure."""
    b1 = await _create_building(db_session, admin_user, address="Rue A 1")
    b2 = await _create_building(db_session, admin_user, address="Rue B 2")
    await _create_trust_score(db_session, b1.id, overall_score=0.7)
    await _create_trust_score(db_session, b2.id, overall_score=0.4)
    await db_session.commit()

    result = await compare_buildings(db_session, [str(b1.id), str(b2.id)])

    assert len(result.buildings) == 2
    assert result.buildings[0].building_id == str(b1.id)
    assert result.buildings[1].building_id == str(b2.id)
    assert result.buildings[0].trust_score == 0.7
    assert result.buildings[1].trust_score == 0.4
    assert len(result.comparison_dimensions) > 0
    assert "passport" in result.comparison_dimensions


@pytest.mark.asyncio
async def test_compare_building_no_diagnostics(db_session, admin_user):
    """Building with no diagnostics should still appear with None/0 values."""
    b1 = await _create_building(db_session, admin_user, address="Rue A 1")
    b2 = await _create_building(db_session, admin_user, address="Rue B 2")
    await _create_diagnostic(db_session, b1.id)
    # b2 has no diagnostics
    await db_session.commit()

    result = await compare_buildings(db_session, [str(b1.id), str(b2.id)])

    assert len(result.buildings) == 2
    entry_b1 = result.buildings[0]
    entry_b2 = result.buildings[1]
    assert entry_b1.diagnostic_count == 1
    assert entry_b2.diagnostic_count == 0
    assert entry_b2.last_diagnostic_date is None


@pytest.mark.asyncio
async def test_best_worst_passport_ranking(db_session, admin_user):
    """Best/worst passport correctly identifies the best and worst graded buildings."""
    b1 = await _create_building(db_session, admin_user, address="Rue A 1")
    b2 = await _create_building(db_session, admin_user, address="Rue B 2")
    b3 = await _create_building(db_session, admin_user, address="Rue C 3")
    # b1: high trust + high completeness = better grade
    await _create_trust_score(db_session, b1.id, overall_score=0.9)
    await _create_readiness(db_session, b1.id, "safe_to_start", status="ready", score=0.95)
    # b2: medium
    await _create_trust_score(db_session, b2.id, overall_score=0.5)
    # b3: low trust = worst grade
    await _create_trust_score(db_session, b3.id, overall_score=0.1)
    await db_session.commit()

    result = await compare_buildings(db_session, [str(b1.id), str(b2.id), str(b3.id)])

    # All buildings should have a passport grade
    grades = {e.building_id: e.passport_grade for e in result.buildings}
    assert grades[str(b1.id)] is not None
    assert result.best_passport is not None
    assert result.worst_passport is not None
    # The best should have a better (earlier in A-F) grade than worst
    best_entry = next(e for e in result.buildings if e.building_id == result.best_passport)
    worst_entry = next(e for e in result.buildings if e.building_id == result.worst_passport)
    grade_order = ["A", "B", "C", "D", "F"]
    best_idx = grade_order.index(best_entry.passport_grade) if best_entry.passport_grade in grade_order else 99
    worst_idx = grade_order.index(worst_entry.passport_grade) if worst_entry.passport_grade in grade_order else 99
    assert best_idx <= worst_idx


@pytest.mark.asyncio
async def test_average_calculations(db_session, admin_user):
    """Average trust and completeness are correctly computed."""
    b1 = await _create_building(db_session, admin_user, address="Rue A 1")
    b2 = await _create_building(db_session, admin_user, address="Rue B 2")
    await _create_trust_score(db_session, b1.id, overall_score=0.8)
    await _create_trust_score(db_session, b2.id, overall_score=0.4)
    await db_session.commit()

    result = await compare_buildings(db_session, [str(b1.id), str(b2.id)])

    assert result.average_trust == 0.6


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Comparison with a non-existent building raises ValueError."""
    b1 = await _create_building(db_session, admin_user, address="Rue A 1")
    await db_session.commit()

    fake_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="Buildings not found"):
        await compare_buildings(db_session, [str(b1.id), fake_id])


@pytest.mark.asyncio
async def test_too_few_buildings(db_session, admin_user):
    """Fewer than 2 buildings raises ValueError."""
    b1 = await _create_building(db_session, admin_user, address="Rue A 1")
    await db_session.commit()

    with pytest.raises(ValueError, match="At least 2"):
        await compare_buildings(db_session, [str(b1.id)])


@pytest.mark.asyncio
async def test_too_many_buildings(db_session, admin_user):
    """More than 10 buildings raises ValueError."""
    buildings = []
    for i in range(11):
        b = await _create_building(db_session, admin_user, address=f"Rue {i}")
        buildings.append(b)
    await db_session.commit()

    ids = [str(b.id) for b in buildings]
    with pytest.raises(ValueError, match="At most 10"):
        await compare_buildings(db_session, ids)


@pytest.mark.asyncio
async def test_counts_actions_unknowns_contradictions(db_session, admin_user):
    """Open actions, unknowns, and contradictions are correctly counted."""
    b1 = await _create_building(db_session, admin_user, address="Rue A 1")
    b2 = await _create_building(db_session, admin_user, address="Rue B 2")
    # b1: 2 open actions, 1 unknown, 1 contradiction
    await _create_action(db_session, b1.id, status="open")
    await _create_action(db_session, b1.id, status="open")
    await _create_action(db_session, b1.id, status="completed")  # should not count
    await _create_unknown(db_session, b1.id, status="open")
    await _create_contradiction(db_session, b1.id, status="open")
    # b2: clean
    await db_session.commit()

    result = await compare_buildings(db_session, [str(b1.id), str(b2.id)])

    entry_b1 = result.buildings[0]
    entry_b2 = result.buildings[1]
    assert entry_b1.open_actions_count == 2
    assert entry_b1.open_unknowns_count == 1
    assert entry_b1.contradictions_count == 1
    assert entry_b2.open_actions_count == 0
    assert entry_b2.open_unknowns_count == 0
    assert entry_b2.contradictions_count == 0


@pytest.mark.asyncio
async def test_readiness_summary(db_session, admin_user):
    """Readiness summary reflects ready/blocked status per type."""
    b1 = await _create_building(db_session, admin_user, address="Rue A 1")
    b2 = await _create_building(db_session, admin_user, address="Rue B 2")
    await _create_readiness(db_session, b1.id, "safe_to_start", status="ready")
    await _create_readiness(db_session, b1.id, "safe_to_tender", status="blocked")
    await db_session.commit()

    result = await compare_buildings(db_session, [str(b1.id), str(b2.id)])

    entry_b1 = result.buildings[0]
    assert entry_b1.readiness_summary["safe_to_start"] is True
    assert entry_b1.readiness_summary["safe_to_tender"] is False
    # Defaults for missing types
    assert entry_b1.readiness_summary["safe_to_reopen"] is False

    entry_b2 = result.buildings[1]
    assert entry_b2.readiness_summary["safe_to_start"] is False


@pytest.mark.asyncio
async def test_compare_api_endpoint(client, admin_user, auth_headers, db_session):
    """POST /api/buildings/compare returns correct response."""
    b1 = Building(
        id=uuid.uuid4(),
        address="Rue API 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    b2 = Building(
        id=uuid.uuid4(),
        address="Rue API 2",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1980,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add_all([b1, b2])
    await db_session.commit()

    resp = await client.post(
        "/api/v1/buildings/compare",
        json={"building_ids": [str(b1.id), str(b2.id)]},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["buildings"]) == 2
    assert "comparison_dimensions" in data
    assert "average_trust" in data
    assert "average_completeness" in data
