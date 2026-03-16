"""Tests for the ChangeSignal generator service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.change_signal_generator import (
    acknowledge_signal,
    generate_signals_for_building,
    get_building_signal_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, status="completed"):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="avant_travaux",
        status=status,
    )
    db.add(d)
    await db.flush()
    return d


async def _create_sample(db, diagnostic_id, pollutant="asbestos", exceeded=True):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant,
        location_room="Salle 1",
        material_category="Flocage",
        threshold_exceeded=exceeded,
    )
    db.add(s)
    await db.flush()
    return s


async def _create_intervention(db, building_id, status="completed"):
    i = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type="asbestos_removal",
        title="Test intervention",
        status=status,
        created_by=None,
    )
    db.add(i)
    await db.flush()
    return i


async def _create_document(db, building_id):
    d = Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path="/test/doc.pdf",
        file_name="doc.pdf",
        document_type="diagnostic_report",
    )
    db.add(d)
    await db.flush()
    return d


async def _create_action(db, building_id, priority="critical", status="open"):
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=building_id,
        title="Test action",
        description="Test",
        source_type="diagnostic",
        action_type="remediation",
        priority=priority,
        status=status,
    )
    db.add(a)
    await db.flush()
    return a


async def _create_risk_score(db, building_id, level="critical"):
    rs = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building_id,
        asbestos_probability=0.9,
        pcb_probability=0.1,
        lead_probability=0.1,
        hap_probability=0.1,
        radon_probability=0.1,
        overall_risk_level=level,
        confidence=0.8,
    )
    db.add(rs)
    await db.flush()
    return rs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnostic_completed_signal(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    await _create_diagnostic(db_session, building.id, status="completed")

    signals = await generate_signals_for_building(db_session, building.id)

    completed = [s for s in signals if s.signal_type == "diagnostic_completed"]
    assert len(completed) == 1
    assert completed[0].severity == "info"
    assert completed[0].entity_type == "diagnostic"
    assert completed[0].source == "diagnostic_service"


@pytest.mark.asyncio
async def test_new_positive_sample_signal(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id, pollutant="asbestos", exceeded=True)

    signals = await generate_signals_for_building(db_session, building.id)

    positive = [s for s in signals if s.signal_type == "new_positive_sample"]
    assert len(positive) == 1
    assert positive[0].severity == "warning"
    assert positive[0].entity_type == "sample"
    assert positive[0].source == "sample_analysis"


@pytest.mark.asyncio
async def test_intervention_completed_signal(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    await _create_intervention(db_session, building.id, status="completed")

    signals = await generate_signals_for_building(db_session, building.id)

    completed = [s for s in signals if s.signal_type == "intervention_completed"]
    assert len(completed) == 1
    assert completed[0].severity == "info"
    assert completed[0].entity_type == "intervention"
    assert completed[0].source == "intervention_service"


@pytest.mark.asyncio
async def test_document_uploaded_signal(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    await _create_document(db_session, building.id)

    signals = await generate_signals_for_building(db_session, building.id)

    uploaded = [s for s in signals if s.signal_type == "document_uploaded"]
    assert len(uploaded) == 1
    assert uploaded[0].severity == "info"
    assert uploaded[0].entity_type == "document"
    assert uploaded[0].source == "document_service"


@pytest.mark.asyncio
async def test_risk_level_change_signal(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    await _create_risk_score(db_session, building.id, level="critical")

    signals = await generate_signals_for_building(db_session, building.id)

    risk = [s for s in signals if s.signal_type == "risk_level_change"]
    assert len(risk) == 1
    assert risk[0].severity == "warning"
    assert risk[0].entity_type == "risk_score"
    assert risk[0].source == "risk_engine"


@pytest.mark.asyncio
async def test_diagnostic_expiring_signal(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id, status="completed")
    # Set inspection date to 4.5 years ago
    old_date = (datetime.now(UTC) - timedelta(days=int(4.5 * 365))).date()
    diag.date_inspection = old_date
    await db_session.flush()

    signals = await generate_signals_for_building(db_session, building.id)

    expiring = [s for s in signals if s.signal_type == "diagnostic_expiring"]
    assert len(expiring) == 1
    assert expiring[0].severity == "warning"
    assert expiring[0].entity_type == "diagnostic"
    assert expiring[0].source == "requalification_monitor"


@pytest.mark.asyncio
async def test_action_overdue_signal(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    action = await _create_action(db_session, building.id, priority="critical", status="open")
    # Set created_at to 35 days ago
    action.created_at = datetime.now(UTC) - timedelta(days=35)
    await db_session.flush()

    signals = await generate_signals_for_building(db_session, building.id)

    overdue = [s for s in signals if s.signal_type == "action_overdue"]
    assert len(overdue) == 1
    assert overdue[0].severity == "warning"
    assert overdue[0].entity_type == "action_item"
    assert overdue[0].source == "action_monitor"


@pytest.mark.asyncio
async def test_idempotent_generation(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    await _create_diagnostic(db_session, building.id, status="completed")
    await _create_document(db_session, building.id)

    signals_1 = await generate_signals_for_building(db_session, building.id)
    assert len(signals_1) > 0

    signals_2 = await generate_signals_for_building(db_session, building.id)
    assert len(signals_2) == 0


@pytest.mark.asyncio
async def test_acknowledge_signal(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    await _create_document(db_session, building.id)

    signals = await generate_signals_for_building(db_session, building.id)
    sig = next(s for s in signals if s.signal_type == "document_uploaded")

    ack = await acknowledge_signal(db_session, sig.id, admin_user.id)
    assert ack.acknowledged_by == admin_user.id
    assert ack.acknowledged_at is not None
    assert ack.status == "active"


@pytest.mark.asyncio
async def test_signal_summary(db_session, admin_user):
    building = await _create_building(db_session, admin_user)
    await _create_diagnostic(db_session, building.id, status="completed")
    await _create_document(db_session, building.id)
    await _create_risk_score(db_session, building.id, level="critical")

    await generate_signals_for_building(db_session, building.id)

    summary = await get_building_signal_summary(db_session, building.id)
    assert summary["total_active"] >= 3
    assert "diagnostic_completed" in summary["by_type"]
    assert "document_uploaded" in summary["by_type"]
    assert "risk_level_change" in summary["by_type"]
    assert summary["unacknowledged"] == summary["total_active"]
    assert "info" in summary["by_severity"]
    assert "warning" in summary["by_severity"]
