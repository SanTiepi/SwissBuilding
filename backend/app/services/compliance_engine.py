"""
SwissBuildingOS - Compliance Engine Service

Swiss regulatory compliance checks for construction pollutants.
Implements threshold verification, CFST work categorization, OLED waste
classification, cantonal requirements, and SUVA notification rules.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import normalize_sample_unit
from app.services.rule_resolver import resolve_cantonal_requirements, resolve_threshold

# ---------------------------------------------------------------------------
# Swiss regulatory thresholds
# ---------------------------------------------------------------------------

SWISS_THRESHOLDS = {
    "asbestos": {
        "material_content": {"threshold": 1.0, "unit": "percent_weight", "legal_ref": "FACH 2018, OTConst Art. 82"},
        "air_fiber_count": {"threshold": 1000, "unit": "fibers_per_m3", "legal_ref": "VLT air interieur"},
        "air_work_limit": {"threshold": 10000, "unit": "fibers_per_m3", "legal_ref": "CFST 6503, VLE travail"},
    },
    "pcb": {
        "material_content": {"threshold": 50, "unit": "mg_per_kg", "legal_ref": "ORRChim Annexe 2.15"},
        "air_indoor": {"threshold": 6000, "unit": "ng_per_m3", "legal_ref": "Recommandation OFSP"},
        "waste_classification": {"threshold": 10, "unit": "mg_per_kg", "legal_ref": "OLED Annexe 5 (dechet entier)"},
    },
    "lead": {
        "paint_content": {"threshold": 5000, "unit": "mg_per_kg", "legal_ref": "ORRChim Annexe 2.18"},
        "water": {"threshold": 10, "unit": "ug_per_l", "legal_ref": "OSEC eau potable"},
    },
    "hap": {
        "material_content": {"threshold": 200, "unit": "mg_per_kg", "legal_ref": "OLED dechet special"},
    },
    "radon": {
        "reference_value": {"threshold": 300, "unit": "bq_per_m3", "legal_ref": "ORaP Art. 110"},
        "mandatory_action": {"threshold": 1000, "unit": "bq_per_m3", "legal_ref": "ORaP Art. 110"},
    },
}

# ---------------------------------------------------------------------------
# Cantonal requirements
# ---------------------------------------------------------------------------

CANTONAL_REQUIREMENTS = {
    "VD": {
        "authority_name": "DGE-DIRNA",
        "diagnostic_required_before_year": 1991,
        "requires_waste_elimination_plan": True,
        "form_name": "Plan d'elimination des dechets (PED)",
        "notification_delay_days": 14,
    },
    "GE": {
        "authority_name": "GESDEC",
        "diagnostic_required_before_year": 1991,
        "requires_waste_elimination_plan": True,
        "form_name": "Formulaire GESDEC diagnostic polluants",
        "notification_delay_days": 14,
        "online_system": "SADEC",
    },
    "ZH": {
        "authority_name": "AWEL",
        "diagnostic_required_before_year": 1991,
        "requires_waste_elimination_plan": True,
        "form_name": "Checkliste Schadstoffe im Gebaude",
        "notification_delay_days": 14,
    },
    "BE": {
        "authority_name": "AWA",
        "diagnostic_required_before_year": 1991,
        "requires_waste_elimination_plan": True,
        "form_name": "Notice intercantonale diagnostic polluants",
        "notification_delay_days": 14,
    },
    "VS": {
        "authority_name": "SEN",
        "diagnostic_required_before_year": 1991,
        "requires_waste_elimination_plan": True,
        "form_name": "Notice diagnostic polluants et plan d'elimination",
        "notification_delay_days": 14,
    },
}

_DEFAULT_CANTONAL = {
    "authority_name": "Service cantonal de l'environnement",
    "diagnostic_required_before_year": 1991,
    "requires_waste_elimination_plan": True,
    "form_name": "Notice intercantonale diagnostic polluants",
    "notification_delay_days": 14,
}


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

_STATE_ALIASES: dict[str, str] = {
    "bon": "good",
    "good": "good",
    "intact": "good",
    "degrade": "degraded",
    "degraded": "degraded",
    "mauvais": "degraded",
    "tres_degrade": "heavily_degraded",
    "heavily_degraded": "heavily_degraded",
    "friable": "friable",
}


def _normalise_unit(unit: str) -> str:
    return normalize_sample_unit(unit) or ""


def _normalise_state(state: str) -> str:
    return _STATE_ALIASES.get(state.lower().strip(), state.lower().strip())


def _find_matching_threshold(pollutant: str, unit: str) -> dict | None:
    """Find the threshold entry matching the pollutant and unit."""
    norm_unit = _normalise_unit(unit)
    entries = SWISS_THRESHOLDS.get(pollutant.lower(), {})
    for entry in entries.values():
        if _normalise_unit(entry["unit"]) == norm_unit:
            return entry
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_threshold(pollutant: str, concentration: float, unit: str) -> dict:
    """
    Check whether a measured concentration exceeds the Swiss regulatory threshold.

    Returns dict with keys: exceeded, threshold, unit, legal_ref, action.
    """
    entry = _find_matching_threshold(pollutant, unit)

    if entry is None:
        return {
            "exceeded": False,
            "threshold": None,
            "unit": unit,
            "legal_ref": None,
            "action": "no_matching_threshold",
        }

    exceeded = concentration >= entry["threshold"]
    if exceeded:
        action = "remove_urgent" if concentration >= entry["threshold"] * 3 else "remove_planned"
    else:
        action = "none"

    return {
        "exceeded": exceeded,
        "threshold": entry["threshold"],
        "unit": entry["unit"],
        "legal_ref": entry["legal_ref"],
        "action": action,
    }


def determine_risk_level(pollutant: str, concentration: float, unit: str) -> str:
    """
    Determine risk level based on concentration relative to threshold.

    Returns one of: low, medium, high, critical.
    """
    entry = _find_matching_threshold(pollutant, unit)

    if entry is None:
        return "low"

    threshold = entry["threshold"]
    ratio = concentration / threshold if threshold > 0 else 0.0

    if ratio < 0.5:
        return "low"
    if ratio < 1.0:
        return "medium"
    if ratio < 3.0:
        return "high"
    return "critical"


def determine_cfst_work_category(
    material_category: str,
    material_state: str,
    surface_m2: float | None,
) -> str:
    """
    Determine CFST 6503 work category for asbestos-containing materials.

    Categories:
      - minor: non-friable, good condition, surface <= 5 m2
      - medium: medium surface or degraded condition
      - major: large surface (>10 m2), friable / heavily degraded material
    """
    state = _normalise_state(material_state or "good")
    cat_lower = (material_category or "").lower()
    area = surface_m2 if surface_m2 is not None else 1.0

    # Friable materials or spray-applied insulation are always major
    friable_keywords = {"friable", "flocage", "spray", "calorifuge"}
    if state in ("friable", "heavily_degraded") or any(kw in cat_lower for kw in friable_keywords):
        return "major"

    if state == "degraded" or area > 10.0:
        return "medium"

    # Non-friable, good condition, small to medium surface
    if state == "good" and area <= 5.0:
        return "minor"

    return "medium"


def determine_waste_disposal(
    pollutant: str,
    material_category: str,
    material_state: str,
) -> str:
    """
    Determine OLED waste disposal type.

    Returns one of: type_b (inert), type_e (controlled), special.
    """
    pollutant_lower = pollutant.lower()
    state = _normalise_state(material_state or "good")
    cat_lower = (material_category or "").lower()

    if pollutant_lower == "asbestos":
        # Friable asbestos (flocage, calorifuge) → special waste
        if state in ("friable", "heavily_degraded") or "flocage" in cat_lower or "calorifuge" in cat_lower:
            return "special"
        # Strongly bonded asbestos (fibrociment, eternit) in good condition → type_b (inert)
        bonded_keywords = {"fibrociment", "fibre_cement", "fiber_cement", "eternit", "toiture", "roof"}
        if any(kw in cat_lower for kw in bonded_keywords) and state == "good":
            return "type_b"
        # Other asbestos → type_e (controlled)
        return "type_e"

    if pollutant_lower == "pcb":
        return "special"

    if pollutant_lower == "lead":
        if state in ("friable", "heavily_degraded"):
            return "special"
        return "type_e"

    if pollutant_lower == "hap":
        return "special"

    # Default for unknown pollutants
    return "type_e"


def determine_action_required(
    pollutant: str,
    risk_level: str,
    concentration: float | None,
) -> str:
    """
    Determine required action based on pollutant, risk level, and concentration.

    Returns one of: none, monitor, encapsulate, remove_planned, remove_urgent.
    """
    level = risk_level.lower()

    if level == "critical":
        return "remove_urgent"

    if level == "high":
        return "remove_planned"

    if level == "medium":
        if pollutant.lower() in ("asbestos", "lead"):
            return "encapsulate"
        return "monitor"

    return "none"


def check_suva_notification_required(
    diagnostic_type: str,
    has_positive_asbestos: bool,
) -> bool:
    """
    Determine whether SUVA notification is required.

    SUVA must be notified when asbestos is found and workers may be exposed
    during renovation/demolition work.
    """
    notifiable_types = {"renovation", "demolition", "full", "asbestos", "avant_travaux", "avt"}
    return diagnostic_type.lower() in notifiable_types and has_positive_asbestos


def get_cantonal_requirements(canton: str) -> dict:
    """
    Return cantonal regulatory requirements.
    Falls back to default requirements for cantons not explicitly configured.
    """
    requirements = CANTONAL_REQUIREMENTS.get(canton.upper(), dict(_DEFAULT_CANTONAL))
    return {**requirements, "canton": canton.upper()}


def auto_classify_sample(sample_data: dict) -> dict:
    """
    Given raw sample data, auto-compute compliance classification fields.

    Expected input keys:
      - pollutant_type: str
      - concentration: float
      - unit: str
      - material_category: str (optional)
      - material_state: str (optional)
      - surface_m2: float (optional)

    Returns dict with:
      - threshold_exceeded: bool
      - risk_level: str
      - cfst_work_category: str | None
      - action_required: str
      - waste_disposal_type: str
    """
    pollutant = sample_data.get("pollutant_type", "")
    concentration = sample_data.get("concentration")
    unit = sample_data.get("unit", "")
    material_category = sample_data.get("material_category", "")
    material_state = sample_data.get("material_state", "good")
    surface_m2 = sample_data.get("surface_m2")

    # Default values when concentration is missing
    if concentration is None:
        return {
            "threshold_exceeded": False,
            "risk_level": "low",
            "cfst_work_category": None,
            "action_required": "none",
            "waste_disposal_type": "type_e",
        }

    # Threshold check
    threshold_result = check_threshold(pollutant, concentration, unit)
    threshold_exceeded = threshold_result["exceeded"]

    # Risk level
    risk_level = determine_risk_level(pollutant, concentration, unit)

    # CFST work category (only meaningful for asbestos)
    cfst_work_category = None
    if pollutant.lower() == "asbestos" and threshold_exceeded:
        cfst_work_category = determine_cfst_work_category(material_category, material_state, surface_m2)

    # Action required
    action_required = determine_action_required(pollutant, risk_level, concentration)

    # Waste disposal type (only if threshold exceeded)
    if threshold_exceeded:
        waste_disposal_type = determine_waste_disposal(pollutant, material_category, material_state)
    else:
        waste_disposal_type = "type_b"

    return {
        "threshold_exceeded": threshold_exceeded,
        "risk_level": risk_level,
        "cfst_work_category": cfst_work_category,
        "action_required": action_required,
        "waste_disposal_type": waste_disposal_type,
    }


# ---------------------------------------------------------------------------
# Async resolved variants (rule_resolver first, hardcoded fallback)
# ---------------------------------------------------------------------------


async def check_threshold_resolved(
    db: AsyncSession,
    jurisdiction_id: UUID | None,
    pollutant: str,
    concentration: float,
    unit: str,
) -> dict:
    """
    Check whether a measured concentration exceeds the regulatory threshold.

    Tries the rule_resolver service first (jurisdiction-aware packs). If no pack
    is found, falls back to the hardcoded ``check_threshold()`` function.
    """
    resolved = await resolve_threshold(db, jurisdiction_id, pollutant, unit)

    if resolved is not None:
        threshold = resolved["threshold"]
        exceeded = concentration >= threshold
        if exceeded:
            action = "remove_urgent" if concentration >= threshold * 3 else "remove_planned"
        else:
            action = "none"

        return {
            "exceeded": exceeded,
            "threshold": threshold,
            "unit": resolved["unit"],
            "legal_ref": resolved["legal_ref"],
            "action": action,
            "source": "regulatory_pack",
        }

    # Fallback to hardcoded thresholds
    result = check_threshold(pollutant, concentration, unit)
    result["source"] = "hardcoded"
    return result


async def get_cantonal_requirements_resolved(
    db: AsyncSession,
    jurisdiction_id: UUID | None,
    canton: str,
) -> dict:
    """
    Return cantonal regulatory requirements.

    Tries the rule_resolver service first (jurisdiction metadata + packs). If no
    jurisdiction data is found, falls back to the hardcoded
    ``get_cantonal_requirements()`` function.
    """
    resolved = await resolve_cantonal_requirements(db, jurisdiction_id)

    if resolved is not None:
        resolved["source"] = "regulatory_pack"
        return resolved

    # Fallback to hardcoded cantonal requirements
    result = get_cantonal_requirements(canton)
    result["source"] = "hardcoded"
    return result
