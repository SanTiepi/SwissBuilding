"""
SwissBuildingOS - Renovation Simulator Service

Simulates renovation costs, timelines, and compliance requirements
based on pollutant risk profiles and Swiss regulatory framework.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.services.compliance_engine import (
    get_cantonal_requirements,
)
from app.services.risk_engine import (
    RENOVATION_EXPOSURE,
    calculate_building_risk,
)

# ---------------------------------------------------------------------------
# Cost constants
# ---------------------------------------------------------------------------

BASE_COSTS_CHF_PER_M2 = {
    "asbestos": {"minor": 80, "medium": 250, "major": 600},
    "pcb": {"low": 60, "medium": 200, "high": 450},
    "lead": {"low": 40, "medium": 150, "high": 350},
    "hap": {"low": 50, "medium": 180, "high": 400},
    "radon": {"low": 30, "medium": 100, "high": 250},
}

DIAGNOSTIC_COSTS_CHF = {
    "asbestos": 2500,
    "pcb": 1800,
    "lead": 1500,
    "hap": 1500,
    "radon": 800,
    "full": 6000,
}

# Which material categories are at risk for each renovation type
MATERIAL_CATEGORIES_BY_RENOVATION = {
    "full_renovation": [
        "flocage",
        "calorifuge",
        "joints",
        "colles_carrelage",
        "dalles_vinyle",
        "fibre_cement",
        "enduit",
        "peinture",
        "mastic_fenetre",
        "etancheite_toiture",
        "conduits",
    ],
    "partial_interior": [
        "colles_carrelage",
        "dalles_vinyle",
        "enduit",
        "peinture",
        "joints",
    ],
    "roof": [
        "fibre_cement",
        "etancheite_toiture",
        "flocage",
    ],
    "facade": [
        "enduit",
        "fibre_cement",
        "peinture",
        "mastic_fenetre",
        "joints",
    ],
    "bathroom": [
        "colles_carrelage",
        "joints",
        "dalles_vinyle",
        "peinture",
        "conduits",
    ],
    "kitchen": [
        "colles_carrelage",
        "joints",
        "dalles_vinyle",
        "peinture",
    ],
    "flooring": [
        "dalles_vinyle",
        "colles_carrelage",
        "enduit",
    ],
    "windows": [
        "mastic_fenetre",
        "peinture",
        "joints",
    ],
}

# ---------------------------------------------------------------------------
# Risk-level to cost-tier mapping
# ---------------------------------------------------------------------------


def _risk_to_cost_tier(pollutant: str, probability: float) -> str:
    """Map a probability to the appropriate cost tier for a pollutant."""
    if pollutant == "asbestos":
        if probability >= 0.7:
            return "major"
        if probability >= 0.3:
            return "medium"
        return "minor"
    else:
        if probability >= 0.7:
            return "high"
        if probability >= 0.3:
            return "medium"
        return "low"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def estimate_remediation_cost(
    pollutant: str,
    risk_level: str,
    surface_m2: float,
) -> float:
    """
    Estimate remediation cost in CHF for a single pollutant.

    risk_level should be one of the tier keys for the pollutant in BASE_COSTS_CHF_PER_M2.
    """
    pollutant_costs = BASE_COSTS_CHF_PER_M2.get(pollutant.lower(), {})
    cost_per_m2 = pollutant_costs.get(risk_level.lower(), 0)
    return round(cost_per_m2 * surface_m2, 2)


def estimate_timeline_weeks(
    pollutant_risks: list[dict],
    renovation_type: str,
) -> int:
    """
    Estimate total project timeline in weeks.

    Base timeline depends on renovation type; high-risk pollutants add
    extra weeks for diagnostics, planning, and remediation.
    """
    base_weeks = {
        "full_renovation": 8,
        "partial_interior": 4,
        "roof": 3,
        "facade": 4,
        "bathroom": 3,
        "kitchen": 3,
        "flooring": 2,
        "windows": 2,
    }

    weeks = base_weeks.get(renovation_type, 4)

    # Add diagnostic phase if any pollutant has significant risk
    significant_risks = [r for r in pollutant_risks if r.get("probability", 0) >= 0.25]
    if significant_risks:
        weeks += 2  # diagnostic phase

    # Add remediation time per high-risk pollutant
    high_risks = [r for r in pollutant_risks if r.get("probability", 0) >= 0.55]
    weeks += len(high_risks) * 2

    # Add 1 week for SUVA/cantonal notification if needed
    critical_risks = [r for r in pollutant_risks if r.get("probability", 0) >= 0.80]
    if critical_risks:
        weeks += 1

    return weeks


def get_required_diagnostics(
    building: Building,
    renovation_type: str,
) -> list[str]:
    """
    Determine which pollutant diagnostics are required before renovation.

    Based on the building's construction year and the renovation type.
    """
    required: list[str] = []
    year = building.construction_year

    # Federal rule: buildings built before 1991 require pollutant diagnostics
    # before any renovation work
    if year is None or year < 1991:
        exposure = RENOVATION_EXPOSURE.get(renovation_type, {})

        # Asbestos diagnostic needed if exposure factor >= 0.5
        if exposure.get("asbestos", 1.0) >= 0.5:
            required.append("asbestos")

        # PCB diagnostic needed if exposure >= 0.3 and year in risk range
        if exposure.get("pcb", 1.0) >= 0.3 and (year is None or (1955 <= year < 1986)):
            required.append("pcb")

        # Lead diagnostic if exposure >= 0.4 and year suggests risk
        if exposure.get("lead", 1.0) >= 0.4 and (year is None or year < 1980):
            required.append("lead")

        # HAP diagnostic if exposure >= 0.4
        if exposure.get("hap", 1.0) >= 0.4 and (year is None or year < 1985):
            required.append("hap")

    # Radon: always recommended for ground-floor / basement work
    if renovation_type in ("full_renovation", "flooring", "partial_interior"):
        canton = (building.canton or "").upper()
        HIGH_RADON = {"GR", "TI", "VS", "UR", "NW", "OW", "JU"}
        MEDIUM_RADON = {"BE", "FR", "NE", "SZ", "GL", "AI", "AR", "SG", "BL", "SO"}
        if canton in HIGH_RADON or canton in MEDIUM_RADON:
            required.append("radon")

    return required


def get_compliance_requirements(
    building: Building,
    pollutant_risks: list[dict],
) -> list[dict]:
    """
    Determine compliance requirements based on building and pollutant risks.

    Returns a list of requirement dicts with keys:
      - requirement, description, legal_ref, mandatory
    """
    requirements: list[dict] = []
    canton = (building.canton or "").upper()
    cantonal = get_cantonal_requirements(canton)

    year = building.construction_year

    # Diagnostic obligation
    diag_year = cantonal.get("diagnostic_required_before_year", 1991)
    if year is None or year < diag_year:
        requirements.append(
            {
                "requirement": "diagnostic_polluants",
                "description": f"Diagnostic polluants obligatoire pour batiments construits avant {diag_year}",
                "legal_ref": "OTConst Art. 82, OLED",
                "mandatory": True,
            }
        )

    # Waste elimination plan
    if cantonal.get("requires_waste_elimination_plan"):
        requirements.append(
            {
                "requirement": "plan_elimination_dechets",
                "description": f"Formulaire: {cantonal.get('form_name', 'N/A')}. "
                f"Autorite: {cantonal.get('authority_name', 'N/A')}.",
                "legal_ref": "OLED",
                "mandatory": True,
            }
        )

    # SUVA notification for asbestos
    asbestos_risk = next(
        (r for r in pollutant_risks if r.get("pollutant") == "asbestos"),
        None,
    )
    if asbestos_risk and asbestos_risk.get("probability", 0) >= 0.55:
        requirements.append(
            {
                "requirement": "suva_notification",
                "description": "Annonce SUVA requise en cas de travaux avec materiaux amiantiferes",
                "legal_ref": "OTConst Art. 82, Directive CFST 6503",
                "mandatory": True,
            }
        )

    # Cantonal notification delay
    notification_days = cantonal.get("notification_delay_days", 14)
    requirements.append(
        {
            "requirement": "cantonal_notification",
            "description": f"Delai d'annonce au canton: {notification_days} jours avant travaux. "
            f"Autorite: {cantonal.get('authority_name', 'Service cantonal')}.",
            "legal_ref": "Legislation cantonale",
            "mandatory": True,
        }
    )

    # Radon-specific
    radon_risk = next(
        (r for r in pollutant_risks if r.get("pollutant") == "radon"),
        None,
    )
    if radon_risk and radon_risk.get("probability", 0) >= 0.30:
        requirements.append(
            {
                "requirement": "radon_measurement",
                "description": "Mesure radon recommandee (dosimetre passif, min. 3 mois en hiver)",
                "legal_ref": "ORaP Art. 110",
                "mandatory": radon_risk.get("probability", 0) >= 0.60,
            }
        )

    return requirements


async def simulate_renovation(
    db: AsyncSession,
    building_id: UUID,
    renovation_type: str,
) -> dict:
    """
    Main renovation simulation function.

    Fetches the building, calculates risk per pollutant, estimates costs,
    determines required diagnostics and compliance, and estimates timeline.

    Returns a complete simulation result dict.
    """
    # Fetch building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one()

    # Calculate risk
    risk_score = await calculate_building_risk(db, building)

    # Build per-pollutant risk list with renovation exposure applied
    exposure = RENOVATION_EXPOSURE.get(renovation_type, {})
    surface = building.surface_area_m2 or 100.0  # default estimate

    pollutant_scores = {
        "asbestos": risk_score.asbestos_probability,
        "pcb": risk_score.pcb_probability,
        "lead": risk_score.lead_probability,
        "hap": risk_score.hap_probability,
        "radon": risk_score.radon_probability,
    }

    pollutant_risks: list[dict] = []
    total_remediation_cost = 0.0
    total_diagnostic_cost = 0.0

    for pollutant, base_prob in pollutant_scores.items():
        # Apply renovation exposure modifier
        expo_factor = exposure.get(pollutant, 1.0)
        effective_prob = min(1.0, base_prob * expo_factor)

        # Determine cost tier
        cost_tier = _risk_to_cost_tier(pollutant, effective_prob)

        # Estimate remediation cost (scaled by probability)
        full_cost = estimate_remediation_cost(pollutant, cost_tier, surface)
        weighted_cost = round(full_cost * effective_prob, 2)

        # Diagnostic cost if probability is significant
        diag_cost = 0.0
        if effective_prob >= 0.20:
            diag_cost = DIAGNOSTIC_COSTS_CHF.get(pollutant, 1500)
            total_diagnostic_cost += diag_cost

        total_remediation_cost += weighted_cost

        pollutant_risks.append(
            {
                "pollutant": pollutant,
                "probability": round(effective_prob, 4),
                "cost_tier": cost_tier,
                "remediation_cost_chf": weighted_cost,
                "diagnostic_cost_chf": diag_cost,
                "materials_at_risk": MATERIAL_CATEGORIES_BY_RENOVATION.get(renovation_type, []),
            }
        )

    # Required diagnostics
    required_diagnostics = get_required_diagnostics(building, renovation_type)

    # Compliance requirements
    compliance = get_compliance_requirements(building, pollutant_risks)

    # Timeline
    timeline_weeks = estimate_timeline_weeks(pollutant_risks, renovation_type)

    # Cost summary
    total_cost = round(total_remediation_cost + total_diagnostic_cost, 2)
    _cost_range_low = round(total_cost * 0.7, 2)
    _cost_range_high = round(total_cost * 1.5, 2)

    # Build pollutant risk details matching PollutantRiskDetail schema
    pollutant_risk_details = []
    for pr in pollutant_risks:
        expo_factor = exposure.get(pr["pollutant"], 1.0)
        risk_level_val = "high" if pr["probability"] >= 0.55 else ("medium" if pr["probability"] >= 0.25 else "low")
        pollutant_risk_details.append(
            {
                "pollutant": pr["pollutant"],
                "probability": pr["probability"],
                "risk_level": risk_level_val,
                "exposure_factor": expo_factor,
                "materials_at_risk": pr.get("materials_at_risk", []),
                "estimated_cost_chf": pr.get("remediation_cost_chf", 0.0),
            }
        )

    # Build compliance requirements matching ComplianceRequirementDetail schema
    compliance_details = []
    for c in compliance:
        compliance_details.append(
            {
                "requirement": c.get("requirement", ""),
                "legal_reference": c.get("legal_ref", ""),
                "mandatory": c.get("mandatory", True),
                "deadline_days": None,
            }
        )

    return {
        "building_id": str(building_id),
        "renovation_type": renovation_type,
        "pollutant_risks": pollutant_risk_details,
        "total_estimated_cost_chf": total_cost,
        "required_diagnostics": required_diagnostics,
        "compliance_requirements": compliance_details,
        "timeline_weeks": timeline_weeks,
    }


def _build_timeline_phases(
    required_diagnostics: list[str],
    pollutant_risks: list[dict],
    renovation_type: str,
) -> list[dict]:
    """Build a list of project phases with estimated durations."""
    phases: list[dict] = []
    week = 1

    # Phase 1: Diagnostics
    if required_diagnostics:
        diag_weeks = 2
        phases.append(
            {
                "phase": "diagnostics",
                "description": f"Diagnostics polluants: {', '.join(required_diagnostics)}",
                "start_week": week,
                "duration_weeks": diag_weeks,
            }
        )
        week += diag_weeks

    # Phase 2: Notifications & permits
    significant = [r for r in pollutant_risks if r.get("probability", 0) >= 0.55]
    if significant:
        phases.append(
            {
                "phase": "notifications",
                "description": "Annonces SUVA/canton et obtention des autorisations",
                "start_week": week,
                "duration_weeks": 1,
            }
        )
        week += 1

    # Phase 3: Remediation (if needed)
    high_risks = [r for r in pollutant_risks if r.get("probability", 0) >= 0.55]
    if high_risks:
        remed_weeks = len(high_risks) * 2
        pollutant_names = [r["pollutant"] for r in high_risks]
        phases.append(
            {
                "phase": "remediation",
                "description": f"Assainissement: {', '.join(pollutant_names)}",
                "start_week": week,
                "duration_weeks": remed_weeks,
            }
        )
        week += remed_weeks

    # Phase 4: Renovation work
    reno_weeks = {
        "full_renovation": 8,
        "partial_interior": 4,
        "roof": 3,
        "facade": 4,
        "bathroom": 3,
        "kitchen": 3,
        "flooring": 2,
        "windows": 2,
    }
    rw = reno_weeks.get(renovation_type, 4)
    phases.append(
        {
            "phase": "renovation",
            "description": f"Travaux de renovation ({renovation_type})",
            "start_week": week,
            "duration_weeks": rw,
        }
    )

    return phases
