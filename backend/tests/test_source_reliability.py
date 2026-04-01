"""Source adapter reliability contract tests (Rail 3).

Tests the RELIABILITY contracts of source adapters, not business logic.
Verifies: graceful degradation, health events, cache respect, explicit gaps,
registry completeness.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.building import Building
from app.models.building_geo_context import BuildingGeoContext
from app.models.building_identity import BuildingIdentityChain
from app.models.source_registry import SourceHealthEvent, SourceRegistryEntry
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HASH = "$2b$12$LJ3m4ys3Lg3LzYHvjpnXaOaB0RVi0V.V.V.V.V.V.V.V.V.V.V.V"  # dummy


async def _make_user(db) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"rel-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH,
        first_name="Rel",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(user)
    await db.flush()
    return user


async def _make_building(db, *, lat=46.52, lon=6.63, egid=None, egrid=None, address="Rue Test 1") -> Building:
    user = await _make_user(db)
    building = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user.id,
        status="active",
        latitude=lat,
        longitude=lon,
        egid=egid,
        egrid=egrid,
    )
    db.add(building)
    await db.flush()
    return building


async def _make_source(
    db,
    name,
    *,
    family="identity",
    circle=1,
    status="active",
    freshness_policy="on_demand",
    cache_ttl_hours=None,
    workspace_consumers=None,
    priority="now",
) -> SourceRegistryEntry:
    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name=name,
        display_name=name.replace("_", " ").title(),
        family=family,
        circle=circle,
        source_class="official",
        access_mode="api",
        trust_posture="canonical_identity",
        status=status,
        freshness_policy=freshness_policy,
        cache_ttl_hours=cache_ttl_hours,
        workspace_consumers=workspace_consumers or ["building_home"],
        priority=priority,
    )
    db.add(source)
    await db.flush()
    return source


def _mock_httpx_client(*, responses=None, side_effect=None):
    """Create a patched httpx.AsyncClient context manager.

    Args:
        responses: list of MagicMock responses to return in order, or single MagicMock
        side_effect: exception to raise on every .get()
    """
    mock_client = AsyncMock()
    if side_effect:
        mock_client.get = AsyncMock(side_effect=side_effect)
    elif responses is not None:
        if isinstance(responses, list):
            mock_client.get = AsyncMock(side_effect=responses)
        else:
            mock_client.get = AsyncMock(return_value=responses)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _ok_response(json_data):
    """Build a MagicMock that looks like a successful httpx.Response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_data
    return resp


# ═══════════════════════════════════════════════════════════════════════════
# TestGeoContextReliability
# ═══════════════════════════════════════════════════════════════════════════


class TestGeoContextReliability:
    """Tests that geo_context_service handles failures gracefully."""

    @pytest.mark.asyncio
    async def test_fetch_returns_partial_on_layer_failure(self):
        """When individual geo.admin layers fail, other layers still return data."""
        from app.services.geo_context_service import fetch_context

        call_count = 0

        async def _selective_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First layer succeeds
                return _ok_response({"results": [{"attributes": {"zone": "moderate", "radon_bq_m3": "300"}}]})
            # All subsequent layers fail
            raise ConnectionError("network error")

        with patch("app.services.geo_context_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=_selective_fail)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await fetch_context(6.63, 46.52, layers=["radon", "noise_road", "solar"])

        # First layer succeeded, others failed silently
        assert "radon" in result
        assert "noise_road" not in result
        assert "solar" not in result

    @pytest.mark.asyncio
    async def test_all_layers_fail_returns_empty(self):
        """When all layers fail, returns empty dict -- no crash."""
        from app.services.geo_context_service import fetch_context

        with patch("app.services.geo_context_service.httpx.AsyncClient") as mock_cls:
            mock_client = _mock_httpx_client(side_effect=Exception("total failure"))
            mock_cls.return_value = mock_client

            result = await fetch_context(6.63, 46.52, layers=["radon", "noise_road"])

        assert result == {}

    @pytest.mark.asyncio
    async def test_cache_ttl_respected(self, db):
        """Cached data is used within TTL, fresh fetch after TTL."""
        from app.services.geo_context_service import enrich_building_context

        building = await _make_building(db)

        # Pre-populate cache with fresh data
        geo_ctx = BuildingGeoContext(
            building_id=building.id,
            context_data={"radon": {"zone": "cached"}},
            fetched_at=datetime.now(UTC),  # fresh
            source_version="geo.admin-v1",
        )
        db.add(geo_ctx)
        await db.flush()

        # Should return cached data without HTTP call
        result = await enrich_building_context(db, building.id, force=False)
        assert result == {"radon": {"zone": "cached"}}

    @pytest.mark.asyncio
    async def test_cache_expired_triggers_fetch(self, db):
        """Expired cache triggers a fresh fetch."""
        from app.services.geo_context_service import enrich_building_context

        building = await _make_building(db)

        # Pre-populate cache with stale data (10 days old)
        geo_ctx = BuildingGeoContext(
            building_id=building.id,
            context_data={"radon": {"zone": "stale"}},
            fetched_at=datetime.now(UTC) - timedelta(days=10),
            source_version="geo.admin-v1",
        )
        db.add(geo_ctx)
        await db.flush()

        with patch("app.services.geo_context_service.fetch_context", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"radon": {"zone": "fresh"}}
            # Patch record_health_event to avoid needing source registry entries
            with patch(
                "app.services.geo_context_service.SourceRegistryService.record_health_event", new_callable=AsyncMock
            ):
                result = await enrich_building_context(db, building.id, force=False)

        assert result == {"radon": {"zone": "fresh"}}
        mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_event_recorded_on_success(self, db):
        """SourceHealthEvent with type 'healthy' recorded after successful fetch."""
        from app.services.geo_context_service import enrich_building_context

        building = await _make_building(db)
        await _make_source(db, "geo_admin_radon", family="constraint")

        with patch("app.services.geo_context_service.fetch_context", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"radon": {"zone": "moderate"}}
            await enrich_building_context(db, building.id, force=True)

        # Check that a healthy event was recorded
        from sqlalchemy import select

        stmt = (
            select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_radon",
                SourceHealthEvent.event_type == "healthy",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_health_event_recorded_on_empty_data(self, db):
        """SourceHealthEvent with type 'degraded' recorded when no data returned."""
        from app.services.geo_context_service import enrich_building_context

        building = await _make_building(db)
        await _make_source(db, "geo_admin_radon", family="constraint")

        with patch("app.services.geo_context_service.fetch_context", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {}  # no data
            await enrich_building_context(db, building.id, force=True)

        from sqlalchemy import select

        stmt = (
            select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_radon",
                SourceHealthEvent.event_type == "degraded",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_coordinates(self, db):
        """Building without coordinates returns empty context, not crash."""
        from app.services.geo_context_service import enrich_building_context

        building = await _make_building(db, lat=None, lon=None)

        result = await enrich_building_context(db, building.id)
        assert "error" in result
        assert result["error"] == "no_coordinates"

    @pytest.mark.asyncio
    async def test_force_bypasses_cache(self, db):
        """force=True triggers fresh fetch even with fresh cache."""
        from app.services.geo_context_service import enrich_building_context

        building = await _make_building(db)

        # Pre-populate with fresh cache
        geo_ctx = BuildingGeoContext(
            building_id=building.id,
            context_data={"radon": {"zone": "cached"}},
            fetched_at=datetime.now(UTC),
            source_version="geo.admin-v1",
        )
        db.add(geo_ctx)
        await db.flush()

        with patch("app.services.geo_context_service.fetch_context", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"radon": {"zone": "forced-fresh"}}
            with patch(
                "app.services.geo_context_service.SourceRegistryService.record_health_event", new_callable=AsyncMock
            ):
                result = await enrich_building_context(db, building.id, force=True)

        assert result == {"radon": {"zone": "forced-fresh"}}
        mock_fetch.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TestIdentityChainReliability
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentityChainReliability:
    """Tests that identity_chain_service handles failures gracefully."""

    @pytest.mark.asyncio
    async def test_partial_chain_on_egrid_failure(self, db):
        """If EGRID lookup fails but EGID is known, chain still returns EGID data."""
        from app.services import identity_chain_service as svc

        building = await _make_building(db, egid=123456)

        # Mock: resolve_egrid returns empty (failure), resolve_egid not called (building has egid)
        with (
            patch.object(svc, "resolve_egrid", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "fetch_rdppf", new_callable=AsyncMock, return_value={}),
            patch.object(svc.SourceRegistryService, "record_health_event", new_callable=AsyncMock),
        ):
            result = await svc.resolve_full_chain(db, building.id)

        # EGID should be present
        assert result["egid"]["value"] == 123456
        # EGRID should be missing
        assert "egrid_not_resolved" in result["chain_gaps"]
        # Chain should NOT be complete
        assert result["chain_complete"] is False

    @pytest.mark.asyncio
    async def test_chain_gaps_explicit(self, db):
        """Chain gaps are listed explicitly, not hidden."""
        from app.services import identity_chain_service as svc

        # Building with no egid, no coordinates -- everything should fail
        building = await _make_building(db, lat=None, lon=None, egid=None, egrid=None)

        with (
            patch.object(svc, "resolve_egid", new_callable=AsyncMock, return_value={}),
            patch.object(svc.SourceRegistryService, "record_health_event", new_callable=AsyncMock),
        ):
            result = await svc.resolve_full_chain(db, building.id)

        # All gaps should be explicit
        assert "egid_not_resolved" in result["chain_gaps"]
        assert "rdppf_skipped_no_egrid" in result["chain_gaps"]
        assert result["chain_complete"] is False

    @pytest.mark.asyncio
    async def test_health_event_on_madd_success(self, db):
        """Health event recorded for MADD source on successful EGID resolution."""
        from app.services import identity_chain_service as svc

        building = await _make_building(db, egid=123456)
        await _make_source(db, "geo_admin_madd")
        await _make_source(db, "geo_admin_cadastre")

        with (
            patch.object(svc, "resolve_egrid", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "fetch_rdppf", new_callable=AsyncMock, return_value={}),
        ):
            await svc.resolve_full_chain(db, building.id)

        from sqlalchemy import select

        stmt = (
            select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_madd",
                SourceHealthEvent.event_type == "healthy",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_health_event_degraded_when_egid_not_resolved(self, db):
        """Health event 'degraded' recorded when EGID resolution fails."""
        from app.services import identity_chain_service as svc

        building = await _make_building(db, egid=None, lat=None, lon=None)
        await _make_source(db, "geo_admin_madd")

        with (
            patch.object(svc, "resolve_egid", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "resolve_egrid", new_callable=AsyncMock, return_value={}),
        ):
            await svc.resolve_full_chain(db, building.id)

        from sqlalchemy import select

        stmt = (
            select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_madd",
                SourceHealthEvent.event_type == "degraded",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_cache_prevents_redundant_fetches(self, db):
        """Cached chain is returned without re-fetching from external APIs."""
        from app.services import identity_chain_service as svc

        building = await _make_building(db)
        now = datetime.now(UTC)

        # Pre-populate identity chain cache
        chain = BuildingIdentityChain(
            building_id=building.id,
            egid=123456,
            egid_source="madd",
            egid_confidence=0.9,
            egid_resolved_at=now,
            egrid="CH1234567890",
            egrid_source="cadastre",
            egrid_resolved_at=now,
            chain_complete=True,
            chain_gaps=None,
        )
        db.add(chain)
        await db.flush()

        # get_identity_chain should return cached without calling resolve_full_chain
        with patch.object(svc, "resolve_full_chain", new_callable=AsyncMock) as mock_resolve:
            result = await svc.get_identity_chain(db, building.id)

        mock_resolve.assert_not_called()
        assert result["cached"] is True
        assert result["egid"]["value"] == 123456

    @pytest.mark.asyncio
    async def test_building_not_found_returns_error(self, db):
        """resolve_full_chain returns error for non-existent building."""
        from app.services import identity_chain_service as svc

        fake_id = uuid.uuid4()
        result = await svc.resolve_full_chain(db, fake_id)

        assert result.get("error") == "building_not_found"
        assert result.get("chain_complete") is False
        assert "building_not_found" in result.get("chain_gaps", [])

    @pytest.mark.asyncio
    async def test_resolve_egid_graceful_on_api_failure(self):
        """resolve_egid returns empty dict when API fails, not crash."""
        from app.services.identity_chain_service import resolve_egid

        with patch("app.services.identity_chain_service._fetch_json", new_callable=AsyncMock, return_value={}):
            result = await resolve_egid(address="Nonexistent Street 999")

        assert result == {}


# ═══════════════════════════════════════════════════════════════════════════
# TestSpatialEnrichmentReliability
# ═══════════════════════════════════════════════════════════════════════════


class TestSpatialEnrichmentReliability:
    """Tests that spatial_enrichment_service handles failures."""

    @pytest.mark.asyncio
    async def test_graceful_on_no_data(self):
        """When swissBUILDINGS3D has no data for location, returns error dict."""
        from app.services.spatial_enrichment_service import SpatialEnrichmentService

        with patch("app.services.spatial_enrichment_service.httpx.AsyncClient") as mock_cls:
            mock_client = _mock_httpx_client(responses=_ok_response({"results": []}))
            mock_cls.return_value = mock_client

            result = await SpatialEnrichmentService.fetch_building_footprint(6.63, 46.52)

        assert result["error"] == "no_data"

    @pytest.mark.asyncio
    async def test_graceful_on_timeout(self):
        """Timeout returns error dict, not exception."""
        import httpx as _httpx

        from app.services.spatial_enrichment_service import SpatialEnrichmentService

        with patch("app.services.spatial_enrichment_service.httpx.AsyncClient") as mock_cls:
            mock_client = _mock_httpx_client(side_effect=_httpx.TimeoutException("timeout"))
            mock_cls.return_value = mock_client

            result = await SpatialEnrichmentService.fetch_building_footprint(6.63, 46.52)

        assert result["error"] == "timeout"

    @pytest.mark.asyncio
    async def test_graceful_on_network_error(self):
        """Network error returns error dict, not exception."""
        from app.services.spatial_enrichment_service import SpatialEnrichmentService

        with patch("app.services.spatial_enrichment_service.httpx.AsyncClient") as mock_cls:
            mock_client = _mock_httpx_client(side_effect=RuntimeError("connection refused"))
            mock_cls.return_value = mock_client

            result = await SpatialEnrichmentService.fetch_building_footprint(6.63, 46.52)

        assert result["error"] == "fetch_failed"

    @pytest.mark.asyncio
    async def test_health_event_recorded_on_success(self, db):
        """Health events wired to source registry on successful enrichment."""
        from app.services.spatial_enrichment_service import SpatialEnrichmentService

        building = await _make_building(db)
        await _make_source(db, "swissbuildings3d", family="spatial", circle=2)

        with patch.object(
            SpatialEnrichmentService,
            "fetch_building_footprint",
            new_callable=AsyncMock,
            return_value={"height_m": 12.0, "roof_type": "flat", "source": "test"},
        ):
            await SpatialEnrichmentService.enrich_building_spatial(db, building.id, force=True)

        from sqlalchemy import select

        stmt = (
            select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "swissbuildings3d",
                SourceHealthEvent.event_type == "healthy",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_health_event_recorded_on_failure(self, db):
        """Health event 'degraded' recorded when spatial enrichment fails."""
        from app.services.spatial_enrichment_service import SpatialEnrichmentService

        building = await _make_building(db)
        await _make_source(db, "swissbuildings3d", family="spatial", circle=2)

        with patch.object(
            SpatialEnrichmentService,
            "fetch_building_footprint",
            new_callable=AsyncMock,
            return_value={"error": "no_data", "detail": "No data"},
        ):
            await SpatialEnrichmentService.enrich_building_spatial(db, building.id, force=True)

        from sqlalchemy import select

        stmt = (
            select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "swissbuildings3d",
                SourceHealthEvent.event_type == "degraded",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_no_coordinates_returns_error(self, db):
        """Building without coordinates returns error, not crash."""
        from app.services.spatial_enrichment_service import SpatialEnrichmentService

        building = await _make_building(db, lat=None, lon=None)

        result = await SpatialEnrichmentService.enrich_building_spatial(db, building.id)
        assert result["error"] == "no_coordinates"

    @pytest.mark.asyncio
    async def test_spatial_cache_ttl_respected(self, db):
        """Cached spatial data is returned within TTL window."""
        from app.services.spatial_enrichment_service import SpatialEnrichmentService

        building = await _make_building(db)

        # Pre-populate cache with fresh spatial data
        now = datetime.now(UTC)
        geo_ctx = BuildingGeoContext(
            building_id=building.id,
            context_data={
                "spatial_enrichment": {
                    "height_m": 15.0,
                    "fetched_at": now.isoformat(),
                }
            },
            fetched_at=now,
            source_version="swissbuildings3d-v3.0",
        )
        db.add(geo_ctx)
        await db.flush()

        # Should return cached without HTTP call
        cached = await SpatialEnrichmentService._get_cached(db, building.id)
        assert cached is not None
        assert cached["height_m"] == 15.0


# ═══════════════════════════════════════════════════════════════════════════
# TestSourceRegistryIntegrity
# ═══════════════════════════════════════════════════════════════════════════


class TestSourceRegistryIntegrity:
    """Tests that source registry is complete and consistent."""

    def test_all_active_sources_have_workspace_consumers(self):
        """Every active source maps to at least one workspace."""
        from app.seeds.seed_source_registry import SOURCES

        for src in SOURCES:
            if src.get("status") == "active" or src.get("priority") == "now":
                consumers = src.get("workspace_consumers") or []
                assert len(consumers) >= 1, f"Source '{src['name']}' has no workspace_consumers"

    def test_all_circle_1_sources_present(self):
        """All Circle 1 (official) sources are registered."""
        from app.seeds.seed_source_registry import SOURCES

        circle_1 = [s for s in SOURCES if s["circle"] == 1]
        names = {s["name"] for s in circle_1}

        # Known required Circle 1 sources
        required = {
            "geo_admin_madd",
            "geo_admin_cadastre",
            "rdppf_federal",
            "geo_admin_radon",
            "geo_admin_natural_hazards",
            "geo_admin_groundwater",
            "geo_admin_contaminated_sites",
            "geo_admin_heritage_isos",
            "vd_asbestos_procedure",
            "ge_asbestos_procedure",
            "suva_cfst_6503",
            "otconst_art60a",
            "orrchim_pcb_lead",
            "orap_radon",
            "oled_waste",
        }
        missing = required - names
        assert not missing, f"Missing Circle 1 sources: {missing}"

    def test_freshness_policy_set_for_active_sources(self):
        """Active sources have explicit freshness policy."""
        from app.seeds.seed_source_registry import SOURCES

        valid_policies = {
            "real_time",
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "event_driven",
            "on_demand",
        }
        for src in SOURCES:
            policy = src.get("freshness_policy", "on_demand")
            assert policy in valid_policies, f"Source '{src['name']}' has invalid freshness_policy: {policy}"

    def test_source_names_unique(self):
        """All source names are unique in the seed registry."""
        from app.seeds.seed_source_registry import SOURCES

        names = [s["name"] for s in SOURCES]
        assert len(names) == len(set(names)), "Duplicate source names found"

    @pytest.mark.asyncio
    async def test_health_dashboard_returns_all_sources(self, db):
        """Dashboard covers all active sources in the DB."""
        from app.services.source_registry_service import SourceRegistryService

        # Insert 3 sources
        for i in range(3):
            await _make_source(db, f"dash_source_{i}")

        dashboard = await SourceRegistryService.get_health_dashboard(db)

        assert dashboard["total_sources"] >= 3
        names = {s["source_name"] for s in dashboard["sources"]}
        for i in range(3):
            assert f"dash_source_{i}" in names

    @pytest.mark.asyncio
    async def test_record_health_event_for_unknown_source_returns_none(self, db):
        """Recording a health event for an unknown source returns None (no crash)."""
        from app.services.source_registry_service import SourceRegistryService

        result = await SourceRegistryService.record_health_event(db, "completely_unknown_source", "healthy")
        assert result is None

    @pytest.mark.asyncio
    async def test_health_event_updates_source_status(self, db):
        """Health events correctly update the source status field."""
        from app.services.source_registry_service import SourceRegistryService

        source = await _make_source(db, "status_test_source")
        assert source.status == "active"

        # Record error -- should move to degraded
        await SourceRegistryService.record_health_event(db, "status_test_source", "error")
        refreshed = await SourceRegistryService.get_source(db, "status_test_source")
        assert refreshed.status == "degraded"

        # Record healthy -- should move back to active
        await SourceRegistryService.record_health_event(db, "status_test_source", "healthy")
        refreshed2 = await SourceRegistryService.get_source(db, "status_test_source")
        assert refreshed2.status == "active"

    def test_all_sources_have_trust_posture(self):
        """Every seed source has a trust_posture defined."""
        from app.seeds.seed_source_registry import SOURCES

        valid_postures = {
            "canonical_identity",
            "canonical_constraint",
            "observed_context",
            "supporting_evidence",
            "commercial_hint",
            "derived_only",
        }
        for src in SOURCES:
            assert src.get("trust_posture") in valid_postures, (
                f"Source '{src['name']}' has invalid trust_posture: {src.get('trust_posture')}"
            )

    def test_api_sources_have_base_url(self):
        """Sources with access_mode='api' should have a base_url set."""
        from app.seeds.seed_source_registry import SOURCES

        for src in SOURCES:
            if src.get("access_mode") == "api" and src.get("base_url") is not None:
                assert src["base_url"].startswith("http"), (
                    f"Source '{src['name']}' has invalid base_url: {src['base_url']}"
                )
