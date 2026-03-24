"""
SwissBuildingOS - Material Recommendation Service

Bridges diagnosis to intervention material choices with explicit evidence needs.
Given a building's diagnostic findings and planned interventions, generates
material replacement recommendations with evidence requirements and risk flags.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.material_recommendation import (
    EvidenceRequirement,
    MaterialRecommendation,
    MaterialRecommendationReport,
)
from app.services.compliance_engine import SWISS_THRESHOLDS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safe replacement material mapping per pollutant + material type
# ---------------------------------------------------------------------------

_SAFE_ALTERNATIVES: dict[str, dict[str, tuple[str, str]]] = {
    "asbestos": {
        "insulation": ("mineral_wool_new_gen", "Mineral wool (asbestos-free, post-1990 certified)"),
        "coating": ("acrylic_coating", "Acrylic-based coating (solvent-free)"),
        "pipe": ("pe_hd_pipe", "PE-HD pipe (polyethylene high-density)"),
        "wall": ("fiber_cement_af", "Fiber cement board (asbestos-free, EN 12467)"),
        "floor": ("vinyl_phthalate_free", "Vinyl flooring (phthalate-free, asbestos-free)"),
        "ceiling": ("gypsum_board", "Gypsum plasterboard (EN 520)"),
        "roof": ("fiber_cement_af", "Fiber cement roofing (asbestos-free, EN 494)"),
        "structural": ("steel_reinforced_concrete", "Steel-reinforced concrete element"),
        "duct": ("galvanized_steel_duct", "Galvanized steel ductwork"),
        "window": ("pvc_frame_lead_free", "PVC frame (lead-free stabilizers)"),
        "door": ("solid_core_composite", "Solid-core composite door panel"),
    },
    "pcb": {
        "coating": ("silicone_sealant_pcb_free", "Silicone sealant (PCB-free, EN 15651)"),
        "insulation": ("polyurethane_foam", "Polyurethane foam (PCB-free)"),
        "wall": ("acrylic_joint_filler", "Acrylic joint filler (PCB-free)"),
    },
    "lead": {
        "coating": ("water_based_paint", "Water-based paint (lead-free, EN 13300)"),
        "pipe": ("pe_hd_pipe", "PE-HD pipe (lead-free)"),
        "wall": ("lime_plaster", "Lime plaster (lead-free)"),
        "window": ("pvc_frame_lead_free", "PVC frame (lead-free stabilizers)"),
    },
    "hap": {
        "coating": ("epoxy_hap_free", "Epoxy coating (HAP-free, low-VOC)"),
        "insulation": ("expanded_polystyrene", "Expanded polystyrene (HAP-free)"),
        "floor": ("concrete_overlay", "Concrete overlay (HAP-free)"),
    },
    "radon": {
        "insulation": ("radon_barrier_membrane", "Radon barrier membrane (EN 13984)"),
        "floor": ("sealed_concrete_slab", "Sealed concrete slab with radon membrane"),
        "wall": ("radon_resistant_coating", "Radon-resistant foundation coating"),
    },
}

_DEFAULT_ALTERNATIVE = ("generic_safe_replacement", "Certified pollutant-free replacement material")

# ---------------------------------------------------------------------------
# Evidence requirements per pollutant
# ---------------------------------------------------------------------------

_EVIDENCE_REQUIREMENTS: dict[str, list[dict]] = {
    "asbestos": [
        {
            "document_type": "lab_analysis_certificate",
            "description": "Laboratory analysis confirming absence of asbestos fibers in replacement material",
            "mandatory": True,
            "legal_ref": "OTConst Art. 82, FACH 2018",
        },
        {
            "document_type": "supplier_declaration",
            "description": "Supplier declaration of asbestos-free composition",
            "mandatory": True,
            "legal_ref": "ORRChim Annexe 1.1",
        },
        {
            "document_type": "waste_elimination_plan",
            "description": "Waste elimination plan for removed asbestos material (PED)",
            "mandatory": True,
            "legal_ref": "OLED Art. 16",
        },
        {
            "document_type": "cfst_work_plan",
            "description": "CFST work plan for asbestos removal (category-dependent)",
            "mandatory": True,
            "legal_ref": "CFST 6503",
        },
    ],
    "pcb": [
        {
            "document_type": "lab_analysis_certificate",
            "description": "Laboratory analysis confirming PCB content < 50 mg/kg in replacement",
            "mandatory": True,
            "legal_ref": "ORRChim Annexe 2.15",
        },
        {
            "document_type": "supplier_declaration",
            "description": "Supplier declaration of PCB-free composition",
            "mandatory": True,
            "legal_ref": "ORRChim Annexe 2.15",
        },
        {
            "document_type": "air_quality_measurement",
            "description": "Indoor air quality measurement post-replacement (if PCB > 6000 ng/m3 prior)",
            "mandatory": False,
            "legal_ref": "OFSP recommendation",
        },
    ],
    "lead": [
        {
            "document_type": "lab_analysis_certificate",
            "description": "Laboratory analysis confirming lead content < 5000 mg/kg in replacement",
            "mandatory": True,
            "legal_ref": "ORRChim Annexe 2.18",
        },
        {
            "document_type": "supplier_declaration",
            "description": "Supplier declaration of lead-free composition",
            "mandatory": True,
            "legal_ref": "ORRChim Annexe 2.18",
        },
    ],
    "hap": [
        {
            "document_type": "lab_analysis_certificate",
            "description": "Laboratory analysis confirming HAP content < 200 mg/kg",
            "mandatory": True,
            "legal_ref": "OLED dechet special",
        },
        {
            "document_type": "supplier_declaration",
            "description": "Supplier declaration of HAP-free composition",
            "mandatory": True,
            "legal_ref": None,
        },
    ],
    "radon": [
        {
            "document_type": "radon_measurement_report",
            "description": "Post-installation radon measurement confirming < 300 Bq/m3",
            "mandatory": True,
            "legal_ref": "ORaP Art. 110",
        },
        {
            "document_type": "product_certification",
            "description": "Radon barrier product certification (EN 13984 or equivalent)",
            "mandatory": True,
            "legal_ref": "ORaP Art. 110",
        },
    ],
}

_DEFAULT_EVIDENCE = [
    {
        "document_type": "supplier_declaration",
        "description": "Supplier declaration confirming pollutant-free composition",
        "mandatory": True,
        "legal_ref": None,
    },
]

# ---------------------------------------------------------------------------
# Risk flags
# ---------------------------------------------------------------------------

_RISK_FLAGS: dict[str, list[str]] = {
    "asbestos": [
        "Worker exposure risk during removal — SUVA notification may be required",
        "Friable asbestos requires specialized containment and HEPA filtration",
    ],
    "pcb": [
        "PCB can contaminate adjacent materials during removal — containment required",
        "PCB waste classified as special waste (OLED) — licensed disposal required",
    ],
    "lead": [
        "Lead dust exposure risk during removal — respiratory protection required",
        "Lead paint in occupied buildings requires occupant protection measures",
    ],
    "hap": [
        "HAP materials require special waste disposal procedures",
    ],
    "radon": [
        "Radon mitigation effectiveness must be verified with long-term measurement",
    ],
}

# Intervention types that imply material replacement
_REPLACEMENT_INTERVENTION_TYPES = {
    "asbestos_removal",
    "decontamination",
    "demolition",
    "renovation",
    "replacement",
    "repair",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_recommendations(
    db: AsyncSession,
    building_id: UUID,
) -> MaterialRecommendationReport:
    """Generate material replacement recommendations for a building.

    Analyzes pollutant-containing materials linked to planned/in-progress
    interventions and produces safe alternative recommendations with
    evidence requirements.

    Raises ValueError if the building does not exist.
    """
    # 0. Verify building exists
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    # 1. Load planned/in-progress interventions
    interventions = await _load_active_interventions(db, building_id)

    # 2. Load pollutant-containing materials for this building
    pollutant_materials = await _load_pollutant_materials(db, building_id)

    # 3. Load positive samples for risk context
    positive_samples = await _load_positive_samples(db, building_id)

    # 4. Generate recommendations
    recommendations: list[MaterialRecommendation] = []

    for material in pollutant_materials:
        pollutant = (material.pollutant_type or "").lower()
        if not pollutant:
            continue

        mat_type = (material.material_type or "").lower()
        risk_level = _assess_risk_level(material, positive_samples)
        alt_type, alt_desc = _get_safe_alternative(pollutant, mat_type)
        evidence = _get_evidence_requirements(pollutant)
        flags = _get_risk_flags(pollutant, material, risk_level)

        recommendations.append(
            MaterialRecommendation(
                original_material_type=material.material_type or "unknown",
                original_pollutant=pollutant,
                recommended_material=alt_desc,
                recommended_material_type=alt_type,
                reason=_build_reason(pollutant, mat_type, risk_level),
                risk_level=risk_level,
                evidence_requirements=evidence,
                risk_flags=flags,
            )
        )

    # 5. Build summary
    summary = _build_summary(len(interventions), len(pollutant_materials), len(recommendations))

    return MaterialRecommendationReport(
        building_id=str(building_id),
        intervention_count=len(interventions),
        pollutant_material_count=len(pollutant_materials),
        recommendations=recommendations,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_active_interventions(db: AsyncSession, building_id: UUID) -> list[Intervention]:
    """Load planned or in-progress interventions for a building."""
    result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status.in_(["planned", "in_progress"]),
            Intervention.intervention_type.in_(_REPLACEMENT_INTERVENTION_TYPES),
        )
    )
    return list(result.scalars().all())


async def _load_pollutant_materials(db: AsyncSession, building_id: UUID) -> list[Material]:
    """Load materials flagged as containing pollutants for a building."""
    result = await db.execute(
        select(Material)
        .join(BuildingElement, Material.element_id == BuildingElement.id)
        .join(Zone, BuildingElement.zone_id == Zone.id)
        .where(
            Zone.building_id == building_id,
            Material.contains_pollutant.is_(True),
        )
    )
    return list(result.scalars().all())


async def _load_positive_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    """Load positive samples from building diagnostics."""
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Sample.threshold_exceeded.is_(True),
        )
    )
    return list(result.scalars().all())


def _assess_risk_level(material: Material, samples: list[Sample]) -> str:
    """Determine risk level for a pollutant-containing material."""
    # If linked to a sample, use the sample's risk level
    if material.sample_id:
        for sample in samples:
            if sample.id == material.sample_id:
                return sample.risk_level or "medium"

    # If confirmed pollutant, higher risk
    if material.pollutant_confirmed:
        return "high"

    # Unconfirmed pollutant presence
    return "medium"


def _get_safe_alternative(pollutant: str, material_type: str) -> tuple[str, str]:
    """Look up a safe replacement material for a pollutant + material type combo."""
    pollutant_alts = _SAFE_ALTERNATIVES.get(pollutant, {})
    return pollutant_alts.get(material_type, _DEFAULT_ALTERNATIVE)


def _get_evidence_requirements(pollutant: str) -> list[EvidenceRequirement]:
    """Get evidence document requirements for a pollutant replacement."""
    entries = _EVIDENCE_REQUIREMENTS.get(pollutant, _DEFAULT_EVIDENCE)
    return [EvidenceRequirement(**e) for e in entries]


def _get_risk_flags(pollutant: str, material: Material, risk_level: str) -> list[str]:
    """Get risk flags for a material replacement."""
    flags = list(_RISK_FLAGS.get(pollutant, []))

    if risk_level == "critical":
        flags.append("CRITICAL: Immediate action required — concentration significantly exceeds threshold")

    if material.pollutant_confirmed and risk_level in ("high", "critical"):
        flags.append("Pollutant presence confirmed by laboratory analysis")

    return flags


def _build_reason(pollutant: str, material_type: str, risk_level: str) -> str:
    """Build a human-readable reason for the recommendation."""
    thresholds = SWISS_THRESHOLDS.get(pollutant, {})
    first_ref = None
    for entry in thresholds.values():
        first_ref = entry.get("legal_ref")
        if first_ref:
            break

    base = f"Material type '{material_type}' contains {pollutant} (risk: {risk_level})"
    if first_ref:
        base += f" — regulatory reference: {first_ref}"
    return base


def _build_summary(intervention_count: int, material_count: int, recommendation_count: int) -> str:
    """Build a summary string for the report."""
    if recommendation_count == 0:
        if material_count == 0:
            return "No pollutant-containing materials identified in this building."
        return (
            f"{material_count} pollutant-containing material(s) identified "
            "but no active interventions require material replacement recommendations."
        )

    return (
        f"{recommendation_count} material replacement recommendation(s) generated "
        f"from {material_count} pollutant-containing material(s) across "
        f"{intervention_count} active intervention(s). "
        "Each recommendation includes required evidence documentation."
    )
