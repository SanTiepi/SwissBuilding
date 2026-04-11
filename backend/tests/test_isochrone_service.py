"""Tests for isochrone service — Mapbox Isochrone API wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.isochrone_service import (
    VALID_PROFILES,
    _cache,
    _cache_key,
    _fetch_isochrone_from_mapbox,
    _parse_features,
    get_building_isochrone,
)


class TestParseFeatures:
    """Test GeoJSON feature parsing."""

    def test_parse_three_contours(self):
        raw = {
            "features": [
                {"geometry": {"type": "Polygon", "coordinates": [[[6.6, 46.5]]]}},
                {"geometry": {"type": "Polygon", "coordinates": [[[6.7, 46.6]]]}},
                {"geometry": {"type": "Polygon", "coordinates": [[[6.8, 46.7]]]}},
            ]
        }
        result = _parse_features(raw, "walking", [5, 10, 15])
        assert len(result) == 3
        assert result[0]["minutes"] == 5
        assert result[0]["profile"] == "walking"
        assert result[2]["minutes"] == 15

    def test_parse_empty_features(self):
        result = _parse_features({"features": []}, "cycling", [5, 10])
        assert result == []

    def test_parse_missing_geometry(self):
        raw = {"features": [{"properties": {}}]}
        result = _parse_features(raw, "driving", [5])
        assert result[0]["geometry"] == {}


class TestCacheKey:
    """Test cache key generation."""

    def test_deterministic(self):
        import uuid

        bid = uuid.uuid4()
        k1 = _cache_key(bid, "walking", [5, 10, 15])
        k2 = _cache_key(bid, "walking", [15, 5, 10])
        assert k1 == k2  # sorted

    def test_different_profiles(self):
        import uuid

        bid = uuid.uuid4()
        k1 = _cache_key(bid, "walking", [5])
        k2 = _cache_key(bid, "cycling", [5])
        assert k1 != k2


class TestValidation:
    """Test input validation in get_building_isochrone."""

    @pytest.mark.asyncio
    async def test_invalid_profile(self):
        db = AsyncMock()
        import uuid

        result = await get_building_isochrone(db, uuid.uuid4(), profile="flying")
        assert "error" in result
        assert "Invalid profile" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_minutes(self):
        db = AsyncMock()
        import uuid

        result = await get_building_isochrone(db, uuid.uuid4(), minutes_list=[0, -1, 999])
        assert "error" in result
        assert "No valid minutes" in result["error"]


class TestFetchMocked:
    """Test Mapbox API call with mocked httpx."""

    @pytest.mark.asyncio
    async def test_no_api_key(self):
        with patch("app.services.isochrone_service.settings") as mock_settings:
            mock_settings.MAPBOX_API_KEY = None
            result = await _fetch_isochrone_from_mapbox(6.63, 46.52, "walking", [5, 10])
            assert result["error"] == "MAPBOX_API_KEY not configured"

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        mock_response = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[6.6, 46.5]]]}},
            ],
        }
        with patch("app.services.isochrone_service.settings") as mock_settings:
            mock_settings.MAPBOX_API_KEY = "pk_test_fake"
            with patch("app.services.isochrone_service.httpx.AsyncClient") as mock_client_cls:
                mock_resp = AsyncMock()
                mock_resp.json = lambda: mock_response  # plain function, not async
                mock_resp.raise_for_status = lambda: None

                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                result = await _fetch_isochrone_from_mapbox(6.63, 46.52, "walking", [5])
                assert "features" in result
                assert len(result["features"]) == 1


class TestGetBuildingIsochrone:
    """Integration test with mocked DB and API."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        import uuid
        from datetime import UTC, datetime

        bid = uuid.uuid4()
        key = _cache_key(bid, "walking", [5, 10, 15])
        cached_data = {
            "building_id": str(bid),
            "latitude": 46.52,
            "longitude": 6.63,
            "profile": "walking",
            "contours": [{"minutes": 5, "profile": "walking", "geometry": {}}],
            "mobility_score": 10.0,
            "cached": False,
            "error": None,
        }
        _cache[key] = (datetime.now(UTC), cached_data)

        db = AsyncMock()
        result = await get_building_isochrone(db, bid, "walking", [5, 10, 15])
        assert result["cached"] is True

        # Cleanup
        del _cache[key]

    @pytest.mark.asyncio
    async def test_valid_profiles(self):
        assert {"walking", "cycling", "driving"} == VALID_PROFILES
