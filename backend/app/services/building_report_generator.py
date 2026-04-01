"""
SwissBuildingOS - Building Report Generator

Compiles a comprehensive building report from all available intelligence:
passport, risk, compliance, interventions, readiness, financial summary.

Includes HTML payload generation for Gotenberg PDF conversion.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALL_POLLUTANTS
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.data_quality_issue import DataQualityIssue
from app.models.intervention import Intervention
from app.models.unknown_issue import UnknownIssue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Grade helpers
# ---------------------------------------------------------------------------

_GRADE_ORDER = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}

_GRADE_THRESHOLDS = [
    ("A", 85),
    ("B", 70),
    ("C", 55),
    ("D", 40),
    ("E", 25),
]


def _score_to_grade(score: float) -> str:
    for grade, threshold in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _format_chf(amount: float | None) -> str:
    """Swiss-format a CHF amount."""
    if amount is None:
        return "-"
    return f"CHF {amount:,.2f}".replace(",", "'")


def _format_date(d: date | datetime | None) -> str:
    """Swiss-format a date (DD.MM.YYYY)."""
    if d is None:
        return "-"
    if isinstance(d, datetime):
        return d.strftime("%d.%m.%Y")
    return d.strftime("%d.%m.%Y")


# ---------------------------------------------------------------------------
# Full report generation
# ---------------------------------------------------------------------------


async def generate_full_report(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Compile a comprehensive building report with all available data.

    Returns None if building not found.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # -- Identity --
    identity = {
        "address": building.address,
        "postal_code": building.postal_code,
        "city": building.city,
        "canton": building.canton,
        "egid": building.egid,
        "egrid": building.egrid,
        "construction_year": building.construction_year,
        "renovation_year": building.renovation_year,
        "building_type": building.building_type,
        "floors_above": building.floors_above,
        "floors_below": building.floors_below,
        "surface_area_m2": building.surface_area_m2,
        "volume_m3": building.volume_m3,
    }

    # -- Passport (trust + completeness) --
    trust_result = await db.execute(
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    trust_obj = trust_result.scalar_one_or_none()
    trust_score = trust_obj.overall_score if trust_obj else 0.0
    trust_trend = trust_obj.trend if trust_obj else None

    # Simplified completeness
    filled = sum(
        1
        for attr in [
            building.construction_year,
            building.building_type,
            building.surface_area_m2,
            building.floors_above,
            building.egid,
            building.egrid,
        ]
        if attr is not None
    )
    completeness_pct = round(filled / 6.0 * 100)

    # Passport grade
    passport_grade = _score_to_grade((trust_score * 50) + (completeness_pct / 2))

    passport = {
        "grade": passport_grade,
        "completeness_pct": completeness_pct,
        "trust_score": round(trust_score * 100),
        "trust_trend": trust_trend,
    }

    # -- Risks (pollutants + overall) --
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_obj = risk_result.scalar_one_or_none()

    pollutant_risks = []
    if risk_obj:
        for pol in ALL_POLLUTANTS:
            prob = getattr(risk_obj, f"{pol}_probability", None)
            if prob is not None:
                level = "critical" if prob > 0.8 else "high" if prob > 0.5 else "medium" if prob > 0.2 else "low"
                pollutant_risks.append(
                    {
                        "pollutant": pol,
                        "probability": round(prob * 100),
                        "level": level,
                    }
                )

    risks = {
        "pollutants": pollutant_risks,
        "overall_grade": risk_obj.overall_risk_level if risk_obj else "unknown",
        "confidence": round((risk_obj.confidence or 0.0) * 100) if risk_obj else 0,
    }

    # -- Compliance --
    artefact_result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = list(artefact_result.scalars().all())

    non_conformities = [a for a in artefacts if a.status in ("draft", "rejected")]
    submitted = [a for a in artefacts if a.status == "submitted"]
    acknowledged = [a for a in artefacts if a.status == "acknowledged"]

    compliance = {
        "status": "compliant" if not non_conformities else "non_compliant",
        "non_conformities_count": len(non_conformities),
        "submitted_count": len(submitted),
        "acknowledged_count": len(acknowledged),
        "total_artefacts": len(artefacts),
    }

    # -- Interventions --
    interv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(interv_result.scalars().all())

    completed_interventions = [
        {
            "title": i.title,
            "type": i.intervention_type,
            "date_end": _format_date(i.date_end),
            "cost_chf": _format_chf(i.cost_chf),
            "contractor": i.contractor_name,
        }
        for i in interventions
        if i.status == "completed"
    ]
    planned_interventions = [
        {
            "title": i.title,
            "type": i.intervention_type,
            "date_start": _format_date(i.date_start),
            "cost_chf": _format_chf(i.cost_chf),
        }
        for i in interventions
        if i.status in ("planned", "in_progress")
    ]

    interventions_section = {
        "completed": completed_interventions,
        "planned": planned_interventions,
        "total_cost_chf": sum(i.cost_chf or 0 for i in interventions if i.cost_chf),
    }

    # -- Financial summary --
    total_cost = sum(i.cost_chf or 0 for i in interventions if i.status == "completed" and i.cost_chf)
    planned_cost = sum(i.cost_chf or 0 for i in interventions if i.status in ("planned", "in_progress") and i.cost_chf)

    financial = {
        "total_spent_chf": _format_chf(total_cost),
        "planned_capex_chf": _format_chf(planned_cost),
        "intervention_count": len(interventions),
    }

    # -- Recommendations --
    recommendations = []

    # From unknowns
    unknown_result = await db.execute(
        select(UnknownIssue).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
            )
        )
    )
    open_unknowns = list(unknown_result.scalars().all())
    for u in open_unknowns[:5]:
        recommendations.append(
            {
                "priority": "high" if u.blocks_readiness else "medium",
                "action": f"Resolve unknown: {u.unknown_type}",
                "detail": u.description or "",
                "source": "unknown_issue",
            }
        )

    # From contradictions
    contra_result = await db.execute(
        select(DataQualityIssue).where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
                DataQualityIssue.status == "open",
            )
        )
    )
    contradictions = list(contra_result.scalars().all())
    for c in contradictions[:3]:
        recommendations.append(
            {
                "priority": "high",
                "action": f"Resolve contradiction: {c.description or c.issue_type}",
                "detail": "",
                "source": "contradiction",
            }
        )

    if completeness_pct < 80:
        recommendations.append(
            {
                "priority": "medium",
                "action": "Improve dossier completeness",
                "detail": f"Current completeness: {completeness_pct}%",
                "source": "completeness",
            }
        )

    # -- Metadata --
    metadata = {
        "generated_at": datetime.now(UTC).isoformat(),
        "data_completeness_pct": completeness_pct,
        "disclaimer": (
            "This report is generated automatically from available data. "
            "It does not constitute a legal assessment or guarantee of compliance. "
            "Professional verification is recommended."
        ),
    }

    return {
        "building_id": str(building_id),
        "identity": identity,
        "passport": passport,
        "risks": risks,
        "compliance": compliance,
        "interventions": interventions_section,
        "financial": financial,
        "recommendations": recommendations,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# PDF HTML payload
# ---------------------------------------------------------------------------

_CSS = """\
body { font-family: 'Helvetica Neue', Arial, sans-serif; margin: 40px; color: #1a1a1a; font-size: 14px; }
h1 { font-size: 24px; border-bottom: 3px solid #dc2626; padding-bottom: 8px; margin-bottom: 24px; }
h2 { font-size: 18px; color: #374151; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; margin-top: 32px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
.logo-placeholder { font-size: 28px; font-weight: bold; color: #dc2626; }
.meta { color: #6b7280; font-size: 12px; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; }
th { background: #f3f4f6; text-align: left; padding: 8px 12px; font-size: 13px; border-bottom: 2px solid #d1d5db; }
td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; }
.grade { display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 16px; }
.grade-A { background: #d1fae5; color: #065f46; }
.grade-B { background: #ecfccb; color: #365314; }
.grade-C { background: #fef9c3; color: #713f12; }
.grade-D { background: #fed7aa; color: #7c2d12; }
.grade-F { background: #fecaca; color: #7f1d1d; }
.score-bar { height: 8px; border-radius: 4px; background: #e5e7eb; margin: 4px 0; }
.score-fill { height: 100%; border-radius: 4px; }
.risk-low { color: #059669; }
.risk-medium { color: #d97706; }
.risk-high { color: #dc2626; }
.risk-critical { color: #7f1d1d; font-weight: bold; }
.footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb; color: #9ca3af; font-size: 11px; }
.recommendation { padding: 8px 12px; margin: 4px 0; border-left: 3px solid #3b82f6; background: #eff6ff; }
.recommendation.high { border-left-color: #dc2626; background: #fef2f2; }
"""


def _risk_class(level: str) -> str:
    return f"risk-{level}" if level in ("low", "medium", "high", "critical") else ""


async def generate_report_pdf_payload(
    db: AsyncSession,
    building_id: UUID,
) -> str | None:
    """Generate HTML payload for Gotenberg PDF conversion.

    Returns None if building not found. Otherwise returns a complete HTML string
    that can be posted to Gotenberg's /forms/chromium/convert/html endpoint.
    """
    report = await generate_full_report(db, building_id)
    if report is None:
        return None

    identity = report["identity"]
    passport = report["passport"]
    risks = report["risks"]
    compliance = report["compliance"]
    interventions = report["interventions"]
    financial = report["financial"]
    recommendations = report["recommendations"]
    metadata = report["metadata"]

    # Build pollutant rows
    pollutant_rows = ""
    for p in risks["pollutants"]:
        pollutant_rows += (
            f"<tr><td>{p['pollutant'].title()}</td>"
            f"<td>{p['probability']}%</td>"
            f'<td class="{_risk_class(p["level"])}">{p["level"].title()}</td></tr>'
        )
    if not pollutant_rows:
        pollutant_rows = '<tr><td colspan="3">Aucune donnee de risque disponible</td></tr>'

    # Build intervention rows
    completed_rows = ""
    for i in interventions["completed"]:
        completed_rows += (
            f"<tr><td>{i['title']}</td><td>{i['type']}</td><td>{i['date_end']}</td><td>{i['cost_chf']}</td></tr>"
        )
    if not completed_rows:
        completed_rows = '<tr><td colspan="4">Aucune intervention terminee</td></tr>'

    planned_rows = ""
    for i in interventions["planned"]:
        planned_rows += (
            f"<tr><td>{i['title']}</td><td>{i['type']}</td><td>{i['date_start']}</td><td>{i['cost_chf']}</td></tr>"
        )
    if not planned_rows:
        planned_rows = '<tr><td colspan="4">Aucune intervention planifiee</td></tr>'

    # Build recommendation rows
    rec_html = ""
    for r in recommendations:
        prio_class = "high" if r["priority"] == "high" else ""
        rec_html += (
            f'<div class="recommendation {prio_class}">'
            f"<strong>{r['action']}</strong>"
            f"{' — ' + r['detail'] if r.get('detail') else ''}"
            f"</div>"
        )
    if not rec_html:
        rec_html = "<p>Aucune recommandation.</p>"

    grade = passport["grade"]
    grade_class = f"grade-{grade}" if grade in ("A", "B", "C", "D") else "grade-F"

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport batiment — {identity["address"]}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="header">
  <div class="logo-placeholder">BatiConnect</div>
  <div class="meta">
    Genere le {_format_date(datetime.now(UTC))}<br>
    Completude des donnees: {metadata["data_completeness_pct"]}%
  </div>
</div>

<h1>Rapport du batiment</h1>

<h2>Identite</h2>
<table>
  <tr><th>Adresse</th><td>{identity["address"]}, {identity["postal_code"]} {identity["city"]}</td></tr>
  <tr><th>Canton</th><td>{identity["canton"]}</td></tr>
  <tr><th>EGID</th><td>{identity["egid"] or "-"}</td></tr>
  <tr><th>EGRID</th><td>{identity["egrid"] or "-"}</td></tr>
  <tr><th>Annee de construction</th><td>{identity["construction_year"] or "-"}</td></tr>
  <tr><th>Type</th><td>{identity["building_type"] or "-"}</td></tr>
  <tr><th>Etages</th><td>{identity["floors_above"] or "-"} hors-sol / {identity["floors_below"] or "-"} sous-sol</td></tr>
  <tr><th>Surface</th><td>{identity["surface_area_m2"] or "-"} m2</td></tr>
</table>

<h2>Passeport</h2>
<table>
  <tr><th>Grade</th><td><span class="grade {grade_class}">{grade}</span></td></tr>
  <tr><th>Completude</th><td>{passport["completeness_pct"]}%</td></tr>
  <tr><th>Score de confiance</th><td>{passport["trust_score"]}%</td></tr>
  <tr><th>Tendance</th><td>{passport["trust_trend"] or "-"}</td></tr>
</table>

<h2>Risques polluants</h2>
<table>
  <tr><th>Polluant</th><th>Probabilite</th><th>Niveau</th></tr>
  {pollutant_rows}
</table>
<p>Risque global: <strong class="{_risk_class(risks["overall_grade"])}">{risks["overall_grade"].title()}</strong>
   (Confiance: {risks["confidence"]}%)</p>

<h2>Conformite</h2>
<table>
  <tr><th>Statut</th><td>{compliance["status"].replace("_", " ").title()}</td></tr>
  <tr><th>Non-conformites</th><td>{compliance["non_conformities_count"]}</td></tr>
  <tr><th>Soumis</th><td>{compliance["submitted_count"]}</td></tr>
  <tr><th>Valides</th><td>{compliance["acknowledged_count"]}</td></tr>
</table>

<h2>Interventions realisees</h2>
<table>
  <tr><th>Titre</th><th>Type</th><th>Date fin</th><th>Cout</th></tr>
  {completed_rows}
</table>

<h2>Interventions planifiees</h2>
<table>
  <tr><th>Titre</th><th>Type</th><th>Date debut</th><th>Cout</th></tr>
  {planned_rows}
</table>

<h2>Resume financier</h2>
<table>
  <tr><th>Total depense</th><td>{financial["total_spent_chf"]}</td></tr>
  <tr><th>CAPEX planifie</th><td>{financial["planned_capex_chf"]}</td></tr>
  <tr><th>Nombre d'interventions</th><td>{financial["intervention_count"]}</td></tr>
</table>

<h2>Recommandations</h2>
{rec_html}

<div class="footer">
  <p>{metadata["disclaimer"]}</p>
  <p>BatiConnect — Batiscan Sarl — {_format_date(datetime.now(UTC))}</p>
</div>
</body>
</html>"""

    return html
