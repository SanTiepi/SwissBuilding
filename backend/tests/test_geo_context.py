"""Tests for geo context service and API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.geo_context_service import (
    LAYERS,
    _build_map_extent,
    _parse_layer_response,
    fetch_context,
)


def test_build_map_extent():
    extent = _build_map_extent(6.63, 46.52)
    parts = extent.split(",")
    assert len(parts) == 4
    assert float(parts[0]) < 6.63
    assert float(parts[2]) > 6.63


def test_parse_layer_response_empty():
    assert _parse_layer_response("radon", []) is None


def test_parse_layer_response_no_attrs():
    assert _parse_layer_response("radon", [{"attributes": {}}]) is None


def test_parse_layer_response_radon():
    features = [{"attributes": {"zone": "moderate", "radon_bq_m3": "200-400"}}]
    result = _parse_layer_response("radon", features)
    assert result is not None
    assert result["source"] == "ch.bag.radonkarte"
    assert result["label"] == "Radon"
    assert result["zone"] == "moderate"


def test_parse_layer_response_noise_road():
    features = [{"attributes": {"lre_d": 55}}]
    result = _parse_layer_response("noise_road", features)
    assert result is not None
    assert result["level_db"] == 55


def test_parse_layer_response_solar():
    features = [{"attributes": {"stromertrag": 1200, "klasse": "gut"}}]
    result = _parse_layer_response("solar", features)
    assert result is not None
    assert result["potential_kwh"] == 1200
    assert result["suitability"] == "gut"


def test_parse_layer_response_natural_hazards():
    features = [{"attributes": {"gefahrenstufe": "erheblich"}}]
    result = _parse_layer_response("natural_hazards", features)
    assert result is not None
    assert result["hazard_level"] == "erheblich"


def test_parse_layer_response_groundwater():
    features = [{"attributes": {"schutzzone": "S2"}}]
    result = _parse_layer_response("groundwater_protection", features)
    assert result is not None
    assert result["zone_type"] == "S2"


def test_parse_layer_response_contaminated():
    features = [{"attributes": {"status": "belastet", "kategorie": "A"}}]
    result = _parse_layer_response("contaminated_sites", features)
    assert result is not None
    assert result["status"] == "belastet"
    assert result["category"] == "A"


def test_parse_layer_response_heritage():
    features = [{"attributes": {"ortsbildname": "Lausanne", "ortsbildbedeutung": "national"}}]
    result = _parse_layer_response("heritage_isos", features)
    assert result is not None
    assert result["name"] == "Lausanne"
    assert result["status"] == "national"


def test_parse_layer_response_public_transport():
    features = [{"attributes": {"klasse": "A"}}]
    result = _parse_layer_response("public_transport", features)
    assert result is not None
    assert result["quality_class"] == "A"


def test_parse_layer_response_thermal():
    features = [{"attributes": {"name": "Reseau Lausanne", "status": "en service"}}]
    result = _parse_layer_response("thermal_networks", features)
    assert result is not None
    assert result["network_name"] == "Reseau Lausanne"


def test_all_layers_defined():
    """Ensure all 24 layers have label and layer_id."""
    assert len(LAYERS) == 24
    for key, info in LAYERS.items():
        assert "layer_id" in info, f"Layer {key} missing layer_id"
        assert "label" in info, f"Layer {key} missing label"
        assert info["layer_id"].startswith("ch."), f"Layer {key} has unexpected layer_id format"


def test_parse_layer_response_seismic():
    features = [{"attributes": {"erdbebenzone": "Z2", "bauwerksklasse": "C"}}]
    result = _parse_layer_response("seismic", features)
    assert result is not None
    assert result["zone"] == "Z2"
    assert result["value"] == "C"


def test_parse_layer_response_flood_zones():
    features = [{"attributes": {"gefahrenstufe": "erheblich", "wiederkehrperiode": "100"}}]
    result = _parse_layer_response("flood_zones", features)
    assert result is not None
    assert result["hazard_level"] == "erheblich"
    assert result["value"] == "100 ans"


def test_parse_layer_response_aircraft_noise():
    features = [{"attributes": {"lr_tag": 62}}]
    result = _parse_layer_response("aircraft_noise", features)
    assert result is not None
    assert result["level_db"] == 62


def test_parse_layer_response_building_zones():
    features = [{"attributes": {"zonentyp": "Wohnzone", "bezeichnung": "W2"}}]
    result = _parse_layer_response("building_zones", features)
    assert result is not None
    assert result["zone_type"] == "Wohnzone"
    assert result["value"] == "W2"


def test_parse_layer_response_mobile_coverage():
    features = [{"attributes": {"technology": "5G"}}]
    result = _parse_layer_response("mobile_coverage", features)
    assert result is not None
    assert result["status"] == "5G disponible"


def test_parse_layer_response_broadband():
    features = [{"attributes": {"technologie": "FTTH", "max_speed": "1000"}}]
    result = _parse_layer_response("broadband", features)
    assert result is not None
    assert result["value"] == "FTTH"
    assert result["name"] == "1000 Mbps"


def test_parse_layer_response_ev_charging():
    features = [{"attributes": {"distance": "250"}}]
    result = _parse_layer_response("ev_charging", features)
    assert result is not None
    assert result["status"] == "Borne(s) a proximite"
    assert result["value"] == "250 m"


def test_parse_layer_response_protected_monuments():
    features = [{"attributes": {"kategorie": "A"}}]
    result = _parse_layer_response("protected_monuments", features)
    assert result is not None
    assert result["status"] == "Monument protege"
    assert result["category"] == "A"


def test_parse_layer_response_agricultural_zones():
    features = [{"attributes": {"eignung": "gut", "zone": "Landwirtschaftszone"}}]
    result = _parse_layer_response("agricultural_zones", features)
    assert result is not None
    assert result["value"] == "gut"
    assert result["zone"] == "Landwirtschaftszone"


def test_parse_layer_response_forest_reserves():
    features = [{"attributes": {"name": "Reserve du Jorat"}}]
    result = _parse_layer_response("forest_reserves", features)
    assert result is not None
    assert result["status"] == "Reserve forestiere"
    assert result["name"] == "Reserve du Jorat"


def test_parse_layer_response_accident_sites():
    features = [{"attributes": {"name": "Chimique SA"}}]
    result = _parse_layer_response("accident_sites", features)
    assert result is not None
    assert result["status"] == "Site Seveso a proximite"
    assert result["name"] == "Chimique SA"


def test_parse_layer_response_groundwater_areas():
    features = [{"attributes": {"schutzzone": "S2", "typ": "Areal"}}]
    result = _parse_layer_response("groundwater_areas", features)
    assert result is not None
    assert result["zone_type"] == "S2"
    assert result["value"] == "Areal"


def test_parse_layer_response_landslides():
    features = [{"attributes": {"stufe": "mittel"}}]
    result = _parse_layer_response("landslides", features)
    assert result is not None
    assert result["hazard_level"] == "mittel"


@pytest.mark.asyncio
async def test_fetch_context_handles_errors():
    """fetch_context should skip layers that fail and return partial results."""
    with patch("app.services.geo_context_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        # All requests raise an error
        mock_client.get = AsyncMock(side_effect=Exception("network error"))

        result = await fetch_context(6.63, 46.52, layers=["radon"])
        assert result == {}


@pytest.mark.asyncio
async def test_fetch_context_parses_response():
    """fetch_context should parse valid responses."""
    with patch("app.services.geo_context_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"attributes": {"zone": "moderate", "radon_bq_m3": "300"}}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await fetch_context(6.63, 46.52, layers=["radon"])
        assert "radon" in result
        assert result["radon"]["zone"] == "moderate"
        assert result["radon"]["source"] == "ch.bag.radonkarte"
