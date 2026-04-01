"""Tests that swissBUILDINGS3D spatial data is persisted in enrichment_meta.

Verifies:
1. enrichment_meta contains spatial keys after enrichment with valid spatial data
2. Mock spatial data maps correctly to the canonical enrichment_meta keys
3. Graceful handling when swissBUILDINGS3D returns nothing (no error, no keys)
"""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Canonical spatial keys expected in enrichment_meta
# ---------------------------------------------------------------------------

SPATIAL_META_KEYS = [
    "building_height_m",
    "building_volume_m3",
    "floor_count_3d",
    "roof_type",
    "footprint_area_m2",
    "spatial_source",
    "spatial_fetched_at",
]

# Module under test — all patches target this module
_O = "app.services.enrichment.orchestrator"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    bld.egid = 1234567
    bld.egrid = None
    bld.parcel_number = None
    bld.construction_year = 1965
    bld.renovation_year = None
    bld.building_type = "residential"
    bld.floors_above = 4
    bld.floors_below = None
    bld.surface_area_m2 = None
    bld.volume_m3 = None
    bld.dwellings = None
    bld.has_elevator = False
    bld.source_metadata_json = {}
    bld.status = "active"
    return bld


def _mock_db_session(building):
    """Create a mock async DB session that returns the given building."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = building
    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


def _full_spatial_response():
    """Return a complete spatial response mimicking swissBUILDINGS3D output."""
    return {
        "footprint_wkt": "POLYGON((6.632 46.519, 6.633 46.519, 6.633 46.520, 6.632 46.520, 6.632 46.519))",
        "height_m": 12.5,
        "roof_type": "Flachdach",
        "volume_m3": 3750.0,
        "surface_m2": 300.0,
        "floors": 4,
        "source": "ch.swisstopo.swissbuildings3d_3_0.v2",
        "source_version": "swissbuildings3d-v3.0",
        "raw_attributes": {"gebaeudehoehe": 12.5, "dachform": "Flachdach"},
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def _empty_spatial_response():
    """Return an error response when swissBUILDINGS3D has no data."""
    return {
        "error": "no_data",
        "detail": "Aucune donnee swissBUILDINGS3D a cette position",
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def _partial_spatial_response():
    """Return a partial spatial response (height only, no footprint/volume)."""
    return {
        "footprint_wkt": None,
        "height_m": 9.8,
        "roof_type": None,
        "volume_m3": None,
        "surface_m2": None,
        "floors": None,
        "source": "ch.swisstopo.swissbuildings3d_3_0.v2",
        "source_version": "swissbuildings3d-v3.0",
        "raw_attributes": {"gebaeudehoehe": 9.8},
        "fetched_at": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# Common patch context: silence all non-spatial fetchers
# ---------------------------------------------------------------------------


def _base_patches() -> dict[str, AsyncMock | MagicMock]:
    """Return patch target -> mock dict that stubs out all non-spatial fetchers."""
    return {
        f"{_O}.geocode_address": AsyncMock(return_value={}),
        f"{_O}.fetch_regbl_data": AsyncMock(return_value={}),
        f"{_O}.enrich_building_with_ai": AsyncMock(return_value={}),
        f"{_O}.fetch_cadastre_egrid": AsyncMock(return_value={}),
        f"{_O}.fetch_swisstopo_image_url": MagicMock(return_value=""),
        f"{_O}.fetch_radon_risk": AsyncMock(return_value={}),
        f"{_O}.fetch_natural_hazards": AsyncMock(return_value={}),
        f"{_O}.fetch_noise_data": AsyncMock(return_value={}),
        f"{_O}.fetch_solar_potential": AsyncMock(return_value={}),
        f"{_O}.fetch_heritage_status": AsyncMock(return_value={}),
        f"{_O}.fetch_transport_quality": AsyncMock(return_value={}),
        f"{_O}.fetch_seismic_zone": AsyncMock(return_value={}),
        f"{_O}.fetch_water_protection": AsyncMock(return_value={}),
        f"{_O}.fetch_railway_noise": AsyncMock(return_value={}),
        f"{_O}.fetch_aircraft_noise": AsyncMock(return_value={}),
        f"{_O}.fetch_building_zones": AsyncMock(return_value={}),
        f"{_O}.fetch_contaminated_sites": AsyncMock(return_value={}),
        f"{_O}.fetch_groundwater_zones": AsyncMock(return_value={}),
        f"{_O}.fetch_flood_zones": AsyncMock(return_value={}),
        f"{_O}.fetch_mobile_coverage": AsyncMock(return_value={}),
        f"{_O}.fetch_broadband": AsyncMock(return_value={}),
        f"{_O}.fetch_ev_charging": AsyncMock(return_value={}),
        f"{_O}.fetch_thermal_networks": AsyncMock(return_value={}),
        f"{_O}.fetch_protected_monuments": AsyncMock(return_value={}),
        f"{_O}.fetch_agricultural_zones": AsyncMock(return_value={}),
        f"{_O}.fetch_forest_reserves": AsyncMock(return_value={}),
        f"{_O}.fetch_military_zones": AsyncMock(return_value={}),
        f"{_O}.fetch_accident_sites": AsyncMock(return_value={}),
        f"{_O}.fetch_osm_amenities": AsyncMock(return_value={}),
        f"{_O}.fetch_osm_building_details": AsyncMock(return_value={}),
        f"{_O}.fetch_climate_data": MagicMock(return_value={}),
        f"{_O}.fetch_nearest_stops": AsyncMock(return_value={}),
        f"{_O}._throttle": AsyncMock(),
        f"{_O}.populate_climate_exposure_profile": AsyncMock(),
    }


def _apply_patches(extra: dict[str, AsyncMock | MagicMock] | None = None):
    """Return a contextlib.ExitStack that patches all enrichment fetchers."""
    patches = _base_patches()
    if extra:
        patches.update(extra)

    stack = contextlib.ExitStack()
    for target, mock_obj in patches.items():
        stack.enter_context(patch(target, mock_obj))
    return stack


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSpatialPersistenceInEnrichmentMeta:
    """Verify swissBUILDINGS3D data is persisted in enrichment_meta (source_metadata_json)."""

    @pytest.mark.asyncio
    async def test_spatial_keys_present_after_successful_fetch(self):
        """All canonical spatial keys appear in enrichment_meta when swissBUILDINGS3D returns data."""
        building = _make_mock_building()
        db = _mock_db_session(building)
        spatial_data = _full_spatial_response()

        extra = {
            f"{_O}.SpatialEnrichmentService.fetch_building_footprint": AsyncMock(return_value=spatial_data),
        }

        with _apply_patches(extra):
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

        meta = building.source_metadata_json
        for key in SPATIAL_META_KEYS:
            assert key in meta, f"enrichment_meta missing spatial key: {key}"

        assert result.spatial_fetched is True
        assert "spatial_3d" in result.fields_updated

    @pytest.mark.asyncio
    async def test_spatial_values_mapped_correctly(self):
        """Spatial values are mapped to the correct enrichment_meta keys."""
        building = _make_mock_building()
        db = _mock_db_session(building)
        spatial_data = _full_spatial_response()

        extra = {
            f"{_O}.SpatialEnrichmentService.fetch_building_footprint": AsyncMock(return_value=spatial_data),
        }

        with _apply_patches(extra):
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

        meta = building.source_metadata_json
        assert meta["building_height_m"] == 12.5
        assert meta["building_volume_m3"] == 3750.0
        assert meta["floor_count_3d"] == 4
        assert meta["roof_type"] == "Flachdach"
        assert meta["footprint_area_m2"] == 300.0
        assert meta["spatial_source"] == "ch.swisstopo.swissbuildings3d_3_0.v2"
        assert meta["spatial_fetched_at"] is not None

    @pytest.mark.asyncio
    async def test_no_spatial_keys_when_api_returns_no_data(self):
        """When swissBUILDINGS3D returns an error/no_data response, spatial keys are absent."""
        building = _make_mock_building()
        db = _mock_db_session(building)

        extra = {
            f"{_O}.SpatialEnrichmentService.fetch_building_footprint": AsyncMock(
                return_value=_empty_spatial_response()
            ),
        }

        with _apply_patches(extra):
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

        meta = building.source_metadata_json
        for key in SPATIAL_META_KEYS:
            assert key not in meta, f"enrichment_meta should not have {key} when no spatial data"

        assert result.spatial_fetched is False
        assert "spatial_3d" not in result.fields_updated

    @pytest.mark.asyncio
    async def test_no_spatial_keys_when_no_coordinates(self):
        """When building has no coordinates, spatial fetch is skipped entirely."""
        building = _make_mock_building()
        building.latitude = None
        building.longitude = None
        db = _mock_db_session(building)

        spatial_mock = AsyncMock(return_value=_full_spatial_response())
        extra = {
            f"{_O}.SpatialEnrichmentService.fetch_building_footprint": spatial_mock,
        }

        with _apply_patches(extra):
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

        spatial_mock.assert_not_called()
        assert result.spatial_fetched is False

    @pytest.mark.asyncio
    async def test_graceful_on_spatial_exception(self):
        """When swissBUILDINGS3D raises an exception, enrichment continues without spatial keys."""
        building = _make_mock_building()
        db = _mock_db_session(building)

        extra = {
            f"{_O}.SpatialEnrichmentService.fetch_building_footprint": AsyncMock(
                side_effect=Exception("Network timeout")
            ),
        }

        with _apply_patches(extra):
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

        meta = building.source_metadata_json
        for key in SPATIAL_META_KEYS:
            assert key not in meta, f"enrichment_meta should not have {key} after exception"

        assert result.spatial_fetched is False
        assert result.fields_updated is not None

    @pytest.mark.asyncio
    async def test_partial_spatial_data_persisted(self):
        """When swissBUILDINGS3D returns partial data, only available values are stored."""
        building = _make_mock_building()
        db = _mock_db_session(building)

        extra = {
            f"{_O}.SpatialEnrichmentService.fetch_building_footprint": AsyncMock(
                return_value=_partial_spatial_response()
            ),
        }

        with _apply_patches(extra):
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

        meta = building.source_metadata_json
        assert meta["building_height_m"] == 9.8
        assert meta["building_volume_m3"] is None
        assert meta["floor_count_3d"] is None
        assert meta["roof_type"] is None
        assert meta["footprint_area_m2"] is None
        assert result.spatial_fetched is True


class TestSpatialParseResponse:
    """Unit tests for _parse_spatial_response from spatial_enrichment_service."""

    def test_parse_full_response(self):
        """Parse a complete swissBUILDINGS3D feature with all attributes."""
        from app.services.spatial_enrichment_service import _parse_spatial_response

        features = [
            {
                "attributes": {
                    "gebaeudehoehe": 15.2,
                    "dachform": "Satteldach",
                    "volumen": 4500.0,
                    "grundflaeche": 350.0,
                    "geschosszahl": 5,
                },
                "geometry": {"rings": [[[6.63, 46.52], [6.64, 46.52], [6.64, 46.53], [6.63, 46.53], [6.63, 46.52]]]},
            }
        ]
        result = _parse_spatial_response(features)

        assert result is not None
        assert result["height_m"] == 15.2
        assert result["roof_type"] == "Satteldach"
        assert result["volume_m3"] == 4500.0
        assert result["surface_m2"] == 350.0
        assert result["floors"] == 5
        assert result["footprint_wkt"] is not None
        assert result["footprint_wkt"].startswith("POLYGON")

    def test_parse_empty_features(self):
        """Parse returns None when features list is empty."""
        from app.services.spatial_enrichment_service import _parse_spatial_response

        assert _parse_spatial_response([]) is None

    def test_parse_no_attributes(self):
        """Parse returns None when feature has no attributes."""
        from app.services.spatial_enrichment_service import _parse_spatial_response

        features = [{"attributes": {}, "geometry": {}}]
        assert _parse_spatial_response(features) is None
