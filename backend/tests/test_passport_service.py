"""Tests for the Building Passport Service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.services.passport_service import get_passport_summary

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


async def _create_unknown_issue(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "unknown_type": "missing_diagnostic",
        "severity": "high",
        "status": "open",
        "title": "Missing diagnostic",
        "blocks_readiness": False,
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
        "severity": "high",
        "status": "open",
        "field_name": "conflicting_sample_results",
        "description": "Test contradiction",
    }
    defaults.update(kwargs)
    dqi = DataQualityIssue(**defaults)
    db.add(dqi)
    await db.flush()
    return dqi


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
        "date_inspection": date(2024, 6, 1),
        "created_at": datetime(2024, 6, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "location_room": "Room A",
        "pollutant_type": "asbestos",
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


async def _create_document(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "file_path": "/fake/path.pdf",
        "file_name": "report.pdf",
        "document_type": "other",
    }
    defaults.update(kwargs)
    d = Document(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_intervention(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "asbestos_removal",
        "title": "Asbestos removal",
        "status": "completed",
    }
    defaults.update(kwargs)
    i = Intervention(**defaults)
    db.add(i)
    await db.flush()
    return i


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_passport_summary_returns_correct_structure(db_session, admin_user):
    """Test: returns correct structure for building with data."""
    building = await _create_building(db_session, admin_user)
    await _create_trust_score(db_session, building.id)
    await _create_readiness(db_session, building.id, "safe_to_start")
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id)
    await _create_document(db_session, building.id)
    await _create_intervention(db_session, building.id)
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    assert result is not None
    assert result["building_id"] == str(building.id)
    assert "knowledge_state" in result
    assert "completeness" in result
    assert "readiness" in result
    assert "blind_spots" in result
    assert "contradictions" in result
    assert "evidence_coverage" in result
    assert "passport_grade" in result
    assert "assessed_at" in result

    # Knowledge state keys
    ks = result["knowledge_state"]
    assert "proven_pct" in ks
    assert "inferred_pct" in ks
    assert "declared_pct" in ks
    assert "obsolete_pct" in ks
    assert "contradictory_pct" in ks
    assert "overall_trust" in ks
    assert "total_data_points" in ks
    assert "trend" in ks

    # Readiness keys
    for rtype in ("safe_to_start", "safe_to_tender", "safe_to_reopen", "safe_to_requalify"):
        assert rtype in result["readiness"]
        assert "status" in result["readiness"][rtype]
        assert "score" in result["readiness"][rtype]
        assert "blockers_count" in result["readiness"][rtype]


@pytest.mark.asyncio
async def test_passport_summary_defaults_for_empty_building(db_session, admin_user):
    """Test: returns defaults for building with no trust/readiness data."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    assert result is not None
    ks = result["knowledge_state"]
    assert ks["overall_trust"] == 0.0
    assert ks["total_data_points"] == 0
    assert ks["trend"] is None

    assert result["completeness"]["overall_score"] == 0.0

    for rtype in ("safe_to_start", "safe_to_tender", "safe_to_reopen", "safe_to_requalify"):
        assert result["readiness"][rtype]["status"] == "not_evaluated"
        assert result["readiness"][rtype]["score"] == 0.0


@pytest.mark.asyncio
async def test_passport_grade_a_for_excellent_building(db_session, admin_user):
    """Test: passport grade A for excellent building."""
    building = await _create_building(db_session, admin_user)
    await _create_trust_score(
        db_session,
        building.id,
        overall_score=0.9,
        percent_proven=0.8,
        percent_inferred=0.1,
        percent_declared=0.1,
        percent_obsolete=0.0,
        percent_contradictory=0.0,
    )
    # Create all 4 readiness assessments with high scores and no blockers
    for rtype in ("safe_to_start", "safe_to_tender", "safe_to_reopen", "safe_to_requalify"):
        await _create_readiness(
            db_session,
            building.id,
            rtype,
            status="ready",
            score=0.95,
            blockers_json=[],
        )
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    assert result["passport_grade"] == "A"


@pytest.mark.asyncio
async def test_passport_grade_f_for_empty_building(db_session, admin_user):
    """Test: passport grade F for empty building."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    assert result["passport_grade"] == "F"


@pytest.mark.asyncio
async def test_blind_spots_count_from_unknown_issues(db_session, admin_user):
    """Test: includes blind spots count from UnknownIssue."""
    building = await _create_building(db_session, admin_user)
    await _create_unknown_issue(
        db_session,
        building.id,
        unknown_type="missing_diagnostic",
        blocks_readiness=True,
    )
    await _create_unknown_issue(
        db_session,
        building.id,
        unknown_type="uninspected_zone",
        blocks_readiness=False,
    )
    await _create_unknown_issue(
        db_session,
        building.id,
        unknown_type="missing_diagnostic",
        blocks_readiness=True,
    )
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    bs = result["blind_spots"]
    assert bs["total_open"] == 3
    assert bs["blocking"] == 2
    assert bs["by_type"]["missing_diagnostic"] == 2
    assert bs["by_type"]["uninspected_zone"] == 1


@pytest.mark.asyncio
async def test_contradiction_count_from_data_quality_issues(db_session, admin_user):
    """Test: includes contradiction count from DataQualityIssue."""
    building = await _create_building(db_session, admin_user)
    await _create_contradiction(
        db_session,
        building.id,
        field_name="conflicting_sample_results",
        status="open",
    )
    await _create_contradiction(
        db_session,
        building.id,
        field_name="inconsistent_risk_levels",
        status="open",
    )
    await _create_contradiction(
        db_session,
        building.id,
        field_name="conflicting_sample_results",
        status="resolved",
    )
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    c = result["contradictions"]
    assert c["total"] == 3
    assert c["unresolved"] == 2
    assert c["by_type"]["conflicting_sample_results"] == 2
    assert c["by_type"]["inconsistent_risk_levels"] == 1


@pytest.mark.asyncio
async def test_evidence_coverage_includes_correct_counts(db_session, admin_user):
    """Test: evidence coverage includes correct entity counts."""
    building = await _create_building(db_session, admin_user)
    diag1 = await _create_diagnostic(db_session, building.id)
    diag2 = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag1.id)
    await _create_sample(db_session, diag1.id)
    await _create_sample(db_session, diag2.id)
    await _create_document(db_session, building.id)
    await _create_document(db_session, building.id)
    await _create_intervention(db_session, building.id)
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    ec = result["evidence_coverage"]
    assert ec["diagnostics_count"] == 2
    assert ec["samples_count"] == 3
    assert ec["documents_count"] == 2
    assert ec["interventions_count"] == 1
    assert ec["latest_diagnostic_date"] is not None


@pytest.mark.asyncio
async def test_passport_summary_returns_none_for_nonexistent_building(db_session, admin_user):
    """Test: returns None for non-existent building."""
    fake_id = uuid.uuid4()
    result = await get_passport_summary(db_session, fake_id)
    assert result is None
