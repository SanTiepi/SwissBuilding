"""Tests for registry_connector_service — mock all HTTP calls."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.registry_connector_service import (
    _cache,
    _parse_regbl_attrs,
    _safe_float,
    _safe_int,
    enrich_building_from_registry,
    get_natural_hazards,
    lookup_by_address,
    lookup_by_egid,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_regbl_response(egid: int = 123456) -> dict:
    return {
        "results": [
            {
                "attrs": {
                    "strname_deinr": "Rue du Midi 15",
                    "dplz4": 1003,
                    "ggdename": "Lausanne",
                    "gdekt": "VD",
                    "gbauj": 1965,
                    "gkat_decoded": "Wohngebaeude",
                    "gastw": 4,
                    "garea": 350.5,
                    "gheizh_decoded": "Fernwaerme",
                    "genhe1_decoded": "Gas",
                    "gbaum": 2010,
                },
                "geometry": {"x": 6.632, "y": 46.519},
            }
        ]
    }


def _make_swisstopo_response() -> dict:
    return {
        "results": [
            {
                "attrs": {
                    "label": "Rue du Midi 15, 1003 Lausanne",
                    "zip": 1003,
                    "commune": "Lausanne",
                    "canton": "VD",
                    "lat": 46.519,
                    "lon": 6.632,
                    "egid": 123456,
                    "featureId": "abc123",
                }
            },
            {
                "attrs": {
                    "label": "Rue du Midi 17, 1003 Lausanne",
                    "zip": 1003,
                    "commune": "Lausanne",
                    "canton": "VD",
                    "lat": 46.5191,
                    "lon": 6.6321,
                }
            },
        ]
    }


def _make_hazard_response(level: str = "erheblich") -> dict:
    return {
        "results": [
            {
                "attributes": {
                    "gefahrenstufe": level,
                    "description": "Moderate hazard",
                }
            }
        ]
    }


# ---------------------------------------------------------------------------
# Unit tests: parsing helpers
# ---------------------------------------------------------------------------


def test_safe_int_valid():
    assert _safe_int(42) == 42
    assert _safe_int("1965") == 1965


def test_safe_int_invalid():
    assert _safe_int(None) is None
    assert _safe_int("abc") is None


def test_safe_float_valid():
    assert _safe_float(3.14) == 3.14
    assert _safe_float("350.5") == 350.5


def test_safe_float_invalid():
    assert _safe_float(None) is None
    assert _safe_float("xyz") is None


def test_parse_regbl_attrs():
    attrs = {
        "strname_deinr": "Rue du Midi 15",
        "dplz4": 1003,
        "ggdename": "Lausanne",
        "gdekt": "VD",
        "gbauj": 1965,
        "gastw": 4,
        "garea": 350.5,
    }
    result = _parse_regbl_attrs(attrs, {"x": 6.632, "y": 46.519}, 123456)
    assert result["egid"] == 123456
    assert result["address"] == "Rue du Midi 15"
    assert result["postal_code"] == "1003"
    assert result["city"] == "Lausanne"
    assert result["canton"] == "VD"
    assert result["construction_year"] == 1965
    assert result["floors"] == 4
    assert result["area"] == 350.5
    assert result["coordinates"] == {"lat": 46.519, "lng": 6.632}
    assert result["source"] == "regbl"


# ---------------------------------------------------------------------------
# Async tests: lookup_by_egid
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_cache():
    _cache.clear()
    yield
    _cache.clear()


@pytest.mark.asyncio
async def test_lookup_by_egid_parses_response():
    mock_response = MagicMock()
    mock_response.json.return_value = _make_regbl_response(123456)
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.registry_connector_service.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await lookup_by_egid(123456)

    assert result is not None
    assert result["egid"] == 123456
    assert result["address"] == "Rue du Midi 15"
    assert result["construction_year"] == 1965
    assert result["coordinates"]["lat"] == 46.519


@pytest.mark.asyncio
async def test_lookup_by_egid_not_found():
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.registry_connector_service.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await lookup_by_egid(999999)

    assert result is None


@pytest.mark.asyncio
async def test_lookup_by_egid_timeout():
    with patch("app.services.registry_connector_service.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await lookup_by_egid(123456)

    assert result is None


@pytest.mark.asyncio
async def test_lookup_by_egid_cache_hit():
    """Second call should hit cache and not make another HTTP request."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_regbl_response(123456)
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.registry_connector_service.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result1 = await lookup_by_egid(123456)
        result2 = await lookup_by_egid(123456)

    assert result1 is not None
    assert result2 is not None
    assert result1 == result2
    # Only 1 HTTP call (the second hit cache)
    assert mock_client.get.call_count == 1


# ---------------------------------------------------------------------------
# Async tests: lookup_by_address
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_by_address_returns_list():
    mock_response = MagicMock()
    mock_response.json.return_value = _make_swisstopo_response()
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.registry_connector_service.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        results = await lookup_by_address("Rue du Midi 15")

    assert len(results) == 2
    assert results[0]["source"] == "swisstopo"
    assert results[0]["egid"] == 123456
    assert results[1]["egid"] is None


@pytest.mark.asyncio
async def test_lookup_by_address_timeout():
    with patch("app.services.registry_connector_service.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        results = await lookup_by_address("Rue du Midi 15")

    assert results == []


# ---------------------------------------------------------------------------
# Async tests: get_natural_hazards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_natural_hazards():
    mock_response = MagicMock()
    mock_response.json.return_value = _make_hazard_response("erheblich")
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.registry_connector_service.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        result = await get_natural_hazards(46.519, 6.632)

    # We have 4 hazard types
    assert "flood_risk" in result
    assert "landslide_risk" in result
    assert "avalanche_risk" in result
    assert "earthquake_risk" in result


# ---------------------------------------------------------------------------
# Async tests: enrich_building_from_registry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_building_fills_empty_fields():
    """Enrichment should fill empty fields but not overwrite existing ones."""
    building_id = uuid.uuid4()

    building = MagicMock()
    building.id = building_id
    building.egid = 123456
    building.latitude = None
    building.longitude = None
    building.construction_year = None
    building.renovation_year = None
    building.canton = "VD"  # already set — must NOT be overwritten
    building.postal_code = None
    building.city = None
    building.floors_above = None
    building.surface_area_m2 = None
    building.source_metadata_json = None

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = building
    mock_db.execute.return_value = mock_result

    regbl_data = {
        "egid": 123456,
        "construction_year": 1965,
        "renovation_year": 2010,
        "canton": "GE",  # different from existing — should NOT overwrite
        "postal_code": "1003",
        "city": "Lausanne",
        "floors": 4,
        "area": 350.5,
        "coordinates": {"lat": 46.519, "lng": 6.632},
    }

    with (
        patch("app.services.registry_connector_service.lookup_by_egid", new_callable=AsyncMock) as mock_egid,
        patch("app.services.registry_connector_service.get_natural_hazards", new_callable=AsyncMock) as mock_hazards,
    ):
        mock_egid.return_value = regbl_data
        mock_hazards.return_value = {"flood_risk": {"level": "low"}}

        result = await enrich_building_from_registry(mock_db, building_id)

    assert result["building_id"] == str(building_id)
    # construction_year was None, so it should be updated
    assert "construction_year" in result["updated_fields"]
    assert result["updated_fields"]["construction_year"] == 1965
    # canton was already "VD", so it must NOT appear in updated_fields
    assert "canton" not in result["updated_fields"]
    # coordinates were None, so they should be filled
    assert "latitude" in result["updated_fields"]


@pytest.mark.asyncio
async def test_enrich_building_not_found():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(ValueError, match="not found"):
        await enrich_building_from_registry(mock_db, uuid.uuid4())


@pytest.mark.asyncio
async def test_enrich_building_no_egid():
    """Building without EGID should still try hazards if has coordinates."""
    building_id = uuid.uuid4()

    building = MagicMock()
    building.id = building_id
    building.egid = None
    building.latitude = 46.519
    building.longitude = 6.632
    building.construction_year = 1970
    building.renovation_year = None
    building.canton = "VD"
    building.postal_code = "1003"
    building.city = "Lausanne"
    building.floors_above = 3
    building.surface_area_m2 = 200
    building.source_metadata_json = {}

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = building
    mock_db.execute.return_value = mock_result

    with patch("app.services.registry_connector_service.get_natural_hazards", new_callable=AsyncMock) as mock_hazards:
        mock_hazards.return_value = {"flood_risk": {"level": "moderate"}}
        result = await enrich_building_from_registry(mock_db, building_id)

    assert result["hazards_fetched"] is True
    assert result["egid_found"] is False
    assert "natural_hazards" in result["updated_fields"]
