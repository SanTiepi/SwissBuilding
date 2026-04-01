"""
BatiConnect - Electricity Tariff Service

Swiss electricity tariffs by commune (simplified from ElCom data).
Provides tariff lookup and comparison to national average.
"""

from __future__ import annotations

# Source: elcom.admin.ch - simplified 2025 reference tariffs (CHF/kWh)
# These are H4 household tariffs (5-room apartment, 4500 kWh/year)
ELECTRICITY_TARIFFS_2025: dict[str, float] = {
    "Lausanne": 0.2450,
    "Pully": 0.2380,
    "Montreux": 0.2520,
    "Vevey": 0.2490,
    "Nyon": 0.2400,
    "Morges": 0.2380,
    "Yverdon-les-Bains": 0.2560,
    "Genève": 0.2280,
    "Carouge": 0.2310,
    "Lancy": 0.2300,
    "Bern": 0.2580,
    "Zürich": 0.2720,
    "Basel": 0.2890,
    "Sion": 0.2150,
    "Fribourg": 0.2340,
}

# Swiss national average electricity tariff 2025 (H4 profile)
NATIONAL_AVERAGE_2025 = 0.2732  # CHF/kWh

# Average annual consumption per m2 for Swiss residential buildings
_KWH_PER_M2_YEAR = 40  # kWh/m2/year (heating + common areas)


async def get_electricity_tariff(commune_name: str) -> dict:
    """Return tariff + comparison to national average.

    Returns:
        {
            commune: str,
            tariff_chf_kwh: float,
            national_average: float,
            comparison: "below_average" | "at_average" | "above_average",
            difference_pct: float,
            annual_cost_estimate_for_m2: {
                50: X, 100: Y, 200: Z, 500: W,
            },
        }
    """
    tariff = ELECTRICITY_TARIFFS_2025.get(commune_name, ELECTRICITY_TARIFFS_2025.get("_default", NATIONAL_AVERAGE_2025))

    diff_pct = round((tariff - NATIONAL_AVERAGE_2025) / NATIONAL_AVERAGE_2025 * 100, 1)

    tolerance_pct = 2.0
    if diff_pct < -tolerance_pct:
        comparison = "below_average"
    elif diff_pct > tolerance_pct:
        comparison = "above_average"
    else:
        comparison = "at_average"

    # Annual cost estimates for different building sizes
    annual_costs = {}
    for m2 in [50, 100, 200, 500]:
        annual_kwh = m2 * _KWH_PER_M2_YEAR
        annual_costs[m2] = round(annual_kwh * tariff, 2)

    return {
        "commune": commune_name,
        "tariff_chf_kwh": tariff,
        "national_average": NATIONAL_AVERAGE_2025,
        "comparison": comparison,
        "difference_pct": diff_pct,
        "annual_cost_estimate_for_m2": annual_costs,
    }


async def compare_tariffs(commune_names: list[str]) -> dict:
    """Compare electricity tariffs across multiple communes.

    Returns:
        {
            communes: [{commune, tariff_chf_kwh, rank}],
            cheapest: str,
            most_expensive: str,
            spread_chf_kwh: float,
        }
    """
    entries = []
    for name in commune_names:
        tariff = ELECTRICITY_TARIFFS_2025.get(name, NATIONAL_AVERAGE_2025)
        entries.append({"commune": name, "tariff_chf_kwh": tariff})

    entries.sort(key=lambda e: e["tariff_chf_kwh"])
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1

    return {
        "communes": entries,
        "cheapest": entries[0]["commune"] if entries else None,
        "most_expensive": entries[-1]["commune"] if entries else None,
        "spread_chf_kwh": round(entries[-1]["tariff_chf_kwh"] - entries[0]["tariff_chf_kwh"], 4) if entries else 0,
    }
