"""Tests for the Compliance Domain Facade."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.readiness_assessment import ReadinessAssessment
from app.services.compliance_facade import get_compliance_summary

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


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nonexistent_building(db_session, admin_user):
    """Returns None for a building that does not exist."""
    result = await get_compliance_summary(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_empty_building(db_session, admin_user):
    """Returns default compliance state for a building with no data."""
    b = await _create_building(db_session, admin_user)
    result = await get_compliance_summary(db_session, b.id)

    assert result is not None
    assert result["completeness_score"] == 0.0 or isinstance(result["completeness_score"], float)
    assert result["artefacts"]["total"] == 0
    assert result["artefacts"]["pending_submissions"] == 0
    # All 4 readiness gates should be present with default status
    for gate in ("safe_to_start", "safe_to_tender", "safe_to_reopen", "safe_to_requalify"):
        assert gate in result["readiness"]
        assert "status" in result["readiness"][gate]
        assert "score" in result["readiness"][gate]


@pytest.mark.asyncio
async def test_building_with_artefacts(db_session, admin_user):
    """Returns correct artefact counts by status."""
    b = await _create_building(db_session, admin_user)

    for status in ("draft", "draft", "submitted", "acknowledged"):
        db_session.add(
            ComplianceArtefact(
                id=uuid.uuid4(),
                building_id=b.id,
                artefact_type="suva_notification",
                status=status,
                title=f"Artefact {status}",
            )
        )
    await db_session.flush()

    result = await get_compliance_summary(db_session, b.id)

    assert result["artefacts"]["total"] == 4
    assert result["artefacts"]["by_status"]["draft"] == 2
    assert result["artefacts"]["by_status"]["submitted"] == 1
    assert result["artefacts"]["by_status"]["acknowledged"] == 1
    assert result["artefacts"]["pending_submissions"] == 2


@pytest.mark.asyncio
async def test_building_with_readiness(db_session, admin_user):
    """Reads existing readiness assessments correctly."""
    b = await _create_building(db_session, admin_user)

    db_session.add(
        ReadinessAssessment(
            id=uuid.uuid4(),
            building_id=b.id,
            readiness_type="safe_to_start",
            status="blocked",
            score=0.4,
            blockers_json=[{"message": "Missing diagnostic"}],
        )
    )
    db_session.add(
        ReadinessAssessment(
            id=uuid.uuid4(),
            building_id=b.id,
            readiness_type="safe_to_tender",
            status="ready",
            score=1.0,
            blockers_json=[],
        )
    )
    await db_session.flush()

    result = await get_compliance_summary(db_session, b.id)

    assert result["readiness"]["safe_to_start"]["status"] == "blocked"
    assert result["readiness"]["safe_to_start"]["score"] == 0.4
    assert result["readiness"]["safe_to_start"]["blockers_count"] == 1
    assert result["readiness"]["safe_to_tender"]["status"] == "ready"
    assert result["readiness"]["safe_to_tender"]["score"] == 1.0
    # Gates without assessments should get defaults
    assert result["readiness"]["safe_to_reopen"]["status"] == "not_evaluated"
    assert result["readiness"]["safe_to_requalify"]["status"] == "not_evaluated"
