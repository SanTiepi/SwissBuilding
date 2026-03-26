"""Tests for enrichment service hardening: geocode match verification,
EGID verification, retry logic, per-source confidence, enrichment quality summary,
address normalization, and _geo_identify improvements.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.building_enrichment_service import (
    _UNSUPPORTED_LAYERS,
    SUPPORTED_IDENTIFY_LAYERS,
    _extract_street_name,
    _extract_street_number,
    _geo_identify,
    _normalize_address,
    _normalize_for_comparison,
    _retry_request,
    _source_entry,
    _strip_accents,
    compute_enrichment_quality,
    fetch_regbl_data,
    geocode_address,
    verify_egid_address,
    verify_geocode_match,
)

# ---------------------------------------------------------------------------
# 1. Address normalization
# ---------------------------------------------------------------------------


class TestAddressNormalization:
    def test_normalize_basic(self):
        result = _normalize_address("Rue de Bourg 1", "1003", "Lausanne")
        assert result == "Rue de Bourg 1, 1003, Lausanne"

    def test_normalize_expands_abbreviations(self):
        result = _normalize_address("av. de la Gare 5")
        assert "avenue" in result.lower()

    def test_normalize_expands_ch(self):
        result = _normalize_address("ch. des Vignes 3")
        assert "chemin" in result.lower()

    def test_normalize_expands_rte(self):
        result = _normalize_address("rte de Geneve 10")
        assert "route" in result.lower()

    def test_normalize_removes_extra_spaces(self):
        result = _normalize_address("Rue   du   Test    1")
        assert "   " not in result

    def test_normalize_empty(self):
        result = _normalize_address("", "", "")
        assert result == ""

    def test_strip_accents(self):
        assert _strip_accents("Geneve") == "Geneve"
        assert _strip_accents("Geneve") == "Geneve"  # no accents = unchanged

    def test_normalize_for_comparison(self):
        result = _normalize_for_comparison("Av. de la Gare 5, 1003 Lausanne")
        assert "avenue" in result or "av" in result
        assert "gare" in result

    def test_extract_street_number(self):
        assert _extract_street_number("Rue de Bourg 12") == "12"
        assert _extract_street_number("12 Rue de Bourg") == "12"
        assert _extract_street_number("Rue de Bourg 12a") == "12a"
        assert _extract_street_number("Rue de Bourg") is None

    def test_extract_street_name(self):
        name = _extract_street_name("rue de bourg 12")
        assert "bourg" in name
        assert "12" not in name


# ---------------------------------------------------------------------------
# 2. Geocode match verification
# ---------------------------------------------------------------------------


class TestGeocodeMatchVerification:
    def test_exact_match(self):
        quality = verify_geocode_match(
            "Rue de Bourg 12",
            "1003",
            "Rue de Bourg 12, 1003 Lausanne",
        )
        assert quality == "exact"

    def test_partial_match_no_number(self):
        """Street name matches but number differs."""
        quality = verify_geocode_match(
            "Rue de Bourg 12",
            "1003",
            "Rue de Bourg 14, 1003 Lausanne",
        )
        assert quality == "partial"

    def test_weak_match(self):
        """Only some words match."""
        quality = verify_geocode_match(
            "Rue de Bourg 12",
            "1003",
            "Place de Bourg 1, 2000 Neuchatel",
        )
        assert quality in ("weak", "partial")

    def test_no_match(self):
        quality = verify_geocode_match(
            "Rue de Bourg 12",
            "1003",
            "Bahnhofstrasse 1, 8001 Zurich",
        )
        assert quality == "no_match"

    def test_empty_label(self):
        quality = verify_geocode_match("Rue de Bourg 12", "1003", "")
        assert quality == "no_match"

    def test_case_insensitive(self):
        quality = verify_geocode_match(
            "RUE DE BOURG 12",
            "1003",
            "rue de bourg 12, 1003 lausanne",
        )
        assert quality == "exact"


# ---------------------------------------------------------------------------
# 3. EGID verification
# ---------------------------------------------------------------------------


class TestEGIDVerification:
    def test_verified_match(self):
        confidence = verify_egid_address(
            "Rue de Bourg 12",
            "Rue de Bourg",
            "12",
        )
        assert confidence == "verified"

    def test_probable_match(self):
        """Street matches but number differs."""
        confidence = verify_egid_address(
            "Rue de Bourg 12",
            "Rue de Bourg",
            "14",
        )
        assert confidence == "probable"

    def test_unverified_no_match(self):
        confidence = verify_egid_address(
            "Rue de Bourg 12",
            "Bahnhofstrasse",
            "1",
        )
        assert confidence == "unverified"

    def test_unverified_no_strname(self):
        confidence = verify_egid_address(
            "Rue de Bourg 12",
            None,
            None,
        )
        assert confidence == "unverified"

    def test_verified_with_no_number_in_regbl(self):
        """If regbl has no house number, still match on street."""
        confidence = verify_egid_address(
            "Rue de Bourg 12",
            "Rue de Bourg",
            None,
        )
        assert confidence == "verified"


# ---------------------------------------------------------------------------
# 4. Per-source confidence scoring
# ---------------------------------------------------------------------------


class TestSourceEntry:
    def test_source_entry_success(self):
        entry = _source_entry("ch.bag.radonkarte", status="success", confidence="high")
        assert entry["source_name"] == "ch.bag.radonkarte"
        assert entry["status"] == "success"
        assert entry["confidence"] == "high"
        assert entry["retry_count"] == 0
        assert entry["error"] is None
        assert "fetched_at" in entry

    def test_source_entry_failed(self):
        entry = _source_entry(
            "geocode",
            status="failed",
            confidence="low",
            error="timeout",
            retry_count=1,
        )
        assert entry["status"] == "failed"
        assert entry["error"] == "timeout"
        assert entry["retry_count"] == 1

    def test_source_entry_with_match_quality(self):
        entry = _source_entry(
            "geocode",
            status="success",
            confidence="high",
            match_quality="exact",
        )
        assert entry["match_quality"] == "exact"

    def test_source_entry_without_match_quality(self):
        entry = _source_entry("ch.bag.radonkarte")
        assert "match_quality" not in entry


# ---------------------------------------------------------------------------
# 5. Enrichment quality summary
# ---------------------------------------------------------------------------


class TestEnrichmentQuality:
    def test_all_success(self):
        entries = [
            _source_entry("geocode", status="success", confidence="high"),
            _source_entry("regbl", status="success", confidence="high"),
            _source_entry("ch.bag.radonkarte", status="success", confidence="high"),
        ]
        quality = compute_enrichment_quality(entries)
        assert quality["total_sources"] == 3
        assert quality["succeeded"] == 3
        assert quality["failed"] == 0
        assert quality["overall_confidence"] == "high"
        assert quality["critical_gaps"] == []

    def test_geocode_failed(self):
        entries = [
            _source_entry("geocode", status="failed", confidence="low"),
            _source_entry("regbl", status="success", confidence="high"),
        ]
        quality = compute_enrichment_quality(entries)
        assert "Geocode failed" in quality["critical_gaps"][0]
        assert quality["overall_confidence"] == "low"

    def test_regbl_failed(self):
        entries = [
            _source_entry("geocode", status="success", confidence="high"),
            _source_entry("regbl", status="failed", confidence="low"),
        ]
        quality = compute_enrichment_quality(entries)
        assert any("RegBL" in g for g in quality["critical_gaps"])
        assert quality["overall_confidence"] == "low"

    def test_weak_geocode_warning(self):
        entries = [
            _source_entry("geocode", status="success", confidence="low"),
            _source_entry("regbl", status="success", confidence="high"),
        ]
        quality = compute_enrichment_quality(entries, geocode_quality="weak")
        assert any("weak" in w for w in quality["warnings"])

    def test_unverified_egid_warning(self):
        entries = [
            _source_entry("geocode", status="success", confidence="high"),
            _source_entry("regbl", status="success", confidence="high"),
        ]
        quality = compute_enrichment_quality(entries, egid_confidence="unverified")
        assert any("not verified" in w for w in quality["warnings"])

    def test_mixed_statuses(self):
        entries = [
            _source_entry("geocode", status="success", confidence="high"),
            _source_entry("regbl", status="success", confidence="high"),
            _source_entry("ch.bag.radonkarte", status="failed", confidence="low"),
            _source_entry("ch.bafu.laerm", status="unavailable", confidence="low"),
            _source_entry("overpass/amenities", status="timeout", confidence="low"),
            _source_entry("ch.bfe.solar", status="skipped", confidence="low"),
        ]
        quality = compute_enrichment_quality(entries)
        assert quality["total_sources"] == 6
        assert quality["succeeded"] == 2
        assert quality["failed"] == 1
        assert quality["unavailable"] == 1
        assert quality["timeout"] == 1
        assert quality["skipped"] == 1

    def test_no_egid_gap(self):
        entries = [
            _source_entry("geocode", status="success", confidence="high"),
            _source_entry("regbl", status="skipped", confidence="low"),
        ]
        quality = compute_enrichment_quality(entries)
        assert any("EGID" in g for g in quality["critical_gaps"])


# ---------------------------------------------------------------------------
# 6. Retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retry_on_500(self):
        """Should retry once on HTTP 500."""
        mock_response_500 = MagicMock(spec=httpx.Response)
        mock_response_500.status_code = 500
        mock_response_200 = MagicMock(spec=httpx.Response)
        mock_response_200.status_code = 200

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=[mock_response_500, mock_response_200])

        resp, retry_count = await _retry_request(client, "GET", "http://test.com")
        assert resp.status_code == 200
        assert retry_count == 1
        assert client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_504(self):
        """Should retry once on HTTP 504 (gateway timeout)."""
        mock_504 = MagicMock(spec=httpx.Response)
        mock_504.status_code = 504
        mock_200 = MagicMock(spec=httpx.Response)
        mock_200.status_code = 200

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=[mock_504, mock_200])

        resp, retry_count = await _retry_request(client, "GET", "http://test.com")
        assert resp.status_code == 200
        assert retry_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_400(self):
        """Should NOT retry on HTTP 400."""
        mock_400 = MagicMock(spec=httpx.Response)
        mock_400.status_code = 400

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=mock_400)

        resp, retry_count = await _retry_request(client, "GET", "http://test.com")
        assert resp.status_code == 400
        assert retry_count == 0
        assert client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_404(self):
        """Should NOT retry on HTTP 404."""
        mock_404 = MagicMock(spec=httpx.Response)
        mock_404.status_code = 404

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=mock_404)

        resp, retry_count = await _retry_request(client, "GET", "http://test.com")
        assert resp.status_code == 404
        assert retry_count == 0

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self):
        """Should retry once on connection error."""
        mock_200 = MagicMock(spec=httpx.Response)
        mock_200.status_code = 200

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=[httpx.ConnectError("refused"), mock_200])

        resp, retry_count = await _retry_request(client, "GET", "http://test.com")
        assert resp.status_code == 200
        assert retry_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_200(self):
        """Should not retry on success."""
        mock_200 = MagicMock(spec=httpx.Response)
        mock_200.status_code = 200

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=mock_200)

        resp, retry_count = await _retry_request(client, "GET", "http://test.com")
        assert resp.status_code == 200
        assert retry_count == 0
        assert client.get.call_count == 1


# ---------------------------------------------------------------------------
# 7. _geo_identify improvements
# ---------------------------------------------------------------------------


class TestGeoIdentify:
    @pytest.mark.asyncio
    async def test_marks_400_as_unsupported(self):
        """400 response should mark layer as unsupported."""
        _UNSUPPORTED_LAYERS.discard("ch.test.bad_layer")

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 400

        with (
            patch("app.services.building_enrichment_service._throttle", new_callable=AsyncMock),
            patch("httpx.AsyncClient") as mock_client_cls,
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_resp)
            result = await _geo_identify(46.5, 6.6, "ch.test.bad_layer")

        assert result.get("_source_entry", {}).get("status") == "unavailable"
        assert "ch.test.bad_layer" in _UNSUPPORTED_LAYERS

        # Cleanup
        _UNSUPPORTED_LAYERS.discard("ch.test.bad_layer")

    @pytest.mark.asyncio
    async def test_skips_known_unsupported(self):
        """Known unsupported layers should be skipped without HTTP call."""
        _UNSUPPORTED_LAYERS.add("ch.test.known_bad")

        result = await _geo_identify(46.5, 6.6, "ch.test.known_bad")
        assert result.get("_source_entry", {}).get("status") == "unavailable"

        # Cleanup
        _UNSUPPORTED_LAYERS.discard("ch.test.known_bad")

    @pytest.mark.asyncio
    async def test_empty_results_is_success(self):
        """200 with empty results is a valid response (no data at location)."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={"results": []})

        with (
            patch("app.services.building_enrichment_service._throttle", new_callable=AsyncMock),
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client
            result = await _geo_identify(46.5, 6.6, "ch.bag.radonkarte")

        assert result.get("_source_entry", {}).get("status") == "success"


# ---------------------------------------------------------------------------
# 8. Geocode integration with match quality
# ---------------------------------------------------------------------------


class TestGeocodeWithMatchQuality:
    @pytest.mark.asyncio
    async def test_geocode_returns_match_quality(self):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(
            return_value={
                "results": [
                    {
                        "attrs": {
                            "lat": 46.5197,
                            "lon": 6.6323,
                            "featureId": "12345_0",
                            "label": "Rue de Bourg 12, 1003 Lausanne",
                            "detail": "lausanne",
                        },
                    }
                ],
            }
        )

        with (
            patch("app.services.building_enrichment_service._throttle", new_callable=AsyncMock),
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client
            result = await geocode_address("Rue de Bourg 12", "1003")

        assert result.get("match_quality") == "exact"
        assert result.get("_source_entry", {}).get("status") == "success"
        assert result.get("_source_entry", {}).get("confidence") == "high"

    @pytest.mark.asyncio
    async def test_geocode_no_results(self):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={"results": []})

        with (
            patch("app.services.building_enrichment_service._throttle", new_callable=AsyncMock),
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client
            result = await geocode_address("Nowhere Street 999", "0000")

        assert result.get("_source_entry", {}).get("status") == "failed"


# ---------------------------------------------------------------------------
# 9. RegBL with EGID verification
# ---------------------------------------------------------------------------


class TestRegBLWithVerification:
    @pytest.mark.asyncio
    async def test_regbl_returns_egid_confidence(self):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(
            return_value={
                "feature": {
                    "attributes": {
                        "gbauj": 1965,
                        "gastw": 4,
                        "strname": "Rue de Bourg",
                        "deinr": "12",
                    },
                },
            }
        )

        with (
            patch("app.services.building_enrichment_service._throttle", new_callable=AsyncMock),
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client
            result = await fetch_regbl_data(12345, "Rue de Bourg 12")

        assert result.get("egid_confidence") == "verified"
        assert result.get("construction_year") == 1965

    @pytest.mark.asyncio
    async def test_regbl_unverified_mismatch(self):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(
            return_value={
                "feature": {
                    "attributes": {
                        "gbauj": 1965,
                        "strname": "Bahnhofstrasse",
                        "deinr": "1",
                    },
                },
            }
        )

        with (
            patch("app.services.building_enrichment_service._throttle", new_callable=AsyncMock),
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client
            result = await fetch_regbl_data(12345, "Rue de Bourg 12")

        assert result.get("egid_confidence") == "unverified"

    @pytest.mark.asyncio
    async def test_regbl_404(self):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 404

        with (
            patch("app.services.building_enrichment_service._throttle", new_callable=AsyncMock),
            patch(
                "app.services.building_enrichment_service._retry_request",
                new_callable=AsyncMock,
                return_value=(mock_resp, 0),
            ),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client
            result = await fetch_regbl_data(99999, "Test")

        assert result.get("_source_entry", {}).get("status") == "failed"
        assert "404" in result.get("_source_entry", {}).get("error", "")


# ---------------------------------------------------------------------------
# 10. Supported layers set
# ---------------------------------------------------------------------------


class TestSupportedLayers:
    def test_supported_layers_not_empty(self):
        assert len(SUPPORTED_IDENTIFY_LAYERS) > 10

    def test_key_layers_in_supported(self):
        assert "ch.bfs.gebaeude_wohnungs_register" in SUPPORTED_IDENTIFY_LAYERS
        assert "ch.bag.radonkarte" in SUPPORTED_IDENTIFY_LAYERS
        assert "ch.bafu.erdbeben-erdbebenzonen" in SUPPORTED_IDENTIFY_LAYERS
