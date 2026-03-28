"""BatiConnect -- Authority document extraction service (rule-based v1).

Extracts structured data from OCR'd authority documents: permits, decisions,
complement requests, notifications.  Uses regex patterns common in Swiss
cantonal and communal authority letters (FR + DE).  This is Phase 1
(deterministic rules), not LLM-based.

Flow: parse -> review -> apply (NEVER auto-persist).
Every extraction gets a confidence score and provenance.
Every correction feeds the ai_feedback flywheel.
"""

from __future__ import annotations

import contextlib
import logging
import re
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.ai_feedback import AIFeedback
from app.models.building import Building
from app.models.building_claim import BuildingClaim, BuildingDecision
from app.models.document import Document
from app.models.evidence_link import EvidenceLink

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Document type keywords (FR + DE)
DOCUMENT_TYPE_KEYWORDS: dict[str, list[str]] = {
    "permit_granted": [
        "permis de construire",
        "autorisation de construire",
        "permis de démolir",
        "autorisation de démolir",
        "baubewilligung",
        "abbruchbewilligung",
        "est autorisé",
        "est accordé",
        "autorise les travaux",
        "wird bewilligt",
        "wird erteilt",
        "genehmigt",
    ],
    "permit_denied": [
        "est refusé",
        "refus du permis",
        "refus de l'autorisation",
        "n'est pas autorisé",
        "wird abgelehnt",
        "wird verweigert",
        "abgewiesen",
    ],
    "permit_conditional": [
        "sous réserve des conditions suivantes",
        "sous les conditions",
        "sous les charges suivantes",
        "mit folgenden auflagen",
        "unter folgenden bedingungen",
        "unter auflagen",
        "bewilligt mit auflagen",
    ],
    "complement_request": [
        "demande de complément",
        "complément d'information",
        "pièces manquantes",
        "documents manquants",
        "nous vous prions de nous fournir",
        "veuillez nous transmettre",
        "nachforderung",
        "ergänzung",
        "fehlende unterlagen",
        "bitte reichen sie",
    ],
    "authority_notification": [
        "notification",
        "avis de mise à l'enquête",
        "mise à l'enquête publique",
        "öffentliche auflage",
        "anzeige",
        "mitteilung",
        "bekanntmachung",
    ],
    "decision": [
        "décision",
        "arrêté",
        "ordonnance",
        "verfügung",
        "entscheid",
        "beschluss",
    ],
}

# Authority name patterns (Swiss cantonal/communal)
AUTHORITY_PATTERNS: list[str] = [
    r"(?:service|office|direction|département|division|amt|direktion|abteilung)"
    r"\s+(?:de\s+|des\s+|du\s+|für\s+|der\s+)?(.+?)(?:\n|$)",
    r"(?:municipalité|commune|ville|stadt|gemeinde)\s+(?:de\s+|d'|von\s+)?(.+?)(?:\n|$)",
    r"(?:canton|kanton)\s+(?:de\s+|du\s+)?(.+?)(?:\n|$)",
    r"(?:SUVA|OFEV|OFEN|BAFU|BFE|SECO|STNE|DGTL|DFIRE|SDT|SDE|SEVEN|DJES)"
    r"(?:\s*[:\-]\s*(.+?))?(?:\n|$)",
]

# Date patterns
DATE_PATTERN = re.compile(
    r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})",
)

# Deadline patterns (explicit dates + relative delays)
DEADLINE_PATTERN = re.compile(
    r"(?:délai|frist|avant\s+le|bis\s+(?:zum|spätestens)?|au\s+plus\s+tard"
    r"|d'ici\s+le|innert|innerhalb)\s*[:\-]?\s*"
    r"(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}|\d+\s*(?:jours?|tage?|semaines?|wochen|mois|monate))",
    re.IGNORECASE,
)

# Legal basis patterns
LEGAL_BASIS_PATTERNS: list[str] = [
    r"(?:en\s+application|fondé\s+sur|conformément\s+à|en\s+vertu\s+de|gestützt\s+auf"
    r"|auf\s+grund|gemäss)\s+(.+?)(?:\.|;|\n)",
    r"(?:art\.?\s*\d+\s*(?:al\.?\s*\d+)?\s*(?:LAT|LCI|LPE|LC|LATC|LATeC|LPol|RPE|OPB"
    r"|OAT|OTConst|ORRChim|OLED|ORaP|SIA|PBG|BauG|USG|RPG|GSchG))",
    r"(?:LATC|LAT|LCI|LPE|LC|LATeC|LPol|RPE|OPB|OAT|OTConst|ORRChim|OLED|ORaP|SIA|PBG"
    r"|BauG|USG|RPG|GSchG)\s*(?:art\.?\s*\d+)",
]

# Reference number patterns
REFERENCE_PATTERNS: list[str] = [
    r"(?:n[°o]?\s*(?:de\s+)?dossier|dossier\s*n[°o]?|geschäfts?\s*(?:nr|nummer)|aktenzeichen)"
    r"\s*[:\-]?\s*([\w\-./]+)",
    r"(?:référence|reference|réf\.?|ref\.?|unser?\s+zeichen)\s*[:\-]?\s*([\w\-./]+)",
    r"(?:votre\s+(?:référence|réf\.?)|ihr\s+zeichen)\s*[:\-]?\s*([\w\-./]+)",
]

# Appeal patterns
APPEAL_PATTERNS: list[str] = [
    r"(?:recours|rekurs|beschwerde|einsprache|opposition)\s*.{0,100}?"
    r"(?:dans\s+(?:un\s+)?délai\s+de|innerhalb\s+(?:von)?|innert)\s+"
    r"(\d+)\s*(?:jours?|tage?)",
    r"(?:voie\s+de\s+recours|rechtsmittelbelehrung|rechtsmittel)\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z]|$)",
]

# Condition category keywords
CONDITION_CATEGORIES: dict[str, list[str]] = {
    "before_works": [
        "avant le début des travaux",
        "avant les travaux",
        "préalablement",
        "vor baubeginn",
        "vor arbeitsbeginn",
    ],
    "during_works": [
        "pendant les travaux",
        "durant les travaux",
        "en cours de chantier",
        "während der bauarbeiten",
        "während der arbeiten",
    ],
    "after_works": [
        "après les travaux",
        "après achèvement",
        "à l'issue des travaux",
        "nach abschluss",
        "nach fertigstellung",
        "nach bauabschluss",
    ],
    "environmental": [
        "environnement",
        "protection de la nature",
        "eaux",
        "bruit",
        "umwelt",
        "naturschutz",
        "gewässer",
        "lärm",
    ],
    "safety": [
        "sécurité",
        "protection",
        "incendie",
        "suva",
        "sicherheit",
        "brandschutz",
    ],
    "administrative": [
        "annonce",
        "notification",
        "permis",
        "autorisation",
        "anmeldung",
        "bewilligung",
    ],
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


def _parse_relative_deadline(text: str, base_date: date | None = None) -> date | None:
    """Parse a relative deadline like '30 jours' into a concrete date."""
    base = base_date or date.today()
    m = re.search(r"(\d+)\s*(jours?|tage?|semaines?|wochen|mois|monate)", text, re.IGNORECASE)
    if not m:
        return None
    amount = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("jour") or unit.startswith("tag"):
        return base + timedelta(days=amount)
    if unit.startswith("semaine") or unit.startswith("woche"):
        return base + timedelta(weeks=amount)
    if unit.startswith("mois") or unit.startswith("monat"):
        return base + timedelta(days=amount * 30)
    return None


def _extract_field(text: str, patterns: list[str]) -> str | None:
    """Extract the first matching field value from text using multiple patterns."""
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            # Return the first non-None group
            for g in m.groups():
                if g is not None:
                    return g.strip()
    return None


# ---------------------------------------------------------------------------
# Core extraction functions
# ---------------------------------------------------------------------------


def detect_document_type(text: str) -> str:
    """Detect authority document type from text content.

    Returns one of: permit_granted, permit_denied, permit_conditional,
    complement_request, authority_notification, decision, other.

    Priority: complement_request > permit_conditional > permit_granted/denied
    > authority_notification > decision > other.
    """
    text_lower = text.lower()
    detected: list[tuple[str, int]] = []

    for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
        count = 0
        for kw in keywords:
            count += text_lower.count(kw.lower())
        if count > 0:
            detected.append((doc_type, count))

    if not detected:
        return "other"

    # Priority ordering: complement_request gets priority if detected
    priority = {
        "complement_request": 100,
        "permit_conditional": 90,
        "permit_denied": 80,
        "permit_granted": 70,
        "decision": 60,
        "authority_notification": 50,
    }

    detected.sort(key=lambda x: (priority.get(x[0], 0), x[1]), reverse=True)
    return detected[0][0]


def extract_authority_metadata(text: str) -> dict:
    """Extract authority document metadata: authority_name, reference, date,
    canton, commune, building_reference, applicant.

    Uses regex patterns common in Swiss cantonal/communal authority letters.
    """
    metadata: dict = {
        "authority_name": None,
        "reference": None,
        "date": None,
        "canton": None,
        "commune": None,
        "building_reference": None,
        "applicant": None,
        "confidence": 0.3,
    }

    # Authority name
    authority = _extract_field(text, AUTHORITY_PATTERNS)
    if authority:
        metadata["authority_name"] = authority
        metadata["confidence"] = min(metadata["confidence"] + 0.1, 1.0)

    # Reference number
    ref = _extract_field(text, REFERENCE_PATTERNS)
    if ref:
        metadata["reference"] = ref
        metadata["confidence"] = min(metadata["confidence"] + 0.1, 1.0)

    # Document date
    date_str = _extract_field(
        text,
        [
            r"(?:date|datum)\s*[:\-]\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:du|le|vom)\s+(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:\w+),?\s+(?:le\s+)?(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
    )
    if date_str:
        parsed_date = _parse_date(date_str)
        if parsed_date:
            metadata["date"] = parsed_date
            metadata["confidence"] = min(metadata["confidence"] + 0.1, 1.0)

    # Canton
    canton = _extract_field(
        text,
        [
            r"(?:canton|kanton)\s+(?:de\s+|du\s+|d')?(\w+)",
            r"\b(VD|GE|VS|FR|BE|NE|JU|TI|ZH|BS|BL|AG|SO|LU|SG|ZG|SZ|TG|AR|AI|GL|GR|NW|OW|SH|UR)\b",
        ],
    )
    if canton:
        # Normalize to 2-letter code
        canton_map = {
            "vaud": "VD",
            "genève": "GE",
            "geneve": "GE",
            "valais": "VS",
            "fribourg": "FR",
            "berne": "BE",
            "bern": "BE",
            "neuchâtel": "NE",
            "neuchatel": "NE",
            "jura": "JU",
            "tessin": "TI",
            "ticino": "TI",
            "zürich": "ZH",
            "zurich": "ZH",
        }
        canton_upper = canton.upper()
        if len(canton_upper) == 2:
            metadata["canton"] = canton_upper
        else:
            metadata["canton"] = canton_map.get(canton.lower(), canton[:2].upper())

    # Commune
    commune = _extract_field(
        text,
        [
            r"(?:commune|municipalité|ville|stadt|gemeinde)\s+(?:de\s+|d'|von\s+)?(\w[\w\s\-]+?)(?:\n|,|;|\()",
            r"(?:lieu|ort|localité)\s*[:\-]\s*(\w[\w\s\-]+?)(?:\n|,|;)",
        ],
    )
    if commune:
        metadata["commune"] = commune.strip()

    # Building reference (EGRID, EGID, parcel, address)
    building_ref = _extract_field(
        text,
        [
            r"(?:parcelle|parzelle)\s*(?:n[°o]?\s*)?[:\-]?\s*([\w\-./]+)",
            r"(?:EGRID|EGID)\s*[:\-]?\s*([\w\-]+)",
            r"(?:bien[\-\s]?fonds|grundstück)\s*(?:n[°o]?\s*)?[:\-]?\s*([\w\-./]+)",
            r"(?:adresse|address|anschrift)\s*[:\-]\s*(.+?)(?:\n|$)",
        ],
    )
    if building_ref:
        metadata["building_reference"] = building_ref.strip()
        metadata["confidence"] = min(metadata["confidence"] + 0.1, 1.0)

    # Applicant
    applicant = _extract_field(
        text,
        [
            r"(?:requérant|demandeur|gesuchsteller|bauherr)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:propriétaire|eigentümer|eigentümerin)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:mandataire|architecte|architekt)\s*[:\-]\s*(.+?)(?:\n|$)",
        ],
    )
    if applicant:
        metadata["applicant"] = applicant.strip()
        metadata["confidence"] = min(metadata["confidence"] + 0.05, 1.0)

    return metadata


def extract_decision(text: str) -> dict:
    """Extract decision details: type, outcome, conditions count,
    validity_period, legal_basis, appeal_deadline.

    Looks for permit grant/deny language, legal references, appeal clauses.
    """
    decision: dict = {
        "decision_type": None,
        "outcome": None,
        "conditions_count": 0,
        "validity_period": None,
        "legal_basis": None,
        "appeal_deadline_days": None,
        "appeal_authority": None,
        "confidence": 0.3,
    }

    text_lower = text.lower()

    # Decision type (inferred from document type keywords)
    doc_type = detect_document_type(text)
    decision["decision_type"] = doc_type

    # Outcome (French + German patterns)
    if any(
        kw in text_lower
        for kw in [
            "est autorisé",
            "est accordé",
            "autorise les travaux",
            "wird bewilligt",
            "wird erteilt",
            "genehmigt",
        ]
    ):
        decision["outcome"] = "granted"
        decision["confidence"] = max(decision["confidence"], 0.7)
    elif any(
        kw in text_lower
        for kw in [
            "est refusé",
            "n'est pas autorisé",
            "wird abgelehnt",
            "wird verweigert",
            "abgewiesen",
        ]
    ):
        decision["outcome"] = "denied"
        decision["confidence"] = max(decision["confidence"], 0.7)
    elif any(
        kw in text_lower
        for kw in [
            "sous réserve",
            "sous les conditions",
            "sous les charges",
            "mit auflagen",
            "unter bedingungen",
        ]
    ):
        decision["outcome"] = "granted_with_conditions"
        decision["confidence"] = max(decision["confidence"], 0.7)

    # Legal basis
    legal_basis = _extract_field(text, LEGAL_BASIS_PATTERNS)
    if legal_basis:
        decision["legal_basis"] = legal_basis
        decision["confidence"] = min(decision["confidence"] + 0.1, 1.0)

    # Validity period
    validity_str = _extract_field(
        text,
        [
            r"(?:validité|durée\s+de\s+validité|gültigkeit|gültigkeitsdauer)"
            r"\s*[:\-]?\s*(\d+)\s*(?:ans?|jahre?|mois|monate|jours?|tage?)",
            r"(?:valable|gültig)\s+(?:pendant\s+|für\s+)?(\d+)\s*(?:ans?|jahre?|mois|monate)",
        ],
    )
    if validity_str:
        decision["validity_period"] = validity_str

    # Appeal deadline (days)
    for pattern in APPEAL_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            # Try to extract number of days
            days_match = re.search(r"(\d+)\s*(?:jours?|tage?)", m.group(0), re.IGNORECASE)
            if days_match:
                with contextlib.suppress(ValueError):
                    decision["appeal_deadline_days"] = int(days_match.group(1))
                    decision["confidence"] = min(decision["confidence"] + 0.1, 1.0)
            break

    # Appeal authority
    appeal_auth = _extract_field(
        text,
        [
            r"(?:recours|rekurs|beschwerde)\s+(?:auprès\s+(?:du|de\s+la|des)|bei(?:m)?)\s+(.+?)(?:\.|,|\n)",
            r"(?:tribunal|cour|gericht)\s+(.+?)(?:\.|,|\n)",
        ],
    )
    if appeal_auth:
        decision["appeal_authority"] = appeal_auth

    return decision


def extract_complement_request(text: str) -> dict:
    """Extract complement request details: missing items, deadline,
    reference to original application, instructions.
    """
    complement: dict = {
        "missing_items": [],
        "deadline": None,
        "deadline_date": None,
        "reference_to_original": None,
        "instructions": None,
        "confidence": 0.3,
    }

    text_lower = text.lower()

    # Check this is actually a complement request
    is_complement = any(
        kw in text_lower
        for kw in [
            "demande de complément",
            "complément d'information",
            "pièces manquantes",
            "documents manquants",
            "nous vous prions de nous fournir",
            "nachforderung",
            "ergänzung",
            "fehlende unterlagen",
        ]
    )
    if not is_complement:
        return complement

    complement["confidence"] = 0.5

    # Missing items: look for bullet/numbered lists after trigger phrases
    # Pattern 1: explicit "pièces manquantes" section
    missing_section = re.search(
        r"(?:pièces?\s+manquantes?|documents?\s+manquants?|il\s+manque|fehlende\s+unterlagen)"
        r"\s*[:\-]?\s*(.+?)(?:\n\n|\nDélai|\nNous\s+rest|\nFrist|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if missing_section:
        block = missing_section.group(1)
        items = re.split(r"\n[\-•]\s*|\n\d+[.)]\s*|\n\s*[;\-]\s*", block)
        for item in items:
            item = item.strip().rstrip(",;.")
            if item and len(item) > 5:
                complement["missing_items"].append(item)
        complement["confidence"] = min(complement["confidence"] + 0.2, 1.0)

    # Pattern 2: "veuillez nous transmettre" followed by items
    if not complement["missing_items"]:
        transmit_section = re.search(
            r"(?:veuillez\s+(?:nous\s+)?(?:transmettre|fournir|remettre)|bitte\s+(?:reichen\s+sie|senden\s+sie))"
            r"\s*[:\-]?\s*(.+?)(?:\n\n|\nDélai|\nNous\s+rest|\nFrist|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if transmit_section:
            block = transmit_section.group(1)
            items = re.split(r"\n[\-•]\s*|\n\d+[.)]\s*|\n\s*[;\-]\s*", block)
            for item in items:
                item = item.strip().rstrip(",;.")
                if item and len(item) > 5:
                    complement["missing_items"].append(item)
            complement["confidence"] = min(complement["confidence"] + 0.15, 1.0)

    # Deadline
    deadline_match = DEADLINE_PATTERN.search(text)
    if deadline_match:
        deadline_raw = deadline_match.group(1)
        # Try parsing as absolute date
        parsed = _parse_date(deadline_raw)
        if parsed:
            complement["deadline_date"] = parsed
            complement["deadline"] = parsed.isoformat()
            complement["confidence"] = min(complement["confidence"] + 0.15, 1.0)
        else:
            # Relative deadline
            complement["deadline"] = deadline_raw.strip()
            relative_date = _parse_relative_deadline(deadline_raw)
            if relative_date:
                complement["deadline_date"] = relative_date

    # Reference to original application
    ref = _extract_field(
        text,
        [
            r"(?:votre\s+(?:demande|requête|dossier|gesuch)|ihr\s+(?:gesuch|antrag))"
            r"\s+(?:du|vom)\s+(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:en\s+référence\s+à|bezugnehmend\s+auf)\s+(.+?)(?:\n|$)",
            r"(?:suite\s+à|im\s+anschluss\s+an)\s+(?:votre|ihr)\s+(.+?)(?:\n|$)",
        ],
    )
    if ref:
        complement["reference_to_original"] = ref
        complement["confidence"] = min(complement["confidence"] + 0.1, 1.0)

    # Instructions
    instructions = _extract_field(
        text,
        [
            r"(?:les\s+documents?\s+(?:doi|dev)(?:vent|t)\s+être|die\s+unterlagen\s+(?:müssen|sind))"
            r"\s+(.+?)(?:\n\n|$)",
            r"(?:merci\s+de|nous\s+vous\s+prions\s+de|bitte)\s+(.+?)(?:\.\n|\n\n|$)",
        ],
    )
    if instructions:
        complement["instructions"] = instructions

    return complement


def extract_conditions(text: str) -> list[dict]:
    """Extract conditions/restrictions from permits.

    Returns list of: [{description, category, mandatory, deadline}].
    """
    conditions: list[dict] = []

    # Find conditions section (FR + DE)
    cond_section = re.search(
        r"(?:conditions?\s*[:\-]|charges?\s*[:\-]|auflagen\s*[:\-]|bedingungen\s*[:\-]"
        r"|sous\s+(?:les?\s+)?(?:conditions?|charges?|réserves?)\s+suivant(?:e?s)?)"
        r"\s*(.+?)(?:\n\n(?:Voie|Recours|Rechtsmittel|La\s+présente|Diese|Le\s+(?:service|département))"
        r"|\n\n\n|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not cond_section:
        return conditions

    block = cond_section.group(1)

    # Split into individual conditions (numbered or bulleted)
    items = re.split(r"\n\s*\d+[.)]\s*|\n\s*[\-•]\s*|\n\s*[a-z]\)\s*", block)

    for item in items:
        item = item.strip().rstrip(",;.")
        if not item or len(item) < 10:
            continue

        condition: dict = {
            "description": item,
            "category": _detect_condition_category(item),
            "mandatory": True,  # authority conditions are mandatory by default
            "deadline": None,
        }

        # Try to extract a deadline from the condition text
        deadline_match = DEADLINE_PATTERN.search(item)
        if deadline_match:
            deadline_raw = deadline_match.group(1)
            parsed = _parse_date(deadline_raw)
            if parsed:
                condition["deadline"] = parsed.isoformat()
            else:
                condition["deadline"] = deadline_raw.strip()

        conditions.append(condition)

    return conditions


def _detect_condition_category(text: str) -> str:
    """Detect the category of a condition from its text."""
    text_lower = text.lower()
    for category, keywords in CONDITION_CATEGORIES.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return "general"


def _compute_overall_confidence(
    metadata: dict,
    decision: dict,
    complement: dict,
    conditions: list[dict],
    doc_type: str,
) -> float:
    """Compute overall extraction confidence from component scores."""
    scores: list[float] = []

    # Metadata quality
    scores.append(metadata.get("confidence", 0.3))

    # Decision quality
    scores.append(decision.get("confidence", 0.3))

    # Document type detection quality
    if doc_type != "other":
        scores.append(0.7)
    else:
        scores.append(0.2)

    # Conditions quality (if it's a permit, conditions matter)
    if doc_type in ("permit_granted", "permit_conditional"):
        if conditions:
            scores.append(min(0.5 + len(conditions) * 0.05, 0.9))
        else:
            scores.append(0.3)

    # Complement request quality
    if doc_type == "complement_request":
        scores.append(complement.get("confidence", 0.3))

    return round(sum(scores) / len(scores), 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def extract_from_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    building_id: uuid.UUID,
    text: str,
) -> dict:
    """Main entry point.  Takes a document + its OCR'd text, extracts authority data.

    Returns a dict with extraction_id, status 'draft', confidence, extracted data,
    and provenance.  NEVER auto-persisted.  The caller presents it for human review.
    """
    # Verify document exists
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise ValueError("Document not found")

    # Run extraction pipeline
    doc_type = detect_document_type(text)
    metadata = extract_authority_metadata(text)
    decision_data = extract_decision(text)
    complement_data = extract_complement_request(text)
    conditions_data = extract_conditions(text)
    confidence = _compute_overall_confidence(
        metadata,
        decision_data,
        complement_data,
        conditions_data,
        doc_type,
    )

    # Update conditions count on decision
    decision_data["conditions_count"] = len(conditions_data)

    extraction_id = uuid.uuid4()

    # Strip internal confidence fields from sub-dicts
    metadata_clean = {k: v for k, v in metadata.items() if k != "confidence"}
    decision_clean = {k: v for k, v in decision_data.items() if k != "confidence"}
    complement_clean = {k: v for k, v in complement_data.items() if k != "confidence"}

    # Serialize dates for JSON
    if metadata_clean.get("date"):
        metadata_clean["date"] = metadata_clean["date"].isoformat()
    if complement_clean.get("deadline_date"):
        complement_clean["deadline_date"] = complement_clean["deadline_date"].isoformat()

    # Build obligations from conditions
    obligations: list[dict] = []
    for cond in conditions_data:
        obligations.append(
            {
                "description": cond["description"],
                "deadline": cond.get("deadline"),
                "category": cond.get("category", "general"),
                "mandatory": cond.get("mandatory", True),
            }
        )

    # Build restrictions from conditions with specific categories
    restrictions: list[dict] = []
    for cond in conditions_data:
        if cond.get("category") in ("environmental", "safety"):
            restrictions.append(
                {
                    "description": cond["description"],
                    "scope": cond.get("category", "general"),
                }
            )

    result = {
        "extraction_id": str(extraction_id),
        "status": "draft",
        "confidence": confidence,
        "extracted": {
            "document_type": doc_type,
            "authority": metadata_clean,
            "reference": metadata_clean.get("reference"),
            "date": metadata_clean.get("date"),
            "decision": decision_clean,
            "complement": complement_clean,
            "conditions": [{k: v for k, v in c.items()} for c in conditions_data],
            "obligations_created": obligations,
            "restrictions": restrictions,
        },
        "provenance": {
            "source_document_id": str(document_id),
            "building_id": str(building_id),
            "extraction_method": "rule_based_v1",
            "extraction_date": datetime.now(UTC).isoformat(),
            "requires_human_review": True,
        },
        "corrections": [],
    }

    logger.info(
        "authority_extraction_created",
        extra={
            "extraction_id": str(extraction_id),
            "document_id": str(document_id),
            "document_type": doc_type,
            "conditions_count": len(conditions_data),
            "confidence": confidence,
        },
    )

    return result


async def apply_authority_extraction(
    db: AsyncSession,
    extraction_data: dict,
    building_id: uuid.UUID,
    applied_by_id: uuid.UUID,
) -> dict:
    """Apply reviewed extraction to the database.

    Creates: BuildingDecision + ActionItems (from complement) +
    BuildingClaims (from conditions/restrictions).
    Follows parse -> review -> apply pattern (NEVER auto-called).

    Returns dict with created entity IDs.
    """
    extracted = extraction_data.get("extracted", {})
    doc_type = extracted.get("document_type", "other")
    provenance = extraction_data.get("provenance", {})
    document_id = provenance.get("source_document_id")
    confidence = extraction_data.get("confidence", 0.0)

    # Look up building for organization_id
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    bld = bld_result.scalar_one_or_none()
    if bld is None:
        raise ValueError("Building not found")

    org_id = bld.organization_id
    created_ids: dict = {
        "decision_id": None,
        "action_item_ids": [],
        "claim_ids": [],
        "evidence_link_ids": [],
    }

    # --- 1. Create BuildingDecision (for permits/decisions) ---
    if doc_type in (
        "permit_granted",
        "permit_denied",
        "permit_conditional",
        "decision",
    ):
        decision_info = extracted.get("decision", {})
        authority_info = extracted.get("authority", {})

        # Derive title
        title_map = {
            "permit_granted": "Permis accordé",
            "permit_denied": "Permis refusé",
            "permit_conditional": "Permis accordé sous conditions",
            "decision": "Décision de l'autorité",
        }
        title = title_map.get(doc_type, "Décision de l'autorité")
        ref = extracted.get("reference")
        if ref:
            title = f"{title} ({ref})"

        # Derive outcome
        outcome_map = {
            "granted": "Autorisation accordée",
            "denied": "Autorisation refusée",
            "granted_with_conditions": "Autorisation accordée sous conditions",
        }
        outcome = outcome_map.get(
            decision_info.get("outcome", ""),
            decision_info.get("outcome", "Décision rendue"),
        )

        # Derive rationale
        rationale_parts = []
        if decision_info.get("legal_basis"):
            rationale_parts.append(f"Base légale: {decision_info['legal_basis']}")
        if authority_info.get("authority_name"):
            rationale_parts.append(f"Autorité: {authority_info['authority_name']}")
        if decision_info.get("conditions_count"):
            rationale_parts.append(f"Conditions: {decision_info['conditions_count']}")
        rationale = ". ".join(rationale_parts) if rationale_parts else "Extraction automatique depuis document"

        # Parse effective date
        effective_at = None
        date_str = extracted.get("date")
        if date_str:
            with contextlib.suppress(ValueError, TypeError):
                effective_at = datetime.fromisoformat(date_str)
                if effective_at.tzinfo is None:
                    effective_at = effective_at.replace(tzinfo=UTC)

        # Parse validity
        valid_until = None
        validity_period = decision_info.get("validity_period")
        if validity_period and effective_at:
            m = re.search(r"(\d+)", validity_period)
            if m:
                years = int(m.group(1))
                with contextlib.suppress(Exception):
                    valid_until = effective_at.replace(year=effective_at.year + years)

        bd = BuildingDecision(
            building_id=building_id,
            organization_id=org_id,
            decision_maker_id=applied_by_id,
            decision_type="permit_decision",
            title=title,
            description=f"Type: {doc_type}. Ref: {ref or 'N/A'}.",
            outcome=outcome,
            rationale=rationale,
            authority_level="authority",
            reversible=True,
            status="enacted",
            enacted_at=datetime.now(UTC),
            effective_at=effective_at,
            valid_until=valid_until,
        )
        db.add(bd)
        await db.flush()
        await db.refresh(bd)
        created_ids["decision_id"] = str(bd.id)

        # EvidenceLink: document -> decision
        if document_id:
            ev = EvidenceLink(
                source_type="document",
                source_id=uuid.UUID(document_id),
                target_type="building_decision",
                target_id=bd.id,
                relationship="extracted_from",
                confidence=confidence,
                explanation=f"Authority decision extracted via rule_based_v1 (confidence: {confidence})",
                created_by=applied_by_id,
            )
            db.add(ev)
            await db.flush()
            await db.refresh(ev)
            created_ids["evidence_link_ids"].append(str(ev.id))

    # --- 2. Create ActionItems from complement requests ---
    if doc_type == "complement_request":
        complement_info = extracted.get("complement", {})
        missing_items = complement_info.get("missing_items", [])

        # Parse due date
        due_date = None
        deadline_date_str = complement_info.get("deadline_date")
        if deadline_date_str:
            with contextlib.suppress(ValueError, TypeError):
                due_date = date.fromisoformat(deadline_date_str)
        if not due_date and complement_info.get("deadline"):
            due_date = _parse_relative_deadline(complement_info["deadline"])

        for i, item in enumerate(missing_items):
            action = ActionItem(
                building_id=building_id,
                source_type="authority_extraction",
                action_type="complement_request",
                title=f"Complément requis: {item[:100]}",
                description=item,
                priority="high",
                status="open",
                due_date=due_date,
                created_by=applied_by_id,
                metadata_json={
                    "extraction_id": extraction_data.get("extraction_id"),
                    "item_index": i,
                    "authority": extracted.get("authority", {}).get("authority_name"),
                    "reference": extracted.get("reference"),
                },
            )
            db.add(action)
            await db.flush()
            await db.refresh(action)
            created_ids["action_item_ids"].append(str(action.id))

        # If no specific items but we detected a complement request, create a generic action
        if not missing_items:
            action = ActionItem(
                building_id=building_id,
                source_type="authority_extraction",
                action_type="complement_request",
                title="Demande de complément reçue",
                description=complement_info.get("instructions", "Complément d'information requis par l'autorité"),
                priority="high",
                status="open",
                due_date=due_date,
                created_by=applied_by_id,
                metadata_json={
                    "extraction_id": extraction_data.get("extraction_id"),
                    "authority": extracted.get("authority", {}).get("authority_name"),
                    "reference": extracted.get("reference"),
                },
            )
            db.add(action)
            await db.flush()
            await db.refresh(action)
            created_ids["action_item_ids"].append(str(action.id))

    # --- 3. Create BuildingClaims from conditions/restrictions ---
    conditions_list = extracted.get("conditions", [])
    for cond in conditions_list:
        claim_type = "condition_assessment"
        if cond.get("category") in ("environmental", "safety"):
            claim_type = "compliance_status"

        # Parse validity
        valid_until = None
        if cond.get("deadline"):
            with contextlib.suppress(ValueError, TypeError):
                valid_until_date = date.fromisoformat(cond["deadline"])
                valid_until = datetime(
                    valid_until_date.year,
                    valid_until_date.month,
                    valid_until_date.day,
                    tzinfo=UTC,
                )

        claim = BuildingClaim(
            building_id=building_id,
            organization_id=org_id,
            claimed_by_id=applied_by_id,
            claim_type=claim_type,
            subject=f"Condition d'autorisation: {cond.get('category', 'general')}",
            assertion=cond["description"],
            basis_type="ai_extraction",
            basis_ids=[extraction_data.get("extraction_id")],
            confidence=confidence,
            status="asserted",
            valid_until=valid_until,
        )
        db.add(claim)
        await db.flush()
        await db.refresh(claim)
        created_ids["claim_ids"].append(str(claim.id))

    await db.flush()

    # --- 4. Run consequence chain ---
    try:
        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        await engine.run_consequences(
            db,
            building_id,
            "authority_extraction_applied",
            trigger_id=extraction_data.get("extraction_id"),
            triggered_by_id=applied_by_id,
        )
    except Exception:
        logger.exception(
            "consequence_engine failed after authority extraction %s",
            extraction_data.get("extraction_id"),
        )

    logger.info(
        "authority_extraction_applied",
        extra={
            "extraction_id": extraction_data.get("extraction_id"),
            "building_id": str(building_id),
            "document_type": doc_type,
            "decision_created": created_ids["decision_id"] is not None,
            "actions_created": len(created_ids["action_item_ids"]),
            "claims_created": len(created_ids["claim_ids"]),
        },
    )

    return created_ids


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
            entity_type="authority_extraction",
            entity_id=uuid.UUID(extraction_id),
            original_output={"field_path": field_path, "old_value": old_value},
            corrected_output={"field_path": field_path, "new_value": new_value},
            confidence=extraction_data.get("confidence"),
            user_id=corrected_by_id,
            notes=f"Authority document field correction: {field_path}",
        )
        db.add(feedback)
        await db.flush()

    return extraction_data


async def reject_extraction(
    db: AsyncSession,
    extraction_data: dict,
    rejected_by_id: uuid.UUID,
    reason: str | None = None,
) -> dict:
    """Reject an extraction. Records feedback for the flywheel."""
    extraction_data["status"] = "rejected"

    extraction_id = extraction_data.get("extraction_id")
    if extraction_id:
        feedback = AIFeedback(
            feedback_type="reject",
            entity_type="authority_extraction",
            entity_id=uuid.UUID(extraction_id),
            original_output=extraction_data.get("extracted"),
            confidence=extraction_data.get("confidence"),
            user_id=rejected_by_id,
            notes=reason,
        )
        db.add(feedback)
        await db.flush()

    return extraction_data


def _apply_field_correction(
    data: dict,
    field_path: str,
    new_value: str | float | bool | None,
) -> None:
    """Apply a dot-path correction to extracted data (e.g., 'authority.authority_name')."""
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


class AuthorityExtractionService:
    """Namespace wrapper around module-level authority extraction functions.

    Extracts structured data from authority documents: permits, decisions,
    complement requests, notifications.
    Rule-based v1 using regex patterns common in Swiss authority documents (FR + DE).
    """

    extract_from_document = staticmethod(extract_from_document)
    apply_authority_extraction = staticmethod(apply_authority_extraction)
    record_correction = staticmethod(record_correction)
    reject_extraction = staticmethod(reject_extraction)
    detect_document_type = staticmethod(detect_document_type)
    extract_authority_metadata = staticmethod(extract_authority_metadata)
    extract_decision = staticmethod(extract_decision)
    extract_complement_request = staticmethod(extract_complement_request)
    extract_conditions = staticmethod(extract_conditions)
