"""Building data quality and completeness scoring service."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def calculate_building_quality(db: AsyncSession, building_id) -> dict:
    """
    Calculate a completeness score for a building based on available data.

    Returns a dict with:
    - overall_score: float 0.0 to 1.0
    - sections: dict of section_name -> {score: float, details: str}
    - missing: list of strings describing what's missing
    """
    from app.models.action_item import ActionItem
    from app.models.building import Building
    from app.models.building_element import BuildingElement
    from app.models.building_risk_score import BuildingRiskScore
    from app.models.diagnostic import Diagnostic
    from app.models.document import Document
    from app.models.evidence_link import EvidenceLink
    from app.models.intervention import Intervention
    from app.models.material import Material
    from app.models.technical_plan import TechnicalPlan
    from app.models.zone import Zone

    sections = {}
    missing = []

    # 1. Identity section
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return {"overall_score": 0.0, "sections": {}, "missing": ["Building not found"]}

    identity_checks = 0
    identity_total = 5
    if building.egid:
        identity_checks += 1
    else:
        missing.append("EGID manquant")
    if building.address:
        identity_checks += 1
    if building.construction_year:
        identity_checks += 1
    else:
        missing.append("Année de construction manquante")
    if building.latitude and building.longitude:
        identity_checks += 1
    else:
        missing.append("Coordonnées GPS manquantes")
    if building.surface_area_m2:
        identity_checks += 1
    else:
        missing.append("Surface manquante")

    identity_score = identity_checks / identity_total
    sections["identity"] = {
        "score": identity_score,
        "details": f"{identity_checks}/{identity_total} champs d'identité renseignés",
    }

    # 2. Diagnostics section
    diag_result = await db.execute(
        select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id)
    )
    diag_count = diag_result.scalar() or 0
    diag_score = min(1.0, diag_count / 3)  # 3 diagnostics = full score
    sections["diagnostics"] = {"score": diag_score, "details": f"{diag_count} diagnostic(s) réalisé(s)"}
    if diag_count == 0:
        missing.append("Aucun diagnostic réalisé")

    # 3. Zones section
    zone_result = await db.execute(select(func.count()).select_from(Zone).where(Zone.building_id == building_id))
    zone_count = zone_result.scalar() or 0
    zone_score = min(1.0, zone_count / 5)  # 5 zones = full score
    sections["zones"] = {"score": zone_score, "details": f"{zone_count} zone(s) définie(s)"}
    if zone_count == 0:
        missing.append("Aucune zone définie")

    # 4. Materials section (via zones -> elements -> materials)
    mat_result = await db.execute(
        select(func.count())
        .select_from(Material)
        .join(BuildingElement, Material.element_id == BuildingElement.id)
        .join(Zone, BuildingElement.zone_id == Zone.id)
        .where(Zone.building_id == building_id)
    )
    mat_count = mat_result.scalar() or 0
    mat_score = min(1.0, mat_count / 10)  # 10 materials = full score
    sections["materials"] = {"score": mat_score, "details": f"{mat_count} matériau(x) identifié(s)"}
    if mat_count == 0:
        missing.append("Aucun matériau identifié")

    # 5. Interventions section
    interv_result = await db.execute(
        select(func.count()).select_from(Intervention).where(Intervention.building_id == building_id)
    )
    interv_count = interv_result.scalar() or 0
    interv_score = min(1.0, interv_count / 3)  # 3 interventions = full score
    sections["interventions"] = {"score": interv_score, "details": f"{interv_count} intervention(s) documentée(s)"}
    if interv_count == 0:
        missing.append("Aucune intervention documentée")

    # 6. Documents section
    doc_result = await db.execute(select(func.count()).select_from(Document).where(Document.building_id == building_id))
    doc_count = doc_result.scalar() or 0
    doc_score = min(1.0, doc_count / 3)  # 3 documents = full score
    sections["documents"] = {"score": doc_score, "details": f"{doc_count} document(s) uploadé(s)"}
    if doc_count == 0:
        missing.append("Aucun document uploadé")

    # 7. Plans section
    plan_result = await db.execute(
        select(func.count()).select_from(TechnicalPlan).where(TechnicalPlan.building_id == building_id)
    )
    plan_count = plan_result.scalar() or 0
    plan_score = min(1.0, plan_count / 2)  # 2 plans = full score
    sections["plans"] = {"score": plan_score, "details": f"{plan_count} plan(s) technique(s)"}
    if plan_count == 0:
        missing.append("Aucun plan technique")

    # 8. Evidence section
    evidence_count = 0

    # Evidence targeting risk scores
    risk_result = await db.execute(select(BuildingRiskScore.id).where(BuildingRiskScore.building_id == building_id))
    risk_score_row = risk_result.scalar_one_or_none()
    if risk_score_row:
        ev_result = await db.execute(
            select(func.count())
            .select_from(EvidenceLink)
            .where(EvidenceLink.target_type == "risk_score")
            .where(EvidenceLink.target_id == risk_score_row)
        )
        evidence_count += ev_result.scalar() or 0

    # Evidence targeting action items
    action_ids_result = await db.execute(select(ActionItem.id).where(ActionItem.building_id == building_id))
    action_ids = [row[0] for row in action_ids_result.all()]
    if action_ids:
        ev_result2 = await db.execute(
            select(func.count())
            .select_from(EvidenceLink)
            .where(EvidenceLink.target_type == "action_item")
            .where(EvidenceLink.target_id.in_(action_ids))
        )
        evidence_count += ev_result2.scalar() or 0

    evidence_score = min(1.0, evidence_count / 5)  # 5 evidence links = full score
    sections["evidence"] = {"score": evidence_score, "details": f"{evidence_count} lien(s) de preuve actif(s)"}
    if evidence_count == 0:
        missing.append("Aucun lien de preuve")

    # Overall score (weighted average)
    weights = {
        "identity": 2.0,
        "diagnostics": 2.0,
        "zones": 1.5,
        "materials": 1.5,
        "interventions": 1.0,
        "documents": 1.0,
        "plans": 0.5,
        "evidence": 1.5,
    }
    total_weight = sum(weights.values())
    weighted_sum = sum(sections[k]["score"] * weights[k] for k in sections)
    overall_score = round(weighted_sum / total_weight, 2)

    return {
        "overall_score": overall_score,
        "sections": sections,
        "missing": missing,
    }
