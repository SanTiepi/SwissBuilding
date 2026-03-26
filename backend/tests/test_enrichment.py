"""Tests for building enrichment pipeline."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.schemas.enrichment import (
    BatchEnrichmentResult,
    EnrichmentRequest,
    EnrichmentResult,
    EnrichmentStatus,
)
from app.services.building_enrichment_service import (
    _build_ai_prompt,
    _geo_identify,
    _lat_lon_to_tile,
    compute_accessibility_assessment,
    compute_connectivity_score,
    compute_environmental_risk_score,
    compute_livability_score,
    compute_neighborhood_score,
    compute_overall_building_intelligence_score,
    compute_pollutant_risk_prediction,
    compute_renovation_potential,
    estimate_subsidy_eligibility,
    fetch_accident_sites,
    fetch_agricultural_zones,
    fetch_aircraft_noise,
    fetch_broadband,
    fetch_building_zones,
    fetch_cadastre_egrid,
    fetch_climate_data,
    fetch_contaminated_sites,
    fetch_ev_charging,
    fetch_flood_zones,
    fetch_forest_reserves,
    fetch_groundwater_zones,
    fetch_heritage_status,
    fetch_military_zones,
    fetch_mobile_coverage,
    fetch_natural_hazards,
    fetch_nearest_stops,
    fetch_noise_data,
    fetch_osm_amenities,
    fetch_osm_building_details,
    fetch_protected_monuments,
    fetch_radon_risk,
    fetch_railway_noise,
    fetch_regbl_data,
    fetch_seismic_zone,
    fetch_solar_potential,
    fetch_swisstopo_image_url,
    fetch_thermal_networks,
    fetch_transport_quality,
    fetch_water_protection,
    geocode_address,
)

# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestEnrichmentSchemas:
    def test_enrichment_result_defaults(self):
        r = EnrichmentResult(building_id=uuid.uuid4())
        assert r.geocoded is False
        assert r.regbl_found is False
        assert r.egrid_found is False
        assert r.image_url is None
        assert r.ai_enriched is False
        assert r.fields_updated == []
        assert r.errors == []

    def test_enrichment_request_defaults(self):
        r = EnrichmentRequest(building_id=uuid.uuid4())
        assert r.skip_geocode is False
        assert r.skip_regbl is False
        assert r.skip_ai is False

    def test_batch_enrichment_result(self):
        r = BatchEnrichmentResult(total=10, enriched=7, error_count=2, results=[])
        assert r.total == 10
        assert r.enriched == 7
        assert r.error_count == 2

    def test_enrichment_status(self):
        s = EnrichmentStatus(
            building_id=uuid.uuid4(),
            has_coordinates=True,
            has_egid=True,
        )
        assert s.has_coordinates is True
        assert s.has_egid is True
        assert s.has_egrid is False


# ---------------------------------------------------------------------------
# Geocode tests
# ---------------------------------------------------------------------------


class TestGeocode:
    @pytest.mark.asyncio
    async def test_geocode_valid_lausanne_address(self):
        """Geocode returns valid coordinates for a known address (mocked)."""
        mock_response = {
            "results": [
                {
                    "attrs": {
                        "lat": 46.5197,
                        "lon": 6.6323,
                        "featureId": "123456",
                        "label": "Rue de Bourg 1, 1003 Lausanne",
                        "detail": "Lausanne VD",
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await geocode_address("Rue de Bourg 1", "1003")

        assert result["lat"] == 46.5197
        assert result["lon"] == 6.6323
        assert result["egid"] == 123456
        assert "Lausanne" in result["label"]

    @pytest.mark.asyncio
    async def test_geocode_unknown_address(self):
        """Geocode returns no data (just source entry) for unknown address."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()

        with (
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client,
        ):
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await geocode_address("Nonexistent Street 999", "0000")

        assert "lat" not in result
        assert "lon" not in result
        assert result.get("_source_entry", {}).get("status") == "failed"

    @pytest.mark.asyncio
    async def test_geocode_network_error(self):
        """Geocode returns source entry with error on network error."""
        with (
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                side_effect=Exception("Connection refused"),
            ),
            patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client,
        ):
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await geocode_address("Rue de Bourg 1", "1003")

        assert "lat" not in result
        assert result.get("_source_entry", {}).get("status") == "failed"


# ---------------------------------------------------------------------------
# RegBL tests
# ---------------------------------------------------------------------------


class TestRegBL:
    @pytest.mark.asyncio
    async def test_regbl_data_parsing(self):
        """RegBL response is correctly parsed into standard fields."""
        # geo.admin.ch GWR layer uses these field names
        mock_data = {
            "feature": {
                "attributes": {
                    "gbauj": 1965,
                    "gastw": 5,
                    "ganzwhg": 12,
                    "gebf": 850.5,
                    "gwaerzh1": "7520",
                    "genh1": "7200",
                    "gklas": "1020",
                    "gkat": "1025",
                    "gbaup": 2005,
                    "egrid": "CH123",
                    "lparz": "456",
                }
            }
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_regbl_data(123456)

        assert result["construction_year"] == 1965
        assert result["floors"] == 5
        assert result["dwellings"] == 12
        assert result["living_area_m2"] == 850.5
        assert result["heating_type_code"] == "7520"
        assert result["renovation_period_code"] == 2005

    @pytest.mark.asyncio
    async def test_regbl_404(self):
        """RegBL returns source entry with failed status on 404."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with (
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client,
        ):
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_regbl_data(999999)

        assert "construction_year" not in result
        assert result.get("_source_entry", {}).get("status") == "failed"


# ---------------------------------------------------------------------------
# Swisstopo tests
# ---------------------------------------------------------------------------


class TestSwisstopo:
    def test_image_url_generation(self):
        """Swisstopo URL is correctly built for known coordinates."""
        url = fetch_swisstopo_image_url(46.5197, 6.6323, zoom=18)
        assert url.startswith("https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage-product")
        assert "/18/" in url
        assert url.endswith(".jpeg")

    def test_tile_conversion(self):
        """Lat/lon to tile conversion produces reasonable values."""
        x, y = _lat_lon_to_tile(46.5197, 6.6323, 18)
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert x > 0
        assert y > 0

    def test_different_zoom_levels(self):
        """Different zoom levels produce different tile coordinates."""
        url_14 = fetch_swisstopo_image_url(46.5, 6.6, zoom=14)
        url_18 = fetch_swisstopo_image_url(46.5, 6.6, zoom=18)
        assert "/14/" in url_14
        assert "/18/" in url_18
        assert url_14 != url_18


# ---------------------------------------------------------------------------
# Cadastre tests
# ---------------------------------------------------------------------------


class TestCadastre:
    @pytest.mark.asyncio
    async def test_cadastre_egrid_found(self):
        """Cadastre lookup returns EGRID when found."""
        mock_data = {
            "results": [
                {
                    "attributes": {
                        "egrid": "CH123456789012",
                        "grundstueckNr": "1234",
                        "gemeindename": "Lausanne",
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_cadastre_egrid(46.5197, 6.6323)

        assert result["egrid"] == "CH123456789012"
        assert result["parcel_number"] == "1234"
        assert result["municipality"] == "Lausanne"

    @pytest.mark.asyncio
    async def test_cadastre_empty_results(self):
        """Cadastre returns empty dict when no results."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_cadastre_egrid(0.0, 0.0)

        assert result == {}


# ---------------------------------------------------------------------------
# AI enrichment tests
# ---------------------------------------------------------------------------


class TestAIEnrichment:
    def test_ai_prompt_construction(self):
        """AI prompt includes building data and expected output keys."""
        building_data = {
            "address": "Rue de Bourg 1",
            "construction_year": 1965,
            "building_type": "residential",
        }
        prompt = _build_ai_prompt(building_data, "Near train station")
        assert "Rue de Bourg 1" in prompt
        assert "1965" in prompt
        assert "building_description" in prompt
        assert "risk_assessment_hint" in prompt
        assert "Near train station" in prompt

    @pytest.mark.asyncio
    async def test_ai_enrichment_no_api_key(self):
        """AI enrichment returns empty dict when no API key is set."""
        from app.services.building_enrichment_service import enrich_building_with_ai

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": ""}, clear=False):
            result = await enrich_building_with_ai({"address": "test"})
        assert result == {}


# ---------------------------------------------------------------------------
# Orchestration tests (enrich_building)
# ---------------------------------------------------------------------------


class TestEnrichBuildingOrchestration:
    @pytest.mark.asyncio
    async def test_enrich_building_not_found(self):
        """enrich_building returns error for nonexistent building."""
        from app.services.building_enrichment_service import enrich_building

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await enrich_building(mock_db, uuid.uuid4())
        assert "Building not found" in result.errors

    @pytest.mark.asyncio
    async def test_enrich_building_full_pipeline(self):
        """enrich_building orchestrates geocode + regbl + cadastre + image."""
        from app.services.building_enrichment_service import enrich_building

        building_id = uuid.uuid4()
        mock_building = MagicMock()
        mock_building.id = building_id
        mock_building.address = "Rue de Bourg 1"
        mock_building.postal_code = "1003"
        mock_building.city = "Lausanne"
        mock_building.canton = "VD"
        mock_building.latitude = None
        mock_building.longitude = None
        mock_building.egid = None
        mock_building.egrid = None
        mock_building.parcel_number = None
        mock_building.construction_year = None
        mock_building.renovation_year = None
        mock_building.floors_above = None
        mock_building.surface_area_m2 = None
        mock_building.building_type = "residential"
        mock_building.dwellings = None
        mock_building.has_elevator = False
        mock_building.source_metadata_json = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_building
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with (
            patch(
                "app.services.building_enrichment_service.geocode_address",
                return_value={
                    "lat": 46.52,
                    "lon": 6.63,
                    "egid": 12345,
                    "label": "Test",
                    "match_quality": "exact",
                    "_source_entry": {
                        "source_name": "geocode",
                        "status": "success",
                        "confidence": "high",
                        "fetched_at": "2026-01-01T00:00:00+00:00",
                        "retry_count": 0,
                        "error": None,
                        "match_quality": "exact",
                    },
                },
            ),
            patch(
                "app.services.building_enrichment_service.fetch_regbl_data",
                return_value={
                    "construction_year": 1965,
                    "floors": 5,
                    "egid_confidence": "verified",
                    "_source_entry": {
                        "source_name": "regbl",
                        "status": "success",
                        "confidence": "high",
                        "fetched_at": "2026-01-01T00:00:00+00:00",
                        "retry_count": 0,
                        "error": None,
                        "match_quality": "verified",
                    },
                },
            ),
            patch(
                "app.services.building_enrichment_service.fetch_cadastre_egrid",
                return_value={"egrid": "CH999", "parcel_number": "42"},
            ),
            patch(
                "app.services.building_enrichment_service.enrich_building_with_ai",
                return_value={},
            ),
        ):
            result = await enrich_building(mock_db, building_id, skip_ai=True)

        assert result.geocoded is True
        assert result.regbl_found is True
        assert result.egrid_found is True
        assert "latitude" in result.fields_updated
        assert "longitude" in result.fields_updated
        assert "egid" in result.fields_updated
        assert "construction_year" in result.fields_updated

    @pytest.mark.asyncio
    async def test_enrich_building_skip_flags(self):
        """enrich_building respects skip flags."""
        from app.services.building_enrichment_service import enrich_building

        building_id = uuid.uuid4()
        mock_building = MagicMock()
        mock_building.id = building_id
        mock_building.address = "Test"
        mock_building.postal_code = "1000"
        mock_building.city = "Lausanne"
        mock_building.canton = "VD"
        mock_building.latitude = None
        mock_building.longitude = None
        mock_building.egid = None
        mock_building.egrid = None
        mock_building.parcel_number = None
        mock_building.construction_year = 2000
        mock_building.renovation_year = None
        mock_building.floors_above = 3
        mock_building.surface_area_m2 = 100.0
        mock_building.building_type = "residential"
        mock_building.dwellings = None
        mock_building.has_elevator = False
        mock_building.source_metadata_json = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_building
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with (
            patch(
                "app.services.building_enrichment_service.geocode_address",
            ) as mock_geo,
            patch(
                "app.services.building_enrichment_service.fetch_regbl_data",
            ) as mock_regbl,
            patch(
                "app.services.building_enrichment_service.enrich_building_with_ai",
            ) as mock_ai,
        ):
            result = await enrich_building(
                mock_db,
                building_id,
                skip_geocode=True,
                skip_regbl=True,
                skip_ai=True,
                skip_image=True,
                skip_cadastre=True,
            )

        mock_geo.assert_not_called()
        mock_regbl.assert_not_called()
        mock_ai.assert_not_called()
        # Pure computations (neighborhood_score, pollutant_risk, accessibility, subsidies)
        # always run even when all external sources are skipped
        assert "latitude" not in result.fields_updated
        assert "longitude" not in result.fields_updated
        assert "egid" not in result.fields_updated
        assert result.pollutant_risk_computed is True
        assert result.accessibility_computed is True
        assert result.subsidies_computed is True


# ---------------------------------------------------------------------------
# Batch enrichment tests
# ---------------------------------------------------------------------------


class TestBatchEnrichment:
    @pytest.mark.asyncio
    async def test_batch_enrichment_empty(self):
        """Batch enrichment handles empty building list."""
        from app.services.building_enrichment_service import enrich_all_buildings

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await enrich_all_buildings(mock_db)
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_enrichment_error_handling(self):
        """Batch enrichment continues after individual failures."""
        from app.services.building_enrichment_service import enrich_all_buildings

        b1 = MagicMock()
        b1.id = uuid.uuid4()
        b2 = MagicMock()
        b2.id = uuid.uuid4()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [b1, b2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        call_count = 0

        async def mock_enrich(db, bid, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("API down")
            return EnrichmentResult(building_id=bid, fields_updated=["latitude"])

        with patch(
            "app.services.building_enrichment_service.enrich_building",
            side_effect=mock_enrich,
        ):
            results = await enrich_all_buildings(mock_db)

        assert len(results) == 2
        assert results[0].errors  # first failed
        assert results[1].fields_updated  # second succeeded


# ---------------------------------------------------------------------------
# Additional unit tests
# ---------------------------------------------------------------------------


class TestEnrichmentResultAggregation:
    def test_result_with_all_sources(self):
        """EnrichmentResult can represent all sources enriched."""
        r = EnrichmentResult(
            building_id=uuid.uuid4(),
            geocoded=True,
            regbl_found=True,
            egrid_found=True,
            image_url="https://example.com/tile.jpeg",
            ai_enriched=True,
            fields_updated=["latitude", "longitude", "egid", "construction_year"],
        )
        assert len(r.fields_updated) == 4
        assert r.image_url is not None

    def test_result_with_errors_only(self):
        """EnrichmentResult can capture errors without updates."""
        r = EnrichmentResult(
            building_id=uuid.uuid4(),
            errors=["API timeout", "Rate limited"],
        )
        assert len(r.errors) == 2
        assert r.geocoded is False
        assert r.fields_updated == []

    def test_enrichment_request_all_skips(self):
        """EnrichmentRequest can skip all sources."""
        r = EnrichmentRequest(
            building_id=uuid.uuid4(),
            skip_geocode=True,
            skip_regbl=True,
            skip_ai=True,
            skip_cadastre=True,
            skip_image=True,
        )
        assert r.skip_geocode is True
        assert r.skip_cadastre is True

    def test_enrichment_result_new_fields(self):
        """EnrichmentResult supports all new source flags."""
        r = EnrichmentResult(
            building_id=uuid.uuid4(),
            radon_fetched=True,
            natural_hazards_fetched=True,
            noise_fetched=True,
            solar_fetched=True,
            heritage_fetched=True,
            transport_fetched=True,
            seismic_fetched=True,
            water_protection_fetched=True,
            neighborhood_score=7.5,
            pollutant_risk_computed=True,
            accessibility_computed=True,
            subsidies_computed=True,
        )
        assert r.radon_fetched is True
        assert r.neighborhood_score == 7.5
        assert r.subsidies_computed is True


# ---------------------------------------------------------------------------
# Radon risk tests
# ---------------------------------------------------------------------------


class TestRadonRisk:
    @pytest.mark.asyncio
    async def test_radon_risk_high_zone(self):
        """Radon fetch returns high risk for high zone."""
        mock_data = {"results": [{"attributes": {"zone": "3", "probability": 0.75}}]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_radon_risk(46.52, 6.63)

        assert result["radon_zone"] == "3"
        assert result["radon_level"] == "high"
        assert result["radon_probability"] == 0.75

    @pytest.mark.asyncio
    async def test_radon_risk_empty_results(self):
        """Radon fetch returns empty dict when no results."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_radon_risk(46.52, 6.63)

        assert result == {}

    @pytest.mark.asyncio
    async def test_radon_risk_network_error(self):
        """Radon fetch returns empty dict on network error."""
        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_radon_risk(46.52, 6.63)

        assert result == {}


# ---------------------------------------------------------------------------
# Natural hazards tests
# ---------------------------------------------------------------------------


class TestNaturalHazards:
    @pytest.mark.asyncio
    async def test_natural_hazards_multi_layer(self):
        """Natural hazards parses multiple layer results."""
        mock_data = {
            "results": [
                {"layerBodId": "ch.bafu.showme-gemeinden_hochwasser", "attributes": {"stufe": "medium"}},
                {"layerBodId": "ch.bafu.showme-gemeinden_rutschungen", "attributes": {"stufe": "low"}},
                {"layerBodId": "ch.bafu.showme-gemeinden_sturzprozesse", "attributes": {"stufe": "high"}},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_natural_hazards(46.52, 6.63)

        assert result["flood_risk"] == "medium"
        assert result["landslide_risk"] == "low"
        assert result["rockfall_risk"] == "high"


# ---------------------------------------------------------------------------
# Noise tests
# ---------------------------------------------------------------------------


class TestNoise:
    @pytest.mark.asyncio
    async def test_noise_loud(self):
        """Noise fetch correctly classifies loud noise."""
        mock_data = {"results": [{"attributes": {"dblr": 62.5}}]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_noise_data(46.52, 6.63)

        assert result["road_noise_day_db"] == 62.5
        assert result["noise_level"] == "loud"


# ---------------------------------------------------------------------------
# Solar potential tests
# ---------------------------------------------------------------------------


class TestSolarPotential:
    @pytest.mark.asyncio
    async def test_solar_high_suitability(self):
        """Solar fetch returns high suitability."""
        mock_data = {"results": [{"attributes": {"stromertrag": 1500, "flaeche": 80, "klasse": "gut geeignet"}}]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_solar_potential(46.52, 6.63)

        assert result["solar_potential_kwh"] == 1500.0
        assert result["roof_area_m2"] == 80.0
        assert result["suitability"] == "high"


# ---------------------------------------------------------------------------
# Heritage / ISOS tests
# ---------------------------------------------------------------------------


class TestHeritage:
    @pytest.mark.asyncio
    async def test_heritage_protected(self):
        """Heritage fetch returns protected site."""
        mock_data = {"results": [{"attributes": {"kategorie": "A", "ortsbildname": "Vieille Ville de Lausanne"}}]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_heritage_status(46.52, 6.63)

        assert result["isos_protected"] is True
        assert result["isos_category"] == "A"
        assert "Lausanne" in result["site_name"]

    @pytest.mark.asyncio
    async def test_heritage_not_protected(self):
        """Heritage fetch returns not protected when no results."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_heritage_status(46.52, 6.63)

        assert result["isos_protected"] is False


# ---------------------------------------------------------------------------
# Transport quality tests
# ---------------------------------------------------------------------------


class TestTransportQuality:
    @pytest.mark.asyncio
    async def test_transport_quality_a(self):
        """Transport fetch returns class A."""
        mock_data = {"results": [{"attributes": {"klasse": "A"}}]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_transport_quality(46.52, 6.63)

        assert result["transport_quality_class"] == "A"
        assert "Excellent" in result["description"]


# ---------------------------------------------------------------------------
# Seismic zone tests
# ---------------------------------------------------------------------------


class TestSeismicZone:
    @pytest.mark.asyncio
    async def test_seismic_zone_parsing(self):
        """Seismic fetch parses zone and derives class."""
        mock_data = {"results": [{"attributes": {"zone": "2"}}]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_seismic_zone(46.52, 6.63)

        assert result["seismic_zone"] == "2"
        assert result["seismic_class"] == "Z2"


# ---------------------------------------------------------------------------
# Water protection tests
# ---------------------------------------------------------------------------


class TestWaterProtection:
    @pytest.mark.asyncio
    async def test_water_protection_zone(self):
        """Water protection fetch returns zone info."""
        mock_data = {"results": [{"attributes": {"zone": "S2", "typ": "Schutzzone"}}]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_water_protection(46.52, 6.63)

        assert result["protection_zone"] == "S2"
        assert result["zone_type"] == "Schutzzone"


# ---------------------------------------------------------------------------
# Neighborhood score tests
# ---------------------------------------------------------------------------


class TestNeighborhoodScore:
    def test_score_excellent_neighborhood(self):
        """High quality transport + quiet + no hazards + good solar = high score."""
        data = {
            "transport": {"transport_quality_class": "A"},
            "noise": {"road_noise_day_db": 40},
            "natural_hazards": {"flood_risk": "none", "landslide_risk": "none", "rockfall_risk": "none"},
            "solar": {"suitability": "high"},
        }
        score = compute_neighborhood_score(data)
        assert score >= 9.0

    def test_score_poor_neighborhood(self):
        """Poor transport + loud + high hazards = low score."""
        data = {
            "transport": {"transport_quality_class": "D"},
            "noise": {"road_noise_day_db": 70},
            "natural_hazards": {"flood_risk": "high", "landslide_risk": "high", "rockfall_risk": "high"},
            "solar": {"suitability": "low"},
        }
        score = compute_neighborhood_score(data)
        assert score <= 3.0

    def test_score_heritage_bonus(self):
        """Heritage protection adds +2 bonus."""
        base_data = {
            "transport": {"transport_quality_class": "C"},
            "heritage": {"isos_protected": False},
        }
        base_score = compute_neighborhood_score(base_data)

        heritage_data = {
            "transport": {"transport_quality_class": "C"},
            "heritage": {"isos_protected": True},
        }
        heritage_score = compute_neighborhood_score(heritage_data)

        assert heritage_score == base_score + 2.0

    def test_score_empty_data_returns_neutral(self):
        """Empty enrichment data returns neutral 5.0."""
        assert compute_neighborhood_score({}) == 5.0


# ---------------------------------------------------------------------------
# Pollutant risk prediction tests
# ---------------------------------------------------------------------------


class TestPollutantRiskPrediction:
    def test_1965_residential_high_asbestos(self):
        """1965 residential building has high asbestos probability."""
        result = compute_pollutant_risk_prediction(
            {
                "construction_year": 1965,
                "building_type": "residential",
                "floors_above": 5,
                "canton": "VD",
            }
        )
        assert result["asbestos_probability"] >= 0.85
        assert result["pcb_probability"] == 0.60
        assert result["lead_probability"] == 0.30
        assert result["hap_probability"] == 0.40
        assert result["overall_risk_score"] > 0.0
        assert len(result["risk_factors"]) > 0

    def test_2010_building_no_risk(self):
        """2010 building has zero pollutant probability."""
        result = compute_pollutant_risk_prediction(
            {
                "construction_year": 2010,
                "building_type": "residential",
            }
        )
        assert result["asbestos_probability"] == 0.0
        assert result["pcb_probability"] == 0.0
        assert result["lead_probability"] == 0.0

    def test_renovation_reduces_risk(self):
        """Post-2000 renovation reduces all probabilities."""
        base = compute_pollutant_risk_prediction(
            {
                "construction_year": 1965,
                "building_type": "residential",
                "floors_above": 5,
            }
        )
        renovated = compute_pollutant_risk_prediction(
            {
                "construction_year": 1965,
                "building_type": "residential",
                "floors_above": 5,
                "renovation_year": 2015,
            }
        )
        assert renovated["asbestos_probability"] < base["asbestos_probability"]
        assert renovated["pcb_probability"] < base["pcb_probability"]

    def test_unknown_year(self):
        """Unknown construction year returns moderate risk with explanation."""
        result = compute_pollutant_risk_prediction({})
        assert result["overall_risk_score"] == 0.5
        assert any("unknown" in f for f in result["risk_factors"])

    def test_high_radon_level(self):
        """High radon level increases radon probability."""
        result = compute_pollutant_risk_prediction(
            {
                "construction_year": 2000,
                "radon_level": "high",
            }
        )
        assert result["radon_probability"] == 0.70


# ---------------------------------------------------------------------------
# Accessibility assessment tests
# ---------------------------------------------------------------------------


class TestAccessibilityAssessment:
    def test_post_2004_large_building(self):
        """Post-2004 building with 8+ dwellings requires full compliance."""
        result = compute_accessibility_assessment(
            {
                "construction_year": 2010,
                "floors_above": 4,
                "dwellings": 12,
            }
        )
        assert result["compliance_status"] == "full_compliance_required"
        assert len(result["requirements"]) >= 2

    def test_pre_2004_major_renovation(self):
        """Pre-2004 building with major renovation requires adaptation."""
        result = compute_accessibility_assessment(
            {
                "construction_year": 1980,
                "renovation_year": 2010,
                "dwellings": 10,
            }
        )
        assert result["compliance_status"] == "adaptation_required"

    def test_old_building_no_renovation(self):
        """Old building without renovation has no legal requirement."""
        result = compute_accessibility_assessment(
            {
                "construction_year": 1960,
                "floors_above": 2,
                "dwellings": 4,
            }
        )
        assert result["compliance_status"] == "no_legal_requirement"

    def test_elevator_recommendation(self):
        """Building with >3 floors and no elevator gets recommendation."""
        result = compute_accessibility_assessment(
            {
                "construction_year": 1980,
                "floors_above": 5,
                "has_elevator": False,
            }
        )
        assert any("Elevator" in r for r in result["recommendations"])


# ---------------------------------------------------------------------------
# Subsidy eligibility tests
# ---------------------------------------------------------------------------


class TestSubsidyEligibility:
    def test_oil_heating_eligible(self):
        """Oil-heated building is eligible for heating replacement subsidy."""
        result = estimate_subsidy_eligibility(
            {
                "construction_year": 1975,
                "heating_type_code": "7520",  # oil
                "canton": "VD",
                "surface_area_m2": 150,
            }
        )
        programs = [p["name"] for p in result["eligible_programs"]]
        assert any("chauffage" in p.lower() for p in programs)
        assert result["total_estimated_chf"] > 0

    def test_old_building_insulation(self):
        """Pre-2000 building is eligible for insulation subsidy."""
        result = estimate_subsidy_eligibility(
            {
                "construction_year": 1970,
            }
        )
        programs = [p["name"] for p in result["eligible_programs"]]
        assert any("isolation" in p.lower() or "fenetre" in p.lower() for p in programs)

    def test_solar_eligible(self):
        """Building with high solar suitability gets solar subsidy."""
        result = estimate_subsidy_eligibility(
            {
                "construction_year": 2005,
                "solar_suitability": "high",
            }
        )
        programs = [p["name"] for p in result["eligible_programs"]]
        assert any("photovoltaique" in p.lower() or "pronovo" in p.lower() for p in programs)

    def test_asbestos_vd_subsidy(self):
        """Asbestos-positive building in VD gets decontamination subsidy."""
        result = estimate_subsidy_eligibility(
            {
                "construction_year": 1970,
                "canton": "VD",
                "asbestos_positive": True,
            }
        )
        programs = [p["name"] for p in result["eligible_programs"]]
        assert any("desamiantage" in p.lower() for p in programs)

    def test_new_building_minimal_subsidies(self):
        """New building with modern heating has minimal subsidies."""
        result = estimate_subsidy_eligibility(
            {
                "construction_year": 2020,
                "heating_type_code": "pac",
            }
        )
        assert result["total_estimated_chf"] == 0


# ---------------------------------------------------------------------------
# Generic _geo_identify helper tests
# ---------------------------------------------------------------------------


class TestGeoIdentify:
    @pytest.mark.asyncio
    async def test_geo_identify_returns_attributes(self):
        """_geo_identify returns attributes from first result."""
        mock_data = {"results": [{"attributes": {"zone": "Z1", "value": 42}}]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await _geo_identify(46.52, 6.63, "ch.test.layer")

        assert result["zone"] == "Z1"
        assert result["value"] == 42

    @pytest.mark.asyncio
    async def test_geo_identify_empty_results(self):
        """_geo_identify returns source entry (success) when no results at location."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()

        with (
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client,
        ):
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await _geo_identify(46.52, 6.63, "ch.test.layer")

        # No data keys, only _source_entry
        data_keys = {k for k in result if not k.startswith("_")}
        assert data_keys == set()
        assert result.get("_source_entry", {}).get("status") == "success"

    @pytest.mark.asyncio
    async def test_geo_identify_network_error(self):
        """_geo_identify returns source entry with failed status on error."""
        with (
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                side_effect=Exception("timeout"),
            ),
            patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client,
        ):
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await _geo_identify(46.52, 6.63, "ch.test.layer")

        assert result.get("_source_entry", {}).get("status") in ("failed", "timeout")


# ---------------------------------------------------------------------------
# Railway noise tests
# ---------------------------------------------------------------------------


class TestRailwayNoise:
    @pytest.mark.asyncio
    async def test_railway_noise_found(self):
        """Railway noise returns dB value."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"lr_tag": 58.3},
        ):
            result = await fetch_railway_noise(46.52, 6.63)

        assert result["railway_noise_day_db"] == 58.3

    @pytest.mark.asyncio
    async def test_railway_noise_empty(self):
        """Railway noise returns empty dict when no data."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={},
        ):
            result = await fetch_railway_noise(46.52, 6.63)

        assert result == {}


# ---------------------------------------------------------------------------
# Aircraft noise tests
# ---------------------------------------------------------------------------


class TestAircraftNoise:
    @pytest.mark.asyncio
    async def test_aircraft_noise_found(self):
        """Aircraft noise returns dB value."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"lr_tag": 65.0},
        ):
            result = await fetch_aircraft_noise(46.52, 6.63)

        assert result["aircraft_noise_db"] == 65.0


# ---------------------------------------------------------------------------
# Building zones tests
# ---------------------------------------------------------------------------


class TestBuildingZones:
    @pytest.mark.asyncio
    async def test_building_zones_found(self):
        """Building zones returns zone info."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"zonentyp": "Wohnzone", "ch_code": "W2", "bezeichnung": "Wohnzone W2"},
        ):
            result = await fetch_building_zones(46.52, 6.63)

        assert result["zone_type"] == "Wohnzone"
        assert result["zone_code"] == "W2"
        assert result["zone_description"] == "Wohnzone W2"


# ---------------------------------------------------------------------------
# Contaminated sites tests
# ---------------------------------------------------------------------------


class TestContaminatedSites:
    @pytest.mark.asyncio
    async def test_contaminated_site_found(self):
        """Contaminated sites returns positive when found."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"standorttyp": "Betriebsstandort", "untersuchungsstand": "Voruntersuchung"},
        ):
            result = await fetch_contaminated_sites(46.52, 6.63)

        assert result["is_contaminated"] is True
        assert result["site_type"] == "Betriebsstandort"
        assert result["investigation_status"] == "Voruntersuchung"

    @pytest.mark.asyncio
    async def test_contaminated_site_not_found(self):
        """Contaminated sites returns false when empty."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={},
        ):
            result = await fetch_contaminated_sites(46.52, 6.63)

        assert result["is_contaminated"] is False


# ---------------------------------------------------------------------------
# Groundwater zones tests
# ---------------------------------------------------------------------------


class TestGroundwaterZones:
    @pytest.mark.asyncio
    async def test_groundwater_zone_s2(self):
        """Groundwater zones returns S2 protection zone."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"zone": "S2", "typ": "Schutzzone"},
        ):
            result = await fetch_groundwater_zones(46.52, 6.63)

        assert result["protection_zone"] == "S2"
        assert result["zone_type"] == "Schutzzone"


# ---------------------------------------------------------------------------
# Flood zones tests
# ---------------------------------------------------------------------------


class TestFloodZones:
    @pytest.mark.asyncio
    async def test_flood_zone_data(self):
        """Flood zones returns danger level."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"gefahrenstufe": "erheblich", "wiederkehrperiode": 100},
        ):
            result = await fetch_flood_zones(46.52, 6.63)

        assert result["flood_danger_level"] == "erheblich"
        assert result["flood_return_period"] == 100


# ---------------------------------------------------------------------------
# Mobile coverage tests
# ---------------------------------------------------------------------------


class TestMobileCoverage:
    @pytest.mark.asyncio
    async def test_5g_coverage_found(self):
        """Mobile coverage returns True when 5G layer returns data."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"provider": "Swisscom"},
        ):
            result = await fetch_mobile_coverage(46.52, 6.63)

        assert result["has_5g_coverage"] is True

    @pytest.mark.asyncio
    async def test_no_5g_coverage(self):
        """Mobile coverage returns False when no 5G data."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={},
        ):
            result = await fetch_mobile_coverage(46.52, 6.63)

        assert result["has_5g_coverage"] is False


# ---------------------------------------------------------------------------
# Broadband tests
# ---------------------------------------------------------------------------


class TestBroadband:
    @pytest.mark.asyncio
    async def test_broadband_data(self):
        """Broadband returns technology and speed."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"technology": "FTTH", "max_speed": 10000},
        ):
            result = await fetch_broadband(46.52, 6.63)

        assert result["broadband_technology"] == "FTTH"
        assert result["max_speed_mbps"] == 10000.0


# ---------------------------------------------------------------------------
# EV charging tests
# ---------------------------------------------------------------------------


class TestEvCharging:
    @pytest.mark.asyncio
    async def test_ev_station_found(self):
        """EV charging returns station found."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"distance": 150},
        ):
            result = await fetch_ev_charging(46.52, 6.63)

        assert result["ev_stations_nearby"] == 1
        assert result["nearest_distance_m"] == 150.0

    @pytest.mark.asyncio
    async def test_ev_station_not_found(self):
        """EV charging returns 0 stations when no data."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={},
        ):
            result = await fetch_ev_charging(46.52, 6.63)

        assert result["ev_stations_nearby"] == 0


# ---------------------------------------------------------------------------
# Thermal networks tests
# ---------------------------------------------------------------------------


class TestThermalNetworks:
    @pytest.mark.asyncio
    async def test_district_heating_found(self):
        """Thermal networks returns district heating info."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"name": "Fernwarme Lausanne"},
        ):
            result = await fetch_thermal_networks(46.52, 6.63)

        assert result["has_district_heating"] is True
        assert result["network_name"] == "Fernwarme Lausanne"

    @pytest.mark.asyncio
    async def test_no_district_heating(self):
        """Thermal networks returns False when no data."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={},
        ):
            result = await fetch_thermal_networks(46.52, 6.63)

        assert result["has_district_heating"] is False


# ---------------------------------------------------------------------------
# Protected monuments tests
# ---------------------------------------------------------------------------


class TestProtectedMonuments:
    @pytest.mark.asyncio
    async def test_monument_found(self):
        """Protected monuments returns listed monument."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"kategorie": "national"},
        ):
            result = await fetch_protected_monuments(46.52, 6.63)

        assert result["is_listed_monument"] is True
        assert result["monument_category"] == "national"


# ---------------------------------------------------------------------------
# Forest reserves tests
# ---------------------------------------------------------------------------


class TestAgriculturalZones:
    @pytest.mark.asyncio
    async def test_agricultural_zone_found(self):
        """Agricultural zones returns soil quality info."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"eignung": "sehr gut", "zone": "Landwirtschaftszone"},
        ):
            result = await fetch_agricultural_zones(46.52, 6.63)

        assert result["soil_quality"] == "sehr gut"
        assert result["agricultural_zone"] == "Landwirtschaftszone"


# ---------------------------------------------------------------------------
# Forest reserves tests
# ---------------------------------------------------------------------------


class TestForestReserves:
    @pytest.mark.asyncio
    async def test_forest_reserve_found(self):
        """Forest reserves returns reserve info."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"name": "Bois de Sauvabelin"},
        ):
            result = await fetch_forest_reserves(46.52, 6.63)

        assert result["in_forest_reserve"] is True
        assert result["reserve_name"] == "Bois de Sauvabelin"


# ---------------------------------------------------------------------------
# Military zones tests
# ---------------------------------------------------------------------------


class TestMilitaryZones:
    @pytest.mark.asyncio
    async def test_shooting_range_nearby(self):
        """Military zones returns shooting range proximity."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"distance": 800},
        ):
            result = await fetch_military_zones(46.52, 6.63)

        assert result["near_shooting_range"] is True
        assert result["distance_m"] == 800.0


# ---------------------------------------------------------------------------
# Accident sites tests
# ---------------------------------------------------------------------------


class TestAccidentSites:
    @pytest.mark.asyncio
    async def test_seveso_site_found(self):
        """Accident sites returns Seveso site info."""
        with patch(
            "app.services.building_enrichment_service._geo_identify",
            return_value={"name": "Chem Corp", "distance": 500},
        ):
            result = await fetch_accident_sites(46.52, 6.63)

        assert result["near_seveso_site"] is True
        assert result["site_name"] == "Chem Corp"
        assert result["distance_m"] == 500.0


# ---------------------------------------------------------------------------
# OSM amenities tests
# ---------------------------------------------------------------------------


class TestOsmAmenities:
    @pytest.mark.asyncio
    async def test_osm_amenities_count(self):
        """OSM amenities counts by type."""
        mock_data = {
            "elements": [
                {"tags": {"amenity": "school"}},
                {"tags": {"amenity": "school"}},
                {"tags": {"amenity": "restaurant"}},
                {"tags": {"amenity": "cafe"}},
                {"tags": {"amenity": "unknown_type"}},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_osm_amenities(46.52, 6.63)

        assert result["schools"] == 2
        assert result["restaurants"] == 1
        assert result["cafes"] == 1
        assert result["hospitals"] == 0
        assert result["total_amenities"] == 5

    @pytest.mark.asyncio
    async def test_osm_amenities_error(self):
        """OSM amenities returns source entry with error status on error."""
        with (
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                side_effect=Exception("timeout"),
            ),
            patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client,
        ):
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_osm_amenities(46.52, 6.63)

        assert "total_amenities" not in result
        assert result.get("_source_entry", {}).get("status") in ("failed", "timeout")


# ---------------------------------------------------------------------------
# OSM building details tests
# ---------------------------------------------------------------------------


class TestOsmBuildingDetails:
    @pytest.mark.asyncio
    async def test_osm_building_found(self):
        """OSM building details returns building info."""
        mock_data = {
            "elements": [
                {
                    "tags": {
                        "height": "15.5",
                        "building:levels": "4",
                        "building:material": "brick",
                        "roof:shape": "gabled",
                        "wheelchair": "yes",
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_osm_building_details(46.52, 6.63)

        assert result["height"] == 15.5
        assert result["levels"] == 4
        assert result["material"] == "brick"
        assert result["roof_type"] == "gabled"
        assert result["wheelchair_access"] == "yes"


# ---------------------------------------------------------------------------
# Climate data tests
# ---------------------------------------------------------------------------


class TestClimateData:
    def test_climate_plateau(self):
        """Climate data for Swiss plateau returns reasonable values."""
        result = fetch_climate_data(46.95, 7.45)  # Bern area
        assert 5.0 < result["avg_temp_c"] < 15.0
        assert result["precipitation_mm"] > 700
        assert result["frost_days"] > 30
        assert result["sunshine_hours"] > 1000
        assert result["heating_degree_days"] > 2000
        assert "estimated_altitude_m" in result

    def test_climate_ticino_has_tropical_days(self):
        """Climate data for Ticino includes tropical days."""
        result = fetch_climate_data(46.0, 8.95)  # Lugano area
        assert result["tropical_days"] > 0


# ---------------------------------------------------------------------------
# Nearest stops tests
# ---------------------------------------------------------------------------


class TestNearestStops:
    @pytest.mark.asyncio
    async def test_nearest_stops_found(self):
        """Nearest stops returns station list."""
        mock_data = {
            "stations": [
                {"name": "Lausanne", "distance": 150},
                {"name": "Flon", "distance": 400},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_nearest_stops(46.52, 6.63)

        assert result["nearest_stop_name"] == "Lausanne"
        assert result["nearest_stop_distance_m"] == 150
        assert len(result["stops"]) == 2

    @pytest.mark.asyncio
    async def test_nearest_stops_empty(self):
        """Nearest stops returns source entry when no stations."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"stations": []}
        mock_resp.raise_for_status = MagicMock()

        with (
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client,
        ):
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_nearest_stops(46.52, 6.63)

        assert "stops" not in result
        assert result.get("_source_entry", {}).get("status") == "success"


# ---------------------------------------------------------------------------
# Connectivity score tests
# ---------------------------------------------------------------------------


class TestConnectivityScore:
    def test_full_connectivity(self):
        """Full connectivity (5G + fast broadband + EV + heating) scores high."""
        data = {
            "mobile_coverage": {"has_5g_coverage": True},
            "broadband": {"max_speed_mbps": 10000},
            "ev_charging": {"ev_stations_nearby": 1},
            "thermal_networks": {"has_district_heating": True},
        }
        score = compute_connectivity_score(data)
        assert score == 10.0

    def test_no_connectivity(self):
        """No connectivity data scores zero."""
        score = compute_connectivity_score({})
        assert score == 0.0

    def test_partial_connectivity(self):
        """Partial connectivity scores proportionally."""
        data = {
            "mobile_coverage": {"has_5g_coverage": True},
            "broadband": {"max_speed_mbps": 50},
        }
        score = compute_connectivity_score(data)
        assert 2.0 < score < 5.0


# ---------------------------------------------------------------------------
# Environmental risk score tests
# ---------------------------------------------------------------------------


class TestEnvironmentalRiskScore:
    def test_safe_environment(self):
        """No environmental risks scores 10."""
        data = {
            "radon": {"radon_level": "low"},
            "noise": {"road_noise_day_db": 35},
        }
        score = compute_environmental_risk_score(data)
        assert score >= 9.0

    def test_risky_environment(self):
        """Multiple environmental risks score low."""
        data = {
            "flood_zones": {"flood_danger_level": "high"},
            "seismic": {"seismic_zone": "3b"},
            "contaminated_sites": {"is_contaminated": True},
            "radon": {"radon_level": "high"},
            "noise": {"road_noise_day_db": 70},
        }
        score = compute_environmental_risk_score(data)
        assert score <= 2.0


# ---------------------------------------------------------------------------
# Livability score tests
# ---------------------------------------------------------------------------


class TestLivabilityScore:
    def test_high_livability(self):
        """Good transport + amenities + quiet = high livability."""
        data = {
            "transport": {"transport_quality_class": "A"},
            "osm_amenities": {"total_amenities": 60},
            "noise": {"road_noise_day_db": 40},
            "connectivity_score": 8.0,
            "nearest_stops": {"nearest_stop_distance_m": 100},
        }
        score = compute_livability_score(data)
        assert score >= 8.0

    def test_empty_data_returns_neutral(self):
        """Empty data returns neutral 5.0."""
        assert compute_livability_score({}) == 5.0


# ---------------------------------------------------------------------------
# Renovation potential tests
# ---------------------------------------------------------------------------


class TestRenovationPotential:
    def test_old_oil_building_high_potential(self):
        """Old oil-heated building has high renovation potential."""
        result = compute_renovation_potential(
            {"construction_year": 1970, "heating_type_code": "7520"},
            {"solar": {"suitability": "high"}, "subsidies": {"total_estimated_chf": 15000}},
        )
        assert result["potential_score"] >= 7.0
        assert len(result["recommended_actions"]) >= 3
        assert result["estimated_savings_chf_per_year"] > 3000

    def test_modern_building_low_potential(self):
        """Modern building has low renovation potential."""
        result = compute_renovation_potential(
            {"construction_year": 2020, "heating_type_code": "pac"},
            {"solar": {"suitability": "low"}},
        )
        assert result["potential_score"] <= 2.0


# ---------------------------------------------------------------------------
# Overall intelligence score tests
# ---------------------------------------------------------------------------


class TestOverallIntelligenceScore:
    def test_high_intelligence_score(self):
        """Good data across all dimensions scores A/B."""
        data = {
            "neighborhood_score": 9.0,
            "environmental_risk_score": 8.5,
            "connectivity_score": 7.0,
            "livability_score": 8.0,
            "renovation_potential": {"potential_score": 3.0},
            "radon": {"level": "low"},
            "natural_hazards": {"flood_risk": "none"},
            "noise": {"road_noise_day_db": 40},
            "solar": {"suitability": "high"},
            "heritage": {"isos_protected": True},
            "transport": {"transport_quality_class": "A"},
            "seismic": {"seismic_zone": "1"},
            "water_protection": {"zone": "none"},
            "railway_noise": {"railway_noise_day_db": 30},
            "aircraft_noise": {},
            "building_zones": {"zone_type": "W2"},
            "contaminated_sites": {"is_contaminated": False},
            "groundwater_zones": {},
            "flood_zones": {},
            "mobile_coverage": {"has_5g_coverage": True},
            "broadband": {"max_speed_mbps": 1000},
            "ev_charging": {"ev_stations_nearby": 1},
            "thermal_networks": {"has_district_heating": True},
            "osm_amenities": {"total_amenities": 50},
            "nearest_stops": {"nearest_stop_distance_m": 100},
            "climate": {"avg_temp_c": 10},
        }
        result = compute_overall_building_intelligence_score(data)
        assert result["score_0_100"] >= 60
        assert result["grade"] in ("A", "B", "C")
        assert isinstance(result["strengths"], list)
        assert isinstance(result["weaknesses"], list)

    def test_empty_data_scores_f(self):
        """No data scores F."""
        result = compute_overall_building_intelligence_score({})
        assert result["grade"] == "F"
        assert result["score_0_100"] == 0


# ---------------------------------------------------------------------------
# EnrichmentResult extended schema tests
# ---------------------------------------------------------------------------


class TestEnrichmentResultExtended:
    def test_new_enrichment_flags(self):
        """EnrichmentResult supports all extended flags."""
        r = EnrichmentResult(
            building_id=uuid.uuid4(),
            railway_noise_fetched=True,
            aircraft_noise_fetched=True,
            building_zones_fetched=True,
            contaminated_sites_fetched=True,
            groundwater_zones_fetched=True,
            flood_zones_fetched=True,
            mobile_coverage_fetched=True,
            broadband_fetched=True,
            ev_charging_fetched=True,
            thermal_networks_fetched=True,
            protected_monuments_fetched=True,
            agricultural_zones_fetched=True,
            forest_reserves_fetched=True,
            military_zones_fetched=True,
            accident_sites_fetched=True,
            osm_amenities_fetched=True,
            osm_building_fetched=True,
            climate_computed=True,
            nearest_stops_fetched=True,
            connectivity_score=7.5,
            environmental_risk_score=8.0,
            livability_score=6.5,
            renovation_potential_computed=True,
            overall_intelligence_computed=True,
            overall_intelligence_score=72,
            overall_intelligence_grade="B",
        )
        assert r.railway_noise_fetched is True
        assert r.connectivity_score == 7.5
        assert r.overall_intelligence_grade == "B"
