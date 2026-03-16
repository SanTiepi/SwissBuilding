"""
SwissBuildingOS - Contractor Matching Service

Matches contractor-type organizations to buildings based on pollutant findings,
required certifications, work categories, and location proximity.
Also estimates workforce needs and aggregates portfolio-level demand.
"""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample

# ---------------------------------------------------------------------------
# Risk level ordering
# ---------------------------------------------------------------------------

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3, "unknown": 0}

# ---------------------------------------------------------------------------
# Certification / pollutant mapping
# ---------------------------------------------------------------------------

_POLLUTANT_CERTIFICATIONS: dict[str, list[dict[str, str]]] = {
    "asbestos": [
        {
            "certification": "SUVA_asbestos",
            "reason": "Asbestos removal requires SUVA-recognized contractor",
            "legal_ref": "OTConst Art. 60a",
        },
        {
            "certification": "CFST_6503",
            "reason": "CFST 6503 training required for asbestos work",
            "legal_ref": "CFST 6503",
        },
    ],
    "pcb": [
        {
            "certification": "SUVA_chemical_hazards",
            "reason": "PCB handling requires chemical hazard certification",
            "legal_ref": "ORRChim Annexe 2.15",
        },
    ],
    "lead": [
        {
            "certification": "SUVA_lead",
            "reason": "Lead paint removal requires SUVA lead certification",
            "legal_ref": "ORRChim Annexe 2.18",
        },
    ],
    "hap": [
        {
            "certification": "SUVA_chemical_hazards",
            "reason": "HAP removal requires chemical hazard certification",
            "legal_ref": "OLED dechet special",
        },
    ],
    "radon": [
        {
            "certification": "OFSP_radon",
            "reason": "Radon mitigation requires OFSP-certified specialist",
            "legal_ref": "ORaP Art. 110",
        },
    ],
}

_WORK_CATEGORY_EQUIPMENT: dict[str, list[str]] = {
    "minor": ["PPE_basic", "HEPA_vacuum"],
    "medium": ["PPE_full", "HEPA_vacuum", "negative_pressure_unit", "decontamination_shower"],
    "major": [
        "PPE_full",
        "HEPA_vacuum",
        "negative_pressure_unit",
        "decontamination_shower",
        "air_monitoring_equipment",
        "full_containment_enclosure",
    ],
}

# Specialists per pollutant per risk level
_SPECIALISTS_BY_RISK: dict[str, dict[str, int]] = {
    "low": {"base": 1, "safety": 0},
    "medium": {"base": 2, "safety": 0},
    "high": {"base": 2, "safety": 1},
    "critical": {"base": 3, "safety": 1},
}

# Estimated days per sample by risk level
_DAYS_PER_SAMPLE: dict[str, float] = {
    "low": 0.5,
    "medium": 1.0,
    "high": 2.0,
    "critical": 3.0,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_building_samples(db: AsyncSession, building_id: UUID) -> tuple[Building | None, list[Sample]]:
    """Fetch a building and all samples from its diagnostics."""
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        return None, []

    stmt = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    result = await db.execute(stmt)
    samples = list(result.scalars().all())
    return building, samples


def _extract_pollutants(samples: list[Sample]) -> dict[str, list[Sample]]:
    """Group positive samples by pollutant type."""
    pollutant_map: dict[str, list[Sample]] = {}
    for sample in samples:
        if sample.pollutant_type and sample.threshold_exceeded:
            key = sample.pollutant_type.lower()
            pollutant_map.setdefault(key, []).append(sample)
    return pollutant_map


def _max_risk(samples: list[Sample]) -> str:
    """Return the highest risk level among samples."""
    if not samples:
        return "low"
    levels = [s.risk_level or "low" for s in samples]
    return max(levels, key=lambda x: _RISK_ORDER.get(x.lower(), 0))


def _max_work_category(samples: list[Sample]) -> str | None:
    """Return the highest CFST work category among samples."""
    order = {"minor": 0, "medium": 1, "major": 2}
    categories = [s.cfst_work_category for s in samples if s.cfst_work_category]
    if not categories:
        return None
    return max(categories, key=lambda x: order.get(x, 0))


def _canton_proximity_score(building_canton: str | None, org_canton: str | None) -> float:
    """Score 0.0-1.0 based on canton proximity."""
    if not building_canton or not org_canton:
        return 0.0
    if building_canton.upper() == org_canton.upper():
        return 1.0
    # Neighboring canton clusters
    _neighbors: dict[str, set[str]] = {
        "VD": {"GE", "VS", "FR", "NE"},
        "GE": {"VD"},
        "VS": {"VD", "BE"},
        "FR": {"VD", "BE", "NE"},
        "NE": {"VD", "FR", "BE", "JU"},
        "BE": {"FR", "VS", "NE", "JU", "SO", "LU", "OW", "NW"},
        "ZH": {"AG", "TG", "SH", "SZ", "ZG", "LU"},
        "AG": {"ZH", "SO", "BE", "LU", "BL", "BS"},
    }
    neighbors = _neighbors.get(building_canton.upper(), set())
    if org_canton.upper() in neighbors:
        return 0.5
    return 0.1


# ---------------------------------------------------------------------------
# FN1: match_contractors
# ---------------------------------------------------------------------------


async def match_contractors(db: AsyncSession, building_id: UUID) -> dict:
    """
    Rank contractor-type organizations by fit for a building.

    Scoring factors:
    - Pollutant certification match (0-40 points)
    - SUVA recognition (0-20 points)
    - FACH approval (0-10 points)
    - Location proximity (0-20 points)
    - Work category capability (0-10 points)
    """
    building, samples = await _get_building_samples(db, building_id)
    if building is None:
        return {
            "building_id": building_id,
            "pollutants_found": [],
            "contractors": [],
        }

    pollutant_map = _extract_pollutants(samples)
    pollutants_found = list(pollutant_map.keys())
    work_category = _max_work_category(samples)

    # Fetch all contractor orgs
    org_result = await db.execute(select(Organization).where(Organization.type == "contractor"))
    contractors = list(org_result.scalars().all())

    scored: list[dict] = []
    for org in contractors:
        reasons: list[dict] = []
        total = 0.0

        # Certification match score (up to 40)
        if pollutants_found:
            matched = 0
            for p in pollutants_found:
                if p in _POLLUTANT_CERTIFICATIONS:
                    matched += 1
            frac = matched / len(pollutants_found) if pollutants_found else 0.0
            pts = frac * 40.0
            total += pts
            reasons.append(
                {
                    "factor": "pollutant_coverage",
                    "score": round(pts, 1),
                    "detail": f"Covers {matched}/{len(pollutants_found)} pollutant types",
                }
            )

        # SUVA recognition (20 pts)
        if org.suva_recognized:
            total += 20.0
            reasons.append({"factor": "suva_recognized", "score": 20.0, "detail": "SUVA-recognized contractor"})
        elif pollutants_found:
            reasons.append(
                {
                    "factor": "suva_recognized",
                    "score": 0.0,
                    "detail": "Not SUVA-recognized",
                }
            )

        # FACH approval (10 pts)
        if org.fach_approved:
            total += 10.0
            reasons.append({"factor": "fach_approved", "score": 10.0, "detail": "FACH-approved contractor"})

        # Location proximity (up to 20 pts)
        prox = _canton_proximity_score(building.canton, org.canton)
        prox_pts = prox * 20.0
        total += prox_pts
        if prox_pts > 0:
            reasons.append(
                {
                    "factor": "location_proximity",
                    "score": round(prox_pts, 1),
                    "detail": f"Canton proximity: {org.canton or 'unknown'} → {building.canton}",
                }
            )

        # Work category capability (10 pts if SUVA + major/medium)
        if work_category in ("major", "medium") and org.suva_recognized:
            total += 10.0
            reasons.append(
                {
                    "factor": "work_category_capability",
                    "score": 10.0,
                    "detail": f"Capable of {work_category} work category (CFST 6503)",
                }
            )

        scored.append(
            {
                "organization_id": org.id,
                "organization_name": org.name,
                "total_score": round(total, 1),
                "suva_recognized": org.suva_recognized or False,
                "fach_approved": org.fach_approved or False,
                "canton": org.canton,
                "city": org.city,
                "match_reasons": reasons,
            }
        )

    scored.sort(key=lambda x: x["total_score"], reverse=True)

    return {
        "building_id": building_id,
        "pollutants_found": pollutants_found,
        "contractors": scored,
    }


# ---------------------------------------------------------------------------
# FN2: get_required_certifications
# ---------------------------------------------------------------------------


async def get_required_certifications(db: AsyncSession, building_id: UUID) -> dict:
    """
    Derive required certifications from building samples and diagnostics.
    """
    building, samples = await _get_building_samples(db, building_id)
    if building is None:
        return {
            "building_id": building_id,
            "cfst_work_category": None,
            "suva_certifications": [],
            "special_equipment": [],
            "regulatory_notifications": [],
        }

    pollutant_map = _extract_pollutants(samples)
    work_category = _max_work_category(samples)

    # Certifications
    certs: list[dict] = []
    seen_certs: set[str] = set()
    for pollutant, _p_samples in pollutant_map.items():
        cert_defs = _POLLUTANT_CERTIFICATIONS.get(pollutant, [])
        for cdef in cert_defs:
            if cdef["certification"] not in seen_certs:
                seen_certs.add(cdef["certification"])
                certs.append(
                    {
                        "certification": cdef["certification"],
                        "reason": cdef["reason"],
                        "pollutant": pollutant,
                        "legal_ref": cdef.get("legal_ref"),
                    }
                )

    # Special equipment
    equipment: list[str] = []
    if work_category:
        equipment = list(_WORK_CATEGORY_EQUIPMENT.get(work_category, []))

    # Regulatory notifications
    notifications: list[str] = []
    if "asbestos" in pollutant_map:
        notifications.append("SUVA notification required (asbestos found)")
        if building.canton:
            notifications.append(f"Cantonal notification to {building.canton} environmental service")
    if work_category == "major":
        notifications.append("Air monitoring required during and after work (CFST 6503 major)")

    return {
        "building_id": building_id,
        "cfst_work_category": work_category,
        "suva_certifications": certs,
        "special_equipment": equipment,
        "regulatory_notifications": notifications,
    }


# ---------------------------------------------------------------------------
# FN3: estimate_contractor_needs
# ---------------------------------------------------------------------------


async def estimate_contractor_needs(db: AsyncSession, building_id: UUID) -> dict:
    """
    Estimate workforce sizing for a building based on pollutant findings.
    """
    building, samples = await _get_building_samples(db, building_id)
    if building is None:
        return {
            "building_id": building_id,
            "pollutant_needs": [],
            "total_specialists": 0,
            "total_estimated_days": 0.0,
            "safety_crew_required": False,
            "parallel_possible": False,
            "work_sequence_recommendation": "No data available",
        }

    pollutant_map = _extract_pollutants(samples)

    needs: list[dict] = []
    total_specialists = 0
    total_days = 0.0
    safety_required = False

    for pollutant, p_samples in pollutant_map.items():
        risk = _max_risk(p_samples)
        risk_key = risk.lower()
        spec = _SPECIALISTS_BY_RISK.get(risk_key, _SPECIALISTS_BY_RISK["low"])
        specialists = spec["base"]
        has_safety = spec["safety"] > 0
        days_per = _DAYS_PER_SAMPLE.get(risk_key, 1.0)
        est_days = len(p_samples) * days_per

        if has_safety:
            safety_required = True

        needs.append(
            {
                "pollutant": pollutant,
                "sample_count": len(p_samples),
                "max_risk_level": risk,
                "specialists_needed": specialists,
                "estimated_days": round(est_days, 1),
                "requires_safety_crew": has_safety,
            }
        )

        total_specialists += specialists
        total_days += est_days

    # Determine if parallel work is possible
    # Parallel is possible if pollutants don't require conflicting containment
    parallel_possible = len(pollutant_map) > 1 and not (
        "asbestos" in pollutant_map and any(p in pollutant_map for p in ("pcb", "hap"))
    )

    # Work sequence recommendation
    if not pollutant_map:
        recommendation = "No remediation needed"
    elif len(pollutant_map) == 1:
        recommendation = f"Single pollutant ({next(iter(pollutant_map.keys()))}): sequential removal"
    elif parallel_possible:
        recommendation = "Multiple pollutants can be addressed in parallel by separate teams"
    else:
        recommendation = (
            "Sequential work required: address asbestos first (containment conflicts), then other pollutants"
        )

    return {
        "building_id": building_id,
        "pollutant_needs": needs,
        "total_specialists": total_specialists,
        "total_estimated_days": round(total_days, 1),
        "safety_crew_required": safety_required,
        "parallel_possible": parallel_possible,
        "work_sequence_recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# FN4: get_portfolio_contractor_demand
# ---------------------------------------------------------------------------


async def get_portfolio_contractor_demand(db: AsyncSession, org_id: UUID) -> dict:
    """
    Aggregate contractor demand across all buildings owned/created by
    users in the given organization.
    """
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return {
            "organization_id": org_id,
            "total_buildings": 0,
            "total_contractor_days": 0.0,
            "certification_demand": [],
            "buildings": [],
        }

    total_days = 0.0
    cert_counter: Counter[str] = Counter()
    building_demands: list[dict] = []

    for bldg in buildings:
        needs = await estimate_contractor_needs(db, bldg.id)
        certs_result = await get_required_certifications(db, bldg.id)

        bldg_days = needs["total_estimated_days"]
        total_days += bldg_days

        cert_names = [c["certification"] for c in certs_result["suva_certifications"]]
        for cn in cert_names:
            cert_counter[cn] += 1

        building_demands.append(
            {
                "building_id": bldg.id,
                "address": bldg.address,
                "contractor_days": bldg_days,
                "certifications_needed": cert_names,
            }
        )

    cert_distribution = [{"certification": cert, "building_count": count} for cert, count in cert_counter.most_common()]

    return {
        "organization_id": org_id,
        "total_buildings": len(buildings),
        "total_contractor_days": round(total_days, 1),
        "certification_demand": cert_distribution,
        "buildings": building_demands,
    }
