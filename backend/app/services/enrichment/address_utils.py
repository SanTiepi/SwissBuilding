"""Address normalization and verification utilities."""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Address normalization
# ---------------------------------------------------------------------------
_ABBREVIATION_MAP: dict[str, str] = {
    "av.": "avenue",
    "av ": "avenue ",
    "ch.": "chemin",
    "ch ": "chemin ",
    "rte": "route",
    "rte.": "route",
    "rte ": "route ",
    "pl.": "place",
    "pl ": "place ",
    "bd.": "boulevard",
    "bd ": "boulevard ",
    "imp.": "impasse",
    "chem.": "chemin",
    "str.": "strasse",
}

_REVERSE_ABBREVIATION_MAP: dict[str, str] = {
    "avenue": "av.",
    "chemin": "ch.",
    "route": "rte",
    "place": "pl.",
    "boulevard": "bd.",
    "strasse": "str.",
}


def _strip_accents(s: str) -> str:
    """Remove diacritics/accents from a string."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize_address(address: str, npa: str = "", city: str = "") -> str:
    """Normalize an address for geocoding.

    - Remove extra spaces
    - Expand abbreviations: av. -> avenue, ch. -> chemin, etc.
    - Add city name to search if provided
    - Format: "{address}, {npa} {city}"
    """
    text = (address or "").strip()
    text = re.sub(r"\s+", " ", text)

    # Expand abbreviations (case-insensitive)
    text_lower = text.lower()
    for abbr, full in _ABBREVIATION_MAP.items():
        if abbr in text_lower:
            # Find position in lowered text, replace in original
            idx = text_lower.find(abbr)
            while idx >= 0:
                text = text[:idx] + full + text[idx + len(abbr) :]
                text_lower = text.lower()
                idx = text_lower.find(abbr, idx + len(full))

    parts = [text]
    if npa:
        parts.append(npa.strip())
    if city:
        parts.append(city.strip())

    return ", ".join(p for p in parts if p)


def _normalize_for_comparison(text: str) -> str:
    """Normalize text for fuzzy comparison: lowercase, strip accents, collapse whitespace."""
    text = _strip_accents(text.lower())
    text = re.sub(r"[,.\-/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Collapse abbreviations to canonical
    for abbr, full in _ABBREVIATION_MAP.items():
        text = text.replace(abbr.strip("."), full.rstrip())
    for full, abbr in _REVERSE_ABBREVIATION_MAP.items():
        text = text.replace(abbr.strip("."), full)
    return text


def _extract_street_number(text: str) -> str | None:
    """Extract the street number from an address string."""
    match = re.search(r"\b(\d+[a-zA-Z]?)\b", text)
    return match.group(1) if match else None


def _extract_street_name(text: str) -> str:
    """Extract the street name (remove number, city, NPA)."""
    # Remove numbers at end (house number)
    name = re.sub(r"\b\d+[a-zA-Z]?\b", "", text)
    # Remove NPA-like patterns (4 digits)
    name = re.sub(r"\b\d{4}\b", "", name)
    return re.sub(r"\s+", " ", name).strip()


def verify_geocode_match(
    input_address: str,
    input_npa: str,
    result_label: str,
) -> str:
    """Compare geocode result label with input address.

    Returns match_quality: 'exact' | 'partial' | 'weak' | 'no_match'.
    """
    if not result_label:
        return "no_match"

    norm_input = _normalize_for_comparison(input_address + " " + (input_npa or ""))
    norm_result = _normalize_for_comparison(result_label)

    input_number = _extract_street_number(norm_input)
    result_number = _extract_street_number(norm_result)
    input_street = _extract_street_name(norm_input)
    result_street = _extract_street_name(norm_result)

    number_match = input_number == result_number if input_number and result_number else False
    # Street name: check if main words overlap
    input_words = set(input_street.split()) - {"de", "du", "des", "la", "le", "les", "l", "d"}
    result_words = set(result_street.split()) - {"de", "du", "des", "la", "le", "les", "l", "d"}
    common = input_words & result_words
    street_match = len(common) >= 1 and len(common) / max(len(input_words), 1) >= 0.5

    if number_match and street_match:
        return "exact"
    if street_match:
        return "partial"
    if common:
        return "weak"
    return "no_match"


def verify_egid_address(
    building_address: str,
    regbl_strname: str | None,
    regbl_deinr: str | None,
) -> str:
    """Compare building address with RegBL strname + deinr.

    Returns egid_confidence: 'verified' | 'probable' | 'unverified'.
    """
    if not regbl_strname:
        return "unverified"

    norm_building = _normalize_for_comparison(building_address or "")
    regbl_full = regbl_strname or ""
    if regbl_deinr:
        regbl_full += " " + regbl_deinr
    norm_regbl = _normalize_for_comparison(regbl_full)

    building_number = _extract_street_number(norm_building)
    regbl_number = _extract_street_number(norm_regbl)
    building_street = _extract_street_name(norm_building)
    regbl_street = _extract_street_name(norm_regbl)

    b_words = set(building_street.split()) - {"de", "du", "des", "la", "le", "les", "l", "d"}
    r_words = set(regbl_street.split()) - {"de", "du", "des", "la", "le", "les", "l", "d"}
    common = b_words & r_words
    street_match = len(common) >= 1 and len(common) / max(len(b_words), 1) >= 0.5
    number_match = building_number == regbl_number if building_number and regbl_number else True

    if street_match and number_match:
        return "verified"
    if street_match:
        return "probable"
    return "unverified"
