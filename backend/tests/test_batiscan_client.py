"""Tests for BatiscanClient adapter (stub + factory)."""

from unittest.mock import patch

import pytest

from app.services.batiscan_client import (
    BatiscanClientBase,
    HttpBatiscanClient,
    StubBatiscanClient,
    get_batiscan_client,
)

# ── StubBatiscanClient ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stub_send_mission_order_returns_expected_structure():
    client = StubBatiscanClient()
    result = await client.send_mission_order({"building_id": "123"})
    assert result["status"] == "acknowledged"
    assert result["external_mission_id"].startswith("BAT-")
    assert len(result["external_mission_id"]) == 12  # BAT- + 8 hex chars
    assert "stub mode" in result["message"]


@pytest.mark.asyncio
async def test_stub_send_mission_order_generates_unique_ids():
    client = StubBatiscanClient()
    r1 = await client.send_mission_order({})
    r2 = await client.send_mission_order({})
    assert r1["external_mission_id"] != r2["external_mission_id"]


@pytest.mark.asyncio
async def test_stub_check_mission_status_returns_expected_structure():
    client = StubBatiscanClient()
    result = await client.check_mission_status("BAT-ABCD1234")
    assert result["external_mission_id"] == "BAT-ABCD1234"
    assert result["status"] == "in_progress"
    assert "stub mode" in result["message"]


# ── Factory ──────────────────────────────────────────────────────────


def test_factory_returns_stub_when_no_url():
    """When BATISCAN_API_URL is not set, factory returns StubBatiscanClient."""
    client = get_batiscan_client()
    assert isinstance(client, StubBatiscanClient)
    assert isinstance(client, BatiscanClientBase)


def test_factory_returns_http_when_url_configured():
    """When BATISCAN_API_URL is set, factory returns HttpBatiscanClient."""
    mock_settings = type(
        "MockSettings",
        (),
        {"BATISCAN_API_URL": "https://batiscan.example.com", "BATISCAN_API_KEY": "test-key-123"},
    )()
    with patch("app.config.settings", mock_settings):
        client = get_batiscan_client()
    assert isinstance(client, HttpBatiscanClient)
    assert isinstance(client, BatiscanClientBase)
    assert client.base_url == "https://batiscan.example.com"
    assert client.api_key == "test-key-123"


def test_factory_returns_http_without_api_key():
    """HttpBatiscanClient works without an API key."""
    mock_settings = type(
        "MockSettings",
        (),
        {"BATISCAN_API_URL": "https://batiscan.example.com", "BATISCAN_API_KEY": None},
    )()
    with patch("app.config.settings", mock_settings):
        client = get_batiscan_client()
    assert isinstance(client, HttpBatiscanClient)
    assert client.api_key is None


# ── HttpBatiscanClient init ──────────────────────────────────────────


def test_http_client_strips_trailing_slash():
    client = HttpBatiscanClient("https://batiscan.example.com/", "key")
    assert client.base_url == "https://batiscan.example.com"


def test_http_client_stores_api_key():
    client = HttpBatiscanClient("https://batiscan.example.com", "my-secret")
    assert client.api_key == "my-secret"
