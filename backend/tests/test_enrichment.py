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
    _lat_lon_to_tile,
    fetch_cadastre_egrid,
    fetch_regbl_data,
    fetch_swisstopo_image_url,
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
        """Geocode returns empty dict for unknown address."""
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

            result = await geocode_address("Nonexistent Street 999", "0000")

        assert result == {}

    @pytest.mark.asyncio
    async def test_geocode_network_error(self):
        """Geocode returns empty dict on network error."""
        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await geocode_address("Rue de Bourg 1", "1003")

        assert result == {}


# ---------------------------------------------------------------------------
# RegBL tests
# ---------------------------------------------------------------------------


class TestRegBL:
    @pytest.mark.asyncio
    async def test_regbl_data_parsing(self):
        """RegBL response is correctly parsed into standard fields."""
        mock_data = {
            "constructionYear": 1965,
            "numberOfFloors": 5,
            "numberOfDwellings": 12,
            "livingArea": 850.5,
            "heatingType": "Oil",
            "energySource": "Heating oil",
            "buildingClass": "1020",
            "buildingCategory": "Multi-family house",
            "renovationYear": 2005,
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
        assert result["heating_type"] == "Oil"
        assert result["renovation_year"] == 2005

    @pytest.mark.asyncio
    async def test_regbl_404(self):
        """RegBL returns empty dict on 404."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("app.services.building_enrichment_service.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await fetch_regbl_data(999999)

        assert result == {}


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
                return_value={"lat": 46.52, "lon": 6.63, "egid": 12345, "label": "Test"},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_regbl_data",
                return_value={"construction_year": 1965, "floors": 5},
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
        assert result.fields_updated == []


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
