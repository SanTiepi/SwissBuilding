"""Tests for electricity tariff service."""

import pytest

from app.services.electricity_tariff_service import (
    NATIONAL_AVERAGE_2025,
    compare_tariffs,
    get_electricity_tariff,
)

# ---------------------------------------------------------------------------
# get_electricity_tariff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_known_commune_tariff():
    """Known commune returns its specific tariff."""
    result = await get_electricity_tariff("Lausanne")
    assert result["commune"] == "Lausanne"
    assert result["tariff_chf_kwh"] == 0.2450
    assert result["national_average"] == NATIONAL_AVERAGE_2025


@pytest.mark.asyncio
async def test_unknown_commune_falls_to_national_average():
    """Unknown commune falls back to national average."""
    result = await get_electricity_tariff("UnknownVillage")
    assert result["tariff_chf_kwh"] == NATIONAL_AVERAGE_2025
    assert result["commune"] == "UnknownVillage"


@pytest.mark.asyncio
async def test_tariff_comparison_below_average():
    """Commune with tariff below national average is flagged correctly."""
    result = await get_electricity_tariff("Sion")
    assert result["tariff_chf_kwh"] == 0.2150
    assert result["comparison"] == "below_average"
    assert result["difference_pct"] < 0


@pytest.mark.asyncio
async def test_tariff_annual_cost_estimates():
    """Annual cost estimates computed for different building sizes."""
    result = await get_electricity_tariff("Lausanne")
    costs = result["annual_cost_estimate_for_m2"]
    assert 50 in costs
    assert 100 in costs
    assert 200 in costs
    assert 500 in costs
    # 100m2 * 40 kWh/m2 * 0.2450 = 980.0
    assert costs[100] == pytest.approx(980.0, abs=0.01)


# ---------------------------------------------------------------------------
# compare_tariffs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_tariffs_ranking():
    """Compare tariffs ranks communes from cheapest to most expensive."""
    result = await compare_tariffs(["Lausanne", "Basel", "Sion"])
    assert result["cheapest"] == "Sion"
    assert result["most_expensive"] == "Basel"
    assert result["spread_chf_kwh"] > 0
    # Verify ranking
    communes = result["communes"]
    assert len(communes) == 3
    assert communes[0]["rank"] == 1
    assert communes[0]["commune"] == "Sion"


@pytest.mark.asyncio
async def test_compare_tariffs_empty_list():
    """Empty commune list returns empty result."""
    result = await compare_tariffs([])
    assert result["cheapest"] is None
    assert result["most_expensive"] is None
    assert result["spread_chf_kwh"] == 0
