"""Tests for flywheel hooks (Lot D)."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.domain_event import DomainEvent
from app.models.user import User
from app.services.flywheel_hooks import (
    on_diagnostic_received,
    on_post_works_finalized,
    on_proof_delivered,
    on_remediation_completed,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def fw_building(db_session: AsyncSession, admin_user: User):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Flywheel 1",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        building_type="residential",
        created_by=admin_user.id,
        construction_year=1980,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def peer_building(db_session: AsyncSession, admin_user: User):
    """Peer building in same postal code + similar year for propagation tests."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Flywheel 3",
        postal_code="1200",
        city="Geneve",
        canton="GE",
        building_type="residential",
        created_by=admin_user.id,
        construction_year=1982,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


def _make_event(event_type: str, building_id: uuid.UUID, payload: dict | None = None) -> DomainEvent:
    return DomainEvent(
        id=uuid.uuid4(),
        event_type=event_type,
        aggregate_type="building",
        aggregate_id=building_id,
        payload=payload or {},
        occurred_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# on_diagnostic_received
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnostic_received_creates_flywheel_event(db_session: AsyncSession, fw_building: Building):
    """on_diagnostic_received creates a flywheel domain event."""
    event = _make_event(
        "diagnostic_publication_received",
        fw_building.id,
        {"building_id": str(fw_building.id)},
    )
    db_session.add(event)
    await db_session.flush()

    await on_diagnostic_received(db_session, event)

    result = await db_session.execute(
        select(DomainEvent).where(DomainEvent.event_type == "flywheel_diagnostic_refreshed")
    )
    flywheel_event = result.scalar_one_or_none()
    assert flywheel_event is not None
    assert flywheel_event.aggregate_id == fw_building.id


@pytest.mark.asyncio
async def test_diagnostic_received_updates_metadata(db_session: AsyncSession, fw_building: Building):
    """on_diagnostic_received updates building source_metadata_json."""
    event = _make_event(
        "diagnostic_publication_received",
        fw_building.id,
        {"building_id": str(fw_building.id)},
    )
    db_session.add(event)
    await db_session.flush()

    await on_diagnostic_received(db_session, event)

    await db_session.refresh(fw_building)
    meta = fw_building.source_metadata_json or {}
    flywheel = meta.get("flywheel", {})
    assert flywheel.get("trigger") == "diagnostic_received"
    assert "last_refreshed_at" in flywheel


# ---------------------------------------------------------------------------
# on_remediation_completed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remediation_completed_creates_event(db_session: AsyncSession, fw_building: Building):
    """on_remediation_completed creates a flywheel domain event."""
    event = _make_event(
        "remediation_completion_fully_confirmed",
        fw_building.id,
        {"building_id": str(fw_building.id), "pollutant_type": "asbestos"},
    )
    db_session.add(event)
    await db_session.flush()

    await on_remediation_completed(db_session, event)

    result = await db_session.execute(
        select(DomainEvent).where(DomainEvent.event_type == "flywheel_remediation_refreshed")
    )
    flywheel_event = result.scalar_one_or_none()
    assert flywheel_event is not None


@pytest.mark.asyncio
async def test_remediation_completed_propagates_to_peers(
    db_session: AsyncSession, fw_building: Building, peer_building: Building
):
    """on_remediation_completed propagates learning to similar buildings."""
    event = _make_event(
        "remediation_completion_fully_confirmed",
        fw_building.id,
        {"building_id": str(fw_building.id), "pollutant_type": "pcb"},
    )
    db_session.add(event)
    await db_session.flush()

    await on_remediation_completed(db_session, event)

    await db_session.refresh(peer_building)
    meta = peer_building.source_metadata_json or {}
    peer_signals = meta.get("peer_signals", [])
    assert len(peer_signals) >= 1
    assert peer_signals[0]["signal_type"] == "remediation_completed"
    assert peer_signals[0]["signal_data"]["pollutant"] == "pcb"


# ---------------------------------------------------------------------------
# on_proof_delivered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_proof_delivered_creates_event(db_session: AsyncSession, fw_building: Building):
    """on_proof_delivered creates a flywheel domain event."""
    event = _make_event(
        "proof_delivery_acknowledged",
        fw_building.id,
        {"building_id": str(fw_building.id), "audience": "authority"},
    )
    db_session.add(event)
    await db_session.flush()

    await on_proof_delivered(db_session, event)

    result = await db_session.execute(
        select(DomainEvent).where(DomainEvent.event_type == "flywheel_proof_delivered_refreshed")
    )
    flywheel_event = result.scalar_one_or_none()
    assert flywheel_event is not None
    assert flywheel_event.payload["audience"] == "authority"


@pytest.mark.asyncio
async def test_proof_delivered_updates_metadata(db_session: AsyncSession, fw_building: Building):
    """on_proof_delivered updates building metadata with audience info."""
    event = _make_event(
        "proof_delivery_acknowledged",
        fw_building.id,
        {"building_id": str(fw_building.id), "audience": "insurer"},
    )
    db_session.add(event)
    await db_session.flush()

    await on_proof_delivered(db_session, event)

    await db_session.refresh(fw_building)
    meta = fw_building.source_metadata_json or {}
    flywheel = meta.get("flywheel", {})
    assert flywheel.get("trigger") == "proof_delivered"
    assert flywheel.get("audience") == "insurer"


# ---------------------------------------------------------------------------
# on_post_works_finalized
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_works_finalized_creates_event(db_session: AsyncSession, fw_building: Building):
    """on_post_works_finalized creates a flywheel domain event."""
    event = _make_event(
        "remediation_post_works_finalized",
        fw_building.id,
        {"intervention_id": str(uuid.uuid4()), "verification_rate": 0.95},
    )
    db_session.add(event)
    await db_session.flush()

    await on_post_works_finalized(db_session, event)

    result = await db_session.execute(
        select(DomainEvent).where(DomainEvent.event_type == "flywheel_post_works_refreshed")
    )
    flywheel_event = result.scalar_one_or_none()
    assert flywheel_event is not None
    assert flywheel_event.payload["verification_rate"] == 0.95


@pytest.mark.asyncio
async def test_post_works_finalized_propagates_benchmarks(
    db_session: AsyncSession, fw_building: Building, peer_building: Building
):
    """on_post_works_finalized propagates benchmarks to peer buildings."""
    event = _make_event(
        "remediation_post_works_finalized",
        fw_building.id,
        {"intervention_id": str(uuid.uuid4()), "verification_rate": 0.9},
    )
    db_session.add(event)
    await db_session.flush()

    await on_post_works_finalized(db_session, event)

    await db_session.refresh(peer_building)
    meta = peer_building.source_metadata_json or {}
    peer_signals = meta.get("peer_signals", [])
    assert len(peer_signals) >= 1
    assert peer_signals[0]["signal_type"] == "post_works_finalized"
