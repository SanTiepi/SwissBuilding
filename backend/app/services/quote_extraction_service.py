"""BatiConnect -- Quote/devis PDF extraction service (rule-based v1).

Extracts structured data from OCR'd quote/devis PDFs using regex patterns
common in Swiss construction quotes (FR + DE). This is Phase 1 (deterministic
rules), not LLM-based.

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
from app.models.document import Document
from app.models.rfq import TenderQuote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Quote type keywords (FR + DE)
QUOTE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "asbestos_removal": [
        "désamiantage",
        "amiante",
        "asbestos",
        "asbest",
        "asbestentsorgung",
        "assainissement amiante",
    ],
    "pcb_removal": ["pcb", "polychlorobiphényle", "pcb-sanierung"],
    "lead_removal": ["plomb", "déplombage", "lead", "blei", "bleisanierung"],
    "hap_removal": ["hap", "hydrocarbure aromatique", "pah", "pak"],
    "radon_mitigation": ["radon", "assainissement radon", "radonsanierung"],
    "pfas_remediation": ["pfas", "pfos", "pfoa", "perfluor"],
    "general_renovation": [
        "rénovation",
        "transformation",
        "renovation",
        "umbau",
        "sanierung",
    ],
    "demolition": ["démolition", "abbruch", "rückbau", "déconstruction"],
}

# Units commonly found in Swiss construction quotes
KNOWN_UNITS = [
    "m2",
    "m²",
    "m3",
    "m³",
    "ml",
    "m",
    "pce",
    "pcs",
    "st",
    "stk",
    "h",
    "heure",
    "heures",
    "stunde",
    "stunden",
    "forfait",
    "fft",
    "global",
    "gl",
    "pauschal",
    "kg",
    "t",
    "tonne",
    "jour",
    "jours",
    "tag",
    "tage",
]

# Regex patterns
DATE_PATTERN = re.compile(r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})")

AMOUNT_PATTERN = re.compile(
    r"(?:CHF|Fr\.?|SFr\.?)\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)"
    r"|(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)\s*(?:CHF|Fr\.?|SFr\.?)",
    re.IGNORECASE,
)

VAT_RATE_PATTERN = re.compile(
    r"(?:TVA|MwSt|MWST|taxe\s*sur\s*la\s*valeur\s*ajoutée)"
    r"\s*[:\-]?\s*(\d+[.,]\d+)\s*%",
    re.IGNORECASE,
)

POSITION_PATTERN = re.compile(
    r"^(?:(?:Pos\.?\s*)?(\d{1,3}(?:\.\d{1,3})*))\s+(.+?)$",
    re.MULTILINE,
)

QUANTITY_PRICE_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s+"
    r"(" + "|".join(re.escape(u) for u in KNOWN_UNITS) + r")\s+"
    r"(\d+(?:[.,]\d+)?)\s+"
    r"(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Text helpers
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


def _parse_amount(amount_str: str) -> float | None:
    """Parse a Swiss-formatted amount (e.g., 12'345.50 or 12 345,50)."""
    # Remove thousands separators (apostrophe, space)
    cleaned = re.sub(r"['\s]", "", amount_str)
    # Normalize comma to dot for decimal
    cleaned = cleaned.replace(",", ".")
    # If there are multiple dots, keep only the last one as decimal
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(cleaned)
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


def detect_quote_type(text: str) -> str:
    """Detect quote category from text content.

    Returns one of: asbestos_removal, pcb_removal, lead_removal, hap_removal,
    radon_mitigation, pfas_remediation, general_renovation, demolition, unknown.
    """
    text_lower = text.lower()
    detected: list[tuple[str, int]] = []

    for quote_type, keywords in QUOTE_TYPE_KEYWORDS.items():
        count = 0
        for kw in keywords:
            count += text_lower.count(kw.lower())
        if count > 0:
            detected.append((quote_type, count))

    if not detected:
        return "unknown"

    # Return the type with the most keyword hits
    detected.sort(key=lambda x: x[1], reverse=True)
    return detected[0][0]


def extract_contractor_info(text: str) -> dict:
    """Extract contractor name, address, contact from header area.

    Swiss quotes typically have the company info in the first ~500 chars.
    """
    header = text[:800] if len(text) > 800 else text
    info: dict = {
        "name": None,
        "address": None,
        "contact": None,
        "confidence": 0.3,
    }

    # Company name patterns (FR + DE)
    name = _extract_field(
        header,
        [
            r"(?:entreprise|firma|société|unternehmen)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"^([A-Z][A-Za-zÀ-ÿ\s&\-]+(?:SA|Sàrl|SARL|AG|GmbH|S\.A\.))",
            r"^([A-Z][A-Za-zÀ-ÿ\s&\-]{5,50})\s*\n",
        ],
    )
    if name:
        info["name"] = name
        info["confidence"] = 0.5

    # Address patterns (Swiss: street + number, NPA + city)
    address = _extract_field(
        header,
        [
            r"(?:adresse|address|anschrift)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(\d{4}\s+[A-Za-zÀ-ÿ\-\s]+)",  # NPA + city
            r"((?:rue|avenue|chemin|route|strasse|weg|gasse)\s+.+?\d+)",
        ],
    )
    if address:
        info["address"] = address
        info["confidence"] = min(info["confidence"] + 0.15, 1.0)

    # Contact (phone / email)
    contact_parts = []
    phone = _extract_field(
        header,
        [
            r"(?:tél|tel|téléphone|phone|telefon)\s*[:\-.]?\s*([\d\s+\-().]{8,20})",
            r"(\+41\s*[\d\s\-().]{8,15})",
            r"(0\d{1,2}\s*[\d\s\-().]{6,12})",
        ],
    )
    if phone:
        contact_parts.append(f"Tel: {phone}")

    email = _extract_field(
        header,
        [r"([\w.\-]+@[\w.\-]+\.\w{2,})"],
    )
    if email:
        contact_parts.append(f"Email: {email}")

    if contact_parts:
        info["contact"] = " | ".join(contact_parts)
        info["confidence"] = min(info["confidence"] + 0.1, 1.0)

    return info


def extract_positions(text: str) -> list[dict]:
    """Extract line items/positions from the quote.

    Look for patterns: position number, description, quantity, unit, price, total.
    Swiss quotes use numbered positions like 1., 1.1, 2.3, Pos. 1, etc.
    """
    positions: list[dict] = []
    lines = text.split("\n")

    current_position: dict | None = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check if line starts with a position number
        pos_match = re.match(
            r"^(?:Pos\.?\s*)?(\d{1,3}(?:\.\d{1,3})*)\s+(.+)",
            line_stripped,
        )
        if pos_match:
            # Save previous position
            if current_position:
                positions.append(current_position)

            pos_num = pos_match.group(1)
            rest = pos_match.group(2)

            current_position = {
                "position": pos_num,
                "description": rest,
                "quantity": None,
                "unit": None,
                "unit_price": None,
                "total": None,
                "category": None,
                "confidence": 0.4,
            }

            # Try to extract quantity/unit/price from the same line
            qp_match = QUANTITY_PRICE_PATTERN.search(rest)
            if qp_match:
                qty_str = qp_match.group(1).replace(",", ".")
                unit = qp_match.group(2)
                up_str = qp_match.group(3).replace(",", ".")
                total_str = qp_match.group(4).replace(",", ".")
                with contextlib.suppress(ValueError):
                    current_position["quantity"] = float(qty_str)
                    current_position["unit"] = unit
                    current_position["unit_price"] = float(up_str)
                    current_position["total"] = float(total_str)
                    current_position["confidence"] = 0.7
                # Clean description: remove the numeric part
                current_position["description"] = rest[: qp_match.start()].strip()

            continue

        # If we have a current position and this line has quantity data, update it
        if current_position and current_position["quantity"] is None:
            qp_match = QUANTITY_PRICE_PATTERN.search(line_stripped)
            if qp_match:
                qty_str = qp_match.group(1).replace(",", ".")
                unit = qp_match.group(2)
                up_str = qp_match.group(3).replace(",", ".")
                total_str = qp_match.group(4).replace(",", ".")
                with contextlib.suppress(ValueError):
                    current_position["quantity"] = float(qty_str)
                    current_position["unit"] = unit
                    current_position["unit_price"] = float(up_str)
                    current_position["total"] = float(total_str)
                    current_position["confidence"] = 0.7

    # Don't forget the last position
    if current_position:
        positions.append(current_position)

    # Try to detect work category for each position
    for pos in positions:
        pos["category"] = _detect_work_category(pos.get("description", ""))

    return positions


def _detect_work_category(description: str) -> str | None:
    """Detect CFST work category from position description."""
    desc_lower = description.lower()

    category_keywords: dict[str, list[str]] = {
        "asbestos_removal": ["amiante", "désamiantage", "asbest"],
        "demolition": ["démolition", "abbruch", "rückbau"],
        "waste_disposal": ["évacuation", "déchets", "entsorgung", "abfall"],
        "containment": ["confinement", "encapsulage", "abdichtung"],
        "protection": ["protection", "sécurité", "sicherheit", "epi"],
        "installation": ["installation", "montage", "einbau"],
        "transport": ["transport", "manutention"],
        "analysis": ["analyse", "prélèvement", "labor", "messung"],
        "supervision": ["surveillance", "direction", "bauleitung"],
    }

    for category, keywords in category_keywords.items():
        if any(kw in desc_lower for kw in keywords):
            return category

    return None


def extract_totals(text: str) -> dict:
    """Extract total amounts, VAT, discounts from the quote text."""
    totals: dict = {
        "total_amount_chf": None,
        "total_with_vat": None,
        "vat_rate": None,
        "subtotal": None,
        "discount": None,
        "currency": "CHF",
        "confidence": 0.3,
    }

    # VAT rate
    vat_match = VAT_RATE_PATTERN.search(text)
    if vat_match:
        rate_str = vat_match.group(1).replace(",", ".")
        with contextlib.suppress(ValueError):
            totals["vat_rate"] = float(rate_str)
            totals["confidence"] = min(totals["confidence"] + 0.15, 1.0)

    # Total HT / Subtotal (before VAT)
    subtotal_str = _extract_field(
        text,
        [
            r"(?:sous[\-\s]?total|subtotal|total\s+HT|total\s+hors\s+taxe|zwischensumme|nettobetrag)"
            r"\s*[:\-]?\s*(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)",
            r"(?:CHF|Fr\.?|SFr\.?)\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)"
            r"\s*(?:sous[\-\s]?total|subtotal|HT|hors\s+taxe)",
        ],
    )
    if subtotal_str:
        subtotal = _parse_amount(subtotal_str)
        if subtotal:
            totals["subtotal"] = subtotal
            totals["total_amount_chf"] = subtotal
            totals["confidence"] = min(totals["confidence"] + 0.2, 1.0)

    # Total TTC (with VAT)
    ttc_str = _extract_field(
        text,
        [
            r"(?:total\s+TTC|total\s+toutes\s+taxes|montant\s+total|gesamtbetrag|totalbetrag|bruttobetrag)"
            r"\s*[:\-]?\s*(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)",
            r"(?:CHF|Fr\.?|SFr\.?)\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)"
            r"\s*(?:TTC|toutes\s+taxes|total)",
        ],
    )
    if ttc_str:
        ttc = _parse_amount(ttc_str)
        if ttc:
            totals["total_with_vat"] = ttc
            totals["confidence"] = min(totals["confidence"] + 0.2, 1.0)

    # Discount / Rabais
    discount_str = _extract_field(
        text,
        [
            r"(?:rabais|escompte|remise|skonto|rabatt|nachlass)"
            r"\s*[:\-]?\s*(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)",
        ],
    )
    if discount_str:
        discount = _parse_amount(discount_str)
        if discount:
            totals["discount"] = discount

    # Fallback: find the largest amount in the document as potential total
    if totals["total_amount_chf"] is None and totals["total_with_vat"] is None:
        all_amounts: list[float] = []
        for m in AMOUNT_PATTERN.finditer(text):
            raw = m.group(1) or m.group(2)
            if raw:
                parsed = _parse_amount(raw)
                if parsed and parsed > 100:  # ignore very small amounts
                    all_amounts.append(parsed)
        if all_amounts:
            largest = max(all_amounts)
            totals["total_amount_chf"] = largest
            totals["confidence"] = 0.3  # low confidence for fallback

    # If we have subtotal + VAT rate but no TTC, compute it
    if totals["total_amount_chf"] and totals["vat_rate"] and not totals["total_with_vat"]:
        totals["total_with_vat"] = round(totals["total_amount_chf"] * (1 + totals["vat_rate"] / 100), 2)

    # If we have TTC but no HT, and we have VAT, compute HT
    if totals["total_with_vat"] and totals["vat_rate"] and not totals["total_amount_chf"]:
        totals["total_amount_chf"] = round(totals["total_with_vat"] / (1 + totals["vat_rate"] / 100), 2)

    return totals


def extract_scope(text: str) -> dict:
    """Extract scope, zones, work types, and duration from the quote."""
    scope: dict = {
        "description": None,
        "zones_mentioned": [],
        "work_types": [],
        "duration_days": None,
        "confidence": 0.3,
    }

    # Scope / object description
    scope_desc = _extract_field(
        text,
        [
            r"(?:objet|concerne|beschreibung|gegenstand|objekt)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:travaux de|arbeiten für|travaux)\s*[:\-]?\s*(.+?)(?:\n|$)",
        ],
    )
    if scope_desc:
        scope["description"] = scope_desc
        scope["confidence"] = min(scope["confidence"] + 0.2, 1.0)

    # Zones / locations mentioned
    zone_patterns = [
        r"(?:zone|local|pièce|étage|raum|stockwerk|geschoss|zimmer)\s*[:\-]?\s*(.+?)(?:\n|,|;)",
        r"(?:sous[\-\s]?sol|cave|grenier|toiture|facade|dach|keller|fassade)",
    ]
    for pattern in zone_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            zone = m.group(0).strip() if m.lastindex == 0 else m.group(1).strip()
            if zone and zone not in scope["zones_mentioned"]:
                scope["zones_mentioned"].append(zone)

    if scope["zones_mentioned"]:
        scope["confidence"] = min(scope["confidence"] + 0.1, 1.0)

    # Work types detected
    text_lower = text.lower()
    for work_type, keywords in QUOTE_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                if work_type not in scope["work_types"]:
                    scope["work_types"].append(work_type)
                break

    # Duration
    duration_str = _extract_field(
        text,
        [
            r"(?:durée\s+des\s+travaux|délai\s+d'exécution|dauer|ausführungsfrist)"
            r"\s*[:\-]?\s*(\d+)\s*(?:jours?|tage?|arbeitstage?)",
            r"(?:durée|dauer)\s*[:\-]?\s*(\d+)\s*(?:semaines?|wochen)",
        ],
    )
    if duration_str:
        with contextlib.suppress(ValueError):
            days = int(duration_str)
            # If the pattern matched weeks, multiply
            if re.search(r"semaines?|wochen", text, re.IGNORECASE):
                days *= 5  # working days
            scope["duration_days"] = days
            scope["confidence"] = min(scope["confidence"] + 0.15, 1.0)

    return scope


def extract_exclusions_inclusions(text: str) -> tuple[list[str], list[str]]:
    """Extract exclusions and inclusions lists from the quote text."""
    exclusions: list[str] = []
    inclusions: list[str] = []

    # Inclusions
    incl_patterns = [
        r"(?:sont\s+compris|comprend|compris\s+dans\s+l'offre|inbegriffen|inklusive|"
        r"im\s+preis\s+inbegriffen)\s*[:\-]\s*(.+?)(?:\n\n|\nSont\s+exclus|\nExclusion|\nNe\s+comprend|$)",
    ]
    for pattern in incl_patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            block = m.group(1)
            items = re.split(r"[\n;\-]", block)
            for item in items:
                item = item.strip().rstrip(",;.")
                if item and len(item) > 3:
                    inclusions.append(item)

    # Exclusions
    excl_patterns = [
        r"(?:sont\s+exclus|ne\s+comprend\s+pas|exclusions?|non\s+compris|nicht\s+inbegriffen|"
        r"ausgeschlossen|exklusive)\s*[:\-]\s*(.+?)(?:\n\n|\nCondition|\nRemarque|\nValidité|$)",
    ]
    for pattern in excl_patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            block = m.group(1)
            items = re.split(r"[\n;\-]", block)
            for item in items:
                item = item.strip().rstrip(",;.")
                if item and len(item) > 3:
                    exclusions.append(item)

    return exclusions, inclusions


def extract_conditions(text: str) -> dict:
    """Extract payment terms, guarantees, start conditions."""
    conditions: dict = {
        "payment_terms": None,
        "guarantee_months": None,
        "start_conditions": None,
        "confidence": 0.3,
    }

    # Payment terms
    payment = _extract_field(
        text,
        [
            r"(?:conditions?\s+de\s+paiement|délai\s+de\s+paiement|zahlungsbedingungen|"
            r"zahlungsfrist)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:paiement|zahlung)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(\d+\s*jours?\s*(?:net|après\s+(?:réception|facturation)))",
        ],
    )
    if payment:
        conditions["payment_terms"] = payment
        conditions["confidence"] = min(conditions["confidence"] + 0.2, 1.0)

    # Guarantee
    guarantee_str = _extract_field(
        text,
        [
            r"(?:garantie|gewährleistung|garantiefrist)\s*[:\-]?\s*(\d+)\s*(?:mois|monate|months)",
            r"(?:garantie|gewährleistung)\s*[:\-]?\s*(\d+)\s*(?:ans?|jahre?|years?)",
        ],
    )
    if guarantee_str:
        with contextlib.suppress(ValueError):
            months = int(guarantee_str)
            # Check if it was years
            if re.search(r"ans?|jahre?|years?", text, re.IGNORECASE):
                months *= 12
            conditions["guarantee_months"] = months
            conditions["confidence"] = min(conditions["confidence"] + 0.15, 1.0)

    # Start conditions
    start = _extract_field(
        text,
        [
            r"(?:début\s+des\s+travaux|commencement|start|beginn)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:condition\s+de\s+démarrage|startbedingung)\s*[:\-]\s*(.+?)(?:\n|$)",
        ],
    )
    if start:
        conditions["start_conditions"] = start
        conditions["confidence"] = min(conditions["confidence"] + 0.1, 1.0)

    return conditions


def extract_regulatory_mentions(text: str) -> dict:
    """Extract mentions of regulatory / safety requirements."""
    regulatory: dict = {
        "suva_mentioned": False,
        "waste_plan_mentioned": False,
        "safety_measures_mentioned": False,
        "confidence": 0.5,
    }

    text_lower = text.lower()

    # SUVA
    if any(kw in text_lower for kw in ["suva", "caisse nationale", "schweizerische unfallversicherung"]):
        regulatory["suva_mentioned"] = True
        regulatory["confidence"] = min(regulatory["confidence"] + 0.15, 1.0)

    # Waste plan
    if any(
        kw in text_lower
        for kw in [
            "plan de gestion des déchets",
            "plan d'élimination",
            "entsorgungsplan",
            "abfallkonzept",
            "oled",
            "déchets spéciaux",
            "sonderabfall",
        ]
    ):
        regulatory["waste_plan_mentioned"] = True
        regulatory["confidence"] = min(regulatory["confidence"] + 0.15, 1.0)

    # Safety measures
    if any(
        kw in text_lower
        for kw in [
            "epi",
            "equipement de protection",
            "mesures de sécurité",
            "sicherheitsmassnahmen",
            "zone confinée",
            "confinement",
            "protection respiratoire",
            "atemschutz",
            "cfst",
            "directive 6503",
        ]
    ):
        regulatory["safety_measures_mentioned"] = True
        regulatory["confidence"] = min(regulatory["confidence"] + 0.15, 1.0)

    return regulatory


def extract_dates(text: str) -> dict:
    """Extract quote date, validity date, reference from the document."""
    dates: dict = {
        "quote_reference": None,
        "quote_date": None,
        "validity_date": None,
        "confidence": 0.3,
    }

    # Quote reference
    ref = _extract_field(
        text,
        [
            r"(?:réf\.?|référence|reference|n[°o]?\s*(?:d'offre|offre)|angebots?\s*(?:nr|nummer))"
            r"\s*[:\-]?\s*([\w\-./]+)",
            r"(?:devis|offre|soumission|angebot|kostenvoranschlag)\s+n[°o]?\s*[:\-]?\s*([\w\-./]+)",
        ],
    )
    if ref:
        dates["quote_reference"] = ref
        dates["confidence"] = min(dates["confidence"] + 0.15, 1.0)

    # Quote date
    date_str = _extract_field(
        text,
        [
            r"(?:date\s+du\s+devis|date\s+de\s+l'offre|datum|angebotsdatum)\s*[:\-]\s*"
            r"(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:du|le|vom)\s+(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:date)\s*[:\-]\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
    )
    if date_str:
        parsed = _parse_date(date_str)
        if parsed:
            dates["quote_date"] = parsed
            dates["confidence"] = min(dates["confidence"] + 0.2, 1.0)

    # Validity date
    validity_str = _extract_field(
        text,
        [
            r"(?:validité|valable\s+jusqu'au|gültig\s+bis|gültigkeit)"
            r"\s*[:\-]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:offre\s+valable|angebot\s+gültig)\s+(?:jusqu'au|bis)\s+(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
    )
    if validity_str:
        parsed = _parse_date(validity_str)
        if parsed:
            dates["validity_date"] = parsed
            dates["confidence"] = min(dates["confidence"] + 0.15, 1.0)

    # Validity in days/months from date
    if not dates["validity_date"] and dates["quote_date"]:
        validity_days_str = _extract_field(
            text,
            [
                r"(?:validité|gültigkeit)\s*[:\-]?\s*(\d+)\s*(?:jours?|tage?)",
                r"(?:valable|gültig)\s+(\d+)\s*(?:jours?|tage?|mois|monate)",
            ],
        )
        if validity_days_str:
            with contextlib.suppress(ValueError):
                val_days = int(validity_days_str)
                if re.search(r"mois|monate", text, re.IGNORECASE):
                    val_days *= 30
                from datetime import timedelta

                dates["validity_date"] = dates["quote_date"] + timedelta(days=val_days)

    return dates


def _compute_overall_confidence(
    contractor: dict,
    dates_info: dict,
    totals: dict,
    positions: list[dict],
    scope: dict,
    conditions: dict,
    regulatory: dict,
) -> float:
    """Compute overall extraction confidence from component scores."""
    scores: list[float] = []

    scores.append(contractor.get("confidence", 0.3))
    scores.append(dates_info.get("confidence", 0.3))
    scores.append(totals.get("confidence", 0.3))
    scores.append(scope.get("confidence", 0.3))
    scores.append(conditions.get("confidence", 0.3))
    scores.append(regulatory.get("confidence", 0.5))

    # Positions quality
    if positions:
        pos_confs = [p.get("confidence", 0.4) for p in positions]
        scores.append(sum(pos_confs) / len(pos_confs))
    else:
        scores.append(0.0)

    return round(sum(scores) / len(scores), 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def extract_from_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    text: str,
    tender_id: uuid.UUID | None = None,
) -> dict:
    """Main entry point. Takes a document + its OCR'd text, extracts quote data.

    Returns a dict with extraction_id, status 'draft', confidence, extracted data,
    and provenance. NEVER auto-persisted to TenderQuote.
    """
    # Verify document exists
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise ValueError("Document not found")

    # Run extraction pipeline
    quote_type = detect_quote_type(text)
    contractor = extract_contractor_info(text)
    dates_info = extract_dates(text)
    totals = extract_totals(text)
    positions = extract_positions(text)
    scope = extract_scope(text)
    exclusions, inclusions = extract_exclusions_inclusions(text)
    conditions_data = extract_conditions(text)
    regulatory = extract_regulatory_mentions(text)
    confidence = _compute_overall_confidence(
        contractor,
        dates_info,
        totals,
        positions,
        scope,
        conditions_data,
        regulatory,
    )

    extraction_id = uuid.uuid4()

    # Strip internal confidence fields from sub-dicts
    contractor_clean = {k: v for k, v in contractor.items() if k != "confidence"}
    scope_clean = {k: v for k, v in scope.items() if k != "confidence"}
    conditions_clean = {k: v for k, v in conditions_data.items() if k != "confidence"}
    regulatory_clean = {k: v for k, v in regulatory.items() if k != "confidence"}

    result = {
        "extraction_id": str(extraction_id),
        "status": "draft",
        "confidence": confidence,
        "extracted": {
            "contractor": contractor_clean,
            "quote_type": quote_type,
            "quote_reference": dates_info.get("quote_reference"),
            "quote_date": dates_info["quote_date"].isoformat() if dates_info.get("quote_date") else None,
            "validity_date": dates_info["validity_date"].isoformat() if dates_info.get("validity_date") else None,
            "total_amount_chf": totals.get("total_amount_chf"),
            "total_with_vat": totals.get("total_with_vat"),
            "vat_rate": totals.get("vat_rate"),
            "discount": totals.get("discount"),
            "currency": totals.get("currency", "CHF"),
            "positions": [{k: v for k, v in p.items() if k != "confidence"} for p in positions],
            "scope": scope_clean,
            "exclusions": exclusions,
            "inclusions": inclusions,
            "conditions": conditions_clean,
            "regulatory": regulatory_clean,
        },
        "provenance": {
            "source_document_id": str(document_id),
            "tender_id": str(tender_id) if tender_id else None,
            "extraction_method": "rule_based_v1",
            "extraction_date": datetime.now(UTC).isoformat(),
            "requires_human_review": True,
        },
        "corrections": [],
    }

    logger.info(
        "quote_extraction_created",
        extra={
            "extraction_id": str(extraction_id),
            "document_id": str(document_id),
            "quote_type": quote_type,
            "positions_count": len(positions),
            "confidence": confidence,
            "total_amount_chf": totals.get("total_amount_chf"),
        },
    )

    return result


async def apply_to_tender_quote(
    db: AsyncSession,
    extraction_data: dict,
    tender_quote_id: uuid.UUID,
) -> TenderQuote:
    """Apply reviewed extraction data to a TenderQuote's extracted_data field.

    This is the review -> apply step. NEVER auto-called.
    Updates TenderQuote fields from the extraction.
    """
    result = await db.execute(select(TenderQuote).where(TenderQuote.id == tender_quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise ValueError("TenderQuote not found")

    extracted = extraction_data.get("extracted", {})

    # Update TenderQuote fields from extraction
    if extracted.get("total_amount_chf") is not None:
        quote.total_amount_chf = extracted["total_amount_chf"]
    if extracted.get("currency"):
        quote.currency = extracted["currency"]
    if extracted.get("scope", {}).get("description"):
        quote.scope_description = extracted["scope"]["description"]
    if extracted.get("exclusions"):
        quote.exclusions = "; ".join(extracted["exclusions"])
    if extracted.get("inclusions"):
        quote.inclusions = "; ".join(extracted["inclusions"])
    if extracted.get("scope", {}).get("duration_days") is not None:
        quote.estimated_duration_days = extracted["scope"]["duration_days"]
    if extracted.get("validity_date"):
        with contextlib.suppress(ValueError, TypeError):
            quote.validity_date = date.fromisoformat(extracted["validity_date"])

    # Store the full extraction in extracted_data
    quote.extracted_data = {
        "status": "applied",
        "applied_at": datetime.now(UTC).isoformat(),
        "extraction": extraction_data,
    }

    await db.flush()
    await db.refresh(quote)

    logger.info(
        "quote_extraction_applied",
        extra={
            "tender_quote_id": str(tender_quote_id),
            "extraction_id": extraction_data.get("extraction_id"),
            "total_amount_chf": extracted.get("total_amount_chf"),
        },
    )

    return quote


async def record_correction(
    db: AsyncSession,
    extraction_data: dict,
    field_path: str,
    old_value: str | float | bool | None,
    new_value: str | float | bool | None,
    corrected_by_id: uuid.UUID,
) -> dict:
    """Record a human correction to an extraction field.

    Feeds the ai_feedback loop for future improvement.
    Returns the updated extraction_data dict.
    """
    # Add correction to the list
    corrections = list(extraction_data.get("corrections", []))
    corrections.append(
        {
            "field_path": field_path,
            "old_value": old_value,
            "new_value": new_value,
            "corrected_by_id": str(corrected_by_id),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
    extraction_data["corrections"] = corrections

    # Apply correction to extracted data
    _apply_field_correction(extraction_data.get("extracted", {}), field_path, new_value)

    # Feed the ai_feedback flywheel
    extraction_id = extraction_data.get("extraction_id")
    if extraction_id:
        feedback = AIFeedback(
            feedback_type="correct",
            entity_type="quote_extraction",
            entity_id=uuid.UUID(extraction_id),
            original_output={"field_path": field_path, "old_value": old_value},
            corrected_output={"field_path": field_path, "new_value": new_value},
            confidence=extraction_data.get("confidence"),
            user_id=corrected_by_id,
            notes=f"Quote field correction: {field_path}",
        )
        db.add(feedback)
        await db.flush()

    return extraction_data


def _apply_field_correction(
    data: dict,
    field_path: str,
    new_value: str | float | bool | None,
) -> None:
    """Apply a dot-path correction to extracted data (e.g., 'contractor.name')."""
    parts = field_path.split(".")
    target = data
    for part in parts[:-1]:
        if isinstance(target, dict) and part in target:
            target = target[part]
        else:
            return  # path not found, skip
    if isinstance(target, dict):
        target[parts[-1]] = new_value


# ---------------------------------------------------------------------------
# Convenience class wrapper
# ---------------------------------------------------------------------------


class QuoteExtractionService:
    """Namespace wrapper around module-level quote extraction functions.

    Extracts structured data from quote/devis PDFs.
    Rule-based v1 using regex patterns common in Swiss construction quotes.
    """

    extract_from_document = staticmethod(extract_from_document)
    apply_to_tender_quote = staticmethod(apply_to_tender_quote)
    record_correction = staticmethod(record_correction)
    detect_quote_type = staticmethod(detect_quote_type)
    extract_contractor_info = staticmethod(extract_contractor_info)
    extract_positions = staticmethod(extract_positions)
    extract_totals = staticmethod(extract_totals)
    extract_conditions = staticmethod(extract_conditions)
    extract_scope = staticmethod(extract_scope)
    extract_regulatory_mentions = staticmethod(extract_regulatory_mentions)
