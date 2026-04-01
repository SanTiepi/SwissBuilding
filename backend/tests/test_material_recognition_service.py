"""Tests for Material Recognition Service — Claude Vision API wrapper.

Tests cover:
- JSON parsing and validation
- Confidence score clamping
- Pollutant probability normalization
- High risk detection
- Dominant pollutant extraction
- File size and MIME type validation
- API error handling
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.material_recognition_service import (
    MAX_FILE_SIZE,
    MaterialRecognitionError,
    _validate_result,
    get_dominant_pollutant,
    has_high_risk_pollutant,
    recognize_material,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_CLAUDE_RESPONSE = {
    "material_type": "vinyl",
    "material_name": "Revêtement vinyle ancien",
    "estimated_year_range": "1970-1980",
    "identified_materials": ["vinyle", "colle bitumineuse"],
    "likely_pollutants": {
        "asbestos": {"probability": 0.75, "reason": "Vinyle pré-1980 contient fréquemment de l'amiante"},
        "pcb": {"probability": 0.2, "reason": "Faible probabilité pour ce type"},
        "lead": {"probability": 0.05, "reason": "Pas typique pour du vinyle"},
        "hap": {"probability": 0.0, "reason": "Non applicable"},
        "radon": {"probability": 0.0, "reason": "Non applicable"},
        "pfas": {"probability": 0.0, "reason": "Non applicable"},
    },
    "confidence_overall": 0.82,
    "recommendations": ["Recommande test laboratoire amiante avant travaux"],
    "description": "Revêtement de sol en vinyle typique des années 1970",
}

DUMMY_IMAGE = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # Fake JPEG header


def _build_httpx_response(body: dict, status: int = 200):
    """Build a mock httpx response."""

    class MockResponse:
        status_code = status

        def json(self):
            return {"content": [{"text": json.dumps(body)}]}

        @property
        def text(self):
            return json.dumps(body)

        def raise_for_status(self):
            if self.status_code >= 400:
                import httpx

                raise httpx.HTTPStatusError(
                    f"{self.status_code}",
                    request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
                    response=self,
                )

    return MockResponse()


# ---------------------------------------------------------------------------
# _validate_result
# ---------------------------------------------------------------------------


class TestValidateResult:
    def test_valid_result_passes(self):
        result = _validate_result(dict(MOCK_CLAUDE_RESPONSE))
        assert result["confidence_overall"] == 0.82
        assert result["material_type"] == "vinyl"

    def test_clamps_confidence_above_1(self):
        data = {"confidence_overall": 1.5, "likely_pollutants": {}}
        result = _validate_result(data)
        assert result["confidence_overall"] == 1.0

    def test_clamps_confidence_below_0(self):
        data = {"confidence_overall": -0.5, "likely_pollutants": {}}
        result = _validate_result(data)
        assert result["confidence_overall"] == 0.0

    def test_non_numeric_confidence_becomes_0(self):
        data = {"confidence_overall": "high", "likely_pollutants": {}}
        result = _validate_result(data)
        assert result["confidence_overall"] == 0.0

    def test_clamps_pollutant_probability(self):
        data = {
            "confidence_overall": 0.5,
            "likely_pollutants": {
                "asbestos": {"probability": 1.5, "reason": "test"},
            },
        }
        result = _validate_result(data)
        assert result["likely_pollutants"]["asbestos"]["probability"] == 1.0

    def test_missing_material_type_defaults_to_autre(self):
        data = {"confidence_overall": 0.5, "likely_pollutants": {}}
        result = _validate_result(data)
        assert result["material_type"] == "autre"

    def test_missing_recommendations_defaults_to_empty(self):
        data = {"confidence_overall": 0.5, "likely_pollutants": {}}
        result = _validate_result(data)
        assert result["recommendations"] == []

    def test_missing_description_defaults_to_empty(self):
        data = {"confidence_overall": 0.5, "likely_pollutants": {}}
        result = _validate_result(data)
        assert result["description"] == ""


# ---------------------------------------------------------------------------
# has_high_risk_pollutant
# ---------------------------------------------------------------------------


class TestHighRiskPollutant:
    def test_detects_high_risk(self):
        assert has_high_risk_pollutant(MOCK_CLAUDE_RESPONSE) is True

    def test_no_high_risk_when_all_below_threshold(self):
        result = {
            "likely_pollutants": {
                "asbestos": {"probability": 0.3},
                "pcb": {"probability": 0.1},
            }
        }
        assert has_high_risk_pollutant(result) is False

    def test_custom_threshold(self):
        result = {
            "likely_pollutants": {
                "asbestos": {"probability": 0.3},
            }
        }
        assert has_high_risk_pollutant(result, threshold=0.2) is True
        assert has_high_risk_pollutant(result, threshold=0.5) is False

    def test_empty_pollutants(self):
        assert has_high_risk_pollutant({"likely_pollutants": {}}) is False

    def test_missing_pollutants_key(self):
        assert has_high_risk_pollutant({}) is False


# ---------------------------------------------------------------------------
# get_dominant_pollutant
# ---------------------------------------------------------------------------


class TestDominantPollutant:
    def test_returns_highest(self):
        assert get_dominant_pollutant(MOCK_CLAUDE_RESPONSE) == "asbestos"

    def test_returns_none_for_empty(self):
        assert get_dominant_pollutant({"likely_pollutants": {}}) is None

    def test_returns_none_when_all_zero(self):
        result = {
            "likely_pollutants": {
                "asbestos": {"probability": 0},
                "pcb": {"probability": 0},
            }
        }
        assert get_dominant_pollutant(result) is None


# ---------------------------------------------------------------------------
# recognize_material — integration (mocked HTTP)
# ---------------------------------------------------------------------------


class TestRecognizeMaterial:
    @pytest.mark.asyncio
    async def test_file_too_large_raises(self):
        big_data = b"\x00" * (MAX_FILE_SIZE + 1)
        with pytest.raises(MaterialRecognitionError, match="File too large"):
            await recognize_material(big_data, "image/jpeg")

    @pytest.mark.asyncio
    async def test_unsupported_mime_raises(self):
        with pytest.raises(MaterialRecognitionError, match="Unsupported image type"):
            await recognize_material(DUMMY_IMAGE, "application/pdf")

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            with pytest.raises(MaterialRecognitionError, match="ANTHROPIC_API_KEY not configured"):
                await recognize_material(DUMMY_IMAGE, "image/jpeg")

    @pytest.mark.asyncio
    async def test_successful_recognition(self):
        mock_resp = _build_httpx_response(MOCK_CLAUDE_RESPONSE)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            with patch("app.services.material_recognition_service.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_resp
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                result = await recognize_material(DUMMY_IMAGE, "image/jpeg")

                assert result["material_type"] == "vinyl"
                assert result["confidence_overall"] == 0.82
                assert result["likely_pollutants"]["asbestos"]["probability"] == 0.75
                assert len(result["recommendations"]) == 1

    @pytest.mark.asyncio
    async def test_invalid_json_from_api_raises(self):
        class BadResponse:
            status_code = 200

            def json(self):
                return {"content": [{"text": "not valid json at all"}]}

            def raise_for_status(self):
                pass

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            with patch("app.services.material_recognition_service.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.return_value = BadResponse()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                with pytest.raises(MaterialRecognitionError, match="Invalid JSON"):
                    await recognize_material(DUMMY_IMAGE, "image/jpeg")

    @pytest.mark.asyncio
    async def test_api_http_error_raises(self):
        mock_resp = _build_httpx_response({}, status=500)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            with patch("app.services.material_recognition_service.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_resp
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                with pytest.raises(MaterialRecognitionError, match="Claude API error"):
                    await recognize_material(DUMMY_IMAGE, "image/jpeg")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_pollutant_with_non_dict_value_ignored(self):
        result = {
            "likely_pollutants": {
                "asbestos": "invalid",
            }
        }
        assert has_high_risk_pollutant(result) is False
        assert get_dominant_pollutant(result) is None

    def test_validate_result_with_empty_dict(self):
        result = _validate_result({})
        assert result["material_type"] == "autre"
        assert result["confidence_overall"] == 0.0
        assert result["recommendations"] == []

    def test_all_six_pollutants_present(self):
        result = _validate_result(dict(MOCK_CLAUDE_RESPONSE))
        pollutants = result["likely_pollutants"]
        assert "asbestos" in pollutants
        assert "pcb" in pollutants
        assert "lead" in pollutants
        assert "hap" in pollutants
        assert "radon" in pollutants
        assert "pfas" in pollutants
