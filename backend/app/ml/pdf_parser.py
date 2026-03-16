"""
SwissBuildingOS - PDF Parser for Diagnostic Reports

Extracts structured data from Swiss building diagnostic PDF reports.
Supports both text-based and scanned (OCR) PDFs.
"""

from __future__ import annotations

import re
from typing import Any


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a text-based PDF using pdfplumber.

    Returns the concatenated text of all pages.
    """
    import pdfplumber

    text_parts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n\n".join(text_parts)


def extract_text_with_ocr(file_path: str) -> str:
    """
    Extract text from a scanned PDF using pdf2image + pytesseract OCR.

    Falls back to this method when pdfplumber returns little or no text.
    """
    import pytesseract
    from pdf2image import convert_from_path

    images = convert_from_path(file_path, dpi=300)
    text_parts: list[str] = []
    for image in images:
        # Use French + German + Italian for Swiss documents
        page_text = pytesseract.image_to_string(image, lang="fra+deu+ita")
        if page_text.strip():
            text_parts.append(page_text)

    return "\n\n".join(text_parts)


# ---------------------------------------------------------------------------
# Regex patterns for Swiss diagnostic reports
# ---------------------------------------------------------------------------

# Sample number patterns (e.g., "E-01", "P-12", "AM-003", "Ech. 5")
_SAMPLE_NUMBER_RE = re.compile(
    r"(?:(?:E|P|AM|ECH|Ech|ech)[\s.\-]*(\d{1,4}))",
    re.IGNORECASE,
)

# Concentration patterns (e.g., "1.2 %", "350 mg/kg", "< 0.001 %")
_CONCENTRATION_RE = re.compile(
    r"(<?\s*[\d]+[.,]?\d*)\s*(%|mg/kg|ppm|f/m[23]|ng/m[23]|Bq/m[23]|fibres?/m[23]|ug/l)",
    re.IGNORECASE,
)

# Asbestos result patterns
_ASBESTOS_RESULT_RE = re.compile(
    r"(chrysotile|amosite|crocidolite|tremolite|actinolite|anthophyllite|"
    r"amiante|asbestos?|amiant)"
    r"[\s:]*"
    r"(detect[eé]|pr[eé]sent|positif|positive|n[eé]gatif|negative|"
    r"non[\s-]?detect[eé]|absent|nd|pos|neg)",
    re.IGNORECASE,
)

# PCB result pattern
_PCB_RESULT_RE = re.compile(
    r"(PCB|polychlorobiphen[yé]l)"
    r"[\s:]*"
    r"(?:total[\s:]*)?(<?\s*[\d]+[.,]?\d*)\s*(mg/kg|ppm)",
    re.IGNORECASE,
)

# Lead result pattern
_LEAD_RESULT_RE = re.compile(
    r"(plomb|lead|Pb)"
    r"[\s:]*"
    r"(?:total[\s:]*)?(<?\s*[\d]+[.,]?\d*)\s*(mg/kg|ppm|%)",
    re.IGNORECASE,
)

# HAP result pattern
_HAP_RESULT_RE = re.compile(
    r"(HAP|PAK|hydrocarbures?\s+aromatiques?\s+polycycliques?)"
    r"[\s:]*"
    r"(?:total[\s:]*)?(<?\s*[\d]+[.,]?\d*)\s*(mg/kg|ppm)",
    re.IGNORECASE,
)

# Laboratory name
_LABORATORY_RE = re.compile(
    r"(?:laboratoire|labor|lab\.?)[\s:]+([A-Za-z\s\-&.]+?)(?:\n|,|;)",
    re.IGNORECASE,
)

# Report number
_REPORT_NUMBER_RE = re.compile(
    r"(?:rapport|report|Bericht)[\s]*(?:n[o°.]?|nr\.?|no\.?)[\s:]*([A-Za-z0-9\-/.]+)",
    re.IGNORECASE,
)

# Date patterns (DD.MM.YYYY or DD/MM/YYYY)
_DATE_RE = re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{4})")

# Location / floor patterns
_LOCATION_RE = re.compile(
    r"(?:etage|floor|stock|niveau|local|piece|salle|raum|zimmer)"
    r"[\s:]+([^\n,;]+)",
    re.IGNORECASE,
)

# Material patterns
_MATERIAL_RE = re.compile(
    r"(colle|carrelage|dalle|vinyl|linol[eé]um|fibrociment|"
    r"eternit|flocage|calorifuge|joint|mastic|enduit|"
    r"cr[eé]pi|peinture|rev[eê]tement|isolation|toiture|"
    r"bitume|goudron|moquette|parquet)",
    re.IGNORECASE,
)


def _parse_concentration(raw: str) -> float | None:
    """Parse a concentration string, handling '<' (below detection limit) and comma decimals."""
    cleaned = raw.strip()
    below_limit = cleaned.startswith("<")
    cleaned = cleaned.lstrip("< ")
    cleaned = cleaned.replace(",", ".")
    try:
        value = float(cleaned)
        if below_limit:
            # Return half the detection limit as estimate
            return value / 2.0
        return value
    except ValueError:
        return None


def parse_diagnostic_report(text: str) -> dict[str, Any]:
    """
    Extract structured data from diagnostic report text.

    Returns a dict with keys:
      - samples: list of dicts with sample_number, location, material,
                 pollutant_type, result, concentration, unit
      - laboratory: str or None
      - report_number: str or None
      - date: str or None (YYYY-MM-DD format)
      - conclusion: str or None
    """
    samples: list[dict[str, Any]] = []

    # Extract metadata
    lab_match = _LABORATORY_RE.search(text)
    laboratory = lab_match.group(1).strip() if lab_match else None

    report_match = _REPORT_NUMBER_RE.search(text)
    report_number = report_match.group(1).strip() if report_match else None

    # Find the last date in the document (usually the report date)
    date_matches = _DATE_RE.findall(text)
    date_str = None
    if date_matches:
        day, month, year = date_matches[-1]
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # Try to extract conclusion
    conclusion = _extract_conclusion(text)

    # Split text into lines for line-by-line analysis
    lines = text.split("\n")

    # Track current context
    current_sample_number: str | None = None
    current_location: str | None = None
    current_material: str | None = None

    for _i, line in enumerate(lines):
        # Check for sample number
        sample_match = _SAMPLE_NUMBER_RE.search(line)
        if sample_match:
            current_sample_number = sample_match.group(0).strip()

        # Check for location
        loc_match = _LOCATION_RE.search(line)
        if loc_match:
            current_location = loc_match.group(1).strip()

        # Check for material
        mat_match = _MATERIAL_RE.search(line)
        if mat_match:
            current_material = mat_match.group(0).strip()

        # Check for asbestos results
        asbestos_match = _ASBESTOS_RESULT_RE.search(line)
        if asbestos_match:
            result_text = asbestos_match.group(2).lower()
            is_positive = any(kw in result_text for kw in ["detect", "present", "positif", "positive", "pos"])
            conc_match = _CONCENTRATION_RE.search(line)
            concentration = None
            unit = None
            if conc_match:
                concentration = _parse_concentration(conc_match.group(1))
                unit = conc_match.group(2)

            samples.append(
                {
                    "sample_number": current_sample_number or f"S-{len(samples) + 1}",
                    "location": current_location,
                    "material": current_material,
                    "pollutant_type": "asbestos",
                    "pollutant_subtype": asbestos_match.group(1).strip(),
                    "result": "positive" if is_positive else "negative",
                    "concentration": concentration,
                    "unit": unit,
                }
            )

        # Check for PCB results
        pcb_match = _PCB_RESULT_RE.search(line)
        if pcb_match:
            concentration = _parse_concentration(pcb_match.group(2))
            unit = pcb_match.group(3)
            is_positive = concentration is not None and concentration >= 50
            samples.append(
                {
                    "sample_number": current_sample_number or f"S-{len(samples) + 1}",
                    "location": current_location,
                    "material": current_material,
                    "pollutant_type": "pcb",
                    "pollutant_subtype": None,
                    "result": "positive" if is_positive else "negative",
                    "concentration": concentration,
                    "unit": unit,
                }
            )

        # Check for lead results
        lead_match = _LEAD_RESULT_RE.search(line)
        if lead_match:
            concentration = _parse_concentration(lead_match.group(2))
            unit = lead_match.group(3)
            threshold = 5000 if unit in ("mg/kg", "ppm") else 1.0
            is_positive = concentration is not None and concentration >= threshold
            samples.append(
                {
                    "sample_number": current_sample_number or f"S-{len(samples) + 1}",
                    "location": current_location,
                    "material": current_material,
                    "pollutant_type": "lead",
                    "pollutant_subtype": None,
                    "result": "positive" if is_positive else "negative",
                    "concentration": concentration,
                    "unit": unit,
                }
            )

        # Check for HAP results
        hap_match = _HAP_RESULT_RE.search(line)
        if hap_match:
            concentration = _parse_concentration(hap_match.group(2))
            unit = hap_match.group(3)
            is_positive = concentration is not None and concentration >= 200
            samples.append(
                {
                    "sample_number": current_sample_number or f"S-{len(samples) + 1}",
                    "location": current_location,
                    "material": current_material,
                    "pollutant_type": "hap",
                    "pollutant_subtype": None,
                    "result": "positive" if is_positive else "negative",
                    "concentration": concentration,
                    "unit": unit,
                }
            )

    return {
        "samples": samples,
        "laboratory": laboratory,
        "report_number": report_number,
        "date": date_str,
        "conclusion": conclusion,
    }


def _extract_conclusion(text: str) -> str | None:
    """
    Attempt to extract the conclusion section from a diagnostic report.
    Swiss reports typically have a 'Conclusion' or 'Schlussfolgerung' section.
    """
    conclusion_patterns = [
        re.compile(
            r"(?:conclusion|conclusions|schlussfolgerung|zusammenfassung|r[eé]sum[eé])"
            r"[\s:]*\n([\s\S]{10,500}?)(?:\n\n|\Z)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:en conclusion|zusammenfassend|il est recommand[eé])"
            r"([\s\S]{10,300}?)(?:\.\s*\n|\Z)",
            re.IGNORECASE,
        ),
    ]

    for pattern in conclusion_patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()

    return None
