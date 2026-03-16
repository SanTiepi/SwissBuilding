"""Material Inventory Service — inventory, risk, lifecycle, and portfolio views for materials."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_element import BuildingElement
from app.models.material import Material
from app.models.zone import Zone
from app.schemas.material_inventory import (
    BuildingMaterialInventory,
    BuildingMaterialLifecycle,
    BuildingMaterialRisk,
    HighRiskMaterial,
    MaterialInventoryItem,
    MaterialLifecycleItem,
    MaterialRiskItem,
    MaterialTypeDistribution,
    MaterialTypeGroup,
    PortfolioMaterialOverview,
)
from app.services.building_data_loader import load_org_buildings

# Expected lifespans by material type (years)
_EXPECTED_LIFESPAN: dict[str, int] = {
    "concrete": 80,
    "steel": 60,
    "wood": 40,
    "glass": 30,
    "insulation": 30,
    "coating": 15,
    "sealant": 20,
    "adhesive": 25,
    "mortar": 50,
    "plaster": 40,
    "tile": 50,
    "linoleum": 25,
    "carpet": 15,
    "plastic": 30,
}

_DEFAULT_LIFESPAN = 40

# Risk weights
_CONDITION_RISK: dict[str, float] = {
    "critical": 4.0,
    "poor": 3.0,
    "fair": 2.0,
    "good": 1.0,
    "new": 0.5,
}

_POLLUTANT_TYPE_RISK: dict[str, float] = {
    "asbestos": 5.0,
    "pcb": 4.0,
    "lead": 3.5,
    "hap": 3.0,
    "radon": 2.5,
}

CURRENT_YEAR = datetime.now(UTC).year


async def _fetch_building_materials(
    db: AsyncSession, building_id: uuid.UUID
) -> list[tuple[Material, BuildingElement, Zone]]:
    """Fetch all materials for a building with their element and zone context."""
    stmt = (
        select(Material, BuildingElement, Zone)
        .join(BuildingElement, Material.element_id == BuildingElement.id)
        .join(Zone, BuildingElement.zone_id == Zone.id)
        .where(Zone.building_id == building_id)
        .order_by(Material.material_type, Material.created_at)
    )
    result = await db.execute(stmt)
    return list(result.all())


def _age_estimate(material: Material, element: BuildingElement) -> int | None:
    """Estimate material age from installation year (material or element)."""
    year = material.installation_year or element.installation_year
    if year is None:
        return None
    return max(CURRENT_YEAR - year, 0)


def _to_inventory_item(material: Material, element: BuildingElement, zone: Zone) -> MaterialInventoryItem:
    return MaterialInventoryItem(
        material_id=material.id,
        material_type=material.material_type,
        name=material.name,
        description=material.description,
        manufacturer=material.manufacturer,
        installation_year=material.installation_year,
        contains_pollutant=material.contains_pollutant or False,
        pollutant_type=material.pollutant_type,
        pollutant_confirmed=material.pollutant_confirmed or False,
        sample_id=material.sample_id,
        condition=element.condition,
        zone_id=zone.id,
        zone_name=zone.name,
        zone_type=zone.zone_type,
        element_id=element.id,
        element_name=element.name,
        element_type=element.element_type,
        age_estimate_years=_age_estimate(material, element),
    )


# ---------------------------------------------------------------------------
# FN1: get_material_inventory
# ---------------------------------------------------------------------------


async def get_material_inventory(db: AsyncSession, building_id: uuid.UUID) -> BuildingMaterialInventory:
    """Complete inventory of all materials in a building, grouped by material_type."""
    rows = await _fetch_building_materials(db, building_id)

    groups_map: dict[str, list[MaterialInventoryItem]] = {}
    for material, element, zone in rows:
        item = _to_inventory_item(material, element, zone)
        groups_map.setdefault(material.material_type, []).append(item)

    groups = [
        MaterialTypeGroup(
            material_type=mt,
            count=len(items),
            items=items,
            pollutant_count=sum(1 for i in items if i.contains_pollutant),
        )
        for mt, items in sorted(groups_map.items())
    ]

    return BuildingMaterialInventory(
        building_id=building_id,
        total_materials=sum(g.count for g in groups),
        groups=groups,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: assess_material_risk
# ---------------------------------------------------------------------------


def _compute_risk(material: Material, element: BuildingElement) -> tuple[float, str, list[str]]:
    """Compute risk score, level, and contributing factors for a material."""
    score = 0.0
    factors: list[str] = []

    # Condition factor
    condition = (element.condition or "").lower()
    cond_score = _CONDITION_RISK.get(condition, 1.5)
    score += cond_score
    if cond_score >= 3.0:
        factors.append(f"poor_condition:{condition}")

    # Age factor
    age = _age_estimate(material, element)
    if age is not None:
        lifespan = _EXPECTED_LIFESPAN.get(material.material_type, _DEFAULT_LIFESPAN)
        age_ratio = age / lifespan if lifespan > 0 else 1.0
        if age_ratio >= 1.0:
            score += 3.0
            factors.append("beyond_expected_lifespan")
        elif age_ratio >= 0.75:
            score += 2.0
            factors.append("approaching_end_of_life")
        elif age_ratio >= 0.5:
            score += 1.0

    # Pollutant factor
    if material.contains_pollutant:
        poll_risk = _POLLUTANT_TYPE_RISK.get((material.pollutant_type or "").lower(), 2.0)
        score += poll_risk
        factors.append(f"contains_pollutant:{material.pollutant_type or 'unknown'}")
        if material.pollutant_confirmed:
            score += 1.0
            factors.append("pollutant_confirmed")

    # Determine level
    if score >= 10.0:
        level = "critical"
    elif score >= 7.0:
        level = "high"
    elif score >= 4.0:
        level = "medium"
    else:
        level = "low"

    return round(score, 2), level, factors


async def assess_material_risk(db: AsyncSession, building_id: uuid.UUID) -> BuildingMaterialRisk:
    """Risk rating per material with priority ranking for intervention."""
    rows = await _fetch_building_materials(db, building_id)

    items: list[MaterialRiskItem] = []
    for material, element, zone in rows:
        risk_score, risk_level, risk_factors = _compute_risk(material, element)
        items.append(
            MaterialRiskItem(
                material_id=material.id,
                material_type=material.material_type,
                name=material.name,
                zone_name=zone.name,
                condition=element.condition,
                age_estimate_years=_age_estimate(material, element),
                contains_pollutant=material.contains_pollutant or False,
                pollutant_type=material.pollutant_type,
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors=risk_factors,
                intervention_priority=0,  # set below
            )
        )

    # Sort by risk score descending and assign priority
    items.sort(key=lambda x: x.risk_score, reverse=True)
    for idx, item in enumerate(items, start=1):
        item.intervention_priority = idx

    level_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in items:
        if item.risk_level in level_counts:
            level_counts[item.risk_level] += 1

    return BuildingMaterialRisk(
        building_id=building_id,
        assessed_count=len(items),
        critical_count=level_counts["critical"],
        high_count=level_counts["high"],
        medium_count=level_counts["medium"],
        low_count=level_counts["low"],
        materials=items,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: get_material_lifecycle
# ---------------------------------------------------------------------------


def _degradation_status(age: int | None, lifespan: int) -> str:
    if age is None:
        return "unknown"
    ratio = age / lifespan if lifespan > 0 else 1.0
    if ratio >= 1.0:
        return "end_of_life"
    if ratio >= 0.75:
        return "degrading"
    if ratio >= 0.5:
        return "aging"
    return "healthy"


async def get_material_lifecycle(db: AsyncSession, building_id: uuid.UUID) -> BuildingMaterialLifecycle:
    """Age analysis: materials approaching end-of-life, degradation, maintenance schedule."""
    rows = await _fetch_building_materials(db, building_id)

    items: list[MaterialLifecycleItem] = []
    end_of_life_count = 0
    approaching_end_count = 0
    healthy_count = 0

    for material, element, zone in rows:
        age = _age_estimate(material, element)
        lifespan = _EXPECTED_LIFESPAN.get(material.material_type, _DEFAULT_LIFESPAN)
        status = _degradation_status(age, lifespan)
        remaining = None
        eol = False
        next_maintenance = None

        if age is not None:
            remaining = max(lifespan - age, 0)
            eol = remaining == 0
            # Maintenance every 25% of lifespan
            maintenance_interval = max(lifespan // 4, 1)
            install_year = material.installation_year or element.installation_year
            if install_year is not None:
                last_maint = install_year
                while last_maint + maintenance_interval <= CURRENT_YEAR:
                    last_maint += maintenance_interval
                next_maintenance = last_maint + maintenance_interval

        if eol:
            end_of_life_count += 1
        elif status == "degrading":
            approaching_end_count += 1
        elif status in ("healthy", "aging"):
            healthy_count += 1

        items.append(
            MaterialLifecycleItem(
                material_id=material.id,
                material_type=material.material_type,
                name=material.name,
                zone_name=zone.name,
                installation_year=material.installation_year or element.installation_year,
                age_estimate_years=age,
                expected_lifespan_years=lifespan,
                remaining_years=remaining,
                end_of_life=eol,
                degradation_status=status,
                next_maintenance_year=next_maintenance,
            )
        )

    return BuildingMaterialLifecycle(
        building_id=building_id,
        total_materials=len(items),
        end_of_life_count=end_of_life_count,
        approaching_end_count=approaching_end_count,
        healthy_count=healthy_count,
        materials=items,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_material_overview
# ---------------------------------------------------------------------------


async def get_portfolio_material_overview(db: AsyncSession, org_id: uuid.UUID) -> PortfolioMaterialOverview:
    """Org-level material overview: counts, pollutant %, highest-risk, patterns."""
    # Get all buildings belonging to org members
    buildings = await load_org_buildings(db, org_id)

    total_materials = 0
    pollutant_count = 0
    type_counts: dict[str, int] = {}
    type_pollutant_counts: dict[str, int] = {}
    all_risk_items: list[HighRiskMaterial] = []

    for building in buildings:
        rows = await _fetch_building_materials(db, building.id)
        for material, element, _zone in rows:
            total_materials += 1
            mt = material.material_type
            type_counts[mt] = type_counts.get(mt, 0) + 1

            if material.contains_pollutant:
                pollutant_count += 1
                type_pollutant_counts[mt] = type_pollutant_counts.get(mt, 0) + 1

            risk_score, risk_level, _ = _compute_risk(material, element)
            if risk_score >= 7.0:
                all_risk_items.append(
                    HighRiskMaterial(
                        material_id=material.id,
                        material_type=material.material_type,
                        name=material.name,
                        building_id=building.id,
                        building_address=building.address,
                        risk_score=risk_score,
                        risk_level=risk_level,
                    )
                )

    all_risk_items.sort(key=lambda x: x.risk_score, reverse=True)

    type_distribution = [
        MaterialTypeDistribution(
            material_type=mt,
            count=count,
            pollutant_count=type_pollutant_counts.get(mt, 0),
            pollutant_percentage=round(type_pollutant_counts.get(mt, 0) / count * 100, 1) if count > 0 else 0.0,
        )
        for mt, count in sorted(type_counts.items())
    ]

    return PortfolioMaterialOverview(
        organization_id=org_id,
        total_buildings=len(buildings),
        total_materials=total_materials,
        pollutant_material_count=pollutant_count,
        pollutant_percentage=round(pollutant_count / total_materials * 100, 1) if total_materials > 0 else 0.0,
        type_distribution=type_distribution,
        highest_risk_materials=all_risk_items[:20],
        generated_at=datetime.now(UTC),
    )
