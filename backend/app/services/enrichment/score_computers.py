"""Pure-computation score and prediction functions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def compute_connectivity_score(enrichment_data: dict[str, Any]) -> float:
    """Compute connectivity score (0-10) from 5G, broadband, EV, district heating.

    Pure function -- no API calls.
    """
    score = 0.0
    count = 0

    # 5G coverage: 2.5 points
    mobile = enrichment_data.get("mobile_coverage", {})
    if mobile.get("has_5g_coverage"):
        score += 2.5
    count += 1

    # Broadband speed: 0-2.5 points
    broadband = enrichment_data.get("broadband", {})
    speed = broadband.get("max_speed_mbps")
    if speed is not None:
        if speed >= 1000:
            score += 2.5
        elif speed >= 100:
            score += 1.5
        elif speed >= 10:
            score += 0.5
    count += 1

    # EV charging nearby: 2.5 points
    ev = enrichment_data.get("ev_charging", {})
    if ev.get("ev_stations_nearby", 0) > 0:
        score += 2.5
    count += 1

    # District heating: 2.5 points
    thermal = enrichment_data.get("thermal_networks", {})
    if thermal.get("has_district_heating"):
        score += 2.5
    count += 1

    return round(score, 1)


def compute_environmental_risk_score(enrichment_data: dict[str, Any]) -> float:
    """Compute environmental risk score (0-10, 10=safest).

    Combines flood, seismic, contamination, radon, noise (road+rail+air).
    Pure function -- no API calls.
    """
    penalties = 0.0

    # Flood risk: 0-2 penalty
    flood = enrichment_data.get("flood_zones", {})
    flood_level = str(flood.get("flood_danger_level", "")).lower()
    if "hoch" in flood_level or "erheblich" in flood_level or "high" in flood_level:
        penalties += 2.0
    elif "mittel" in flood_level or "medium" in flood_level:
        penalties += 1.0
    elif flood_level and "gering" not in flood_level and "low" not in flood_level:
        penalties += 0.5

    # Seismic: 0-2 penalty
    seismic = enrichment_data.get("seismic", {})
    zone = str(seismic.get("seismic_zone", "")).lower()
    if zone in ("3b", "3a"):
        penalties += 2.0
    elif zone == "2":
        penalties += 1.0
    elif zone == "1":
        penalties += 0.3

    # Contaminated site: 0-2 penalty
    contam = enrichment_data.get("contaminated_sites", {})
    if contam.get("is_contaminated"):
        penalties += 2.0

    # Radon: 0-2 penalty
    radon = enrichment_data.get("radon", {})
    radon_level = radon.get("radon_level", "low")
    if radon_level == "high":
        penalties += 2.0
    elif radon_level == "medium":
        penalties += 1.0

    # Noise (combined): 0-2 penalty
    noise = enrichment_data.get("noise", {})
    road_db = noise.get("road_noise_day_db", 0) or 0
    rail = enrichment_data.get("railway_noise", {})
    rail_db = rail.get("railway_noise_day_db", 0) or 0
    aircraft = enrichment_data.get("aircraft_noise", {})
    air_db = aircraft.get("aircraft_noise_db", 0) or 0
    max_noise = max(road_db, rail_db, air_db)
    if max_noise > 65:
        penalties += 2.0
    elif max_noise > 55:
        penalties += 1.0
    elif max_noise > 45:
        penalties += 0.5

    return round(max(0.0, 10.0 - penalties), 1)


def compute_livability_score(enrichment_data: dict[str, Any]) -> float:
    """Compute livability score (0-10) from transport, amenities, noise, connectivity.

    Pure function -- no API calls.
    """
    scores: list[tuple[float, float]] = []  # (score, weight)

    # Transport quality: weight 3
    transport = enrichment_data.get("transport", {})
    tclass = transport.get("transport_quality_class", "").upper()
    _t_scores = {"A": 10.0, "B": 8.0, "C": 5.0, "D": 2.0}
    if tclass in _t_scores:
        scores.append((_t_scores[tclass], 3.0))

    # Amenities: weight 2
    amenities = enrichment_data.get("osm_amenities", {})
    total_am = amenities.get("total_amenities", 0)
    if total_am > 0:
        am_score = min(10.0, total_am / 5.0)  # 50+ amenities = 10
        scores.append((am_score, 2.0))

    # Noise (inverse): weight 2
    noise = enrichment_data.get("noise", {})
    road_db = noise.get("road_noise_day_db")
    if road_db is not None:
        if road_db < 45:
            scores.append((10.0, 2.0))
        elif road_db < 55:
            scores.append((7.0, 2.0))
        elif road_db < 65:
            scores.append((4.0, 2.0))
        else:
            scores.append((1.0, 2.0))

    # Connectivity: weight 1.5
    conn = enrichment_data.get("connectivity_score")
    if conn is not None:
        scores.append((float(conn), 1.5))

    # Nearest transport stop: weight 1.5
    stops = enrichment_data.get("nearest_stops", {})
    stop_dist = stops.get("nearest_stop_distance_m")
    if stop_dist is not None:
        if stop_dist < 200:
            scores.append((10.0, 1.5))
        elif stop_dist < 500:
            scores.append((7.0, 1.5))
        elif stop_dist < 1000:
            scores.append((4.0, 1.5))
        else:
            scores.append((2.0, 1.5))

    if not scores:
        return 5.0

    total_weight = sum(w for _, w in scores)
    weighted_sum = sum(s * w for s, w in scores)
    return round(weighted_sum / total_weight, 1)


def compute_renovation_potential(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Compute renovation potential from building characteristics + enrichment data.

    Pure function -- no API calls.
    """
    score = 0.0
    actions: list[str] = []
    savings = 0

    year = building_data.get("construction_year")
    heating = str(building_data.get("heating_type", "") or building_data.get("heating_type_code", "") or "").lower()
    solar = enrichment_data.get("solar", {})
    subsidies = enrichment_data.get("subsidies", {})

    # Fossil heating -> high potential
    oil_gas = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas", "7520", "7530", "7500", "7510")
    if any(ind in heating for ind in oil_gas):
        score += 3.0
        actions.append("Replace fossil heating with heat pump or district heating")
        savings += 3000

    # Old building envelope
    if year and year < 1990:
        score += 2.5
        actions.append("Insulate building envelope (facade, roof, basement)")
        savings += 2000
    elif year and year < 2000:
        score += 1.5
        actions.append("Evaluate envelope insulation potential")
        savings += 1000

    # Solar potential
    suitability = solar.get("suitability", "")
    if suitability == "high":
        score += 2.0
        actions.append("Install rooftop photovoltaic system")
        savings += 1500
    elif suitability == "medium":
        score += 1.0
        actions.append("Consider rooftop solar installation")
        savings += 800

    # Windows (pre-1990)
    if year and year < 1990:
        score += 1.5
        actions.append("Replace windows with triple-glazed Minergie-certified")
        savings += 800

    # Subsidy availability bonus
    subsidy_total = subsidies.get("total_estimated_chf", 0) if subsidies else 0
    if subsidy_total > 10000:
        score += 1.0
        actions.append(f"Apply for available subsidies (est. CHF {subsidy_total:,})")

    # District heating available
    thermal = enrichment_data.get("thermal_networks", {})
    if thermal.get("has_district_heating") and any(ind in heating for ind in oil_gas):
        score += 0.5
        actions.append("Connect to nearby district heating network")
        savings += 500

    score = min(10.0, score)

    return {
        "potential_score": round(score, 1),
        "recommended_actions": actions,
        "estimated_savings_chf_per_year": savings,
    }


def compute_overall_building_intelligence_score(all_data: dict[str, Any]) -> dict[str, Any]:
    """Compute overall building intelligence score (0-100, grade A-F).

    Weighted combination of all sub-scores.
    Pure function -- no API calls.
    """
    sub_scores: dict[str, float] = {}
    weights = {
        "neighborhood": 2.0,
        "environmental_risk": 2.5,
        "connectivity": 1.5,
        "livability": 2.0,
        "renovation_potential": 1.0,
        "data_completeness": 1.0,
    }

    # Neighborhood score (0-10)
    ns = all_data.get("neighborhood_score")
    if ns is not None:
        sub_scores["neighborhood"] = float(ns)

    # Environmental risk (0-10)
    er = all_data.get("environmental_risk_score")
    if er is not None:
        sub_scores["environmental_risk"] = float(er)

    # Connectivity (0-10)
    cs = all_data.get("connectivity_score")
    if cs is not None:
        sub_scores["connectivity"] = float(cs)

    # Livability (0-10)
    ls = all_data.get("livability_score")
    if ls is not None:
        sub_scores["livability"] = float(ls)

    # Renovation potential (0-10)
    rp = all_data.get("renovation_potential", {})
    if isinstance(rp, dict) and rp.get("potential_score") is not None:
        sub_scores["renovation_potential"] = float(rp["potential_score"])

    # Data completeness: how many enrichment sources returned data
    _data_keys = [
        "radon",
        "natural_hazards",
        "noise",
        "solar",
        "heritage",
        "transport",
        "seismic",
        "water_protection",
        "railway_noise",
        "aircraft_noise",
        "building_zones",
        "contaminated_sites",
        "groundwater_zones",
        "flood_zones",
        "mobile_coverage",
        "broadband",
        "ev_charging",
        "thermal_networks",
        "osm_amenities",
        "nearest_stops",
        "climate",
    ]
    filled = sum(1 for k in _data_keys if all_data.get(k))
    completeness = min(10.0, filled / len(_data_keys) * 10.0)
    sub_scores["data_completeness"] = completeness

    if not sub_scores:
        return {"score_0_100": 0, "grade": "F", "strengths": [], "weaknesses": [], "top_actions": []}

    total_weight = sum(weights.get(k, 1.0) for k in sub_scores)
    weighted_sum = sum(sub_scores[k] * weights.get(k, 1.0) for k in sub_scores)
    score_10 = weighted_sum / total_weight
    score_100 = round(score_10 * 10)

    # Grade
    if score_100 >= 85:
        grade = "A"
    elif score_100 >= 70:
        grade = "B"
    elif score_100 >= 55:
        grade = "C"
    elif score_100 >= 40:
        grade = "D"
    elif score_100 >= 25:
        grade = "E"
    else:
        grade = "F"

    # Strengths and weaknesses
    strengths: list[str] = []
    weaknesses: list[str] = []
    for k, v in sub_scores.items():
        label = k.replace("_", " ").title()
        if v >= 7.0:
            strengths.append(f"{label}: {v:.1f}/10")
        elif v < 4.0:
            weaknesses.append(f"{label}: {v:.1f}/10")

    # Top actions from renovation potential
    top_actions: list[str] = []
    if isinstance(rp, dict):
        top_actions = rp.get("recommended_actions", [])[:3]

    return {
        "score_0_100": score_100,
        "grade": grade,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "top_actions": top_actions,
    }


def compute_neighborhood_score(enrichment_data: dict[str, Any]) -> float:
    """Compute a neighborhood attractiveness score (0-10) from enriched data.

    Weighted average of transport, noise, hazards, solar, with heritage bonus.
    Pure function -- no API calls.
    """
    scores: dict[str, float] = {}
    weights: dict[str, float] = {
        "transport": 3.0,
        "noise": 2.0,
        "hazards": 2.5,
        "solar": 1.5,
    }

    # Transport quality: A=10, B=8, C=5, D=2
    transport = enrichment_data.get("transport", {})
    tclass = transport.get("transport_quality_class", "").upper() if transport else ""
    _transport_scores = {"A": 10.0, "B": 8.0, "C": 5.0, "D": 2.0}
    if tclass in _transport_scores:
        scores["transport"] = _transport_scores[tclass]

    # Noise: <45dB=10, 45-55=7, 55-65=4, >65=1
    noise = enrichment_data.get("noise", {})
    noise_db = noise.get("road_noise_day_db") if noise else None
    if noise_db is not None:
        if noise_db < 45:
            scores["noise"] = 10.0
        elif noise_db < 55:
            scores["noise"] = 7.0
        elif noise_db < 65:
            scores["noise"] = 4.0
        else:
            scores["noise"] = 1.0

    # Natural hazards: no risk=10, low=7, medium=4, high=1
    hazards = enrichment_data.get("natural_hazards", {})
    if hazards:
        risk_values = [
            hazards.get("flood_risk", "unknown"),
            hazards.get("landslide_risk", "unknown"),
            hazards.get("rockfall_risk", "unknown"),
        ]
        _risk_scores = {"unknown": 8.0, "keine": 10.0, "none": 10.0, "low": 7.0, "medium": 4.0, "high": 1.0}
        hazard_scores = []
        for rv in risk_values:
            rv_lower = str(rv).lower()
            for key, val in _risk_scores.items():
                if key in rv_lower:
                    hazard_scores.append(val)
                    break
            else:
                hazard_scores.append(8.0)  # unknown defaults to neutral
        scores["hazards"] = sum(hazard_scores) / len(hazard_scores) if hazard_scores else 8.0

    # Solar: high=10, medium=7, low=4
    solar = enrichment_data.get("solar", {})
    if solar:
        _solar_scores = {"high": 10.0, "medium": 7.0, "low": 4.0}
        suitability = solar.get("suitability", "")
        if suitability in _solar_scores:
            scores["solar"] = _solar_scores[suitability]

    if not scores:
        return 5.0  # neutral default

    total_weight = sum(weights.get(k, 1.0) for k in scores)
    weighted_sum = sum(scores[k] * weights.get(k, 1.0) for k in scores)
    base_score = weighted_sum / total_weight

    # Heritage bonus: protected = +2 (capped at 10)
    heritage = enrichment_data.get("heritage", {})
    if heritage and heritage.get("isos_protected"):
        base_score = min(10.0, base_score + 2.0)

    return round(base_score, 1)


def compute_pollutant_risk_prediction(building_data: dict[str, Any]) -> dict[str, Any]:
    """Predict pollutant probabilities based on building characteristics.

    Uses known correlations between construction era, building type,
    and pollutant presence in Swiss buildings.
    Pure function -- no API calls.
    """
    year = building_data.get("construction_year")
    btype = str(building_data.get("building_type", "")).lower()
    floors = building_data.get("floors_above") or building_data.get("floors") or 0
    canton = str(building_data.get("canton", "")).upper()
    renovation_year = building_data.get("renovation_year")
    radon_level = building_data.get("radon_level", "low")

    result: dict[str, Any] = {
        "asbestos_probability": 0.0,
        "pcb_probability": 0.0,
        "lead_probability": 0.0,
        "hap_probability": 0.0,
        "radon_probability": 0.0,
        "overall_risk_score": 0.0,
        "risk_factors": [],
    }

    if year is None:
        result["risk_factors"].append("construction_year_unknown — cannot assess age-based risk")
        result["overall_risk_score"] = 0.5
        return result

    # Asbestos: peak usage 1960-1990 in Switzerland
    if year < 1990:
        base = 0.85 if btype in ("residential", "mixed", "") else 0.70
        if 1960 <= year <= 1980:
            base = min(1.0, base + 0.10)  # peak years
        # VD historically higher
        if canton in ("VD", "GE", "VS"):
            base = min(1.0, base + 0.05)
        result["asbestos_probability"] = round(base, 2)
        result["risk_factors"].append(f"construction_year={year} (pre-1990 asbestos era)")

    # PCB: primarily 1955-1975 (joints, condensateurs, peintures)
    if 1955 <= year <= 1975:
        result["pcb_probability"] = 0.60
        result["risk_factors"].append(f"construction_year={year} (PCB peak era 1955-1975)")
    elif year < 1985:
        result["pcb_probability"] = 0.30
        result["risk_factors"].append(f"construction_year={year} (late PCB era)")

    # Lead: pre-1960 paints
    if year < 1960:
        result["lead_probability"] = 0.70
        result["risk_factors"].append(f"construction_year={year} (pre-1960 lead paint era)")
    elif year < 1980:
        result["lead_probability"] = 0.30

    # HAP: pre-1991 etancheite in taller buildings
    if year < 1991 and floors > 3:
        result["hap_probability"] = 0.40
        result["risk_factors"].append(f"construction_year={year}, floors={floors} (HAP risk in waterproofing)")
    elif year < 1991:
        result["hap_probability"] = 0.20

    # Radon: based on radon data if available
    _radon_map = {"high": 0.70, "medium": 0.40, "low": 0.10}
    result["radon_probability"] = _radon_map.get(radon_level, 0.10)
    if radon_level in ("high", "medium"):
        result["risk_factors"].append(f"radon_level={radon_level}")

    # Renovation reduces probabilities
    if renovation_year and renovation_year > 2000:
        reduction = 0.30
        result["asbestos_probability"] = round(max(0, result["asbestos_probability"] - reduction), 2)
        result["pcb_probability"] = round(max(0, result["pcb_probability"] - reduction), 2)
        result["lead_probability"] = round(max(0, result["lead_probability"] - reduction), 2)
        result["hap_probability"] = round(max(0, result["hap_probability"] - reduction), 2)
        result["risk_factors"].append(f"renovation_year={renovation_year} (probabilities reduced)")

    # Overall risk score: weighted average
    weights = {"asbestos": 3.0, "pcb": 2.0, "lead": 2.0, "hap": 1.5, "radon": 1.5}
    total = (
        result["asbestos_probability"] * weights["asbestos"]
        + result["pcb_probability"] * weights["pcb"]
        + result["lead_probability"] * weights["lead"]
        + result["hap_probability"] * weights["hap"]
        + result["radon_probability"] * weights["radon"]
    )
    result["overall_risk_score"] = round(total / sum(weights.values()), 2)

    return result


def compute_accessibility_assessment(building_data: dict[str, Any]) -> dict[str, Any]:
    """Assess accessibility compliance based on LHand (Swiss disability law).

    Pure function -- no API calls.
    """
    year = building_data.get("construction_year")
    floors = building_data.get("floors_above") or building_data.get("floors") or 0
    dwellings = building_data.get("dwellings") or 0
    renovation_year = building_data.get("renovation_year")
    has_elevator = building_data.get("has_elevator", False)

    requirements: list[str] = []
    recommendations: list[str] = []
    compliance_status = "unknown"

    post_2004 = year is not None and year >= 2004
    major_renovation = renovation_year is not None and renovation_year >= 2004

    if post_2004 and dwellings >= 8:
        compliance_status = "full_compliance_required"
        requirements.append("LHand Art. 3: buildings with 8+ dwellings built after 2004 must be fully accessible")
        requirements.append("Wheelchair-accessible entrance and common areas required")
        if floors > 1:
            requirements.append("Elevator required for multi-story accessible buildings")
    elif post_2004:
        compliance_status = "partial_compliance_required"
        requirements.append("LHand: new buildings must meet basic accessibility standards")
    elif major_renovation:
        compliance_status = "adaptation_required"
        requirements.append("LHand: major renovation triggers accessibility adaptation requirements")
        if dwellings >= 8:
            requirements.append("Adaptation to accessibility standards required for 8+ dwelling buildings")
    else:
        compliance_status = "no_legal_requirement"

    # Recommendations regardless of legal status
    if floors > 3 and not has_elevator:
        recommendations.append("Elevator recommended for buildings with more than 3 floors")
    if floors > 1 and not has_elevator:
        recommendations.append("Consider stairlift or platform lift for upper floors")
    if dwellings >= 4:
        recommendations.append("Consider accessible design for aging-in-place readiness")

    return {
        "compliance_status": compliance_status,
        "requirements": requirements,
        "recommendations": recommendations,
    }


def estimate_subsidy_eligibility(building_data: dict[str, Any]) -> dict[str, Any]:
    """Estimate subsidy eligibility based on Programme Batiments + cantonal programs.

    Pure function -- no API calls.
    """
    year = building_data.get("construction_year")
    heating_type = str(
        building_data.get("heating_type", "") or building_data.get("heating_type_code", "") or ""
    ).lower()
    canton = str(building_data.get("canton", "")).upper()
    solar_suitability = building_data.get("solar_suitability", "")
    solar_kwh = building_data.get("solar_potential_kwh")
    asbestos_positive = building_data.get("asbestos_positive", False)
    surface_area = building_data.get("surface_area_m2") or 0

    eligible_programs: list[dict[str, Any]] = []

    # 1. Heating replacement (Programme Batiments)
    oil_gas_indicators = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas", "7520", "7530", "7500", "7510")
    if any(ind in heating_type for ind in oil_gas_indicators):
        amount = 10_000 if surface_area < 200 else 15_000
        eligible_programs.append(
            {
                "name": "Programme Batiments — Remplacement chauffage fossile",
                "estimated_amount_chf": amount,
                "requirements": [
                    "Remplacement du chauffage fossile par pompe a chaleur, bois, ou raccordement CAD",
                    "Batiment existant avec chauffage mazout ou gaz",
                ],
            }
        )

    # 2. Envelope insulation (Programme Batiments)
    if year and year < 2000:
        base_amount = int(surface_area * 40) if surface_area else 8_000
        amount = max(5_000, min(base_amount, 30_000))
        eligible_programs.append(
            {
                "name": "Programme Batiments — Isolation enveloppe",
                "estimated_amount_chf": amount,
                "requirements": [
                    "Batiment construit avant 2000",
                    "Isolation facade, toiture ou dalle sur sous-sol",
                    "Valeur U amelioree selon exigences cantonales",
                ],
            }
        )

    # 3. Solar installation
    if solar_suitability in ("high", "medium") or (solar_kwh and solar_kwh > 500):
        eligible_programs.append(
            {
                "name": "Pronovo — Installation photovoltaique (retribution unique)",
                "estimated_amount_chf": 3_000,
                "requirements": [
                    "Installation PV sur toiture existante",
                    "Puissance minimale 2 kWp",
                    "Raccordement au reseau confirme par GRD",
                ],
            }
        )

    # 4. Asbestos decontamination (VD cantonal)
    if asbestos_positive and canton == "VD":
        eligible_programs.append(
            {
                "name": "Canton de Vaud — Subvention desamiantage",
                "estimated_amount_chf": 5_000,
                "requirements": [
                    "Diagnostic amiante positif confirme",
                    "Travaux realises par entreprise certifiee SUVA",
                    "Batiment situe dans le canton de Vaud",
                ],
            }
        )

    # 5. Window replacement
    if year and year < 1990:
        eligible_programs.append(
            {
                "name": "Programme Batiments — Remplacement fenetres",
                "estimated_amount_chf": 5_000,
                "requirements": [
                    "Fenetres existantes simple ou double vitrage ancien",
                    "Remplacement par triple vitrage certifie Minergie",
                ],
            }
        )

    total = sum(p["estimated_amount_chf"] for p in eligible_programs)

    return {
        "eligible_programs": eligible_programs,
        "total_estimated_chf": total,
    }


# ---------------------------------------------------------------------------
# Component lifecycle prediction
# ---------------------------------------------------------------------------

COMPONENT_LIFESPANS: dict[str, int] = {
    "roof_flat": 25,
    "roof_pitched": 40,
    "facade_plaster": 35,
    "facade_curtain": 30,
    "windows_wood": 28,
    "windows_pvc": 33,
    "windows_alu": 35,
    "heating_oil": 22,
    "heating_gas": 20,
    "heating_heatpump": 20,
    "water_pipes": 45,
    "drainage": 50,
    "electrical": 35,
    "elevator": 28,
    "thermal_insulation": 40,
    "waterproofing": 25,
    "interior_finishes": 20,
    "ventilation": 20,
    "fire_protection": 30,
    "intercom_access": 20,
}

COMPONENT_NAMES_FR: dict[str, str] = {
    "roof_flat": "Toiture plate",
    "roof_pitched": "Toiture en pente",
    "facade_plaster": "Facade enduit",
    "facade_curtain": "Facade rideau",
    "windows_wood": "Fenetres bois",
    "windows_pvc": "Fenetres PVC",
    "windows_alu": "Fenetres aluminium",
    "heating_oil": "Chauffage mazout",
    "heating_gas": "Chauffage gaz",
    "heating_heatpump": "Pompe a chaleur",
    "water_pipes": "Conduites eau",
    "drainage": "Evacuation",
    "electrical": "Installation electrique",
    "elevator": "Ascenseur",
    "thermal_insulation": "Isolation thermique",
    "waterproofing": "Etancheite",
    "interior_finishes": "Finitions interieures",
    "ventilation": "Ventilation mecanique",
    "fire_protection": "Protection incendie",
    "intercom_access": "Interphone / controle d'acces",
}


def _component_status(lifespan_pct: float) -> str:
    """Return component status based on percentage of lifespan used."""
    if lifespan_pct < 0.20:
        return "new"
    if lifespan_pct < 0.50:
        return "good"
    if lifespan_pct < 0.75:
        return "aging"
    if lifespan_pct <= 1.0:
        return "end_of_life"
    return "overdue"


def _component_urgency(status: str, lifespan_pct: float) -> str:
    """Return urgency level from status."""
    if status == "overdue":
        return "critical" if lifespan_pct > 1.25 else "urgent"
    if status == "end_of_life":
        return "budget"
    if status == "aging":
        return "plan"
    return "none"


def compute_component_lifecycle(building_data: dict[str, Any]) -> dict[str, Any]:
    """Predict the state of each major building component.

    Based on construction_year + renovation_year + building_type.
    Pure function -- no API calls.
    All estimates are indicative and should be confirmed by on-site inspection.
    """
    year = building_data.get("construction_year")
    renovation_year = building_data.get("renovation_year")
    current_year = datetime.now(UTC).year

    if year is None:
        return {
            "components": [
                {
                    "name": name,
                    "name_fr": COMPONENT_NAMES_FR[name],
                    "installed_year": None,
                    "expected_end_year": None,
                    "age_years": None,
                    "lifespan_pct": None,
                    "status": "unknown",
                    "urgency": "none",
                }
                for name in COMPONENT_LIFESPANS
            ],
            "critical_count": 0,
            "urgent_count": 0,
            "total_overdue_years": 0,
        }

    installed_year = renovation_year if renovation_year and renovation_year > year else year

    components: list[dict[str, Any]] = []
    critical_count = 0
    urgent_count = 0
    total_overdue_years = 0

    for name, lifespan in COMPONENT_LIFESPANS.items():
        expected_end = installed_year + lifespan
        age = current_year - installed_year
        pct = age / lifespan if lifespan > 0 else 0.0
        status = _component_status(pct)
        urgency = _component_urgency(status, pct)

        if urgency == "critical":
            critical_count += 1
        if urgency == "urgent":
            urgent_count += 1
        if status == "overdue":
            total_overdue_years += current_year - expected_end

        components.append(
            {
                "name": name,
                "name_fr": COMPONENT_NAMES_FR[name],
                "installed_year": installed_year,
                "expected_end_year": expected_end,
                "age_years": age,
                "lifespan_pct": round(pct, 2),
                "status": status,
                "urgency": urgency,
            }
        )

    return {
        "components": components,
        "critical_count": critical_count,
        "urgent_count": urgent_count,
        "total_overdue_years": total_overdue_years,
    }


# ---------------------------------------------------------------------------
# Composite geospatial risk score
# ---------------------------------------------------------------------------

_GEO_RISK_GRADES = [
    (15, "A"),
    (30, "B"),
    (50, "C"),
    (70, "D"),
    (85, "E"),
]


def _geo_grade(score: float) -> str:
    """Return letter grade A-F from a 0-100 risk score."""
    for threshold, grade in _GEO_RISK_GRADES:
        if score <= threshold:
            return grade
    return "F"


def _risk_level(raw: float) -> str:
    """Classify a 0-100 dimension score into a human-readable level."""
    if raw <= 15:
        return "low"
    if raw <= 40:
        return "moderate"
    if raw <= 65:
        return "elevated"
    return "high"


def _flood_risk_score(enrichment_meta: dict[str, Any]) -> float | None:
    """Score 0-100 from natural_hazards.flood_risk + flood_zones.flood_danger_level.

    Takes the *worse* of the two sources.
    """
    scores: list[float] = []

    # From natural_hazards
    hazards = enrichment_meta.get("natural_hazards", {})
    if hazards:
        level = str(hazards.get("flood_risk", "")).lower()
        _map = {"high": 90.0, "medium": 50.0, "low": 15.0, "none": 0.0, "keine": 0.0}
        for key, val in _map.items():
            if key in level:
                scores.append(val)
                break

    # From flood_zones
    flood = enrichment_meta.get("flood_zones", {})
    if flood:
        level = str(flood.get("flood_danger_level", "")).lower()
        if "hoch" in level or "erheblich" in level or "high" in level:
            scores.append(90.0)
        elif "mittel" in level or "medium" in level:
            scores.append(50.0)
        elif "gering" in level or "low" in level:
            scores.append(15.0)
        elif level:
            scores.append(30.0)  # unknown non-empty = moderate

    return max(scores) if scores else None


def _seismic_risk_score(enrichment_meta: dict[str, Any]) -> float | None:
    """Score 0-100 from seismic zone."""
    seismic = enrichment_meta.get("seismic", {})
    if not seismic:
        return None
    zone = str(seismic.get("seismic_zone", "")).lower()
    _map = {"3b": 95.0, "3a": 80.0, "2": 50.0, "1": 20.0}
    return _map.get(zone)


def _contamination_score(enrichment_meta: dict[str, Any]) -> float | None:
    """Score 0-100 from contaminated_sites."""
    contam = enrichment_meta.get("contaminated_sites", {})
    if not contam:
        return None
    if contam.get("is_contaminated"):
        return 90.0
    return 5.0


def _radon_score(enrichment_meta: dict[str, Any]) -> float | None:
    """Score 0-100 from radon level."""
    radon = enrichment_meta.get("radon", {})
    if not radon:
        return None
    level = radon.get("radon_level", "")
    _map = {"high": 80.0, "medium": 40.0, "low": 10.0}
    return _map.get(level)


def _noise_score(enrichment_meta: dict[str, Any]) -> float | None:
    """Score 0-100 from the loudest noise source (road, rail, aircraft)."""
    noise = enrichment_meta.get("noise", {})
    rail = enrichment_meta.get("railway_noise", {})
    aircraft = enrichment_meta.get("aircraft_noise", {})

    values: list[float] = []
    road_db = noise.get("road_noise_day_db")
    if road_db is not None:
        values.append(float(road_db))
    rail_db = rail.get("railway_noise_day_db")
    if rail_db is not None:
        values.append(float(rail_db))
    air_db = aircraft.get("aircraft_noise_db")
    if air_db is not None:
        values.append(float(air_db))

    if not values:
        return None

    max_db = max(values)
    # Map dB to 0-100: <40→5, 40-50→20, 50-60→40, 60-70→65, >70→85
    if max_db < 40:
        return 5.0
    if max_db < 50:
        return 20.0
    if max_db < 55:
        return 35.0
    if max_db < 60:
        return 50.0
    if max_db < 65:
        return 65.0
    if max_db < 70:
        return 75.0
    return 85.0


def _landslide_score(enrichment_meta: dict[str, Any]) -> float | None:
    """Score 0-100 from natural_hazards.landslide_risk."""
    hazards = enrichment_meta.get("natural_hazards", {})
    if not hazards:
        return None
    level = str(hazards.get("landslide_risk", "")).lower()
    _map = {"high": 90.0, "medium": 50.0, "low": 15.0, "none": 0.0, "keine": 0.0}
    for key, val in _map.items():
        if key in level:
            return val
    return None


def _rockfall_score(enrichment_meta: dict[str, Any]) -> float | None:
    """Score 0-100 from natural_hazards.rockfall_risk."""
    hazards = enrichment_meta.get("natural_hazards", {})
    if not hazards:
        return None
    level = str(hazards.get("rockfall_risk", "")).lower()
    _map = {"high": 90.0, "medium": 50.0, "low": 15.0, "none": 0.0, "keine": 0.0}
    for key, val in _map.items():
        if key in level:
            return val
    return None


def _groundwater_restriction_score(enrichment_meta: dict[str, Any]) -> float | None:
    """Score 0-100 from groundwater protection zone."""
    gw = enrichment_meta.get("groundwater_zones", {})
    if not gw:
        return None
    zone = str(gw.get("protection_zone", "")).lower()
    if "s1" in zone:
        return 90.0
    if "s2" in zone:
        return 60.0
    if "s3" in zone:
        return 30.0
    # Has data but unknown zone
    return 15.0


def _seveso_proximity_score(enrichment_meta: dict[str, Any]) -> float | None:
    """Score 0-100 from proximity to a Seveso / major accident site."""
    seveso = enrichment_meta.get("accident_sites", {})
    if not seveso:
        return None
    if not seveso.get("near_seveso_site"):
        return 5.0
    # Near a Seveso site — distance modulates severity
    dist = seveso.get("distance_m")
    if dist is not None:
        if dist < 200:
            return 95.0
        if dist < 500:
            return 75.0
        if dist < 1000:
            return 50.0
        return 30.0
    # Near but no distance info
    return 80.0


def compute_geo_risk_score(enrichment_meta: dict[str, Any]) -> dict[str, Any] | None:
    """Composite geospatial risk score 0-100 (lower = safer).

    Grade: A (0-15), B (16-30), C (31-50), D (51-70), E (71-85), F (86-100).

    Dimensions weighted:
    - flood_risk (weight 3.0): from natural_hazards + flood_zones
    - seismic_risk (weight 2.5): from seismic zone
    - contamination (weight 3.0): from contaminated_sites
    - radon (weight 2.0): from radon zone (high=80, medium=40, low=10)
    - noise (weight 1.5): from road+rail+aircraft noise dB
    - landslide (weight 2.0): from natural_hazards
    - rockfall (weight 2.0): from natural_hazards
    - groundwater_restriction (weight 1.0): from groundwater zones
    - seveso_proximity (weight 2.5): from accident_sites

    Returns dict with geo_risk_score, geo_risk_grade, breakdown, top_risks,
    data_completeness.  Returns ``None`` when *no* dimension has data.

    Pure function -- no API calls.
    """
    dimensions: dict[str, tuple[float, float]] = {
        # name -> (weight, ...)
        "flood_risk": (3.0,),
        "seismic_risk": (2.5,),
        "contamination": (3.0,),
        "radon": (2.0,),
        "noise": (1.5,),
        "landslide": (2.0,),
        "rockfall": (2.0,),
        "groundwater_restriction": (1.0,),
        "seveso_proximity": (2.5,),
    }

    _scorers: dict[str, Any] = {
        "flood_risk": _flood_risk_score,
        "seismic_risk": _seismic_risk_score,
        "contamination": _contamination_score,
        "radon": _radon_score,
        "noise": _noise_score,
        "landslide": _landslide_score,
        "rockfall": _rockfall_score,
        "groundwater_restriction": _groundwater_restriction_score,
        "seveso_proximity": _seveso_proximity_score,
    }

    total_dimensions = len(dimensions)
    breakdown: dict[str, dict[str, Any]] = {}
    available_count = 0

    for dim, (weight,) in dimensions.items():
        raw = _scorers[dim](enrichment_meta)
        if raw is not None:
            available_count += 1
            breakdown[dim] = {
                "score": round(raw, 1),
                "weight": weight,
                "level": _risk_level(raw),
            }

    # No data at all → cannot compute
    if available_count == 0:
        return None

    data_completeness = round(available_count / total_dimensions, 2)

    # Weighted average of available dimensions only
    weighted_sum = sum(breakdown[d]["score"] * breakdown[d]["weight"] for d in breakdown)
    total_weight = sum(breakdown[d]["weight"] for d in breakdown)
    score = round(weighted_sum / total_weight, 1)
    score = max(0.0, min(100.0, score))

    grade = _geo_grade(score)

    # Top risks: sorted by weighted contribution descending
    ranked = sorted(
        breakdown.items(),
        key=lambda kv: kv[1]["score"] * kv[1]["weight"],
        reverse=True,
    )
    top_risks = [name for name, _ in ranked[:3]]

    return {
        "geo_risk_score": score,
        "geo_risk_grade": grade,
        "breakdown": breakdown,
        "top_risks": top_risks,
        "data_completeness": data_completeness,
    }
