"""Tests that ALL geo.admin fetchers are wired and called in the enrichment pipeline.

Verifies:
1. All 23 geo.admin fetchers are called during enrichment
2. Graceful degradation when individual fetchers fail
3. enrichment_meta contains all expected keys after successful enrichment
"""

from __future__ import annotations

import contextlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# All 23 geo.admin fetchers -- canonical list
# ---------------------------------------------------------------------------

GEO_ADMIN_FETCHERS: list[dict[str, str]] = [
    {"name": "fetch_radon_risk", "meta_key": "radon", "result_flag": "radon_fetched"},
    {"name": "fetch_natural_hazards", "meta_key": "natural_hazards", "result_flag": "natural_hazards_fetched"},
    {"name": "fetch_noise_data", "meta_key": "noise", "result_flag": "noise_fetched"},
    {"name": "fetch_solar_potential", "meta_key": "solar", "result_flag": "solar_fetched"},
    {"name": "fetch_heritage_status", "meta_key": "heritage", "result_flag": "heritage_fetched"},
    {"name": "fetch_transport_quality", "meta_key": "transport", "result_flag": "transport_fetched"},
    {"name": "fetch_seismic_zone", "meta_key": "seismic", "result_flag": "seismic_fetched"},
    {"name": "fetch_water_protection", "meta_key": "water_protection", "result_flag": "water_protection_fetched"},
    {"name": "fetch_railway_noise", "meta_key": "railway_noise", "result_flag": "railway_noise_fetched"},
    {"name": "fetch_aircraft_noise", "meta_key": "aircraft_noise", "result_flag": "aircraft_noise_fetched"},
    {"name": "fetch_building_zones", "meta_key": "building_zones", "result_flag": "building_zones_fetched"},
    {
        "name": "fetch_contaminated_sites",
        "meta_key": "contaminated_sites",
        "result_flag": "contaminated_sites_fetched",
    },
    {"name": "fetch_groundwater_zones", "meta_key": "groundwater_zones", "result_flag": "groundwater_zones_fetched"},
    {"name": "fetch_flood_zones", "meta_key": "flood_zones", "result_flag": "flood_zones_fetched"},
    {"name": "fetch_mobile_coverage", "meta_key": "mobile_coverage", "result_flag": "mobile_coverage_fetched"},
    {"name": "fetch_broadband", "meta_key": "broadband", "result_flag": "broadband_fetched"},
    {"name": "fetch_ev_charging", "meta_key": "ev_charging", "result_flag": "ev_charging_fetched"},
    {"name": "fetch_thermal_networks", "meta_key": "thermal_networks", "result_flag": "thermal_networks_fetched"},
    {
        "name": "fetch_protected_monuments",
        "meta_key": "protected_monuments",
        "result_flag": "protected_monuments_fetched",
    },
    {"name": "fetch_agricultural_zones", "meta_key": "agricultural_zones", "result_flag": "agricultural_zones_fetched"},
    {"name": "fetch_forest_reserves", "meta_key": "forest_reserves", "result_flag": "forest_reserves_fetched"},
    {"name": "fetch_military_zones", "meta_key": "military_zones", "result_flag": "military_zones_fetched"},
    {"name": "fetch_accident_sites", "meta_key": "accident_sites", "result_flag": "accident_sites_fetched"},
]

EXPECTED_META_KEYS: list[str] = [f["meta_key"] for f in GEO_ADMIN_FETCHERS]

# Module path prefix for patching (backward-compat shim)
_P = "app.services.building_enrichment_service"


def _make_mock_building(building_id: uuid.UUID | None = None):
    """Create a mock building with coordinates for enrichment."""
    bid = building_id or uuid.uuid4()
    bld = MagicMock()
    bld.id = bid
    bld.address = "Rue de Bourg 1"
    bld.postal_code = "1003"
    bld.city = "Lausanne"
    bld.canton = "VD"
    bld.latitude = 46.5197
    bld.longitude = 6.6323
    bld.egid = 123456
    bld.egrid = None
    bld.parcel_number = None
    bld.construction_year = 1965
    bld.building_type = "residential"
    bld.floors_above = 5
    bld.surface_area_m2 = 850.0
    bld.renovation_year = None
    bld.volume_m3 = None
    bld.dwellings = None
    bld.has_elevator = False
    bld.source_metadata_json = {}
    return bld


def _mock_db_session(building):
    """Create a mock async DB session that returns the given building."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = building
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


def _build_patches(
    geo_overrides: dict[str, object] | None = None,
) -> contextlib.ExitStack:
    """Build an ExitStack of patches for all fetchers.

    *geo_overrides* maps fetcher name -> mock to use for that fetcher.
    Fetchers not in geo_overrides get a default AsyncMock returning ``{"test_data": True}``.
    """
    stack = contextlib.ExitStack()
    # Core pipeline mocks (non-geo-admin)
    core_mocks = {
        "geocode_address": AsyncMock(return_value={}),
        "fetch_regbl_data": AsyncMock(return_value={}),
        "enrich_building_with_ai": AsyncMock(return_value={}),
        "fetch_cadastre_egrid": AsyncMock(return_value={}),
        "fetch_osm_amenities": AsyncMock(return_value={}),
        "fetch_osm_building_details": AsyncMock(return_value={}),
        "fetch_climate_data": MagicMock(return_value={}),
        "fetch_nearest_stops": AsyncMock(return_value={}),
        "_throttle": AsyncMock(),
    }
    for name, mock_obj in core_mocks.items():
        stack.enter_context(patch(f"{_P}.{name}", mock_obj))

    # Geo-admin fetcher mocks
    overrides = geo_overrides or {}
    for f in GEO_ADMIN_FETCHERS:
        mock_obj = overrides.get(f["name"], AsyncMock(return_value={"test_data": True}))
        stack.enter_context(patch(f"{_P}.{f['name']}", mock_obj))

    return stack


# ---------------------------------------------------------------------------
# Test: all 23 fetchers are called
# ---------------------------------------------------------------------------


class TestAllFetchersCalled:
    """Verify every geo.admin fetcher is invoked during enrichment."""

    @pytest.mark.asyncio
    async def test_all_23_fetchers_called_during_enrichment(self):
        """The orchestrator calls all 23 geo.admin fetchers when building has coordinates."""
        building = _make_mock_building()
        db = _mock_db_session(building)

        # Track which fetchers were called
        called_fetchers: set[str] = set()

        def _make_tracker(name: str, return_value: dict):
            async def _tracked(*args, **kwargs):
                called_fetchers.add(name)
                return return_value

            return _tracked

        overrides = {}
        for f in GEO_ADMIN_FETCHERS:
            overrides[f["name"]] = _make_tracker(f["name"], {"test_data": True})

        with _build_patches(geo_overrides=overrides):
            from app.services.enrichment.orchestrator import enrich_building

            await enrich_building(
                db,
                building.id,
                skip_geocode=True,
                skip_regbl=True,
                skip_ai=True,
                skip_cadastre=True,
                skip_image=True,
            )

        # Verify all 23 were called
        expected = {f["name"] for f in GEO_ADMIN_FETCHERS}
        missing = expected - called_fetchers
        assert not missing, f"These geo.admin fetchers were NOT called: {missing}"
        assert len(called_fetchers) == 23

    @pytest.mark.asyncio
    async def test_fetcher_count_is_23(self):
        """Canonical count: exactly 23 geo.admin fetchers exist."""
        from app.services.enrichment import geo_admin_fetchers

        fetcher_names = [
            name
            for name in dir(geo_admin_fetchers)
            if name.startswith("fetch_") and callable(getattr(geo_admin_fetchers, name))
        ]
        assert len(fetcher_names) == 23, f"Expected 23 geo.admin fetchers, found {len(fetcher_names)}: {fetcher_names}"

    @pytest.mark.asyncio
    async def test_all_fetchers_imported_in_orchestrator(self):
        """Every fetcher from geo_admin_fetchers.py is imported in orchestrator.py."""
        from app.services.enrichment import geo_admin_fetchers, orchestrator

        fetcher_names = [
            name
            for name in dir(geo_admin_fetchers)
            if name.startswith("fetch_") and callable(getattr(geo_admin_fetchers, name))
        ]
        for name in fetcher_names:
            assert hasattr(orchestrator, name) or name in dir(orchestrator), (
                f"Fetcher {name} not imported in orchestrator"
            )


# ---------------------------------------------------------------------------
# Test: graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Verify that a failing fetcher does not crash the pipeline."""

    @pytest.mark.asyncio
    async def test_single_fetcher_failure_does_not_block_pipeline(self):
        """If fetch_radon_risk raises, other fetchers still run and result is returned."""
        building = _make_mock_building()
        db = _mock_db_session(building)

        async def _raise_radon(*args, **kwargs):
            raise RuntimeError("Radon API exploded")

        overrides = {"fetch_radon_risk": _raise_radon}

        with _build_patches(geo_overrides=overrides):
            from app.services.enrichment.orchestrator import enrich_building

            result = await enrich_building(
                db,
                building.id,
                skip_geocode=True,
                skip_regbl=True,
                skip_ai=True,
                skip_cadastre=True,
                skip_image=True,
            )

        # Pipeline completed (no crash)
        assert result is not None
        assert result.building_id == building.id
        # Radon was NOT fetched
        assert result.radon_fetched is False
        # Error was logged
        assert any("fetch_radon_risk" in e for e in result.errors)
        # Other fetchers succeeded
        assert result.noise_fetched is True
        assert result.solar_fetched is True
        assert result.heritage_fetched is True

    @pytest.mark.asyncio
    async def test_multiple_fetcher_failures_still_complete(self):
        """Pipeline completes even when multiple fetchers fail."""
        building = _make_mock_building()
        db = _mock_db_session(building)

        failing_fetchers = {"fetch_radon_risk", "fetch_noise_data", "fetch_flood_zones", "fetch_military_zones"}

        async def _raise(*args, **kwargs):
            raise RuntimeError("API down")

        overrides = {name: _raise for name in failing_fetchers}

        with _build_patches(geo_overrides=overrides):
            from app.services.enrichment.orchestrator import enrich_building

            result = await enrich_building(
                db,
                building.id,
                skip_geocode=True,
                skip_regbl=True,
                skip_ai=True,
                skip_cadastre=True,
                skip_image=True,
            )

        assert result is not None
        # 4 failures recorded
        failure_errors = [e for e in result.errors if "failed:" in e]
        assert len(failure_errors) == 4
        # Non-failing fetchers succeeded
        assert result.solar_fetched is True
        assert result.heritage_fetched is True
        assert result.transport_fetched is True

    @pytest.mark.asyncio
    async def test_no_coords_skips_all_fetchers(self):
        """When building has no coordinates, geo.admin fetchers are skipped gracefully."""
        building = _make_mock_building()
        building.latitude = None
        building.longitude = None
        db = _mock_db_session(building)

        # Only need core mocks -- geo fetchers should never be called
        core = {
            "geocode_address": AsyncMock(return_value={}),
            "fetch_regbl_data": AsyncMock(return_value={}),
            "enrich_building_with_ai": AsyncMock(return_value={}),
            "fetch_cadastre_egrid": AsyncMock(return_value={}),
            "_throttle": AsyncMock(),
        }
        stack = contextlib.ExitStack()
        for name, mock_obj in core.items():
            stack.enter_context(patch(f"{_P}.{name}", mock_obj))

        with stack:
            from app.services.enrichment.orchestrator import enrich_building

            result = await enrich_building(
                db,
                building.id,
                skip_geocode=True,
                skip_regbl=True,
                skip_ai=True,
                skip_cadastre=True,
                skip_image=True,
            )

        # No fetcher flags set
        for f in GEO_ADMIN_FETCHERS:
            assert getattr(result, f["result_flag"]) is False


# ---------------------------------------------------------------------------
# Test: enrichment_meta keys
# ---------------------------------------------------------------------------


class TestEnrichmentMetaKeys:
    """Verify enrichment_meta contains all expected keys after successful enrichment."""

    @pytest.mark.asyncio
    async def test_all_meta_keys_present_after_success(self):
        """After successful enrichment, enrichment_meta has entries for all 23 fetchers."""
        building = _make_mock_building()
        db = _mock_db_session(building)

        overrides = {}
        for f in GEO_ADMIN_FETCHERS:
            overrides[f["name"]] = AsyncMock(return_value={"test_key": f["meta_key"]})

        with _build_patches(geo_overrides=overrides):
            from app.services.enrichment.orchestrator import enrich_building

            await enrich_building(
                db,
                building.id,
                skip_geocode=True,
                skip_regbl=True,
                skip_ai=True,
                skip_cadastre=True,
                skip_image=True,
            )

        # Check that source_metadata_json was updated with all keys
        meta = building.source_metadata_json
        for key in EXPECTED_META_KEYS:
            assert key in meta, f"enrichment_meta missing key: {key}"

    @pytest.mark.asyncio
    async def test_all_result_flags_true_after_success(self):
        """After successful enrichment, all fetched flags on EnrichmentResult are True."""
        building = _make_mock_building()
        db = _mock_db_session(building)

        overrides = {}
        for f in GEO_ADMIN_FETCHERS:
            overrides[f["name"]] = AsyncMock(return_value={"test_key": True})

        with _build_patches(geo_overrides=overrides):
            from app.services.enrichment.orchestrator import enrich_building

            result = await enrich_building(
                db,
                building.id,
                skip_geocode=True,
                skip_regbl=True,
                skip_ai=True,
                skip_cadastre=True,
                skip_image=True,
            )

        for f in GEO_ADMIN_FETCHERS:
            assert getattr(result, f["result_flag"]) is True, f"result.{f['result_flag']} should be True but is False"
