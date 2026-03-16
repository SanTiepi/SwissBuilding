"""OLED-compliant waste management service.

Swiss waste regulations (OLED - Ordonnance sur les déchets):
- type_b: inert / clean construction waste
- type_e: controlled waste (e.g. HAP-contaminated)
- special: hazardous / polluted waste (asbestos, PCB > 50 mg/kg, lead > 5000 mg/kg)

Disposal cost benchmarks (CHF/ton):
- type_b: 80
- type_e: 250
- special: 800
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.waste_management import (
    BuildingWasteClassification,
    BuildingWasteForecastEntry,
    BuildingWasteVolumes,
    DisposalRoute,
    PortfolioWasteForecast,
    WasteClassificationItem,
    WastePlan,
    WasteVolumeEstimate,
)

# Cost per ton by waste category (CHF)
COST_PER_TON = {
    "type_b": 80.0,
    "type_e": 250.0,
    "special": 800.0,
}

# Density factors (tons/m³) for volume-to-weight conversion
DENSITY_FACTORS = {
    "type_b": 1.5,  # inert rubble
    "type_e": 1.3,  # controlled waste
    "special": 1.1,  # hazardous, often lighter packaged materials
}

# Depth assumption for area-to-volume conversion (meters)
DEFAULT_DEPTH_M = 0.05  # ~5cm material layer

# Packaging requirements
PACKAGING = {
    "type_b": "standard",
    "type_e": "sealed_bags",
    "special": "double_sealed_bags",
}

# Container types
CONTAINERS = {
    "type_b": "open_top",
    "type_e": "closed_container",
    "special": "hazmat_container",
}


def _classify_sample(sample: Sample) -> tuple[str, str]:
    """Classify a single sample into a waste category.

    Returns (waste_category, classification_basis).
    """
    ptype = (sample.pollutant_type or "").lower()
    conc = sample.concentration

    if ptype == "asbestos" or ptype == "amiante":
        return "special", "OLED: asbestos → special waste"

    if ptype == "pcb" and conc is not None and conc > 50:
        return "special", f"ORRChim Annexe 2.15: PCB {conc} mg/kg > 50 mg/kg → special"

    if (ptype == "lead" or ptype == "plomb") and conc is not None and conc > 5000:
        return "special", f"ORRChim Annexe 2.18: lead {conc} mg/kg > 5000 mg/kg → special"

    if ptype == "hap":
        return "type_e", "OLED: HAP → controlled waste (type_e)"

    # PCB below threshold
    if ptype == "pcb" and conc is not None and conc <= 50:
        return "type_e", f"PCB {conc} mg/kg ≤ 50 mg/kg → controlled waste"

    # Lead below threshold
    if (ptype == "lead" or ptype == "plomb") and conc is not None and conc <= 5000:
        return "type_e", f"Lead {conc} mg/kg ≤ 5000 mg/kg → controlled waste"

    return "type_b", "Clean material → inert waste (type_b)"


async def _get_building_or_raise(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_building_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    """Get all samples for a building via diagnostics."""
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


async def _get_building_zones(db: AsyncSession, building_id: UUID) -> list[Zone]:
    result = await db.execute(
        select(Zone)
        .where(Zone.building_id == building_id)
        .options(selectinload(Zone.elements).selectinload(BuildingElement.materials))
    )
    return list(result.scalars().unique().all())


async def classify_building_waste(db: AsyncSession, building_id: UUID) -> BuildingWasteClassification:
    """Classify all waste for a building based on sample analysis results."""
    await _get_building_or_raise(db, building_id)
    samples = await _get_building_samples(db, building_id)

    items: list[WasteClassificationItem] = []
    summary: dict[str, int] = {"type_b": 0, "type_e": 0, "special": 0}

    for sample in samples:
        category, basis = _classify_sample(sample)
        location = " / ".join(filter(None, [sample.location_floor, sample.location_room, sample.location_detail]))
        items.append(
            WasteClassificationItem(
                sample_id=sample.id,
                pollutant_type=sample.pollutant_type,
                concentration=sample.concentration,
                unit=sample.unit,
                waste_category=category,
                classification_basis=basis,
                location=location or None,
            )
        )
        summary[category] = summary.get(category, 0) + 1

    # Also classify materials with contains_pollutant flag
    zones = await _get_building_zones(db, building_id)
    for zone in zones:
        for element in zone.elements:
            for material in element.materials:
                if material.contains_pollutant and not material.sample_id:
                    ptype = (material.pollutant_type or "").lower()
                    if ptype in ("asbestos", "amiante"):
                        cat, basis = "special", "OLED: asbestos material → special waste"
                    elif ptype == "hap":
                        cat, basis = "type_e", "OLED: HAP material → controlled waste"
                    else:
                        cat, basis = "type_e", f"Pollutant material ({material.pollutant_type}) → controlled"
                    items.append(
                        WasteClassificationItem(
                            material_id=material.id,
                            pollutant_type=material.pollutant_type,
                            waste_category=cat,
                            classification_basis=basis,
                        )
                    )
                    summary[cat] = summary.get(cat, 0) + 1

    return BuildingWasteClassification(
        building_id=building_id,
        items=items,
        summary=summary,
        generated_at=datetime.now(UTC),
    )


def _build_disposal_routes(categories: set[str]) -> list[DisposalRoute]:
    """Build OLED-compliant disposal routes for each waste category present."""
    routes: list[DisposalRoute] = []

    if "special" in categories:
        routes.append(
            DisposalRoute(
                waste_category="special",
                disposal_method="Incinération en installation agréée OLED",
                authorized_facility_type="Installation d'élimination agréée (type spécial)",
                transport_requirements=[
                    "Bordereau de suivi des déchets spéciaux (LMD)",
                    "Transporteur agréé ADR",
                    "Emballage double sac étanche",
                ],
                documentation_required=[
                    "Bordereau de suivi OLED",
                    "Attestation d'élimination",
                    "Rapport de diagnostic amiante/polluants",
                    "Notification SUVA si amiante",
                ],
                estimated_cost_chf_per_ton=COST_PER_TON["special"],
            )
        )

    if "type_e" in categories:
        routes.append(
            DisposalRoute(
                waste_category="type_e",
                disposal_method="Élimination contrôlée en décharge type E",
                authorized_facility_type="Décharge de type E (déchets contrôlés)",
                transport_requirements=[
                    "Bordereau de suivi des déchets",
                    "Transport couvert",
                ],
                documentation_required=[
                    "Bordereau de suivi OLED",
                    "Analyse de caractérisation",
                    "Attestation d'élimination",
                ],
                estimated_cost_chf_per_ton=COST_PER_TON["type_e"],
            )
        )

    if "type_b" in categories:
        routes.append(
            DisposalRoute(
                waste_category="type_b",
                disposal_method="Recyclage ou mise en décharge type B",
                authorized_facility_type="Décharge de type B (matériaux inertes)",
                transport_requirements=[
                    "Bon de livraison standard",
                ],
                documentation_required=[
                    "Bon de livraison",
                    "Déclaration de conformité matériaux inertes",
                ],
                estimated_cost_chf_per_ton=COST_PER_TON["type_b"],
            )
        )

    return routes


async def generate_waste_plan(db: AsyncSession, building_id: UUID) -> WastePlan:
    """Generate an OLED-compliant waste management plan for a building."""
    classification = await classify_building_waste(db, building_id)
    volumes = await estimate_waste_volumes(db, building_id)

    categories_present = {item.waste_category for item in classification.items}
    if not categories_present:
        categories_present = {"type_b"}  # default: assume clean inert waste

    routes = _build_disposal_routes(categories_present)

    total_cost = 0.0
    for est in volumes.estimates:
        total_cost += est.weight_tons * COST_PER_TON.get(est.waste_category, 80.0)

    return WastePlan(
        building_id=building_id,
        disposal_routes=routes,
        total_estimated_cost_chf=round(total_cost, 2),
        regulatory_references=[
            "OLED (Ordonnance sur la limitation et l'élimination des déchets)",
            "ORRChim Annexe 2.15 (PCB: seuil 50 mg/kg)",
            "ORRChim Annexe 2.18 (Plomb: seuil 5000 mg/kg)",
            "OTConst Art. 60a, 82-86 (amiante)",
            "LMD (Mouvement des déchets spéciaux)",
        ],
        generated_at=datetime.now(UTC),
    )


async def estimate_waste_volumes(db: AsyncSession, building_id: UUID) -> BuildingWasteVolumes:
    """Estimate waste volumes per category from zones and materials."""
    classification = await classify_building_waste(db, building_id)
    zones = await _get_building_zones(db, building_id)

    # Calculate total zone area
    total_zone_area_m2 = sum(z.surface_area_m2 or 0.0 for z in zones)

    # Count items per category
    category_counts: dict[str, int] = {}
    total_items = 0
    for item in classification.items:
        category_counts[item.waste_category] = category_counts.get(item.waste_category, 0) + 1
        total_items += 1

    estimates: list[WasteVolumeEstimate] = []
    total_volume = 0.0
    total_weight = 0.0

    for category in ("type_b", "type_e", "special"):
        count = category_counts.get(category, 0)
        if count == 0 and category != "type_b":
            continue

        # Distribute zone area proportionally among categories
        if total_items > 0:
            proportion = count / total_items
        else:
            proportion = 1.0 if category == "type_b" else 0.0

        area = total_zone_area_m2 * proportion
        volume = round(area * DEFAULT_DEPTH_M, 3)
        density = DENSITY_FACTORS[category]
        weight = round(volume * density, 3)

        estimates.append(
            WasteVolumeEstimate(
                waste_category=category,
                volume_m3=volume,
                weight_tons=weight,
                density_factor=density,
                packaging_requirement=PACKAGING[category],
                container_type=CONTAINERS[category],
            )
        )
        total_volume += volume
        total_weight += weight

    # If no items at all, provide a default type_b estimate based on zone area
    if not estimates:
        volume = round(total_zone_area_m2 * DEFAULT_DEPTH_M, 3)
        density = DENSITY_FACTORS["type_b"]
        weight = round(volume * density, 3)
        estimates.append(
            WasteVolumeEstimate(
                waste_category="type_b",
                volume_m3=volume,
                weight_tons=weight,
                density_factor=density,
                packaging_requirement=PACKAGING["type_b"],
                container_type=CONTAINERS["type_b"],
            )
        )
        total_volume = volume
        total_weight = weight

    return BuildingWasteVolumes(
        building_id=building_id,
        estimates=estimates,
        total_volume_m3=round(total_volume, 3),
        total_weight_tons=round(total_weight, 3),
        generated_at=datetime.now(UTC),
    )


async def get_portfolio_waste_forecast(db: AsyncSession, org_id: UUID) -> PortfolioWasteForecast:
    """Aggregate waste forecast across all buildings in an organization."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioWasteForecast(
            organization_id=org_id,
            buildings=[],
            total_volumes_by_category={},
            total_disposal_cost_chf=0.0,
            regulatory_filing_requirements=[],
            generated_at=datetime.now(UTC),
        )

    entries: list[BuildingWasteForecastEntry] = []
    total_by_category: dict[str, float] = {"type_b": 0.0, "type_e": 0.0, "special": 0.0}
    grand_total_cost = 0.0

    for building in buildings:
        volumes = await estimate_waste_volumes(db, building.id)

        # Find earliest planned intervention
        interv_result = await db.execute(
            select(Intervention)
            .where(
                Intervention.building_id == building.id,
                Intervention.status == "planned",
            )
            .order_by(Intervention.date_start)
            .limit(1)
        )
        intervention = interv_result.scalar_one_or_none()
        planned_date = str(intervention.date_start) if intervention and intervention.date_start else None

        building_cost = 0.0
        for est in volumes.estimates:
            cost = est.weight_tons * COST_PER_TON.get(est.waste_category, 80.0)
            building_cost += cost
            total_by_category[est.waste_category] = total_by_category.get(est.waste_category, 0.0) + est.volume_m3

        grand_total_cost += building_cost

        entries.append(
            BuildingWasteForecastEntry(
                building_id=building.id,
                address=building.address,
                total_volume_m3=volumes.total_volume_m3,
                total_cost_chf=round(building_cost, 2),
                planned_intervention_date=planned_date,
            )
        )

    # Determine regulatory filing requirements
    filing_requirements: list[str] = []
    if total_by_category.get("special", 0) > 0:
        filing_requirements.append("Déclaration de mouvement de déchets spéciaux (LMD)")
        filing_requirements.append("Notification SUVA si présence d'amiante")
    if total_by_category.get("type_e", 0) > 0:
        filing_requirements.append("Bordereau de suivi déchets contrôlés")
    if any(v > 0 for v in total_by_category.values()):
        filing_requirements.append("Plan de gestion des déchets de chantier (PGDC)")

    return PortfolioWasteForecast(
        organization_id=org_id,
        buildings=entries,
        total_volumes_by_category={k: round(v, 3) for k, v in total_by_category.items()},
        total_disposal_cost_chf=round(grand_total_cost, 2),
        regulatory_filing_requirements=filing_requirements,
        generated_at=datetime.now(UTC),
    )
