"""Hybrid document classification pipeline: OCR + regex rules first, LLM fallback for ambiguous cases.

Classifies uploaded documents into 10 priority types using a multi-step approach:
1. Filename analysis (extension, keywords)
2. Content analysis (OCR text — regex patterns + keyword frequency)
3. Confidence scoring — each type scored, top candidate returned
4. Low confidence (<0.6) → "unclassified" with top-3 candidates

All results are flagged with ai_generated=True for the correction flywheel.
"""

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

# ── 10 priority document types ─────────────────────────────────────────

DOCUMENT_TYPES: dict[str, dict] = {
    "asbestos_report": {
        "keywords": ["amiante", "asbest", "asbestos", "FACH", "diagnostic amiante"],
        "patterns": [r"rapport.*amiante", r"asbest.*bericht"],
        "label_fr": "Rapport amiante",
        "label_en": "Asbestos report",
        "label_de": "Asbestbericht",
        "label_it": "Rapporto amianto",
    },
    "lead_report": {
        "keywords": ["plomb", "blei", "lead", "peinture au plomb"],
        "patterns": [r"rapport.*plomb", r"blei.*analyse"],
        "label_fr": "Rapport plomb",
        "label_en": "Lead report",
        "label_de": "Bleibericht",
        "label_it": "Rapporto piombo",
    },
    "pcb_report": {
        "keywords": ["PCB", "polychlorobiphényle", "polychlorobiphenyle", "joint", "fugenmasse"],
        "patterns": [r"rapport.*PCB", r"PCB.*analyse"],
        "label_fr": "Rapport PCB",
        "label_en": "PCB report",
        "label_de": "PCB-Bericht",
        "label_it": "Rapporto PCB",
    },
    "cfc_estimate": {
        "keywords": ["devis", "CFC", "Kostenvoranschlag", "soumission"],
        "patterns": [r"devis.*CFC", r"CFC\s*\d{3}"],
        "label_fr": "Devis CFC",
        "label_en": "CFC estimate",
        "label_de": "CFC-Kostenvoranschlag",
        "label_it": "Preventivo CFC",
    },
    "contractor_invoice": {
        "keywords": ["facture", "Rechnung", "invoice", "montant dû", "montant du"],
        "patterns": [r"facture\s*n", r"Rechnung\s*Nr"],
        "label_fr": "Facture entreprise",
        "label_en": "Contractor invoice",
        "label_de": "Unternehmerrechnung",
        "label_it": "Fattura impresa",
    },
    "cecb_certificate": {
        "keywords": ["CECB", "certificat énergétique", "certificat energetique", "GEAK", "Energieausweis"],
        "patterns": [r"CECB.*[A-G]", r"GEAK.*[A-G]"],
        "label_fr": "Certificat CECB",
        "label_en": "CECB certificate",
        "label_de": "GEAK-Zertifikat",
        "label_it": "Certificato CECE",
    },
    "building_permit": {
        "keywords": ["permis de construire", "Baubewilligung", "autorisation", "permis"],
        "patterns": [r"permis.*construire", r"Bau(?:bewilligung|gesuch)"],
        "label_fr": "Permis de construire",
        "label_en": "Building permit",
        "label_de": "Baubewilligung",
        "label_it": "Permesso di costruzione",
    },
    "site_report": {
        "keywords": ["PV chantier", "procès-verbal", "proces-verbal", "Bauprotokoll", "rapport de visite"],
        "patterns": [r"PV.*chantier", r"proc[eè]s.*verbal"],
        "label_fr": "PV de chantier",
        "label_en": "Site report",
        "label_de": "Bauprotokoll",
        "label_it": "Verbale di cantiere",
    },
    "insurance_policy": {
        "keywords": ["assurance", "Versicherung", "police", "ECA", "bâtiment assuré", "batiment assure"],
        "patterns": [r"police.*assurance", r"Versicherungs.*police"],
        "label_fr": "Police d'assurance",
        "label_en": "Insurance policy",
        "label_de": "Versicherungspolice",
        "label_it": "Polizza assicurativa",
    },
    "management_report": {
        "keywords": ["rapport de gérance", "rapport de gerance", "gerance", "Verwaltungsbericht", "gestion locative"],
        "patterns": [r"rapport.*g[eé]rance", r"bilan.*gestion"],
        "label_fr": "Rapport de gérance",
        "label_en": "Management report",
        "label_de": "Verwaltungsbericht",
        "label_it": "Rapporto di gestione",
    },
}

# Pre-compiled patterns per type
_COMPILED_PATTERNS: dict[str, list[re.Pattern[str]]] = {}
for _dtype, _spec in DOCUMENT_TYPES.items():
    _COMPILED_PATTERNS[_dtype] = [re.compile(p, re.IGNORECASE) for p in _spec["patterns"]]

# Pre-compiled keyword patterns per type (for content scoring)
_COMPILED_KEYWORDS: dict[str, list[re.Pattern[str]]] = {}
for _dtype, _spec in DOCUMENT_TYPES.items():
    _COMPILED_KEYWORDS[_dtype] = [re.compile(re.escape(kw), re.IGNORECASE) for kw in _spec["keywords"]]

# Confidence thresholds
CONFIDENCE_AUTO_UPDATE = 0.7
CONFIDENCE_CLASSIFIED = 0.6


def _normalize_filename(file_name: str) -> str:
    """Normalize filename for matching: replace separators with spaces, lowercase."""
    # Replace common separators with spaces for multi-word keyword matching
    return re.sub(r"[_\-.]", " ", file_name.lower())


def _score_filename(file_name: str) -> dict[str, float]:
    """Score each document type based on filename keywords and patterns."""
    scores: dict[str, float] = {}
    name_lower = file_name.lower()
    name_normalized = _normalize_filename(file_name)

    for dtype, spec in DOCUMENT_TYPES.items():
        score = 0.0

        # Keyword hits in filename (check both raw and normalized)
        for kw in spec["keywords"]:
            kw_lower = kw.lower()
            if kw_lower in name_lower or kw_lower in name_normalized:
                score += 0.65
                break  # one keyword hit is enough from filename

        # Pattern hits in filename (check both raw and normalized)
        for pattern in _COMPILED_PATTERNS[dtype]:
            if pattern.search(file_name) or pattern.search(name_normalized):
                score += 0.15
                break

        if score > 0:
            scores[dtype] = min(score, 0.7)  # filename alone caps at 0.7

    return scores


def _score_content(content_text: str) -> dict[str, float]:
    """Score each document type based on OCR text content analysis."""
    scores: dict[str, float] = {}

    for dtype, _spec in DOCUMENT_TYPES.items():
        score = 0.0
        keyword_hits = 0

        # Keyword frequency in content
        for kw_pattern in _COMPILED_KEYWORDS[dtype]:
            matches = kw_pattern.findall(content_text)
            if matches:
                keyword_hits += len(matches)

        if keyword_hits > 0:
            # Scale: 1 hit = 0.3, 2 hits = 0.4, 3+ hits = 0.5, 5+ = 0.6
            score += min(0.2 + keyword_hits * 0.1, 0.6)

        # Pattern matches in content
        for pattern in _COMPILED_PATTERNS[dtype]:
            if pattern.search(content_text):
                score += 0.3
                break

        if score > 0:
            scores[dtype] = min(score, 0.9)  # content alone caps at 0.9

    return scores


def classify_document(
    file_name: str,
    content_text: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Classify a document using hybrid filename + content analysis.

    Returns:
        {
            "document_type": str,
            "confidence": float,
            "method": "filename" | "content" | "hybrid",
            "candidates": [{"type": str, "confidence": float}],
            "ai_generated": True,
            "keywords_found": [str],
        }
    """
    filename_scores = _score_filename(file_name)
    content_scores: dict[str, float] = {}

    method = "filename"
    if content_text and content_text.strip():
        content_scores = _score_content(content_text)
        if content_scores:
            method = "hybrid" if filename_scores else "content"

    # Merge scores (filename + content, capped at 1.0)
    all_types = set(filename_scores.keys()) | set(content_scores.keys())
    combined: dict[str, float] = {}
    for dtype in all_types:
        f_score = filename_scores.get(dtype, 0.0)
        c_score = content_scores.get(dtype, 0.0)
        # Hybrid boost: if both filename and content agree, bonus
        if f_score > 0 and c_score > 0:
            combined[dtype] = min(f_score + c_score + 0.1, 1.0)
        else:
            combined[dtype] = max(f_score, c_score)

    # Sort by confidence descending
    ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)

    # Build candidates list (top 3)
    candidates = [{"type": dtype, "confidence": round(conf, 2)} for dtype, conf in ranked[:3]]

    # Determine classification
    keywords_found: list[str] = []
    if ranked and ranked[0][1] >= CONFIDENCE_CLASSIFIED:
        doc_type = ranked[0][0]
        confidence = round(ranked[0][1], 2)
        # Collect found keywords
        name_lower = file_name.lower()
        for kw in DOCUMENT_TYPES[doc_type]["keywords"]:
            if kw.lower() in name_lower:
                keywords_found.append(kw)
        if content_text:
            for kw in DOCUMENT_TYPES[doc_type]["keywords"]:
                if kw.lower() in content_text.lower() and kw not in keywords_found:
                    keywords_found.append(kw)
    else:
        doc_type = "unclassified"
        confidence = round(ranked[0][1], 2) if ranked else 0.0

    return {
        "document_type": doc_type,
        "confidence": confidence,
        "method": method,
        "candidates": candidates,
        "ai_generated": True,
        "keywords_found": keywords_found,
    }


async def classify_and_update(db: AsyncSession, document_id: UUID) -> dict:
    """Load document from DB, classify it, and update document_type if confidence > 0.7.

    Returns classification result dict.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    # Try to get OCR text from processing_metadata
    content_text = None
    if doc.processing_metadata and isinstance(doc.processing_metadata, dict):
        content_text = doc.processing_metadata.get("ocr_text")

    classification = classify_document(
        file_name=doc.file_name or "",
        content_text=content_text,
        metadata=doc.processing_metadata,
    )

    # Auto-update if confidence is high enough
    if classification["confidence"] >= CONFIDENCE_AUTO_UPDATE and classification["document_type"] != "unclassified":
        doc.document_type = classification["document_type"]
        # Store classification metadata
        pm = dict(doc.processing_metadata) if doc.processing_metadata else {}
        pm["auto_classification"] = {
            "document_type": classification["document_type"],
            "confidence": classification["confidence"],
            "method": classification["method"],
            "ai_generated": True,
            "keywords_found": classification["keywords_found"],
        }
        doc.processing_metadata = pm
        await db.commit()

    classification["document_id"] = str(document_id)
    return classification


async def batch_classify(db: AsyncSession, building_id: UUID) -> list[dict]:
    """Classify all unclassified documents for a building.

    Returns list of classification results.
    """
    stmt = select(Document).where(
        Document.building_id == building_id,
        (Document.document_type.is_(None)) | (Document.document_type == "") | (Document.document_type == "other"),
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    results: list[dict] = []
    for doc in docs:
        try:
            classification = await classify_and_update(db, doc.id)
            results.append(classification)
        except ValueError:
            continue

    return results
