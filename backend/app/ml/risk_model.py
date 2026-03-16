"""
SwissBuildingOS - Risk Prediction Model

Simple prediction model that combines construction year probabilities
with canton and building type modifiers to predict pollutant presence.
"""

from __future__ import annotations

from app.services.risk_engine import (
    BUILDING_TYPE_MODIFIERS,
    calculate_asbestos_base_probability,
    calculate_hap_base_probability,
    calculate_lead_base_probability,
    calculate_pcb_base_probability,
    calculate_radon_base_probability,
)


def predict_pollutant_presence(
    construction_year: int | None,
    canton: str,
    building_type: str,
    renovation_year: int | None,
) -> dict[str, float]:
    """
    Predict probability of each pollutant being present in a building.

    Combines:
      1. Construction year base probabilities
      2. Canton-based radon risk
      3. Building type modifiers
      4. Renovation year adjustment (prior renovation may have removed some pollutants)

    Returns a dict mapping pollutant names to probabilities (0.0 - 1.0).
    """
    building_type_lower = (building_type or "residential").lower()

    # Step 1: base probabilities from construction year
    asbestos = calculate_asbestos_base_probability(construction_year)
    pcb = calculate_pcb_base_probability(construction_year)
    lead = calculate_lead_base_probability(construction_year)
    hap = calculate_hap_base_probability(construction_year)
    radon = calculate_radon_base_probability(canton or "")

    # Step 2: apply building type modifiers
    for pollutant_name, base_val in [
        ("asbestos", asbestos),
        ("pcb", pcb),
        ("lead", lead),
        ("hap", hap),
    ]:
        modifier = BUILDING_TYPE_MODIFIERS.get(pollutant_name, {}).get(building_type_lower, 1.0)
        adjusted = base_val * modifier
        if pollutant_name == "asbestos":
            asbestos = adjusted
        elif pollutant_name == "pcb":
            pcb = adjusted
        elif pollutant_name == "lead":
            lead = adjusted
        elif pollutant_name == "hap":
            hap = adjusted

    # Step 3: renovation year adjustment
    # If the building was renovated after the ban year for a pollutant,
    # there's a chance the pollutant was partially removed.
    if renovation_year is not None:
        # Asbestos ban in Switzerland: 1990
        if renovation_year >= 1990:
            # The later the renovation, the more likely asbestos was addressed
            years_since_ban = renovation_year - 1990
            reduction = min(0.5, years_since_ban * 0.02)
            asbestos = max(0.02, asbestos * (1.0 - reduction))

        # PCB ban: 1986
        if renovation_year >= 1986:
            years_since_ban = renovation_year - 1986
            reduction = min(0.5, years_since_ban * 0.02)
            pcb = max(0.02, pcb * (1.0 - reduction))

        # Lead paint restrictions tightened over time
        if renovation_year >= 1980:
            years_since = renovation_year - 1980
            reduction = min(0.4, years_since * 0.015)
            lead = max(0.02, lead * (1.0 - reduction))

        # HAP awareness increased from ~1985
        if renovation_year >= 1985:
            years_since = renovation_year - 1985
            reduction = min(0.3, years_since * 0.01)
            hap = max(0.02, hap * (1.0 - reduction))

    # Clamp all values to [0.0, 1.0]
    return {
        "asbestos": round(min(1.0, max(0.0, asbestos)), 4),
        "pcb": round(min(1.0, max(0.0, pcb)), 4),
        "lead": round(min(1.0, max(0.0, lead)), 4),
        "hap": round(min(1.0, max(0.0, hap)), 4),
        "radon": round(min(1.0, max(0.0, radon)), 4),
    }
