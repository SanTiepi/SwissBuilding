"""HTML template sections for the authority report PDF.

Each function renders one logical section of the 20+ page report.
The HTML is designed for Gotenberg chromium-based PDF conversion with
proper page breaks, headers, and professional styling.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_date(d: date | datetime | None) -> str:
    if d is None:
        return "-"
    if isinstance(d, datetime):
        return d.strftime("%d.%m.%Y")
    return d.strftime("%d.%m.%Y")


def _fmt_chf(amount: float | None) -> str:
    if amount is None:
        return "-"
    return f"CHF {amount:,.2f}".replace(",", "'")


def _risk_badge(level: str) -> str:
    colors = {
        "critical": "#7f1d1d",
        "high": "#dc2626",
        "medium": "#d97706",
        "low": "#059669",
        "unknown": "#6b7280",
    }
    bg_colors = {
        "critical": "#fecaca",
        "high": "#fee2e2",
        "medium": "#fef3c7",
        "low": "#d1fae5",
        "unknown": "#f3f4f6",
    }
    color = colors.get(level, "#6b7280")
    bg = bg_colors.get(level, "#f3f4f6")
    return f'<span class="risk-badge" style="color:{color};background:{bg}">{level.upper()}</span>'


POLLUTANT_LABELS = {
    "asbestos": "Amiante",
    "pcb": "PCB (polychlorobiphenyles)",
    "lead": "Plomb",
    "hap": "HAP",
    "radon": "Radon",
    "pfas": "PFAS",
}

POLLUTANT_REGULATIONS = {
    "asbestos": "OTConst Art. 60a, 82-86 / CFST 6503",
    "pcb": "ORRChim Annexe 2.15 (seuil: 50 mg/kg)",
    "lead": "ORRChim Annexe 2.18 (seuil: 5000 mg/kg)",
    "hap": "ORRChim / OLED",
    "radon": "ORaP Art. 110 (seuils: 300/1000 Bq/m3)",
    "pfas": "OSol / OPPS (reglementation en evolution)",
}

CFST_WORK_LABELS = {
    "minor": "Travaux mineurs (sous-categorie A)",
    "medium": "Travaux moyens (sous-categorie B)",
    "major": "Travaux majeurs (sous-categorie C)",
}


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def render_report_css() -> str:
    return """\
@page {
    size: A4;
    margin: 25mm 20mm 30mm 20mm;
    @bottom-center {
        content: "BatiConnect — Rapport Autorite — Page " counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #9ca3af;
    }
}
body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    color: #1a1a1a;
    font-size: 11pt;
    line-height: 1.5;
}
h1 { font-size: 26pt; color: #1a365d; margin-bottom: 8px; }
h2 { font-size: 18pt; color: #1a365d; border-bottom: 2px solid #dc2626; padding-bottom: 6px; margin-top: 24px; page-break-after: avoid; }
h3 { font-size: 14pt; color: #2b6cb0; margin-top: 16px; page-break-after: avoid; }
h4 { font-size: 12pt; color: #374151; margin-top: 12px; }
table { width: 100%; border-collapse: collapse; margin: 10px 0 16px 0; page-break-inside: avoid; }
th { background: #f3f4f6; text-align: left; padding: 8px 10px; font-size: 10pt; border-bottom: 2px solid #d1d5db; }
td { padding: 7px 10px; border-bottom: 1px solid #e5e7eb; font-size: 10pt; }
tr:nth-child(even) td { background: #f9fafb; }
.cover { page-break-after: always; text-align: center; padding-top: 120px; }
.cover h1 { font-size: 36pt; margin-bottom: 16px; }
.cover .subtitle { font-size: 16pt; color: #4a5568; margin-bottom: 8px; }
.cover .meta { font-size: 11pt; color: #718096; margin-top: 40px; line-height: 1.8; }
.cover .logo { font-size: 32pt; color: #dc2626; font-weight: bold; margin-bottom: 40px; }
.cover .disclaimer { font-size: 9pt; color: #a0aec0; margin-top: 60px; max-width: 400px; margin-left: auto; margin-right: auto; }
.section { page-break-before: always; }
.section:first-of-type { page-break-before: avoid; }
.toc { page-break-after: always; }
.toc ul { list-style: none; padding: 0; }
.toc li { padding: 6px 0; border-bottom: 1px dotted #d1d5db; font-size: 12pt; }
.toc li span.page-ref { float: right; color: #6b7280; }
.risk-badge { display: inline-block; padding: 2px 10px; border-radius: 4px; font-weight: bold; font-size: 9pt; text-transform: uppercase; }
.metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }
.metric-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; text-align: center; }
.metric-card .value { font-size: 24pt; font-weight: bold; color: #1a365d; }
.metric-card .label { font-size: 9pt; color: #718096; margin-top: 4px; }
.highlight-box { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin: 12px 0; border-radius: 0 6px 6px 0; }
.warning-box { background: #fef2f2; border-left: 4px solid #dc2626; padding: 12px 16px; margin: 12px 0; border-radius: 0 6px 6px 0; }
.footer-section { margin-top: 32px; padding-top: 16px; border-top: 1px solid #e5e7eb; color: #9ca3af; font-size: 9pt; }
.pollutant-detail { margin-bottom: 20px; padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px; page-break-inside: avoid; }
.pollutant-detail h4 { margin-top: 0; }
.evidence-item { padding: 8px 12px; margin: 4px 0; border-left: 3px solid #3b82f6; background: #f8fafc; }
.no-data { color: #9ca3af; font-style: italic; padding: 8px 0; }
"""


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def render_cover_page(identity: dict, now: datetime, language: str = "fr") -> str:
    return f"""
<div class="cover">
    <div class="logo">BatiConnect</div>
    <h1>Rapport Technique<br>pour Soumission Autorite</h1>
    <div class="subtitle">{identity["address"]}, {identity["postal_code"]} {identity["city"]}</div>
    <div class="subtitle">Canton: {identity["canton"] or "-"}</div>
    <div class="meta">
        EGID: {identity["egid"] or "-"}<br>
        EGRID: {identity["egrid"] or "-"}<br>
        Date du rapport: {_fmt_date(now)}<br>
        Annee de construction: {identity["construction_year"] or "-"}<br>
        Type: {identity["building_type"] or "-"}<br>
        Surface: {identity["surface_area_m2"] or "-"} m&sup2;
    </div>
    <div class="disclaimer">
        Ce document est genere automatiquement par BatiConnect.
        Il ne constitue pas une expertise legale.<br>
        Verification professionnelle recommandee.
    </div>
</div>"""


def render_toc() -> str:
    sections = [
        ("1", "Resume executif"),
        ("2", "Diagnostics polluants detailles"),
        ("3", "Statut de conformite reglementaire"),
        ("4", "Recommandations et mesures prioritaires"),
        ("5", "Plan d'interventions"),
        ("6", "Preuves et documents justificatifs"),
        ("7", "Annexes — cadre legal, glossaire, metadata"),
    ]
    items = "\n".join(
        f'<li><strong>{num}.</strong> {title} <span class="page-ref">&rarr;</span></li>' for num, title in sections
    )
    return f"""
<div class="toc">
    <h2>Table des matieres</h2>
    <ul>
        {items}
    </ul>
</div>"""


def render_executive_summary(
    *,
    identity: dict,
    pollutant_risks: list[dict],
    risk_obj: Any,
    trust_score: int,
    completeness_pct: int,
    diagnostics: list,
    actions: list,
) -> str:
    # Key metrics
    overall_risk = risk_obj.overall_risk_level if risk_obj else "unknown"
    critical_pollutants = [p for p in pollutant_risks if p["level"] in ("critical", "high")]
    diag_count = len(diagnostics)
    urgent_actions = [a for a in actions if getattr(a, "priority", "") in ("urgent", "critical", "high")]

    # Pollutant summary table
    pol_rows = ""
    for p in pollutant_risks:
        pol_rows += f"<tr><td>{p['label']}</td><td>{p['probability']}%</td><td>{_risk_badge(p['level'])}</td></tr>"
    if not pol_rows:
        pol_rows = '<tr><td colspan="3" class="no-data">Aucune donnee de risque polluant disponible</td></tr>'

    # Urgent actions
    action_items = ""
    for a in urgent_actions[:5]:
        title = getattr(a, "title", getattr(a, "description", str(a)))
        prio = getattr(a, "priority", "medium")
        action_items += f"<li><strong>[{prio.upper()}]</strong> {title}</li>"
    if not action_items:
        action_items = '<li class="no-data">Aucune action urgente identifiee</li>'

    return f"""
<div class="section">
    <h2>1. Resume executif</h2>

    <div class="metric-grid">
        <div class="metric-card">
            <div class="value">{_risk_badge(overall_risk)}</div>
            <div class="label">Risque global</div>
        </div>
        <div class="metric-card">
            <div class="value">{trust_score}%</div>
            <div class="label">Score de confiance</div>
        </div>
        <div class="metric-card">
            <div class="value">{completeness_pct}%</div>
            <div class="label">Completude du dossier</div>
        </div>
    </div>

    <h3>Vue d'ensemble</h3>
    <table>
        <tr><th>Caracteristique</th><th>Valeur</th></tr>
        <tr><td>Adresse</td><td>{identity["address"]}, {identity["postal_code"]} {identity["city"]}</td></tr>
        <tr><td>EGID / EGRID</td><td>{identity["egid"] or "-"} / {identity["egrid"] or "-"}</td></tr>
        <tr><td>Annee de construction</td><td>{identity["construction_year"] or "-"}</td></tr>
        <tr><td>Diagnostics realises</td><td>{diag_count}</td></tr>
        <tr><td>Polluants a risque eleve/critique</td><td>{len(critical_pollutants)}</td></tr>
        <tr><td>Actions urgentes</td><td>{len(urgent_actions)}</td></tr>
    </table>

    <h3>Synthese des risques polluants</h3>
    <table>
        <tr><th>Polluant</th><th>Probabilite</th><th>Niveau</th></tr>
        {pol_rows}
    </table>

    {"<div class='warning-box'><strong>Attention:</strong> " + str(len(critical_pollutants)) + " polluant(s) a risque eleve/critique identifie(s). Action immediate recommandee.</div>" if critical_pollutants else ""}

    <h3>Actions prioritaires</h3>
    <ul>{action_items}</ul>
</div>"""


def render_diagnostics_section(
    *,
    diagnostics: list,
    samples: list,
    pollutant_risks: list[dict],
) -> str:
    """Pages 6-10: Detailed diagnostics per pollutant type."""

    # Group samples by pollutant type
    samples_by_pollutant: dict[str, list] = {}
    for s in samples:
        pol = getattr(s, "pollutant_type", None) or "unknown"
        samples_by_pollutant.setdefault(pol, []).append(s)

    # Diagnostic summary table
    diag_rows = ""
    for d in diagnostics:
        sample_count = len(getattr(d, "samples", []))
        diag_rows += (
            f"<tr><td>{getattr(d, 'diagnostic_type', '-')}</td>"
            f"<td>{getattr(d, 'status', '-')}</td>"
            f"<td>{_fmt_date(getattr(d, 'date_inspection', None))}</td>"
            f"<td>{getattr(d, 'laboratory', '-') or '-'}</td>"
            f"<td>{sample_count}</td>"
            f"<td>{getattr(d, 'conclusion', '-') or '-'}</td></tr>"
        )
    if not diag_rows:
        diag_rows = '<tr><td colspan="6" class="no-data">Aucun diagnostic enregistre</td></tr>'

    # Pollutant detail blocks
    pollutant_blocks = ""
    for pol_key, label in POLLUTANT_LABELS.items():
        regulation = POLLUTANT_REGULATIONS.get(pol_key, "-")
        risk_info = next((p for p in pollutant_risks if p["pollutant"] == pol_key), None)
        risk_level = risk_info["level"] if risk_info else "unknown"
        risk_prob = risk_info["probability"] if risk_info else 0
        pol_samples = samples_by_pollutant.get(pol_key, [])

        sample_rows = ""
        for s in pol_samples[:15]:
            loc = (
                " / ".join(
                    filter(
                        None,
                        [
                            getattr(s, "location_floor", None),
                            getattr(s, "location_room", None),
                            getattr(s, "location_detail", None),
                        ],
                    )
                )
                or "-"
            )
            conc = getattr(s, "concentration", None)
            conc_str = f"{conc} {getattr(s, 'unit', '') or ''}" if conc is not None else "-"
            exceeded = "OUI" if getattr(s, "threshold_exceeded", False) else "non"
            work_cat = CFST_WORK_LABELS.get(
                getattr(s, "cfst_work_category", ""),
                getattr(s, "cfst_work_category", "-") or "-",
            )
            sample_rows += (
                f"<tr><td>{getattr(s, 'sample_number', '-')}</td>"
                f"<td>{loc}</td>"
                f"<td>{getattr(s, 'material_description', '-') or '-'}</td>"
                f"<td>{conc_str}</td>"
                f"<td><strong>{exceeded}</strong></td>"
                f"<td>{work_cat}</td></tr>"
            )

        if not sample_rows:
            sample_table = '<p class="no-data">Aucun echantillon pour ce polluant.</p>'
        else:
            overflow = ""
            if len(pol_samples) > 15:
                overflow = f'<p class="no-data">... et {len(pol_samples) - 15} echantillon(s) supplementaire(s)</p>'
            sample_table = f"""
            <table>
                <tr><th>N&deg;</th><th>Localisation</th><th>Materiau</th><th>Concentration</th><th>Seuil depasse</th><th>Cat. CFST</th></tr>
                {sample_rows}
            </table>
            {overflow}"""

        pollutant_blocks += f"""
        <div class="pollutant-detail">
            <h4>{label} {_risk_badge(risk_level)}</h4>
            <p><strong>Probabilite de presence:</strong> {risk_prob}% &mdash;
               <strong>Base legale:</strong> {regulation}</p>
            {sample_table}
        </div>"""

    return f"""
<div class="section">
    <h2>2. Diagnostics polluants detailles</h2>

    <h3>Synthese des diagnostics</h3>
    <table>
        <tr><th>Type</th><th>Statut</th><th>Date inspection</th><th>Laboratoire</th><th>Echantillons</th><th>Conclusion</th></tr>
        {diag_rows}
    </table>

    <h3>Detail par polluant</h3>
    {pollutant_blocks}
</div>"""


def render_compliance_section(
    *,
    compliance_artefacts: list,
    zones: list,
) -> str:
    """Pages 11-14: Compliance status and zone analysis."""

    # Compliance artefacts table
    comp_rows = ""
    for a in compliance_artefacts:
        comp_rows += (
            f"<tr><td>{getattr(a, 'artefact_type', '-') or '-'}</td>"
            f"<td>{getattr(a, 'status', '-')}</td>"
            f"<td>{getattr(a, 'regulation_ref', '-') or '-'}</td>"
            f"<td>{_fmt_date(getattr(a, 'created_at', None))}</td>"
            f"<td>{getattr(a, 'notes', '-') or '-'}</td></tr>"
        )
    if not comp_rows:
        comp_rows = '<tr><td colspan="5" class="no-data">Aucun artefact de conformite enregistre</td></tr>'

    non_conf = [a for a in compliance_artefacts if getattr(a, "status", "") in ("draft", "rejected")]
    submitted = [a for a in compliance_artefacts if getattr(a, "status", "") == "submitted"]
    acknowledged = [a for a in compliance_artefacts if getattr(a, "status", "") == "acknowledged"]

    # Zones table
    zone_rows = ""
    for z in zones:
        zone_rows += (
            f"<tr><td>{getattr(z, 'name', '-') or '-'}</td>"
            f"<td>{getattr(z, 'zone_type', '-') or '-'}</td>"
            f"<td>{getattr(z, 'description', '-') or '-'}</td></tr>"
        )
    if not zone_rows:
        zone_rows = '<tr><td colspan="3" class="no-data">Aucune zone enregistree</td></tr>'

    status_text = "Conforme" if not non_conf else "Non conforme"
    status_class = "highlight-box" if not non_conf else "warning-box"

    return f"""
<div class="section">
    <h2>3. Statut de conformite reglementaire</h2>

    <div class="{status_class}">
        <strong>Statut global:</strong> {status_text}<br>
        Non-conformites: {len(non_conf)} | Soumis: {len(submitted)} | Valides: {len(acknowledged)} | Total: {len(compliance_artefacts)}
    </div>

    <h3>Artefacts de conformite</h3>
    <table>
        <tr><th>Type</th><th>Statut</th><th>Reference legale</th><th>Date</th><th>Notes</th></tr>
        {comp_rows}
    </table>

    <h3>Zones du batiment</h3>
    <table>
        <tr><th>Nom</th><th>Type</th><th>Description</th></tr>
        {zone_rows}
    </table>
</div>"""


def render_recommendations_section(
    *,
    actions: list,
    pollutant_risks: list[dict],
) -> str:
    """Pages 15-17: Recommendations."""

    # Per-pollutant recommendations
    pol_recs = ""
    for p in pollutant_risks:
        if p["level"] in ("critical", "high"):
            urgency = "IMMEDIATE" if p["level"] == "critical" else "PRIORITAIRE"
            pol_recs += f"""
            <div class="warning-box">
                <strong>{p["label"]} — Action {urgency}</strong><br>
                Probabilite: {p["probability"]}% | Niveau: {_risk_badge(p["level"])}<br>
                Base legale: {POLLUTANT_REGULATIONS.get(p["pollutant"], "-")}<br>
                Recommandation: diagnostic approfondi et plan d'assainissement requis.
            </div>"""
        elif p["level"] == "medium":
            pol_recs += f"""
            <div class="highlight-box">
                <strong>{p["label"]} — Surveillance recommandee</strong><br>
                Probabilite: {p["probability"]}% | Niveau: {_risk_badge(p["level"])}<br>
                Recommandation: surveillance reguliere et diagnostic si travaux prevus.
            </div>"""

    if not pol_recs:
        pol_recs = '<p class="no-data">Aucune recommandation specifique aux polluants.</p>'

    # Action items
    action_rows = ""
    for a in actions[:20]:
        title = getattr(a, "title", getattr(a, "description", "-"))
        prio = getattr(a, "priority", "medium") or "medium"
        status = getattr(a, "status", "-") or "-"
        due = _fmt_date(getattr(a, "due_date", None))
        action_rows += f"<tr><td>{title}</td><td>{prio.upper()}</td><td>{status}</td><td>{due}</td></tr>"

    if not action_rows:
        action_rows = '<tr><td colspan="4" class="no-data">Aucune action enregistree</td></tr>'

    return f"""
<div class="section">
    <h2>4. Recommandations et mesures prioritaires</h2>

    <h3>Recommandations par polluant</h3>
    {pol_recs}

    <h3>Plan d'actions</h3>
    <table>
        <tr><th>Action</th><th>Priorite</th><th>Statut</th><th>Echeance</th></tr>
        {action_rows}
    </table>
</div>"""


def render_action_plan_section(*, interventions: list) -> str:
    """Pages: Interventions calendar."""

    completed_rows = ""
    planned_rows = ""

    for i in interventions:
        status = getattr(i, "status", "")
        title = getattr(i, "title", "-") or "-"
        itype = getattr(i, "intervention_type", "-") or "-"
        cost = _fmt_chf(getattr(i, "cost_chf", None))
        contractor = getattr(i, "contractor_name", "-") or "-"

        if status == "completed":
            completed_rows += (
                f"<tr><td>{title}</td><td>{itype}</td>"
                f"<td>{_fmt_date(getattr(i, 'date_end', None))}</td>"
                f"<td>{cost}</td><td>{contractor}</td></tr>"
            )
        elif status in ("planned", "in_progress"):
            planned_rows += (
                f"<tr><td>{title}</td><td>{itype}</td>"
                f"<td>{_fmt_date(getattr(i, 'date_start', None))}</td>"
                f"<td>{cost}</td><td>{status}</td></tr>"
            )

    if not completed_rows:
        completed_rows = '<tr><td colspan="5" class="no-data">Aucune intervention terminee</td></tr>'
    if not planned_rows:
        planned_rows = '<tr><td colspan="5" class="no-data">Aucune intervention planifiee</td></tr>'

    total_cost = sum(getattr(i, "cost_chf", 0) or 0 for i in interventions if getattr(i, "status", "") == "completed")

    return f"""
<div class="section">
    <h2>5. Plan d'interventions</h2>

    <h3>Interventions realisees</h3>
    <table>
        <tr><th>Titre</th><th>Type</th><th>Date fin</th><th>Cout</th><th>Entreprise</th></tr>
        {completed_rows}
    </table>
    <p><strong>Cout total des interventions:</strong> {_fmt_chf(total_cost)}</p>

    <h3>Interventions planifiees / en cours</h3>
    <table>
        <tr><th>Titre</th><th>Type</th><th>Date debut</th><th>Cout estime</th><th>Statut</th></tr>
        {planned_rows}
    </table>
</div>"""


def render_evidence_section(
    *,
    documents: list,
    include_photos: bool = True,
) -> str:
    """Pages 18-20: Evidence — documents and photos."""

    doc_rows = ""
    photo_docs = []
    for d in documents:
        doc_type = getattr(d, "document_type", "-") or "-"
        name = getattr(d, "file_name", getattr(d, "name", "-")) or "-"
        uploaded = _fmt_date(getattr(d, "created_at", None))
        doc_rows += f"<tr><td>{name}</td><td>{doc_type}</td><td>{uploaded}</td></tr>"
        if doc_type in ("photo", "field_photo", "observation"):
            photo_docs.append(d)

    if not doc_rows:
        doc_rows = '<tr><td colspan="3" class="no-data">Aucun document rattache</td></tr>'

    photo_section = ""
    if include_photos and photo_docs:
        photo_items = ""
        for p in photo_docs[:10]:
            name = getattr(p, "file_name", getattr(p, "name", "-")) or "-"
            notes = getattr(p, "notes", "") or ""
            photo_items += f"""
            <div class="evidence-item">
                <strong>{name}</strong>
                {f"<br><em>{notes}</em>" if notes else ""}
            </div>"""
        photo_section = f"""
        <h3>Photos terrain ({len(photo_docs)} piece(s))</h3>
        {photo_items}
        {"<p class='no-data'>... et " + str(len(photo_docs) - 10) + " photo(s) supplementaire(s)</p>" if len(photo_docs) > 10 else ""}
        """
    elif include_photos:
        photo_section = '<h3>Photos terrain</h3><p class="no-data">Aucune photo de terrain disponible.</p>'

    return f"""
<div class="section">
    <h2>6. Preuves et documents justificatifs</h2>

    <h3>Inventaire des documents ({len(documents)} piece(s))</h3>
    <table>
        <tr><th>Document</th><th>Type</th><th>Date</th></tr>
        {doc_rows}
    </table>

    {photo_section}
</div>"""


def render_appendix_section(
    *,
    identity: dict,
    now: datetime,
    version: str,
) -> str:
    """Pages 21+: Legal framework, glossary, metadata."""

    return f"""
<div class="section">
    <h2>7. Annexes</h2>

    <h3>A. Cadre reglementaire applicable</h3>
    <table>
        <tr><th>Polluant</th><th>Base legale</th></tr>
        <tr><td>Amiante</td><td>OTConst Art. 60a, 82-86 — CFST 6503 (categories de travaux: mineur/moyen/majeur)</td></tr>
        <tr><td>PCB</td><td>ORRChim Annexe 2.15 — seuil d'assainissement: 50 mg/kg</td></tr>
        <tr><td>Plomb</td><td>ORRChim Annexe 2.18 — seuil d'assainissement: 5'000 mg/kg</td></tr>
        <tr><td>HAP</td><td>ORRChim / OLED — selon concentration et matrice</td></tr>
        <tr><td>Radon</td><td>ORaP Art. 110 — valeur de reference: 300 Bq/m3, valeur limite: 1'000 Bq/m3</td></tr>
        <tr><td>PFAS</td><td>OSol / OPPS — reglementation en evolution, valeurs indicatives cantonales</td></tr>
    </table>

    <h3>B. Glossaire</h3>
    <table>
        <tr><th>Terme</th><th>Definition</th></tr>
        <tr><td>EGID</td><td>Identificateur federal du batiment (Registre federal des batiments)</td></tr>
        <tr><td>EGRID</td><td>Identificateur du bien-fonds (Registre foncier)</td></tr>
        <tr><td>AvT</td><td>Avant travaux — diagnostic prealable aux interventions</td></tr>
        <tr><td>ApT</td><td>Apres travaux — controle post-intervention</td></tr>
        <tr><td>CFST</td><td>Commission federale de coordination pour la securite au travail</td></tr>
        <tr><td>OTConst</td><td>Ordonnance sur les travaux de construction</td></tr>
        <tr><td>ORRChim</td><td>Ordonnance sur la reduction des risques lies aux produits chimiques</td></tr>
        <tr><td>ORaP</td><td>Ordonnance sur la radioprotection</td></tr>
        <tr><td>OLED</td><td>Ordonnance sur la limitation et l'elimination des dechets</td></tr>
        <tr><td>SUVA</td><td>Caisse nationale suisse d'assurance en cas d'accidents</td></tr>
    </table>

    <h3>C. Metadata du rapport</h3>
    <table>
        <tr><th>Champ</th><th>Valeur</th></tr>
        <tr><td>Emetteur</td><td>BatiConnect — Batiscan Sarl</td></tr>
        <tr><td>EGID</td><td>{identity["egid"] or "-"}</td></tr>
        <tr><td>Canton</td><td>{identity["canton"] or "-"}</td></tr>
        <tr><td>Date de generation</td><td>{_fmt_date(now)}</td></tr>
        <tr><td>Version du rapport</td><td>{version}</td></tr>
        <tr><td>Format</td><td>PDF genere via Gotenberg (Chromium)</td></tr>
    </table>

    <div class="footer-section">
        <p><strong>Avertissement:</strong> Ce rapport est genere automatiquement par BatiConnect a partir
        des donnees disponibles dans le systeme. Il ne constitue pas une expertise legale et ne
        garantit pas la conformite reglementaire. Les informations contenues dans ce document
        doivent etre verifiees par un professionnel qualifie avant toute soumission officielle.</p>
        <p>BatiConnect — Batiscan Sarl — {_fmt_date(now)}</p>
        <p>Lien de verification: batiscan.ch/verify</p>
    </div>
</div>"""
