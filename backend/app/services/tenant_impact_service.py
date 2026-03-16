"""
SwissBuildingOS - Tenant Impact Service

Assesses impact on tenants during pollutant remediation works:
displacement needs, communication plans, cost estimates, and portfolio exposure.

Swiss tenancy law context:
- CO Art. 259a-259i: tenant rights when premises have defects
- CO Art. 256-256b: landlord obligations (habitability, notice)
- CO Art. 266l-266o: notice periods and form requirements
- Rent reduction: proportional to impairment of use (Swiss case law)
- Minimum notice: 30 days for residential, 60 days for commercial
- Friable asbestos in habitable zone -> mandatory displacement
- Major works (CFST category 3) -> displacement likely
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.tenant_impact import (
    BuildingTenantSummary,
    CommunicationTemplate,
    CommunicationType,
    DisplacementCostEstimate,
    DisplacementNeed,
    PortfolioTenantExposure,
    TenantCommunicationPlan,
    TenantImpactAssessment,
    TenantType,
    ZoneDisplacementCost,
    ZoneTenantImpact,
)

# Zone types where tenants live/work (extended occupancy)
_HABITABLE_ZONE_TYPES = {"floor", "room", "staircase"}
_COMMERCIAL_ZONE_TYPES = {"room", "floor"}

# Material states that indicate friable / high-risk
_FRIABLE_STATES = {"friable", "friable_damaged", "degraded", "damaged"}

# Swiss daily accommodation cost estimates (CHF)
_DAILY_ACCOMMODATION_RESIDENTIAL = 150.0  # hotel/temp housing per unit
_DAILY_ACCOMMODATION_COMMERCIAL = 300.0  # temp office/commercial space

# Moving cost flat estimates (CHF)
_MOVING_COST_RESIDENTIAL = 2000.0
_MOVING_COST_COMMERCIAL = 5000.0

# Daily business interruption estimate (CHF)
_DAILY_BUSINESS_INTERRUPTION = 500.0

# Monthly rent estimate per m2 for rent loss calculation (CHF)
_MONTHLY_RENT_PER_M2 = 25.0

# Duration estimates (days) by remediation severity
_DURATION_MINOR = 7
_DURATION_MEDIUM = 21
_DURATION_MAJOR = 45


async def _load_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _load_zones_with_materials(db: AsyncSession, building_id: UUID) -> list[Zone]:
    result = await db.execute(
        select(Zone)
        .where(Zone.building_id == building_id)
        .options(selectinload(Zone.elements).selectinload(BuildingElement.materials))
    )
    return list(result.scalars().all())


async def _load_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


def _zone_has_pollutants(zone: Zone, samples: list[Sample]) -> list[dict]:
    """Collect pollutant data for a zone from materials and samples."""
    pollutants: list[dict] = []

    for element in zone.elements:
        for material in element.materials:
            if material.contains_pollutant and material.pollutant_type:
                pollutants.append(
                    {
                        "pollutant_type": material.pollutant_type,
                        "material_state": material.source,
                        "concentration": None,
                        "risk_level": None,
                        "cfst_work_category": None,
                    }
                )

    for sample in samples:
        if not sample.pollutant_type:
            continue
        if sample.location_floor and zone.name and sample.location_floor.lower() in zone.name.lower():
            pollutants.append(
                {
                    "pollutant_type": sample.pollutant_type,
                    "material_state": sample.material_state,
                    "concentration": sample.concentration,
                    "risk_level": sample.risk_level,
                    "cfst_work_category": sample.cfst_work_category,
                }
            )

    return pollutants


def _assess_displacement(
    zone_type: str,
    pollutants: list[dict],
    building_type: str | None,
) -> tuple[DisplacementNeed, int, str]:
    """
    Determine displacement need, duration, and reason for a zone.
    Returns (need, duration_days, reason).
    """
    if not pollutants:
        return DisplacementNeed.none, 0, "Aucun polluant detecte"

    habitable = zone_type in _HABITABLE_ZONE_TYPES
    worst_need = DisplacementNeed.none
    max_duration = 0
    reason_parts: list[str] = []

    for p in pollutants:
        pt = (p["pollutant_type"] or "").lower()
        state = (p["material_state"] or "").lower()
        cfst = p.get("cfst_work_category") or ""
        risk = (p.get("risk_level") or "").lower()

        need = DisplacementNeed.none
        duration = 0
        reason = ""

        # Friable asbestos in habitable zone -> mandatory displacement
        if pt == "asbestos" and state in _FRIABLE_STATES and habitable:
            need = DisplacementNeed.temporary
            duration = _DURATION_MAJOR
            reason = "Amiante friable en zone habitable - deplacement obligatoire"
        elif pt == "asbestos" and habitable:
            need = DisplacementNeed.temporary
            duration = _DURATION_MEDIUM
            reason = "Amiante non-friable en zone habitable - deplacement recommande"
        elif pt == "asbestos":
            need = DisplacementNeed.none
            duration = _DURATION_MINOR
            reason = "Amiante en zone technique - pas de deplacement"

        # CFST major works -> displacement
        elif cfst == "major" or risk == "critical":
            need = DisplacementNeed.temporary
            duration = _DURATION_MAJOR
            reason = f"Travaux majeurs (CFST) pour {pt} - deplacement necessaire"
        elif cfst == "medium" and habitable:
            need = DisplacementNeed.temporary
            duration = _DURATION_MEDIUM
            reason = f"Travaux moyens pour {pt} en zone habitable"

        # Radon above threshold in habitable
        elif pt == "radon" and habitable:
            conc = p.get("concentration") or 0
            if conc > 1000:
                need = DisplacementNeed.temporary
                duration = _DURATION_MEDIUM
                reason = f"Radon {conc} Bq/m3 - assainissement necessaire"
            elif conc > 300:
                need = DisplacementNeed.none
                duration = _DURATION_MINOR
                reason = "Radon moderement eleve - ventilation suffisante"

        # Lead / PCB in habitable
        elif pt in ("lead", "pcb") and habitable and risk in ("high", "critical"):
            need = DisplacementNeed.temporary
            duration = _DURATION_MEDIUM
            reason = f"{pt.upper()} a risque eleve en zone habitable"

        # Default: no displacement
        else:
            need = DisplacementNeed.none
            duration = _DURATION_MINOR
            reason = f"{pt} - travaux mineurs sans deplacement"

        if need.value > worst_need.value:
            worst_need = need
        if duration > max_duration:
            max_duration = duration
        if reason:
            reason_parts.append(reason)

    combined_reason = "; ".join(reason_parts) if reason_parts else "Evaluation par defaut"
    return worst_need, max_duration, combined_reason


def _estimate_rent_reduction(displacement: DisplacementNeed, zone_type: str) -> float:
    """Estimate rent reduction percentage per Swiss case law."""
    if displacement == DisplacementNeed.temporary:
        return 100.0  # Full reduction during displacement
    if displacement == DisplacementNeed.permanent:
        return 100.0
    # Minor works in habitable zones still warrant partial reduction
    if zone_type in _HABITABLE_ZONE_TYPES:
        return 10.0
    return 0.0


def _notice_period_days(building_type: str | None) -> int:
    """Swiss minimum notice period: 30 days residential, 60 days commercial."""
    if building_type in ("commercial", "industrial"):
        return 60
    return 30


def _get_tenant_type(zone_type: str, building_type: str | None) -> TenantType:
    if building_type == "commercial":
        return TenantType.commercial
    if building_type == "mixed" and zone_type in _COMMERCIAL_ZONE_TYPES:
        return TenantType.mixed
    return TenantType.residential


async def assess_tenant_impact(
    db: AsyncSession,
    building_id: UUID,
) -> TenantImpactAssessment:
    """
    Assess tenant impact during remediation: displacement per zone,
    duration, accommodation cost, rent reduction, notice period.
    """
    building = await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    samples = await _load_samples(db, building_id)

    zone_impacts: list[ZoneTenantImpact] = []
    total_cost = 0.0
    max_duration = 0
    displacement_count = 0

    for zone in zones:
        pollutants = _zone_has_pollutants(zone, samples)
        displacement, duration, reason = _assess_displacement(zone.zone_type, pollutants, building.building_type)
        rent_reduction = _estimate_rent_reduction(displacement, zone.zone_type)
        notice = _notice_period_days(building.building_type)

        # Accommodation cost
        if displacement != DisplacementNeed.none:
            daily_rate = (
                _DAILY_ACCOMMODATION_COMMERCIAL
                if building.building_type in ("commercial", "industrial")
                else _DAILY_ACCOMMODATION_RESIDENTIAL
            )
            accom_cost = daily_rate * duration
            displacement_count += 1
        else:
            accom_cost = 0.0

        total_cost += accom_cost
        if duration > max_duration:
            max_duration = duration

        zone_impacts.append(
            ZoneTenantImpact(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                displacement_needed=displacement,
                estimated_duration_days=duration,
                alternative_accommodation_cost_chf=accom_cost,
                rent_reduction_percent=rent_reduction,
                notice_period_days=notice,
                reason=reason,
            )
        )

    return TenantImpactAssessment(
        building_id=building_id,
        building_type=building.building_type,
        zones=zone_impacts,
        total_zones=len(zones),
        zones_requiring_displacement=displacement_count,
        total_estimated_cost_chf=total_cost,
        max_duration_days=max_duration,
        assessed_at=datetime.now(UTC),
    )


async def generate_tenant_communication_plan(
    db: AsyncSession,
    building_id: UUID,
) -> TenantCommunicationPlan:
    """
    Generate timeline of required tenant notifications:
    initial notice, work start, progress updates, re-entry clearance.
    """
    building = await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    samples = await _load_samples(db, building_id)

    # Determine if any zone requires displacement
    has_displacement = False
    max_duration = 0
    for zone in zones:
        pollutants = _zone_has_pollutants(zone, samples)
        displacement, duration, _ = _assess_displacement(zone.zone_type, pollutants, building.building_type)
        if displacement != DisplacementNeed.none:
            has_displacement = True
        if duration > max_duration:
            max_duration = duration

    notice_days = _notice_period_days(building.building_type)

    communications: list[CommunicationTemplate] = []
    step = 1

    # 1. Initial notice (mandatory)
    communications.append(
        CommunicationTemplate(
            step=step,
            communication_type=CommunicationType.initial_notice,
            title="Avis de travaux d'assainissement",
            description=(
                "Notification initiale aux locataires informant des travaux prevus, "
                "de leur nature, de la duree estimee et des mesures de protection."
            ),
            days_before_work=notice_days,
            required=True,
            recipients="all_tenants",
            template_sections=[
                "Objet des travaux",
                "Nature des polluants concernes",
                "Duree estimee des travaux",
                "Mesures de protection pour les occupants",
                "Personne de contact",
            ],
        )
    )
    step += 1

    # 2. Displacement notice (if needed)
    if has_displacement:
        communications.append(
            CommunicationTemplate(
                step=step,
                communication_type=CommunicationType.initial_notice,
                title="Avis de relogement temporaire",
                description=(
                    "Notification detaillee du relogement temporaire: "
                    "modalites, duree, prise en charge des frais, reduction de loyer."
                ),
                days_before_work=notice_days,
                required=True,
                recipients="affected_tenants",
                template_sections=[
                    "Zones concernees par le deplacement",
                    "Duree du relogement",
                    "Solution d'hebergement proposee",
                    "Prise en charge des frais de demenagement",
                    "Reduction de loyer applicable",
                    "Droits du locataire (CO Art. 259a-259i)",
                ],
            )
        )
        step += 1

    # 3. Work start notification
    communications.append(
        CommunicationTemplate(
            step=step,
            communication_type=CommunicationType.work_start,
            title="Debut des travaux d'assainissement",
            description=(
                "Notification du demarrage effectif des travaux, "
                "rappel des consignes de securite et des restrictions d'acces."
            ),
            days_before_work=3,
            required=True,
            recipients="all_tenants",
            template_sections=[
                "Date de debut effectif",
                "Horaires des travaux",
                "Zones a acces restreint",
                "Consignes de securite",
                "Numeros d'urgence",
            ],
        )
    )
    step += 1

    # 4. Progress updates (every 2 weeks for longer works)
    if max_duration > 14:
        num_updates = max(1, max_duration // 14)
        for i in range(num_updates):
            communications.append(
                CommunicationTemplate(
                    step=step,
                    communication_type=CommunicationType.progress_update,
                    title=f"Mise a jour de l'avancement - semaine {(i + 1) * 2}",
                    description=(
                        "Point d'avancement sur les travaux: "
                        "etat d'avancement, respect du planning, eventuels ajustements."
                    ),
                    days_after_start=14 * (i + 1),
                    required=False,
                    recipients="all_tenants",
                    template_sections=[
                        "Etat d'avancement",
                        "Respect du calendrier",
                        "Ajustements eventuels",
                        "Prochaines etapes",
                    ],
                )
            )
            step += 1

    # 5. Re-entry clearance
    communications.append(
        CommunicationTemplate(
            step=step,
            communication_type=CommunicationType.reentry_clearance,
            title="Autorisation de reintegration",
            description=(
                "Notification de fin de travaux et autorisation de reintegrer les lieux. "
                "Inclut les resultats des mesures de controle post-travaux."
            ),
            days_after_start=max_duration if max_duration > 0 else None,
            required=True,
            recipients="all_tenants" if has_displacement else "affected_tenants",
            template_sections=[
                "Confirmation de fin de travaux",
                "Resultats des mesures de controle",
                "Zones liberees",
                "Conditions de reintegration",
                "Rapport de controle disponible",
            ],
        )
    )

    return TenantCommunicationPlan(
        building_id=building_id,
        communications=communications,
        total_communications=len(communications),
        earliest_notice_days_before=notice_days,
        generated_at=datetime.now(UTC),
    )


async def estimate_displacement_costs(
    db: AsyncSession,
    building_id: UUID,
) -> DisplacementCostEstimate:
    """
    Financial impact: temporary relocation, rent loss, moving costs,
    business interruption. Per-zone and total.
    """
    building = await _load_building(db, building_id)
    zones = await _load_zones_with_materials(db, building_id)
    samples = await _load_samples(db, building_id)

    zone_costs: list[ZoneDisplacementCost] = []
    totals = {
        "relocation": 0.0,
        "rent_loss": 0.0,
        "moving": 0.0,
        "business": 0.0,
    }

    for zone in zones:
        pollutants = _zone_has_pollutants(zone, samples)
        displacement, duration, _ = _assess_displacement(zone.zone_type, pollutants, building.building_type)
        tenant_type = _get_tenant_type(zone.zone_type, building.building_type)

        if displacement == DisplacementNeed.none:
            zone_costs.append(
                ZoneDisplacementCost(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    zone_type=zone.zone_type,
                    tenant_type=tenant_type,
                    duration_days=duration,
                )
            )
            continue

        # Temporary relocation cost
        daily_rate = (
            _DAILY_ACCOMMODATION_COMMERCIAL
            if tenant_type == TenantType.commercial
            else _DAILY_ACCOMMODATION_RESIDENTIAL
        )
        relocation = daily_rate * duration

        # Rent loss (surface-based estimate)
        surface = zone.surface_area_m2 or 50.0  # default 50m2
        monthly_rent = surface * _MONTHLY_RENT_PER_M2
        rent_loss = monthly_rent * (duration / 30.0)

        # Moving costs
        moving = _MOVING_COST_COMMERCIAL if tenant_type == TenantType.commercial else _MOVING_COST_RESIDENTIAL
        # Two moves: out + back
        moving_total = moving * 2

        # Business interruption (commercial only)
        business = 0.0
        if tenant_type in (TenantType.commercial, TenantType.mixed):
            business = _DAILY_BUSINESS_INTERRUPTION * duration

        subtotal = relocation + rent_loss + moving_total + business

        totals["relocation"] += relocation
        totals["rent_loss"] += rent_loss
        totals["moving"] += moving_total
        totals["business"] += business

        zone_costs.append(
            ZoneDisplacementCost(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                tenant_type=tenant_type,
                temporary_relocation_chf=relocation,
                rent_loss_chf=rent_loss,
                moving_costs_chf=moving_total,
                business_interruption_chf=business,
                subtotal_chf=subtotal,
                duration_days=duration,
            )
        )

    grand_total = sum(totals.values())

    return DisplacementCostEstimate(
        building_id=building_id,
        zones=zone_costs,
        total_temporary_relocation_chf=totals["relocation"],
        total_rent_loss_chf=totals["rent_loss"],
        total_moving_costs_chf=totals["moving"],
        total_business_interruption_chf=totals["business"],
        grand_total_chf=grand_total,
        estimated_at=datetime.now(UTC),
    )


async def get_portfolio_tenant_exposure(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioTenantExposure:
    """
    Organization-level: total tenants affected, total displacement cost,
    buildings requiring tenant action, timeline pressure.
    """
    from app.models.organization import Organization
    from app.services.building_data_loader import load_org_buildings

    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise ValueError(f"Organization {org_id} not found")

    buildings = await load_org_buildings(db, org_id)

    building_summaries: list[BuildingTenantSummary] = []
    total_affected_zones = 0
    total_cost = 0.0
    action_count = 0
    max_timeline = 0

    for bldg in buildings:
        try:
            impact = await assess_tenant_impact(db, bldg.id)
        except ValueError:
            continue

        requires_action = impact.zones_requiring_displacement > 0
        if requires_action:
            action_count += 1

        total_affected_zones += impact.zones_requiring_displacement
        total_cost += impact.total_estimated_cost_chf
        if impact.max_duration_days > max_timeline:
            max_timeline = impact.max_duration_days

        if requires_action:
            building_summaries.append(
                BuildingTenantSummary(
                    building_id=bldg.id,
                    address=bldg.address,
                    city=bldg.city,
                    zones_requiring_displacement=impact.zones_requiring_displacement,
                    estimated_cost_chf=impact.total_estimated_cost_chf,
                    max_duration_days=impact.max_duration_days,
                    requires_tenant_action=True,
                )
            )

    # Sort by cost descending
    building_summaries.sort(key=lambda b: b.estimated_cost_chf, reverse=True)

    return PortfolioTenantExposure(
        organization_id=org_id,
        total_buildings=len(buildings),
        buildings_requiring_action=action_count,
        total_tenants_affected_zones=total_affected_zones,
        total_displacement_cost_chf=total_cost,
        buildings=building_summaries,
        timeline_pressure_days=max_timeline,
        assessed_at=datetime.now(UTC),
    )
