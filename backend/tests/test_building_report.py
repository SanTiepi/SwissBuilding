"""Tests for the Building Report Generator service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.intervention import Intervention
from app.models.unknown_issue import UnknownIssue
from app.services.building_report_generator import (
    _format_chf,
    _format_date,
    _score_to_grade,
    generate_full_report,
    generate_report_pdf_payload,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue du Rapport 12",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": admin_user.id,
        "owner_id": admin_user.id,
        "status": "active",
        "floors_above": 4,
        "floors_below": 1,
        "surface_area_m2": 500.0,
        "volume_m3": 1500.0,
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_risk_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "asbestos_probability": 0.85,
        "pcb_probability": 0.40,
        "lead_probability": 0.30,
        "hap_probability": 0.15,
        "radon_probability": 0.10,
        "overall_risk_level": "high",
        "confidence": 0.75,
    }
    defaults.update(kwargs)
    rs = BuildingRiskScore(**defaults)
    db.add(rs)
    await db.flush()
    return rs


async def _create_trust_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "overall_score": 0.65,
        "percent_proven": 0.5,
        "percent_inferred": 0.1,
        "percent_declared": 0.2,
        "percent_obsolete": 0.1,
        "percent_contradictory": 0.1,
        "total_data_points": 20,
        "proven_count": 10,
        "inferred_count": 2,
        "declared_count": 4,
        "obsolete_count": 2,
        "contradictory_count": 2,
        "trend": "improving",
        "assessed_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    ts = BuildingTrustScore(**defaults)
    db.add(ts)
    await db.flush()
    return ts


async def _create_intervention(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "remediation",
        "title": "Asbestos removal",
        "status": "completed",
        "date_start": date(2024, 1, 1),
        "date_end": date(2024, 3, 15),
        "cost_chf": 25000.0,
        "contractor_name": "SanaCorp SA",
    }
    defaults.update(kwargs)
    interv = Intervention(**defaults)
    db.add(interv)
    await db.flush()
    return interv


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_report_building_not_found(db_session, admin_user):
    """Full report returns None for non-existent building."""
    result = await generate_full_report(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_full_report_minimal_building(db_session, admin_user):
    """Full report works with a building that has minimal data."""
    b = await _create_building(db_session, admin_user)
    result = await generate_full_report(db_session, b.id)

    assert result is not None
    assert result["building_id"] == str(b.id)
    assert result["identity"]["address"] == "Rue du Rapport 12"
    assert result["identity"]["canton"] == "VD"
    assert result["passport"]["grade"] in ("A", "B", "C", "D", "E", "F")
    assert result["metadata"]["disclaimer"]
    assert result["metadata"]["generated_at"]


@pytest.mark.asyncio
async def test_full_report_with_risk_scores(db_session, admin_user):
    """Full report includes pollutant risk data."""
    b = await _create_building(db_session, admin_user)
    await _create_risk_score(db_session, b.id)
    result = await generate_full_report(db_session, b.id)

    assert result["risks"]["pollutants"]
    assert len(result["risks"]["pollutants"]) >= 5
    asbestos = next(p for p in result["risks"]["pollutants"] if p["pollutant"] == "asbestos")
    assert asbestos["probability"] == 85
    assert asbestos["level"] == "critical"
    assert result["risks"]["overall_grade"] == "high"


@pytest.mark.asyncio
async def test_full_report_with_trust_score(db_session, admin_user):
    """Full report includes trust/passport data."""
    b = await _create_building(db_session, admin_user)
    await _create_trust_score(db_session, b.id)
    result = await generate_full_report(db_session, b.id)

    assert result["passport"]["trust_score"] == 65
    assert result["passport"]["trust_trend"] == "improving"


@pytest.mark.asyncio
async def test_full_report_with_interventions(db_session, admin_user):
    """Full report includes completed and planned interventions."""
    b = await _create_building(db_session, admin_user)
    await _create_intervention(db_session, b.id)
    await _create_intervention(
        db_session,
        b.id,
        title="PCB cleanup",
        status="planned",
        cost_chf=15000.0,
        date_end=None,
    )
    result = await generate_full_report(db_session, b.id)

    assert len(result["interventions"]["completed"]) == 1
    assert len(result["interventions"]["planned"]) == 1
    assert result["interventions"]["completed"][0]["title"] == "Asbestos removal"


@pytest.mark.asyncio
async def test_full_report_recommendations_from_unknowns(db_session, admin_user):
    """Full report generates recommendations from open unknowns."""
    b = await _create_building(db_session, admin_user)
    unknown = UnknownIssue(
        id=uuid.uuid4(),
        building_id=b.id,
        unknown_type="missing_diagnostic",
        title="Missing PCB diagnostic",
        description="No PCB diagnostic found",
        status="open",
        blocks_readiness=True,
    )
    db_session.add(unknown)
    await db_session.flush()

    result = await generate_full_report(db_session, b.id)
    assert len(result["recommendations"]) >= 1
    assert any("missing_diagnostic" in r["action"] for r in result["recommendations"])


@pytest.mark.asyncio
async def test_full_report_compliance_section(db_session, admin_user):
    """Full report includes compliance artefact counts."""
    b = await _create_building(db_session, admin_user)
    artefact = ComplianceArtefact(
        id=uuid.uuid4(),
        building_id=b.id,
        artefact_type="authority_notification",
        title="Authority notification",
        status="submitted",
    )
    db_session.add(artefact)
    await db_session.flush()

    result = await generate_full_report(db_session, b.id)
    assert result["compliance"]["submitted_count"] == 1
    assert result["compliance"]["total_artefacts"] == 1


@pytest.mark.asyncio
async def test_pdf_payload_building_not_found(db_session, admin_user):
    """PDF payload returns None for non-existent building."""
    result = await generate_report_pdf_payload(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_pdf_payload_generates_html(db_session, admin_user):
    """PDF payload generates valid HTML string."""
    b = await _create_building(db_session, admin_user)
    await _create_risk_score(db_session, b.id)
    await _create_trust_score(db_session, b.id)
    await _create_intervention(db_session, b.id)

    html = await generate_report_pdf_payload(db_session, b.id)
    assert html is not None
    assert "<!DOCTYPE html>" in html
    assert "Rue du Rapport 12" in html
    assert "BatiConnect" in html
    assert "Asbestos" in html or "asbestos" in html.lower()
    assert "CHF" in html


@pytest.mark.asyncio
async def test_pdf_payload_missing_data_graceful(db_session, admin_user):
    """PDF payload handles missing risk/trust data gracefully."""
    b = await _create_building(
        db_session,
        admin_user,
        construction_year=None,
        floors_above=None,
        surface_area_m2=None,
    )
    html = await generate_report_pdf_payload(db_session, b.id)
    assert html is not None
    assert "<!DOCTYPE html>" in html
    assert "Aucune donnee de risque" in html


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------


def test_format_chf():
    assert _format_chf(None) == "-"
    assert _format_chf(25000.0) == "CHF 25'000.00"
    assert _format_chf(0.0) == "CHF 0.00"


def test_format_date():
    assert _format_date(None) == "-"
    assert _format_date(date(2024, 3, 15)) == "15.03.2024"
    assert _format_date(datetime(2024, 12, 1, 10, 30)) == "01.12.2024"


def test_score_to_grade():
    assert _score_to_grade(90) == "A"
    assert _score_to_grade(75) == "B"
    assert _score_to_grade(60) == "C"
    assert _score_to_grade(45) == "D"
    assert _score_to_grade(30) == "E"
    assert _score_to_grade(10) == "F"
