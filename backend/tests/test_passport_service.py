"""Tests for the Building Passport Service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.diagnostic_publication import DiagnosticReportPublication
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
    assert "diagnostic_publications" in result
    assert "pollutant_coverage" in result
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


# ── Pollutant coverage tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_pollutant_coverage_empty_building(db_session, admin_user):
    """Test: all pollutants missing when no diagnostics exist."""
    from app.constants import ALL_POLLUTANTS

    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)
    pc = result["pollutant_coverage"]

    assert pc["total_pollutants"] == len(ALL_POLLUTANTS)
    assert pc["covered_count"] == 0
    assert pc["missing_count"] == len(ALL_POLLUTANTS)
    assert pc["coverage_ratio"] == 0.0
    assert set(pc["missing"]) == set(ALL_POLLUTANTS)
    assert pc["covered"] == {}


@pytest.mark.asyncio
async def test_pollutant_coverage_partial(db_session, admin_user):
    """Test: partial pollutant coverage with asbestos and pfas diagnostics."""
    from app.constants import ALL_POLLUTANTS

    building = await _create_building(db_session, admin_user)
    await _create_diagnostic(db_session, building.id, diagnostic_type="asbestos")
    await _create_diagnostic(db_session, building.id, diagnostic_type="pfas")
    await _create_diagnostic(db_session, building.id, diagnostic_type="pfas")
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)
    pc = result["pollutant_coverage"]

    assert pc["covered_count"] == 2
    assert pc["covered"]["asbestos"] == 1
    assert pc["covered"]["pfas"] == 2
    assert "asbestos" not in pc["missing"]
    assert "pfas" not in pc["missing"]
    assert pc["missing_count"] == len(ALL_POLLUTANTS) - 2
    assert pc["coverage_ratio"] == round(2 / len(ALL_POLLUTANTS), 4)


@pytest.mark.asyncio
async def test_pollutant_coverage_all_covered(db_session, admin_user):
    """Test: full coverage when all pollutants have diagnostics."""
    from app.constants import ALL_POLLUTANTS

    building = await _create_building(db_session, admin_user)
    for p in ALL_POLLUTANTS:
        await _create_diagnostic(db_session, building.id, diagnostic_type=p)
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)
    pc = result["pollutant_coverage"]

    assert pc["covered_count"] == len(ALL_POLLUTANTS)
    assert pc["missing_count"] == 0
    assert pc["missing"] == []
    assert pc["coverage_ratio"] == 1.0
    assert "pfas" in pc["covered"]


@pytest.mark.asyncio
async def test_pollutant_coverage_includes_pfas(db_session, admin_user):
    """Test: PFAS is tracked as a distinct pollutant in coverage."""
    building = await _create_building(db_session, admin_user)
    await _create_diagnostic(db_session, building.id, diagnostic_type="pfas")
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)
    pc = result["pollutant_coverage"]

    assert "pfas" in pc["covered"]
    assert pc["covered"]["pfas"] == 1
    assert "pfas" not in pc["missing"]


# ── Diagnostic publications tests ─────────────────────────────────


async def _create_publication(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "source_system": "batiscan",
        "source_mission_id": f"M-{uuid.uuid4().hex[:8]}",
        "current_version": 1,
        "match_state": "auto_matched",
        "match_key": "12345",
        "match_key_type": "egid",
        "mission_type": "asbestos_full",
        "report_pdf_url": "https://example.com/report.pdf",
        "structured_summary": {"pollutants_found": ["asbestos"]},
        "payload_hash": uuid.uuid4().hex + uuid.uuid4().hex,
        "published_at": datetime(2025, 6, 1, tzinfo=UTC),
        "is_immutable": True,
    }
    defaults.update(kwargs)
    p = DiagnosticReportPublication(**defaults)
    db.add(p)
    await db.flush()
    return p


@pytest.mark.asyncio
async def test_diagnostic_publications_empty(db_session, admin_user):
    """Test: diagnostic_publications is empty when no publications exist."""
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    dp = result["diagnostic_publications"]
    assert dp["count"] == 0
    assert dp["pollutants_covered"] == []
    assert dp["latest_published_at"] is None


@pytest.mark.asyncio
async def test_diagnostic_publications_with_matched_reports(db_session, admin_user):
    """Test: diagnostic_publications counts matched publications."""
    building = await _create_building(db_session, admin_user)
    await _create_publication(
        db_session,
        building.id,
        mission_type="asbestos_full",
        published_at=datetime(2025, 3, 1, tzinfo=UTC),
    )
    await _create_publication(
        db_session,
        building.id,
        mission_type="pcb",
        published_at=datetime(2025, 6, 15, tzinfo=UTC),
    )
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    dp = result["diagnostic_publications"]
    assert dp["count"] == 2
    assert sorted(dp["pollutants_covered"]) == ["asbestos_full", "pcb"]
    assert dp["latest_published_at"] is not None
    assert "2025-06-15" in dp["latest_published_at"]


@pytest.mark.asyncio
async def test_diagnostic_publications_excludes_unmatched(db_session, admin_user):
    """Test: unmatched publications are excluded from passport."""
    building = await _create_building(db_session, admin_user)
    await _create_publication(
        db_session,
        building.id,
        match_state="auto_matched",
        mission_type="asbestos_full",
    )
    await _create_publication(
        db_session,
        building.id,
        match_state="unmatched",
        mission_type="pcb",
    )
    await _create_publication(
        db_session,
        building.id,
        match_state="needs_review",
        mission_type="lead",
    )
    await db_session.commit()

    result = await get_passport_summary(db_session, building.id)

    dp = result["diagnostic_publications"]
    assert dp["count"] == 1
    assert dp["pollutants_covered"] == ["asbestos_full"]
