"""Tests for ImportedDiagnosticSummary read-model projection and API."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import relationship

from app.models.building import Building
from app.models.diagnostic_publication import DiagnosticReportPublication

# Wire the missing back_populates relationship on Building so the mapper resolves.
if not hasattr(Building, "diagnostic_publications"):
    Building.diagnostic_publications = relationship(
        "DiagnosticReportPublication",
        back_populates="building",
    )

from app.services.imported_diagnostic_service import (
    get_building_diagnostic_summaries,
    project_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_publication(
    *,
    source_mission_id: str = "M-001",
    match_state: str = "auto_matched",
    match_key_type: str = "egid",
    building_id: uuid.UUID | None = None,
    consumer_state: str | None = "ingested",
    current_version: int = 1,
    payload_hash: str = "abc123def456",
    structured_summary: dict | None = None,
    contract_version: str | None = "v1.0",
) -> DiagnosticReportPublication:
    pub = DiagnosticReportPublication(
        id=uuid.uuid4(),
        building_id=building_id or uuid.uuid4(),
        source_system="batiscan",
        source_mission_id=source_mission_id,
        current_version=current_version,
        match_state=match_state,
        match_key_type=match_key_type,
        match_key="12345",
        mission_type="asbestos_full",
        report_pdf_url="https://cdn.example.com/report.pdf",
        structured_summary=structured_summary
        or {
            "pollutants_found": ["asbestos"],
            "sample_count": 12,
            "positive_sample_count": 3,
            "review_sample_count": 1,
            "not_analyzed_count": 2,
            "ai_structured_summary": {"summary_text": "Asbestos found in floor tiles."},
            "remediation_handoff": {"priority": "high"},
            "report_readiness": {"status": "ready"},
        },
        annexes=[],
        payload_hash=payload_hash,
        published_at=datetime.now(UTC),
        is_immutable=True,
        consumer_state=consumer_state,
        contract_version=contract_version,
    )
    return pub


# ===========================================================================
# 1. project_summary nominal — all fields populated
# ===========================================================================


def test_project_summary_nominal():
    pub = _make_publication()
    s = project_summary(pub)
    assert s.source_system == "batiscan"
    assert s.mission_ref == "M-001"
    assert s.match_state == "auto_matched"
    assert s.match_key_type == "egid"
    assert s.report_readiness_status == "ready"
    assert s.snapshot_version == 1
    assert s.sample_count == 12
    assert s.positive_count == 3
    assert s.review_count == 1
    assert s.not_analyzed_count == 2
    assert s.ai_summary_text == "Asbestos found in floor tiles."
    assert s.has_ai is True
    assert s.has_remediation is True
    assert s.is_partial is False
    assert "no_ai" not in s.flags
    assert "no_remediation" not in s.flags
    assert "partial_package" not in s.flags


# ===========================================================================
# 2. project_summary no AI — has_ai=false, flags contains "no_ai"
# ===========================================================================


def test_project_summary_no_ai():
    pub = _make_publication(
        structured_summary={
            "pollutants_found": ["asbestos"],
            "sample_count": 5,
            "positive_sample_count": 1,
            "remediation_handoff": {"priority": "low"},
            "report_readiness": {"status": "ready"},
        }
    )
    s = project_summary(pub)
    assert s.has_ai is False
    assert s.ai_summary_text is None
    assert "no_ai" in s.flags


# ===========================================================================
# 3. project_summary no remediation — flags contains "no_remediation"
# ===========================================================================


def test_project_summary_no_remediation():
    pub = _make_publication(
        structured_summary={
            "pollutants_found": ["asbestos"],
            "sample_count": 5,
            "positive_sample_count": 1,
            "ai_structured_summary": {"summary_text": "Some AI text."},
            "report_readiness": {"status": "ready"},
        }
    )
    s = project_summary(pub)
    assert s.has_remediation is False
    assert "no_remediation" in s.flags


# ===========================================================================
# 4. project_summary partial — is_partial=true, flags contains "partial_package"
# ===========================================================================


def test_project_summary_partial():
    pub = _make_publication(
        structured_summary={
            # No pollutants_found → partial
            "ai_structured_summary": {"summary_text": "Some AI text."},
            "remediation_handoff": {"priority": "low"},
        }
    )
    s = project_summary(pub)
    assert s.is_partial is True
    assert "partial_package" in s.flags


# ===========================================================================
# 5. project_summary needs_review matching
# ===========================================================================


def test_project_summary_needs_review():
    pub = _make_publication(match_state="needs_review", match_key_type="address")
    s = project_summary(pub)
    assert s.match_state == "needs_review"
    assert s.match_key_type == "address"


# ===========================================================================
# 6. project_summary rejected_source — consumer_state flag
# ===========================================================================


def test_project_summary_rejected_source():
    pub = _make_publication(consumer_state="rejected_source")
    s = project_summary(pub)
    assert s.consumer_state == "rejected_source"
    assert "rejected_source" in s.flags


# ===========================================================================
# 7. API returns summaries for building (service-level async)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_building_diagnostic_summaries(db_session, admin_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        egid=99999,
    )
    db_session.add(building)
    await db_session.flush()

    pub = DiagnosticReportPublication(
        id=uuid.uuid4(),
        building_id=building.id,
        source_system="batiscan",
        source_mission_id="M-API-001",
        current_version=1,
        match_state="auto_matched",
        match_key_type="egid",
        match_key="99999",
        mission_type="asbestos_full",
        structured_summary={
            "pollutants_found": ["asbestos"],
            "sample_count": 5,
            "positive_sample_count": 2,
            "ai_structured_summary": {"summary_text": "Test AI summary."},
            "remediation_handoff": {"priority": "medium"},
            "report_readiness": {"status": "ready"},
        },
        annexes=[],
        payload_hash="apitest" + "a" * 58,
        published_at=datetime.now(UTC),
        is_immutable=True,
        consumer_state="ingested",
        contract_version="v1.0",
    )
    db_session.add(pub)
    await db_session.flush()

    summaries = await get_building_diagnostic_summaries(db_session, building.id)
    assert len(summaries) == 1
    s = summaries[0]
    assert s.mission_ref == "M-API-001"
    assert s.sample_count == 5
    assert s.positive_count == 2
    assert s.has_ai is True
    assert s.has_remediation is True
