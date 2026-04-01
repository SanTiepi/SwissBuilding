"""Tests for swissBUILDINGS3D spatial enrichment service and API."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.spatial_enrichment_service import (
    LAYER_ID,
    SOURCE_VERSION,
    SpatialEnrichmentService,
    _build_map_extent,
    _parse_spatial_response,
)

# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------


def test_build_map_extent():
    extent = _build_map_extent(6.63, 46.52)
    parts = extent.split(",")
    assert len(parts) == 4
    assert float(parts[0]) < 6.63
    assert float(parts[2]) > 6.63
    assert float(parts[1]) < 46.52
    assert float(parts[3]) > 46.52


def test_build_map_extent_custom_buffer():
    extent = _build_map_extent(7.0, 47.0, buffer=0.01)
    parts = extent.split(",")
    assert float(parts[0]) == pytest.approx(6.99, abs=0.001)
    assert float(parts[2]) == pytest.approx(7.01, abs=0.001)


def test_parse_spatial_response_empty():
    assert _parse_spatial_response([]) is None


def test_parse_spatial_response_no_attrs():
    assert _parse_spatial_response([{"attributes": {}}]) is None


def test_parse_spatial_response_full():
    features = [
        {
            "attributes": {
                "gebaeudehoehe": 12.5,
                "dachform": "Flachdach",
                "volumen": 3200.0,
                "grundflaeche": 256.0,
                "geschosszahl": 4,
            },
            "geometry": {
                "rings": [
                    [
                        [6.63, 46.52],
                        [6.631, 46.52],
                        [6.631, 46.521],
                        [6.63, 46.521],
                        [6.63, 46.52],
                    ]
                ]
            },
        }
    ]
    result = _parse_spatial_response(features)
    assert result is not None
    assert result["height_m"] == 12.5
    assert result["roof_type"] == "Flachdach"
    assert result["volume_m3"] == 3200.0
    assert result["surface_m2"] == 256.0
    assert result["floors"] == 4
    assert result["source"] == LAYER_ID
    assert result["source_version"] == SOURCE_VERSION
    assert result["footprint_wkt"] is not None
    assert result["footprint_wkt"].startswith("POLYGON((")


def test_parse_spatial_response_partial():
    """Only height available — other fields None."""
    features = [{"attributes": {"building_height": 8.0}}]
    result = _parse_spatial_response(features)
    assert result is not None
    assert result["height_m"] == 8.0
    assert result["roof_type"] is None
    assert result["volume_m3"] is None
    assert result["surface_m2"] is None
    assert result["footprint_wkt"] is None


def test_parse_spatial_response_geojson_geometry():
    """Test GeoJSON-style coordinates instead of ESRI rings."""
    features = [
        {
            "attributes": {"hoehe": 10},
            "geometry": {
                "coordinates": [
                    [
                        [6.63, 46.52],
                        [6.631, 46.52],
                        [6.631, 46.521],
                        [6.63, 46.52],
                    ]
                ]
            },
        }
    ]
    result = _parse_spatial_response(features)
    assert result is not None
    assert result["footprint_wkt"] is not None
    assert "POLYGON" in result["footprint_wkt"]


def test_parse_spatial_response_string_height():
    """Height as string should still parse to float."""
    features = [{"attributes": {"height": "15.3"}}]
    result = _parse_spatial_response(features)
    assert result is not None
    assert result["height_m"] == 15.3


def test_parse_spatial_response_invalid_numeric():
    """Non-numeric height string should yield None."""
    features = [{"attributes": {"height": "unknown", "dachform": "Satteldach"}}]
    result = _parse_spatial_response(features)
    assert result is not None
    assert result["height_m"] is None
    assert result["roof_type"] == "Satteldach"


# ---------------------------------------------------------------------------
# Service tests (mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_building_footprint_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "attributes": {
                    "gebaeudehoehe": 18.0,
                    "dachform": "Satteldach",
                    "volumen": 5400.0,
                    "grundflaeche": 300.0,
                },
                "geometry": {},
            }
        ]
    }

    with patch("app.services.spatial_enrichment_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await SpatialEnrichmentService.fetch_building_footprint(6.63, 46.52)

    assert "error" not in result
    assert result["height_m"] == 18.0
    assert result["roof_type"] == "Satteldach"
    assert result["volume_m3"] == 5400.0
    assert result["surface_m2"] == 300.0
    assert result["fetched_at"] is not None


@pytest.mark.asyncio
async def test_fetch_building_footprint_no_results():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"results": []}

    with patch("app.services.spatial_enrichment_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await SpatialEnrichmentService.fetch_building_footprint(6.63, 46.52)

    assert result["error"] == "no_data"


@pytest.mark.asyncio
async def test_fetch_building_footprint_timeout():
    import httpx as _httpx

    with patch("app.services.spatial_enrichment_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=_httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await SpatialEnrichmentService.fetch_building_footprint(6.63, 46.52)

    assert result["error"] == "timeout"


@pytest.mark.asyncio
async def test_fetch_building_footprint_exception():
    with patch("app.services.spatial_enrichment_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await SpatialEnrichmentService.fetch_building_footprint(6.63, 46.52)

    assert result["error"] == "fetch_failed"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_spatial_enrichment_endpoint(client, db_session, sample_building, auth_headers):
    """GET /buildings/{id}/spatial-enrichment returns spatial data."""
    with patch.object(
        SpatialEnrichmentService,
        "get_building_spatial",
        new_callable=AsyncMock,
        return_value={
            "height_m": 12.0,
            "roof_type": "Flachdach",
            "volume_m3": 2400.0,
            "surface_m2": 200.0,
            "source": LAYER_ID,
            "source_version": SOURCE_VERSION,
            "fetched_at": datetime.now(UTC).isoformat(),
            "cached": True,
        },
    ):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/spatial-enrichment",
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["height_m"] == 12.0
    assert data["roof_type"] == "Flachdach"
    assert data["cached"] is True


@pytest.mark.asyncio
async def test_refresh_spatial_enrichment_endpoint(client, db_session, sample_building, auth_headers):
    """POST /buildings/{id}/spatial-enrichment/refresh refreshes data."""
    with patch.object(
        SpatialEnrichmentService,
        "enrich_building_spatial",
        new_callable=AsyncMock,
        return_value={
            "footprint_wkt": "POLYGON((6.63 46.52, 6.631 46.52, 6.631 46.521, 6.63 46.52))",
            "height_m": 15.0,
            "roof_type": "Satteldach",
            "volume_m3": 4500.0,
            "surface_m2": 300.0,
            "floors": 3,
            "source": LAYER_ID,
            "source_version": SOURCE_VERSION,
            "fetched_at": datetime.now(UTC).isoformat(),
            "raw_attributes": {"gebaeudehoehe": 15.0},
        },
    ):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/spatial-enrichment/refresh",
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["height_m"] == 15.0
    assert data["building_updated"] is True


@pytest.mark.asyncio
async def test_refresh_spatial_enrichment_error(client, db_session, sample_building, auth_headers):
    """POST refresh returns 400 when swissBUILDINGS3D has no data."""
    with patch.object(
        SpatialEnrichmentService,
        "enrich_building_spatial",
        new_callable=AsyncMock,
        return_value={"error": "no_data", "detail": "Aucune donnee"},
    ):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/spatial-enrichment/refresh",
            headers=auth_headers,
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_spatial_enrichment_not_found(client, db_session, auth_headers):
    """GET with invalid building ID returns 404."""
    with patch.object(
        SpatialEnrichmentService,
        "get_building_spatial",
        new_callable=AsyncMock,
        side_effect=ValueError("Building not found"),
    ):
        response = await client.get(
            "/api/v1/buildings/00000000-0000-0000-0000-000000000099/spatial-enrichment",
            headers=auth_headers,
        )
    assert response.status_code == 404
