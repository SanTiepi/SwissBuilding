"""Authority report PDF generator — Programme M.1.

Orchestrates data collection from building, diagnostics, samples, risks,
interventions, documents, and compliance artefacts, then renders a 20+ page
HTML payload suitable for Gotenberg PDF conversion.

Killer demo: "Votre dossier complet en 1 PDF, 20 secondes."
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import ALL_POLLUTANTS
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.report_templates import (
    render_action_plan_section,
    render_appendix_section,
    render_compliance_section,
    render_cover_page,
    render_diagnostics_section,
    render_evidence_section,
    render_executive_summary,
    render_recommendations_section,
    render_report_css,
    render_toc,
)

logger = logging.getLogger(__name__)

REPORT_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_date(d: date | datetime | None) -> str:
    if d is None:
        return "-"
    if isinstance(d, datetime):
        return d.strftime("%d.%m.%Y")
    return d.strftime("%d.%m.%Y")


def _format_chf(amount: float | None) -> str:
    if amount is None:
        return "-"
    return f"CHF {amount:,.2f}".replace(",", "'")


def _risk_level(prob: float) -> str:
    if prob > 0.8:
        return "critical"
    if prob > 0.5:
        return "high"
    if prob > 0.2:
        return "medium"
    return "low"


POLLUTANT_LABELS = {
    "asbestos": "Amiante",
    "pcb": "PCB (polychlorobiphenyles)",
    "lead": "Plomb",
    "hap": "HAP (hydrocarbures aromatiques polycycliques)",
    "radon": "Radon",
    "pfas": "PFAS (substances per- et polyfluoroalkylees)",
}


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------


async def _collect_report_data(
    db: AsyncSession,
    building_id: UUID,
    *,
    include_photos: bool = True,
    include_plans: bool = True,
) -> dict[str, Any] | None:
    """Collect all data needed for the authority report."""

    # Building with relationships
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # Diagnostics + samples
    diag_result = await db.execute(
        select(Diagnostic)
        .where(Diagnostic.building_id == building_id)
        .options(selectinload(Diagnostic.samples))
        .order_by(Diagnostic.date_inspection.desc().nullslast())
    )
    diagnostics = list(diag_result.scalars().all())

    # Risk scores
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_obj = risk_result.scalar_one_or_none()

    # Trust score
    trust_result = await db.execute(
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    trust_obj = trust_result.scalar_one_or_none()

    # Actions
    action_result = await db.execute(
        select(ActionItem).where(ActionItem.building_id == building_id).order_by(ActionItem.priority.desc().nullslast())
    )
    actions = list(action_result.scalars().all())

    # Interventions
    interv_result = await db.execute(
        select(Intervention)
        .where(Intervention.building_id == building_id)
        .order_by(Intervention.date_start.desc().nullslast())
    )
    interventions = list(interv_result.scalars().all())

    # Documents
    doc_result = await db.execute(
        select(Document).where(Document.building_id == building_id).order_by(Document.created_at.desc())
    )
    documents = list(doc_result.scalars().all())

    # Compliance artefacts
    comp_result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    compliance_artefacts = list(comp_result.scalars().all())

    # Zones
    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())

    # Collect all samples across diagnostics
    all_samples: list[Sample] = []
    for diag in diagnostics:
        all_samples.extend(diag.samples)

    # Build pollutant risks
    pollutant_risks = []
    if risk_obj:
        for pol in ALL_POLLUTANTS:
            prob = getattr(risk_obj, f"{pol}_probability", None)
            if prob is not None:
                pollutant_risks.append(
                    {
                        "pollutant": pol,
                        "label": POLLUTANT_LABELS.get(pol, pol.title()),
                        "probability": round(prob * 100),
                        "level": _risk_level(prob),
                    }
                )

    # Build identity
    identity = {
        "address": building.address or "Adresse inconnue",
        "postal_code": building.postal_code or "",
        "city": building.city or "",
        "canton": building.canton or "",
        "egid": building.egid or "",
        "egrid": building.egrid or "",
        "construction_year": building.construction_year,
        "renovation_year": building.renovation_year,
        "building_type": building.building_type or "",
        "floors_above": building.floors_above,
        "floors_below": building.floors_below,
        "surface_area_m2": building.surface_area_m2,
        "volume_m3": building.volume_m3,
    }

    # Trust / completeness
    trust_score = trust_obj.overall_score if trust_obj else 0.0
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

    return {
        "identity": identity,
        "diagnostics": diagnostics,
        "samples": all_samples,
        "risk_obj": risk_obj,
        "pollutant_risks": pollutant_risks,
        "trust_score": round(trust_score * 100),
        "completeness_pct": completeness_pct,
        "actions": actions,
        "interventions": interventions,
        "documents": documents,
        "compliance_artefacts": compliance_artefacts,
        "zones": zones,
        "include_photos": include_photos,
        "include_plans": include_plans,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_authority_report(
    db: AsyncSession,
    building_id: UUID,
    *,
    include_photos: bool = True,
    include_plans: bool = True,
    language: str = "fr",
) -> dict[str, Any] | None:
    """Generate a 20+ page authority report as HTML payload.

    Returns dict with html_payload, metadata, or None if building not found.
    """
    data = await _collect_report_data(db, building_id, include_photos=include_photos, include_plans=include_plans)
    if data is None:
        return None

    now = datetime.now(UTC)
    identity = data["identity"]

    # Render all sections
    sections_html = []

    # Pages 1-2: Cover + TOC
    sections_html.append(render_cover_page(identity, now, language))
    sections_html.append(render_toc())

    # Pages 3-5: Executive summary
    sections_html.append(
        render_executive_summary(
            identity=identity,
            pollutant_risks=data["pollutant_risks"],
            risk_obj=data["risk_obj"],
            trust_score=data["trust_score"],
            completeness_pct=data["completeness_pct"],
            diagnostics=data["diagnostics"],
            actions=data["actions"],
        )
    )

    # Pages 6-10: Detailed diagnostics per pollutant
    sections_html.append(
        render_diagnostics_section(
            diagnostics=data["diagnostics"],
            samples=data["samples"],
            pollutant_risks=data["pollutant_risks"],
        )
    )

    # Pages 11-14: Compliance status
    sections_html.append(
        render_compliance_section(
            compliance_artefacts=data["compliance_artefacts"],
            zones=data["zones"],
        )
    )

    # Pages 15-17: Recommendations + action plan
    sections_html.append(
        render_recommendations_section(
            actions=data["actions"],
            pollutant_risks=data["pollutant_risks"],
        )
    )
    sections_html.append(
        render_action_plan_section(
            interventions=data["interventions"],
        )
    )

    # Pages 18-20: Evidence (documents, photos)
    sections_html.append(
        render_evidence_section(
            documents=data["documents"],
            include_photos=data["include_photos"],
        )
    )

    # Pages 21+: Appendix (legal, glossary, metadata)
    sections_html.append(
        render_appendix_section(
            identity=identity,
            now=now,
            version=REPORT_VERSION,
        )
    )

    # Assemble full HTML
    body_html = "\n".join(sections_html)
    css = render_report_css()

    html = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
<meta charset="UTF-8">
<title>Rapport technique autorite — {identity["address"]}</title>
<style>{css}</style>
</head>
<body>
{body_html}
</body>
</html>"""

    # Compute hash
    sha256 = hashlib.sha256(html.encode("utf-8")).hexdigest()

    return {
        "building_id": str(building_id),
        "status": "generated",
        "report_type": "authority",
        "html_payload": html,
        "html_payload_length": len(html),
        "sha256": sha256,
        "generated_at": now.isoformat(),
        "version": REPORT_VERSION,
        "language": language,
        "sections_count": len(sections_html),
        "include_photos": include_photos,
        "include_plans": include_plans,
        "metadata": {
            "address": identity["address"],
            "egid": identity["egid"],
            "canton": identity["canton"],
            "completeness_pct": data["completeness_pct"],
            "diagnostics_count": len(data["diagnostics"]),
            "samples_count": len(data["samples"]),
            "documents_count": len(data["documents"]),
            "disclaimer": (
                "Ce rapport est genere automatiquement par BatiConnect a partir des "
                "donnees disponibles. Il ne constitue pas une expertise legale et ne "
                "garantit pas la conformite reglementaire. Une verification professionnelle "
                "est recommandee."
            ),
            "emitter": "BatiConnect — Batiscan Sarl",
        },
    }
