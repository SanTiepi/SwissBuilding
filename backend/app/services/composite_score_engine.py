"""
SwissBuildingOS - Composite Score Engine

Computes 15 composite scores for a building, covering health, investment,
resilience, sustainability, attractiveness, and operational readiness.
Each score includes value, grade, data completeness, and top contributing factors.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALL_POLLUTANTS
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.inventory_item import InventoryItem
from app.models.lease import Lease
from app.models.obligation import Obligation
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.zone import Zone

# ---------------------------------------------------------------------------
# Grade thresholds (A-F for 0-100 scores)
# ---------------------------------------------------------------------------

_GRADE_100 = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (40, "D"),
    (20, "E"),
    (0, "F"),
]

_GRADE_10 = [
    (9, "A"),
    (7.5, "B"),
    (6, "C"),
    (4, "D"),
    (2, "E"),
    (0, "F"),
]


def _grade(score: float, thresholds: list[tuple[float, str]]) -> str:
    for threshold, g in thresholds:
        if score >= threshold:
            return g
    return "F"


def _score_result(
    value: float,
    thresholds: list[tuple[float, str]],
    completeness: float,
    factors: list[str],
) -> dict:
    return {
        "value": round(value, 1),
        "grade": _grade(value, thresholds),
        "data_completeness": round(min(1.0, max(0.0, completeness)), 2),
        "top_factors": factors[:5],
    }


# ---------------------------------------------------------------------------
# Data fetching (batched)
# ---------------------------------------------------------------------------


async def _fetch_all(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch all data needed for composite score computation."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    plan_result = await db.execute(select(TechnicalPlan).where(TechnicalPlan.building_id == building_id))
    plans = list(plan_result.scalars().all())

    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())

    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())

    elements: list[BuildingElement] = []
    if zones:
        zone_ids = [z.id for z in zones]
        el_result = await db.execute(select(BuildingElement).where(BuildingElement.zone_id.in_(zone_ids)))
        elements = list(el_result.scalars().all())

    iv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(iv_result.scalars().all())

    lease_result = await db.execute(select(Lease).where(Lease.building_id == building_id))
    leases = list(lease_result.scalars().all())

    inv_result = await db.execute(select(InventoryItem).where(InventoryItem.building_id == building_id))
    inventory = list(inv_result.scalars().all())

    obl_result = await db.execute(select(Obligation).where(Obligation.building_id == building_id))
    obligations = list(obl_result.scalars().all())

    return {
        "building": building,
        "diagnostics": diagnostics,
        "samples": samples,
        "documents": documents,
        "plans": plans,
        "actions": actions,
        "zones": zones,
        "elements": elements,
        "interventions": interventions,
        "leases": leases,
        "inventory": inventory,
        "obligations": obligations,
    }


# ---------------------------------------------------------------------------
# Individual score computers
# ---------------------------------------------------------------------------


def _health_score(data: dict) -> dict:
    """Health: pollutants + structural condition (0-100)."""
    samples = data["samples"]
    diagnostics = data["diagnostics"]
    elements = data["elements"]
    building = data["building"]
    factors: list[str] = []
    signals = 0
    total_checks = 4

    # Pollutant coverage
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed:
        signals += 1
        factors.append(f"{len(completed)} diagnostic(s) complétés")
    else:
        factors.append("Aucun diagnostic complété")

    # Threshold exceedances
    exceeded = [s for s in samples if s.threshold_exceeded]
    if samples:
        signals += 1
        clean_ratio = 1 - (len(exceeded) / len(samples))
        pollutant_score = clean_ratio * 50 + 25
        if exceeded:
            factors.append(f"{len(exceeded)} dépassement(s) de seuil")
    else:
        pollutant_score = 30.0

    # Structural condition from elements
    condition_scores = {"excellent": 100, "good": 80, "fair": 60, "poor": 35, "critical": 10}
    el_scores = [condition_scores.get((e.condition or "").lower(), 50) for e in elements]
    if el_scores:
        signals += 1
        structural = sum(el_scores) / len(el_scores)
        factors.append(f"{len(el_scores)} éléments évalués")
    else:
        # Age-based fallback
        year = building.construction_year
        age = datetime.now(UTC).year - year if year else 40
        structural = max(20, 100 - age * 1.2)
        factors.append("Condition structurelle estimée par l'âge")

    # Building age penalty
    if building.construction_year:
        signals += 1
        age = datetime.now(UTC).year - building.construction_year
        if age > 50:
            factors.append(f"Bâtiment ancien ({age} ans)")

    completeness = signals / total_checks
    score = pollutant_score * 0.6 + structural * 0.4
    return _score_result(min(100, max(0, score)), _GRADE_100, completeness, factors)


def _investment_score(data: dict) -> dict:
    """Investment attractiveness (0-100): revenue potential + risk."""
    leases = data["leases"]
    building = data["building"]
    interventions = data["interventions"]
    factors: list[str] = []
    signals = 0
    total_checks = 3

    # Revenue from leases
    active_leases = [ls for ls in leases if ls.status == "active"]
    monthly_revenue = sum(ls.rent_monthly_chf or 0 for ls in active_leases)
    if active_leases:
        signals += 1
        factors.append(f"{len(active_leases)} bail(aux) actif(s), CHF {monthly_revenue:.0f}/mois")

    # Surface yield proxy
    surface = building.surface_area_m2 or 0
    if surface > 0 and monthly_revenue > 0:
        yield_per_m2 = monthly_revenue / surface
        if yield_per_m2 >= 20:
            revenue_score = 85
        elif yield_per_m2 >= 12:
            revenue_score = 70
        else:
            revenue_score = 50
        factors.append(f"Rendement CHF {yield_per_m2:.1f}/m²/mois")
    else:
        revenue_score = 30

    # Risk from pending interventions (cost)
    pending_cost = sum(iv.cost_chf or 0 for iv in interventions if iv.status in ("planned", "in_progress"))
    if interventions:
        signals += 1
        if pending_cost > 0:
            factors.append(f"Travaux en attente: CHF {pending_cost:.0f}")

    risk_penalty = min(30, pending_cost / 10000) if pending_cost > 0 else 0

    # Age/renovation premium
    if building.renovation_year:
        signals += 1
        years_since = datetime.now(UTC).year - building.renovation_year
        if years_since <= 5:
            factors.append("Rénové récemment")
            renovation_bonus = 15
        elif years_since <= 15:
            renovation_bonus = 5
        else:
            renovation_bonus = 0
    else:
        renovation_bonus = 0

    completeness = signals / total_checks
    score = revenue_score + renovation_bonus - risk_penalty
    return _score_result(min(100, max(0, score)), _GRADE_100, completeness, factors)


def _family_score(data: dict) -> dict:
    """Family suitability (0-10): safety + condition + leases."""
    building = data["building"]
    samples = data["samples"]
    elements = data["elements"]
    factors: list[str] = []
    signals = 0
    total_checks = 3

    # Safety: no critical pollutants
    critical_samples = [s for s in samples if s.threshold_exceeded and s.risk_level in ("high", "critical")]
    if samples:
        signals += 1
        if critical_samples:
            safety = 2.0
            factors.append(f"{len(critical_samples)} risque(s) élevé(s)")
        else:
            safety = 8.0
            factors.append("Aucun risque sanitaire élevé")
    else:
        safety = 5.0
        factors.append("Données sanitaires incomplètes")

    # Condition of living spaces
    condition_scores = {"excellent": 10, "good": 8, "fair": 6, "poor": 3, "critical": 1}
    el_scores = [condition_scores.get((e.condition or "").lower(), 5) for e in elements]
    if el_scores:
        signals += 1
        condition = sum(el_scores) / len(el_scores)
    else:
        condition = 5.0

    # Building type suitability
    signals += 1
    type_bonus = 0.0
    if building.building_type == "residential":
        type_bonus = 1.0
        factors.append("Type résidentiel")
    elif building.building_type == "mixed":
        type_bonus = 0.5

    completeness = signals / total_checks
    score = safety * 0.5 + condition * 0.3 + type_bonus * 2 + 1.0 * 0.2
    return _score_result(min(10, max(0, score)), _GRADE_10, completeness, factors)


def _resilience_score(data: dict) -> dict:
    """Resilience (0-100): material condition + maintenance + incident history."""
    elements = data["elements"]
    interventions = data["interventions"]
    building = data["building"]
    factors: list[str] = []
    signals = 0
    total_checks = 3

    # Structural resilience from elements
    condition_scores = {"excellent": 100, "good": 80, "fair": 55, "poor": 25, "critical": 5}
    el_scores = [condition_scores.get((e.condition or "").lower(), 50) for e in elements]
    if el_scores:
        signals += 1
        structural = sum(el_scores) / len(el_scores)
        factors.append(f"{len(el_scores)} éléments structurels évalués")
    else:
        structural = 50.0

    # Maintenance track record
    completed_iv = [iv for iv in interventions if iv.status == "completed"]
    if interventions:
        signals += 1
        maint_ratio = len(completed_iv) / len(interventions)
        maintenance = maint_ratio * 100
        factors.append(f"{len(completed_iv)}/{len(interventions)} interventions complétées")
    else:
        maintenance = 50.0

    # Age factor
    if building.construction_year:
        signals += 1
        age = datetime.now(UTC).year - building.construction_year
        age_factor = max(0, 100 - age * 1.0)
        if age > 50:
            factors.append(f"Bâtiment ancien ({age} ans)")
    else:
        age_factor = 50.0

    completeness = signals / total_checks
    score = structural * 0.4 + maintenance * 0.3 + age_factor * 0.3
    return _score_result(min(100, max(0, score)), _GRADE_100, completeness, factors)


def _carbon_score(data: dict) -> dict:
    """Carbon footprint estimate (kg CO2/m2/an)."""
    building = data["building"]
    factors: list[str] = []
    signals = 0
    total_checks = 2

    surface = building.surface_area_m2
    if surface and surface > 0:
        signals += 1
    else:
        return _score_result(0, _GRADE_100, 0, ["Surface inconnue — calcul impossible"])

    # Estimate based on construction era (Swiss averages)
    year = building.construction_year
    if year:
        signals += 1
        if year >= 2010:
            co2 = 8.0
            factors.append("Construction récente — faible empreinte")
        elif year >= 1990:
            co2 = 18.0
            factors.append("Construction 1990-2010")
        elif year >= 1960:
            co2 = 30.0
            factors.append("Construction 1960-1990 — forte empreinte probable")
        else:
            co2 = 25.0
            factors.append("Construction pré-1960")
    else:
        co2 = 20.0
        factors.append("Année inconnue — estimation moyenne")

    # Renovation adjustment
    if building.renovation_year:
        years_since = datetime.now(UTC).year - building.renovation_year
        if years_since <= 10:
            co2 *= 0.7
            factors.append("Rénovation récente — réduction estimée 30%")

    completeness = signals / total_checks
    return _score_result(co2, _GRADE_100, completeness, factors)


def _urgency_score(data: dict) -> dict:
    """Urgency (0-10): how urgently does this building need attention."""
    actions = data["actions"]
    samples = data["samples"]
    obligations = data["obligations"]
    factors: list[str] = []
    signals = 0
    total_checks = 3
    urgency = 0.0

    # Critical/high open actions
    critical_actions = [
        a for a in actions if a.status in ("open", "in_progress") and a.priority in ("critical", "high")
    ]
    if actions:
        signals += 1
        if critical_actions:
            urgency += min(5, len(critical_actions) * 1.5)
            factors.append(f"{len(critical_actions)} action(s) critique(s)/haute(s)")

    # Health risks
    high_risk = [s for s in samples if s.threshold_exceeded and s.risk_level in ("high", "critical")]
    if samples:
        signals += 1
        if high_risk:
            urgency += min(3, len(high_risk) * 1.0)
            factors.append(f"{len(high_risk)} risque(s) sanitaire(s) élevé(s)")

    # Approaching obligations
    today = date.today()
    approaching = [
        o
        for o in obligations
        if o.status in ("upcoming", "due_soon") and o.due_date and (o.due_date - today).days <= 60
    ]
    if obligations:
        signals += 1
        if approaching:
            urgency += min(3, len(approaching) * 1.0)
            factors.append(f"{len(approaching)} obligation(s) imminente(s)")

    if not factors:
        factors.append("Aucune urgence détectée")

    completeness = signals / total_checks
    return _score_result(min(10, max(0, urgency)), _GRADE_10, completeness, factors)


def _digital_twin_score(data: dict) -> dict:
    """Digital twin completeness (0-100%): how complete is the data."""
    building = data["building"]
    diagnostics = data["diagnostics"]
    documents = data["documents"]
    plans = data["plans"]
    elements = data["elements"]
    zones = data["zones"]
    inventory = data["inventory"]
    factors: list[str] = []

    checks = 0
    passed = 0

    # Basic info
    checks += 1
    if building.construction_year and building.surface_area_m2:
        passed += 1
    else:
        factors.append("Informations de base incomplètes")

    # Coordinates
    checks += 1
    if building.latitude and building.longitude:
        passed += 1
    else:
        factors.append("Coordonnées manquantes")

    # Diagnostics
    checks += 1
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed:
        passed += 1
    else:
        factors.append("Aucun diagnostic complété")

    # Pollutant coverage
    tested_pollutants = {s.pollutant_type for s in data["samples"] if s.pollutant_type}
    coverage = len(tested_pollutants & set(ALL_POLLUTANTS))
    checks += 1
    if coverage >= 4:
        passed += 1
    else:
        factors.append(f"Couverture polluants: {coverage}/{len(ALL_POLLUTANTS)}")

    # Documents
    checks += 1
    if documents:
        passed += 1
    else:
        factors.append("Aucun document")

    # Plans
    checks += 1
    if plans:
        passed += 1
    else:
        factors.append("Aucun plan technique")

    # Zones
    checks += 1
    if zones:
        passed += 1
    else:
        factors.append("Aucune zone définie")

    # Elements
    checks += 1
    if elements:
        passed += 1
    else:
        factors.append("Aucun élément de construction")

    # Inventory
    checks += 1
    if inventory:
        passed += 1
    else:
        factors.append("Aucun équipement inventorié")

    # Interventions
    checks += 1
    if data["interventions"]:
        passed += 1

    score = (passed / checks * 100) if checks > 0 else 0
    completeness = 1.0  # This score IS the completeness measure
    if not factors:
        factors.append("Jumeau numérique complet")
    return _score_result(score, _GRADE_100, completeness, factors)


def _potential_score(data: dict) -> dict:
    """Renovation/improvement potential (0-100)."""
    building = data["building"]
    elements = data["elements"]
    factors: list[str] = []
    signals = 0
    total_checks = 3
    potential = 50.0

    # Older buildings have more potential
    if building.construction_year:
        signals += 1
        age = datetime.now(UTC).year - building.construction_year
        if age > 40:
            potential += 20
            factors.append(f"Fort potentiel de rénovation (âge: {age} ans)")
        elif age > 20:
            potential += 10
            factors.append(f"Potentiel de modernisation (âge: {age} ans)")
        else:
            factors.append("Construction récente — potentiel limité")

    # Poor condition elements = renovation opportunity
    poor_elements = [e for e in elements if (e.condition or "").lower() in ("poor", "critical")]
    if elements:
        signals += 1
        if poor_elements:
            potential += min(20, len(poor_elements) * 5)
            factors.append(f"{len(poor_elements)} élément(s) à rénover")

    # Surface area for solar/energy potential
    if building.surface_area_m2 and building.surface_area_m2 > 200:
        signals += 1
        potential += 10
        factors.append(f"Grande surface ({building.surface_area_m2:.0f} m²) — potentiel énergétique")

    completeness = signals / total_checks
    return _score_result(min(100, max(0, potential)), _GRADE_100, completeness, factors)


def _tenant_attractiveness(data: dict) -> dict:
    """Tenant attractiveness (0-100): condition + location + energy."""
    elements = data["elements"]
    leases = data["leases"]
    samples = data["samples"]
    factors: list[str] = []
    signals = 0
    total_checks = 3
    score = 50.0

    # Condition
    condition_map = {"excellent": 25, "good": 20, "fair": 10, "poor": 0, "critical": -10}
    el_scores = [condition_map.get((e.condition or "").lower(), 5) for e in elements]
    if el_scores:
        signals += 1
        score += sum(el_scores) / len(el_scores)
        factors.append(f"{len(el_scores)} éléments évalués")

    # Safety (no high-risk pollutants)
    high_risk = [s for s in samples if s.threshold_exceeded and s.risk_level in ("high", "critical")]
    if samples:
        signals += 1
        if not high_risk:
            score += 15
            factors.append("Aucun risque sanitaire élevé")
        else:
            score -= 20
            factors.append(f"{len(high_risk)} risque(s) élevé(s) — impact locataire")

    # Lease occupancy signal
    active_leases = [ls for ls in leases if ls.status == "active"]
    if leases:
        signals += 1
        occupancy = len(active_leases) / len(leases)
        if occupancy >= 0.8:
            score += 10
            factors.append(f"Taux d'occupation élevé ({occupancy * 100:.0f}%)")

    completeness = signals / total_checks
    return _score_result(min(100, max(0, score)), _GRADE_100, completeness, factors)


def _sellability_score(data: dict) -> dict:
    """Sellability (0-100): compliance + documentation + readiness."""
    diagnostics = data["diagnostics"]
    documents = data["documents"]
    plans = data["plans"]
    samples = data["samples"]
    factors: list[str] = []
    signals = 0
    total_checks = 4
    score = 0.0

    # Documentation completeness
    if documents:
        signals += 1
        score += 25
        factors.append(f"{len(documents)} document(s) disponible(s)")
    else:
        factors.append("Aucune documentation")

    # Diagnostic completeness
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed:
        signals += 1
        score += 25
        factors.append(f"{len(completed)} diagnostic(s) validé(s)")
    else:
        factors.append("Diagnostics incomplets")

    # Plans
    if plans:
        signals += 1
        score += 20
    else:
        factors.append("Plans manquants")

    # No critical issues
    critical = [s for s in samples if s.threshold_exceeded and s.risk_level in ("high", "critical")]
    signals += 1
    if not critical:
        score += 30
        factors.append("Aucun problème critique")
    else:
        score += max(0, 30 - len(critical) * 10)
        factors.append(f"{len(critical)} problème(s) critique(s)")

    completeness = signals / total_checks
    return _score_result(min(100, max(0, score)), _GRADE_100, completeness, factors)


def _insurability_score(data: dict) -> dict:
    """Insurability (0-100): risks + materials + maintenance."""
    samples = data["samples"]
    elements = data["elements"]
    interventions = data["interventions"]
    factors: list[str] = []
    signals = 0
    total_checks = 3
    score = 70.0  # Base: insurable unless problems

    # Risk exposure
    exceeded = [s for s in samples if s.threshold_exceeded]
    critical = [s for s in exceeded if s.risk_level in ("high", "critical")]
    if samples:
        signals += 1
        if critical:
            score -= len(critical) * 15
            factors.append(f"{len(critical)} risque(s) critique(s)")
        elif exceeded:
            score -= len(exceeded) * 5
            factors.append(f"{len(exceeded)} dépassement(s) de seuil")
        else:
            score += 10
            factors.append("Aucun dépassement de seuil")

    # Material/structural condition
    poor_el = [e for e in elements if (e.condition or "").lower() in ("poor", "critical")]
    if elements:
        signals += 1
        if poor_el:
            score -= len(poor_el) * 5
            factors.append(f"{len(poor_el)} élément(s) en mauvais état")
        else:
            score += 10

    # Maintenance record
    completed_iv = [iv for iv in interventions if iv.status == "completed"]
    if interventions:
        signals += 1
        ratio = len(completed_iv) / len(interventions)
        if ratio >= 0.8:
            score += 10
            factors.append("Bon historique de maintenance")
        elif ratio < 0.5:
            score -= 10
            factors.append("Maintenance insuffisante")

    completeness = signals / total_checks
    return _score_result(min(100, max(0, score)), _GRADE_100, completeness, factors)


def _bankability_score(data: dict) -> dict:
    """Bankability (0-100): value + revenue + risks + docs."""
    building = data["building"]
    leases = data["leases"]
    documents = data["documents"]
    samples = data["samples"]
    factors: list[str] = []
    signals = 0
    total_checks = 4
    score = 50.0

    # Revenue
    active_leases = [ls for ls in leases if ls.status == "active"]
    revenue = sum(ls.rent_monthly_chf or 0 for ls in active_leases)
    if active_leases:
        signals += 1
        score += min(20, revenue / 500)
        factors.append(f"Revenus locatifs: CHF {revenue:.0f}/mois")

    # Documentation
    if documents and len(documents) >= 3:
        signals += 1
        score += 15
        factors.append("Documentation suffisante")
    elif documents:
        signals += 1
        score += 5
        factors.append("Documentation partielle")

    # Risk
    critical = [s for s in samples if s.threshold_exceeded and s.risk_level in ("high", "critical")]
    if samples:
        signals += 1
        if not critical:
            score += 15
        else:
            score -= len(critical) * 10
            factors.append(f"{len(critical)} risque(s) critique(s)")

    # Value proxy (surface)
    if building.surface_area_m2:
        signals += 1

    completeness = signals / total_checks
    return _score_result(min(100, max(0, score)), _GRADE_100, completeness, factors)


def _comfort_score(data: dict) -> dict:
    """Comfort (0-10): proxy from building condition and type."""
    building = data["building"]
    elements = data["elements"]
    factors: list[str] = []
    signals = 0
    total_checks = 2
    score = 5.0

    # Element conditions
    condition_map = {"excellent": 9, "good": 7, "fair": 5, "poor": 3, "critical": 1}
    el_scores = [condition_map.get((e.condition or "").lower(), 5) for e in elements]
    if el_scores:
        signals += 1
        score = sum(el_scores) / len(el_scores)
        factors.append(f"{len(el_scores)} éléments évalués")

    # Renovation recency
    if building.renovation_year:
        signals += 1
        years_since = datetime.now(UTC).year - building.renovation_year
        if years_since <= 5:
            score += 1.5
            factors.append("Rénové récemment")
        elif years_since <= 15:
            score += 0.5

    completeness = signals / total_checks
    return _score_result(min(10, max(0, score)), _GRADE_10, completeness, factors)


def _maintenance_score(data: dict) -> dict:
    """Maintenance health (0-100): component ages + warranties + services."""
    inventory = data["inventory"]
    interventions = data["interventions"]
    factors: list[str] = []
    signals = 0
    total_checks = 3
    score = 50.0

    # Warranty coverage
    today = date.today()
    if inventory:
        signals += 1
        with_warranty = [i for i in inventory if i.warranty_end_date and i.warranty_end_date >= today]
        warranty_ratio = len(with_warranty) / len(inventory)
        score += warranty_ratio * 20
        factors.append(f"{len(with_warranty)}/{len(inventory)} équipements sous garantie")

    # Component condition
    if inventory:
        signals += 1
        condition_map = {"good": 100, "fair": 60, "poor": 25, "critical": 5, "unknown": 40}
        cond_scores = [condition_map.get(i.condition or "unknown", 40) for i in inventory]
        avg_cond = sum(cond_scores) / len(cond_scores)
        score = score * 0.5 + avg_cond * 0.5
        poor_items = [i for i in inventory if (i.condition or "").lower() in ("poor", "critical")]
        if poor_items:
            factors.append(f"{len(poor_items)} équipement(s) en mauvais état")

    # Intervention follow-through
    completed = [iv for iv in interventions if iv.status == "completed"]
    if interventions:
        signals += 1
        ratio = len(completed) / len(interventions)
        score += ratio * 15
        if ratio < 0.5:
            factors.append("Taux de complétion des interventions faible")

    if not factors:
        factors.append("Données de maintenance insuffisantes")

    completeness = signals / total_checks
    return _score_result(min(100, max(0, score)), _GRADE_100, completeness, factors)


def _renovation_readiness(data: dict) -> dict:
    """Renovation readiness (0-100): documentation + diagnostics + season + permits."""
    diagnostics = data["diagnostics"]
    documents = data["documents"]
    plans = data["plans"]
    leases = data["leases"]
    factors: list[str] = []
    signals = 0
    total_checks = 4
    score = 0.0

    # Documentation ready
    if documents and len(documents) >= 2:
        signals += 1
        score += 25
        factors.append("Documentation disponible")
    else:
        factors.append("Documentation insuffisante")

    # Diagnostics ready
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed:
        signals += 1
        score += 25
        factors.append(f"{len(completed)} diagnostic(s) prêt(s)")
    else:
        factors.append("Diagnostics non complétés")

    # Plans available
    if plans:
        signals += 1
        score += 25
    else:
        factors.append("Plans manquants")

    # Lease window (no active leases blocking renovation)
    active_leases = [ls for ls in leases if ls.status == "active"]
    signals += 1
    if not active_leases:
        score += 25
        factors.append("Aucun bail actif — fenêtre libre")
    else:
        # Check if any lease ends soon
        today = date.today()
        ending_soon = [ls for ls in active_leases if ls.date_end and (ls.date_end - today).days <= 180]
        if ending_soon:
            score += 15
            factors.append(f"{len(ending_soon)} bail(aux) se terminant prochainement")
        else:
            score += 5
            factors.append("Baux actifs — coordination nécessaire")

    completeness = signals / total_checks
    return _score_result(min(100, max(0, score)), _GRADE_100, completeness, factors)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_SCORE_COMPUTERS = {
    "health_score": _health_score,
    "investment_score": _investment_score,
    "family_score": _family_score,
    "resilience_score": _resilience_score,
    "carbon_score": _carbon_score,
    "urgency_score": _urgency_score,
    "digital_twin_score": _digital_twin_score,
    "potential_score": _potential_score,
    "tenant_attractiveness": _tenant_attractiveness,
    "sellability_score": _sellability_score,
    "insurability_score": _insurability_score,
    "bankability_score": _bankability_score,
    "comfort_score": _comfort_score,
    "maintenance_score": _maintenance_score,
    "renovation_readiness": _renovation_readiness,
}


async def compute_all_composite_scores(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Compute 15 composite scores for a building.

    Returns dict keyed by score name, each containing:
    {value, grade, data_completeness, top_factors}
    """
    data = await _fetch_all(db, building_id)
    if data is None:
        raise ValueError(f"Building {building_id} not found")

    scores = {}
    for name, computer in _SCORE_COMPUTERS.items():
        scores[name] = computer(data)

    scores["building_id"] = str(building_id)
    scores["generated_at"] = datetime.now(UTC).isoformat()
    return scores


async def compute_single_score(
    db: AsyncSession,
    building_id: UUID,
    score_name: str,
) -> dict:
    """Compute a single named composite score."""
    computer = _SCORE_COMPUTERS.get(score_name)
    if computer is None:
        raise ValueError(f"Unknown score: {score_name}. Available: {list(_SCORE_COMPUTERS.keys())}")

    data = await _fetch_all(db, building_id)
    if data is None:
        raise ValueError(f"Building {building_id} not found")

    result = computer(data)
    result["score_name"] = score_name
    result["building_id"] = str(building_id)
    result["generated_at"] = datetime.now(UTC).isoformat()
    return result
