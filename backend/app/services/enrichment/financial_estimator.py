"""Financial impact estimator (pure computation)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def estimate_financial_impact(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Estimate the financial impact of the current building state.

    Pure function -- no API calls.
    All figures are rough estimates for planning purposes only.
    """
    surface = building_data.get("surface_area_m2") or 200
    year = building_data.get("construction_year")
    heating = str(building_data.get("heating_type", "") or "").lower()
    current_year = datetime.now(UTC).year
    age = (current_year - year) if year else 30  # default assumption

    renovation_plan = enrichment_data.get("renovation_plan", {})
    total_reno_cost = renovation_plan.get("total_net_chf", 0)

    oil_gas = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas")
    has_fossil = any(ind in heating for ind in oil_gas)

    # --- Cost of inaction per year ---
    # Energy waste: older buildings waste more
    energy_waste = 0.0
    if year and year < 1980:
        energy_waste = surface * 25  # CHF 25/m2/year excess energy cost
    elif year and year < 2000:
        energy_waste = surface * 15
    elif year and year < 2010:
        energy_waste = surface * 5

    # Maintenance overspend on aging systems
    maintenance_excess = 0.0
    lifecycle = enrichment_data.get("component_lifecycle", {})
    overdue_count = sum(1 for c in lifecycle.get("components", []) if c.get("status") == "overdue")
    maintenance_excess = overdue_count * 500  # CHF 500/year per overdue component

    # Depreciation acceleration
    depreciation = 0.0
    if age > 40:
        depreciation = surface * 10
    elif age > 25:
        depreciation = surface * 5

    cost_of_inaction = round(energy_waste + maintenance_excess + depreciation)

    # --- Renovation ROI ---
    energy_savings = 0.0
    if has_fossil and year and year < 2000:
        energy_savings = surface * 20  # CHF 20/m2/year with full renovation
    elif year and year < 2000:
        energy_savings = surface * 10
    elif year and year < 2010:
        energy_savings = surface * 5

    roi_years = round(total_reno_cost / energy_savings, 1) if energy_savings > 0 and total_reno_cost > 0 else 0.0

    # --- Property value impact ---
    value_increase_pct = 0.0
    if age > 40:
        value_increase_pct = 15.0
    elif age > 25:
        value_increase_pct = 10.0
    elif age > 15:
        value_increase_pct = 5.0

    # --- Insurance premium impact ---
    insurance_impact = 0.0
    if overdue_count > 5:
        insurance_impact = -1500  # premium reduction after renovation
    elif overdue_count > 2:
        insurance_impact = -800

    # --- CO2 reduction ---
    co2_reduction = 0.0
    if has_fossil:
        co2_reduction = round(surface * 0.025, 1)  # ~25 kg CO2/m2/year for fossil -> renewable

    summary_parts: list[str] = []
    if cost_of_inaction > 0:
        summary_parts.append(f"Cout de l'inaction estime: CHF {cost_of_inaction:,.0f}/an")
    if energy_savings > 0:
        summary_parts.append(f"economies d'energie estimees: CHF {energy_savings:,.0f}/an")
    if roi_years > 0:
        summary_parts.append(f"retour sur investissement estime: {roi_years} ans")
    if co2_reduction > 0:
        summary_parts.append(f"reduction CO2 estimee: {co2_reduction} t/an")
    summary_fr = ". ".join(summary_parts) + "." if summary_parts else "Estimation financiere non disponible."

    return {
        "cost_of_inaction_chf_per_year": cost_of_inaction,
        "renovation_roi_years": roi_years,
        "value_increase_pct": value_increase_pct,
        "energy_savings_chf": round(energy_savings),
        "insurance_impact_chf": round(insurance_impact),
        "co2_reduction_tons": co2_reduction,
        "summary_fr": summary_fr,
    }
