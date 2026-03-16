"""Building dossier generation service.

Generates a complete HTML dossier for a building, optionally converting to PDF via Gotenberg.
Falls back to HTML if Gotenberg is not available.
Integrates completeness engine, compliance engine, and risk engine data.
"""

import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gotenberg PDF conversion
# ---------------------------------------------------------------------------


async def html_to_pdf(html_content: str) -> bytes:
    """Convert HTML to PDF via Gotenberg."""
    url = f"{settings.GOTENBERG_URL}/forms/chromium/convert/html"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            files={"index.html": ("index.html", html_content.encode(), "text/html")},
            data={
                "marginTop": "1",
                "marginBottom": "1",
                "marginLeft": "0.8",
                "marginRight": "0.8",
                "paperWidth": "8.27",
                "paperHeight": "11.69",
            },
        )
        response.raise_for_status()
        return response.content


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


async def _fetch_building_data(db: AsyncSession, building_id):
    """Fetch all building-related data for dossier generation."""
    from app.models.action_item import ActionItem
    from app.models.building import Building
    from app.models.building_element import BuildingElement
    from app.models.building_risk_score import BuildingRiskScore
    from app.models.diagnostic import Diagnostic
    from app.models.document import Document
    from app.models.evidence_link import EvidenceLink
    from app.models.intervention import Intervention
    from app.models.technical_plan import TechnicalPlan
    from app.models.zone import Zone

    # Building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError("Building not found")

    # Diagnostics with samples
    diags_result = await db.execute(
        select(Diagnostic)
        .options(selectinload(Diagnostic.samples))
        .where(Diagnostic.building_id == building_id)
        .order_by(Diagnostic.created_at.desc())
    )
    diagnostics = list(diags_result.scalars().all())

    # Zones with elements and materials
    zones_result = await db.execute(
        select(Zone)
        .options(selectinload(Zone.elements).selectinload(BuildingElement.materials))
        .where(Zone.building_id == building_id)
        .order_by(Zone.floor_number.nulls_last(), Zone.name)
    )
    zones = list(zones_result.scalars().all())

    # Interventions
    interv_result = await db.execute(
        select(Intervention)
        .where(Intervention.building_id == building_id)
        .order_by(Intervention.date_start.desc().nulls_last())
    )
    interventions = list(interv_result.scalars().all())

    # Risk scores
    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_scores = risk_result.scalar_one_or_none()

    # Action items
    actions_result = await db.execute(
        select(ActionItem)
        .where(ActionItem.building_id == building_id)
        .order_by(ActionItem.priority.desc(), ActionItem.created_at.desc())
    )
    action_items = list(actions_result.scalars().all())

    # Evidence links
    evidence_links = []
    if risk_scores:
        ev_result = await db.execute(
            select(EvidenceLink)
            .where(EvidenceLink.target_type == "risk_score")
            .where(EvidenceLink.target_id == risk_scores.id)
        )
        evidence_links.extend(ev_result.scalars().all())

    for action in action_items:
        ev_result2 = await db.execute(
            select(EvidenceLink)
            .where(EvidenceLink.target_type == "action_item")
            .where(EvidenceLink.target_id == action.id)
        )
        evidence_links.extend(ev_result2.scalars().all())

    # Technical plans
    plans_result = await db.execute(
        select(TechnicalPlan)
        .where(TechnicalPlan.building_id == building_id)
        .order_by(TechnicalPlan.plan_type, TechnicalPlan.created_at)
    )
    plans = list(plans_result.scalars().all())

    # Documents
    docs_result = await db.execute(
        select(Document).where(Document.building_id == building_id).order_by(Document.created_at.desc())
    )
    documents = list(docs_result.scalars().all())

    return {
        "building": building,
        "diagnostics": diagnostics,
        "zones": zones,
        "interventions": interventions,
        "risk_scores": risk_scores,
        "action_items": action_items,
        "evidence_links": evidence_links,
        "plans": plans,
        "documents": documents,
    }


# ---------------------------------------------------------------------------
# Threshold pre-resolution
# ---------------------------------------------------------------------------

_POLLUTANT_TYPES = ["asbestos", "pcb", "lead", "hap", "radon"]

# Units used across SWISS_THRESHOLDS — collected for pack lookup attempts
_KNOWN_UNITS = [
    "percent_weight",
    "fibers_per_m3",
    "mg_per_kg",
    "ng_per_m3",
    "ug_per_l",
    "bq_per_m3",
]


async def _resolve_thresholds_for_building(db: AsyncSession, building) -> dict:
    """
    Pre-resolve regulatory thresholds from packs for a building's jurisdiction.

    Returns a dict keyed by (pollutant_type, unit) → {threshold, unit, legal_ref, ...}.
    Empty dict if jurisdiction_id is None or no packs found.
    """
    resolved: dict[tuple[str, str], dict] = {}
    jurisdiction_id = getattr(building, "jurisdiction_id", None)
    if jurisdiction_id is None:
        return resolved

    try:
        from app.services.rule_resolver import resolve_threshold

        for pollutant in _POLLUTANT_TYPES:
            for unit in _KNOWN_UNITS:
                result = await resolve_threshold(db, jurisdiction_id, pollutant, unit)
                if result is not None:
                    resolved[(pollutant, unit)] = result
    except Exception as e:
        logger.warning(f"Failed to resolve thresholds for jurisdiction {jurisdiction_id}: {e}")

    return resolved


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_building_dossier(
    db: AsyncSession,
    building_id,
    requested_by_id,
    stage: str = "avt",
) -> dict:
    """
    Generate a complete building dossier.

    Returns a dict with:
    - html: str (the generated HTML)
    - pdf_bytes: bytes | None (PDF if Gotenberg available, else None)
    - export_job_id: str (ID of the created ExportJob)
    """
    from app.models.export_job import ExportJob

    data = await _fetch_building_data(db, building_id)

    # Evaluate completeness
    completeness = None
    try:
        from app.services.completeness_engine import evaluate_completeness

        completeness = await evaluate_completeness(db, building_id, workflow_stage=stage)
    except Exception as e:
        logger.warning(f"Failed to evaluate completeness for building {building_id}: {e}")

    # Get compliance data — prefer rule_resolver packs, fall back to hardcoded
    compliance = None
    try:
        from app.services.rule_resolver import resolve_cantonal_requirements

        compliance = await resolve_cantonal_requirements(db, data["building"].jurisdiction_id)
    except Exception as e:
        logger.warning(f"Failed to resolve cantonal requirements: {e}")
    if compliance is None:
        try:
            from app.services.compliance_engine import get_cantonal_requirements

            canton = data["building"].canton or "VD"
            compliance = get_cantonal_requirements(canton)
        except Exception as e:
            logger.warning(f"Failed to get cantonal requirements for canton {data['building'].canton}: {e}")

    # Pre-resolve thresholds from packs for sample display and reference table
    resolved_thresholds = await _resolve_thresholds_for_building(db, data["building"])

    # Generate HTML
    html = _render_dossier_html(
        building=data["building"],
        diagnostics=data["diagnostics"],
        zones=data["zones"],
        interventions=data["interventions"],
        risk_scores=data["risk_scores"],
        action_items=data["action_items"],
        evidence_links=data["evidence_links"],
        plans=data["plans"],
        documents=data["documents"],
        completeness=completeness,
        compliance=compliance,
        stage=stage,
        resolved_thresholds=resolved_thresholds,
    )

    # Try PDF conversion via Gotenberg
    pdf_bytes = None
    if settings.GOTENBERG_URL:
        try:
            pdf_bytes = await html_to_pdf(html)
        except Exception as e:
            logger.warning(f"Failed to convert dossier to PDF via Gotenberg: {e}")

    # Create ExportJob
    export_job = ExportJob(
        id=uuid.uuid4(),
        type="building_dossier",
        building_id=building_id,
        status="completed",
        requested_by=requested_by_id,
        file_path=None,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db.add(export_job)
    await db.commit()

    return {
        "html": html,
        "pdf_bytes": pdf_bytes,
        "export_job_id": str(export_job.id),
    }


async def generate_dossier_preview(
    db: AsyncSession,
    building_id,
    stage: str = "avt",
) -> str:
    """Generate just the HTML preview without PDF conversion or ExportJob creation."""
    data = await _fetch_building_data(db, building_id)

    # Evaluate completeness
    completeness = None
    try:
        from app.services.completeness_engine import evaluate_completeness

        completeness = await evaluate_completeness(db, building_id, workflow_stage=stage)
    except Exception as e:
        logger.warning(f"Failed to evaluate completeness for building {building_id} preview: {e}")

    # Get compliance data — prefer rule_resolver packs, fall back to hardcoded
    compliance = None
    try:
        from app.services.rule_resolver import resolve_cantonal_requirements

        compliance = await resolve_cantonal_requirements(db, data["building"].jurisdiction_id)
    except Exception as e:
        logger.warning(f"Failed to resolve cantonal requirements for preview: {e}")
    if compliance is None:
        try:
            from app.services.compliance_engine import get_cantonal_requirements

            canton = data["building"].canton or "VD"
            compliance = get_cantonal_requirements(canton)
        except Exception as e:
            logger.warning(f"Failed to get cantonal requirements for canton {data['building'].canton} preview: {e}")

    # Pre-resolve thresholds from packs for sample display and reference table
    resolved_thresholds = await _resolve_thresholds_for_building(db, data["building"])

    return _render_dossier_html(
        building=data["building"],
        diagnostics=data["diagnostics"],
        zones=data["zones"],
        interventions=data["interventions"],
        risk_scores=data["risk_scores"],
        action_items=data["action_items"],
        evidence_links=data["evidence_links"],
        plans=data["plans"],
        documents=data["documents"],
        completeness=completeness,
        compliance=compliance,
        stage=stage,
        resolved_thresholds=resolved_thresholds,
    )


# ---------------------------------------------------------------------------
# HTML rendering helpers
# ---------------------------------------------------------------------------

_RISK_COLORS = {
    "low": "#22c55e",
    "medium": "#eab308",
    "high": "#f97316",
    "critical": "#ef4444",
    "unknown": "#6b7280",
}

_PRIORITY_COLORS = {
    "low": "#6b7280",
    "medium": "#3b82f6",
    "high": "#f97316",
    "critical": "#ef4444",
}

_STATUS_ICONS = {
    "complete": '<span style="color:#22c55e;font-weight:bold;">&#10003;</span>',
    "partial": '<span style="color:#eab308;font-weight:bold;">&#9888;</span>',
    "missing": '<span style="color:#ef4444;font-weight:bold;">&#10007;</span>',
    "not_applicable": '<span style="color:#9ca3af;">n/a</span>',
}

_STAGE_LABELS = {
    "avt": "Dossier de diagnostic avant travaux (AvT)",
    "apt": "Dossier de diagnostic apres travaux (ApT)",
}

# Em-dash constant for use in f-string expressions (Python 3.11 compat)
_EM = "\u2014"


def _risk_badge(level: str) -> str:
    """Render an inline HTML badge for a risk level."""
    color = _RISK_COLORS.get(level, "#6b7280")
    return (
        f'<span style="display:inline-block;background:{color};color:white;'
        f'padding:3px 10px;border-radius:4px;font-size:12px;font-weight:600;">'
        f"{level.upper()}</span>"
    )


def _priority_badge(priority: str) -> str:
    """Render an inline HTML badge for a priority level."""
    color = _PRIORITY_COLORS.get(priority, "#6b7280")
    return (
        f'<span style="display:inline-block;background:{color};color:white;'
        f'padding:2px 8px;border-radius:3px;font-size:11px;font-weight:500;">'
        f"{priority}</span>"
    )


def _completeness_bar(score: float) -> str:
    """Render a horizontal completeness progress bar."""
    pct = int(score * 100)
    if pct >= 95:
        bar_color = "#22c55e"
    elif pct >= 70:
        bar_color = "#eab308"
    else:
        bar_color = "#ef4444"
    return (
        f'<div style="background:#e5e7eb;border-radius:6px;height:24px;width:100%;'
        f'max-width:400px;overflow:hidden;margin:8px 0;">'
        f'<div style="background:{bar_color};height:100%;width:{pct}%;'
        f"border-radius:6px;display:flex;align-items:center;justify-content:center;"
        f'color:white;font-size:12px;font-weight:600;min-width:40px;">{pct}%</div>'
        f"</div>"
    )


def _completeness_badge(score: float) -> str:
    """Render a circular completeness score badge for the cover page."""
    pct = int(score * 100)
    if pct >= 95:
        color = "#22c55e"
    elif pct >= 70:
        color = "#eab308"
    else:
        color = "#ef4444"
    return (
        f'<div style="display:inline-block;width:80px;height:80px;border-radius:50%;'
        f"background:{color};color:white;text-align:center;line-height:80px;"
        f'font-size:24px;font-weight:bold;margin-top:12px;">{pct}%</div>'
    )


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_DOSSIER_CSS = """
body {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  margin: 0; padding: 0; color: #1a1a1a; line-height: 1.6; font-size: 13px;
}
.page { padding: 30px 40px; }
h1 { color: #1e40af; font-size: 22px; border-bottom: 3px solid #1e40af; padding-bottom: 6px; margin-top: 0; }
h2 {
  color: #1e3a5f; font-size: 16px; margin-top: 28px;
  border-bottom: 2px solid #dbeafe; padding-bottom: 4px;
}
h3 { color: #374151; font-size: 14px; margin-top: 16px; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; }
th, td { border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; font-size: 12px; }
th { background: #f0f4ff; font-weight: 600; color: #1e3a5f; }
tr:nth-child(even) { background: #f9fafb; }
.cover {
  text-align: center; padding: 48px 40px; margin-bottom: 0;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
  color: white; page-break-after: always;
}
.cover h1 { color: white; border: none; font-size: 32px; margin-bottom: 8px; }
.cover p { font-size: 15px; opacity: 0.92; margin: 4px 0; }
.cover .subtitle { font-size: 13px; opacity: 0.75; margin-top: 20px; }
.section { page-break-inside: avoid; margin-bottom: 20px; }
.section-number {
  display: inline-block; background: #1e40af; color: white;
  width: 28px; height: 28px; border-radius: 50%; text-align: center;
  line-height: 28px; font-size: 14px; font-weight: bold; margin-right: 8px;
}
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 500;
}
.evidence-chain {
  background: #f9fafb; border: 1px solid #e5e7eb;
  border-radius: 6px; padding: 10px; margin: 6px 0; font-size: 12px;
}
.exceeded-yes { background: #fef2f2; color: #dc2626; font-weight: 600; }
.exceeded-no { color: #16a34a; }
.missing-item { color: #dc2626; font-weight: 500; }
.footer {
  margin-top: 36px; padding-top: 12px; border-top: 2px solid #1e40af;
  font-size: 10px; color: #6b7280; text-align: center;
}
.info-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 4px 24px; margin: 8px 0;
}
.info-grid dt { font-weight: 600; color: #374151; }
.info-grid dd { margin: 0; color: #4b5563; }
@media print {
  .cover { page-break-after: always; }
  .section { page-break-inside: avoid; }
}
"""


# ---------------------------------------------------------------------------
# Main HTML renderer
# ---------------------------------------------------------------------------


def _render_dossier_html(
    *,
    building,
    diagnostics,
    zones,
    interventions,
    risk_scores,
    action_items,
    evidence_links,
    plans,
    documents,
    completeness=None,
    compliance=None,
    stage: str = "avt",
    resolved_thresholds: dict | None = None,
) -> str:
    """Render the complete building dossier as HTML with inline CSS."""
    now = datetime.now(UTC).strftime("%d.%m.%Y %H:%M")
    stage_label = _STAGE_LABELS.get(stage, _STAGE_LABELS["avt"])

    # Compute completeness score for cover badge
    completeness_score = completeness.overall_score if completeness else 0.0

    html_parts: list[str] = []

    # --- Document start ---
    html_parts.append(f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Dossier — {building.address}, {building.city}</title>
<style>{_DOSSIER_CSS}</style>
</head>
<body>""")

    # --- COVER PAGE ---
    egid_display = building.egid or "\u2014"
    egrid_display = getattr(building, "egrid", None) or "\u2014"
    html_parts.append(f"""
<div class="cover">
  <div style="font-size:14px;letter-spacing:3px;opacity:0.7;margin-bottom:12px;">SWISSBUILDINGOS</div>
  <h1>DOSSIER BATIMENT</h1>
  <p style="font-size:18px;font-weight:600;margin-top:16px;">{building.address}</p>
  <p>{building.postal_code} {building.city} ({building.canton})</p>
  <p style="font-size:13px;margin-top:12px;">EGID: {egid_display} &nbsp;|&nbsp; EGRID: {egrid_display}</p>
  <div style="margin-top:20px;padding:12px;background:rgba(255,255,255,0.15);border-radius:8px;display:inline-block;">
    <div style="font-size:12px;opacity:0.8;">Type de dossier</div>
    <div style="font-size:15px;font-weight:600;">{stage_label}</div>
  </div>
  {_completeness_badge(completeness_score)}
  <p class="subtitle">Genere le {now} par SwissBuildingOS</p>
</div>
""")

    # --- SECTION 1: Building Identity ---
    html_parts.append("""<div class="page">""")
    html_parts.append("""<div class="section">
<h2><span class="section-number">1</span>Identite du batiment</h2>""")

    construction_year = building.construction_year or "\u2014"
    building_type = building.building_type or "\u2014"
    floors = getattr(building, "floors", None) or "\u2014"
    surface = getattr(building, "surface_m2", None)
    surface_display = f"{surface} m2" if surface else "\u2014"
    lat = getattr(building, "latitude", None)
    lon = getattr(building, "longitude", None)
    coords = f"{lat}, {lon}" if lat and lon else "\u2014"

    html_parts.append(f"""
<dl class="info-grid">
  <dt>Adresse</dt><dd>{building.address}, {building.postal_code} {building.city}</dd>
  <dt>Canton</dt><dd>{building.canton or _EM}</dd>
  <dt>EGID</dt><dd>{egid_display}</dd>
  <dt>EGRID</dt><dd>{egrid_display}</dd>
  <dt>Annee de construction</dt><dd>{construction_year}</dd>
  <dt>Type de batiment</dt><dd>{building_type}</dd>
  <dt>Nombre d'etages</dt><dd>{floors}</dd>
  <dt>Surface</dt><dd>{surface_display}</dd>
  <dt>Coordonnees</dt><dd>{coords}</dd>
</dl>
</div>
""")

    # --- SECTION 2: Completeness Assessment ---
    html_parts.append("""<div class="section">
<h2><span class="section-number">2</span>Evaluation de la completude</h2>""")

    if completeness:
        html_parts.append(f"""
<p><strong>Score global:</strong> {int(completeness.overall_score * 100)}%
&nbsp;&mdash;&nbsp;
{
            "<span style='color:#22c55e;font-weight:600;'>Pret</span>"
            if completeness.ready_to_proceed
            else "<span style='color:#ef4444;font-weight:600;'>Incomplet</span>"
        }</p>
{_completeness_bar(completeness.overall_score)}
<table>
  <tr><th>Statut</th><th>Verification</th><th>Categorie</th><th>Details</th></tr>""")
        for check in completeness.checks:
            icon = _STATUS_ICONS.get(check.status, "")
            row_style = ' style="background:#fef2f2;"' if check.status == "missing" else ""
            detail_class = ' class="missing-item"' if check.status == "missing" else ""
            html_parts.append(
                f"<tr{row_style}><td>{icon}</td><td>{check.label_key}</td>"
                f"<td>{check.category}</td><td{detail_class}>{check.details or _EM}</td></tr>"
            )
        html_parts.append("</table>")

        if completeness.missing_items:
            html_parts.append("<h3>Elements manquants</h3><ul>")
            for item in completeness.missing_items:
                html_parts.append(f'<li class="missing-item">{item}</li>')
            html_parts.append("</ul>")
    else:
        html_parts.append("<p><em>Evaluation de completude non disponible.</em></p>")

    html_parts.append("</div>")

    # --- SECTION 3: Risk Summary ---
    html_parts.append("""<div class="section">
<h2><span class="section-number">3</span>Synthese des risques</h2>""")

    if risk_scores:
        pollutant_rows = [
            ("Amiante (Asbest)", risk_scores.asbestos_probability),
            ("PCB", risk_scores.pcb_probability),
            ("Plomb (Blei)", risk_scores.lead_probability),
            ("HAP (PAK)", risk_scores.hap_probability),
            ("Radon", risk_scores.radon_probability),
        ]
        html_parts.append(f"""
<p><strong>Niveau global:</strong> {_risk_badge(risk_scores.overall_risk_level)}
&nbsp;&mdash;&nbsp; Confiance: {risk_scores.confidence:.0%}
&nbsp;|&nbsp; Source: {risk_scores.data_source}</p>
<table>
  <tr><th>Polluant</th><th>Probabilite</th><th>Niveau</th></tr>""")
        for name, prob in pollutant_rows:
            from app.services.risk_engine import calculate_overall_risk_level

            level = calculate_overall_risk_level({name: prob})
            color = _RISK_COLORS.get(level, "#6b7280")
            html_parts.append(
                f'<tr><td>{name}</td><td style="text-align:center;">{prob:.0%}</td>'
                f'<td style="background:{color}20;text-align:center;">{_risk_badge(level)}</td></tr>'
            )
        html_parts.append("</table>")
    else:
        html_parts.append("<p><em>Aucune evaluation de risque disponible.</em></p>")

    html_parts.append("</div>")

    # --- SECTION 4: Diagnostic Details ---
    html_parts.append("""<div class="section">
<h2><span class="section-number">4</span>Details des diagnostics</h2>""")

    if diagnostics:
        for diag in diagnostics:
            html_parts.append(
                f"<h3>{diag.diagnostic_type} &mdash; "
                f"{_risk_badge(diag.status) if diag.status in _RISK_COLORS else diag.status}</h3>"
            )
            html_parts.append(
                f"<p><strong>Contexte:</strong> {diag.diagnostic_context or _EM} &nbsp;|&nbsp; "
                f"<strong>Inspection:</strong> {diag.date_inspection or _EM} &nbsp;|&nbsp; "
                f"<strong>Laboratoire:</strong> {diag.laboratory or _EM}"
            )
            if diag.laboratory_report_number:
                html_parts.append(f" &nbsp;|&nbsp; <strong>Rapport:</strong> {diag.laboratory_report_number}")
            html_parts.append("</p>")

            if diag.samples:
                html_parts.append(
                    "<table><tr><th>N\u00b0</th><th>Localisation</th><th>Materiau</th>"
                    "<th>Polluant</th><th>Concentration</th><th>Seuil</th><th>Depasse</th>"
                    "<th>Cat. CFST</th></tr>"
                )
                for s in diag.samples:
                    loc = " / ".join(filter(None, [s.location_floor, s.location_room, s.location_detail]))
                    exceeded_class = "exceeded-yes" if s.threshold_exceeded else "exceeded-no"
                    exceeded_text = "OUI" if s.threshold_exceeded else "non"
                    conc = f"{s.concentration} {s.unit or ''}" if s.concentration is not None else "\u2014"

                    # Get threshold for display — prefer resolved pack data, fall back to hardcoded
                    threshold_display = "\u2014"
                    _poll = (s.pollutant_type or "").lower()
                    _unit = s.unit or ""
                    if resolved_thresholds and (_poll, _unit) in resolved_thresholds:
                        _rt = resolved_thresholds[(_poll, _unit)]
                        threshold_display = f"{_rt['threshold']} {_rt['unit']}"
                    else:
                        try:
                            from app.services.compliance_engine import _find_matching_threshold

                            entry = _find_matching_threshold(_poll, _unit)
                            if entry:
                                threshold_display = f"{entry['threshold']} {entry['unit']}"
                        except Exception as e:
                            logger.warning(f"Failed to find matching threshold for {_poll}/{_unit}: {e}")

                    html_parts.append(
                        f"<tr><td>{s.sample_number}</td><td>{loc or _EM}</td>"
                        f"<td>{s.material_category or _EM}</td><td>{s.pollutant_type or _EM}</td>"
                        f"<td>{conc}</td><td>{threshold_display}</td>"
                        f'<td class="{exceeded_class}">{exceeded_text}</td>'
                        f"<td>{s.cfst_work_category or _EM}</td></tr>"
                    )
                html_parts.append("</table>")
            else:
                html_parts.append("<p><em>Aucun echantillon pour ce diagnostic.</em></p>")
    else:
        html_parts.append("<p><em>Aucun diagnostic enregistre.</em></p>")

    html_parts.append("</div>")

    # --- SECTION 5: Compliance Requirements ---
    html_parts.append("""<div class="section">
<h2><span class="section-number">5</span>Exigences reglementaires</h2>""")

    if compliance:
        html_parts.append(f"""
<dl class="info-grid">
  <dt>Canton</dt><dd>{compliance.get("canton", _EM)}</dd>
  <dt>Autorite competente</dt><dd>{compliance.get("authority_name", _EM)}</dd>
  <dt>Formulaire requis</dt><dd>{compliance.get("form_name", _EM)}</dd>
  <dt>Delai de notification</dt><dd>{compliance.get("notification_delay_days", _EM)} jours</dd>
  <dt>Diagnostic avant annee</dt><dd>{compliance.get("diagnostic_required_before_year", _EM)}</dd>
  <dt>Plan d'elimination requis</dt>
  <dd>{"Oui" if compliance.get("requires_waste_elimination_plan") else "Non"}</dd>
</dl>""")
    else:
        html_parts.append("<p><em>Donnees reglementaires cantonales non disponibles.</em></p>")

    # Applicable thresholds reference table — overlay resolved pack data on hardcoded defaults
    html_parts.append("""
<h3>Seuils reglementaires suisses applicables</h3>
<table>
  <tr><th>Polluant</th><th>Type de mesure</th><th>Seuil</th><th>Unite</th><th>Reference legale</th></tr>""")
    from app.services.compliance_engine import SWISS_THRESHOLDS

    pollutant_names = {
        "asbestos": "Amiante",
        "pcb": "PCB",
        "lead": "Plomb",
        "hap": "HAP",
        "radon": "Radon",
    }
    for pollutant, entries in SWISS_THRESHOLDS.items():
        for measure_type, entry in entries.items():
            # Check if pack data overrides this threshold
            rt_key = (pollutant, entry["unit"])
            if resolved_thresholds and rt_key in resolved_thresholds:
                rt = resolved_thresholds[rt_key]
                html_parts.append(
                    f"<tr><td>{pollutant_names.get(pollutant, pollutant)}</td>"
                    f"<td>{measure_type}</td><td>{rt['threshold']}</td>"
                    f"<td>{rt['unit']}</td><td>{rt.get('legal_ref', entry['legal_ref'])}</td></tr>"
                )
            else:
                html_parts.append(
                    f"<tr><td>{pollutant_names.get(pollutant, pollutant)}</td>"
                    f"<td>{measure_type}</td><td>{entry['threshold']}</td>"
                    f"<td>{entry['unit']}</td><td>{entry['legal_ref']}</td></tr>"
                )
    html_parts.append("</table>")

    # SUVA notification status
    has_positive_asbestos = False
    suva_notified = False
    for diag in diagnostics:
        for s in getattr(diag, "samples", []):
            if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded:
                has_positive_asbestos = True
        if diag.suva_notification_required and diag.suva_notification_date:
            suva_notified = True

    if has_positive_asbestos:
        suva_status = (
            '<span style="color:#22c55e;font-weight:600;">Notification SUVA effectuee</span>'
            if suva_notified
            else '<span style="color:#ef4444;font-weight:600;">Notification SUVA requise mais non effectuee</span>'
        )
        html_parts.append(f"<p><strong>SUVA:</strong> {suva_status}</p>")

    # Waste disposal summary from samples
    waste_samples = []
    for diag in diagnostics:
        for s in getattr(diag, "samples", []):
            if s.threshold_exceeded and s.waste_disposal_type:
                waste_samples.append(s)
    if waste_samples:
        html_parts.append("""
<h3>Classification des dechets (OLED)</h3>
<table>
  <tr><th>Polluant</th><th>Materiau</th><th>Type de dechet</th></tr>""")
        for ws in waste_samples:
            html_parts.append(
                f"<tr><td>{ws.pollutant_type or _EM}</td>"
                f"<td>{ws.material_category or _EM}</td>"
                f"<td>{ws.waste_disposal_type}</td></tr>"
            )
        html_parts.append("</table>")

    html_parts.append("</div>")

    # --- SECTION 6: Actions ---
    html_parts.append("""<div class="section">
<h2><span class="section-number">6</span>Actions recommandees</h2>""")

    if action_items:
        html_parts.append(
            "<table><tr><th>Priorite</th><th>Action</th><th>Type</th>"
            "<th>Statut</th><th>Echeance</th><th>Assigne a</th></tr>"
        )
        for action in action_items:
            assignee = getattr(action, "assigned_to", None) or "\u2014"
            html_parts.append(
                f"<tr><td>{_priority_badge(action.priority)}</td><td>{action.title}</td>"
                f"<td>{action.action_type}</td><td>{action.status}</td>"
                f"<td>{action.due_date or _EM}</td><td>{assignee}</td></tr>"
            )
        html_parts.append("</table>")
    else:
        html_parts.append("<p><em>Aucune action en cours.</em></p>")

    html_parts.append("</div>")

    # --- SECTION 7: Document Inventory ---
    html_parts.append("""<div class="section">
<h2><span class="section-number">7</span>Inventaire des documents</h2>""")

    if documents:
        html_parts.append("<table><tr><th>Type</th><th>Nom du fichier</th><th>Taille</th><th>Date</th></tr>")
        for doc in documents:
            size = f"{doc.file_size_bytes / 1024:.0f} Ko" if doc.file_size_bytes else "\u2014"
            html_parts.append(
                f"<tr><td>{doc.document_type or _EM}</td><td>{doc.file_name}</td>"
                f"<td>{size}</td><td>{doc.created_at}</td></tr>"
            )
        html_parts.append("</table>")
    else:
        html_parts.append("<p><em>Aucun document attache.</em></p>")

    # Technical plans
    if plans:
        html_parts.append("<h3>Plans techniques</h3>")
        html_parts.append("<table><tr><th>Type</th><th>Titre</th><th>Version</th><th>Fichier</th></tr>")
        for plan in plans:
            html_parts.append(
                f"<tr><td>{plan.plan_type}</td><td>{plan.title}</td>"
                f"<td>{plan.version or _EM}</td><td>{plan.file_name}</td></tr>"
            )
        html_parts.append("</table>")

    html_parts.append("</div>")

    # --- Evidence Chain (if any) ---
    if evidence_links:
        html_parts.append("""<div class="section">
<h2>Chaine de preuve</h2>""")
        for ev in evidence_links:
            legal = f" &mdash; <strong>{ev.legal_reference}</strong>" if ev.legal_reference else ""
            conf = f" (confiance: {ev.confidence:.0%})" if ev.confidence else ""
            explanation_html = f"<br><small>{ev.explanation}</small>" if ev.explanation else ""
            html_parts.append(
                f'<div class="evidence-chain">'
                f"  <strong>{ev.source_type}</strong> &rarr; <em>{ev.relationship}</em>"
                f" &rarr; <strong>{ev.target_type}</strong>{legal}{conf}"
                f"  {explanation_html}"
                f"</div>"
            )
        html_parts.append("</div>")

    # --- Metadata ---
    html_parts.append(f"""
<div class="section">
<h2>Metadonnees et provenance</h2>
<dl class="info-grid">
  <dt>Source dataset</dt><dd>{building.source_dataset or _EM}</dd>
  <dt>Importe le</dt><dd>{building.source_imported_at or _EM}</dd>
  <dt>Cree le</dt><dd>{building.created_at}</dd>
  <dt>Derniere mise a jour</dt><dd>{building.updated_at}</dd>
</dl>
</div>
""")

    # --- FOOTER ---
    html_parts.append(f"""
<div class="footer">
  <p>SwissBuildingOS &mdash; Dossier batiment genere automatiquement le {now}</p>
  <p><strong>Ce document ne constitue pas une garantie de conformite legale.</strong>
  Les donnees proviennent de sources publiques et de diagnostics enregistres dans le systeme.</p>
  <p>Page generee pour: {building.address}, {building.postal_code} {building.city}</p>
</div>
</div><!-- .page -->
</body>
</html>""")

    return "\n".join(html_parts)
