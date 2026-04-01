"""
SwissBuildingOS - Building Age Intelligence Service (Programme S/W)

Age-based intelligence combining construction year with Swiss regulatory
history, pollutant timelines, and energy norms. Unlike building_age_analysis_service
(which classifies eras and hotspots), this service produces a comprehensive
intelligence profile for decision support.

Era timeline for Swiss construction:
  - Pre-1950: lead paint era, minimal insulation, no radon protection
  - 1950-1960: early asbestos adoption, lead paint still common
  - 1960-1975: peak asbestos and PCB, mass construction boom
  - 1975-1990: declining asbestos (banned 1990), PCB phaseout (~1986), HAP
  - 1990-2000: post-ban, early Minergie, first energy regs
  - 2000+: modern standards, Minergie-P, low pollutant risk
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

# ---------------------------------------------------------------------------
# Era definitions with comprehensive intelligence
# ---------------------------------------------------------------------------

_ERA_PROFILES: dict[str, dict] = {
    "pre_1950": {
        "era": "pre_1950",
        "era_label": "Avant 1950 — Plomb et matériaux anciens",
        "expected_pollutants": [
            {
                "type": "lead",
                "probability": 0.85,
                "typical_materials": [
                    "Peinture intérieure au plomb",
                    "Peinture extérieure au plomb",
                    "Mastic de vitrage au plomb",
                    "Canalisations en plomb",
                ],
            },
            {
                "type": "hap",
                "probability": 0.5,
                "typical_materials": [
                    "Étanchéité goudron",
                    "Revêtements bitumineux",
                ],
            },
            {
                "type": "radon",
                "probability": 0.4,
                "typical_materials": [
                    "Fondation sans barrière radon",
                    "Cave non ventilée",
                ],
            },
            {
                "type": "asbestos",
                "probability": 0.15,
                "typical_materials": [
                    "Isolation de conduites (rare)",
                ],
            },
        ],
        "typical_issues": [
            "Peintures au plomb sur murs et boiseries",
            "Absence d'isolation thermique",
            "Ventilation naturelle insuffisante",
            "Fondations sans protection radon",
            "Installations électriques vétustes",
        ],
        "regulatory_era": "Pré-réglementaire",
        "energy_era": "Aucune norme énergétique",
        "recommended_diagnostics": [
            {"type": "lead", "urgency": "high", "reason": "Probabilité élevée de peinture au plomb"},
            {"type": "hap", "urgency": "medium", "reason": "Goudron et bitume potentiels"},
            {"type": "radon", "urgency": "medium", "reason": "Absence de barrière radon"},
            {"type": "asbestos", "urgency": "low", "reason": "Amiante rare mais possible"},
        ],
    },
    "1950_1960": {
        "era": "1950_1960",
        "era_label": "1950-1960 — Début de l'amiante",
        "expected_pollutants": [
            {
                "type": "asbestos",
                "probability": 0.6,
                "typical_materials": [
                    "Isolation de conduites",
                    "Plaques Eternit (toiture)",
                    "Dalles de sol vinyle-amiante",
                ],
            },
            {
                "type": "lead",
                "probability": 0.7,
                "typical_materials": [
                    "Peinture intérieure au plomb",
                    "Mastic de vitrage",
                ],
            },
            {
                "type": "hap",
                "probability": 0.4,
                "typical_materials": [
                    "Colle à parquet noire",
                    "Étanchéité bitumineuse",
                ],
            },
            {
                "type": "radon",
                "probability": 0.35,
                "typical_materials": [
                    "Fondation standard",
                ],
            },
        ],
        "typical_issues": [
            "Premiers usages d'amiante dans l'isolation",
            "Peintures au plomb encore courantes",
            "Isolation thermique minimale",
            "Double vitrage inexistant",
        ],
        "regulatory_era": "Pré-OTConst",
        "energy_era": "Aucune norme énergétique",
        "recommended_diagnostics": [
            {"type": "asbestos", "urgency": "high", "reason": "Amiante probable dans isolation"},
            {"type": "lead", "urgency": "high", "reason": "Peintures au plomb courantes"},
            {"type": "hap", "urgency": "medium", "reason": "Colles et étanchéité à vérifier"},
        ],
    },
    "1960_1975": {
        "era": "1960_1975",
        "era_label": "1960-1975 — Pic amiante et PCB",
        "expected_pollutants": [
            {
                "type": "asbestos",
                "probability": 0.9,
                "typical_materials": [
                    "Flocage coupe-feu",
                    "Isolation de conduites",
                    "Dalles de sol vinyle-amiante",
                    "Plaques Eternit façade/toiture",
                    "Panneaux coupe-feu",
                    "Colles de carrelage",
                ],
            },
            {
                "type": "pcb",
                "probability": 0.8,
                "typical_materials": [
                    "Joints élastiques de fenêtres",
                    "Joints de dilatation",
                    "Mastics de façade",
                ],
            },
            {
                "type": "lead",
                "probability": 0.5,
                "typical_materials": [
                    "Couches de peinture anciennes",
                    "Canalisations d'eau",
                ],
            },
            {
                "type": "hap",
                "probability": 0.55,
                "typical_materials": [
                    "Colle à parquet noire",
                    "Étanchéité bitumineuse",
                ],
            },
            {
                "type": "radon",
                "probability": 0.3,
                "typical_materials": [
                    "Fondation — protection variable",
                ],
            },
        ],
        "typical_issues": [
            "Usage massif d'amiante sous toutes formes",
            "PCB dans les mastics de joints courants",
            "Construction en série — matériaux standardisés",
            "Ponts thermiques importants",
            "Ventilation mécanique absente",
        ],
        "regulatory_era": "Pré-OTConst (OTConst Art. 60a, 82-86)",
        "energy_era": "Aucune norme énergétique",
        "recommended_diagnostics": [
            {
                "type": "asbestos",
                "urgency": "critical",
                "reason": "Pic d'utilisation — diagnostic complet obligatoire avant travaux",
            },
            {"type": "pcb", "urgency": "critical", "reason": "PCB probable dans joints (seuil ORRChim 50 mg/kg)"},
            {"type": "lead", "urgency": "medium", "reason": "Peintures au plomb possibles sous couches récentes"},
            {"type": "hap", "urgency": "medium", "reason": "HAP dans colles et étanchéité"},
        ],
    },
    "1975_1990": {
        "era": "1975_1990",
        "era_label": "1975-1990 — Déclin amiante, transition",
        "expected_pollutants": [
            {
                "type": "asbestos",
                "probability": 0.5,
                "typical_materials": [
                    "Dalles de sol (fin de production)",
                    "Plaques Eternit",
                    "Isolation résiduelle",
                ],
            },
            {
                "type": "pcb",
                "probability": 0.45,
                "typical_materials": [
                    "Joints de fenêtres (stock jusqu'à ~1986)",
                    "Mastics élastiques",
                ],
            },
            {
                "type": "hap",
                "probability": 0.3,
                "typical_materials": [
                    "Colles anciennes",
                    "Étanchéité résiduelle",
                ],
            },
            {
                "type": "lead",
                "probability": 0.2,
                "typical_materials": [
                    "Couches de peinture anciennes",
                ],
            },
            {
                "type": "radon",
                "probability": 0.25,
                "typical_materials": [
                    "Fondation — pré-norme SIA 180",
                ],
            },
        ],
        "typical_issues": [
            "Amiante en déclin mais pas encore interdit (1990)",
            "Stock de PCB utilisé jusqu'à ~1986",
            "Premières normes d'isolation (insuffisantes)",
            "Fenêtres simple ou double vitrage basique",
        ],
        "regulatory_era": "Transition pré-ban (interdiction amiante CH 1990)",
        "energy_era": "Premières normes SIA (isolation minimale)",
        "recommended_diagnostics": [
            {"type": "asbestos", "urgency": "high", "reason": "Amiante possible — interdit seulement en 1990"},
            {"type": "pcb", "urgency": "high", "reason": "PCB stock utilisé jusqu'à 1986"},
            {"type": "hap", "urgency": "low", "reason": "HAP en déclin"},
        ],
    },
    "1990_2000": {
        "era": "1990_2000",
        "era_label": "1990-2000 — Post-interdiction, premières normes",
        "expected_pollutants": [
            {
                "type": "radon",
                "probability": 0.2,
                "typical_materials": [
                    "Fondation — selon géologie locale",
                ],
            },
            {
                "type": "asbestos",
                "probability": 0.05,
                "typical_materials": [],
            },
            {
                "type": "pcb",
                "probability": 0.05,
                "typical_materials": [],
            },
        ],
        "typical_issues": [
            "Risque polluants minimal",
            "Isolation conforme normes 1990s",
            "Double vitrage standard",
            "Premières pompes à chaleur",
        ],
        "regulatory_era": "Post-ban amiante (1990), PCB-free",
        "energy_era": "SIA 380/1 (premières normes énergétiques fédérales)",
        "recommended_diagnostics": [
            {"type": "radon", "urgency": "low", "reason": "Vérification radon selon géologie"},
        ],
    },
    "post_2000": {
        "era": "post_2000",
        "era_label": "Après 2000 — Standards modernes",
        "expected_pollutants": [
            {
                "type": "radon",
                "probability": 0.15,
                "typical_materials": [
                    "Fondation — protection selon SIA 180 / zone radon",
                ],
            },
        ],
        "typical_issues": [
            "Risque polluants très faible",
            "Minergie / Minergie-P possible",
            "Triple vitrage courant",
            "Ventilation mécanique contrôlée",
        ],
        "regulatory_era": "Normes modernes (OTConst, CFST, ORRChim à jour)",
        "energy_era": "MoPEC / Minergie / nZEB",
        "recommended_diagnostics": [
            {"type": "radon", "urgency": "low", "reason": "Contrôle radon si zone à risque"},
        ],
    },
    "unknown": {
        "era": "unknown",
        "era_label": "Année de construction inconnue",
        "expected_pollutants": [
            {
                "type": "asbestos",
                "probability": 0.5,
                "typical_materials": ["À déterminer par diagnostic"],
            },
            {
                "type": "pcb",
                "probability": 0.4,
                "typical_materials": ["À déterminer par diagnostic"],
            },
            {
                "type": "lead",
                "probability": 0.4,
                "typical_materials": ["À déterminer par diagnostic"],
            },
            {
                "type": "hap",
                "probability": 0.3,
                "typical_materials": ["À déterminer par diagnostic"],
            },
            {
                "type": "radon",
                "probability": 0.3,
                "typical_materials": ["À déterminer par diagnostic"],
            },
        ],
        "typical_issues": [
            "Année de construction inconnue — tous risques possibles",
            "Diagnostic complet recommandé",
        ],
        "regulatory_era": "Inconnu",
        "energy_era": "Inconnu",
        "recommended_diagnostics": [
            {"type": "asbestos", "urgency": "high", "reason": "Année inconnue — amiante à exclure"},
            {"type": "pcb", "urgency": "high", "reason": "Année inconnue — PCB à exclure"},
            {"type": "lead", "urgency": "medium", "reason": "Année inconnue — plomb à vérifier"},
            {"type": "hap", "urgency": "medium", "reason": "Année inconnue — HAP à vérifier"},
            {"type": "radon", "urgency": "medium", "reason": "Radon à mesurer indépendamment de l'âge"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_era(year: int | None) -> str:
    """Classify construction year into fine-grained era."""
    if year is None:
        return "unknown"
    if year < 1950:
        return "pre_1950"
    if year < 1960:
        return "1950_1960"
    if year < 1975:
        return "1960_1975"
    if year < 1990:
        return "1975_1990"
    if year < 2000:
        return "1990_2000"
    return "post_2000"


# ---------------------------------------------------------------------------
# FN1: compute_age_risk_profile
# ---------------------------------------------------------------------------


async def compute_age_risk_profile(db: AsyncSession, building_id: UUID) -> dict:
    """Comprehensive risk profile based on construction era.

    Combines era-based pollutant intelligence with:
    - Expected pollutant list with probabilities
    - Typical construction issues for the era
    - Regulatory context (which laws applied at construction time)
    - Energy norm context
    - Recommended diagnostics with urgency
    - Count of similar buildings in the system
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    era_key = _classify_era(building.construction_year)
    profile = _ERA_PROFILES[era_key]

    # Count similar-era buildings in the system
    if building.construction_year is not None:
        era_ranges = {
            "pre_1950": (0, 1950),
            "1950_1960": (1950, 1960),
            "1960_1975": (1960, 1975),
            "1975_1990": (1975, 1990),
            "1990_2000": (1990, 2000),
            "post_2000": (2000, 9999),
        }
        lo, hi = era_ranges.get(era_key, (0, 9999))
        similar_stmt = (
            select(func.count())
            .select_from(Building)
            .where(
                Building.id != building_id,
                Building.status != "archived",
                Building.construction_year >= lo,
                Building.construction_year < hi,
            )
        )
    else:
        similar_stmt = (
            select(func.count())
            .select_from(Building)
            .where(
                Building.id != building_id,
                Building.status != "archived",
                Building.construction_year.is_(None),
            )
        )

    similar_result = await db.execute(similar_stmt)
    similar_count = similar_result.scalar() or 0

    return {
        "era": profile["era"],
        "era_label": profile["era_label"],
        "construction_year": building.construction_year,
        "expected_pollutants": profile["expected_pollutants"],
        "typical_issues": profile["typical_issues"],
        "regulatory_era": profile["regulatory_era"],
        "energy_era": profile["energy_era"],
        "recommended_diagnostics": profile["recommended_diagnostics"],
        "similar_buildings_in_system": similar_count,
    }
