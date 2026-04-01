"""Document extraction service — regex-based structured data extraction from document text.

Extracts dates, amounts, addresses, parcels, CFC codes, parties, references,
pollutant results, energy classes, and building years from OCR'd text.
No LLM needed — pure regex + heuristics. All extractions flagged ai_generated=True.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

# ---------------------------------------------------------------------------
# Extraction field types
# ---------------------------------------------------------------------------

FIELD_TYPES = [
    "dates",
    "amounts",
    "addresses",
    "parcels",
    "cfc_codes",
    "parties",
    "references",
    "pollutant_results",
    "energy_class",
    "building_year",
]

# ---------------------------------------------------------------------------
# Regex patterns (FR / DE / IT / EN — 4 Swiss languages)
# ---------------------------------------------------------------------------

# Swiss date formats: dd.mm.yyyy, dd/mm/yyyy, dd. Monat yyyy
_MONTHS_FR = r"(?:janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre)"
_MONTHS_DE = r"(?:Januar|Februar|M[aä]rz|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)"
_MONTHS_IT = r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)"
_MONTHS_EN = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
_MONTHS_ALL = f"(?:{_MONTHS_FR}|{_MONTHS_DE}|{_MONTHS_IT}|{_MONTHS_EN})"

DATE_PATTERNS = [
    # dd.mm.yyyy or dd/mm/yyyy
    re.compile(r"\b(\d{1,2}[./]\d{1,2}[./]\d{4})\b"),
    # dd. Month yyyy (with optional dot after day)
    re.compile(rf"\b(\d{{1,2}}\.?\s+{_MONTHS_ALL}\s+\d{{4}})\b", re.IGNORECASE),
]

# CHF amounts: CHF 1'234.56, Fr. 1234.-, 1'234 CHF, CHF 1234, CHF 1'234'567.80
AMOUNT_PATTERNS = [
    # CHF / Fr. prefix
    re.compile(r"\b((?:CHF|Fr\.?)\s*\d[\d']*(?:\.\d{2}|-)?)\b", re.IGNORECASE),
    # Suffix: 1'234.56 CHF
    re.compile(r"\b(\d[\d']*(?:\.\d{2}|-)?)\s*(?:CHF|Fr\.?)\b", re.IGNORECASE),
]

# Swiss addresses: Rue/Strasse/Via X 12, NPA Ville
ADDRESS_PATTERNS = [
    # French/English style: Rue/Avenue/... Name 12, NPA City
    re.compile(
        r"((?:(?:Rue|Avenue|Chemin|Route|Boulevard|Place|Passage|Impasse|Quai|"
        r"Via|Piazza|Vicolo|Viale|"
        r"Street|Road|Lane|Square)\s+[A-ZÀ-Ü][\w\s\-']{1,40}?\s*\d{1,5}[a-zA-Z]?)\s*[,\n]\s*(\d{4})\s+([A-ZÀ-Ü][\wÀ-ü\-\s]{1,30}))",
        re.IGNORECASE | re.MULTILINE,
    ),
    # German style: Compound+strasse/gasse/weg/platz 12, NPA City
    re.compile(
        r"((?:[A-ZÀ-Ü][\wÀ-ü\-]{2,30}(?:strasse|gasse|weg|platz))\s+\d{1,5}[a-zA-Z]?\s*[,\n]\s*(\d{4})\s+([A-ZÀ-Ü][\wÀ-ü\-\s]{1,30}))",
        re.IGNORECASE | re.MULTILINE,
    ),
]

# Cadastral references: parcelle n° XXX, Parzelle Nr. XXX, parcella n. XXX
PARCEL_PATTERNS = [
    re.compile(
        r"\b(?:parcelle|parzelle|parcella|parcel)\s*(?:n[°o.]?|Nr\.?|no\.?)\s*(\d[\d\-/]*)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:RF|DP|DDP)\s*(\d[\d\-/]*)\b"),
]

# CFC codes: CFC 281, CFC 371.1
CFC_PATTERNS = [
    re.compile(r"\b(CFC\s*\d{2,3}(?:\.\d{1,2})?)\b", re.IGNORECASE),
    re.compile(r"\b(eCCC\s*\d{1,3}(?:\.\d{1,2})?)\b", re.IGNORECASE),
]

# Parties: after mandant:, client:, Auftraggeber:, committente:, proprietaire:, etc.
PARTY_PATTERNS = [
    re.compile(
        r"(?:mandant|client|ma[iî]tre\s+d[''']ouvrage|propri[eé]taire|"
        r"Auftraggeber|Bauherr|Eigent[uü]mer|"
        r"committente|proprietario|"
        r"owner|client|principal)\s*[:]\s*(.+?)(?:\n|$)",
        re.IGNORECASE,
    ),
]

# Document references: Réf. XXX, dossier n° XXX, Aktenzeichen, riferimento
REFERENCE_PATTERNS = [
    re.compile(
        r"\b(?:R[eé]f(?:[eé]rence)?|dossier|n/r[eé]f|Aktenzeichen|Referenz|riferimento|Ref)\s*[:.n°]*\s*([\w\-/\.]{2,30})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:dossier|Akte)\s*(?:n[°o.]?|Nr\.?|no\.?)\s*([\w\-/\.]{2,30})\b",
        re.IGNORECASE,
    ),
]

# Pollutant results: concentration values with units
POLLUTANT_PATTERNS = [
    # mg/kg, µg/kg, ppm
    re.compile(r"\b(\d[\d\s']*(?:[.,]\d+)?)\s*(mg/kg|µg/kg|ppm|mg/l|µg/l)\b", re.IGNORECASE),
    # Bq/m3 (radon)
    re.compile(r"\b(\d[\d\s']*(?:[.,]\d+)?)\s*(Bq/m[³3])\b"),
    # f/l or f/ml (asbestos fibers)
    re.compile(r"\b(\d[\d\s']*(?:[.,]\d+)?)\s*(f/l|f/ml|fibres?/l)\b", re.IGNORECASE),
    # % (weight percent)
    re.compile(r"\b(\d[\d\s']*(?:[.,]\d+)?)\s*(%\s*(?:poids|masse|Gewicht|peso|weight))\b", re.IGNORECASE),
]

# Energy class: CECB/GEAK/CECE grade A-G
ENERGY_CLASS_PATTERNS = [
    re.compile(r"\b(?:CECB|GEAK|CECE)\s*[:\-]?\s*([A-Ga-g])\b"),
    re.compile(
        r"\b(?:classe\s+[eé]nerg[eé]tique|Energieklasse|classe\s+energetica|energy\s+class)\s*[:\-]?\s*([A-Ga-g])\b",
        re.IGNORECASE,
    ),
]

# Building year: construction year mentions
BUILDING_YEAR_PATTERNS = [
    re.compile(
        r"\b(?:constru(?:it|ction)|erbaut|Baujahr|costruito|costruzione|built|year\s+of\s+construction|ann[eé]e\s+de\s+construction)\s*(?:en|in|im|nel)?\s*[:.\-]?\s*(\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:ann[eé]e|Baujahr|anno|year)\s*[:]\s*(\d{4})\b", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Extraction logic
# ---------------------------------------------------------------------------


def _make_field(field: str, value: str, raw_match: str, position: int, confidence: float) -> dict:
    return {
        "field": field,
        "value": value,
        "raw_match": raw_match,
        "position": position,
        "confidence": confidence,
        "ai_generated": True,
    }


def _extract_dates(text: str) -> list[dict]:
    results: list[dict] = []
    for pat in DATE_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            results.append(_make_field("dates", raw, raw, m.start(), 0.85))
    return results


def _extract_amounts(text: str) -> list[dict]:
    results: list[dict] = []
    for pat in AMOUNT_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            # Normalize: remove spaces, replace ' with nothing for numeric parsing
            normalized = raw.replace("'", "").replace(" ", "")
            results.append(_make_field("amounts", normalized, raw, m.start(), 0.80))
    return results


def _extract_addresses(text: str) -> list[dict]:
    results: list[dict] = []
    for pat in ADDRESS_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            results.append(_make_field("addresses", raw, raw, m.start(), 0.70))
    return results


def _extract_parcels(text: str) -> list[dict]:
    results: list[dict] = []
    for pat in PARCEL_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            value = m.group(1).strip()
            results.append(_make_field("parcels", value, raw, m.start(), 0.85))
    return results


def _extract_cfc_codes(text: str) -> list[dict]:
    results: list[dict] = []
    for pat in CFC_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            results.append(_make_field("cfc_codes", raw, raw, m.start(), 0.90))
    return results


def _extract_parties(text: str) -> list[dict]:
    results: list[dict] = []
    for pat in PARTY_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            value = m.group(1).strip()
            if len(value) >= 2:
                results.append(_make_field("parties", value, raw, m.start(), 0.65))
    return results


def _extract_references(text: str) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    for pat in REFERENCE_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            value = m.group(1).strip()
            if value not in seen and len(value) >= 2:
                seen.add(value)
                results.append(_make_field("references", value, raw, m.start(), 0.75))
    return results


def _extract_pollutant_results(text: str) -> list[dict]:
    results: list[dict] = []
    for pat in POLLUTANT_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            value_num = m.group(1).replace("'", "").replace(" ", "").strip()
            unit = m.group(2).strip()
            results.append(_make_field("pollutant_results", f"{value_num} {unit}", raw, m.start(), 0.80))
    return results


def _extract_energy_class(text: str) -> list[dict]:
    results: list[dict] = []
    for pat in ENERGY_CLASS_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            value = m.group(1).upper()
            results.append(_make_field("energy_class", value, raw, m.start(), 0.90))
    return results


def _extract_building_year(text: str) -> list[dict]:
    results: list[dict] = []
    for pat in BUILDING_YEAR_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            year = int(m.group(1))
            if 1500 <= year <= 2100:
                results.append(_make_field("building_year", str(year), raw, m.start(), 0.85))
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

EXTRACTORS = {
    "dates": _extract_dates,
    "amounts": _extract_amounts,
    "addresses": _extract_addresses,
    "parcels": _extract_parcels,
    "cfc_codes": _extract_cfc_codes,
    "parties": _extract_parties,
    "references": _extract_references,
    "pollutant_results": _extract_pollutant_results,
    "energy_class": _extract_energy_class,
    "building_year": _extract_building_year,
}


def extract_from_text(text: str, document_type: str | None = None) -> dict[str, list[dict]]:
    """Extract structured data from document text using regex patterns.

    Args:
        text: OCR'd or raw document text.
        document_type: Optional document type hint for prioritizing extractors.

    Returns:
        dict grouped by field type, each containing a list of ExtractionField dicts.
    """
    if not text or not text.strip():
        return {ft: [] for ft in FIELD_TYPES}

    result: dict[str, list[dict]] = {}
    for field_type, extractor in EXTRACTORS.items():
        result[field_type] = extractor(text)

    return result


async def extract_and_store(
    db: AsyncSession,
    document_id: UUID,
) -> dict[str, Any]:
    """Extract data from a document's OCR text and store in metadata_json.

    Args:
        db: Database session.
        document_id: UUID of the document.

    Returns:
        Extraction summary with field counts.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    # Get text from processing_metadata.ocr.text or read from file
    text = _get_document_text(doc)
    if not text:
        raise ValueError(f"No text content available for document {document_id}")

    extractions = extract_from_text(text, doc.document_type)

    # Store in metadata_json
    meta = dict(doc.processing_metadata) if doc.processing_metadata else {}
    meta["extractions"] = {
        "fields": extractions,
        "extracted_at": datetime.utcnow().isoformat(),
        "ai_generated": True,
        "total_fields": sum(len(v) for v in extractions.values()),
    }
    doc.processing_metadata = meta

    return {
        "document_id": str(document_id),
        "total_fields": sum(len(v) for v in extractions.values()),
        "field_counts": {k: len(v) for k, v in extractions.items()},
        "extractions": extractions,
    }


def _get_document_text(doc: Document) -> str | None:
    """Try to retrieve text from document metadata."""
    meta = doc.processing_metadata or {}

    # Check OCR output first
    ocr_meta = meta.get("ocr", {})
    if isinstance(ocr_meta, dict):
        text = ocr_meta.get("text")
        if text:
            return text

    # Check extractions cache
    ext_meta = meta.get("extractions", {})
    if isinstance(ext_meta, dict):
        text = ext_meta.get("source_text")
        if text:
            return text

    return None
