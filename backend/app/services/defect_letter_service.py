"""BatiConnect — DefectShield notification letter PDF generator.

Generates formal defect notification letters (Art. 367 CO) in FR/DE/IT
via Gotenberg HTML→PDF conversion.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.defect_timeline_service import get_timeline
from app.services.gotenberg_service import html_to_pdf

logger = logging.getLogger(__name__)

Lang = Literal["fr", "de", "it"]

# ---------------------------------------------------------------------------
# i18n content
# ---------------------------------------------------------------------------

_TRANSLATIONS: dict[Lang, dict[str, str]] = {
    "fr": {
        "title": "Notification de défaut de construction",
        "subtitle": "Art. 367 al. 1bis CO — Avis des défauts",
        "building_header": "Immeuble concerné",
        "address": "Adresse",
        "egid": "EGID",
        "canton": "Canton",
        "defect_section": "Défaut constaté",
        "defect_type": "Type de défaut",
        "description": "Description",
        "discovery_date": "Date de découverte",
        "notification_deadline": "Délai de notification",
        "guarantee_type": "Type de garantie",
        "legal_section": "Base légale",
        "legal_text": (
            "Conformément à l'art. 367 al. 1bis du Code des obligations (CO), "
            "entré en vigueur le 1er janvier 2026, le maître de l'ouvrage est tenu "
            "d'aviser l'entrepreneur des défauts constatés dans un délai de "
            "<strong>60 jours civils</strong> dès leur découverte. "
            "Le non-respect de ce délai entraîne la déchéance du droit de faire "
            "valoir la garantie pour les défauts concernés."
        ),
        "prescription_note": (
            "Prescription: 5 ans pour les défauts cachés (art. 371 CO), 2 ans pour les défauts apparents."
        ),
        "signature_section": "Signatures",
        "owner_signature": "Maître de l'ouvrage / Propriétaire",
        "contractor_signature": "Entrepreneur / Entreprise",
        "date_label": "Date",
        "signature_label": "Signature",
        "generated_by": "Document généré par BatiConnect — Plateforme d'intelligence immobilière",
        "defect_types": {
            "construction": "Construction",
            "pollutant": "Polluant",
            "structural": "Structurel",
            "installation": "Installation",
            "other": "Autre",
        },
        "guarantee_types": {
            "standard": "Standard",
            "new_build_rectification": "Garantie construction neuve (2 ans)",
        },
    },
    "de": {
        "title": "Mängelrüge — Bauwerk",
        "subtitle": "Art. 367 Abs. 1bis OR — Mängelanzeige",
        "building_header": "Betroffenes Gebäude",
        "address": "Adresse",
        "egid": "EGID",
        "canton": "Kanton",
        "defect_section": "Festgestellter Mangel",
        "defect_type": "Mangelart",
        "description": "Beschreibung",
        "discovery_date": "Entdeckungsdatum",
        "notification_deadline": "Rügefrist",
        "guarantee_type": "Garantietyp",
        "legal_section": "Rechtsgrundlage",
        "legal_text": (
            "Gemäss Art. 367 Abs. 1bis des Obligationenrechts (OR), "
            "in Kraft seit dem 1. Januar 2026, ist der Besteller verpflichtet, "
            "dem Unternehmer festgestellte Mängel innerhalb von "
            "<strong>60 Kalendertagen</strong> seit deren Entdeckung anzuzeigen. "
            "Die Nichteinhaltung dieser Frist führt zum Verlust des Rechts auf "
            "Mängelgewährleistung."
        ),
        "prescription_note": (
            "Verjährung: 5 Jahre für verborgene Mängel (Art. 371 OR), 2 Jahre für offensichtliche Mängel."
        ),
        "signature_section": "Unterschriften",
        "owner_signature": "Besteller / Eigentümer",
        "contractor_signature": "Unternehmer / Firma",
        "date_label": "Datum",
        "signature_label": "Unterschrift",
        "generated_by": "Dokument erstellt durch BatiConnect — Immobilien-Intelligenzplattform",
        "defect_types": {
            "construction": "Baumangel",
            "pollutant": "Schadstoff",
            "structural": "Strukturell",
            "installation": "Installation",
            "other": "Andere",
        },
        "guarantee_types": {
            "standard": "Standard",
            "new_build_rectification": "Neubau-Garantie (2 Jahre)",
        },
    },
    "it": {
        "title": "Notifica di difetto di costruzione",
        "subtitle": "Art. 367 cpv. 1bis CO — Avviso dei difetti",
        "building_header": "Immobile interessato",
        "address": "Indirizzo",
        "egid": "EGID",
        "canton": "Cantone",
        "defect_section": "Difetto constatato",
        "defect_type": "Tipo di difetto",
        "description": "Descrizione",
        "discovery_date": "Data di scoperta",
        "notification_deadline": "Termine di notifica",
        "guarantee_type": "Tipo di garanzia",
        "legal_section": "Base legale",
        "legal_text": (
            "Conformemente all'art. 367 cpv. 1bis del Codice delle obbligazioni (CO), "
            "in vigore dal 1° gennaio 2026, il committente è tenuto a notificare "
            "all'appaltatore i difetti constatati entro un termine di "
            "<strong>60 giorni civili</strong> dalla loro scoperta. "
            "Il mancato rispetto di questo termine comporta la decadenza del diritto "
            "di far valere la garanzia per i difetti in questione."
        ),
        "prescription_note": (
            "Prescrizione: 5 anni per i difetti nascosti (art. 371 CO), 2 anni per i difetti apparenti."
        ),
        "signature_section": "Firme",
        "owner_signature": "Committente / Proprietario",
        "contractor_signature": "Appaltatore / Impresa",
        "date_label": "Data",
        "signature_label": "Firma",
        "generated_by": "Documento generato da BatiConnect — Piattaforma di intelligenza immobiliare",
        "defect_types": {
            "construction": "Costruzione",
            "pollutant": "Inquinante",
            "structural": "Strutturale",
            "installation": "Installazione",
            "other": "Altro",
        },
        "guarantee_types": {
            "standard": "Standard",
            "new_build_rectification": "Garanzia nuova costruzione (2 anni)",
        },
    },
}


def _format_date(d: date, lang: Lang) -> str:
    """Format a date according to Swiss conventions per language."""
    if lang == "de":
        return d.strftime("%d.%m.%Y")
    if lang == "it":
        return d.strftime("%d.%m.%Y")
    return d.strftime("%d.%m.%Y")  # Swiss FR also uses DD.MM.YYYY


def _t(lang: Lang, key: str) -> str:
    """Get translation string."""
    return _TRANSLATIONS[lang].get(key, key)


def _t_defect_type(lang: Lang, defect_type: str) -> str:
    """Get translated defect type label."""
    return _TRANSLATIONS[lang]["defect_types"].get(defect_type, defect_type)


def _t_guarantee_type(lang: Lang, guarantee_type: str) -> str:
    """Get translated guarantee type label."""
    return _TRANSLATIONS[lang]["guarantee_types"].get(guarantee_type, guarantee_type)


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<style>
  @page {{ margin: 0; }}
  body {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
  }}
  .header {{
    background: #1e3a5f;
    color: white;
    padding: 24px 40px;
  }}
  .header h1 {{
    margin: 0 0 4px 0;
    font-size: 18pt;
    font-weight: 600;
  }}
  .header p {{
    margin: 0;
    font-size: 10pt;
    opacity: 0.85;
  }}
  .content {{
    padding: 30px 40px;
  }}
  .section {{
    margin-bottom: 24px;
  }}
  .section-title {{
    font-size: 12pt;
    font-weight: 600;
    color: #1e3a5f;
    border-bottom: 2px solid #1e3a5f;
    padding-bottom: 4px;
    margin-bottom: 12px;
  }}
  table.info {{
    width: 100%;
    border-collapse: collapse;
  }}
  table.info td {{
    padding: 6px 12px;
    vertical-align: top;
  }}
  table.info td.label {{
    font-weight: 600;
    width: 200px;
    color: #4a4a4a;
  }}
  .legal-box {{
    background: #f5f7fa;
    border-left: 4px solid #1e3a5f;
    padding: 16px 20px;
    font-size: 10pt;
    line-height: 1.6;
  }}
  .legal-box p {{
    margin: 0 0 8px 0;
  }}
  .legal-box p:last-child {{
    margin-bottom: 0;
  }}
  .signatures {{
    display: flex;
    justify-content: space-between;
    margin-top: 40px;
    gap: 40px;
  }}
  .sig-block {{
    flex: 1;
  }}
  .sig-block .sig-role {{
    font-weight: 600;
    margin-bottom: 8px;
  }}
  .sig-block .sig-line {{
    border-bottom: 1px solid #333;
    margin-top: 50px;
    margin-bottom: 4px;
  }}
  .sig-block .sig-label {{
    font-size: 9pt;
    color: #666;
  }}
  .footer {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 8pt;
    color: #999;
    padding: 12px 40px;
    border-top: 1px solid #eee;
  }}
  .deadline-highlight {{
    background: #fff3cd;
    border: 1px solid #ffc107;
    padding: 4px 10px;
    border-radius: 3px;
    font-weight: 600;
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>

  <div class="content">
    <div class="section">
      <div class="section-title">{building_header}</div>
      <table class="info">
        <tr><td class="label">{lbl_address}</td><td>{address}</td></tr>
        <tr><td class="label">{lbl_egid}</td><td>{egid}</td></tr>
        <tr><td class="label">{lbl_canton}</td><td>{canton}</td></tr>
      </table>
    </div>

    <div class="section">
      <div class="section-title">{defect_section}</div>
      <table class="info">
        <tr><td class="label">{lbl_defect_type}</td><td>{defect_type}</td></tr>
        <tr><td class="label">{lbl_description}</td><td>{description}</td></tr>
        <tr><td class="label">{lbl_discovery_date}</td><td>{discovery_date}</td></tr>
        <tr><td class="label">{lbl_notification_deadline}</td><td><span class="deadline-highlight">{notification_deadline}</span></td></tr>
        <tr><td class="label">{lbl_guarantee_type}</td><td>{guarantee_type}</td></tr>
      </table>
    </div>

    <div class="section">
      <div class="section-title">{legal_section}</div>
      <div class="legal-box">
        <p>{legal_text}</p>
        <p><em>{prescription_note}</em></p>
      </div>
    </div>

    <div class="section">
      <div class="section-title">{signature_section}</div>
      <div class="signatures">
        <div class="sig-block">
          <div class="sig-role">{owner_signature}</div>
          <div class="sig-line"></div>
          <div class="sig-label">{lbl_date}: _______________</div>
          <div style="margin-top: 30px;">
            <div class="sig-line"></div>
            <div class="sig-label">{lbl_signature}</div>
          </div>
        </div>
        <div class="sig-block">
          <div class="sig-role">{contractor_signature}</div>
          <div class="sig-line"></div>
          <div class="sig-label">{lbl_date}: _______________</div>
          <div style="margin-top: 30px;">
            <div class="sig-line"></div>
            <div class="sig-label">{lbl_signature}</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="footer">{generated_by}</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_letter_html(
    *,
    lang: Lang,
    address: str,
    egid: str,
    canton: str,
    defect_type: str,
    description: str,
    discovery_date: date,
    notification_deadline: date,
    guarantee_type: str,
) -> str:
    """Render the notification letter as a full HTML document.

    Pure function — no I/O. Suitable for testing template output.
    """
    t = _TRANSLATIONS[lang]
    return _HTML_TEMPLATE.format(
        lang=lang,
        title=t["title"],
        subtitle=t["subtitle"],
        building_header=t["building_header"],
        lbl_address=t["address"],
        address=address,
        lbl_egid=t["egid"],
        egid=egid or "—",
        lbl_canton=t["canton"],
        canton=canton or "—",
        defect_section=t["defect_section"],
        lbl_defect_type=t["defect_type"],
        defect_type=_t_defect_type(lang, defect_type),
        lbl_description=t["description"],
        description=description or "—",
        lbl_discovery_date=t["discovery_date"],
        discovery_date=_format_date(discovery_date, lang),
        lbl_notification_deadline=t["notification_deadline"],
        notification_deadline=_format_date(notification_deadline, lang),
        lbl_guarantee_type=t["guarantee_type"],
        guarantee_type=_t_guarantee_type(lang, guarantee_type),
        legal_section=t["legal_section"],
        legal_text=t["legal_text"],
        prescription_note=t["prescription_note"],
        signature_section=t["signature_section"],
        owner_signature=t["owner_signature"],
        contractor_signature=t["contractor_signature"],
        lbl_date=t["date_label"],
        lbl_signature=t["signature_label"],
        generated_by=t["generated_by"],
    )


async def generate_letter_pdf(
    db: AsyncSession,
    timeline_id: UUID,
    lang: Lang = "fr",
) -> bytes:
    """Generate a defect notification letter PDF for a given DefectTimeline.

    Loads the DefectTimeline + related Building from DB, renders HTML,
    converts via Gotenberg, returns raw PDF bytes.

    Raises:
        ValueError: If timeline or building not found.
    """
    from app.services.building_service import get_building

    timeline = await get_timeline(db, timeline_id)
    if not timeline:
        raise ValueError(f"DefectTimeline {timeline_id} not found")

    building = await get_building(db, timeline.building_id)
    if not building:
        raise ValueError(f"Building {timeline.building_id} not found")

    html = render_letter_html(
        lang=lang,
        address=building.address or "—",
        egid=str(building.egid) if building.egid else "—",
        canton=building.canton or "—",
        defect_type=timeline.defect_type,
        description=timeline.description or "",
        discovery_date=timeline.discovery_date,
        notification_deadline=timeline.notification_deadline,
        guarantee_type=timeline.guarantee_type,
    )

    pdf_bytes = await html_to_pdf(html)
    logger.info(
        "Generated defect letter PDF: timeline=%s, lang=%s, size=%d",
        timeline_id,
        lang,
        len(pdf_bytes),
    )
    return pdf_bytes
