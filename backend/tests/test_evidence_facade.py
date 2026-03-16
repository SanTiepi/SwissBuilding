"""Tests for the Evidence Domain Facade."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.sample import Sample
from app.services.evidence_facade import get_evidence_summary

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
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "full",
        "status": "completed",
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
        "pollutant_type": "asbestos",
        "concentration": 2.0,
        "unit": "percent_weight",
        "threshold_exceeded": True,
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nonexistent_building(db_session, admin_user):
    """Returns None for a building that does not exist."""
    result = await get_evidence_summary(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_empty_building(db_session, admin_user):
    """Returns zero counts for a building with no data."""
    b = await _create_building(db_session, admin_user)
    result = await get_evidence_summary(db_session, b.id)

    assert result is not None
    assert result["diagnostics_count"] == 0
    assert result["samples_count"] == 0
    assert result["documents_count"] == 0
    assert result["evidence_links_count"] == 0
    assert result["coverage_ratio"] == 0.0


@pytest.mark.asyncio
async def test_building_with_data(db_session, admin_user):
    """Returns correct counts and coverage for a building with diagnostics and samples."""
    b = await _create_building(db_session, admin_user)

    diag = await _create_diagnostic(db_session, b.id)
    await _create_sample(db_session, diag.id, pollutant_type="asbestos", threshold_exceeded=True)
    await _create_sample(db_session, diag.id, pollutant_type="pcb", threshold_exceeded=False)
    await _create_sample(db_session, diag.id, pollutant_type="lead", threshold_exceeded=True)

    # Add a document
    doc = Document(
        id=uuid.uuid4(),
        building_id=b.id,
        file_name="report.pdf",
        document_type="diagnostic_report",
        file_path="/test/report.pdf",
    )
    db_session.add(doc)

    # Add an evidence link referencing the building
    link = EvidenceLink(
        id=uuid.uuid4(),
        source_type="building",
        source_id=b.id,
        target_type="diagnostic",
        target_id=diag.id,
        relationship="contains",
    )
    db_session.add(link)
    await db_session.flush()

    result = await get_evidence_summary(db_session, b.id)

    assert result is not None
    assert result["diagnostics_count"] == 1
    assert result["diagnostics_by_status"]["completed"] == 1
    assert result["samples_count"] == 3
    assert result["samples_positive"] == 2
    assert result["samples_negative"] == 1
    assert result["documents_count"] == 1
    assert result["evidence_links_count"] == 1
    # 3 out of 5 pollutants covered
    assert result["coverage_ratio"] == 0.6


@pytest.mark.asyncio
async def test_full_pollutant_coverage(db_session, admin_user):
    """Coverage ratio is 1.0 when all 5 pollutants have samples."""
    b = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, b.id)

    for pollutant in ("asbestos", "pcb", "lead", "hap", "radon"):
        await _create_sample(db_session, diag.id, pollutant_type=pollutant)

    result = await get_evidence_summary(db_session, b.id)

    assert result is not None
    assert result["coverage_ratio"] == 1.0
    assert len(result["samples_by_pollutant"]) == 5
