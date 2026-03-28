"""BatiConnect -- Contract & invoice PDF extraction service (rule-based v1).

Extracts structured data from OCR'd contracts and invoices using regex patterns
common in Swiss property management documents (FR + DE).  This is Phase 1
(deterministic rules), not LLM-based.

Flow: parse -> review -> apply (NEVER auto-persist).
Every extraction gets a confidence score and provenance.
Every correction feeds the ai_feedback flywheel.

Contracts create Contract + ActionItem (renewal deadlines).
Invoices create FinancialEntry.
Both trigger ConsequenceEngine on apply.
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
from app.models.contract import Contract
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.financial_entry import FinancialEntry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Document type keywords (FR + DE)
DOCUMENT_TYPE_KEYWORDS: dict[str, list[str]] = {
    "contract": [
        "contrat",
        "convention",
        "mandat",
        "vertrag",
        "vereinbarung",
        "auftrag",
        "contrat de maintenance",
        "contrat d'entretien",
        "wartungsvertrag",
    ],
    "invoice": [
        "facture",
        "rechnung",
        "note d'honoraires",
        "honorarrechnung",
        "décompte",
        "abrechnung",
    ],
    "purchase_order": [
        "bon de commande",
        "commande",
        "bestellung",
        "kaufauftrag",
        "order",
    ],
    "service_agreement": [
        "accord de service",
        "contrat de service",
        "servicevertrag",
        "dienstleistungsvertrag",
        "service level agreement",
        "sla",
    ],
    "insurance_policy": [
        "police d'assurance",
        "assurance",
        "versicherungspolice",
        "versicherung",
        "couverture",
    ],
    "lease": [
        "bail",
        "bail à loyer",
        "contrat de bail",
        "mietvertrag",
        "pachtvertrag",
    ],
    "warranty": [
        "garantie",
        "certificat de garantie",
        "garantieschein",
        "gewährleistung",
    ],
}

# Contract type mapping from detected keywords
CONTRACT_TYPE_KEYWORDS: dict[str, list[str]] = {
    "maintenance": [
        "maintenance",
        "entretien",
        "wartung",
        "instandhaltung",
    ],
    "management_mandate": [
        "mandat de gestion",
        "gérance",
        "verwaltungsmandat",
        "liegenschaftsverwaltung",
    ],
    "concierge": [
        "concierge",
        "conciergerie",
        "hauswart",
        "hauswartung",
    ],
    "cleaning": [
        "nettoyage",
        "reinigung",
        "entretien des communs",
    ],
    "elevator": [
        "ascenseur",
        "lift",
        "aufzug",
        "élévateur",
    ],
    "heating": [
        "chauffage",
        "heizung",
        "chaudière",
        "pompe à chaleur",
        "wärmepumpe",
    ],
    "insurance": [
        "assurance",
        "versicherung",
        "police",
    ],
    "security": [
        "sécurité",
        "alarme",
        "surveillance",
        "sicherheit",
        "alarmanlage",
        "überwachung",
    ],
    "energy": [
        "énergie",
        "électricité",
        "gaz",
        "energie",
        "strom",
    ],
}

# Invoice category mapping from keywords
INVOICE_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "maintenance": ["maintenance", "entretien", "wartung", "réparation", "reparatur"],
    "repair": ["réparation", "dépannage", "reparatur", "instandsetzung"],
    "renovation": ["rénovation", "transformation", "renovation", "umbau", "sanierung"],
    "cleaning": ["nettoyage", "reinigung"],
    "elevator": ["ascenseur", "lift", "aufzug"],
    "energy": ["énergie", "électricité", "gaz", "strom", "heizöl", "mazout"],
    "insurance_premium": ["assurance", "prime", "versicherung", "prämie"],
    "management_fee": ["gérance", "honoraires de gestion", "verwaltung"],
    "concierge": ["concierge", "hauswart"],
    "legal": ["juridique", "avocat", "notaire", "rechtsberatung", "anwalt"],
    "audit": ["audit", "révision", "prüfung"],
    "other_expense": [],  # fallback
}

# Swiss QR-bill reference pattern (26 or 27 digits)
QR_REFERENCE_PATTERN = re.compile(r"\b(\d{26,27})\b")

# Standard regex patterns
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

# Notice period pattern (months / days)
NOTICE_PERIOD_PATTERN = re.compile(
    r"(?:préavis|résiliation|délai\s+de\s+résiliation|kündigungsfrist|notice)"
    r"\s*[:\-]?\s*(\d+)\s*(mois|monate|months|jours?|tage?|days?)",
    re.IGNORECASE,
)

# Duration pattern for contracts
DURATION_PATTERN = re.compile(
    r"(?:durée|dauer|duration|période)"
    r"\s*[:\-]?\s*(\d+)\s*(ans?|jahre?|years?|mois|monate|months)",
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
    cleaned = re.sub(r"['\s]", "", amount_str)
    cleaned = cleaned.replace(",", ".")
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
            for g in m.groups():
                if g is not None:
                    return g.strip()
    return None


# ---------------------------------------------------------------------------
# Core extraction functions
# ---------------------------------------------------------------------------


def detect_document_type(text: str) -> str:
    """Detect document type from text content.

    Returns one of: contract, invoice, purchase_order, service_agreement,
    insurance_policy, lease, warranty, other.

    Sort by keyword count (most hits wins); priority is tiebreaker only.
    This avoids false positives where e.g. a contract mentioning "facture"
    once in its payment terms gets classified as an invoice.
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

    # Tiebreaker priority (used only when keyword counts are equal)
    tiebreaker = {
        "invoice": 100,
        "lease": 90,
        "insurance_policy": 80,
        "service_agreement": 70,
        "contract": 60,
        "purchase_order": 50,
        "warranty": 40,
    }

    # Primary sort: keyword count (highest wins), secondary: tiebreaker
    detected.sort(key=lambda x: (x[1], tiebreaker.get(x[0], 0)), reverse=True)
    return detected[0][0]


def _detect_contract_type(text: str) -> str:
    """Detect contract sub-type from content keywords."""
    text_lower = text.lower()
    detected: list[tuple[str, int]] = []

    for ctype, keywords in CONTRACT_TYPE_KEYWORDS.items():
        count = 0
        for kw in keywords:
            count += text_lower.count(kw.lower())
        if count > 0:
            detected.append((ctype, count))

    if not detected:
        return "other"
    detected.sort(key=lambda x: x[1], reverse=True)
    return detected[0][0]


def _detect_invoice_category(text: str) -> str:
    """Detect invoice expense category from content keywords."""
    text_lower = text.lower()
    detected: list[tuple[str, int]] = []

    for category, keywords in INVOICE_CATEGORY_KEYWORDS.items():
        count = 0
        for kw in keywords:
            count += text_lower.count(kw.lower())
        if count > 0:
            detected.append((category, count))

    if not detected:
        return "other_expense"
    detected.sort(key=lambda x: x[1], reverse=True)
    return detected[0][0]


def extract_parties(text: str) -> dict:
    """Extract contract parties from text.

    Swiss contracts typically have 'Entre:' (between) parties.
    Returns dict with party_a, party_b, and confidence.
    """
    parties: dict = {
        "party_a": None,
        "party_b": None,
        "confidence": 0.3,
    }

    # French patterns: "Entre:" ... "et" ...
    entre_match = re.search(
        r"(?:entre|zwischen)\s*[:\-]?\s*(.+?)(?:\net\s+|\nund\s+|\n\s*d'une\s+part.+?\n\s*et\s+)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if entre_match:
        parties["party_a"] = entre_match.group(1).strip()[:200]
        parties["confidence"] = 0.5

        # Find party B after "et" / "und"
        rest = text[entre_match.end() :]
        party_b_match = re.match(r"(.+?)(?:\n\n|\nci-après|\nnachfolgend|\nil\s+est\s+convenu|$)", rest, re.DOTALL)
        if party_b_match:
            parties["party_b"] = party_b_match.group(1).strip()[:200]
            parties["confidence"] = 0.6

    # Fallback: look for explicit party labels
    if not parties["party_a"]:
        party_a = _extract_field(
            text,
            [
                r"(?:mandant|donneur\s+d'ordre|auftraggeber|maître\s+d'ouvrage|client)\s*[:\-]\s*(.+?)(?:\n|$)",
                r"(?:propriétaire|eigentümer|bailleur|vermieter)\s*[:\-]\s*(.+?)(?:\n|$)",
            ],
        )
        if party_a:
            parties["party_a"] = party_a[:200]
            parties["confidence"] = 0.5

    if not parties["party_b"]:
        party_b = _extract_field(
            text,
            [
                r"(?:mandataire|prestataire|auftragnehmer|entrepreneur|dienstleister)\s*[:\-]\s*(.+?)(?:\n|$)",
                r"(?:locataire|mieter|preneur)\s*[:\-]\s*(.+?)(?:\n|$)",
                r"(?:fournisseur|lieferant|supplier)\s*[:\-]\s*(.+?)(?:\n|$)",
            ],
        )
        if party_b:
            parties["party_b"] = party_b[:200]
            parties["confidence"] = min(parties["confidence"] + 0.1, 1.0)

    return parties


def extract_contract_data(text: str) -> dict:
    """Extract structured data from a contract document.

    Returns: parties, start_date, end_date, renewal_clause, termination_notice_days,
    amount, payment_terms, scope, obligations, guarantees, exclusions.
    """
    data: dict = {
        "contract_type": _detect_contract_type(text),
        "parties": extract_parties(text),
        "reference": None,
        "title": None,
        "start_date": None,
        "end_date": None,
        "auto_renewal": False,
        "renewal_clause": None,
        "termination_notice_months": None,
        "amount": None,
        "payment_terms": None,
        "payment_frequency": None,
        "scope": None,
        "obligations": [],
        "guarantees": [],
        "exclusions": [],
        "confidence": 0.3,
    }

    # Reference
    ref = _extract_field(
        text,
        [
            r"(?:référence|reference|réf\.?|n[°o]?\s*(?:de\s+)?contrat|vertrags?\s*(?:nr|nummer))"
            r"\s*[:\-]?\s*([\w\-./]+)",
            r"(?:contrat|vertrag)\s+n[°o]?\s*[:\-]?\s*([\w\-./]+)",
        ],
    )
    if ref:
        data["reference"] = ref
        data["confidence"] = min(data["confidence"] + 0.1, 1.0)

    # Title / object
    title = _extract_field(
        text,
        [
            r"(?:objet\s+du\s+contrat|vertragsgegenstand|objet)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:titre|title|bezeichnung)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:concerne|betrifft)\s*[:\-]\s*(.+?)(?:\n|$)",
        ],
    )
    if title:
        data["title"] = title[:300]
        data["confidence"] = min(data["confidence"] + 0.1, 1.0)

    # Start date
    start_str = _extract_field(
        text,
        [
            r"(?:date\s+de\s+début|début\s+du\s+contrat|entrée\s+en\s+vigueur|"
            r"vertragsbeginn|gültig\s+ab|début|start)\s*[:\-]\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:à\s+partir\s+du|ab\s+dem|dès\s+le)\s*[:\-]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
    )
    if start_str:
        parsed = _parse_date(start_str)
        if parsed:
            data["start_date"] = parsed
            data["confidence"] = min(data["confidence"] + 0.15, 1.0)

    # End date
    end_str = _extract_field(
        text,
        [
            r"(?:date\s+de\s+fin|fin\s+du\s+contrat|échéance|vertragsende|"
            r"gültig\s+bis|fin|end)\s*[:\-]\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:jusqu'au|bis\s+zum)\s*[:\-]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
    )
    if end_str:
        parsed = _parse_date(end_str)
        if parsed:
            data["end_date"] = parsed
            data["confidence"] = min(data["confidence"] + 0.1, 1.0)

    # If no explicit end date, try to compute from duration
    if not data["end_date"] and data["start_date"]:
        dur_match = DURATION_PATTERN.search(text)
        if dur_match:
            amount = int(dur_match.group(1))
            unit_str = dur_match.group(2).lower()
            if unit_str.startswith("an") or unit_str.startswith("jahr") or unit_str.startswith("year"):
                data["end_date"] = data["start_date"].replace(year=data["start_date"].year + amount)
            elif unit_str.startswith("mois") or unit_str.startswith("monat") or unit_str.startswith("month"):
                data["end_date"] = data["start_date"] + timedelta(days=amount * 30)

    # Auto-renewal
    text_lower = text.lower()
    renewal_keywords = [
        "reconduit tacitement",
        "renouvellement tacite",
        "tacite reconduction",
        "renouvelable automatiquement",
        "stillschweigende verlängerung",
        "automatische verlängerung",
        "auto-renewal",
        "reconductible",
    ]
    if any(kw in text_lower for kw in renewal_keywords):
        data["auto_renewal"] = True
        data["confidence"] = min(data["confidence"] + 0.1, 1.0)

    # Renewal clause text
    renewal = _extract_field(
        text,
        [
            r"(?:renouvellement|reconduction|verlängerung|renewal)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:le\s+contrat\s+(?:est|sera)\s+(?:reconduit|renouvelé|prolongé)|"
            r"der\s+vertrag\s+(?:wird|verlängert\s+sich))\s*(.+?)(?:\.\s|\n|$)",
        ],
    )
    if renewal:
        data["renewal_clause"] = renewal[:300]

    # Termination notice
    notice_match = NOTICE_PERIOD_PATTERN.search(text)
    if notice_match:
        amount = int(notice_match.group(1))
        unit_str = notice_match.group(2).lower()
        if unit_str.startswith("jour") or unit_str.startswith("tag") or unit_str.startswith("day"):
            # Convert days to months (approximate)
            data["termination_notice_months"] = max(1, amount // 30)
        else:
            data["termination_notice_months"] = amount
        data["confidence"] = min(data["confidence"] + 0.1, 1.0)

    # Amount (annual cost / total)
    amount_str = _extract_field(
        text,
        [
            r"(?:montant\s+annuel|coût\s+annuel|jahresbetrag|jährliche\s+kosten|annual\s+cost)"
            r"\s*[:\-]?\s*(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)",
            r"(?:montant|prix\s+forfaitaire|honoraires|betrag|pauschalpreis|vergütung)"
            r"\s*[:\-]?\s*(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)",
        ],
    )
    if amount_str:
        parsed_amount = _parse_amount(amount_str)
        if parsed_amount:
            data["amount"] = parsed_amount
            data["confidence"] = min(data["confidence"] + 0.15, 1.0)
    else:
        # Fallback: largest amount in the document
        all_amounts: list[float] = []
        for m in AMOUNT_PATTERN.finditer(text):
            raw = m.group(1) or m.group(2)
            if raw:
                parsed_amt = _parse_amount(raw)
                if parsed_amt and parsed_amt > 100:
                    all_amounts.append(parsed_amt)
        if all_amounts:
            data["amount"] = max(all_amounts)
            data["confidence"] = max(data["confidence"], 0.3)

    # Payment terms
    payment = _extract_field(
        text,
        [
            r"(?:conditions?\s+de\s+paiement|modalités?\s+de\s+paiement|"
            r"zahlungsbedingungen|zahlungsmodalitäten|payment\s+terms)"
            r"\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(\d+\s*jours?\s*(?:net|après\s+(?:réception|facturation)))",
        ],
    )
    if payment:
        data["payment_terms"] = payment

    # Payment frequency
    freq_patterns = [
        (r"mensuel|monatlich|monthly", "monthly"),
        (r"trimestriel|vierteljährlich|quarterly", "quarterly"),
        (r"semestriel|halbjährlich|semi[\-\s]?annual", "semi_annual"),
        (r"annuel|jährlich|annual|yearly", "annual"),
    ]
    for pattern, freq in freq_patterns:
        if re.search(pattern, text_lower):
            data["payment_frequency"] = freq
            break

    # Scope
    scope = _extract_field(
        text,
        [
            r"(?:prestations|scope|étendue\s+des\s+prestations|leistungsumfang|"
            r"description\s+des\s+travaux|périmètre)\s*[:\-]\s*(.+?)(?:\n\n|$)",
        ],
    )
    if scope:
        data["scope"] = scope[:500]

    # Obligations (look for numbered/bulleted lists in obligations section)
    _extract_list_section(
        text,
        data["obligations"],
        [
            r"(?:obligations?|pflichten|duties)\s*[:\-]\s*(.+?)(?:\n\n|$)",
            r"(?:le\s+(?:mandataire|prestataire)\s+s'engage\s+à|der\s+auftragnehmer\s+verpflichtet\s+sich)"
            r"\s*[:\-]?\s*(.+?)(?:\n\n|$)",
        ],
    )

    # Guarantees
    guarantee_text = _extract_field(
        text,
        [
            r"(?:garantie|caution|sûreté|kaution|sicherheit|bürgschaft)\s*[:\-]\s*(.+?)(?:\n\n|$)",
        ],
    )
    if guarantee_text:
        data["guarantees"].append(guarantee_text[:300])

    # Exclusions
    _extract_list_section(
        text,
        data["exclusions"],
        [
            r"(?:exclusions?|non\s+compris|ne\s+comprend\s+pas|"
            r"nicht\s+inbegriffen|ausgeschlossen)\s*[:\-]\s*(.+?)(?:\n\n|$)",
        ],
    )

    return data


def _extract_list_section(text: str, target_list: list[str], patterns: list[str]) -> None:
    """Extract a list of items from a text section matching patterns."""
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            block = m.group(1)
            items = re.split(r"\n[\-•]\s*|\n\d+[.)]\s*|\n\s*[;\-]\s*", block)
            for item in items:
                item = item.strip().rstrip(",;.")
                if item and len(item) > 5:
                    target_list.append(item[:300])
            break


def extract_invoice_data(text: str) -> dict:
    """Extract structured data from an invoice document.

    Returns: supplier, invoice_number, date, due_date, amount_ht, vat_rate,
    amount_ttc, line_items, payment_reference, building_reference.
    """
    data: dict = {
        "supplier": None,
        "supplier_address": None,
        "invoice_number": None,
        "date": None,
        "due_date": None,
        "amount_ht": None,
        "vat_rate": None,
        "vat_amount": None,
        "amount_ttc": None,
        "currency": "CHF",
        "line_items": [],
        "payment_reference": None,
        "qr_reference": None,
        "building_reference": None,
        "category": _detect_invoice_category(text),
        "confidence": 0.3,
    }

    header = text[:1000] if len(text) > 1000 else text

    # Supplier name (typically in header)
    supplier = _extract_field(
        header,
        [
            r"(?:fournisseur|lieferant|supplier|émetteur)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"^([A-Z][A-Za-zÀ-ÿ\s&\-]+(?:SA|Sàrl|SARL|AG|GmbH|S\.A\.))",
        ],
    )
    if supplier:
        data["supplier"] = supplier[:200]
        data["confidence"] = min(data["confidence"] + 0.1, 1.0)

    # Supplier address
    address = _extract_field(
        header,
        [
            r"(\d{4}\s+[A-Za-zÀ-ÿ\-\s]+)",
            r"((?:rue|avenue|chemin|route|strasse|weg|gasse)\s+.+?\d+)",
        ],
    )
    if address:
        data["supplier_address"] = address[:200]

    # Invoice number (FR + DE patterns)
    # Note: use [^\S\n] instead of \s where newline-spanning would cause false matches
    inv_num = _extract_field(
        text,
        [
            r"(?:n[°o]?[^\S\n]*(?:de[^\S\n]+)?facture|facture[^\S\n]+n[°o]?|rechnungs?[^\S\n]*(?:nr|nummer)|"
            r"invoice[^\S\n]*(?:no?\.?|number))[^\S\n]*[:\-]?[^\S\n]*([\w\-./]+)",
            r"(?:réf\.?[^\S\n]+facture|rechnung[^\S\n]+réf\.?)[^\S\n]*[:\-]?[^\S\n]*([\w\-./]+)",
        ],
    )
    if inv_num:
        data["invoice_number"] = inv_num
        data["confidence"] = min(data["confidence"] + 0.15, 1.0)

    # Invoice date
    date_str = _extract_field(
        text,
        [
            r"(?:date\s+(?:de\s+)?(?:la\s+)?facture|date\s+d'émission|rechnungsdatum|"
            r"invoice\s+date)\s*[:\-]\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:datum|date)\s*[:\-]\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"(?:du|le|vom)\s+(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
    )
    if date_str:
        parsed = _parse_date(date_str)
        if parsed:
            data["date"] = parsed
            data["confidence"] = min(data["confidence"] + 0.15, 1.0)

    # Due date
    due_str = _extract_field(
        text,
        [
            r"(?:échéance|date\s+d'échéance|délai\s+de\s+paiement|fällig(?:keit)?(?:sdatum)?|"
            r"due\s+date|payable\s+(?:avant|jusqu'au|d'ici)\s+le)"
            r"\s*[:\-]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
    )
    if due_str:
        parsed = _parse_date(due_str)
        if parsed:
            data["due_date"] = parsed
            data["confidence"] = min(data["confidence"] + 0.1, 1.0)

    # If no explicit due date but we have payment terms in days
    if not data["due_date"] and data["date"]:
        days_str = _extract_field(
            text,
            [
                r"(?:payable\s+à|zahlbar\s+innert|payable\s+within)\s*(\d+)\s*(?:jours?|tage?|days?)",
                r"(\d+)\s*(?:jours?\s+(?:net|après)|tage?\s+netto)",
            ],
        )
        if days_str:
            with contextlib.suppress(ValueError):
                data["due_date"] = data["date"] + timedelta(days=int(days_str))

    # Amount HT (net / before VAT)
    ht_str = _extract_field(
        text,
        [
            r"(?:montant\s+(?:HT|hors\s+taxe|net)|sous[\-\s]?total|netto(?:betrag)?|subtotal)"
            r"\s*[:\-]?\s*(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)",
            r"(?:CHF|Fr\.?|SFr\.?)\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)"
            r"\s*(?:HT|hors\s+taxe|netto)",
        ],
    )
    if ht_str:
        parsed_ht = _parse_amount(ht_str)
        if parsed_ht:
            data["amount_ht"] = parsed_ht
            data["confidence"] = min(data["confidence"] + 0.15, 1.0)

    # VAT rate
    vat_match = VAT_RATE_PATTERN.search(text)
    if vat_match:
        rate_str = vat_match.group(1).replace(",", ".")
        with contextlib.suppress(ValueError):
            data["vat_rate"] = float(rate_str)

    # VAT amount
    vat_amount_str = _extract_field(
        text,
        [
            r"(?:TVA|MwSt|MWST)\s*(?:\d+[.,]\d+\s*%)?\s*[:\-]?\s*(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?"
            r"(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)",
        ],
    )
    if vat_amount_str:
        parsed_vat = _parse_amount(vat_amount_str)
        if parsed_vat:
            data["vat_amount"] = parsed_vat

    # Amount TTC (gross / with VAT)
    ttc_str = _extract_field(
        text,
        [
            r"(?:montant\s+(?:TTC|toutes\s+taxes)|total\s+(?:TTC|à\s+payer|general)|"
            r"gesamtbetrag|totalbetrag|brutto(?:betrag)?|amount\s+due)"
            r"\s*[:\-]?\s*(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)",
            r"(?:CHF|Fr\.?|SFr\.?)\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2})?)"
            r"\s*(?:TTC|toutes\s+taxes|total)",
        ],
    )
    if ttc_str:
        parsed_ttc = _parse_amount(ttc_str)
        if parsed_ttc:
            data["amount_ttc"] = parsed_ttc
            data["confidence"] = min(data["confidence"] + 0.15, 1.0)

    # Compute missing amounts
    if data["amount_ht"] and data["vat_rate"] and not data["amount_ttc"]:
        data["amount_ttc"] = round(data["amount_ht"] * (1 + data["vat_rate"] / 100), 2)
    if data["amount_ttc"] and data["vat_rate"] and not data["amount_ht"]:
        data["amount_ht"] = round(data["amount_ttc"] / (1 + data["vat_rate"] / 100), 2)
    if data["amount_ht"] and data["amount_ttc"] and not data["vat_amount"]:
        data["vat_amount"] = round(data["amount_ttc"] - data["amount_ht"], 2)

    # Fallback: largest amount as TTC
    if not data["amount_ttc"] and not data["amount_ht"]:
        all_amounts: list[float] = []
        for m in AMOUNT_PATTERN.finditer(text):
            raw = m.group(1) or m.group(2)
            if raw:
                parsed_amt = _parse_amount(raw)
                if parsed_amt and parsed_amt > 10:
                    all_amounts.append(parsed_amt)
        if all_amounts:
            data["amount_ttc"] = max(all_amounts)
            data["confidence"] = max(data["confidence"], 0.3)

    # Line items (simple extraction: position + description + amount)
    _extract_invoice_line_items(text, data["line_items"])

    # QR-bill reference (Swiss standard 26-27 digit reference)
    qr_match = QR_REFERENCE_PATTERN.search(text)
    if qr_match:
        data["qr_reference"] = qr_match.group(1)
        data["confidence"] = min(data["confidence"] + 0.1, 1.0)

    # Payment reference (IBAN, postal account, etc.)
    pay_ref = _extract_field(
        text,
        [
            r"(CH\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{1})",  # Swiss IBAN
            r"(?:IBAN)\s*[:\-]?\s*(CH\d{2}\s*[\d\s]{10,25})",
            r"(?:CCP|compte\s+postal|postkonto)\s*[:\-]?\s*([\d\-]+)",
            r"(?:référence\s+de\s+paiement|zahlungsreferenz)\s*[:\-]?\s*([\w\-./]+)",
        ],
    )
    if pay_ref:
        data["payment_reference"] = pay_ref

    # Building reference
    bld_ref = _extract_field(
        text,
        [
            r"(?:immeuble|bâtiment|objet|objekt|liegenschaft|gebäude)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:adresse\s+de\s+(?:l'immeuble|l'objet)|objektadresse)\s*[:\-]\s*(.+?)(?:\n|$)",
        ],
    )
    if bld_ref:
        data["building_reference"] = bld_ref[:200]

    return data


def _extract_invoice_line_items(text: str, items: list[dict]) -> None:
    """Extract line items from invoice body."""
    # Pattern: position number + description + amount at end of line
    line_pattern = re.compile(
        r"^(?:(?:Pos\.?\s*)?(\d{1,3}(?:\.\d{1,3})*))\s+"
        r"(.+?)\s+"
        r"(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2}))\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    for m in line_pattern.finditer(text):
        position = m.group(1)
        description = m.group(2).strip()
        amount_str = m.group(3)
        amount = _parse_amount(amount_str)
        if amount:
            items.append(
                {
                    "position": position,
                    "description": description[:300],
                    "amount": amount,
                }
            )

    # Fallback: lines with amount at the end but no position number
    if not items:
        simple_pattern = re.compile(
            r"^(.{10,80}?)\s+"
            r"(?:CHF|Fr\.?|SFr\.?)?\s*['\s]?(\d{1,3}(?:['\s.,]\d{3})*(?:[.,]\d{2}))\s*$",
            re.MULTILINE | re.IGNORECASE,
        )
        for i, m in enumerate(simple_pattern.finditer(text)):
            description = m.group(1).strip()
            amount_str = m.group(2)
            amount = _parse_amount(amount_str)
            if amount:
                items.append(
                    {
                        "position": str(i + 1),
                        "description": description[:300],
                        "amount": amount,
                    }
                )
            if len(items) >= 50:  # safety limit
                break


def _compute_overall_confidence(doc_type: str, specific_data: dict, parties_data: dict | None = None) -> float:
    """Compute overall extraction confidence from component scores."""
    scores: list[float] = []

    # Document type detection quality
    if doc_type != "other":
        scores.append(0.6)
    else:
        scores.append(0.2)

    # Specific data confidence
    scores.append(specific_data.get("confidence", 0.3))

    # Parties confidence (only for contracts)
    if parties_data:
        scores.append(parties_data.get("confidence", 0.3))

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
    """Main entry point. Takes a document + its OCR'd text, extracts contract/invoice data.

    Returns a dict with extraction_id, status 'draft', confidence, extracted data,
    and provenance. NEVER auto-persisted. The caller presents it for human review.
    """
    # Verify document exists
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise ValueError("Document not found")

    # Detect document type first
    doc_type = detect_document_type(text)

    # Branch: contract-family vs invoice-family
    if doc_type in ("invoice", "purchase_order"):
        invoice_data = extract_invoice_data(text)
        confidence = _compute_overall_confidence(doc_type, invoice_data)

        # Strip internal confidence
        invoice_clean = {k: v for k, v in invoice_data.items() if k != "confidence"}
        # Serialize dates
        for date_field in ("date", "due_date"):
            if invoice_clean.get(date_field) and isinstance(invoice_clean[date_field], date):
                invoice_clean[date_field] = invoice_clean[date_field].isoformat()

        extracted = {
            "document_type": doc_type,
            "invoice": invoice_clean,
        }
    else:
        contract_data = extract_contract_data(text)
        parties_data = contract_data.pop("parties", {})
        confidence = _compute_overall_confidence(doc_type, contract_data, parties_data)

        # Strip internal confidence
        contract_clean = {k: v for k, v in contract_data.items() if k != "confidence"}
        parties_clean = {k: v for k, v in parties_data.items() if k != "confidence"}
        # Serialize dates
        for date_field in ("start_date", "end_date"):
            if contract_clean.get(date_field) and isinstance(contract_clean[date_field], date):
                contract_clean[date_field] = contract_clean[date_field].isoformat()

        extracted = {
            "document_type": doc_type,
            "contract": contract_clean,
            "parties": parties_clean,
        }

    extraction_id = uuid.uuid4()

    result = {
        "extraction_id": str(extraction_id),
        "status": "draft",
        "confidence": confidence,
        "extracted": extracted,
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
        "contract_extraction_created",
        extra={
            "extraction_id": str(extraction_id),
            "document_id": str(document_id),
            "document_type": doc_type,
            "confidence": confidence,
        },
    )

    return result


async def apply_contract_extraction(
    db: AsyncSession,
    extraction_data: dict,
    building_id: uuid.UUID,
    applied_by_id: uuid.UUID,
) -> dict:
    """Apply reviewed extraction to the database.

    Contracts create: Contract + ActionItem (renewal deadline obligation).
    Invoices create: FinancialEntry.
    Both create EvidenceLinks and trigger ConsequenceEngine.

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

    created_ids: dict = {
        "contract_id": None,
        "financial_entry_id": None,
        "action_item_ids": [],
        "evidence_link_ids": [],
    }

    if doc_type in ("invoice", "purchase_order"):
        # --- Create FinancialEntry from invoice ---
        inv = extracted.get("invoice", {})

        entry_date = date.today()
        if inv.get("date"):
            with contextlib.suppress(ValueError, TypeError):
                entry_date = date.fromisoformat(inv["date"])

        period_start = entry_date
        period_end = None
        if inv.get("due_date"):
            with contextlib.suppress(ValueError, TypeError):
                period_end = date.fromisoformat(inv["due_date"])

        amount = inv.get("amount_ttc") or inv.get("amount_ht") or 0.0

        description_parts = []
        if inv.get("supplier"):
            description_parts.append(f"Fournisseur: {inv['supplier']}")
        if inv.get("invoice_number"):
            description_parts.append(f"Facture n° {inv['invoice_number']}")
        if inv.get("building_reference"):
            description_parts.append(f"Objet: {inv['building_reference']}")

        fe = FinancialEntry(
            building_id=building_id,
            entry_type="expense",
            category=inv.get("category", "other_expense"),
            amount_chf=amount,
            entry_date=entry_date,
            period_start=period_start,
            period_end=period_end,
            fiscal_year=entry_date.year,
            description=" | ".join(description_parts) if description_parts else "Facture extraite automatiquement",
            document_id=uuid.UUID(document_id) if document_id else None,
            external_ref=inv.get("invoice_number"),
            status="draft",
            created_by=applied_by_id,
        )
        db.add(fe)
        await db.flush()
        await db.refresh(fe)
        created_ids["financial_entry_id"] = str(fe.id)

        # EvidenceLink: document -> financial_entry
        if document_id:
            ev = EvidenceLink(
                source_type="document",
                source_id=uuid.UUID(document_id),
                target_type="financial_entry",
                target_id=fe.id,
                relationship="extracted_from",
                confidence=confidence,
                explanation=f"Invoice extracted via rule_based_v1 (confidence: {confidence})",
                created_by=applied_by_id,
            )
            db.add(ev)
            await db.flush()
            await db.refresh(ev)
            created_ids["evidence_link_ids"].append(str(ev.id))

    else:
        # --- Create Contract from contract-family document ---
        cdata = extracted.get("contract", {})
        parties = extracted.get("parties", {})

        # Parse dates
        start_date = date.today()
        if cdata.get("start_date"):
            with contextlib.suppress(ValueError, TypeError):
                start_date = date.fromisoformat(cdata["start_date"])

        end_date = None
        if cdata.get("end_date"):
            with contextlib.suppress(ValueError, TypeError):
                end_date = date.fromisoformat(cdata["end_date"])

        # Build title
        title = cdata.get("title") or f"Contrat {cdata.get('contract_type', 'other')}"
        if parties.get("party_b"):
            title = f"{title} - {parties['party_b'][:100]}"

        # Reference code: use extracted ref or generate one
        ref_code = cdata.get("reference") or f"EXT-{uuid.uuid4().hex[:8].upper()}"

        contract = Contract(
            building_id=building_id,
            contract_type=cdata.get("contract_type", "other"),
            reference_code=ref_code,
            title=title[:500],
            counterparty_type="contact",
            counterparty_id=applied_by_id,  # placeholder until contact is linked
            date_start=start_date,
            date_end=end_date,
            annual_cost_chf=cdata.get("amount"),
            payment_frequency=cdata.get("payment_frequency"),
            auto_renewal=cdata.get("auto_renewal", False),
            notice_period_months=cdata.get("termination_notice_months"),
            status="draft",
            notes=cdata.get("scope"),
            created_by=applied_by_id,
        )
        db.add(contract)
        await db.flush()
        await db.refresh(contract)
        created_ids["contract_id"] = str(contract.id)

        # EvidenceLink: document -> contract
        if document_id:
            ev = EvidenceLink(
                source_type="document",
                source_id=uuid.UUID(document_id),
                target_type="contract",
                target_id=contract.id,
                relationship="extracted_from",
                confidence=confidence,
                explanation=f"Contract extracted via rule_based_v1 (confidence: {confidence})",
                created_by=applied_by_id,
            )
            db.add(ev)
            await db.flush()
            await db.refresh(ev)
            created_ids["evidence_link_ids"].append(str(ev.id))

        # --- Create ActionItems for renewal deadlines (obligations) ---
        if cdata.get("auto_renewal") and end_date and cdata.get("termination_notice_months"):
            # Create reminder action before the renewal/termination deadline
            notice_months = cdata["termination_notice_months"]
            reminder_date = end_date - timedelta(days=notice_months * 30)
            if reminder_date > date.today():
                action = ActionItem(
                    building_id=building_id,
                    source_type="contract_extraction",
                    action_type="renewal_deadline",
                    title=f"Échéance résiliation contrat: {title[:80]}",
                    description=(
                        f"Le contrat {ref_code} (tacite reconduction) arrive à échéance le {end_date.isoformat()}. "
                        f"Préavis de résiliation: {notice_months} mois. "
                        f"Dernier jour pour résilier: {reminder_date.isoformat()}."
                    ),
                    priority="high",
                    status="open",
                    due_date=reminder_date,
                    created_by=applied_by_id,
                    metadata_json={
                        "extraction_id": extraction_data.get("extraction_id"),
                        "contract_id": str(contract.id),
                        "end_date": end_date.isoformat(),
                        "notice_months": notice_months,
                    },
                )
                db.add(action)
                await db.flush()
                await db.refresh(action)
                created_ids["action_item_ids"].append(str(action.id))

        # Create obligation actions from contract obligations list
        for i, obligation_text in enumerate(cdata.get("obligations", [])):
            action = ActionItem(
                building_id=building_id,
                source_type="contract_extraction",
                action_type="contract_obligation",
                title=f"Obligation contractuelle: {obligation_text[:80]}",
                description=obligation_text,
                priority="medium",
                status="open",
                created_by=applied_by_id,
                metadata_json={
                    "extraction_id": extraction_data.get("extraction_id"),
                    "contract_id": str(contract.id),
                    "obligation_index": i,
                },
            )
            db.add(action)
            await db.flush()
            await db.refresh(action)
            created_ids["action_item_ids"].append(str(action.id))

    await db.flush()

    # --- Run consequence chain ---
    try:
        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        await engine.run_consequences(
            db,
            building_id,
            "contract_extraction_applied",
            trigger_id=extraction_data.get("extraction_id"),
            triggered_by_id=applied_by_id,
        )
    except Exception:
        logger.exception(
            "consequence_engine failed after contract extraction %s",
            extraction_data.get("extraction_id"),
        )

    logger.info(
        "contract_extraction_applied",
        extra={
            "extraction_id": extraction_data.get("extraction_id"),
            "building_id": str(building_id),
            "document_type": doc_type,
            "contract_created": created_ids["contract_id"] is not None,
            "financial_entry_created": created_ids["financial_entry_id"] is not None,
            "actions_created": len(created_ids["action_item_ids"]),
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
            entity_type="contract_extraction",
            entity_id=uuid.UUID(extraction_id),
            original_output={"field_path": field_path, "old_value": old_value},
            corrected_output={"field_path": field_path, "new_value": new_value},
            confidence=extraction_data.get("confidence"),
            user_id=corrected_by_id,
            notes=f"Contract/invoice field correction: {field_path}",
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
            entity_type="contract_extraction",
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
    """Apply a dot-path correction to extracted data (e.g., 'contract.amount')."""
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


class ContractExtractionService:
    """Namespace wrapper around module-level contract/invoice extraction functions.

    Extracts structured data from contracts and invoices.
    Rule-based v1 using regex patterns common in Swiss property documents (FR + DE).
    """

    extract_from_document = staticmethod(extract_from_document)
    apply_contract_extraction = staticmethod(apply_contract_extraction)
    record_correction = staticmethod(record_correction)
    reject_extraction = staticmethod(reject_extraction)
    detect_document_type = staticmethod(detect_document_type)
    extract_contract_data = staticmethod(extract_contract_data)
    extract_invoice_data = staticmethod(extract_invoice_data)
    extract_parties = staticmethod(extract_parties)
