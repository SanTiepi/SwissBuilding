"""Tests for the Proof of State Service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.services.proof_of_state_service import (
    _compute_integrity_hash,
    generate_proof_of_state,
    generate_proof_of_state_summary,
)

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


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
        "date_inspection": datetime.now(UTC).date(),
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
        "sample_number": "S001",
        "location_floor": "1",
        "location_room": "Room 1",
        "material_category": "flocage",
        "risk_level": "high",
        "concentration": 1.5,
        "unit": "%",
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
        "document_type": "diagnostic_report",
        "file_name": "report.pdf",
        "file_path": "/reports/report.pdf",
        "content_hash": "abc123",
        "created_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    d = Document(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_unknown(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "unknown_type": "missing_diagnostic",
        "title": "Missing PCB diagnostic",
        "description": "PCB diagnostic missing",
        "status": "open",
        "blocks_readiness": True,
        "detected_by": "system",
    }
    defaults.update(kwargs)
    u = UnknownIssue(**defaults)
    db.add(u)
    await db.flush()
    return u


# ── Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_export_has_all_sections(db, admin_user):
    building = await _create_building(db, admin_user)
    await _create_diagnostic(db, building.id)
    await db.commit()

    result = await generate_proof_of_state(db, building.id, admin_user.id)

    assert result is not None
    assert "metadata" in result
    assert "building" in result
    assert "evidence_score" in result
    assert "passport" in result
    assert "completeness" in result
    assert "trust" in result
    assert "diagnostics" in result
    assert "samples" in result
    assert "documents" in result
    assert "actions" in result
    assert "timeline" in result
    assert "readiness" in result
    assert "unknowns" in result
    assert "contradictions" in result
    assert "integrity" in result

    # Verify metadata fields
    metadata = result["metadata"]
    assert metadata["format_version"] == "1.0"
    assert metadata["building_id"] == str(building.id)
    assert metadata["generated_by"] == str(admin_user.id)
    assert "export_id" in metadata
    assert "generated_at" in metadata


@pytest.mark.asyncio
async def test_summary_has_correct_subset(db, admin_user):
    building = await _create_building(db, admin_user)
    await db.commit()

    result = await generate_proof_of_state_summary(db, building.id, admin_user.id)

    assert result is not None
    assert "metadata" in result
    assert "evidence_score" in result
    assert "passport" in result
    assert "readiness" in result
    assert "integrity" in result
    assert result["metadata"]["summary_only"] is True

    # Summary should NOT have full sections
    assert "building" not in result
    assert "diagnostics" not in result
    assert "samples" not in result
    assert "documents" not in result
    assert "actions" not in result
    assert "timeline" not in result


@pytest.mark.asyncio
async def test_integrity_hash_is_deterministic():
    """Same content should always produce the same hash."""
    content = {"metadata": {"export_id": "abc"}, "building": {"address": "Rue Test"}}
    hash1 = _compute_integrity_hash(content)
    hash2 = _compute_integrity_hash(content)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest length


@pytest.mark.asyncio
async def test_integrity_hash_changes_with_content():
    """Different content should produce different hashes."""
    content1 = {"metadata": {"export_id": "abc"}}
    content2 = {"metadata": {"export_id": "def"}}
    assert _compute_integrity_hash(content1) != _compute_integrity_hash(content2)


@pytest.mark.asyncio
async def test_building_not_found(db, admin_user):
    fake_id = uuid.uuid4()
    result = await generate_proof_of_state(db, fake_id, admin_user.id)
    assert result is None


@pytest.mark.asyncio
async def test_summary_building_not_found(db, admin_user):
    fake_id = uuid.uuid4()
    result = await generate_proof_of_state_summary(db, fake_id, admin_user.id)
    assert result is None


@pytest.mark.asyncio
async def test_anonymization_no_personal_data_in_samples(db, admin_user):
    """Samples in the export should not contain technician personal data."""
    building = await _create_building(db, admin_user)
    diag = await _create_diagnostic(db, building.id)
    await _create_sample(db, diag.id)
    await db.commit()

    result = await generate_proof_of_state(db, building.id, admin_user.id)
    assert result is not None
    assert len(result["samples"]) == 1

    sample = result["samples"][0]
    # Should have analytical data
    assert "location_floor" in sample
    assert "material_category" in sample
    assert "risk_level" in sample
    assert "concentration" in sample
    # Should NOT have personal fields
    assert "technician_name" not in sample
    assert "technician_email" not in sample
    assert "email" not in sample
    assert "phone" not in sample


@pytest.mark.asyncio
async def test_documents_have_hash_not_content(db, admin_user):
    """Documents in the export should include hash but not file content."""
    building = await _create_building(db, admin_user)
    await _create_document(db, building.id, content_hash="sha256:abc123def456")
    await db.commit()

    result = await generate_proof_of_state(db, building.id, admin_user.id)
    assert result is not None
    assert len(result["documents"]) == 1

    doc = result["documents"][0]
    assert doc["content_hash"] == "sha256:abc123def456"
    assert "content" not in doc
    assert "file_path" not in doc


@pytest.mark.asyncio
async def test_unknowns_included(db, admin_user):
    building = await _create_building(db, admin_user)
    await _create_unknown(db, building.id)
    await db.commit()

    result = await generate_proof_of_state(db, building.id, admin_user.id)
    assert result is not None
    assert len(result["unknowns"]) == 1
    assert result["unknowns"][0]["unknown_type"] == "missing_diagnostic"


@pytest.mark.asyncio
async def test_building_info_in_export(db, admin_user):
    building = await _create_building(db, admin_user, egid=12345, address="Rue de Bourg 1")
    await db.commit()

    result = await generate_proof_of_state(db, building.id, admin_user.id)
    assert result is not None
    assert result["building"]["address"] == "Rue de Bourg 1"
    assert result["building"]["egid"] == 12345
    assert result["building"]["city"] == "Lausanne"
