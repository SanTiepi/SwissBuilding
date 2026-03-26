"""Instant Card service — decision-grade building intelligence aggregation.

Lot B: Truth → Decision graph (5 questions structure + neighbor signals)
Lot C: Decision → Execution graph (subsidies, ROI, insurance, renovation plan)

Pure read — delegates to existing services.
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.post_works_link import PostWorksLink
from app.models.sample import Sample
from app.models.source_snapshot import BuildingSourceSnapshot
from app.schemas.instant_card import (
    EvidenceByNature,
    ExecutionSection,
    InstantCardResult,
    NextAction,
    ResidualMaterial,
    SubsidyRef,
    TrustMeta,
    WhatBlocks,
    WhatIsReusable,
    WhatIsRisky,
    WhatToDoNext,
    WhatWeKnow,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _build_what_we_know(
    db: AsyncSession,
    building: Building,
    passport: dict | None,
) -> WhatWeKnow:
    """Assemble the what_we_know section from building + passport + snapshots."""
    identity = {
        "egid": building.egid,
        "egrid": building.egrid,
        "address": building.address,
        "postal_code": building.postal_code,
        "city": building.city,
        "canton": building.canton,
        "lat": building.latitude,
        "lon": building.longitude,
    }
    physical = {
        "construction_year": building.construction_year,
        "renovation_year": building.renovation_year,
        "building_type": building.building_type,
        "floors_above": building.floors_above,
        "floors_below": building.floors_below,
        "surface_area_m2": building.surface_area_m2,
        "volume_m3": building.volume_m3,
    }

    # Environment + energy from latest source snapshots
    environment: dict = {}
    energy: dict = {}
    snap_result = await db.execute(
        select(BuildingSourceSnapshot)
        .where(BuildingSourceSnapshot.building_id == building.id)
        .order_by(BuildingSourceSnapshot.fetched_at.desc())
    )
    for snap in snap_result.scalars().all():
        nd = snap.normalized_data or {}
        if snap.source_category == "environment" and not environment:
            environment = nd
        elif snap.source_category == "energy" and not energy:
            energy = nd

    # Diagnostics summary from passport
    diagnostics: dict = {}
    if passport:
        diagnostics = {
            "evidence_coverage": passport.get("evidence_coverage", {}),
            "pollutant_coverage": passport.get("pollutant_coverage", {}),
            "diagnostic_publications": passport.get("diagnostic_publications", {}),
        }

    # Residual materials from post-works + samples
    residual_materials = await _collect_residual_materials(db, building.id)

    return WhatWeKnow(
        identity=identity,
        physical=physical,
        environment=environment,
        energy=energy,
        diagnostics=diagnostics,
        residual_materials=residual_materials,
    )


async def _collect_residual_materials(
    db: AsyncSession,
    building_id: UUID,
) -> list[ResidualMaterial]:
    """Derive residual materials from post-works + diagnostic samples + interventions."""
    residuals: list[ResidualMaterial] = []

    # 1. From post-works links: check residual_risks in grade_delta
    pw_result = await db.execute(
        select(PostWorksLink)
        .join(Intervention, PostWorksLink.intervention_id == Intervention.id)
        .where(
            Intervention.building_id == building_id,
            PostWorksLink.status == "finalized",
        )
    )
    for pw in pw_result.scalars().all():
        residual_risks = pw.residual_risks or []
        for rr in residual_risks:
            if isinstance(rr, dict):
                residuals.append(
                    ResidualMaterial(
                        material_type=rr.get("material_type", "unknown"),
                        location=rr.get("location"),
                        status=rr.get("status", "present"),
                        last_verified=(pw.finalized_at.isoformat() if pw.finalized_at else None),
                        source="post_works",
                    )
                )

    # 2. From samples with threshold exceeded but no completed remediation
    sample_result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
            Sample.threshold_exceeded.is_(True),
        )
    )
    # Check for completed remediation interventions
    remediation_result = await db.execute(
        select(Intervention.intervention_type)
        .where(
            Intervention.building_id == building_id,
            Intervention.intervention_type == "remediation",
            Intervention.status == "completed",
        )
        .distinct()
    )
    has_remediation = remediation_result.scalars().first() is not None

    if not has_remediation:
        seen: set[str] = set()
        for sample in sample_result.scalars().all():
            ptype = sample.pollutant_type or "unknown"
            if ptype not in seen:
                seen.add(ptype)
                loc_parts = [sample.location_floor, sample.location_room, sample.location_detail]
                location_str = ", ".join(p for p in loc_parts if p) or None
                residuals.append(
                    ResidualMaterial(
                        material_type=ptype,
                        location=location_str,
                        status="present",
                        source="diagnostic_sample",
                    )
                )

    return residuals


def _build_what_is_risky(
    decision_view: object | None,
    passport: dict | None,
) -> WhatIsRisky:
    """Assemble risk section from decision view + passport."""
    pollutant_risk: dict = {}
    environmental_risk: dict = {}
    compliance_gaps: list[dict] = []

    if passport:
        pollutant_risk = passport.get("pollutant_coverage", {})
        blind_spots = passport.get("blind_spots", {})
        if blind_spots.get("total_open", 0) > 0:
            compliance_gaps.append(
                {
                    "type": "blind_spots",
                    "count": blind_spots["total_open"],
                    "blocking": blind_spots.get("blocking", 0),
                }
            )
        contradictions = passport.get("contradictions", {})
        if contradictions.get("unresolved", 0) > 0:
            compliance_gaps.append(
                {
                    "type": "contradictions",
                    "count": contradictions["unresolved"],
                }
            )

    if decision_view is not None:
        environmental_risk = {"blockers_count": len(getattr(decision_view, "blockers", []))}

    return WhatIsRisky(
        pollutant_risk=pollutant_risk,
        environmental_risk=environmental_risk,
        compliance_gaps=compliance_gaps,
    )


def _build_what_blocks(decision_view: object | None) -> WhatBlocks:
    """Assemble blockers from decision view."""
    procedural_blockers: list[dict] = []
    missing_proof: list[dict] = []
    overdue_obligations: list[dict] = []

    if decision_view is not None:
        for b in getattr(decision_view, "blockers", []):
            item = {"id": b.id, "title": b.title, "category": b.category}
            if b.category == "procedure_blocked":
                procedural_blockers.append(item)
            elif b.category == "unresolved_unknown":
                missing_proof.append(item)
            elif b.category == "overdue_obligation":
                overdue_obligations.append(item)
            else:
                procedural_blockers.append(item)

    return WhatBlocks(
        procedural_blockers=procedural_blockers,
        missing_proof=missing_proof,
        overdue_obligations=overdue_obligations,
    )


def _build_what_to_do_next(
    suggestions: list | None,
    decision_view: object | None,
) -> WhatToDoNext:
    """Top 3 actions from readiness advisor suggestions."""
    actions: list[NextAction] = []

    if suggestions:
        for s in suggestions[:3]:
            actions.append(
                NextAction(
                    action=s.recommended_action or s.title,
                    priority="high" if s.type == "blocker" else "medium",
                    evidence_needed=s.description if s.evidence_refs else None,
                )
            )

    # If not enough from suggestions, derive from blockers
    if len(actions) < 3 and decision_view is not None:
        for b in getattr(decision_view, "blockers", []):
            if len(actions) >= 3:
                break
            actions.append(
                NextAction(
                    action=f"Resolve: {b.title}",
                    priority="high",
                )
            )

    return WhatToDoNext(top_3_actions=actions[:3])


def _build_what_is_reusable(decision_view: object | None) -> WhatIsReusable:
    """Diagnostic publications, packs, deliveries from decision view proof chain."""
    pubs: list[dict] = []
    packs: list[dict] = []
    deliveries: list[dict] = []

    if decision_view is not None:
        for item in getattr(decision_view, "proof_chain", []):
            entry = {
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "status": item.status,
            }
            if item.entity_type == "diagnostic_publication":
                pubs.append(entry)
            elif item.entity_type == "audience_pack":
                packs.append(entry)
            elif item.entity_type == "proof_delivery":
                deliveries.append(entry)

    return WhatIsReusable(
        diagnostic_publications=pubs,
        packs_generated=packs,
        proof_deliveries=deliveries,
    )


async def _build_execution(
    db: AsyncSession,
    building_id: UUID,
) -> ExecutionSection:
    """Wire existing services into execution section (Lot C)."""
    execution = ExecutionSection()

    # --- Subsidies ---
    try:
        from app.services.subsidy_tracking_service import get_building_subsidy_eligibility

        eligibility = await get_building_subsidy_eligibility(building_id, db)
        subsidies: list[SubsidyRef] = []
        for prog in eligibility.eligible_programs:
            subsidies.append(
                SubsidyRef(
                    program=prog.name,
                    amount=prog.max_amount_chf,
                    requirements=prog.requirements,
                )
            )
        execution.subsidies = subsidies
        execution.renovation_plan_10y = {
            "total_subsidy": eligibility.total_potential_funding,
            "priority": eligibility.recommended_priority,
        }
    except Exception:
        logger.debug("Subsidy data unavailable for building %s", building_id, exc_info=True)

    # --- ROI ---
    try:
        from app.services.cost_benefit_analysis_service import analyze_intervention_roi

        roi_report = await analyze_intervention_roi(db, building_id)
        if roi_report.interventions:
            total_cost = sum(i.remediation_cost_chf for i in roi_report.interventions)
            total_npv = sum(i.npv_10y for i in roi_report.interventions)
            best_payback = min(
                (i.payback_years for i in roi_report.interventions if i.payback_years > 0),
                default=0,
            )
            execution.roi_renovation = {
                "payback_years": best_payback,
                "npv": total_npv,
                "total_cost": total_cost,
            }
            # Build renovation plan items from interventions
            items = []
            for i in roi_report.interventions:
                items.append(
                    {
                        "pollutant": i.pollutant,
                        "cost_chf": i.remediation_cost_chf,
                        "risk_reduction_annual": i.risk_reduction_value_chf,
                        "priority": i.priority,
                    }
                )
            execution.renovation_plan_10y["items"] = items
            execution.renovation_plan_10y["total_cost"] = total_cost
            execution.renovation_plan_10y["net_cost"] = total_cost - execution.renovation_plan_10y.get(
                "total_subsidy", 0
            )

            # Sequence recommendation from priority ordering
            phases = {}
            sorted_items = sorted(roi_report.interventions, key=lambda x: x.priority)
            for idx, item in enumerate(sorted_items[:3]):
                phases[f"phase_{idx + 1}"] = {
                    "pollutant": item.pollutant,
                    "action": f"Remediate {item.pollutant}",
                    "cost": item.remediation_cost_chf,
                }
            execution.sequence_recommendation = phases

            # Next concrete step = highest priority intervention
            if sorted_items:
                top = sorted_items[0]
                execution.next_concrete_step = {
                    "action": f"Remediate {top.pollutant}",
                    "estimated_cost": top.remediation_cost_chf,
                    "who_to_contact": "Certified remediation contractor",
                    "deadline": None,
                }
    except Exception:
        logger.debug("ROI data unavailable for building %s", building_id, exc_info=True)

    # --- Insurance impact ---
    try:
        from app.services.insurance_risk_assessment_service import assess_building_insurance_risk

        assessment = await assess_building_insurance_risk(db, building_id)
        execution.insurance_impact = {
            "current_risk_tier": assessment.risk_tier.value
            if hasattr(assessment.risk_tier, "value")
            else str(assessment.risk_tier),
            "premium_multiplier": assessment.premium_impact_multiplier,
            "summary": assessment.summary,
        }
    except Exception:
        logger.debug("Insurance data unavailable for building %s", building_id, exc_info=True)

    # --- Energy / CO2 from enrichment snapshots ---
    try:
        snap_result = await db.execute(
            select(BuildingSourceSnapshot)
            .where(
                BuildingSourceSnapshot.building_id == building_id,
                BuildingSourceSnapshot.source_category == "energy",
            )
            .order_by(BuildingSourceSnapshot.fetched_at.desc())
            .limit(1)
        )
        snap = snap_result.scalar_one_or_none()
        if snap and snap.normalized_data:
            nd = snap.normalized_data
            if "solar_potential" in nd or "heating_type" in nd:
                execution.energy_savings = {
                    "solar_potential": nd.get("solar_potential"),
                    "heating_type": nd.get("heating_type"),
                }
    except Exception:
        logger.debug("Energy snapshot unavailable for building %s", building_id, exc_info=True)

    return execution


async def _build_evidence_by_nature(
    db: AsyncSession,
    building: Building,
) -> EvidenceByNature:
    """Group building evidence by source_class taxonomy."""
    official_truth: dict = {}
    documentary_proof: dict = {}
    observations: dict = {}
    signals: dict = {}
    inferences: dict = {}

    # Identity + physical from building model = official
    official_truth["identity"] = {
        "egid": building.egid,
        "egrid": building.egrid,
        "address": building.address,
        "postal_code": building.postal_code,
        "city": building.city,
        "canton": building.canton,
    }
    official_truth["physical"] = {
        "construction_year": building.construction_year,
        "floors_above": building.floors_above,
        "floors_below": building.floors_below,
        "parcel_number": building.parcel_number,
    }

    # Source metadata entries → classify by source_class
    source_meta = building.source_metadata_json or {}
    source_entries = source_meta.get("_source_entries", [])
    for entry in source_entries:
        sc = entry.get("source_class", "derived")
        name = entry.get("source_name", "unknown")
        if sc == "official":
            official_truth[name] = {"status": entry.get("status"), "confidence": entry.get("confidence")}
        elif sc == "documentary":
            documentary_proof[name] = {"status": entry.get("status"), "confidence": entry.get("confidence")}
        elif sc == "observed":
            observations[name] = {"status": entry.get("status"), "confidence": entry.get("confidence")}
        elif sc == "commercial":
            signals[name] = {"status": entry.get("status"), "confidence": entry.get("confidence")}
        elif sc == "derived":
            inferences[name] = {"status": entry.get("status"), "confidence": entry.get("confidence")}

    # Snapshots → classify by source_category
    snap_result = await db.execute(
        select(BuildingSourceSnapshot)
        .where(BuildingSourceSnapshot.building_id == building.id)
        .order_by(BuildingSourceSnapshot.fetched_at.desc())
    )
    for snap in snap_result.scalars().all():
        cat = snap.source_category or "unknown"
        if cat in ("environment", "energy"):
            observations[cat] = snap.normalized_data or {}
        elif cat in ("cadastre", "regulatory"):
            official_truth[cat] = snap.normalized_data or {}
        elif cat in ("market", "neighborhood"):
            signals[cat] = snap.normalized_data or {}

    # Diagnostics → documentary proof
    diag_result = await db.execute(
        select(Diagnostic).where(Diagnostic.building_id == building.id).order_by(Diagnostic.created_at.desc()).limit(5)
    )
    diags = diag_result.scalars().all()
    if diags:
        documentary_proof["diagnostics"] = {
            "count": len(list(diags)),
            "latest_status": diags[0].status if diags else None,
        }

    return EvidenceByNature(
        official_truth=official_truth,
        documentary_proof=documentary_proof,
        observations=observations,
        signals=signals,
        inferences=inferences,
    )


async def _find_neighbor_signals(
    db: AsyncSession,
    building: Building,
) -> list[dict]:
    """Find nearby buildings in the DB and surface relevant signals."""
    if not building.latitude or not building.longitude:
        return []

    # Simple approach: find buildings in the same postal code + city
    result = await db.execute(
        select(Building.id, Building.address, Building.construction_year)
        .where(
            Building.postal_code == building.postal_code,
            Building.city == building.city,
            Building.id != building.id,
        )
        .limit(5)
    )
    neighbors = []
    for row in result.all():
        neighbors.append(
            {
                "building_id": str(row[0]),
                "address": row[1],
                "construction_year": row[2],
                "signal": "same_neighborhood",
            }
        )
    return neighbors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def build_instant_card(
    db: AsyncSession,
    building_id: UUID,
) -> InstantCardResult | None:
    """Aggregate a full decision-grade instant card for a building.

    Calls into existing services:
    - passport_service → grade, pollutant coverage, evidence
    - decision_view_service → blockers, conditions, clear items, proof chain
    - readiness_advisor_service → suggestions
    - trust_annotation_service → freshness/confidence (via passport)
    - subsidy_tracking_service → subsidies
    - cost_benefit_analysis_service → ROI
    - insurance_risk_assessment_service → insurance impact

    Returns None if building does not exist.
    """
    # 0. Verify building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # 1. Passport
    passport: dict | None = None
    passport_grade = "F"
    overall_trust = 0.0
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            passport_grade = passport.get("passport_grade", "F")
            overall_trust = passport.get("knowledge_state", {}).get("overall_trust", 0.0)
    except Exception:
        logger.debug("Passport unavailable for %s", building_id, exc_info=True)

    # 2. Decision view
    decision_view = None
    try:
        from app.services.decision_view_service import get_building_decision_view

        decision_view = await get_building_decision_view(db, building_id)
    except Exception:
        logger.debug("Decision view unavailable for %s", building_id, exc_info=True)

    # 3. Readiness advisor suggestions
    suggestions: list = []
    try:
        from app.services.readiness_advisor_service import get_suggestions

        suggestions = await get_suggestions(db, building_id)
    except Exception:
        logger.debug("Readiness suggestions unavailable for %s", building_id, exc_info=True)

    # 4. Build 5-question structure
    what_we_know = await _build_what_we_know(db, building, passport)
    what_is_risky = _build_what_is_risky(decision_view, passport)
    what_blocks = _build_what_blocks(decision_view)
    what_to_do_next = _build_what_to_do_next(suggestions, decision_view)
    what_is_reusable = _build_what_is_reusable(decision_view)

    # 5. Execution section (Lot C)
    execution = await _build_execution(db, building_id)

    # 6. Trust metadata
    trust_freshness = "unknown"
    trust_trend: str | None = None
    if passport:
        ks = passport.get("knowledge_state", {})
        trust_trend = ks.get("trend")
        # Freshness from latest diagnostic
        ec = passport.get("evidence_coverage", {})
        latest_diag = ec.get("latest_diagnostic_date")
        if latest_diag:
            try:
                from app.services.trust_annotation_service import annotate_publication_freshness

                dt = datetime.fromisoformat(latest_diag)
                fa = annotate_publication_freshness(dt)
                trust_freshness = fa.state
            except Exception:
                pass

    trust = TrustMeta(
        freshness=trust_freshness,
        confidence="high" if overall_trust >= 0.7 else "medium" if overall_trust >= 0.4 else "low",
        overall_trust=overall_trust,
        trend=trust_trend,
    )

    # 7. Evidence by nature (source_class grouping)
    evidence_by_nature = await _build_evidence_by_nature(db, building)

    # 8. Safe-to-start status
    safe_to_start_data: dict = {}
    try:
        from app.services.safe_to_start_service import compute_safe_to_start

        sts_result = await compute_safe_to_start(db, building_id)
        if sts_result:
            safe_to_start_data = sts_result.model_dump(mode="json")
    except Exception:
        logger.debug("Safe-to-start unavailable for %s", building_id, exc_info=True)

    # 9. Neighbor signals
    neighbor_signals = await _find_neighbor_signals(db, building)

    return InstantCardResult(
        building_id=building_id,
        passport_grade=passport_grade,
        what_we_know=what_we_know,
        evidence_by_nature=evidence_by_nature,
        safe_to_start=safe_to_start_data,
        what_is_risky=what_is_risky,
        what_blocks=what_blocks,
        what_to_do_next=what_to_do_next,
        what_is_reusable=what_is_reusable,
        execution=execution,
        trust=trust,
        neighbor_signals=neighbor_signals,
    )
