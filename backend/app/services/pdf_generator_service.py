"""PDF generator service for BatiConnect pack artifacts.

Generates real PDF files from pack data using reportlab.
Falls back to structured HTML if reportlab is unavailable.
"""

import hashlib
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# Default output directory — gitignored
_DEFAULT_ARTIFACT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "artifacts")


def _ensure_artifact_dir(output_dir: str | None = None) -> str:
    """Return (and create if needed) the artifact output directory."""
    d = output_dir or _DEFAULT_ARTIFACT_DIR
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# reportlab PDF builder
# ---------------------------------------------------------------------------


def _build_styles() -> dict[str, Any]:
    """Return custom paragraph styles for the PDF."""
    base = getSampleStyleSheet()
    styles: dict[str, Any] = {"base": base}

    styles["title"] = ParagraphStyle(
        "PackTitle",
        parent=base["Heading1"],
        fontSize=20,
        spaceAfter=6 * mm,
        textColor=colors.HexColor("#1a365d"),
    )
    styles["subtitle"] = ParagraphStyle(
        "PackSubtitle",
        parent=base["Heading2"],
        fontSize=14,
        spaceAfter=4 * mm,
        textColor=colors.HexColor("#2d3748"),
    )
    styles["section_title"] = ParagraphStyle(
        "SectionTitle",
        parent=base["Heading3"],
        fontSize=12,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        textColor=colors.HexColor("#2b6cb0"),
    )
    styles["body"] = ParagraphStyle(
        "PackBody",
        parent=base["Normal"],
        fontSize=9,
        leading=13,
    )
    styles["caveat"] = ParagraphStyle(
        "PackCaveat",
        parent=base["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#e53e3e"),
    )
    styles["footer"] = ParagraphStyle(
        "PackFooter",
        parent=base["Normal"],
        fontSize=7,
        leading=10,
        textColor=colors.grey,
    )
    styles["metric_label"] = ParagraphStyle(
        "MetricLabel",
        parent=base["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#718096"),
    )
    styles["metric_value"] = ParagraphStyle(
        "MetricValue",
        parent=base["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#1a365d"),
    )
    return styles


def _grade_color(grade: str) -> colors.Color:
    """Map passport grade to a colour."""
    mapping = {
        "A": colors.HexColor("#38a169"),
        "B": colors.HexColor("#68d391"),
        "C": colors.HexColor("#ecc94b"),
        "D": colors.HexColor("#ed8936"),
        "E": colors.HexColor("#e53e3e"),
        "F": colors.HexColor("#9b2c2c"),
    }
    return mapping.get(grade, colors.grey)


def _build_pdf_reportlab(pack_data: dict, output_path: str) -> None:
    """Build a real PDF using reportlab."""
    styles = _build_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story: list[Any] = []

    # --- Header ---
    pack_name = pack_data.get("pack_name", "Pack BatiConnect")
    story.append(Paragraph("BatiConnect", styles["title"]))
    story.append(Paragraph(pack_name, styles["subtitle"]))
    story.append(Spacer(1, 4 * mm))

    # --- Building info ---
    building = pack_data.get("building_info", {})
    address = building.get("address", "Adresse inconnue")
    city = building.get("city", "")
    canton = building.get("canton", "")
    egid = building.get("egid", "")
    building_line = f"<b>{address}</b>"
    if city:
        building_line += f", {city}"
    if canton:
        building_line += f" ({canton})"
    if egid:
        building_line += f" — EGID {egid}"
    story.append(Paragraph(building_line, styles["body"]))
    story.append(Spacer(1, 6 * mm))

    # --- Key metrics table ---
    grade = pack_data.get("passport_grade", "—")
    completeness = pack_data.get("overall_completeness", 0)
    readiness = pack_data.get("readiness_verdict", "—")
    caveats_count = pack_data.get("caveats_count", 0)
    financials_redacted = pack_data.get("financials_redacted", False)

    metric_data = [
        ["Note", "Completude", "Readiness", "Reserves"],
        [
            grade,
            f"{completeness:.0%}" if isinstance(completeness, (int, float)) else str(completeness),
            str(readiness),
            str(caveats_count),
        ],
    ]
    grade_c = _grade_color(grade)
    metric_table = Table(metric_data, colWidths=[4 * cm, 4 * cm, 5 * cm, 3 * cm])
    metric_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, 1), 14),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TEXTCOLOR", (0, 1), (0, 1), grade_c),
            ]
        )
    )
    story.append(metric_table)

    if financials_redacted:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Donnees financieres expurgees", styles["caveat"]))

    story.append(Spacer(1, 8 * mm))

    # --- Sections ---
    sections = pack_data.get("sections", [])
    for section in sections:
        section_name = section.get("section_name", section.get("section_type", "Section"))
        section_type = section.get("section_type", "")
        items = section.get("items", [])
        section_completeness = section.get("completeness", 1.0)

        story.append(
            Paragraph(
                f"{section_name} ({section_completeness:.0%})"
                if isinstance(section_completeness, (int, float))
                else section_name,
                styles["section_title"],
            )
        )

        if section.get("notes"):
            story.append(Paragraph(str(section["notes"]), styles["body"]))
            story.append(Spacer(1, 2 * mm))

        # Render caveats section specially
        if section_type == "caveats":
            for item in items:
                text = item.get("text", item.get("caveat", str(item)))
                story.append(Paragraph(f"• {text}", styles["caveat"]))
            story.append(Spacer(1, 4 * mm))
            continue

        # Render other sections as key-value tables
        if items:
            for item in items[:20]:  # cap per section to avoid huge PDFs
                if isinstance(item, dict):
                    for k, v in item.items():
                        if k.startswith("_"):
                            continue
                        label = k.replace("_", " ").capitalize()
                        value = str(v) if v is not None else "—"
                        if len(value) > 200:
                            value = value[:200] + "..."
                        story.append(Paragraph(f"<b>{label}:</b> {value}", styles["body"]))
                else:
                    story.append(Paragraph(f"• {item}", styles["body"]))
            if len(items) > 20:
                story.append(Paragraph(f"... et {len(items) - 20} element(s) supplementaire(s)", styles["body"]))
        else:
            story.append(Paragraph("Aucune donnee disponible.", styles["body"]))

        story.append(Spacer(1, 4 * mm))

    # --- Footer ---
    story.append(Spacer(1, 10 * mm))
    sha = pack_data.get("sha256_hash", "—")
    gen_date = pack_data.get("generated_at", datetime.now(UTC).isoformat())
    version = pack_data.get("pack_version", "1.0.0")

    story.append(Paragraph(f"SHA-256: {sha}", styles["footer"]))
    story.append(Paragraph(f"Date de generation: {gen_date}", styles["footer"]))
    story.append(Paragraph(f"Version: {version}", styles["footer"]))
    story.append(Paragraph("Genere par BatiConnect — batiscan.ch", styles["footer"]))

    doc.build(story)


# ---------------------------------------------------------------------------
# HTML fallback
# ---------------------------------------------------------------------------


def _build_html_fallback(pack_data: dict, output_path: str) -> None:
    """Generate a structured HTML file as PDF fallback."""
    pack_name = pack_data.get("pack_name", "Pack BatiConnect")
    building = pack_data.get("building_info", {})
    address = building.get("address", "Adresse inconnue")
    city = building.get("city", "")
    canton = building.get("canton", "")
    grade = pack_data.get("passport_grade", "—")
    completeness = pack_data.get("overall_completeness", 0)
    readiness = pack_data.get("readiness_verdict", "—")
    sha = pack_data.get("sha256_hash", "—")
    gen_date = pack_data.get("generated_at", datetime.now(UTC).isoformat())
    version = pack_data.get("pack_version", "1.0.0")
    sections = pack_data.get("sections", [])

    lines = [
        "<!DOCTYPE html>",
        "<html lang='fr'><head><meta charset='utf-8'>",
        f"<title>{pack_name}</title>",
        "<style>",
        "body{font-family:sans-serif;max-width:800px;margin:auto;padding:2em;color:#2d3748}",
        "h1{color:#1a365d} h2{color:#2b6cb0;border-bottom:1px solid #e2e8f0;padding-bottom:4px}",
        ".metric{display:inline-block;text-align:center;padding:12px 24px;margin:6px;",
        "background:#edf2f7;border-radius:6px}",
        ".metric .value{font-size:1.5em;font-weight:bold}",
        ".caveat{color:#e53e3e;font-size:0.9em}",
        ".footer{color:#a0aec0;font-size:0.8em;margin-top:3em;border-top:1px solid #e2e8f0;padding-top:1em}",
        "</style></head><body>",
        "<h1>BatiConnect</h1>",
        f"<h2>{pack_name}</h2>",
        f"<p><strong>{address}</strong>{', ' + city if city else ''}{' (' + canton + ')' if canton else ''}</p>",
        '<div class="metrics">',
        f'<div class="metric"><div class="value">{grade}</div><div>Note</div></div>',
        f'<div class="metric"><div class="value">{completeness:.0%}</div><div>Completude</div></div>',
        f'<div class="metric"><div class="value">{readiness}</div><div>Readiness</div></div>',
        "</div>",
    ]

    for section in sections:
        s_name = section.get("section_name", "Section")
        s_type = section.get("section_type", "")
        items = section.get("items", [])
        lines.append(f"<h2>{s_name}</h2>")
        if s_type == "caveats":
            for item in items:
                text = item.get("text", item.get("caveat", str(item)))
                lines.append(f'<p class="caveat">• {text}</p>')
        elif items:
            lines.append("<ul>")
            for item in items[:20]:
                if isinstance(item, dict):
                    parts = ", ".join(f"{k}: {v}" for k, v in item.items() if not k.startswith("_"))
                    lines.append(f"<li>{parts}</li>")
                else:
                    lines.append(f"<li>{item}</li>")
            lines.append("</ul>")
        else:
            lines.append("<p>Aucune donnee disponible.</p>")

    lines.append('<div class="footer">')
    lines.append(f"<p>SHA-256: {sha}</p>")
    lines.append(f"<p>Date de generation: {gen_date}</p>")
    lines.append(f"<p>Version: {version}</p>")
    lines.append("<p>Genere par BatiConnect — batiscan.ch</p>")
    lines.append("</div></body></html>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Public service class
# ---------------------------------------------------------------------------


class PDFGeneratorService:
    """Generate PDF artifacts from pack data."""

    async def generate_pack_pdf(self, pack_data: dict, output_dir: str | None = None) -> dict:
        """Generate a PDF from pack data.

        Returns dict with pdf_path, filename, size_bytes, sha256, generated_at.
        """
        artifact_dir = _ensure_artifact_dir(output_dir)
        pack_type = pack_data.get("pack_type", "pack")
        pack_id = pack_data.get("pack_id", str(uuid.uuid4()))

        ext = "pdf" if HAS_REPORTLAB else "html"
        filename = f"baticonnect_{pack_type}_{pack_id[:8]}.{ext}"
        output_path = os.path.join(artifact_dir, filename)

        if HAS_REPORTLAB:
            _build_pdf_reportlab(pack_data, output_path)
        else:
            _build_html_fallback(pack_data, output_path)

        # Compute SHA-256 of generated file
        with open(output_path, "rb") as f:
            file_bytes = f.read()
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        size_bytes = len(file_bytes)
        generated_at = datetime.now(UTC)

        return {
            "pdf_path": output_path,
            "filename": filename,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "generated_at": generated_at,
        }

    async def generate_authority_pack_pdf(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
        org_id: uuid.UUID | None,
        created_by_id: uuid.UUID,
        *,
        redact_financials: bool = False,
        output_dir: str | None = None,
    ) -> dict:
        """Generate authority pack + write PDF. Delegates to authority_pack_service."""
        from app.schemas.authority_pack import AuthorityPackConfig
        from app.services.authority_pack_service import generate_authority_pack

        config = AuthorityPackConfig(
            building_id=building_id,
            redact_financials=redact_financials,
        )
        result = await generate_authority_pack(db, building_id, config, created_by_id)
        pack_data = _authority_pack_to_dict(result)
        return await self.generate_pack_pdf(pack_data, output_dir=output_dir)

    async def generate_transaction_pack_pdf(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
        org_id: uuid.UUID | None,
        created_by_id: uuid.UUID,
        *,
        redact_financials: bool = True,
        output_dir: str | None = None,
    ) -> dict:
        """Generate transaction pack + write PDF. Delegates to pack_builder."""
        from app.services.pack_builder_service import generate_pack

        result = await generate_pack(
            db,
            building_id,
            "transaction",
            org_id=org_id,
            created_by_id=created_by_id,
            redact_financials=redact_financials,
        )
        pack_data = _pack_result_to_dict(result)
        return await self.generate_pack_pdf(pack_data, output_dir=output_dir)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _authority_pack_to_dict(result: Any) -> dict:
    """Convert an AuthorityPackResult to a flat dict for PDF rendering."""
    data = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    sections = data.get("sections", [])
    # Extract building_info from building_identity section if present
    building_info: dict[str, Any] = {}
    for s in sections:
        if s.get("section_type") == "building_identity" and s.get("items"):
            first = s["items"][0] if s["items"] else {}
            building_info = {
                "address": first.get("address", ""),
                "city": first.get("city", ""),
                "canton": first.get("canton", data.get("canton", "")),
                "egid": first.get("egid", ""),
            }
            break

    # Extract grade from passport_summary section
    grade = "—"
    for s in sections:
        if s.get("section_type") == "passport_summary" and s.get("items"):
            first = s["items"][0] if s["items"] else {}
            grade = first.get("passport_grade", first.get("grade", "—"))
            break

    # Extract readiness verdict
    readiness = "—"
    for s in sections:
        if s.get("section_type") == "readiness_verdict" and s.get("items"):
            first = s["items"][0] if s["items"] else {}
            readiness = first.get("verdict", first.get("readiness", "—"))
            break

    return {
        "pack_id": str(data.get("pack_id", "")),
        "pack_type": "authority",
        "pack_name": "Pack Autorite",
        "building_info": building_info,
        "passport_grade": grade,
        "overall_completeness": data.get("overall_completeness", 0),
        "readiness_verdict": readiness,
        "caveats_count": data.get("caveats_count", 0),
        "sections": sections,
        "sha256_hash": data.get("sha256_hash", ""),
        "generated_at": str(data.get("generated_at", "")),
        "pack_version": data.get("pack_version", "1.0.0"),
        "financials_redacted": data.get("financials_redacted", False),
    }


def _pack_result_to_dict(result: Any) -> dict:
    """Convert a PackResult to a flat dict for PDF rendering."""
    data = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    sections = data.get("sections", [])

    building_info: dict[str, Any] = {}
    grade = "—"
    readiness = "—"
    for s in sections:
        st = s.get("section_type", "")
        items = s.get("items", [])
        first = items[0] if items else {}
        if st == "building_identity" and items:
            building_info = {
                "address": first.get("address", ""),
                "city": first.get("city", ""),
                "canton": first.get("canton", ""),
                "egid": first.get("egid", ""),
            }
        if st == "passport_summary" and items:
            grade = first.get("passport_grade", first.get("grade", "—"))
        if st == "readiness_verdict" and items:
            readiness = first.get("verdict", first.get("readiness", "—"))

    return {
        "pack_id": str(data.get("pack_id", "")),
        "pack_type": data.get("pack_type", "pack"),
        "pack_name": data.get("pack_name", "Pack BatiConnect"),
        "building_info": building_info,
        "passport_grade": grade,
        "overall_completeness": data.get("overall_completeness", 0),
        "readiness_verdict": readiness,
        "caveats_count": data.get("caveats_count", 0),
        "sections": sections,
        "sha256_hash": data.get("sha256_hash", ""),
        "generated_at": str(data.get("generated_at", "")),
        "pack_version": data.get("pack_version", "1.0.0"),
        "financials_redacted": data.get("financials_redacted", False),
    }
