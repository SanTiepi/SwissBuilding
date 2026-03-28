"""Tests for source registry model, service, and API."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.source_registry import SourceHealthEvent, SourceRegistryEntry

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_source_registry_entry(db_session):
    """Create a source registry entry and verify fields."""
    entry = SourceRegistryEntry(
        id=uuid.uuid4(),
        name="test_source",
        display_name="Test Source",
        description="A test source",
        family="identity",
        circle=1,
        source_class="official",
        access_mode="api",
        trust_posture="canonical_identity",
        status="active",
        priority="now",
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.name == "test_source"
    assert entry.family == "identity"
    assert entry.circle == 1
    assert entry.active is True


@pytest.mark.asyncio
async def test_create_health_event(db_session):
    """Create a health event linked to a source."""
    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name="health_test_source",
        display_name="Health Test",
        family="spatial",
        circle=2,
        source_class="official",
        access_mode="api",
        trust_posture="observed_context",
    )
    db_session.add(source)
    await db_session.flush()

    event = SourceHealthEvent(
        id=uuid.uuid4(),
        source_id=source.id,
        event_type="healthy",
        description="All good",
    )
    db_session.add(event)
    await db_session.flush()

    assert event.event_type == "healthy"
    assert event.source_id == source.id
    assert event.fallback_used is False


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_get_all_sources_empty(db_session):
    """get_all_sources returns empty list when no sources exist."""
    from app.services.source_registry_service import SourceRegistryService

    sources = await SourceRegistryService.get_all_sources(db_session)
    # May have sources from other test fixtures, but should not error
    assert isinstance(sources, list)


@pytest.mark.asyncio
async def test_service_get_source_not_found(db_session):
    """get_source returns None for unknown name."""
    from app.services.source_registry_service import SourceRegistryService

    result = await SourceRegistryService.get_source(db_session, "nonexistent_source")
    assert result is None


@pytest.mark.asyncio
async def test_service_record_health_event(db_session):
    """record_health_event creates event and updates source status."""
    from app.services.source_registry_service import SourceRegistryService

    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name="svc_health_source",
        display_name="Svc Health Test",
        family="constraint",
        circle=1,
        source_class="official",
        access_mode="api",
        trust_posture="canonical_constraint",
        status="active",
    )
    db_session.add(source)
    await db_session.flush()

    # Record an error event
    event = await SourceRegistryService.record_health_event(
        db_session,
        "svc_health_source",
        "error",
        description="Connection timeout",
        error="TimeoutError",
    )
    assert event is not None
    assert event.event_type == "error"
    assert event.error_detail == "TimeoutError"

    # Source status should update to degraded
    refreshed = await SourceRegistryService.get_source(db_session, "svc_health_source")
    assert refreshed.status == "degraded"


@pytest.mark.asyncio
async def test_service_record_health_event_unknown_source(db_session):
    """record_health_event returns None for unknown source."""
    from app.services.source_registry_service import SourceRegistryService

    result = await SourceRegistryService.record_health_event(db_session, "totally_unknown", "healthy")
    assert result is None


@pytest.mark.asyncio
async def test_service_get_source_health(db_session):
    """get_source_health returns summary with events."""
    from app.services.source_registry_service import SourceRegistryService

    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name="health_detail_source",
        display_name="Health Detail",
        family="identity",
        circle=1,
        source_class="official",
        access_mode="api",
        trust_posture="canonical_identity",
        status="active",
    )
    db_session.add(source)
    await db_session.flush()

    await SourceRegistryService.record_health_event(db_session, "health_detail_source", "healthy")
    await SourceRegistryService.record_health_event(db_session, "health_detail_source", "error", error="500")

    result = await SourceRegistryService.get_source_health(db_session, "health_detail_source")
    assert result["source_name"] == "health_detail_source"
    assert len(result["recent_events"]) == 2


@pytest.mark.asyncio
async def test_service_get_health_dashboard(db_session):
    """get_health_dashboard returns summary across sources."""
    from app.services.source_registry_service import SourceRegistryService

    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name="dashboard_source",
        display_name="Dashboard Source",
        family="identity",
        circle=1,
        source_class="official",
        access_mode="api",
        trust_posture="canonical_identity",
        status="active",
    )
    db_session.add(source)
    await db_session.flush()

    result = await SourceRegistryService.get_health_dashboard(db_session)
    assert "total_sources" in result
    assert "sources" in result
    assert isinstance(result["sources"], list)


@pytest.mark.asyncio
async def test_service_filter_by_family(db_session):
    """get_all_sources filters by family."""
    from app.services.source_registry_service import SourceRegistryService

    for i, fam in enumerate(["identity", "spatial"]):
        source = SourceRegistryEntry(
            id=uuid.uuid4(),
            name=f"filter_{fam}_{i}",
            display_name=f"Filter {fam}",
            family=fam,
            circle=1,
            source_class="official",
            access_mode="api",
            trust_posture="canonical_identity",
            status="active",
        )
        db_session.add(source)
    await db_session.flush()

    identity_sources = await SourceRegistryService.get_all_sources(db_session, family="identity")
    names = [s.name for s in identity_sources]
    assert "filter_identity_0" in names
    assert "filter_spatial_1" not in names


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_list_sources(client: AsyncClient, auth_headers: dict, db_session):
    """GET /sources returns list."""
    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name="api_list_source",
        display_name="API List Source",
        family="identity",
        circle=1,
        source_class="official",
        access_mode="api",
        trust_posture="canonical_identity",
        status="active",
    )
    db_session.add(source)
    await db_session.commit()

    resp = await client.get("/api/v1/sources", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_api_get_source(client: AsyncClient, auth_headers: dict, db_session):
    """GET /sources/{name} returns source detail."""
    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name="api_detail_source",
        display_name="API Detail",
        family="identity",
        circle=1,
        source_class="official",
        access_mode="api",
        trust_posture="canonical_identity",
        status="active",
    )
    db_session.add(source)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/sources/api_detail_source",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "api_detail_source"


@pytest.mark.asyncio
async def test_api_get_source_not_found(client: AsyncClient, auth_headers: dict):
    """GET /sources/{name} returns 404 for unknown source."""
    resp = await client.get(
        "/api/v1/sources/nonexistent",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_health_dashboard(client: AsyncClient, auth_headers: dict):
    """GET /sources/health-dashboard returns dashboard."""
    resp = await client.get(
        "/api/v1/sources/health-dashboard",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_sources" in data


@pytest.mark.asyncio
async def test_api_source_health(client: AsyncClient, auth_headers: dict, db_session):
    """GET /sources/{name}/health returns health events."""
    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name="api_health_source",
        display_name="API Health",
        family="identity",
        circle=1,
        source_class="official",
        access_mode="api",
        trust_posture="canonical_identity",
        status="active",
    )
    db_session.add(source)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/sources/api_health_source/health",
        headers=auth_headers,
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------


def test_seed_sources_list():
    """Verify seed data has expected count and structure."""
    from app.seeds.seed_source_registry import SOURCES

    assert len(SOURCES) >= 20
    for source in SOURCES:
        assert "name" in source
        assert "display_name" in source
        assert "family" in source
        assert "circle" in source
        assert "source_class" in source
        assert "access_mode" in source
        assert "trust_posture" in source


def test_seed_source_names_unique():
    """All seed source names must be unique."""
    from app.seeds.seed_source_registry import SOURCES

    names = [s["name"] for s in SOURCES]
    assert len(names) == len(set(names)), f"Duplicate source names: {[n for n in names if names.count(n) > 1]}"


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


def test_source_constants():
    """Verify source constants are defined."""
    from app.constants import (
        SOURCE_ACCESS_MODES,
        SOURCE_CLASSES,
        SOURCE_FAMILIES,
        SOURCE_FRESHNESS_POLICIES,
        SOURCE_HEALTH_EVENT_TYPES,
        SOURCE_PRIORITIES,
        SOURCE_STATUSES,
        SOURCE_TRUST_POSTURES,
    )

    assert len(SOURCE_FAMILIES) == 9
    assert "identity" in SOURCE_FAMILIES
    assert "official" in SOURCE_CLASSES
    assert "api" in SOURCE_ACCESS_MODES
    assert "canonical_identity" in SOURCE_TRUST_POSTURES
    assert "active" in SOURCE_STATUSES
    assert "now" in SOURCE_PRIORITIES
    assert "healthy" in SOURCE_HEALTH_EVENT_TYPES
    assert "on_demand" in SOURCE_FRESHNESS_POLICIES
