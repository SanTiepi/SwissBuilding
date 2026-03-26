"""Instant Card API — address preview + building card + source snapshots."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.address_preview import (
    AddressPreviewRequest,
    AddressPreviewResult,
    ComplianceSection,
    EnergySection,
    EnvironmentSection,
    FinancialSection,
    IdentitySection,
    InstantCardResult,
    LifecycleSection,
    MetadataSection,
    NarrativeSection,
    PhysicalSection,
    RenovationSection,
    RiskSection,
    ScoresSection,
    SourceSnapshotRead,
    TransportSection,
)

router = APIRouter()


@router.post("/intelligence/address-preview", response_model=AddressPreviewResult)
async def address_preview(
    body: AddressPreviewRequest,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Preview enrichment for an address without creating a building."""
    from app.services.address_preview_service import preview_address

    result = await preview_address(
        db,
        body.address,
        postal_code=body.postal_code,
        city=body.city,
    )
    await db.commit()
    return result


@router.get("/buildings/{building_id}/instant-card", response_model=InstantCardResult)
async def get_instant_card(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated instant card for an existing building.

    Merges data from:
    1. Building model fields (authoritative)
    2. source_metadata_json (enrichment data)
    3. Latest BuildingSourceSnapshots (normalized)
    4. Computed scores
    """
    from app.models.building import Building
    from app.models.source_snapshot import BuildingSourceSnapshot

    stmt = select(Building).where(Building.id == building_id)
    row = await db.execute(stmt)
    building = row.scalar_one_or_none()
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")

    meta = building.source_metadata_json or {}

    # Fetch latest snapshots for this building
    snap_stmt = (
        select(BuildingSourceSnapshot)
        .where(BuildingSourceSnapshot.building_id == building_id)
        .order_by(BuildingSourceSnapshot.fetched_at.desc())
    )
    snap_rows = await db.execute(snap_stmt)
    snapshots = snap_rows.scalars().all()

    # Index snapshots by source_name (latest first due to ordering)
    snap_map: dict[str, dict] = {}
    for s in snapshots:
        if s.source_name not in snap_map:
            snap_map[s.source_name] = s.normalized_data or {}

    sources_used = list(snap_map.keys())

    # Build identity from authoritative fields
    identity = IdentitySection(
        egid=building.egid,
        egrid=building.egrid,
        parcel=building.parcel_number,
        address_normalized=building.address,
        lat=building.latitude,
        lon=building.longitude,
    )

    physical = PhysicalSection(
        construction_year=building.construction_year,
        floors=building.floors_above,
        surface_m2=building.surface_area_m2,
        heating_type=meta.get("regbl_data", {}).get("heating_type_code"),
        dwellings=meta.get("regbl_data", {}).get("dwellings"),
    )

    environment = EnvironmentSection(
        radon=snap_map.get("ch.bag.radonkarte") or meta.get("radon"),
        noise=snap_map.get("ch.bafu.laerm") or meta.get("noise"),
        hazards=snap_map.get("ch.bafu.naturgefahren") or meta.get("hazards"),
        seismic=snap_map.get("ch.bafu.erdbeben") or meta.get("seismic"),
    )

    energy = EnergySection(
        solar_potential=snap_map.get("ch.bfe.solarenergie") or meta.get("solar"),
        heating_type=meta.get("regbl_data", {}).get("heating_type_code"),
        district_heating_available=bool(meta.get("thermal_networks")),
    )

    tq = snap_map.get("ch.are.gueteklassen") or meta.get("transport_quality") or {}
    stops_data = snap_map.get("ch.bav.haltestellen") or meta.get("nearest_stops") or {}
    transport_section = TransportSection(
        quality_class=tq.get("quality_class"),
        nearest_stops=stops_data if isinstance(stops_data, list) else [],
        ev_charging=meta.get("ev_charging"),
    )

    risk_section = RiskSection(
        pollutant_prediction=meta.get("pollutant_risk"),
        environmental_score=meta.get("environmental_risk_score"),
    )

    scores_data = snap_map.get("computed/scores") or {}
    scores_section = ScoresSection(
        neighborhood=meta.get("neighborhood_score") or scores_data.get("neighborhood"),
        livability=meta.get("livability_score") or scores_data.get("livability"),
        connectivity=meta.get("connectivity_score") or scores_data.get("connectivity"),
        overall_grade=meta.get("overall_intelligence", {}).get("grade") or scores_data.get("overall_grade"),
    )

    lifecycle_data = snap_map.get("computed/lifecycle") or meta.get("component_lifecycle") or {}
    lifecycle_section = LifecycleSection(
        components=lifecycle_data.get("components", []),
        critical_count=lifecycle_data.get("critical_count", 0),
        urgent_count=lifecycle_data.get("urgent_count", 0),
    )

    reno_data = snap_map.get("computed/renovation") or meta.get("renovation_plan") or {}
    renovation_section = RenovationSection(
        plan_summary=reno_data.get("plan_summary"),
        total_cost=reno_data.get("total_net_chf"),
        total_subsidy=reno_data.get("total_subsidy_chf"),
        roi_years=reno_data.get("roi_years"),
    )

    compliance_data = snap_map.get("computed/compliance") or meta.get("regulatory_compliance") or {}
    compliance_section = ComplianceSection(
        checks_count=compliance_data.get("checks_count", 0),
        non_compliant_count=compliance_data.get("non_compliant_count", 0),
        summary=compliance_data.get("summary"),
    )

    financial_data = snap_map.get("computed/financial") or meta.get("financial_impact") or {}
    financial_section = FinancialSection(
        cost_of_inaction=financial_data.get("cost_of_inaction_chf"),
        energy_savings=financial_data.get("energy_savings_chf_year"),
        value_increase=financial_data.get("value_increase_pct"),
    )

    narrative_data = snap_map.get("computed/narrative") or meta.get("building_narrative") or {}
    narrative_section = NarrativeSection(
        summary_fr=narrative_data.get("summary_fr"),
    )

    # Determine freshness from most recent snapshot
    freshness = "current"
    if snapshots:
        from app.services.address_preview_service import _freshness

        freshness = _freshness(snapshots[0].fetched_at)

    return InstantCardResult(
        building_id=building_id,
        identity=identity,
        physical=physical,
        environment=environment,
        energy=energy,
        transport=transport_section,
        risk=risk_section,
        scores=scores_section,
        lifecycle=lifecycle_section,
        renovation=renovation_section,
        compliance=compliance_section,
        financial=financial_section,
        narrative=narrative_section,
        metadata=MetadataSection(
            sources_used=sources_used,
            freshness=freshness,
            run_id=None,
        ),
    )


@router.get("/buildings/{building_id}/source-snapshots", response_model=list[SourceSnapshotRead])
async def get_source_snapshots(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all source snapshots for a building with freshness state."""
    from app.models.source_snapshot import BuildingSourceSnapshot

    stmt = (
        select(BuildingSourceSnapshot)
        .where(BuildingSourceSnapshot.building_id == building_id)
        .order_by(BuildingSourceSnapshot.fetched_at.desc())
    )
    rows = await db.execute(stmt)
    snapshots = rows.scalars().all()

    results = []
    for s in snapshots:
        # Recompute freshness dynamically
        from app.services.address_preview_service import _freshness

        fresh = _freshness(s.fetched_at) if s.fetched_at else "stale"
        results.append(
            SourceSnapshotRead(
                id=s.id,
                building_id=s.building_id,
                enrichment_run_id=s.enrichment_run_id,
                source_name=s.source_name,
                source_category=s.source_category,
                normalized_data=s.normalized_data,
                fetched_at=s.fetched_at.isoformat() if s.fetched_at else None,
                freshness_state=fresh,
                confidence=s.confidence or "medium",
            )
        )

    return results
