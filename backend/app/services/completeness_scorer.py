"""
Completeness Scorer — 16-dimension dossier completeness assessment.

Each building is scored across 16 dimensions with weighted max points.
Overall score = weighted average across all dimensions (0-100).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.completeness_report import CompletenessReport
from app.models.completeness_score import CompletenessScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.zone import Zone

# ---------------------------------------------------------------------------
# Dimension definitions: (key, label, max_weight)
# ---------------------------------------------------------------------------

DIMENSIONS: list[tuple[str, str, int]] = [
    ("building_metadata", "Building metadata", 20),
    ("energy_data", "Energy data", 15),
    ("hazardous_materials", "Hazardous materials", 20),
    ("structural_health", "Structural health", 15),
    ("environmental_exposure", "Environmental exposure", 15),
    ("regulatory_compliance", "Regulatory compliance", 20),
    ("materials_inventory", "Materials inventory", 15),
    ("repair_history", "Repair/renovation history", 10),
    ("owner_occupant", "Owner/occupant info", 10),
    ("legal_documents", "Legal documents", 15),
    ("photos_evidence", "Photos/evidence", 10),
    ("field_observations", "Field observations", 10),
    ("third_party_inspections", "Third-party inspections", 10),
    ("remediation_plan", "Remediation plan", 10),
    ("post_works", "Post-works documentation", 10),
    ("maintenance_manual", "Maintenance/operations manual", 5),
]

TOTAL_WEIGHT = sum(w for _, _, w in DIMENSIONS)


# ---------------------------------------------------------------------------
# Individual dimension scorers
# ---------------------------------------------------------------------------


def _score_building_metadata(building: Building) -> tuple[float, list[dict], list[dict]]:
    """Score building metadata completeness (address, owner, area, year, stories)."""
    fields = {
        "address": (building.address, "critical"),
        "city": (building.city, "critical"),
        "canton": (building.canton, "important"),
        "postal_code": (building.postal_code, "important"),
        "construction_year": (building.construction_year, "critical"),
        "building_type": (building.building_type, "important"),
        "total_area": (getattr(building, "total_area", None), "nice_to_have"),
        "stories": (getattr(building, "stories", None), "nice_to_have"),
        "owner_name": (getattr(building, "owner_name", None), "important"),
        "egid": (getattr(building, "egid", None), "nice_to_have"),
    }
    present = sum(1 for v, _ in fields.values() if v)
    total = len(fields)
    score = (present / total) * 100 if total else 0
    missing = [{"field": k, "importance": imp} for k, (v, imp) in fields.items() if not v]
    actions = [{"action": f"Add {m['field']}", "priority": m["importance"], "effort": "low"} for m in missing]
    return score, missing, actions


def _score_energy_data(building: Building, documents: list[Document]) -> tuple[float, list[dict], list[dict]]:
    """Score energy data (CECB certificate, energy labels)."""
    checks = []
    has_cecb = getattr(building, "cecb_label", None) is not None
    checks.append(("cecb_label", has_cecb, "critical"))
    energy_docs = [
        d for d in documents if (d.document_type or "").lower() in ("cecb", "energy_certificate", "energy_audit")
    ]
    checks.append(("energy_certificate", len(energy_docs) > 0, "important"))
    has_heating = getattr(building, "heating_type", None) is not None
    checks.append(("heating_type", has_heating, "nice_to_have"))

    present = sum(1 for _, ok, _ in checks if ok)
    score = (present / len(checks)) * 100
    missing = [{"field": k, "importance": imp} for k, ok, imp in checks if not ok]
    actions = [{"action": f"Provide {m['field']}", "priority": m["importance"], "effort": "medium"} for m in missing]
    return score, missing, actions


def _score_hazardous_materials(
    samples: list[Sample], diagnostics: list[Diagnostic]
) -> tuple[float, list[dict], list[dict]]:
    """Score hazardous materials coverage (asbestos, lead, PCB, HAP, radon)."""
    pollutants = {"asbestos", "pcb", "lead", "hap", "radon"}
    evaluated = {(s.pollutant_type or "").lower() for s in samples} & pollutants
    has_diagnostic = len(diagnostics) > 0
    has_completed = any(d.status in ("completed", "validated") for d in diagnostics)

    points = 0.0
    total = 4.0  # diagnostic exists, diagnostic complete, pollutant coverage, lab results
    missing = []
    if has_diagnostic:
        points += 1
    else:
        missing.append({"field": "diagnostic", "importance": "critical"})
    if has_completed:
        points += 1
    else:
        missing.append({"field": "completed_diagnostic", "importance": "critical"})

    pollutant_ratio = len(evaluated) / len(pollutants)
    points += pollutant_ratio
    for p in pollutants - evaluated:
        missing.append({"field": f"{p}_test", "importance": "critical"})

    with_results = [s for s in samples if s.concentration is not None]
    if samples:
        points += len(with_results) / len(samples)
    else:
        missing.append({"field": "lab_results", "importance": "critical"})

    score = (points / total) * 100
    actions = [{"action": f"Obtain {m['field']}", "priority": m["importance"], "effort": "high"} for m in missing]
    return score, missing, actions


def _score_structural_health(building: Building) -> tuple[float, list[dict], list[dict]]:
    """Score structural health data availability."""
    checks = [
        ("sinistralite_score", getattr(building, "sinistralite_score", None) is not None, "important"),
        ("last_inspection_date", getattr(building, "last_inspection_date", None) is not None, "important"),
        ("structural_condition", getattr(building, "structural_condition", None) is not None, "nice_to_have"),
    ]
    present = sum(1 for _, ok, _ in checks if ok)
    score = (present / len(checks)) * 100
    missing = [{"field": k, "importance": imp} for k, ok, imp in checks if not ok]
    actions = [{"action": f"Assess {m['field']}", "priority": m["importance"], "effort": "medium"} for m in missing]
    return score, missing, actions


def _score_environmental_exposure(building: Building) -> tuple[float, list[dict], list[dict]]:
    """Score environmental exposure data (noise, flood risk, contamination, radon)."""
    checks = [
        ("noise_exposure", getattr(building, "noise_exposure", None) is not None, "important"),
        ("flood_risk", getattr(building, "flood_risk", None) is not None, "important"),
        ("contaminated_site", getattr(building, "contaminated_site", None) is not None, "important"),
        ("radon_zone", getattr(building, "radon_zone", None) is not None, "important"),
    ]
    present = sum(1 for _, ok, _ in checks if ok)
    score = (present / len(checks)) * 100 if checks else 0
    missing = [{"field": k, "importance": imp} for k, ok, imp in checks if not ok]
    actions = [{"action": f"Check {m['field']}", "priority": m["importance"], "effort": "low"} for m in missing]
    return score, missing, actions


def _score_regulatory_compliance(
    samples: list[Sample], diagnostics: list[Diagnostic]
) -> tuple[float, list[dict], list[dict]]:
    """Score regulatory compliance checks (OTConst, CFST, LCI)."""
    checks = []
    # SUVA notification if asbestos positive
    asbestos_pos = [s for s in samples if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded]
    if asbestos_pos:
        suva_ok = any(d.suva_notification_required and d.suva_notification_date for d in diagnostics)
        checks.append(("suva_notification", suva_ok, "critical"))

    # Work category for asbestos
    if asbestos_pos:
        cat_ok = all(s.cfst_work_category for s in asbestos_pos)
        checks.append(("work_category", cat_ok, "critical"))

    # Waste classification for positive samples
    positive = [s for s in samples if s.threshold_exceeded]
    if positive:
        waste_ok = all(s.waste_disposal_type for s in positive)
        checks.append(("waste_classification", waste_ok, "important"))

    if not checks:
        return 100.0, [], []

    present = sum(1 for _, ok, _ in checks if ok)
    score = (present / len(checks)) * 100
    missing = [{"field": k, "importance": imp} for k, ok, imp in checks if not ok]
    actions = [{"action": f"Complete {m['field']}", "priority": m["importance"], "effort": "medium"} for m in missing]
    return score, missing, actions


def _score_materials_inventory(elements: list[BuildingElement]) -> tuple[float, list[dict], list[dict]]:
    """Score materials inventory (building elements documented)."""
    if not elements:
        return (
            0.0,
            [{"field": "building_elements", "importance": "important"}],
            [{"action": "Document building elements", "priority": "important", "effort": "high"}],
        )
    # More elements = better, cap at 10 for 100%
    score = min(100.0, (len(elements) / 10) * 100)
    missing = [] if score >= 100 else [{"field": "more_elements", "importance": "nice_to_have"}]
    actions = (
        [{"action": "Document additional elements", "priority": "nice_to_have", "effort": "medium"}] if missing else []
    )
    return score, missing, actions


def _score_repair_history(interventions: list[Intervention]) -> tuple[float, list[dict], list[dict]]:
    """Score repair/renovation history."""
    if not interventions:
        return (
            0.0,
            [{"field": "intervention_history", "importance": "important"}],
            [{"action": "Record past interventions", "priority": "important", "effort": "medium"}],
        )
    completed = [i for i in interventions if i.status == "completed"]
    score = min(100.0, (len(completed) / max(len(interventions), 1)) * 100)
    missing = []
    if not completed:
        missing.append({"field": "completed_interventions", "importance": "nice_to_have"})
    return score, missing, []


def _score_owner_occupant(building: Building) -> tuple[float, list[dict], list[dict]]:
    """Score owner/occupant info."""
    checks = [
        ("owner_name", getattr(building, "owner_name", None) is not None, "important"),
        ("contact_email", getattr(building, "contact_email", None) is not None, "nice_to_have"),
        ("contact_phone", getattr(building, "contact_phone", None) is not None, "nice_to_have"),
    ]
    present = sum(1 for _, ok, _ in checks if ok)
    score = (present / len(checks)) * 100
    missing = [{"field": k, "importance": imp} for k, ok, imp in checks if not ok]
    actions = [{"action": f"Add {m['field']}", "priority": m["importance"], "effort": "low"} for m in missing]
    return score, missing, actions


def _score_legal_documents(documents: list[Document]) -> tuple[float, list[dict], list[dict]]:
    """Score legal documents (deed, permits, insurance)."""
    legal_types = {"property_deed", "building_permit", "insurance", "permit", "legal"}
    found = {(d.document_type or "").lower() for d in documents} & legal_types
    score = min(100.0, (len(found) / 3) * 100)  # 3 key types = 100%
    all_missing = legal_types - found
    missing = [{"field": t, "importance": "important"} for t in sorted(all_missing)[:3]]
    actions = [{"action": f"Upload {m['field']}", "priority": m["importance"], "effort": "low"} for m in missing]
    return score, missing, actions


def _score_photos_evidence(documents: list[Document]) -> tuple[float, list[dict], list[dict]]:
    """Score photos/evidence (photo documents)."""
    photos = [d for d in documents if (d.document_type or "").lower() in ("photo", "image", "evidence_photo")]
    score = min(100.0, (len(photos) / 5) * 100)  # 5 photos = 100%
    missing = [] if score >= 100 else [{"field": "photos", "importance": "nice_to_have"}]
    actions = [{"action": "Upload building photos", "priority": "nice_to_have", "effort": "low"}] if missing else []
    return score, missing, actions


def _score_field_observations(actions_list: list[ActionItem]) -> tuple[float, list[dict], list[dict]]:
    """Score field observations (inspector notes, risk flags via actions)."""
    observations = [a for a in actions_list if a.source_type in ("inspection", "observation", "field_note")]
    if not observations:
        # Fallback: any action = some observation
        score = min(100.0, (len(actions_list) / 3) * 100) if actions_list else 0.0
    else:
        score = min(100.0, (len(observations) / 3) * 100)
    missing = [] if score >= 100 else [{"field": "field_observations", "importance": "nice_to_have"}]
    actions = [{"action": "Add field observations", "priority": "nice_to_have", "effort": "medium"}] if missing else []
    return score, missing, actions


def _score_third_party_inspections(diagnostics: list[Diagnostic]) -> tuple[float, list[dict], list[dict]]:
    """Score third-party inspections."""
    external = [d for d in diagnostics if d.status in ("completed", "validated")]
    score = min(100.0, (len(external) / 2) * 100)  # 2 completed = 100%
    missing = [] if score >= 100 else [{"field": "independent_assessment", "importance": "nice_to_have"}]
    actions = (
        [{"action": "Commission independent assessment", "priority": "nice_to_have", "effort": "high"}]
        if missing
        else []
    )
    return score, missing, actions


def _score_remediation_plan(
    interventions: list[Intervention], documents: list[Document]
) -> tuple[float, list[dict], list[dict]]:
    """Score remediation plan (proposals, timelines)."""
    planned = [i for i in interventions if i.status in ("planned", "in_progress")]
    remed_docs = [d for d in documents if (d.document_type or "").lower() in ("remediation_plan", "quote", "proposal")]
    points = 0.0
    total = 2.0
    missing = []
    if planned:
        points += 1
    else:
        missing.append({"field": "remediation_plan", "importance": "important"})
    if remed_docs:
        points += 1
    else:
        missing.append({"field": "contractor_proposal", "importance": "important"})
    score = (points / total) * 100
    actions = [{"action": f"Prepare {m['field']}", "priority": m["importance"], "effort": "high"} for m in missing]
    return score, missing, actions


def _score_post_works(
    interventions: list[Intervention], documents: list[Document]
) -> tuple[float, list[dict], list[dict]]:
    """Score post-works documentation (completion certificates, photos)."""
    completed_interventions = [i for i in interventions if i.status == "completed"]
    post_docs = [
        d
        for d in documents
        if (d.document_type or "").lower() in ("completion_certificate", "post_work_photo", "handover")
    ]
    points = 0.0
    total = 2.0
    missing = []
    if completed_interventions:
        points += 1
    else:
        missing.append({"field": "completion_records", "importance": "important"})
    if post_docs:
        points += 1
    else:
        missing.append({"field": "post_work_documents", "importance": "nice_to_have"})
    score = (points / total) * 100
    actions = [{"action": f"Upload {m['field']}", "priority": m["importance"], "effort": "low"} for m in missing]
    return score, missing, actions


def _score_maintenance_manual(documents: list[Document]) -> tuple[float, list[dict], list[dict]]:
    """Score maintenance/operations manual."""
    manuals = [
        d for d in documents if (d.document_type or "").lower() in ("maintenance_manual", "operations_manual", "manual")
    ]
    score = 100.0 if manuals else 0.0
    missing = [] if manuals else [{"field": "maintenance_manual", "importance": "nice_to_have"}]
    actions = [{"action": "Upload maintenance manual", "priority": "nice_to_have", "effort": "low"}] if missing else []
    return score, missing, actions


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _score_dimension(
    dim_key: str,
    building: Building,
    diagnostics: list[Diagnostic],
    samples: list[Sample],
    documents: list[Document],
    elements: list[BuildingElement],
    interventions: list[Intervention],
    actions_list: list[ActionItem],
    plans: list[TechnicalPlan],
) -> tuple[float, list[dict], list[dict]]:
    """Dispatch to the correct dimension scorer."""
    scorers = {
        "building_metadata": lambda: _score_building_metadata(building),
        "energy_data": lambda: _score_energy_data(building, documents),
        "hazardous_materials": lambda: _score_hazardous_materials(samples, diagnostics),
        "structural_health": lambda: _score_structural_health(building),
        "environmental_exposure": lambda: _score_environmental_exposure(building),
        "regulatory_compliance": lambda: _score_regulatory_compliance(samples, diagnostics),
        "materials_inventory": lambda: _score_materials_inventory(elements),
        "repair_history": lambda: _score_repair_history(interventions),
        "owner_occupant": lambda: _score_owner_occupant(building),
        "legal_documents": lambda: _score_legal_documents(documents),
        "photos_evidence": lambda: _score_photos_evidence(documents),
        "field_observations": lambda: _score_field_observations(actions_list),
        "third_party_inspections": lambda: _score_third_party_inspections(diagnostics),
        "remediation_plan": lambda: _score_remediation_plan(interventions, documents),
        "post_works": lambda: _score_post_works(interventions, documents),
        "maintenance_manual": lambda: _score_maintenance_manual(documents),
    }
    scorer = scorers.get(dim_key)
    if scorer is None:
        return 0.0, [], []
    return scorer()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_color(score: float) -> str:
    """Return color code for a score: green/yellow/orange/red."""
    if score >= 90:
        return "green"
    if score >= 70:
        return "yellow"
    if score >= 50:
        return "orange"
    return "red"


async def calculate_completeness(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """
    Calculate 16-dimension completeness for a building.

    Returns dict with overall_score, dimensions list, missing_items, actions.
    """
    # Fetch building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return {
            "building_id": str(building_id),
            "overall_score": 0.0,
            "dimensions": [],
            "missing_items_count": 0,
            "urgent_actions": 0,
            "recommended_actions": 0,
            "trend": "stable",
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    # Fetch related data
    diag_res = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_res.scalars().all())

    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_res = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_res.scalars().all())

    doc_res = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_res.scalars().all())

    elem_res = await db.execute(
        select(BuildingElement).join(Zone, BuildingElement.zone_id == Zone.id).where(Zone.building_id == building_id)
    )
    elements = list(elem_res.scalars().all())

    intv_res = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intv_res.scalars().all())

    action_res = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions_list = list(action_res.scalars().all())

    plan_res = await db.execute(select(TechnicalPlan).where(TechnicalPlan.building_id == building_id))
    plans = list(plan_res.scalars().all())

    # Score each dimension
    dimensions = []
    all_missing = []
    all_actions = []
    weighted_sum = 0.0

    for dim_key, dim_label, max_weight in DIMENSIONS:
        score, missing, dim_actions = _score_dimension(
            dim_key,
            building,
            diagnostics,
            samples,
            documents,
            elements,
            interventions,
            actions_list,
            plans,
        )
        weighted_sum += score * max_weight
        all_missing.extend(missing)
        all_actions.extend(dim_actions)
        dimensions.append(
            {
                "key": dim_key,
                "label": dim_label,
                "score": round(score, 1),
                "max_weight": max_weight,
                "color": score_color(score),
                "missing_items": missing,
                "required_actions": dim_actions,
            }
        )

    overall_score = round(weighted_sum / TOTAL_WEIGHT, 1) if TOTAL_WEIGHT else 0.0
    urgent = [a for a in all_actions if a.get("priority") == "critical"]
    recommended = [a for a in all_actions if a.get("priority") != "critical"]

    # Determine trend from historical reports
    trend = await _compute_trend(db, building_id, overall_score)

    return {
        "building_id": str(building_id),
        "overall_score": overall_score,
        "overall_color": score_color(overall_score),
        "dimensions": dimensions,
        "missing_items_count": len(all_missing),
        "urgent_actions": len(urgent),
        "recommended_actions": len(recommended),
        "trend": trend,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


async def get_missing_items(db: AsyncSession, building_id: UUID) -> list[dict]:
    """Return detailed checklist of all missing items across dimensions."""
    data = await calculate_completeness(db, building_id)
    items = []
    for dim in data.get("dimensions", []):
        for m in dim.get("missing_items", []):
            items.append(
                {
                    "dimension": dim["key"],
                    "dimension_label": dim["label"],
                    "field": m["field"],
                    "importance": m["importance"],
                    "status": "missing",
                }
            )
    return items


async def get_recommended_actions(db: AsyncSession, building_id: UUID) -> list[dict]:
    """Return prioritized list of recommended actions."""
    data = await calculate_completeness(db, building_id)
    actions = []
    priority_order = {"critical": 0, "important": 1, "nice_to_have": 2}
    for dim in data.get("dimensions", []):
        for a in dim.get("required_actions", []):
            actions.append(
                {
                    "dimension": dim["key"],
                    "dimension_label": dim["label"],
                    **a,
                }
            )
    actions.sort(key=lambda x: priority_order.get(x.get("priority", ""), 9))
    return actions


async def _compute_trend(db: AsyncSession, building_id: UUID, current_score: float) -> str:
    """Compare current score against last stored report to determine trend."""
    result = await db.execute(
        select(CompletenessReport)
        .where(CompletenessReport.building_id == building_id)
        .order_by(CompletenessReport.created_at.desc())
        .limit(1)
    )
    prev = result.scalar_one_or_none()
    if not prev:
        return "stable"
    diff = current_score - prev.overall_score
    if diff > 2:
        return "improving"
    if diff < -2:
        return "declining"
    return "stable"


async def save_completeness_snapshot(db: AsyncSession, building_id: UUID) -> dict:
    """Calculate and persist a completeness snapshot."""
    data = await calculate_completeness(db, building_id)

    report = CompletenessReport(
        building_id=building_id,
        overall_score=data["overall_score"],
        dimension_scores={d["key"]: d["score"] for d in data["dimensions"]},
        missing_items_count=data["missing_items_count"],
        urgent_actions=data["urgent_actions"],
        recommended_actions=data["recommended_actions"],
        trend=data["trend"],
    )
    db.add(report)

    # Upsert per-dimension scores
    for dim in data["dimensions"]:
        result = await db.execute(
            select(CompletenessScore).where(
                CompletenessScore.building_id == building_id,
                CompletenessScore.dimension == dim["key"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.score = dim["score"]
            existing.missing_items = dim["missing_items"]
            existing.required_actions = dim["required_actions"]
        else:
            db.add(
                CompletenessScore(
                    building_id=building_id,
                    dimension=dim["key"],
                    score=dim["score"],
                    missing_items=dim["missing_items"],
                    required_actions=dim["required_actions"],
                )
            )

    await db.commit()
    return data
