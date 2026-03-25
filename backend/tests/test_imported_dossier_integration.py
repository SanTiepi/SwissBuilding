"""Tests for imported diagnostic dossier integration (passport, timeline, transfer package)."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.user import User
from app.services.imported_diagnostic_dossier import project_dossier_summary

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(db: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash="fakehash",
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(u)
    await db.flush()
    return u


async def _make_building(db: AsyncSession, *, address: str = "1 Test Street") -> Building:
    user = await _make_user(db)
    b = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=user.id,
    )
    db.add(b)
    await db.flush()
    return b


_FULL_SUMMARY = {
    "pollutants_found": ["asbestos"],
    "sample_count": 12,
    "positive_sample_count": 3,
    "review_sample_count": 1,
    "not_analyzed_count": 2,
    "ai_structured_summary": {"summary_text": "Asbestos found in floor tiles."},
    "remediation_handoff": {"priority": "high"},
    "report_readiness": {"status": "ready"},
}


def _make_pub(
    *,
    source_mission_id: str = "M-001",
    match_state: str = "auto_matched",
    match_key_type: str = "egid",
    building_id: uuid.UUID | None = None,
    consumer_state: str | None = "ingested",
    current_version: int = 1,
    payload_hash: str = "abc123def456",
    structured_summary: dict | None = None,
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
        structured_summary=structured_summary if structured_summary is not None else dict(_FULL_SUMMARY),
        annexes=[],
        payload_hash=payload_hash,
        published_at=datetime.now(UTC),
        is_immutable=True,
        consumer_state=consumer_state,
        contract_version="v1.0",
    )
    return pub


# ===========================================================================
# 1. project_dossier_summary nominal — all fields populated
# ===========================================================================


def test_project_dossier_summary_nominal():
    pub = _make_pub()
    result = project_dossier_summary(pub)

    assert result["source_system"] == "batiscan"
    assert result["mission_ref"] == "M-001"
    assert result["published_at"] is not None
    assert result["local_ingestion_status"] == "ingested"
    assert result["building_match_status"] == "auto_matched"
    assert result["report_readiness_status"] == "ready"
    assert result["snapshot_version"] == 1
    assert result["payload_hash"] == "abc123def456"
    assert result["sample_count"] == 12
    assert result["positive_sample_count"] == 3
    assert result["ai_summary_text"] == "Asbestos found in floor tiles."
    assert result["flags"] == []


# ===========================================================================
# 2. project_dossier_summary no_ai — flags contains "no_ai"
# ===========================================================================


def test_project_dossier_summary_no_ai():
    summary = dict(_FULL_SUMMARY)
    summary["ai_structured_summary"] = {}
    pub = _make_pub(structured_summary=summary)
    result = project_dossier_summary(pub)

    assert "no_ai" in result["flags"]
    assert result["ai_summary_text"] is None


# ===========================================================================
# 3. project_dossier_summary partial — flags contains "partial_package"
# ===========================================================================


def test_project_dossier_summary_partial():
    summary = dict(_FULL_SUMMARY)
    summary.pop("pollutants_found")
    pub = _make_pub(structured_summary=summary)
    result = project_dossier_summary(pub)

    assert "partial_package" in result["flags"]


# ===========================================================================
# 4. project_dossier_summary snapshot_ref always None
# ===========================================================================


def test_project_dossier_summary_snapshot_ref_always_none():
    pub = _make_pub()
    result = project_dossier_summary(pub)
    assert result["snapshot_ref"] is None


# ===========================================================================
# 5. passport includes latest_imported_summary for matched publication
# ===========================================================================


@pytest.mark.asyncio
async def test_passport_includes_latest_imported_summary(db_session):
    """Passport should include latest_imported_summary when matched publications exist."""
    building = await _make_building(db_session, address="1 Test Street")

    pub = _make_pub(building_id=building.id, match_state="auto_matched")
    db_session.add(pub)
    await db_session.flush()

    from app.services.passport_service import get_passport_summary

    passport = await get_passport_summary(db_session, building.id)
    assert passport is not None
    dp = passport["diagnostic_publications"]
    assert dp["latest_imported_summary"] is not None
    assert dp["latest_imported_summary"]["source_system"] == "batiscan"
    assert dp["latest_imported_summary"]["mission_ref"] == "M-001"
    assert dp["latest_imported_summary"]["snapshot_ref"] is None


# ===========================================================================
# 6. passport latest_imported_summary is None when no matched publications
# ===========================================================================


@pytest.mark.asyncio
async def test_passport_no_imported_summary_when_no_publications(db_session):
    """Passport should have latest_imported_summary=None when no matched publications."""
    building = await _make_building(db_session, address="2 Test Street")

    from app.services.passport_service import get_passport_summary

    passport = await get_passport_summary(db_session, building.id)
    assert passport is not None
    assert passport["diagnostic_publications"]["latest_imported_summary"] is None


# ===========================================================================
# 7. passport excludes unmatched/rejected publications from latest_imported_summary
# ===========================================================================


@pytest.mark.asyncio
async def test_passport_excludes_unmatched_publications(db_session):
    """Passport should not include unmatched or rejected publications."""
    building = await _make_building(db_session, address="3 Test Street")

    # Add unmatched publication
    pub = _make_pub(building_id=building.id, match_state="unmatched")
    db_session.add(pub)
    await db_session.flush()

    from app.services.passport_service import get_passport_summary

    passport = await get_passport_summary(db_session, building.id)
    assert passport is not None
    assert passport["diagnostic_publications"]["latest_imported_summary"] is None


# ===========================================================================
# 8. timeline diagnostic_publication entries have enriched metadata
# ===========================================================================


@pytest.mark.asyncio
async def test_timeline_diagnostic_publication_enriched_metadata(db_session):
    """Timeline should include enriched dossier metadata in diagnostic_publication entries."""
    building = await _make_building(db_session, address="4 Test Street")

    pub = _make_pub(building_id=building.id, match_state="auto_matched")
    db_session.add(pub)
    await db_session.flush()

    from app.services.timeline_service import get_building_timeline

    items, _total = await get_building_timeline(db_session, building.id)
    pub_items = [i for i in items if i.event_type == "diagnostic_publication"]
    assert len(pub_items) == 1

    meta = pub_items[0].metadata
    assert meta["source_system"] == "batiscan"
    assert meta["source_mission_id"] == "M-001"
    assert meta["report_readiness_status"] == "ready"
    assert meta["local_ingestion_status"] == "ingested"
    assert meta["building_match_status"] == "auto_matched"
    assert meta["sample_count"] == 12
    assert meta["positive_sample_count"] == 3
    assert isinstance(meta["flags"], list)

    # Check enriched description
    assert "Imported from batiscan" in pub_items[0].description
    assert "M-001" in pub_items[0].description
    assert "12 samples" in pub_items[0].description


# ===========================================================================
# 9. transfer package diagnostic_publications use dossier summary format
# ===========================================================================


@pytest.mark.asyncio
async def test_transfer_package_dossier_summary_format(db_session):
    """Transfer package should use project_dossier_summary format for publications."""
    building = await _make_building(db_session, address="5 Test Street")

    pub = _make_pub(building_id=building.id, match_state="auto_matched")
    db_session.add(pub)
    await db_session.flush()

    from app.services.transfer_package_service import generate_transfer_package

    package = await generate_transfer_package(db_session, building.id, include_sections=["diagnostic_publications"])
    assert package is not None
    pubs = package.diagnostic_publications
    assert pubs is not None
    assert len(pubs) == 1

    item = pubs[0]
    # Dossier summary fields
    assert item["source_system"] == "batiscan"
    assert item["mission_ref"] == "M-001"
    assert item["report_readiness_status"] == "ready"
    assert item["snapshot_ref"] is None
    assert item["sample_count"] == 12
    assert isinstance(item["flags"], list)


# ===========================================================================
# 10. transfer package preserves report_pdf_url alongside summary
# ===========================================================================


@pytest.mark.asyncio
async def test_transfer_package_preserves_report_pdf_url(db_session):
    """Transfer package should preserve report_pdf_url and mission_type alongside dossier summary."""
    building = await _make_building(db_session, address="6 Test Street")

    pub = _make_pub(building_id=building.id, match_state="manual_matched")
    db_session.add(pub)
    await db_session.flush()

    from app.services.transfer_package_service import generate_transfer_package

    package = await generate_transfer_package(db_session, building.id, include_sections=["diagnostic_publications"])
    assert package is not None
    pubs = package.diagnostic_publications
    assert len(pubs) == 1

    item = pubs[0]
    assert item["report_pdf_url"] == "https://cdn.example.com/report.pdf"
    assert item["mission_type"] == "asbestos_full"
    assert item["id"] is not None
