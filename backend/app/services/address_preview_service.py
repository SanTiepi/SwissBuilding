"""Address preview service — enrichment without creating a building.

Runs geocode + RegBL + key layers and returns structured preview data.
Creates an EnrichmentRun (building_id=null) + SourceSnapshots for audit.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrichment_run import BuildingEnrichmentRun
from app.models.source_snapshot import BuildingSourceSnapshot
from app.schemas.address_preview import (
    AddressPreviewResult,
    ComplianceSection,
    EnergySection,
    EnvironmentSection,
    FinancialSection,
    IdentitySection,
    LifecycleSection,
    MetadataSection,
    NarrativeSection,
    PhysicalSection,
    RenovationSection,
    RiskSection,
    ScoresSection,
    TransportSection,
)

logger = logging.getLogger(__name__)

# Source name -> category mapping
SOURCE_CATEGORIES: dict[str, str] = {
    "geo.admin.ch/geocode": "identity",
    "geo.admin.ch/gwr": "identity",
    "ch.bag.radonkarte": "environment",
    "ch.bafu.laerm": "environment",
    "ch.bafu.naturgefahren": "risk",
    "ch.bfe.solarenergie": "energy",
    "ch.are.gueteklassen": "transport",
    "ch.bafu.erdbeben": "environment",
    "ch.bav.haltestellen": "transport",
    "computed/scores": "computed",
    "computed/lifecycle": "computed",
    "computed/renovation": "computed",
    "computed/compliance": "computed",
    "computed/financial": "computed",
    "computed/narrative": "computed",
    "computed/neighborhood": "computed",
}


def _freshness(fetched_at: datetime) -> str:
    """Compute freshness_state based on age."""
    now = datetime.now(UTC)
    # Handle naive datetimes (e.g. from SQLite) by assuming UTC
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    age_hours = (now - fetched_at).total_seconds() / 3600
    if age_hours < 24:
        return "current"
    if age_hours < 168:  # 7 days
        return "aging"
    return "stale"


def _confidence_for_source(source_name: str) -> str:
    """Default confidence level by source type."""
    if source_name.startswith("geo.admin.ch"):
        return "high"
    if source_name.startswith("ch."):
        return "high"
    if source_name.startswith("computed/"):
        return "medium"
    return "medium"


async def _record_snapshot(
    db: AsyncSession,
    run: BuildingEnrichmentRun,
    source_name: str,
    raw_data: Any,
    normalized_data: Any,
    *,
    building_id: Any = None,
) -> BuildingSourceSnapshot:
    """Create and persist a source snapshot."""
    now = datetime.now(UTC)
    snap = BuildingSourceSnapshot(
        building_id=building_id,
        enrichment_run_id=run.id,
        source_name=source_name,
        source_category=SOURCE_CATEGORIES.get(source_name, "identity"),
        raw_data=raw_data,
        normalized_data=normalized_data,
        fetched_at=now,
        freshness_state=_freshness(now),
        confidence=_confidence_for_source(source_name),
    )
    db.add(snap)
    return snap


async def preview_address(
    db: AsyncSession,
    address: str,
    postal_code: str | None = None,
    city: str | None = None,
) -> AddressPreviewResult:
    """Preview enrichment for an address without creating a Building.

    Returns structured AddressPreviewResult with all data found.
    Creates an EnrichmentRun with building_id=null for audit trail.
    """
    from app.services.building_enrichment_service import (
        compute_component_lifecycle,
        compute_connectivity_score,
        compute_environmental_risk_score,
        compute_livability_score,
        compute_neighborhood_score,
        compute_overall_building_intelligence_score,
        compute_pollutant_risk_prediction,
        compute_regulatory_compliance,
        estimate_financial_impact,
        fetch_natural_hazards,
        fetch_nearest_stops,
        fetch_noise_data,
        fetch_radon_risk,
        fetch_regbl_data,
        fetch_seismic_zone,
        fetch_solar_potential,
        fetch_transport_quality,
        generate_building_narrative,
        generate_renovation_plan,
        geocode_address,
    )

    start_time = time.monotonic()
    npa = postal_code or ""
    address_full = f"{address} {npa} {city or ''}".strip()

    # Create enrichment run
    run = BuildingEnrichmentRun(
        building_id=None,
        address_input=address_full,
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(run)
    await db.flush()

    sources_attempted = 0
    sources_succeeded = 0
    sources_failed = 0
    sources_used: list[str] = []
    errors: list[str] = []

    identity = IdentitySection(address_normalized=address_full)
    physical = PhysicalSection()
    environment = EnvironmentSection()
    energy = EnergySection()
    transport = TransportSection()
    risk = RiskSection()
    scores = ScoresSection()

    # --- 1. Geocode ---
    sources_attempted += 1
    try:
        geo = await geocode_address(address, npa)
        if geo.get("lat"):
            identity.lat = geo["lat"]
            identity.lon = geo.get("lon")
            identity.egid = geo.get("egid")
            sources_succeeded += 1
            sources_used.append("geo.admin.ch/geocode")
            await _record_snapshot(
                db,
                run,
                "geo.admin.ch/geocode",
                geo,
                {"lat": geo["lat"], "lon": geo.get("lon"), "egid": geo.get("egid")},
            )
        else:
            sources_failed += 1
    except Exception as exc:
        sources_failed += 1
        errors.append(f"geocode: {exc}")

    # --- 2. RegBL ---
    if identity.egid:
        sources_attempted += 1
        try:
            regbl = await fetch_regbl_data(identity.egid)
            if regbl:
                physical.construction_year = regbl.get("construction_year")
                physical.floors = regbl.get("floors")
                physical.dwellings = regbl.get("dwellings")
                physical.surface_m2 = regbl.get("living_area_m2") or regbl.get("ground_area_m2")
                physical.heating_type = regbl.get("heating_type_code")
                identity.egrid = regbl.get("egrid") or identity.egrid
                identity.parcel = regbl.get("parcel_number")
                energy.heating_type = regbl.get("heating_type_code")
                sources_succeeded += 1
                sources_used.append("geo.admin.ch/gwr")
                await _record_snapshot(
                    db,
                    run,
                    "geo.admin.ch/gwr",
                    regbl,
                    {
                        "construction_year": physical.construction_year,
                        "floors": physical.floors,
                        "dwellings": physical.dwellings,
                        "egrid": identity.egrid,
                    },
                )
            else:
                sources_failed += 1
        except Exception as exc:
            sources_failed += 1
            errors.append(f"regbl: {exc}")

    lat, lon = identity.lat, identity.lon

    # --- 3. Radon ---
    if lat and lon:
        sources_attempted += 1
        try:
            radon = await fetch_radon_risk(lat, lon)
            if radon:
                environment.radon = radon
                sources_succeeded += 1
                sources_used.append("ch.bag.radonkarte")
                await _record_snapshot(db, run, "ch.bag.radonkarte", radon, radon)
            else:
                sources_failed += 1
        except Exception as exc:
            sources_failed += 1
            errors.append(f"radon: {exc}")

    # --- 4. Noise ---
    if lat and lon:
        sources_attempted += 1
        try:
            noise = await fetch_noise_data(lat, lon)
            if noise:
                environment.noise = noise
                sources_succeeded += 1
                sources_used.append("ch.bafu.laerm")
                await _record_snapshot(db, run, "ch.bafu.laerm", noise, noise)
            else:
                sources_failed += 1
        except Exception as exc:
            sources_failed += 1
            errors.append(f"noise: {exc}")

    # --- 5. Natural hazards ---
    if lat and lon:
        sources_attempted += 1
        try:
            hazards = await fetch_natural_hazards(lat, lon)
            if hazards:
                environment.hazards = hazards
                sources_succeeded += 1
                sources_used.append("ch.bafu.naturgefahren")
                await _record_snapshot(db, run, "ch.bafu.naturgefahren", hazards, hazards)
            else:
                sources_failed += 1
        except Exception as exc:
            sources_failed += 1
            errors.append(f"hazards: {exc}")

    # --- 6. Solar ---
    if lat and lon:
        sources_attempted += 1
        try:
            solar = await fetch_solar_potential(lat, lon)
            if solar:
                energy.solar_potential = solar
                sources_succeeded += 1
                sources_used.append("ch.bfe.solarenergie")
                await _record_snapshot(db, run, "ch.bfe.solarenergie", solar, solar)
            else:
                sources_failed += 1
        except Exception as exc:
            sources_failed += 1
            errors.append(f"solar: {exc}")

    # --- 7. Transport quality ---
    if lat and lon:
        sources_attempted += 1
        try:
            tq = await fetch_transport_quality(lat, lon)
            if tq:
                transport.quality_class = tq.get("quality_class")
                sources_succeeded += 1
                sources_used.append("ch.are.gueteklassen")
                await _record_snapshot(
                    db,
                    run,
                    "ch.are.gueteklassen",
                    tq,
                    {"quality_class": transport.quality_class},
                )
            else:
                sources_failed += 1
        except Exception as exc:
            sources_failed += 1
            errors.append(f"transport: {exc}")

    # --- 8. Seismic ---
    if lat and lon:
        sources_attempted += 1
        try:
            seismic = await fetch_seismic_zone(lat, lon)
            if seismic:
                environment.seismic = seismic
                sources_succeeded += 1
                sources_used.append("ch.bafu.erdbeben")
                await _record_snapshot(db, run, "ch.bafu.erdbeben", seismic, seismic)
            else:
                sources_failed += 1
        except Exception as exc:
            sources_failed += 1
            errors.append(f"seismic: {exc}")

    # --- 9. Nearest stops ---
    if lat and lon:
        sources_attempted += 1
        try:
            stops = await fetch_nearest_stops(lat, lon)
            if stops:
                transport.nearest_stops = stops if isinstance(stops, list) else [stops]
                sources_succeeded += 1
                sources_used.append("ch.bav.haltestellen")
                await _record_snapshot(
                    db,
                    run,
                    "ch.bav.haltestellen",
                    stops,
                    {"count": len(transport.nearest_stops)},
                )
            else:
                sources_failed += 1
        except Exception as exc:
            sources_failed += 1
            errors.append(f"stops: {exc}")

    # --- Computed scores ---
    enrichment_meta: dict[str, Any] = {
        "radon": environment.radon or {},
        "noise": environment.noise or {},
        "hazards": environment.hazards or {},
        "solar": energy.solar_potential or {},
        "transport_quality": {"quality_class": transport.quality_class},
        "nearest_stops": transport.nearest_stops,
    }
    building_data: dict[str, Any] = {
        "construction_year": physical.construction_year,
        "lat": lat,
        "lon": lon,
        "heating_type": physical.heating_type,
        "building_type": "residential",
        "floors_above": physical.floors,
        "surface_area_m2": physical.surface_m2,
    }

    # Neighborhood score
    sources_attempted += 1
    try:
        ns = compute_neighborhood_score(enrichment_meta)
        if ns is not None:
            scores.neighborhood = ns
            sources_succeeded += 1
            sources_used.append("computed/neighborhood")
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Connectivity score
    sources_attempted += 1
    try:
        cs = compute_connectivity_score(enrichment_meta)
        if cs is not None:
            scores.connectivity = cs
            sources_succeeded += 1
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Environmental risk
    sources_attempted += 1
    try:
        ers = compute_environmental_risk_score(enrichment_meta)
        if ers is not None:
            risk.environmental_score = ers
            sources_succeeded += 1
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Livability
    sources_attempted += 1
    try:
        ls = compute_livability_score(enrichment_meta)
        if ls is not None:
            scores.livability = ls
            sources_succeeded += 1
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Pollutant risk
    sources_attempted += 1
    try:
        pr = compute_pollutant_risk_prediction(building_data)
        if pr:
            risk.pollutant_prediction = pr
            sources_succeeded += 1
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Overall intelligence grade
    sources_attempted += 1
    try:
        oi = compute_overall_building_intelligence_score(enrichment_meta)
        if oi:
            scores.overall_grade = oi.get("grade")
            sources_succeeded += 1
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Component lifecycle
    lifecycle = LifecycleSection()
    sources_attempted += 1
    try:
        lc = compute_component_lifecycle(building_data)
        if lc:
            lifecycle.components = lc.get("components", [])
            lifecycle.critical_count = lc.get("critical_count", 0)
            lifecycle.urgent_count = lc.get("urgent_count", 0)
            sources_succeeded += 1
            sources_used.append("computed/lifecycle")
            await _record_snapshot(db, run, "computed/lifecycle", None, lc)
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Renovation plan
    renovation = RenovationSection()
    sources_attempted += 1
    try:
        rp = generate_renovation_plan(building_data, enrichment_meta)
        if rp:
            renovation.plan_summary = rp.get("plan_summary")
            renovation.total_cost = rp.get("total_net_chf")
            renovation.total_subsidy = rp.get("total_subsidy_chf")
            renovation.roi_years = rp.get("roi_years")
            sources_succeeded += 1
            sources_used.append("computed/renovation")
            await _record_snapshot(db, run, "computed/renovation", None, rp)
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Compliance
    compliance = ComplianceSection()
    sources_attempted += 1
    try:
        rc = compute_regulatory_compliance(building_data, enrichment_meta)
        if rc:
            compliance.checks_count = rc.get("checks_count", 0)
            compliance.non_compliant_count = rc.get("non_compliant_count", 0)
            compliance.summary = rc.get("summary")
            sources_succeeded += 1
            sources_used.append("computed/compliance")
            await _record_snapshot(db, run, "computed/compliance", None, rc)
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Financial impact
    financial = FinancialSection()
    sources_attempted += 1
    try:
        fi = estimate_financial_impact(building_data, enrichment_meta)
        if fi:
            financial.cost_of_inaction = fi.get("cost_of_inaction_chf")
            financial.energy_savings = fi.get("energy_savings_chf_year")
            financial.value_increase = fi.get("value_increase_pct")
            sources_succeeded += 1
            sources_used.append("computed/financial")
            await _record_snapshot(db, run, "computed/financial", None, fi)
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Narrative
    narrative = NarrativeSection()
    sources_attempted += 1
    try:
        bn = generate_building_narrative(building_data, enrichment_meta)
        if bn:
            narrative.summary_fr = bn.get("summary_fr")
            sources_succeeded += 1
            sources_used.append("computed/narrative")
            await _record_snapshot(db, run, "computed/narrative", None, bn)
        else:
            sources_failed += 1
    except Exception:
        sources_failed += 1

    # Record computed scores snapshot
    await _record_snapshot(
        db,
        run,
        "computed/scores",
        None,
        {
            "neighborhood": scores.neighborhood,
            "connectivity": scores.connectivity,
            "livability": scores.livability,
            "environmental_risk": risk.environmental_score,
            "overall_grade": scores.overall_grade,
        },
    )

    # Finalize run
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    run.status = "completed"
    run.sources_attempted = sources_attempted
    run.sources_succeeded = sources_succeeded
    run.sources_failed = sources_failed
    run.duration_ms = elapsed_ms
    run.completed_at = datetime.now(UTC)
    if errors:
        run.error_summary = "; ".join(errors)

    await db.flush()

    return AddressPreviewResult(
        identity=identity,
        physical=physical,
        environment=environment,
        energy=energy,
        transport=transport,
        risk=risk,
        scores=scores,
        lifecycle=lifecycle,
        renovation=renovation,
        compliance=compliance,
        financial=financial,
        narrative=narrative,
        metadata=MetadataSection(
            sources_used=sources_used,
            freshness="current",
            run_id=run.id,
        ),
    )
