"""BatiConnect -- Diagnostic PDF extraction service (rule-based v1).

Extracts structured diagnostic data from OCR'd PDF text using regex patterns
common in Swiss diagnostic lab reports. This is Phase 1 (deterministic rules),
not LLM-based.

Flow: parse -> review -> apply (NEVER auto-persist).
Every extraction gets a confidence score and provenance.
Every correction feeds the ai_feedback flywheel.
"""

from __future__ import annotations

import contextlib
import logging
import re
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_feedback import AIFeedback
from app.models.diagnostic import Diagnostic
from app.models.diagnostic_extraction import DiagnosticExtraction
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.sample import Sample

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLLUTANT_KEYWORDS: dict[str, list[str]] = {
    "asbestos": [
        "amiante",
        "asbestos",
        "chrysotile",
        "amosite",
        "crocidolite",
        "actinolite",
        "tremolite",
        "anthophyllite",
    ],
    "pcb": ["pcb", "polychlorobiphényle", "polychlorobiphenyl", "congénère"],
    "lead": ["plomb", "lead", "pb"],
    "hap": ["hap", "pah", "hydrocarbure aromatique polycyclique", "polycyclic aromatic"],
    "radon": ["radon", "rn-222", "becquerel"],
    "pfas": ["pfas", "pfos", "pfoa", "substance perfluoroalkylée", "perfluoroalkyl"],
}

ASBESTOS_SUBTYPES = [
    "chrysotile",
    "amosite",
    "crocidolite",
    "actinolite",
    "trémolite",
    "tremolite",
    "anthophyllite",
]

# Regex patterns for metadata extraction
DATE_PATTERN = re.compile(
    r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})",
)
CONCENTRATION_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(mg/kg|%|ppm|Bq/m[³3]|mg/l)",
    re.IGNORECASE,
)
SAMPLE_ID_PATTERN = re.compile(
    r"(?:(?:échantillon|sample|prélèvement|éch\.?|E)\s*[:\-]?\s*)([\w\-./]+)",
    re.IGNORECASE,
)

# PCB congeners for individual detection
PCB_CONGENERS = ["PCB 28", "PCB 52", "PCB 101", "PCB 138", "PCB 153", "PCB 180"]

# Regulatory thresholds
THRESHOLDS: dict[str, dict[str, float]] = {
    "pcb": {"mg/kg": 50.0},  # ORRChim Annexe 2.15
    "lead": {"mg/kg": 5000.0},  # ORRChim Annexe 2.18
    "radon": {"Bq/m3": 300.0},  # ORaP Art. 110
}


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """Normalize whitespace and encoding artifacts."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_date(date_str: str) -> date | None:
    """Parse a date string in DD.MM.YYYY or DD/MM/YYYY format."""
    m = DATE_PATTERN.search(date_str)
    if not m:
        return None
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _extract_field(text: str, patterns: list[str]) -> str | None:
    """Extract the first matching field value from text using multiple patterns."""
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# Core extraction functions
# ---------------------------------------------------------------------------


def detect_report_type(text: str) -> str:
    """Detect which pollutant type this report covers.

    Returns one of: asbestos, pcb, lead, hap, radon, pfas, multi, unknown.
    """
    text_lower = text.lower()
    detected = []

    for pollutant, keywords in POLLUTANT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                detected.append(pollutant)
                break

    if len(detected) == 0:
        return "unknown"
    if len(detected) == 1:
        return detected[0]
    return "multi"


def extract_diagnostic_metadata(text: str) -> dict:
    """Extract report metadata: lab name, reference, date, type.

    Uses regex patterns common in Swiss diagnostic reports.
    """
    metadata: dict = {}

    # Lab name
    lab = _extract_field(
        text,
        [
            r"(?:laboratoire|labor|lab\.?)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:mandataire|mandant)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:analysé par|analyzed by)\s*[:\-]?\s*(.+?)(?:\n|$)",
        ],
    )
    metadata["lab_name"] = lab

    # Lab reference / mandate number
    ref = _extract_field(
        text,
        [
            r"(?:référence|reference|réf\.?)\s*[:\-]\s*([\w\-./]+)",
            r"(?:n[°o]?\s*(?:de\s+)?mandat|mandate?\s*(?:no?\.?|number))\s*[:\-]\s*([\w\-./]+)",
            r"(?:rapport\s*n[°o]?\.?|report\s*no?\.?)\s*[:\-]?\s*([\w\-./]+)",
        ],
    )
    metadata["lab_reference"] = ref

    # Report date
    report_date_str = _extract_field(
        text,
        [
            r"(?:date\s+du\s+rapport|report\s+date|date\s*[:\-])\s*[:\-]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:du|dated?)\s+(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
    )
    metadata["report_date"] = _parse_date(report_date_str) if report_date_str else None

    # Sampling date
    sampling_date_str = _extract_field(
        text,
        [
            r"(?:date\s+(?:de\s+)?prélèvement|sampling\s+date)\s*[:\-]\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:date\s+d'analyse|analysis\s+date)\s*[:\-]\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
    )
    metadata["sampling_date"] = _parse_date(sampling_date_str) if sampling_date_str else None

    # Report type
    metadata["report_type"] = detect_report_type(text)

    return metadata


def extract_samples(text: str, report_type: str) -> list[dict]:
    """Extract sample results from the report text.

    Pattern-based extraction for common Swiss lab report formats.
    Returns a list of sample dicts with confidence scores.
    """
    samples: list[dict] = []
    text_normalized = _normalize_text(text)

    # Split text into potential sample blocks
    # Look for sample identifiers and extract surrounding context
    sample_markers = list(SAMPLE_ID_PATTERN.finditer(text_normalized))

    if not sample_markers:
        # Fallback: look for numbered lines with concentration data
        return _extract_samples_tabular(text_normalized, report_type)

    for i, marker in enumerate(sample_markers):
        sample_id = marker.group(1)

        # Get text block for this sample (until next sample or end)
        start = marker.start()
        end = sample_markers[i + 1].start() if i + 1 < len(sample_markers) else len(text_normalized)
        block = text_normalized[start:end]

        sample = _parse_sample_block(block, sample_id, report_type)
        samples.append(sample)

    return samples


def _parse_sample_block(block: str, sample_id: str, report_type: str) -> dict:
    """Parse a single sample block into structured data."""
    sample: dict = {
        "sample_id": sample_id,
        "location": None,
        "material_type": None,
        "result": "not_tested",
        "concentration": None,
        "unit": None,
        "threshold_exceeded": None,
        "confidence": 0.5,  # base confidence for pattern extraction
    }

    # Location extraction
    location = _extract_field(
        block,
        [
            r"(?:localisation|location|lieu|emplacement)\s*[:\-]\s*(.+?)(?:\n|,|;)",
            r"(?:étage|floor|niveau)\s*[:\-]?\s*(.+?)(?:\n|,|;)",
            r"(?:pièce|room|local)\s*[:\-]?\s*(.+?)(?:\n|,|;)",
        ],
    )
    sample["location"] = location

    # Material type
    material = _extract_field(
        block,
        [
            r"(?:matériau|material|type)\s*[:\-]\s*(.+?)(?:\n|,|;)",
            r"(?:description|nature)\s*[:\-]\s*(.+?)(?:\n|,|;)",
        ],
    )
    sample["material_type"] = material

    # Concentration
    conc_match = CONCENTRATION_PATTERN.search(block)
    if conc_match:
        raw_value = conc_match.group(1).replace(",", ".")
        with contextlib.suppress(ValueError):
            sample["concentration"] = float(raw_value)
        sample["unit"] = conc_match.group(2).replace("³", "3")
        sample["confidence"] = 0.7  # higher confidence when concentration found

    # Result determination
    block_lower = block.lower()
    if report_type == "asbestos":
        sample = _classify_asbestos_result(sample, block_lower)
    elif report_type in ("pcb", "lead") or report_type == "radon":
        sample = _classify_concentration_result(sample, report_type)
    else:
        # Generic: presence/absence keywords
        sample = _classify_generic_result(sample, block_lower)

    return sample


def _classify_asbestos_result(sample: dict, block_lower: str) -> dict:
    """Classify asbestos sample result from text."""
    if any(kw in block_lower for kw in ["absence d'amiante", "négatif", "negative", "non détecté", "not detected"]):
        sample["result"] = "negative"
        sample["threshold_exceeded"] = False
        sample["confidence"] = max(sample["confidence"], 0.8)
    elif any(
        kw in block_lower for kw in ["présence d'amiante", "positif", "positive", "détecté", "detected", "contient"]
    ):
        sample["result"] = "positive"
        sample["threshold_exceeded"] = True
        sample["confidence"] = max(sample["confidence"], 0.8)
    elif "trace" in block_lower or "< seuil" in block_lower or "< limite" in block_lower:
        sample["result"] = "trace"
        sample["threshold_exceeded"] = False
        sample["confidence"] = max(sample["confidence"], 0.6)

    # Detect asbestos subtype
    for subtype in ASBESTOS_SUBTYPES:
        if subtype.lower() in block_lower:
            sample["material_type"] = sample.get("material_type") or subtype.capitalize()
            break

    return sample


def _classify_concentration_result(sample: dict, report_type: str) -> dict:
    """Classify result by comparing concentration to regulatory threshold."""
    conc = sample.get("concentration")
    unit = sample.get("unit", "")
    if conc is None:
        return sample

    # Normalize unit for lookup
    unit_key = unit.lower().replace("³", "3").replace(" ", "")
    if unit_key == "ppm":
        unit_key = "mg/kg"  # ppm == mg/kg for solids

    thresholds = THRESHOLDS.get(report_type, {})
    threshold = thresholds.get(unit_key)

    if threshold is not None:
        sample["threshold_exceeded"] = conc > threshold
        sample["result"] = "positive" if conc > threshold else "negative"
        sample["confidence"] = max(sample["confidence"], 0.85)
    else:
        # Concentration found but no matching threshold
        sample["result"] = "positive" if conc > 0 else "negative"
        sample["confidence"] = max(sample["confidence"], 0.5)

    return sample


def _classify_generic_result(sample: dict, block_lower: str) -> dict:
    """Classify sample result using generic presence/absence keywords."""
    positive_keywords = ["positif", "positive", "présence", "presence", "détecté", "detected", "contaminé"]
    negative_keywords = ["négatif", "negative", "absence", "non détecté", "not detected", "conforme"]

    if any(kw in block_lower for kw in positive_keywords):
        sample["result"] = "positive"
        sample["threshold_exceeded"] = True
        sample["confidence"] = max(sample["confidence"], 0.7)
    elif any(kw in block_lower for kw in negative_keywords):
        sample["result"] = "negative"
        sample["threshold_exceeded"] = False
        sample["confidence"] = max(sample["confidence"], 0.7)

    return sample


def _extract_samples_tabular(text: str, report_type: str) -> list[dict]:
    """Fallback: extract samples from tabular data with concentration patterns."""
    samples: list[dict] = []
    # Look for lines with concentration values
    for match in CONCENTRATION_PATTERN.finditer(text):
        raw_value = match.group(1).replace(",", ".")
        try:
            conc = float(raw_value)
        except ValueError:
            continue

        unit = match.group(2).replace("³", "3")

        # Try to get context around the match
        start = max(0, match.start() - 100)
        end = min(len(text), match.end() + 50)
        context = text[start:end]

        sample: dict = {
            "sample_id": f"auto_{len(samples) + 1}",
            "location": None,
            "material_type": None,
            "result": "not_tested",
            "concentration": conc,
            "unit": unit,
            "threshold_exceeded": None,
            "confidence": 0.4,  # lower confidence for tabular fallback
        }

        sample = _classify_concentration_result(sample, report_type)

        # Try to find a sample ID nearby
        id_match = SAMPLE_ID_PATTERN.search(context)
        if id_match:
            sample["sample_id"] = id_match.group(1)
            sample["confidence"] = min(sample["confidence"] + 0.1, 1.0)

        samples.append(sample)

    return samples


def extract_conclusions(text: str) -> dict:
    """Extract overall conclusions and recommendations from the report text."""
    conclusions: dict = {
        "overall_result": "partial",
        "risk_level": "unknown",
        "recommendations": [],
    }

    text_lower = text.lower()

    # Overall result
    if any(
        kw in text_lower
        for kw in [
            "absence totale",
            "aucune présence",
            "tous négatifs",
            "all negative",
            "aucun matériau amianté",
        ]
    ):
        conclusions["overall_result"] = "absence"
    elif any(
        kw in text_lower
        for kw in [
            "présence confirmée",
            "matériaux positifs",
            "contamination avérée",
            "positif",
            "présence d'amiante",
        ]
    ):
        conclusions["overall_result"] = "presence"

    # Risk level
    if any(kw in text_lower for kw in ["risque élevé", "high risk", "urgence", "urgent", "danger immédiat"]):
        conclusions["risk_level"] = "critical"
    elif any(kw in text_lower for kw in ["risque moyen", "medium risk", "modéré", "moderate"]):
        conclusions["risk_level"] = "medium"
    elif any(kw in text_lower for kw in ["risque faible", "low risk", "faible", "minimal"]):
        conclusions["risk_level"] = "low"
    elif conclusions["overall_result"] == "presence":
        conclusions["risk_level"] = "high"
    elif conclusions["overall_result"] == "absence":
        conclusions["risk_level"] = "low"

    # Recommendations
    rec_patterns = [
        r"(?:recommandation|recommendation)\s*[:\-]\s*(.+?)(?:\n|$)",
        r"(?:mesure[s]?\s+(?:à prendre|recommandée[s]?))\s*[:\-]\s*(.+?)(?:\n|$)",
        r"(?:il est recommandé|we recommend|nous recommandons)\s+(.+?)(?:\.\s|\n|$)",
    ]
    for pattern in rec_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            rec = m.group(1).strip()
            if rec and len(rec) > 5:
                conclusions["recommendations"].append(rec)

    return conclusions


def _extract_scope(text: str, samples: list[dict]) -> dict:
    """Extract scope information from the report."""
    scope: dict = {
        "zones_covered": [],
        "zones_excluded": [],
        "elements_sampled": len(samples),
        "elements_positive": sum(1 for s in samples if s.get("result") == "positive"),
    }

    # Zones covered
    zone_patterns = [
        r"(?:zones?\s+(?:inspectée?s?|couvertes?|analysée?s?))\s*[:\-]\s*(.+?)(?:\n|$)",
        r"(?:périmètre|scope|étendue)\s*[:\-]\s*(.+?)(?:\n|$)",
    ]
    for pattern in zone_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            zones = [z.strip() for z in m.group(1).split(",") if z.strip()]
            scope["zones_covered"].extend(zones)

    # Zones excluded
    excl_patterns = [
        r"(?:zones?\s+(?:exclues?|non\s+inspectée?s?|non\s+accessibles?))\s*[:\-]\s*(.+?)(?:\n|$)",
        r"(?:exclusion|hors\s+périmètre)\s*[:\-]\s*(.+?)(?:\n|$)",
    ]
    for pattern in excl_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            zones = [z.strip() for z in m.group(1).split(",") if z.strip()]
            scope["zones_excluded"].extend(zones)

    return scope


def _extract_regulatory_context(text: str, report_type: str) -> dict:
    """Extract regulatory references from the report."""
    context: dict = {
        "regulation_ref": None,
        "threshold_applied": None,
        "work_category": None,
    }

    text_lower = text.lower()

    # Regulation references
    reg_patterns = [
        (r"OTConst\s+(?:Art\.?\s*)?(\d+\w*)", "OTConst Art. "),
        (r"ORRChim\s+(?:Annexe\s+)?(\d+(?:\.\d+)?)", "ORRChim Annexe "),
        (r"OLED\s+(?:Art\.?\s*)?(\d+\w*)", "OLED Art. "),
        (r"ORaP\s+(?:Art\.?\s*)?(\d+\w*)", "ORaP Art. "),
        (r"CFST\s+(\d+)", "CFST "),
    ]
    for pattern, prefix in reg_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            context["regulation_ref"] = prefix + m.group(1)
            break

    # Default regulation refs by pollutant type
    if not context["regulation_ref"]:
        default_refs = {
            "asbestos": "OTConst Art. 60a",
            "pcb": "ORRChim Annexe 2.15",
            "lead": "ORRChim Annexe 2.18",
            "radon": "ORaP Art. 110",
        }
        context["regulation_ref"] = default_refs.get(report_type)

    # Threshold applied
    if report_type in THRESHOLDS:
        for unit, threshold in THRESHOLDS[report_type].items():
            context["threshold_applied"] = f"{threshold} {unit}"
            break

    # Work category (CFST 6503)
    if any(kw in text_lower for kw in ["travaux majeurs", "major works", "catégorie 3"]):
        context["work_category"] = "major"
    elif any(kw in text_lower for kw in ["travaux moyens", "medium works", "catégorie 2"]):
        context["work_category"] = "medium"
    elif any(kw in text_lower for kw in ["travaux mineurs", "minor works", "catégorie 1"]):
        context["work_category"] = "minor"

    return context


def _compute_overall_confidence(metadata: dict, samples: list[dict], conclusions: dict) -> float:
    """Compute overall extraction confidence from component confidences."""
    scores: list[float] = []

    # Metadata completeness
    meta_fields = ["lab_name", "lab_reference", "report_date", "report_type"]
    meta_filled = sum(1 for f in meta_fields if metadata.get(f))
    scores.append(meta_filled / len(meta_fields))

    # Sample confidence average
    if samples:
        sample_confs = [s.get("confidence", 0.0) for s in samples]
        scores.append(sum(sample_confs) / len(sample_confs))
    else:
        scores.append(0.0)

    # Conclusions quality
    conc_score = 0.3
    if conclusions.get("overall_result") != "partial":
        conc_score += 0.3
    if conclusions.get("risk_level") != "unknown":
        conc_score += 0.2
    if conclusions.get("recommendations"):
        conc_score += 0.2
    scores.append(conc_score)

    return round(sum(scores) / len(scores), 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def extract_from_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    building_id: uuid.UUID,
    created_by_id: uuid.UUID,
    text: str,
) -> DiagnosticExtraction:
    """Main entry point. Takes a document + its OCR'd text, extracts diagnostic data.

    Returns a DiagnosticExtraction in 'draft' status (NEVER auto-persisted).
    The caller must commit the session.
    """
    # Verify document exists
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise ValueError("Document not found")

    # Run extraction pipeline
    metadata = extract_diagnostic_metadata(text)
    report_type = metadata["report_type"]
    samples = extract_samples(text, report_type)
    conclusions = extract_conclusions(text)
    scope = _extract_scope(text, samples)
    regulatory = _extract_regulatory_context(text, report_type)
    confidence = _compute_overall_confidence(metadata, samples, conclusions)

    extracted_data = {
        "report_type": report_type,
        "lab_name": metadata.get("lab_name"),
        "lab_reference": metadata.get("lab_reference"),
        "report_date": metadata["report_date"].isoformat() if metadata.get("report_date") else None,
        "validity_date": None,
        "scope": scope,
        "samples": samples,
        "conclusions": conclusions,
        "regulatory_context": regulatory,
    }

    extraction = DiagnosticExtraction(
        document_id=document_id,
        building_id=building_id,
        created_by_id=created_by_id,
        status="draft",
        confidence=confidence,
        extracted_data=extracted_data,
        corrections=[],
    )
    db.add(extraction)
    await db.flush()
    await db.refresh(extraction)

    logger.info(
        "diagnostic_extraction_created",
        extra={
            "extraction_id": str(extraction.id),
            "document_id": str(document_id),
            "report_type": report_type,
            "samples_count": len(samples),
            "confidence": confidence,
        },
    )

    # Auto-create review task for the extraction
    try:
        from app.models.building import Building
        from app.services.review_queue_service import auto_create_from_extraction

        bld_result = await db.execute(select(Building).where(Building.id == building_id))
        bld = bld_result.scalar_one_or_none()
        org_id = bld.organization_id if bld else None
        if org_id:
            await auto_create_from_extraction(
                db,
                extraction_id=extraction.id,
                building_id=building_id,
                organization_id=org_id,
                confidence=confidence,
                report_type=report_type,
            )
    except Exception:
        logger.exception("review_queue: failed to create task for extraction %s", extraction.id)

    return extraction


async def get_extraction(db: AsyncSession, extraction_id: uuid.UUID) -> DiagnosticExtraction | None:
    """Get a diagnostic extraction by ID."""
    result = await db.execute(select(DiagnosticExtraction).where(DiagnosticExtraction.id == extraction_id))
    return result.scalar_one_or_none()


async def review_extraction(
    db: AsyncSession,
    extraction_id: uuid.UUID,
    reviewed_by_id: uuid.UUID,
    updated_data: dict | None = None,
) -> DiagnosticExtraction:
    """Mark an extraction as reviewed, optionally updating extracted data.

    This is the 'review' step in parse -> review -> apply.
    """
    extraction = await get_extraction(db, extraction_id)
    if extraction is None:
        raise ValueError("Extraction not found")
    if extraction.status not in ("draft", "reviewed"):
        raise ValueError(f"Cannot review extraction in status '{extraction.status}'")

    extraction.status = "reviewed"
    extraction.reviewed_by_id = reviewed_by_id

    if updated_data is not None:
        extraction.extracted_data = updated_data

    await db.flush()
    await db.refresh(extraction)
    return extraction


async def apply_extraction(
    db: AsyncSession,
    extraction_id: uuid.UUID,
    applied_by_id: uuid.UUID,
) -> dict:
    """Apply a reviewed extraction to the database.

    Creates: Diagnostic, Samples, EvidenceLinks.
    This is the 'apply' step in parse -> review -> apply (NEVER auto-persist).

    Returns dict with created entity IDs.
    """
    extraction = await get_extraction(db, extraction_id)
    if extraction is None:
        raise ValueError("Extraction not found")
    if extraction.status not in ("reviewed", "draft"):
        raise ValueError(f"Cannot apply extraction in status '{extraction.status}'")

    data = extraction.extracted_data or {}
    report_type = data.get("report_type", "unknown")

    # Map report_type to diagnostic_type
    diag_type = report_type if report_type != "multi" else "full"
    if diag_type == "unknown":
        diag_type = "full"

    # Create Diagnostic
    report_date = None
    if data.get("report_date"):
        with contextlib.suppress(ValueError, TypeError):
            report_date = date.fromisoformat(data["report_date"])

    diagnostic = Diagnostic(
        building_id=extraction.building_id,
        diagnostic_type=diag_type,
        status="draft",
        laboratory=data.get("lab_name"),
        laboratory_report_number=data.get("lab_reference"),
        date_inspection=report_date or date.today(),
        date_report=report_date,
        summary=_build_summary(data),
        conclusion=data.get("conclusions", {}).get("overall_result"),
    )
    db.add(diagnostic)
    await db.flush()
    await db.refresh(diagnostic)

    # Create Samples
    sample_ids = []
    for s in data.get("samples", []):
        sample = Sample(
            diagnostic_id=diagnostic.id,
            sample_number=s.get("sample_id", "unknown"),
            location_detail=s.get("location"),
            material_description=s.get("material_type"),
            pollutant_type=diag_type if diag_type != "full" else None,
            concentration=s.get("concentration"),
            unit=s.get("unit"),
            threshold_exceeded=s.get("threshold_exceeded", False),
            risk_level=_sample_risk_level(s),
        )
        db.add(sample)
        await db.flush()
        await db.refresh(sample)
        sample_ids.append(str(sample.id))

    # Create EvidenceLink: document -> diagnostic
    evidence = EvidenceLink(
        source_type="document",
        source_id=extraction.document_id,
        target_type="diagnostic",
        target_id=diagnostic.id,
        relationship="extracted_from",
        confidence=extraction.confidence,
        explanation=f"Diagnostic extracted from document via rule_based_v1 (confidence: {extraction.confidence})",
        created_by=applied_by_id,
    )
    db.add(evidence)

    # Update extraction status
    extraction.status = "applied"
    extraction.applied_at = datetime.now(UTC)
    extraction.reviewed_by_id = extraction.reviewed_by_id or applied_by_id

    await db.flush()
    await db.refresh(extraction)

    logger.info(
        "diagnostic_extraction_applied",
        extra={
            "extraction_id": str(extraction_id),
            "diagnostic_id": str(diagnostic.id),
            "samples_created": len(sample_ids),
        },
    )

    # Run consequence chain after truth change
    try:
        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        await engine.run_consequences(
            db,
            extraction.building_id,
            "extraction_applied",
            trigger_id=str(extraction.id),
            triggered_by_id=applied_by_id,
        )
    except Exception:
        logger.exception("consequence_engine failed after extraction %s", extraction_id)

    return {
        "diagnostic_id": str(diagnostic.id),
        "sample_ids": sample_ids,
        "evidence_link_id": str(evidence.id),
    }


async def reject_extraction(
    db: AsyncSession,
    extraction_id: uuid.UUID,
    rejected_by_id: uuid.UUID,
    reason: str | None = None,
) -> DiagnosticExtraction:
    """Reject an extraction. Records feedback for the flywheel."""
    extraction = await get_extraction(db, extraction_id)
    if extraction is None:
        raise ValueError("Extraction not found")
    if extraction.status == "applied":
        raise ValueError("Cannot reject an already-applied extraction")

    extraction.status = "rejected"
    extraction.reviewed_by_id = rejected_by_id

    # Feed the ai_feedback flywheel
    feedback = AIFeedback(
        feedback_type="reject",
        entity_type="diagnostic_extraction",
        entity_id=extraction.id,
        original_output=extraction.extracted_data,
        confidence=extraction.confidence,
        user_id=rejected_by_id,
        notes=reason,
    )
    db.add(feedback)

    await db.flush()
    await db.refresh(extraction)
    return extraction


async def record_correction(
    db: AsyncSession,
    extraction_id: uuid.UUID,
    field_path: str,
    old_value: str | float | bool | None,
    new_value: str | float | bool | None,
    corrected_by_id: uuid.UUID,
) -> DiagnosticExtraction:
    """Record a human correction to an extraction field.

    Feeds the ai_feedback loop for future improvement.
    """
    extraction = await get_extraction(db, extraction_id)
    if extraction is None:
        raise ValueError("Extraction not found")
    if extraction.status == "applied":
        raise ValueError("Cannot correct an already-applied extraction")

    # Add correction to the list
    corrections = list(extraction.corrections or [])
    corrections.append(
        {
            "field_path": field_path,
            "old_value": old_value,
            "new_value": new_value,
            "corrected_by_id": str(corrected_by_id),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
    extraction.corrections = corrections

    # Apply correction to extracted_data
    _apply_field_correction(extraction, field_path, new_value)

    # Feed the ai_feedback flywheel
    feedback = AIFeedback(
        feedback_type="correct",
        entity_type="diagnostic_extraction",
        entity_id=extraction.id,
        original_output={"field_path": field_path, "old_value": old_value},
        corrected_output={"field_path": field_path, "new_value": new_value},
        confidence=extraction.confidence,
        user_id=corrected_by_id,
        notes=f"Field correction: {field_path}",
    )
    db.add(feedback)

    await db.flush()
    await db.refresh(extraction)
    return extraction


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_field_correction(
    extraction: DiagnosticExtraction,
    field_path: str,
    new_value: str | float | bool | None,
) -> None:
    """Apply a dot-path correction to extracted_data (e.g., 'conclusions.risk_level')."""
    data = dict(extraction.extracted_data or {})
    parts = field_path.split(".")

    target = data
    for part in parts[:-1]:
        if isinstance(target, dict) and part in target:
            target = target[part]
        else:
            return  # path not found, skip

    if isinstance(target, dict):
        target[parts[-1]] = new_value

    extraction.extracted_data = data


def _build_summary(data: dict) -> str:
    """Build a diagnostic summary from extracted data."""
    parts = []

    report_type = data.get("report_type", "unknown")
    parts.append(f"Type: {report_type}")

    scope = data.get("scope", {})
    sampled = scope.get("elements_sampled", 0)
    positive = scope.get("elements_positive", 0)
    if sampled > 0:
        parts.append(f"Samples: {positive}/{sampled} positive")

    conclusions = data.get("conclusions", {})
    result = conclusions.get("overall_result", "partial")
    parts.append(f"Result: {result}")

    risk = conclusions.get("risk_level", "unknown")
    parts.append(f"Risk: {risk}")

    return " | ".join(parts)


def _sample_risk_level(sample: dict) -> str:
    """Derive risk level from sample result."""
    result = sample.get("result", "not_tested")
    if result == "positive":
        return "high"
    if result == "trace":
        return "medium"
    if result == "negative":
        return "low"
    return "unknown"


# ---------------------------------------------------------------------------
# Convenience class wrapper (allows `from ... import DiagnosticExtractionService`)
# ---------------------------------------------------------------------------


class DiagnosticExtractionService:
    """Namespace wrapper around module-level extraction functions."""

    extract_from_document = staticmethod(extract_from_document)
    get_extraction = staticmethod(get_extraction)
    review_extraction = staticmethod(review_extraction)
    apply_extraction = staticmethod(apply_extraction)
    reject_extraction = staticmethod(reject_extraction)
    record_correction = staticmethod(record_correction)
    detect_report_type = staticmethod(detect_report_type)
    extract_diagnostic_metadata = staticmethod(extract_diagnostic_metadata)
    extract_samples = staticmethod(extract_samples)
    extract_conclusions = staticmethod(extract_conclusions)
