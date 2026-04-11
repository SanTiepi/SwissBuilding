"""Regulatory compliance checks (pure computation)."""

from __future__ import annotations

from typing import Any


def _fire_safety_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """AEAI fire protection compliance check."""
    year = building_data.get("construction_year")
    floors = building_data.get("floors_above") or building_data.get("floors") or 0
    lifecycle = enrichment_data.get("component_lifecycle", {})
    comps = {c["name"]: c for c in lifecycle.get("components", [])}
    fire_comp = comps.get("fire_protection", {})

    if fire_comp.get("status") in ("overdue", "end_of_life"):
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Protection incendie en fin de vie ou depassee — verification obligatoire.",
            "action_required_fr": "Mandater un controle AEAI et planifier la mise aux normes.",
            "deadline": None,
            "confidence": "medium",
        }
    if year and year < 1985 and floors > 3:
        return {
            "status": "review_needed",
            "reason_fr": f"Batiment de {year}, {floors} etages — normes AEAI potentiellement non respectees.",
            "action_required_fr": "Verifier la conformite avec les prescriptions AEAI actuelles.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Aucun indicateur de non-conformite incendie detecte.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _electrical_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OIBT electrical installations check."""
    lifecycle = enrichment_data.get("component_lifecycle", {})
    comps = {c["name"]: c for c in lifecycle.get("components", [])}
    elec = comps.get("electrical", {})

    if elec.get("status") == "overdue":
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Installation electrique depassee — controle periodique probablement non conforme.",
            "action_required_fr": "Mandater un controle OIBT par un organisme agree.",
            "deadline": None,
            "confidence": "medium",
        }
    if elec.get("status") == "end_of_life":
        return {
            "status": "review_needed",
            "reason_fr": "Installation electrique en fin de vie — controle OIBT recommande.",
            "action_required_fr": "Planifier un controle OIBT.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Installation electrique dans sa duree de vie estimee.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _noise_protection_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OPB noise protection check."""
    noise = enrichment_data.get("noise", {})
    road_db = noise.get("road_noise_day_db", 0) or 0
    rail = enrichment_data.get("railway_noise", {})
    rail_db = rail.get("railway_noise_day_db", 0) or 0
    max_noise = max(road_db, rail_db)

    if max_noise > 65:
        return {
            "status": "likely_non_compliant",
            "reason_fr": f"Exposition au bruit elevee ({max_noise} dB) — depassement probable des VLI.",
            "action_required_fr": "Evaluer les mesures d'isolation phonique (fenetres, facade).",
            "deadline": None,
            "confidence": "medium",
        }
    if max_noise > 55:
        return {
            "status": "review_needed",
            "reason_fr": f"Exposition au bruit moderee ({max_noise} dB) — verification recommandee.",
            "action_required_fr": "Verifier la conformite avec les valeurs limites OPB.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Niveaux de bruit dans les limites OPB estimees.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _energy_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OEne energy ordinance check."""
    year = building_data.get("construction_year")
    heating = str(building_data.get("heating_type", "") or "").lower()
    oil_gas = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas")

    if any(ind in heating for ind in oil_gas) and year and year < 2000:
        return {
            "status": "likely_non_compliant",
            "reason_fr": f"Chauffage fossile dans un batiment de {year} — non conforme OEne/MoPEC.",
            "action_required_fr": "Planifier le remplacement du chauffage fossile par une energie renouvelable.",
            "deadline": None,
            "confidence": "medium",
        }
    if year and year < 1990:
        return {
            "status": "review_needed",
            "reason_fr": f"Batiment de {year} — performance energetique probablement insuffisante.",
            "action_required_fr": "Realiser un CECB pour evaluer la performance energetique.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Aucun indicateur de non-conformite energetique detecte.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _accessibility_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """LHand accessibility check."""
    acc = enrichment_data.get("accessibility", {})
    status = acc.get("compliance_status", "unknown")

    _status_map = {
        "full_compliance_required": (
            "review_needed",
            "LHand: conformite complete requise pour ce batiment.",
            "Verifier la conformite avec les exigences LHand.",
        ),
        "partial_compliance_required": (
            "review_needed",
            "LHand: conformite partielle requise.",
            "Verifier les exigences minimales d'accessibilite.",
        ),
        "adaptation_required": (
            "review_needed",
            "LHand: adaptation requise suite a renovation majeure.",
            "Evaluer les adaptations d'accessibilite necessaires.",
        ),
    }
    if status in _status_map:
        s, reason, action = _status_map[status]
        return {
            "status": s,
            "reason_fr": reason,
            "action_required_fr": action,
            "deadline": None,
            "confidence": "medium",
        }
    return {
        "status": "not_assessed",
        "reason_fr": "Pas d'obligation LHand identifiee pour ce batiment.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _hazardous_substances_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OTConst hazardous substances check."""
    pollutant_risk = enrichment_data.get("pollutant_risk", {})
    asbestos = pollutant_risk.get("asbestos_probability", 0)
    pcb = pollutant_risk.get("pcb_probability", 0)
    lead = pollutant_risk.get("lead_probability", 0)

    if asbestos > 0.6 or pcb > 0.5:
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Probabilite elevee de presence de substances dangereuses (amiante/PCB).",
            "action_required_fr": "Realiser un diagnostic substances dangereuses avant tout travaux.",
            "deadline": None,
            "confidence": "medium",
        }
    if asbestos > 0.3 or pcb > 0.2 or lead > 0.3:
        return {
            "status": "review_needed",
            "reason_fr": "Probabilite moderee de presence de polluants — verification recommandee.",
            "action_required_fr": "Planifier un diagnostic de polluants du batiment.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Probabilite faible de presence de substances dangereuses.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _air_protection_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OPAM air protection check."""
    heating = str(building_data.get("heating_type", "") or "").lower()
    oil_indicators = ("oil", "mazout", "heizol")

    if any(ind in heating for ind in oil_indicators):
        return {
            "status": "review_needed",
            "reason_fr": "Chauffage au mazout — conformite OPAM a verifier (emissions).",
            "action_required_fr": "Verifier les emissions du systeme de chauffage.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Aucun indicateur de non-conformite OPAM detecte.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _water_protection_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """LEaux water protection check."""
    water = enrichment_data.get("water_protection", {})
    groundwater = enrichment_data.get("groundwater_zones", {})

    if water.get("in_protection_zone") or groundwater.get("in_protection_zone"):
        return {
            "status": "review_needed",
            "reason_fr": "Batiment en zone de protection des eaux — contraintes LEaux applicables.",
            "action_required_fr": "Verifier les restrictions applicables (stockage, evacuation, travaux).",
            "deadline": None,
            "confidence": "medium",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Pas en zone de protection des eaux identifiee.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _mopec_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """MoPEC cantonal energy prescriptions check."""
    year = building_data.get("construction_year")
    heating = str(building_data.get("heating_type", "") or "").lower()
    oil_gas = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas")

    if year and year < 2000 and any(ind in heating for ind in oil_gas):
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Chauffage fossile dans batiment ancien — objectifs MoPEC non atteints.",
            "action_required_fr": "Planifier la transition vers une source d'energie renouvelable.",
            "deadline": None,
            "confidence": "medium",
        }
    if year and year < 2010:
        return {
            "status": "review_needed",
            "reason_fr": f"Batiment de {year} — verifier la conformite aux prescriptions MoPEC cantonales.",
            "action_required_fr": "Realiser un audit energetique (CECB).",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Batiment recent — probablement conforme MoPEC.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _sia500_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """SIA 500 accessibility check."""
    year = building_data.get("construction_year")
    dwellings = building_data.get("dwellings") or 0
    has_elevator = building_data.get("has_elevator", False)
    floors = building_data.get("floors_above") or building_data.get("floors") or 0

    if year and year >= 2009 and dwellings >= 8 and not has_elevator and floors > 1:
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Batiment post-2009 avec 8+ logements sans ascenseur — SIA 500 non respectee.",
            "action_required_fr": "Installer un ascenseur conforme SIA 500.",
            "deadline": None,
            "confidence": "medium",
        }
    if dwellings >= 8 and not has_elevator and floors > 2:
        return {
            "status": "review_needed",
            "reason_fr": "Batiment avec 8+ logements et 3+ etages sans ascenseur.",
            "action_required_fr": "Evaluer la faisabilite d'installation d'un ascenseur.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Aucun indicateur de non-conformite SIA 500 detecte.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


_REGULATION_CHECKS: list[dict[str, Any]] = [
    {"code": "AEAI", "name": "Protection incendie", "check": _fire_safety_check},
    {"code": "OIBT", "name": "Installations electriques", "check": _electrical_check},
    {"code": "OPB", "name": "Protection contre le bruit", "check": _noise_protection_check},
    {"code": "OEne", "name": "Ordonnance sur l'energie", "check": _energy_check},
    {"code": "LHand", "name": "Egalite pour les handicapes", "check": _accessibility_check},
    {"code": "OTConst", "name": "Substances dangereuses", "check": _hazardous_substances_check},
    {"code": "OPAM", "name": "Protection de l'air", "check": _air_protection_check},
    {"code": "LEaux", "name": "Protection des eaux", "check": _water_protection_check},
    {"code": "MoPEC", "name": "Prescriptions energetiques", "check": _mopec_check},
    {"code": "SIA500", "name": "Accessibilite", "check": _sia500_check},
]


def compute_regulatory_compliance(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Check applicable Swiss regulations against building data.

    Pure function -- no API calls.
    Results are indicative estimates -- formal compliance requires professional assessment.
    """
    checks: list[dict[str, Any]] = []
    compliant_count = 0
    non_compliant_count = 0
    review_needed_count = 0

    for reg in _REGULATION_CHECKS:
        check_fn = reg["check"]
        result = check_fn(building_data, enrichment_data)
        entry = {
            "code": reg["code"],
            "name": reg["name"],
            "applicable": True,
            **result,
        }
        checks.append(entry)

        status = result.get("status", "not_assessed")
        if status in ("compliant", "likely_compliant"):
            compliant_count += 1
        elif status in ("non_compliant", "likely_non_compliant"):
            non_compliant_count += 1
        elif status == "review_needed":
            review_needed_count += 1

    if non_compliant_count > 0:
        overall_status = "action_required"
    elif review_needed_count > 0:
        overall_status = "review_recommended"
    else:
        overall_status = "satisfactory"

    parts: list[str] = []
    if non_compliant_count:
        parts.append(f"{non_compliant_count} non-conformite(s) probable(s)")
    if review_needed_count:
        parts.append(f"{review_needed_count} verification(s) recommandee(s)")
    if compliant_count:
        parts.append(f"{compliant_count} point(s) conformes")
    summary_fr = (
        "Bilan reglementaire (estimation): " + ", ".join(parts) + "." if parts else "Evaluation non disponible."
    )

    return {
        "checks": checks,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "review_needed_count": review_needed_count,
        "overall_status": overall_status,
        "summary_fr": summary_fr,
    }
