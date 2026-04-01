"""
SwissBuildingOS - Diagnostic PDF Analyzer

Quick analysis of diagnostic PDFs without full extraction.
Detects document type, pollutants, materials, structure, and language
using regex patterns from the existing document_extraction_service.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Document type patterns
# ---------------------------------------------------------------------------

_DOC_TYPE_PATTERNS: dict[str, list[re.Pattern]] = {
    "diagnostic_report": [
        re.compile(
            r"\b(?:rapport\s+de\s+diagnostic|diagnostic\s+(?:amiante|plomb|pcb|hap|radon|pfas)|"
            r"Diagnosebericht|rapporto\s+di\s+diagnosi|diagnostic\s+report)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:rep[eé]rage|expertise\s+polluants?|Schadstoffgutachten|perizia)\b",
            re.IGNORECASE,
        ),
    ],
    "lab_result": [
        re.compile(
            r"\b(?:r[eé]sultat(?:s)?\s+(?:d[''']analyse|de\s+laboratoire)|"
            r"Laborergebnis|risultati?\s+di\s+laboratorio|"
            r"lab(?:oratory)?\s+result|bulletin\s+d[''']analyse)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:analyse\s+(?:par|en)\s+(?:microscopie|MET|DRX|PLM|spectrométrie)|"
            r"Analysenbericht|certificato\s+d[''']analisi)\b",
            re.IGNORECASE,
        ),
    ],
    "quote": [
        re.compile(
            r"\b(?:devis|offre\s+de\s+prix|estimation|Offerte|Kostenvoranschlag|"
            r"preventivo|quotation|quote|estimate)\b",
            re.IGNORECASE,
        ),
    ],
    "plan": [
        re.compile(
            r"\b(?:plan\s+(?:de\s+situation|d['''](?:étage|intervention)|technique)|"
            r"Situationsplan|Grundriss|pianta|floor\s+plan|site\s+plan)\b",
            re.IGNORECASE,
        ),
    ],
}

# ---------------------------------------------------------------------------
# Pollutant detection patterns
# ---------------------------------------------------------------------------

_POLLUTANT_PATTERNS: dict[str, re.Pattern] = {
    "asbestos": re.compile(
        r"\b(?:amiante|chrysotile|crocidolite|amosite|tremolite|actinolite|anthophyllite|"
        r"Asbest|amianto|asbestos|MCA|FRAL|fibre\s+amphibole)\b",
        re.IGNORECASE,
    ),
    "pcb": re.compile(
        r"\b(?:PCB|polychlorobiph[eé]nyl|Aroclor|clophen|"
        r"polychlorierte\s+Biphenyle|bifenili\s+policlorurati)\b",
        re.IGNORECASE,
    ),
    "lead": re.compile(
        r"\b(?:plomb|Blei|piombo|lead|Pb|peinture\s+au\s+plomb|"
        r"c[eé]ruse|minium)\b",
        re.IGNORECASE,
    ),
    "hap": re.compile(
        r"\b(?:HAP|PAK|IPA|PAH|hydrocarbure(?:s)?\s+aromatique(?:s)?\s+polycyclique(?:s)?|"
        r"benz[oa]?\[a\]pyr[eè]ne|goudron|teer|catrame)\b",
        re.IGNORECASE,
    ),
    "radon": re.compile(
        r"\b(?:radon|Rn[\s-]?222|Bq/m[³3]|dosim[eè]tre\s+radon|"
        r"Radonmessung|misurazione\s+radon)\b",
        re.IGNORECASE,
    ),
    "pfas": re.compile(
        r"\b(?:PFAS|PFOA|PFOS|substance(?:s)?\s+per-?\s*et\s+polyfluoroalkyl[eé](?:e|s)?|"
        r"per-?\s*und\s+Polyfluoralkyl)\b",
        re.IGNORECASE,
    ),
}

# ---------------------------------------------------------------------------
# Material detection patterns
# ---------------------------------------------------------------------------

_MATERIAL_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(?:fibre-?ciment|fibrociment|Faserzement|fibrocemento|"
        r"fiber[\s-]?cement|eternit)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:joint(?:s)?\s+(?:d[''']?[eé]tanch[eé]it[eé]|de\s+dilatation|silicone)|"
        r"Dichtung|guarnizione|sealant|gasket|mastic)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:rev[eê]tement\s+de\s+sol|dalles?\s+(?:vinyl|PVC)|"
        r"Bodenbelag|rivestimento\s+del\s+pavimento|floor\s+covering|"
        r"linol[eé]um|cushion[\s-]?vinyl)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:isolant|isolation\s+thermique|calorifuge(?:age)?|"
        r"D[aä]mmung|isolamento|insulation|laine\s+de\s+verre|"
        r"laine\s+min[eé]rale|laine\s+de\s+roche)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:colle|Kleber|colla|adhesive|glue|"
        r"colle\s+(?:de\s+carrelage|à\s+bois|de\s+faïence))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:peinture|Farbe|Anstrich|vernice|paint|"
        r"enduit|cr[eé]pi|Putz|intonaco|plaster)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:toiture|couverture|Dach|tetto|roof|"
        r"tuile|Ziegel|tegola|tile|ardoise|Schiefer|ardesia|slate)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:conduite|canalisation|tuyau|Rohr|Leitung|tubazione|pipe|"
        r"gaine\s+(?:technique|de\s+ventilation))\b",
        re.IGNORECASE,
    ),
]

# ---------------------------------------------------------------------------
# Structure detection patterns (samples table, floor plan)
# ---------------------------------------------------------------------------

_SAMPLES_TABLE_PATTERNS = [
    re.compile(
        r"(?:pr[eé]l[eè]vement|[eé]chantillon|Probe|campione|sample)\s*(?:n[°o.]?|Nr\.?|#)\s*\d",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:S-\d{3,}|ECH[\s-]?\d{3,}|P[\s-]?\d{3,})\b"),
    re.compile(
        r"(?:local(?:isation)?|emplacement|Standort|posizione|location)\s*\|?\s*(?:mat[eé]riau|Material|materiale|material)",
        re.IGNORECASE,
    ),
]

_FLOOR_PLAN_PATTERNS = [
    re.compile(
        r"\b(?:plan\s+(?:d[''']?[eé]tage|de\s+rep[eé]rage|de\s+situation)|"
        r"Grundriss|Lageplan|pianta|floor\s+plan)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:annexe\s+(?:plan|graphique)|Anlage\s+Plan|allegato\s+pianta)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_LANGUAGE_INDICATORS: dict[str, list[str]] = {
    "fr": ["rapport", "diagnostic", "prélèvement", "échantillon", "bâtiment", "étage", "résultat", "analyse"],
    "de": ["Bericht", "Diagnose", "Probe", "Gebäude", "Stockwerk", "Ergebnis", "Analyse", "Schadstoff"],
    "it": ["rapporto", "diagnosi", "campione", "edificio", "piano", "risultato", "analisi", "inquinante"],
    "en": ["report", "diagnostic", "sample", "building", "floor", "result", "analysis", "pollutant"],
}


def _detect_language(text: str) -> str:
    """Detect dominant language from word frequency."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for lang, words in _LANGUAGE_INDICATORS.items():
        scores[lang] = sum(1 for w in words if w.lower() in text_lower)
    if not scores or max(scores.values()) == 0:
        return "fr"  # default
    return max(scores, key=lambda k: scores[k])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def analyze_diagnostic_pdf(file_content: bytes) -> dict[str, Any]:
    """Quick analysis of a diagnostic PDF without full extraction.

    Decodes text from bytes (assumes pre-OCR'd text or text-layer PDF).
    Returns document type, detected pollutants, materials, structure info,
    confidence, language, and a brief summary.
    """
    # Decode text — try UTF-8, fall back to latin-1
    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = file_content.decode("latin-1")
        except Exception:
            text = ""

    if not text.strip():
        return {
            "document_type": "unknown",
            "detected_pollutants": [],
            "detected_materials": [],
            "page_count": 0,
            "has_samples_table": False,
            "has_floor_plan": False,
            "confidence": 0.0,
            "language": "fr",
            "summary": "",
        }

    # Detect document type
    doc_type = "unknown"
    doc_type_confidence = 0.0
    for dtype, patterns in _DOC_TYPE_PATTERNS.items():
        for pat in patterns:
            if pat.search(text):
                doc_type = dtype
                doc_type_confidence = 0.85
                break
        if doc_type != "unknown":
            break

    # Detect pollutants
    detected_pollutants: list[str] = []
    for pollutant, pattern in _POLLUTANT_PATTERNS.items():
        if pattern.search(text):
            detected_pollutants.append(pollutant)

    # Detect materials
    detected_materials: list[str] = []
    material_names = [
        "fibre-ciment",
        "joints",
        "revêtement de sol",
        "isolant",
        "colle",
        "peinture",
        "toiture",
        "conduite",
    ]
    for idx, pattern in enumerate(_MATERIAL_PATTERNS):
        if pattern.search(text):
            detected_materials.append(material_names[idx])

    # Estimate page count (look for page markers)
    page_markers = re.findall(r"\b(?:page|Page|Seite|pagina)\s+(\d+)\b", text, re.IGNORECASE)
    form_feed_count = text.count("\f")
    if page_markers:
        page_count = max(int(p) for p in page_markers)
    elif form_feed_count > 0:
        page_count = form_feed_count + 1
    else:
        # Rough estimate: ~3000 chars per page
        page_count = max(1, len(text) // 3000)

    # Check for samples table
    has_samples_table = any(pat.search(text) for pat in _SAMPLES_TABLE_PATTERNS)

    # Check for floor plan reference
    has_floor_plan = any(pat.search(text) for pat in _FLOOR_PLAN_PATTERNS)

    # Detect language
    language = _detect_language(text)

    # Compute confidence
    confidence = doc_type_confidence
    if detected_pollutants:
        confidence = max(confidence, 0.7)
    if has_samples_table:
        confidence += 0.05
    if detected_materials:
        confidence += 0.05
    confidence = min(1.0, confidence)

    # Count samples if detected
    sample_count = 0
    if has_samples_table:
        # Count sample references
        sample_refs = re.findall(r"\b(?:S-\d+|ECH[\s-]?\d+|P[\s-]?\d+)\b", text)
        sample_count = len(set(sample_refs))
        if sample_count == 0:
            # Try counting numbered samples
            numbered = re.findall(
                r"(?:pr[eé]l[eè]vement|[eé]chantillon|Probe|sample)\s*n?[°o.]?\s*(\d+)", text, re.IGNORECASE
            )
            sample_count = len(set(numbered))

    # Count positive results
    positive_count = len(
        re.findall(
            r"\b(?:positif|positiv|positivo|positive|détecté|nachgewiesen|rilevato|detected)\b", text, re.IGNORECASE
        )
    )

    # Build summary
    summary_parts: list[str] = []
    if doc_type == "diagnostic_report":
        pollutant_str = ", ".join(detected_pollutants) if detected_pollutants else "polluants"
        summary_parts.append(f"Diagnostic {pollutant_str}")
        if sample_count:
            summary_parts.append(f"{sample_count} prélèvements")
        if positive_count:
            summary_parts.append(f"{positive_count} positifs")
    elif doc_type == "lab_result":
        summary_parts.append("Résultats de laboratoire")
        if detected_pollutants:
            summary_parts.append(", ".join(detected_pollutants))
    elif doc_type == "quote":
        summary_parts.append("Devis")
        if detected_pollutants:
            summary_parts.append(f"travaux {', '.join(detected_pollutants)}")
    elif doc_type == "plan":
        summary_parts.append("Plan technique")
    else:
        summary_parts.append("Document non classifié")

    summary = " - ".join(summary_parts) if summary_parts else ""

    return {
        "document_type": doc_type,
        "detected_pollutants": detected_pollutants,
        "detected_materials": detected_materials,
        "page_count": page_count,
        "has_samples_table": has_samples_table,
        "has_floor_plan": has_floor_plan,
        "confidence": round(confidence, 2),
        "language": language,
        "summary": summary,
    }
