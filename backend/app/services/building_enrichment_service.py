"""Building auto-enrichment pipeline — Swiss public APIs + AI.

Fills building records with data from geo.admin.ch, RegBL/GWR,
Swisstopo, cadastre, and optionally AI-generated descriptions.
All external calls use httpx with graceful error handling.
Production-grade: per-source confidence, match verification,
retry with backoff, enrichment quality summary.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import os
import re
import unicodedata
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.enrichment import EnrichmentResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate-limit helper
# ---------------------------------------------------------------------------
_last_request_time: float = 0.0
_RATE_LIMIT_SECONDS = 1.0


async def _throttle() -> None:
    """Wait if needed to enforce 1 request/second to external APIs."""
    global _last_request_time
    now = asyncio.get_event_loop().time()
    elapsed = now - _last_request_time
    if elapsed < _RATE_LIMIT_SECONDS:
        await asyncio.sleep(_RATE_LIMIT_SECONDS - elapsed)
    _last_request_time = asyncio.get_event_loop().time()


# ---------------------------------------------------------------------------
# Retry with backoff
# ---------------------------------------------------------------------------
_TRANSIENT_STATUS_CODES = {500, 502, 503, 504}
_RETRY_DELAYS: dict[int, float] = {
    500: 2.0,
    502: 2.0,
    503: 2.0,
    504: 5.0,
}
_CONNECTION_RETRY_DELAY = 3.0


async def _retry_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    params: dict | None = None,
    data: dict | None = None,
    json_body: dict | None = None,
    headers: dict | None = None,
    timeout: float = 15.0,
) -> tuple[httpx.Response, int]:
    """Execute an HTTP request with a single retry on transient failures.

    Returns (response, retry_count).
    On permanent errors (400, 404) returns immediately with no retry.
    """
    retry_count = 0
    kwargs: dict[str, Any] = {}
    if params:
        kwargs["params"] = params
    if data:
        kwargs["data"] = data
    if json_body:
        kwargs["json"] = json_body
    if headers:
        kwargs["headers"] = headers

    try:
        if method == "GET":
            resp = await client.get(url, **kwargs)
        else:
            resp = await client.post(url, **kwargs)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
        # Connection error — retry once
        logger.warning("Connection error for %s, retrying in %.1fs: %s", url, _CONNECTION_RETRY_DELAY, exc)
        await asyncio.sleep(_CONNECTION_RETRY_DELAY)
        retry_count = 1
        if method == "GET":
            resp = await client.get(url, **kwargs)
        else:
            resp = await client.post(url, **kwargs)
        return resp, retry_count

    if resp.status_code in _TRANSIENT_STATUS_CODES:
        delay = _RETRY_DELAYS.get(resp.status_code, 2.0)
        logger.warning(
            "Transient %d for %s, retrying in %.1fs",
            resp.status_code,
            url,
            delay,
        )
        await asyncio.sleep(delay)
        retry_count = 1
        if method == "GET":
            resp = await client.get(url, **kwargs)
        else:
            resp = await client.post(url, **kwargs)

    return resp, retry_count


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


# ---------------------------------------------------------------------------
# Per-source metadata helper
# ---------------------------------------------------------------------------


def _source_entry(
    source_name: str,
    *,
    status: str = "success",
    confidence: str = "high",
    match_quality: str | None = None,
    retry_count: int = 0,
    error: str | None = None,
) -> dict[str, Any]:
    """Create a standardized per-source metadata entry."""
    entry: dict[str, Any] = {
        "source_name": source_name,
        "status": status,
        "confidence": confidence,
        "fetched_at": datetime.now(UTC).isoformat(),
        "retry_count": retry_count,
        "error": error,
    }
    if match_quality is not None:
        entry["match_quality"] = match_quality
    return entry


# ---------------------------------------------------------------------------
# Enrichment quality summary
# ---------------------------------------------------------------------------


def compute_enrichment_quality(
    source_entries: list[dict[str, Any]],
    *,
    geocode_quality: str | None = None,
    egid_confidence: str | None = None,
) -> dict[str, Any]:
    """Compute an enrichment quality summary from per-source entries.

    Returns dict with total_sources, succeeded, failed, unavailable,
    timeout, skipped, overall_confidence, critical_gaps, warnings.
    """
    total = len(source_entries)
    succeeded = sum(1 for e in source_entries if e.get("status") == "success")
    partial = sum(1 for e in source_entries if e.get("status") == "partial")
    failed = sum(1 for e in source_entries if e.get("status") == "failed")
    unavailable = sum(1 for e in source_entries if e.get("status") == "unavailable")
    timeout = sum(1 for e in source_entries if e.get("status") == "timeout")
    skipped = sum(1 for e in source_entries if e.get("status") == "skipped")

    critical_gaps: list[str] = []
    warnings: list[str] = []

    # Check critical sources
    source_map = {e["source_name"]: e for e in source_entries}

    geocode_entry = source_map.get("geocode")
    if geocode_entry and geocode_entry.get("status") != "success":
        critical_gaps.append("Geocode failed — no coordinates")
    elif geocode_quality and geocode_quality in ("weak", "no_match"):
        warnings.append(f"Geocode match is {geocode_quality}")

    regbl_entry = source_map.get("regbl")
    if regbl_entry and regbl_entry.get("status") != "success":
        critical_gaps.append("RegBL data missing")

    if egid_confidence == "unverified":
        warnings.append("EGID not verified against address")
    elif egid_confidence == "probable":
        warnings.append("EGID match is probable but not exact")

    # No EGID at all
    if not source_map.get("regbl") or source_map.get("regbl", {}).get("status") in ("failed", "skipped"):
        critical_gaps.append("EGID not found")

    # Overall confidence
    if critical_gaps:
        overall_confidence = "low"
    elif warnings or failed > total * 0.3:
        overall_confidence = "medium"
    else:
        overall_confidence = "high"

    return {
        "total_sources": total,
        "succeeded": succeeded + partial,
        "failed": failed,
        "unavailable": unavailable,
        "timeout": timeout,
        "skipped": skipped,
        "overall_confidence": overall_confidence,
        "critical_gaps": critical_gaps,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Supported geo.admin.ch identify layers
# ---------------------------------------------------------------------------
# Layers known to work with the identify API.
# Layers that consistently return 400 are excluded.
SUPPORTED_IDENTIFY_LAYERS: set[str] = {
    "ch.bfs.gebaeude_wohnungs_register",
    "ch.bag.radonkarte",
    "ch.bafu.showme-gemeinden_hochwasser",
    "ch.bafu.showme-gemeinden_rutschungen",
    "ch.bafu.showme-gemeinden_sturzprozesse",
    "ch.bafu.laerm-strassenlaerm_tag",
    "ch.bfe.solarenergie-eignung-daecher",
    "ch.bak.bundesinventar-schuetzenswerte-ortsbilder",
    "ch.are.gueteklassen_oev",
    "ch.bafu.erdbeben-erdbebenzonen",
    "ch.bafu.grundwasserschutzareale",
    "ch.bafu.laerm-bahnlaerm_tag",
    "ch.bazl.laermbelastungskataster-zivilflugplaetze",
    "ch.are.bauzonen",
    "ch.bafu.altlasten-kataster",
    "ch.bafu.grundwasserschutzzonen",
    "ch.bafu.gefahrenkarte-hochwasser",
    "ch.bakom.mobilnetz-5g",
    "ch.bakom.breitband-technologien",
    "ch.bfe.ladestellen-elektromobilitaet",
    "ch.bfe.thermische-netze",
    "ch.bak.bundesinventar-schuetzenswerte-denkmaler",
    "ch.blw.bodeneignungskarte",
    "ch.bafu.waldreservate",
    "ch.vbs.schiessplaetze",
    "ch.bafu.stoerfallverordnung",
}

# Layers discovered to NOT support identify (400 errors).
# Cached to avoid wasting requests.
_UNSUPPORTED_LAYERS: set[str] = set()


# ---------------------------------------------------------------------------
# 1. Geocode via geo.admin.ch
# ---------------------------------------------------------------------------


async def geocode_address(address: str, npa: str, city: str = "") -> dict[str, Any]:
    """Geocode a Swiss address using geo.admin.ch search API.

    Returns dict with keys: lat, lon, egid, label, detail, match_quality,
    _source_entry (per-source metadata).
    Returns empty dict on failure.
    """
    await _throttle()
    search_text = _normalize_address(address, npa, city)
    url = "https://api3.geo.admin.ch/rest/services/api/SearchServer"
    params = {
        "searchText": search_text,
        "type": "locations",
        "limit": 1,
    }
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp, retry_count = await _retry_request(client, "GET", url, params=params, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {
                "_source_entry": _source_entry(
                    "geocode",
                    status="failed",
                    confidence="low",
                    error="no results",
                    retry_count=retry_count,
                ),
            }

        attrs = results[0].get("attrs", {})
        result: dict[str, Any] = {}

        # Coordinates (WGS84)
        if "lat" in attrs and "lon" in attrs:
            result["lat"] = float(attrs["lat"])
            result["lon"] = float(attrs["lon"])

        # EGID (featureId format is "884846_0" — take part before underscore)
        if "featureId" in attrs:
            with contextlib.suppress(ValueError, TypeError):
                fid = str(attrs["featureId"]).split("_")[0]
                result["egid"] = int(fid)

        result["label"] = attrs.get("label", "")
        result["detail"] = attrs.get("detail", "")

        # Verify match quality
        match_quality = verify_geocode_match(address, npa, result.get("label", ""))
        result["match_quality"] = match_quality

        if match_quality in ("weak", "no_match"):
            logger.warning(
                "Geocode match_quality=%s for '%s %s' → '%s'",
                match_quality,
                address,
                npa,
                result.get("label", ""),
            )

        confidence = "high" if match_quality == "exact" else "medium" if match_quality == "partial" else "low"
        result["_source_entry"] = _source_entry(
            "geocode",
            status="success",
            confidence=confidence,
            match_quality=match_quality,
            retry_count=retry_count,
        )

        return result

    except Exception as exc:
        logger.warning("Geocoding failed for '%s %s': %s", address, npa, exc)
        return {
            "_source_entry": _source_entry(
                "geocode",
                status="failed",
                confidence="low",
                error=str(exc),
                retry_count=retry_count,
            ),
        }


# ---------------------------------------------------------------------------
# 2. RegBL / GWR data
# ---------------------------------------------------------------------------


async def fetch_regbl_data(egid: int, building_address: str = "") -> dict[str, Any]:
    """Fetch building data from the Swiss Register of Buildings via geo.admin.ch.

    Uses the GWR layer on geo.admin.ch which returns comprehensive building data
    including EGRID, parcel number, construction year, floors, dwellings, surface,
    heating type, energy source, and individual dwelling details.

    Returns dict with construction_year, floors, dwellings, egid_confidence, etc.
    Returns empty dict on 404 or error.
    """
    await _throttle()
    url = f"https://api3.geo.admin.ch/rest/services/ech/MapServer/ch.bfs.gebaeude_wohnungs_register/{egid}_0"
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp, retry_count = await _retry_request(client, "GET", url, timeout=15.0)
            if resp.status_code == 404:
                logger.info("RegBL: EGID %d not found (404)", egid)
                return {
                    "_source_entry": _source_entry(
                        "regbl",
                        status="failed",
                        confidence="low",
                        error="EGID not found (404)",
                        retry_count=retry_count,
                    ),
                }
            resp.raise_for_status()
            data = resp.json()

        # geo.admin.ch wraps data in feature.attributes
        attrs = data
        if isinstance(data, dict) and "feature" in data:
            attrs = data["feature"].get("attributes", data)
        if not isinstance(attrs, dict):
            return {
                "_source_entry": _source_entry(
                    "regbl",
                    status="failed",
                    confidence="low",
                    error="invalid response structure",
                    retry_count=retry_count,
                ),
            }

        result: dict[str, Any] = {}

        # Direct field mapping from GWR geo.admin.ch response
        if attrs.get("gbauj"):
            result["construction_year"] = int(attrs["gbauj"])
        if attrs.get("gastw"):
            result["floors"] = int(attrs["gastw"])
        if attrs.get("ganzwhg"):
            result["dwellings"] = int(attrs["ganzwhg"])
        if attrs.get("gebf"):
            result["living_area_m2"] = float(attrs["gebf"])
        if attrs.get("garea"):
            result["ground_area_m2"] = float(attrs["garea"])
        if attrs.get("gwaerzh1"):
            result["heating_type_code"] = attrs["gwaerzh1"]
        if attrs.get("genh1"):
            result["energy_source_code"] = attrs["genh1"]
        if attrs.get("gkat"):
            result["building_category_code"] = attrs["gkat"]
        if attrs.get("gklas"):
            result["building_class_code"] = attrs["gklas"]
        if attrs.get("gbaup"):
            result["renovation_period_code"] = attrs["gbaup"]

        # EGRID and parcel (very valuable)
        if attrs.get("egrid"):
            result["egrid"] = attrs["egrid"]
        if attrs.get("lparz"):
            result["parcel_number"] = attrs["lparz"]
        if attrs.get("gebnr"):
            result["building_number"] = attrs["gebnr"]  # = ECA number

        # Address fields from RegBL for verification
        strname = attrs.get("strname") or attrs.get("strname_deinr") or attrs.get("strasse")
        deinr = attrs.get("deinr") or attrs.get("hausnummer")
        result["_regbl_strname"] = strname
        result["_regbl_deinr"] = deinr

        # EGID verification against building address
        egid_confidence = verify_egid_address(building_address, strname, deinr)
        result["egid_confidence"] = egid_confidence
        if egid_confidence == "unverified":
            logger.warning(
                "EGID %d address mismatch: building='%s', regbl='%s %s'",
                egid,
                building_address,
                strname or "",
                deinr or "",
            )

        # Dwelling details
        if attrs.get("warea") and isinstance(attrs["warea"], list):
            result["dwelling_areas_m2"] = attrs["warea"]
            result["dwelling_rooms"] = attrs.get("wazim", [])
            result["dwelling_floors"] = attrs.get("wstwk", [])

        # Heating update date
        if attrs.get("gwaerdath1"):
            result["heating_updated_at"] = attrs["gwaerdath1"]

        confidence = "high" if egid_confidence == "verified" else "medium" if egid_confidence == "probable" else "low"
        result["_source_entry"] = _source_entry(
            "regbl",
            status="success",
            confidence=confidence,
            match_quality=egid_confidence,
            retry_count=retry_count,
        )

        return result

    except Exception as exc:
        logger.warning("RegBL fetch failed for EGID %d: %s", egid, exc)
        return {
            "_source_entry": _source_entry(
                "regbl",
                status="failed",
                confidence="low",
                error=str(exc),
                retry_count=retry_count,
            ),
        }


# ---------------------------------------------------------------------------
# 3. Swisstopo orthophoto URL
# ---------------------------------------------------------------------------


def _lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert WGS84 lat/lon to Web Mercator tile x/y at given zoom."""
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def fetch_swisstopo_image_url(lat: float, lon: float, zoom: int = 18) -> str:
    """Build a Swisstopo WMTS orthophoto tile URL for the given location."""
    x, y = _lat_lon_to_tile(lat, lon, zoom)
    return f"https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage-product/default/current/3857/{zoom}/{x}/{y}.jpeg"


# ---------------------------------------------------------------------------
# 4. Cadastre EGRID lookup
# ---------------------------------------------------------------------------


async def fetch_cadastre_egrid(lat: float, lon: float) -> dict[str, Any]:
    """Look up EGRID and parcel info for a coordinate via geo.admin.ch identify.

    Returns dict with keys: egrid, parcel_number, municipality.
    Returns empty dict on failure.
    """
    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": "all:ch.bfs.gebaeude_wohnungs_register",
        "tolerance": 10,
        "sr": 4326,
        "returnGeometry": "false",
        "limit": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {}

        attrs = results[0].get("attributes", {})
        result: dict[str, Any] = {}

        if attrs.get("egrid"):
            result["egrid"] = str(attrs["egrid"])
        if attrs.get("grundstueckNr"):
            result["parcel_number"] = str(attrs["grundstueckNr"])
        elif "parcel_number" in attrs:
            result["parcel_number"] = str(attrs["parcel_number"])
        if attrs.get("gemeindename"):
            result["municipality"] = str(attrs["gemeindename"])

        return result

    except Exception as exc:
        logger.warning("Cadastre EGRID lookup failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# 5. AI enrichment (Claude / OpenAI — graceful if no key)
# ---------------------------------------------------------------------------


async def enrich_building_with_ai(building_data: dict, context: str = "") -> dict[str, Any]:
    """Generate AI descriptions for a building using available LLM API.

    Uses ANTHROPIC_API_KEY (Claude) or OPENAI_API_KEY (OpenAI) if set.
    Returns empty dict if no API key is configured (graceful degradation).
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if not anthropic_key and not openai_key:
        logger.info("No AI API key configured — skipping AI enrichment")
        return {}

    prompt = _build_ai_prompt(building_data, context)

    try:
        if anthropic_key:
            return await _call_anthropic(anthropic_key, prompt)
        else:
            return await _call_openai(openai_key, prompt)
    except Exception as exc:
        logger.warning("AI enrichment failed: %s", exc)
        return {}


def _build_ai_prompt(building_data: dict, context: str) -> str:
    """Build the prompt for AI enrichment."""
    info = json.dumps(building_data, ensure_ascii=False, default=str)
    return (
        "Tu es un expert en immobilier suisse. Analyse les donnees suivantes "
        "d'un batiment et genere un JSON avec exactement ces cles:\n"
        "- building_description: 2-3 phrases decrivant le batiment et son contexte\n"
        "- neighborhood_description: contexte du quartier/zone\n"
        "- risk_assessment_hint: risques typiques de polluants selon l'annee et le type\n"
        "- renovation_context: types de renovations courantes pour ce profil\n\n"
        f"Donnees du batiment:\n{info}\n"
        f"{'Contexte supplementaire: ' + context if context else ''}\n\n"
        "Reponds UNIQUEMENT avec du JSON valide, sans markdown ni commentaire."
    )


async def _call_anthropic(api_key: str, prompt: str) -> dict[str, Any]:
    """Call Anthropic Claude API."""
    await _throttle()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("content", [{}])[0].get("text", "{}")
        return json.loads(text)


async def _call_openai(api_key: str, prompt: str) -> dict[str, Any]:
    """Call OpenAI API."""
    await _throttle()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return json.loads(text)


# ---------------------------------------------------------------------------
# 5b. Radon risk
# ---------------------------------------------------------------------------


async def fetch_radon_risk(lat: float, lon: float) -> dict[str, Any]:
    """Fetch radon risk data from BAG radon map via geo.admin.ch.

    Returns dict with radon_zone, radon_probability, radon_level.
    Returns empty dict on failure.
    """
    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": "all:ch.bag.radonkarte",
        "tolerance": 50,
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {}

        attrs = results[0].get("attributes", {})
        result: dict[str, Any] = {}

        radon_zone = attrs.get("zone") or attrs.get("radon_zone") or attrs.get("klasse")
        if radon_zone is not None:
            result["radon_zone"] = str(radon_zone)

        probability = attrs.get("probability") or attrs.get("wahrscheinlichkeit")
        if probability is not None:
            with contextlib.suppress(ValueError, TypeError):
                result["radon_probability"] = float(probability)

        # Derive level from zone
        zone_str = str(radon_zone).lower() if radon_zone else ""
        if "hoch" in zone_str or "high" in zone_str or zone_str in ("3", "4"):
            result["radon_level"] = "high"
        elif "mittel" in zone_str or "medium" in zone_str or zone_str == "2":
            result["radon_level"] = "medium"
        else:
            result["radon_level"] = "low"

        return result

    except Exception as exc:
        logger.warning("Radon risk fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# 5c. Natural hazards
# ---------------------------------------------------------------------------


async def fetch_natural_hazards(lat: float, lon: float) -> dict[str, Any]:
    """Fetch natural hazard data (flood, landslide, rockfall) via geo.admin.ch.

    Returns dict with flood_risk, landslide_risk, rockfall_risk.
    Returns empty dict on failure.
    """
    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": (
            "all:ch.bafu.showme-gemeinden_hochwasser,"
            "ch.bafu.showme-gemeinden_rutschungen,"
            "ch.bafu.showme-gemeinden_sturzprozesse"
        ),
        "tolerance": 50,
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {}

        result: dict[str, Any] = {
            "flood_risk": "unknown",
            "landslide_risk": "unknown",
            "rockfall_risk": "unknown",
        }

        for item in results:
            layer = item.get("layerBodId", "") or item.get("layerId", "")
            attrs = item.get("attributes", {})
            level = attrs.get("stufe") or attrs.get("level") or attrs.get("intensitaet") or "unknown"

            if "hochwasser" in layer:
                result["flood_risk"] = str(level)
            elif "rutschungen" in layer:
                result["landslide_risk"] = str(level)
            elif "sturzprozesse" in layer:
                result["rockfall_risk"] = str(level)

        return result

    except Exception as exc:
        logger.warning("Natural hazards fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# 5d. Noise exposure
# ---------------------------------------------------------------------------


async def fetch_noise_data(lat: float, lon: float) -> dict[str, Any]:
    """Fetch road noise exposure data via geo.admin.ch.

    Returns dict with road_noise_day_db, noise_level.
    Returns empty dict on failure.
    """
    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": "all:ch.bafu.laerm-strassenlaerm_tag",
        "tolerance": 50,
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {}

        attrs = results[0].get("attributes", {})
        result: dict[str, Any] = {}

        db_value = attrs.get("dblr") or attrs.get("db") or attrs.get("lrpegel")
        if db_value is not None:
            with contextlib.suppress(ValueError, TypeError):
                db_float = float(db_value)
                result["road_noise_day_db"] = db_float
                if db_float < 45:
                    result["noise_level"] = "quiet"
                elif db_float < 55:
                    result["noise_level"] = "moderate"
                elif db_float < 65:
                    result["noise_level"] = "loud"
                else:
                    result["noise_level"] = "very_loud"

        return result

    except Exception as exc:
        logger.warning("Noise data fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# 5e. Solar potential
# ---------------------------------------------------------------------------


async def fetch_solar_potential(lat: float, lon: float) -> dict[str, Any]:
    """Fetch solar energy potential for rooftops via geo.admin.ch.

    Returns dict with solar_potential_kwh, roof_area_m2, suitability.
    Returns empty dict on failure.
    """
    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": "all:ch.bfe.solarenergie-eignung-daecher",
        "tolerance": 20,
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {}

        attrs = results[0].get("attributes", {})
        result: dict[str, Any] = {}

        kwh = attrs.get("stromertrag") or attrs.get("gstrahlung") or attrs.get("mstrahlung")
        if kwh is not None:
            with contextlib.suppress(ValueError, TypeError):
                result["solar_potential_kwh"] = float(kwh)

        area = attrs.get("flaeche") or attrs.get("df_uid")
        if area is not None:
            with contextlib.suppress(ValueError, TypeError):
                result["roof_area_m2"] = float(area)

        eignung = attrs.get("klasse") or attrs.get("eignung")
        if eignung is not None:
            eignung_str = str(eignung).lower()
            if "gut" in eignung_str or "sehr" in eignung_str or "hoch" in eignung_str:
                result["suitability"] = "high"
            elif "mittel" in eignung_str or "medium" in eignung_str:
                result["suitability"] = "medium"
            else:
                result["suitability"] = "low"
        elif result.get("solar_potential_kwh"):
            # Derive suitability from kWh
            kwh_val = result["solar_potential_kwh"]
            if kwh_val > 1000:
                result["suitability"] = "high"
            elif kwh_val > 500:
                result["suitability"] = "medium"
            else:
                result["suitability"] = "low"

        return result

    except Exception as exc:
        logger.warning("Solar potential fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# 5f. Heritage / ISOS
# ---------------------------------------------------------------------------


async def fetch_heritage_status(lat: float, lon: float) -> dict[str, Any]:
    """Fetch heritage/ISOS protection status via geo.admin.ch.

    Returns dict with isos_protected, isos_category, site_name.
    Returns empty dict on failure.
    """
    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": "all:ch.bak.bundesinventar-schuetzenswerte-ortsbilder",
        "tolerance": 50,
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {"isos_protected": False}

        attrs = results[0].get("attributes", {})
        result: dict[str, Any] = {"isos_protected": True}

        category = attrs.get("kategorie") or attrs.get("category") or attrs.get("isos_kategorie")
        if category is not None:
            result["isos_category"] = str(category)

        name = attrs.get("ortsbildname") or attrs.get("name") or attrs.get("bezeichnung")
        if name is not None:
            result["site_name"] = str(name)

        return result

    except Exception as exc:
        logger.warning("Heritage status fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# 5g. Public transport quality
# ---------------------------------------------------------------------------


async def fetch_transport_quality(lat: float, lon: float) -> dict[str, Any]:
    """Fetch public transport quality class via geo.admin.ch.

    Returns dict with transport_quality_class (A-D), description.
    Returns empty dict on failure.
    """
    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": "all:ch.are.gueteklassen_oev",
        "tolerance": 50,
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {}

        attrs = results[0].get("attributes", {})
        result: dict[str, Any] = {}

        klasse = attrs.get("klasse") or attrs.get("gueteklasse") or attrs.get("class")
        if klasse is not None:
            klasse_str = str(klasse).upper().strip()
            # Normalize to A/B/C/D
            for letter in ("A", "B", "C", "D"):
                if letter in klasse_str:
                    result["transport_quality_class"] = letter
                    break
            else:
                result["transport_quality_class"] = klasse_str

        desc = attrs.get("beschreibung") or attrs.get("description") or attrs.get("label")
        if desc is not None:
            result["description"] = str(desc)
        elif result.get("transport_quality_class"):
            _desc_map = {
                "A": "Excellent public transport access",
                "B": "Good public transport access",
                "C": "Moderate public transport access",
                "D": "Poor public transport access",
            }
            result["description"] = _desc_map.get(result["transport_quality_class"], "Unknown quality")

        return result

    except Exception as exc:
        logger.warning("Transport quality fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# 5h. Seismic zone
# ---------------------------------------------------------------------------


async def fetch_seismic_zone(lat: float, lon: float) -> dict[str, Any]:
    """Fetch seismic zone classification via geo.admin.ch.

    Returns dict with seismic_zone, seismic_class.
    Returns empty dict on failure.
    """
    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": "all:ch.bafu.erdbeben-erdbebenzonen",
        "tolerance": 50,
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {}

        attrs = results[0].get("attributes", {})
        result: dict[str, Any] = {}

        zone = attrs.get("zone") or attrs.get("erdbebenzone")
        if zone is not None:
            result["seismic_zone"] = str(zone)

        klasse = attrs.get("klasse") or attrs.get("bauwerksklasse") or attrs.get("class")
        if klasse is not None:
            result["seismic_class"] = str(klasse)
        elif zone is not None:
            # SIA 261 mapping
            zone_str = str(zone)
            _class_map = {"1": "Z1", "2": "Z2", "3a": "Z3a", "3b": "Z3b"}
            result["seismic_class"] = _class_map.get(zone_str.lower(), f"Z{zone_str}")

        return result

    except Exception as exc:
        logger.warning("Seismic zone fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# 5i. Water protection
# ---------------------------------------------------------------------------


async def fetch_water_protection(lat: float, lon: float) -> dict[str, Any]:
    """Fetch groundwater protection zone via geo.admin.ch.

    Returns dict with protection_zone, zone_type.
    Returns empty dict on failure.
    """
    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": "all:ch.bafu.grundwasserschutzareale",
        "tolerance": 50,
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return {}

        attrs = results[0].get("attributes", {})
        result: dict[str, Any] = {}

        zone = attrs.get("zone") or attrs.get("schutzzone") or attrs.get("azone")
        if zone is not None:
            result["protection_zone"] = str(zone)

        zone_type = attrs.get("typ") or attrs.get("zone_type") or attrs.get("art")
        if zone_type is not None:
            result["zone_type"] = str(zone_type)

        return result

    except Exception as exc:
        logger.warning("Water protection fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# Generic geo.admin.ch identify helper
# ---------------------------------------------------------------------------


async def _geo_identify(lat: float, lon: float, layer: str) -> dict[str, Any]:
    """Generic geo.admin.ch identify call for any layer.

    Returns attributes dict on success, or dict with only '_source_entry' key on failure.
    Handles:
    - 400 → marks layer as unsupported, returns unavailable status
    - 200 empty → normal (no data at location), returns empty dict
    - 500/502/503/504 → retries once
    """
    # Skip known-unsupported layers
    if layer in _UNSUPPORTED_LAYERS:
        return {
            "_source_entry": _source_entry(
                layer,
                status="unavailable",
                confidence="low",
                error="layer not supported by identify API",
            ),
        }

    await _throttle()
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "layers": f"all:{layer}",
        "tolerance": 50,
        "sr": 4326,
        "returnGeometry": "false",
        "limit": 1,
    }
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp, retry_count = await _retry_request(client, "GET", url, params=params, timeout=15.0)

            # 400 → layer not supported by identify
            if resp.status_code == 400:
                _UNSUPPORTED_LAYERS.add(layer)
                logger.info("Layer %s returned 400 — marking as unsupported", layer)
                return {
                    "_source_entry": _source_entry(
                        layer,
                        status="unavailable",
                        confidence="low",
                        error="400 — layer not supported",
                        retry_count=retry_count,
                    ),
                }

            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if results:
            attrs = results[0].get("attributes", results[0].get("properties", {}))
            attrs["_source_entry"] = _source_entry(
                layer,
                status="success",
                confidence="high",
                retry_count=retry_count,
            )
            return attrs
        # Empty results — valid response, just no data at this location
        return {
            "_source_entry": _source_entry(
                layer,
                status="success",
                confidence="high",
                retry_count=retry_count,
            ),
        }
    except Exception as exc:
        logger.warning("geo.admin.ch identify failed for layer %s: %s", layer, exc)
        status = "timeout" if "timeout" in str(exc).lower() else "failed"
        return {
            "_source_entry": _source_entry(
                layer,
                status=status,
                confidence="low",
                error=str(exc),
                retry_count=retry_count,
            ),
        }


# ---------------------------------------------------------------------------
# 5i-2. Railway noise
# ---------------------------------------------------------------------------


async def fetch_railway_noise(lat: float, lon: float) -> dict[str, Any]:
    """Fetch railway noise exposure (day) via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bafu.laerm-bahnlaerm_tag")
    if not attrs:
        return {}
    result: dict[str, Any] = {}
    db_val = attrs.get("lr_tag") or attrs.get("dblr") or attrs.get("db")
    if db_val is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["railway_noise_day_db"] = float(db_val)
    return result


# ---------------------------------------------------------------------------
# 5i-3. Aircraft noise
# ---------------------------------------------------------------------------


async def fetch_aircraft_noise(lat: float, lon: float) -> dict[str, Any]:
    """Fetch aircraft noise from civil airfield noise cadastre via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bazl.laermbelastungskataster-zivilflugplaetze")
    if not attrs:
        return {}
    result: dict[str, Any] = {}
    db_val = attrs.get("lr_tag") or attrs.get("db") or attrs.get("lrpegel")
    if db_val is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["aircraft_noise_db"] = float(db_val)
    return result


# ---------------------------------------------------------------------------
# 5i-4. Building zones
# ---------------------------------------------------------------------------


async def fetch_building_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch building zone classification via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.are.bauzonen")
    if not attrs:
        return {}
    result: dict[str, Any] = {}
    zone_type = attrs.get("zone_type") or attrs.get("zonentyp") or attrs.get("typ")
    if zone_type is not None:
        result["zone_type"] = str(zone_type)
    zone_code = attrs.get("zone_code") or attrs.get("ch_code") or attrs.get("code")
    if zone_code is not None:
        result["zone_code"] = str(zone_code)
    desc = attrs.get("zone_description") or attrs.get("bezeichnung") or attrs.get("description") or attrs.get("label")
    if desc is not None:
        result["zone_description"] = str(desc)
    return result


# ---------------------------------------------------------------------------
# 5i-5. Contaminated sites
# ---------------------------------------------------------------------------


async def fetch_contaminated_sites(lat: float, lon: float) -> dict[str, Any]:
    """Fetch contaminated site (Altlasten) info via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bafu.altlasten-kataster")
    if not attrs:
        return {"is_contaminated": False}
    result: dict[str, Any] = {"is_contaminated": True}
    site_type = attrs.get("standorttyp") or attrs.get("site_type") or attrs.get("typ")
    if site_type is not None:
        result["site_type"] = str(site_type)
    status = attrs.get("untersuchungsstand") or attrs.get("investigation_status") or attrs.get("status")
    if status is not None:
        result["investigation_status"] = str(status)
    return result


# ---------------------------------------------------------------------------
# 5i-6. Groundwater protection zones
# ---------------------------------------------------------------------------


async def fetch_groundwater_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch groundwater protection zone (S1/S2/S3) via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bafu.grundwasserschutzzonen")
    if not attrs:
        return {}
    result: dict[str, Any] = {}
    zone = attrs.get("zone") or attrs.get("schutzzone") or attrs.get("azone")
    if zone is not None:
        result["protection_zone"] = str(zone)
    zone_type = attrs.get("typ") or attrs.get("zone_type") or attrs.get("art")
    if zone_type is not None:
        result["zone_type"] = str(zone_type)
    return result


# ---------------------------------------------------------------------------
# 5i-7. Flood zones
# ---------------------------------------------------------------------------


async def fetch_flood_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch flood danger map data via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bafu.gefahrenkarte-hochwasser")
    if not attrs:
        return {}
    result: dict[str, Any] = {}
    level = attrs.get("gefahrenstufe") or attrs.get("stufe") or attrs.get("danger_level")
    if level is not None:
        result["flood_danger_level"] = str(level)
    period = attrs.get("wiederkehrperiode") or attrs.get("return_period") or attrs.get("jt")
    if period is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["flood_return_period"] = int(period)
    return result


# ---------------------------------------------------------------------------
# 5i-8. Mobile coverage (5G)
# ---------------------------------------------------------------------------


async def fetch_mobile_coverage(lat: float, lon: float) -> dict[str, Any]:
    """Fetch 5G mobile coverage via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bakom.mobilnetz-5g")
    return {"has_5g_coverage": bool(attrs)}


# ---------------------------------------------------------------------------
# 5i-9. Broadband technologies
# ---------------------------------------------------------------------------


async def fetch_broadband(lat: float, lon: float) -> dict[str, Any]:
    """Fetch broadband technology info via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bakom.breitband-technologien")
    if not attrs:
        return {}
    result: dict[str, Any] = {}
    tech = attrs.get("technology") or attrs.get("technologie") or attrs.get("typ")
    if tech is not None:
        result["broadband_technology"] = str(tech)
    speed = attrs.get("max_speed") or attrs.get("geschwindigkeit") or attrs.get("speed_down")
    if speed is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["max_speed_mbps"] = float(speed)
    return result


# ---------------------------------------------------------------------------
# 5i-10. EV charging stations
# ---------------------------------------------------------------------------


async def fetch_ev_charging(lat: float, lon: float) -> dict[str, Any]:
    """Fetch EV charging station proximity via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bfe.ladestellen-elektromobilitaet")
    if not attrs:
        return {"ev_stations_nearby": 0}
    result: dict[str, Any] = {"ev_stations_nearby": 1}
    dist = attrs.get("distance") or attrs.get("entfernung")
    if dist is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["nearest_distance_m"] = float(dist)
    return result


# ---------------------------------------------------------------------------
# 5i-11. Thermal / district heating networks
# ---------------------------------------------------------------------------


async def fetch_thermal_networks(lat: float, lon: float) -> dict[str, Any]:
    """Fetch district heating / thermal network info via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bfe.thermische-netze")
    if not attrs:
        return {"has_district_heating": False}
    result: dict[str, Any] = {"has_district_heating": True}
    name = attrs.get("name") or attrs.get("bezeichnung") or attrs.get("netzname")
    if name is not None:
        result["network_name"] = str(name)
    return result


# ---------------------------------------------------------------------------
# 5i-12. Protected monuments (Bundesinventar)
# ---------------------------------------------------------------------------


async def fetch_protected_monuments(lat: float, lon: float) -> dict[str, Any]:
    """Fetch listed monument status via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bak.bundesinventar-schuetzenswerte-denkmaler")
    if not attrs:
        return {"is_listed_monument": False}
    result: dict[str, Any] = {"is_listed_monument": True}
    cat = attrs.get("kategorie") or attrs.get("category") or attrs.get("klasse")
    if cat is not None:
        result["monument_category"] = str(cat)
    return result


# ---------------------------------------------------------------------------
# 5i-13. Agricultural zones / soil quality
# ---------------------------------------------------------------------------


async def fetch_agricultural_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch soil quality / agricultural zone info via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.blw.bodeneignungskarte")
    if not attrs:
        return {}
    result: dict[str, Any] = {}
    quality = attrs.get("eignung") or attrs.get("soil_quality") or attrs.get("klasse")
    if quality is not None:
        result["soil_quality"] = str(quality)
    zone = attrs.get("zone") or attrs.get("agricultural_zone") or attrs.get("typ")
    if zone is not None:
        result["agricultural_zone"] = str(zone)
    return result


# ---------------------------------------------------------------------------
# 5i-14. Forest reserves
# ---------------------------------------------------------------------------


async def fetch_forest_reserves(lat: float, lon: float) -> dict[str, Any]:
    """Fetch forest reserve status via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bafu.waldreservate")
    if not attrs:
        return {"in_forest_reserve": False}
    result: dict[str, Any] = {"in_forest_reserve": True}
    name = attrs.get("name") or attrs.get("bezeichnung") or attrs.get("reservatname")
    if name is not None:
        result["reserve_name"] = str(name)
    return result


# ---------------------------------------------------------------------------
# 5i-15. Military zones (shooting ranges)
# ---------------------------------------------------------------------------


async def fetch_military_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch military shooting range proximity via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.vbs.schiessplaetze")
    if not attrs:
        return {"near_shooting_range": False}
    result: dict[str, Any] = {"near_shooting_range": True}
    dist = attrs.get("distance") or attrs.get("entfernung")
    if dist is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["distance_m"] = float(dist)
    return result


# ---------------------------------------------------------------------------
# 5i-16. Accident (Seveso) sites
# ---------------------------------------------------------------------------


async def fetch_accident_sites(lat: float, lon: float) -> dict[str, Any]:
    """Fetch Seveso / major accident site proximity via geo.admin.ch."""
    attrs = await _geo_identify(lat, lon, "ch.bafu.stoerfallverordnung")
    if not attrs:
        return {"near_seveso_site": False}
    result: dict[str, Any] = {"near_seveso_site": True}
    name = attrs.get("name") or attrs.get("bezeichnung") or attrs.get("betrieb")
    if name is not None:
        result["site_name"] = str(name)
    dist = attrs.get("distance") or attrs.get("entfernung")
    if dist is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["distance_m"] = float(dist)
    return result


# ---------------------------------------------------------------------------
# 5i-17. OSM amenities via Overpass API
# ---------------------------------------------------------------------------


async def fetch_osm_amenities(lat: float, lon: float, radius: int = 500) -> dict[str, Any]:
    """Count amenities by type within radius using Overpass API."""
    await _throttle()
    query = f"[out:json][timeout:15];(node[amenity](around:{radius},{lat},{lon}););out body;"
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp, retry_count = await _retry_request(
                client,
                "POST",
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()

        elements = data.get("elements", [])
        counts: dict[str, int] = {}
        _amenity_map = {
            "school": "schools",
            "hospital": "hospitals",
            "pharmacy": "pharmacies",
            "supermarket": "supermarkets",
            "restaurant": "restaurants",
            "cafe": "cafes",
            "bank": "banks",
            "post_office": "post_offices",
            "park": "parks",
            "kindergarten": "kindergartens",
        }
        for el in elements:
            amenity = el.get("tags", {}).get("amenity", "")
            key = _amenity_map.get(amenity)
            if key:
                counts[key] = counts.get(key, 0) + 1

        result: dict[str, Any] = {k: counts.get(k, 0) for k in _amenity_map.values()}
        result["total_amenities"] = len(elements)
        result["_source_entry"] = _source_entry(
            "overpass/amenities",
            status="success",
            confidence="medium",
            retry_count=retry_count,
        )
        return result

    except Exception as exc:
        logger.warning("Overpass amenities fetch failed for (%s, %s): %s", lat, lon, exc)
        status = "timeout" if "504" in str(exc) or "timeout" in str(exc).lower() else "failed"
        return {
            "_source_entry": _source_entry(
                "overpass/amenities",
                status=status,
                confidence="low",
                error=str(exc),
                retry_count=retry_count,
            ),
        }


# ---------------------------------------------------------------------------
# 5i-18. OSM building details via Overpass API
# ---------------------------------------------------------------------------


async def fetch_osm_building_details(lat: float, lon: float) -> dict[str, Any]:
    """Fetch building footprint details from OSM via Overpass."""
    await _throttle()
    query = f"[out:json][timeout:15];(way[building](around:30,{lat},{lon}););out body 1;"
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp, retry_count = await _retry_request(
                client,
                "POST",
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()

        elements = data.get("elements", [])
        if not elements:
            return {
                "_source_entry": _source_entry(
                    "overpass/building",
                    status="success",
                    confidence="medium",
                    retry_count=retry_count,
                ),
            }

        tags = elements[0].get("tags", {})
        result: dict[str, Any] = {}
        if tags.get("height"):
            with contextlib.suppress(ValueError, TypeError):
                result["height"] = float(tags["height"])
        if tags.get("building:levels"):
            with contextlib.suppress(ValueError, TypeError):
                result["levels"] = int(tags["building:levels"])
        if tags.get("building:material"):
            result["material"] = str(tags["building:material"])
        if tags.get("roof:shape"):
            result["roof_type"] = str(tags["roof:shape"])
        if tags.get("wheelchair"):
            result["wheelchair_access"] = str(tags["wheelchair"])
        result["_source_entry"] = _source_entry(
            "overpass/building",
            status="success",
            confidence="medium",
            retry_count=retry_count,
        )
        return result

    except Exception as exc:
        logger.warning("Overpass building details fetch failed for (%s, %s): %s", lat, lon, exc)
        status = "timeout" if "504" in str(exc) or "timeout" in str(exc).lower() else "failed"
        return {
            "_source_entry": _source_entry(
                "overpass/building",
                status=status,
                confidence="low",
                error=str(exc),
                retry_count=retry_count,
            ),
        }


# ---------------------------------------------------------------------------
# 5i-19. Climate data (estimate from altitude + canton)
# ---------------------------------------------------------------------------


def fetch_climate_data(lat: float, lon: float) -> dict[str, Any]:
    """Estimate climate data from coordinates using Swiss climate zone heuristics.

    Pure function — no API calls. Uses latitude/altitude approximation.
    """
    # Rough altitude estimate from latitude in Switzerland
    # (higher altitude in the south / Alps)
    # Swiss plateau ~400-600m, Jura ~800-1000m, Alps ~1500-3000m
    # Latitude range: 45.8 (Chiasso) to 47.8 (Schaffhausen)
    estimated_alt = max(300, int((47.5 - lat) * 800 + 400))
    estimated_alt = min(estimated_alt, 3000)

    # Temperature: roughly -6.5C per 1000m altitude
    base_temp = 10.5  # Swiss mean at 500m
    avg_temp = round(base_temp - (estimated_alt - 500) * 0.0065, 1)

    # Precipitation: varies 800-2000mm, higher in Alps
    precip = int(900 + (estimated_alt - 500) * 0.6)
    precip = max(800, min(precip, 2200))

    # Frost days: ~80 at 500m, +15 per 500m altitude
    frost_days = int(80 + (estimated_alt - 500) * 0.03)
    frost_days = max(40, min(frost_days, 200))

    # Sunshine hours: ~1600 at plateau, less in Alps due to fog but more at high alt
    sunshine = int(1600 - abs(estimated_alt - 1200) * 0.2)
    sunshine = max(1200, min(sunshine, 2100))

    # Heating degree days (base 20C): roughly (20 - avg_temp) * 365 * 0.6
    hdd = int(max(0, (20 - avg_temp) * 365 * 0.6))

    # Tropical days (>30C): rare in Switzerland, mostly Ticino/Rhone
    tropical = 0
    if lat < 46.2:  # Ticino
        tropical = 15
    elif estimated_alt < 500:
        tropical = 5
    elif estimated_alt < 800:
        tropical = 2

    return {
        "avg_temp_c": avg_temp,
        "precipitation_mm": precip,
        "frost_days": frost_days,
        "sunshine_hours": sunshine,
        "heating_degree_days": hdd,
        "tropical_days": tropical,
        "estimated_altitude_m": estimated_alt,
    }


# ---------------------------------------------------------------------------
# 5i-20. Nearest public transport stops (transport.opendata.ch)
# ---------------------------------------------------------------------------


async def fetch_nearest_stops(lat: float, lon: float) -> dict[str, Any]:
    """Fetch nearest public transport stops via transport.opendata.ch."""
    await _throttle()
    url = "https://transport.opendata.ch/v1/locations"
    params = {
        "x": str(lat),
        "y": str(lon),
        "type": "station",
    }
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp, retry_count = await _retry_request(client, "GET", url, params=params, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

        stations = data.get("stations", [])
        if not stations:
            return {
                "_source_entry": _source_entry(
                    "transport.opendata.ch",
                    status="success",
                    confidence="high",
                    retry_count=retry_count,
                ),
            }

        stops: list[dict[str, Any]] = []
        for s in stations[:5]:
            stop: dict[str, Any] = {"name": s.get("name", "")}
            if s.get("distance") is not None:
                stop["distance_m"] = int(s["distance"])
            stops.append(stop)

        result: dict[str, Any] = {"stops": stops}
        if stops:
            result["nearest_stop_name"] = stops[0]["name"]
            result["nearest_stop_distance_m"] = stops[0].get("distance_m", 0)
        result["_source_entry"] = _source_entry(
            "transport.opendata.ch",
            status="success",
            confidence="high",
            retry_count=retry_count,
        )
        return result

    except Exception as exc:
        logger.warning("Transport stops fetch failed for (%s, %s): %s", lat, lon, exc)
        status = "timeout" if "timeout" in str(exc).lower() else "failed"
        return {
            "_source_entry": _source_entry(
                "transport.opendata.ch",
                status=status,
                confidence="low",
                error=str(exc),
                retry_count=retry_count,
            ),
        }


# ---------------------------------------------------------------------------
# Computed scores
# ---------------------------------------------------------------------------


def compute_connectivity_score(enrichment_data: dict[str, Any]) -> float:
    """Compute connectivity score (0-10) from 5G, broadband, EV, district heating.

    Pure function — no API calls.
    """
    score = 0.0
    count = 0

    # 5G coverage: 2.5 points
    mobile = enrichment_data.get("mobile_coverage", {})
    if mobile.get("has_5g_coverage"):
        score += 2.5
    count += 1

    # Broadband speed: 0-2.5 points
    broadband = enrichment_data.get("broadband", {})
    speed = broadband.get("max_speed_mbps")
    if speed is not None:
        if speed >= 1000:
            score += 2.5
        elif speed >= 100:
            score += 1.5
        elif speed >= 10:
            score += 0.5
    count += 1

    # EV charging nearby: 2.5 points
    ev = enrichment_data.get("ev_charging", {})
    if ev.get("ev_stations_nearby", 0) > 0:
        score += 2.5
    count += 1

    # District heating: 2.5 points
    thermal = enrichment_data.get("thermal_networks", {})
    if thermal.get("has_district_heating"):
        score += 2.5
    count += 1

    return round(score, 1)


def compute_environmental_risk_score(enrichment_data: dict[str, Any]) -> float:
    """Compute environmental risk score (0-10, 10=safest).

    Combines flood, seismic, contamination, radon, noise (road+rail+air).
    Pure function — no API calls.
    """
    penalties = 0.0

    # Flood risk: 0-2 penalty
    flood = enrichment_data.get("flood_zones", {})
    flood_level = str(flood.get("flood_danger_level", "")).lower()
    if "hoch" in flood_level or "erheblich" in flood_level or "high" in flood_level:
        penalties += 2.0
    elif "mittel" in flood_level or "medium" in flood_level:
        penalties += 1.0
    elif flood_level and "gering" not in flood_level and "low" not in flood_level:
        penalties += 0.5

    # Seismic: 0-2 penalty
    seismic = enrichment_data.get("seismic", {})
    zone = str(seismic.get("seismic_zone", "")).lower()
    if zone in ("3b", "3a"):
        penalties += 2.0
    elif zone == "2":
        penalties += 1.0
    elif zone == "1":
        penalties += 0.3

    # Contaminated site: 0-2 penalty
    contam = enrichment_data.get("contaminated_sites", {})
    if contam.get("is_contaminated"):
        penalties += 2.0

    # Radon: 0-2 penalty
    radon = enrichment_data.get("radon", {})
    radon_level = radon.get("radon_level", "low")
    if radon_level == "high":
        penalties += 2.0
    elif radon_level == "medium":
        penalties += 1.0

    # Noise (combined): 0-2 penalty
    noise = enrichment_data.get("noise", {})
    road_db = noise.get("road_noise_day_db", 0) or 0
    rail = enrichment_data.get("railway_noise", {})
    rail_db = rail.get("railway_noise_day_db", 0) or 0
    aircraft = enrichment_data.get("aircraft_noise", {})
    air_db = aircraft.get("aircraft_noise_db", 0) or 0
    max_noise = max(road_db, rail_db, air_db)
    if max_noise > 65:
        penalties += 2.0
    elif max_noise > 55:
        penalties += 1.0
    elif max_noise > 45:
        penalties += 0.5

    return round(max(0.0, 10.0 - penalties), 1)


def compute_livability_score(enrichment_data: dict[str, Any]) -> float:
    """Compute livability score (0-10) from transport, amenities, noise, connectivity.

    Pure function — no API calls.
    """
    scores: list[tuple[float, float]] = []  # (score, weight)

    # Transport quality: weight 3
    transport = enrichment_data.get("transport", {})
    tclass = transport.get("transport_quality_class", "").upper()
    _t_scores = {"A": 10.0, "B": 8.0, "C": 5.0, "D": 2.0}
    if tclass in _t_scores:
        scores.append((_t_scores[tclass], 3.0))

    # Amenities: weight 2
    amenities = enrichment_data.get("osm_amenities", {})
    total_am = amenities.get("total_amenities", 0)
    if total_am > 0:
        am_score = min(10.0, total_am / 5.0)  # 50+ amenities = 10
        scores.append((am_score, 2.0))

    # Noise (inverse): weight 2
    noise = enrichment_data.get("noise", {})
    road_db = noise.get("road_noise_day_db")
    if road_db is not None:
        if road_db < 45:
            scores.append((10.0, 2.0))
        elif road_db < 55:
            scores.append((7.0, 2.0))
        elif road_db < 65:
            scores.append((4.0, 2.0))
        else:
            scores.append((1.0, 2.0))

    # Connectivity: weight 1.5
    conn = enrichment_data.get("connectivity_score")
    if conn is not None:
        scores.append((float(conn), 1.5))

    # Nearest transport stop: weight 1.5
    stops = enrichment_data.get("nearest_stops", {})
    stop_dist = stops.get("nearest_stop_distance_m")
    if stop_dist is not None:
        if stop_dist < 200:
            scores.append((10.0, 1.5))
        elif stop_dist < 500:
            scores.append((7.0, 1.5))
        elif stop_dist < 1000:
            scores.append((4.0, 1.5))
        else:
            scores.append((2.0, 1.5))

    if not scores:
        return 5.0

    total_weight = sum(w for _, w in scores)
    weighted_sum = sum(s * w for s, w in scores)
    return round(weighted_sum / total_weight, 1)


def compute_renovation_potential(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Compute renovation potential from building characteristics + enrichment data.

    Pure function — no API calls.
    """
    score = 0.0
    actions: list[str] = []
    savings = 0

    year = building_data.get("construction_year")
    heating = str(building_data.get("heating_type", "") or building_data.get("heating_type_code", "") or "").lower()
    solar = enrichment_data.get("solar", {})
    subsidies = enrichment_data.get("subsidies", {})

    # Fossil heating → high potential
    oil_gas = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas", "7520", "7530", "7500", "7510")
    if any(ind in heating for ind in oil_gas):
        score += 3.0
        actions.append("Replace fossil heating with heat pump or district heating")
        savings += 3000

    # Old building envelope
    if year and year < 1990:
        score += 2.5
        actions.append("Insulate building envelope (facade, roof, basement)")
        savings += 2000
    elif year and year < 2000:
        score += 1.5
        actions.append("Evaluate envelope insulation potential")
        savings += 1000

    # Solar potential
    suitability = solar.get("suitability", "")
    if suitability == "high":
        score += 2.0
        actions.append("Install rooftop photovoltaic system")
        savings += 1500
    elif suitability == "medium":
        score += 1.0
        actions.append("Consider rooftop solar installation")
        savings += 800

    # Windows (pre-1990)
    if year and year < 1990:
        score += 1.5
        actions.append("Replace windows with triple-glazed Minergie-certified")
        savings += 800

    # Subsidy availability bonus
    subsidy_total = subsidies.get("total_estimated_chf", 0) if subsidies else 0
    if subsidy_total > 10000:
        score += 1.0
        actions.append(f"Apply for available subsidies (est. CHF {subsidy_total:,})")

    # District heating available
    thermal = enrichment_data.get("thermal_networks", {})
    if thermal.get("has_district_heating") and any(ind in heating for ind in oil_gas):
        score += 0.5
        actions.append("Connect to nearby district heating network")
        savings += 500

    score = min(10.0, score)

    return {
        "potential_score": round(score, 1),
        "recommended_actions": actions,
        "estimated_savings_chf_per_year": savings,
    }


def compute_overall_building_intelligence_score(all_data: dict[str, Any]) -> dict[str, Any]:
    """Compute overall building intelligence score (0-100, grade A-F).

    Weighted combination of all sub-scores.
    Pure function — no API calls.
    """
    sub_scores: dict[str, float] = {}
    weights = {
        "neighborhood": 2.0,
        "environmental_risk": 2.5,
        "connectivity": 1.5,
        "livability": 2.0,
        "renovation_potential": 1.0,
        "data_completeness": 1.0,
    }

    # Neighborhood score (0-10)
    ns = all_data.get("neighborhood_score")
    if ns is not None:
        sub_scores["neighborhood"] = float(ns)

    # Environmental risk (0-10)
    er = all_data.get("environmental_risk_score")
    if er is not None:
        sub_scores["environmental_risk"] = float(er)

    # Connectivity (0-10)
    cs = all_data.get("connectivity_score")
    if cs is not None:
        sub_scores["connectivity"] = float(cs)

    # Livability (0-10)
    ls = all_data.get("livability_score")
    if ls is not None:
        sub_scores["livability"] = float(ls)

    # Renovation potential (0-10)
    rp = all_data.get("renovation_potential", {})
    if isinstance(rp, dict) and rp.get("potential_score") is not None:
        sub_scores["renovation_potential"] = float(rp["potential_score"])

    # Data completeness: how many enrichment sources returned data
    _data_keys = [
        "radon",
        "natural_hazards",
        "noise",
        "solar",
        "heritage",
        "transport",
        "seismic",
        "water_protection",
        "railway_noise",
        "aircraft_noise",
        "building_zones",
        "contaminated_sites",
        "groundwater_zones",
        "flood_zones",
        "mobile_coverage",
        "broadband",
        "ev_charging",
        "thermal_networks",
        "osm_amenities",
        "nearest_stops",
        "climate",
    ]
    filled = sum(1 for k in _data_keys if all_data.get(k))
    completeness = min(10.0, filled / len(_data_keys) * 10.0)
    sub_scores["data_completeness"] = completeness

    if not sub_scores:
        return {"score_0_100": 0, "grade": "F", "strengths": [], "weaknesses": [], "top_actions": []}

    total_weight = sum(weights.get(k, 1.0) for k in sub_scores)
    weighted_sum = sum(sub_scores[k] * weights.get(k, 1.0) for k in sub_scores)
    score_10 = weighted_sum / total_weight
    score_100 = round(score_10 * 10)

    # Grade
    if score_100 >= 85:
        grade = "A"
    elif score_100 >= 70:
        grade = "B"
    elif score_100 >= 55:
        grade = "C"
    elif score_100 >= 40:
        grade = "D"
    elif score_100 >= 25:
        grade = "E"
    else:
        grade = "F"

    # Strengths and weaknesses
    strengths: list[str] = []
    weaknesses: list[str] = []
    for k, v in sub_scores.items():
        label = k.replace("_", " ").title()
        if v >= 7.0:
            strengths.append(f"{label}: {v:.1f}/10")
        elif v < 4.0:
            weaknesses.append(f"{label}: {v:.1f}/10")

    # Top actions from renovation potential
    top_actions: list[str] = []
    if isinstance(rp, dict):
        top_actions = rp.get("recommended_actions", [])[:3]

    return {
        "score_0_100": score_100,
        "grade": grade,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "top_actions": top_actions,
    }


# ---------------------------------------------------------------------------
# 5j. Neighborhood attractiveness score (pure computation)
# ---------------------------------------------------------------------------


def compute_neighborhood_score(enrichment_data: dict[str, Any]) -> float:
    """Compute a neighborhood attractiveness score (0-10) from enriched data.

    Weighted average of transport, noise, hazards, solar, with heritage bonus.
    Pure function — no API calls.
    """
    scores: dict[str, float] = {}
    weights: dict[str, float] = {
        "transport": 3.0,
        "noise": 2.0,
        "hazards": 2.5,
        "solar": 1.5,
    }

    # Transport quality: A=10, B=8, C=5, D=2
    transport = enrichment_data.get("transport", {})
    tclass = transport.get("transport_quality_class", "").upper() if transport else ""
    _transport_scores = {"A": 10.0, "B": 8.0, "C": 5.0, "D": 2.0}
    if tclass in _transport_scores:
        scores["transport"] = _transport_scores[tclass]

    # Noise: <45dB=10, 45-55=7, 55-65=4, >65=1
    noise = enrichment_data.get("noise", {})
    noise_db = noise.get("road_noise_day_db") if noise else None
    if noise_db is not None:
        if noise_db < 45:
            scores["noise"] = 10.0
        elif noise_db < 55:
            scores["noise"] = 7.0
        elif noise_db < 65:
            scores["noise"] = 4.0
        else:
            scores["noise"] = 1.0

    # Natural hazards: no risk=10, low=7, medium=4, high=1
    hazards = enrichment_data.get("natural_hazards", {})
    if hazards:
        risk_values = [
            hazards.get("flood_risk", "unknown"),
            hazards.get("landslide_risk", "unknown"),
            hazards.get("rockfall_risk", "unknown"),
        ]
        _risk_scores = {"unknown": 8.0, "keine": 10.0, "none": 10.0, "low": 7.0, "medium": 4.0, "high": 1.0}
        hazard_scores = []
        for rv in risk_values:
            rv_lower = str(rv).lower()
            for key, val in _risk_scores.items():
                if key in rv_lower:
                    hazard_scores.append(val)
                    break
            else:
                hazard_scores.append(8.0)  # unknown defaults to neutral
        scores["hazards"] = sum(hazard_scores) / len(hazard_scores) if hazard_scores else 8.0

    # Solar: high=10, medium=7, low=4
    solar = enrichment_data.get("solar", {})
    if solar:
        _solar_scores = {"high": 10.0, "medium": 7.0, "low": 4.0}
        suitability = solar.get("suitability", "")
        if suitability in _solar_scores:
            scores["solar"] = _solar_scores[suitability]

    if not scores:
        return 5.0  # neutral default

    total_weight = sum(weights.get(k, 1.0) for k in scores)
    weighted_sum = sum(scores[k] * weights.get(k, 1.0) for k in scores)
    base_score = weighted_sum / total_weight

    # Heritage bonus: protected = +2 (capped at 10)
    heritage = enrichment_data.get("heritage", {})
    if heritage and heritage.get("isos_protected"):
        base_score = min(10.0, base_score + 2.0)

    return round(base_score, 1)


# ---------------------------------------------------------------------------
# 5k. Predictive pollutant risk (pure computation)
# ---------------------------------------------------------------------------


def compute_pollutant_risk_prediction(building_data: dict[str, Any]) -> dict[str, Any]:
    """Predict pollutant probabilities based on building characteristics.

    Uses known correlations between construction era, building type,
    and pollutant presence in Swiss buildings.
    Pure function — no API calls.
    """
    year = building_data.get("construction_year")
    btype = str(building_data.get("building_type", "")).lower()
    floors = building_data.get("floors_above") or building_data.get("floors") or 0
    canton = str(building_data.get("canton", "")).upper()
    renovation_year = building_data.get("renovation_year")
    radon_level = building_data.get("radon_level", "low")

    result: dict[str, Any] = {
        "asbestos_probability": 0.0,
        "pcb_probability": 0.0,
        "lead_probability": 0.0,
        "hap_probability": 0.0,
        "radon_probability": 0.0,
        "overall_risk_score": 0.0,
        "risk_factors": [],
    }

    if year is None:
        result["risk_factors"].append("construction_year_unknown — cannot assess age-based risk")
        result["overall_risk_score"] = 0.5
        return result

    # Asbestos: peak usage 1960-1990 in Switzerland
    if year < 1990:
        base = 0.85 if btype in ("residential", "mixed", "") else 0.70
        if 1960 <= year <= 1980:
            base = min(1.0, base + 0.10)  # peak years
        # VD historically higher
        if canton in ("VD", "GE", "VS"):
            base = min(1.0, base + 0.05)
        result["asbestos_probability"] = round(base, 2)
        result["risk_factors"].append(f"construction_year={year} (pre-1990 asbestos era)")

    # PCB: primarily 1955-1975 (joints, condensateurs, peintures)
    if 1955 <= year <= 1975:
        result["pcb_probability"] = 0.60
        result["risk_factors"].append(f"construction_year={year} (PCB peak era 1955-1975)")
    elif year < 1985:
        result["pcb_probability"] = 0.30
        result["risk_factors"].append(f"construction_year={year} (late PCB era)")

    # Lead: pre-1960 paints
    if year < 1960:
        result["lead_probability"] = 0.70
        result["risk_factors"].append(f"construction_year={year} (pre-1960 lead paint era)")
    elif year < 1980:
        result["lead_probability"] = 0.30

    # HAP: pre-1991 etancheite in taller buildings
    if year < 1991 and floors > 3:
        result["hap_probability"] = 0.40
        result["risk_factors"].append(f"construction_year={year}, floors={floors} (HAP risk in waterproofing)")
    elif year < 1991:
        result["hap_probability"] = 0.20

    # Radon: based on radon data if available
    _radon_map = {"high": 0.70, "medium": 0.40, "low": 0.10}
    result["radon_probability"] = _radon_map.get(radon_level, 0.10)
    if radon_level in ("high", "medium"):
        result["risk_factors"].append(f"radon_level={radon_level}")

    # Renovation reduces probabilities
    if renovation_year and renovation_year > 2000:
        reduction = 0.30
        result["asbestos_probability"] = round(max(0, result["asbestos_probability"] - reduction), 2)
        result["pcb_probability"] = round(max(0, result["pcb_probability"] - reduction), 2)
        result["lead_probability"] = round(max(0, result["lead_probability"] - reduction), 2)
        result["hap_probability"] = round(max(0, result["hap_probability"] - reduction), 2)
        result["risk_factors"].append(f"renovation_year={renovation_year} (probabilities reduced)")

    # Overall risk score: weighted average
    weights = {"asbestos": 3.0, "pcb": 2.0, "lead": 2.0, "hap": 1.5, "radon": 1.5}
    total = (
        result["asbestos_probability"] * weights["asbestos"]
        + result["pcb_probability"] * weights["pcb"]
        + result["lead_probability"] * weights["lead"]
        + result["hap_probability"] * weights["hap"]
        + result["radon_probability"] * weights["radon"]
    )
    result["overall_risk_score"] = round(total / sum(weights.values()), 2)

    return result


# ---------------------------------------------------------------------------
# 5l. Accessibility assessment (pure computation, LHand)
# ---------------------------------------------------------------------------


def compute_accessibility_assessment(building_data: dict[str, Any]) -> dict[str, Any]:
    """Assess accessibility compliance based on LHand (Swiss disability law).

    Pure function — no API calls.
    """
    year = building_data.get("construction_year")
    floors = building_data.get("floors_above") or building_data.get("floors") or 0
    dwellings = building_data.get("dwellings") or 0
    renovation_year = building_data.get("renovation_year")
    has_elevator = building_data.get("has_elevator", False)

    requirements: list[str] = []
    recommendations: list[str] = []
    compliance_status = "unknown"

    post_2004 = year is not None and year >= 2004
    major_renovation = renovation_year is not None and renovation_year >= 2004

    if post_2004 and dwellings >= 8:
        compliance_status = "full_compliance_required"
        requirements.append("LHand Art. 3: buildings with 8+ dwellings built after 2004 must be fully accessible")
        requirements.append("Wheelchair-accessible entrance and common areas required")
        if floors > 1:
            requirements.append("Elevator required for multi-story accessible buildings")
    elif post_2004:
        compliance_status = "partial_compliance_required"
        requirements.append("LHand: new buildings must meet basic accessibility standards")
    elif major_renovation:
        compliance_status = "adaptation_required"
        requirements.append("LHand: major renovation triggers accessibility adaptation requirements")
        if dwellings >= 8:
            requirements.append("Adaptation to accessibility standards required for 8+ dwelling buildings")
    else:
        compliance_status = "no_legal_requirement"

    # Recommendations regardless of legal status
    if floors > 3 and not has_elevator:
        recommendations.append("Elevator recommended for buildings with more than 3 floors")
    if floors > 1 and not has_elevator:
        recommendations.append("Consider stairlift or platform lift for upper floors")
    if dwellings >= 4:
        recommendations.append("Consider accessible design for aging-in-place readiness")

    return {
        "compliance_status": compliance_status,
        "requirements": requirements,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 5m. Subsidy eligibility (pure computation)
# ---------------------------------------------------------------------------


def estimate_subsidy_eligibility(building_data: dict[str, Any]) -> dict[str, Any]:
    """Estimate subsidy eligibility based on Programme Batiments + cantonal programs.

    Pure function — no API calls.
    """
    year = building_data.get("construction_year")
    heating_type = str(
        building_data.get("heating_type", "") or building_data.get("heating_type_code", "") or ""
    ).lower()
    canton = str(building_data.get("canton", "")).upper()
    solar_suitability = building_data.get("solar_suitability", "")
    solar_kwh = building_data.get("solar_potential_kwh")
    asbestos_positive = building_data.get("asbestos_positive", False)
    surface_area = building_data.get("surface_area_m2") or 0

    eligible_programs: list[dict[str, Any]] = []

    # 1. Heating replacement (Programme Batiments)
    oil_gas_indicators = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas", "7520", "7530", "7500", "7510")
    if any(ind in heating_type for ind in oil_gas_indicators):
        amount = 10_000 if surface_area < 200 else 15_000
        eligible_programs.append(
            {
                "name": "Programme Batiments — Remplacement chauffage fossile",
                "estimated_amount_chf": amount,
                "requirements": [
                    "Remplacement du chauffage fossile par pompe a chaleur, bois, ou raccordement CAD",
                    "Batiment existant avec chauffage mazout ou gaz",
                ],
            }
        )

    # 2. Envelope insulation (Programme Batiments)
    if year and year < 2000:
        base_amount = int(surface_area * 40) if surface_area else 8_000
        amount = max(5_000, min(base_amount, 30_000))
        eligible_programs.append(
            {
                "name": "Programme Batiments — Isolation enveloppe",
                "estimated_amount_chf": amount,
                "requirements": [
                    "Batiment construit avant 2000",
                    "Isolation facade, toiture ou dalle sur sous-sol",
                    "Valeur U amelioree selon exigences cantonales",
                ],
            }
        )

    # 3. Solar installation
    if solar_suitability in ("high", "medium") or (solar_kwh and solar_kwh > 500):
        eligible_programs.append(
            {
                "name": "Pronovo — Installation photovoltaique (retribution unique)",
                "estimated_amount_chf": 3_000,
                "requirements": [
                    "Installation PV sur toiture existante",
                    "Puissance minimale 2 kWp",
                    "Raccordement au reseau confirme par GRD",
                ],
            }
        )

    # 4. Asbestos decontamination (VD cantonal)
    if asbestos_positive and canton == "VD":
        eligible_programs.append(
            {
                "name": "Canton de Vaud — Subvention desamiantage",
                "estimated_amount_chf": 5_000,
                "requirements": [
                    "Diagnostic amiante positif confirme",
                    "Travaux realises par entreprise certifiee SUVA",
                    "Batiment situe dans le canton de Vaud",
                ],
            }
        )

    # 5. Window replacement
    if year and year < 1990:
        eligible_programs.append(
            {
                "name": "Programme Batiments — Remplacement fenetres",
                "estimated_amount_chf": 5_000,
                "requirements": [
                    "Fenetres existantes simple ou double vitrage ancien",
                    "Remplacement par triple vitrage certifie Minergie",
                ],
            }
        )

    total = sum(p["estimated_amount_chf"] for p in eligible_programs)

    return {
        "eligible_programs": eligible_programs,
        "total_estimated_chf": total,
    }


# ---------------------------------------------------------------------------
# 5n. Component lifecycle prediction (pure computation)
# ---------------------------------------------------------------------------

COMPONENT_LIFESPANS: dict[str, int] = {
    "roof_flat": 25,
    "roof_pitched": 40,
    "facade_plaster": 35,
    "facade_curtain": 30,
    "windows_wood": 28,
    "windows_pvc": 33,
    "windows_alu": 35,
    "heating_oil": 22,
    "heating_gas": 20,
    "heating_heatpump": 20,
    "water_pipes": 45,
    "drainage": 50,
    "electrical": 35,
    "elevator": 28,
    "thermal_insulation": 40,
    "waterproofing": 25,
    "interior_finishes": 20,
    "ventilation": 20,
    "fire_protection": 30,
    "intercom_access": 20,
}

COMPONENT_NAMES_FR: dict[str, str] = {
    "roof_flat": "Toiture plate",
    "roof_pitched": "Toiture en pente",
    "facade_plaster": "Facade enduit",
    "facade_curtain": "Facade rideau",
    "windows_wood": "Fenetres bois",
    "windows_pvc": "Fenetres PVC",
    "windows_alu": "Fenetres aluminium",
    "heating_oil": "Chauffage mazout",
    "heating_gas": "Chauffage gaz",
    "heating_heatpump": "Pompe a chaleur",
    "water_pipes": "Conduites eau",
    "drainage": "Evacuation",
    "electrical": "Installation electrique",
    "elevator": "Ascenseur",
    "thermal_insulation": "Isolation thermique",
    "waterproofing": "Etancheite",
    "interior_finishes": "Finitions interieures",
    "ventilation": "Ventilation mecanique",
    "fire_protection": "Protection incendie",
    "intercom_access": "Interphone / controle d'acces",
}


def _component_status(lifespan_pct: float) -> str:
    """Return component status based on percentage of lifespan used."""
    if lifespan_pct < 0.20:
        return "new"
    if lifespan_pct < 0.50:
        return "good"
    if lifespan_pct < 0.75:
        return "aging"
    if lifespan_pct <= 1.0:
        return "end_of_life"
    return "overdue"


def _component_urgency(status: str, lifespan_pct: float) -> str:
    """Return urgency level from status."""
    if status == "overdue":
        return "critical" if lifespan_pct > 1.25 else "urgent"
    if status == "end_of_life":
        return "budget"
    if status == "aging":
        return "plan"
    return "none"


def compute_component_lifecycle(building_data: dict[str, Any]) -> dict[str, Any]:
    """Predict the state of each major building component.

    Based on construction_year + renovation_year + building_type.
    Pure function — no API calls.
    All estimates are indicative and should be confirmed by on-site inspection.
    """
    year = building_data.get("construction_year")
    renovation_year = building_data.get("renovation_year")
    current_year = datetime.now(UTC).year

    if year is None:
        return {
            "components": [
                {
                    "name": name,
                    "name_fr": COMPONENT_NAMES_FR[name],
                    "installed_year": None,
                    "expected_end_year": None,
                    "age_years": None,
                    "lifespan_pct": None,
                    "status": "unknown",
                    "urgency": "none",
                }
                for name in COMPONENT_LIFESPANS
            ],
            "critical_count": 0,
            "urgent_count": 0,
            "total_overdue_years": 0,
        }

    installed_year = renovation_year if renovation_year and renovation_year > year else year

    components: list[dict[str, Any]] = []
    critical_count = 0
    urgent_count = 0
    total_overdue_years = 0

    for name, lifespan in COMPONENT_LIFESPANS.items():
        expected_end = installed_year + lifespan
        age = current_year - installed_year
        pct = age / lifespan if lifespan > 0 else 0.0
        status = _component_status(pct)
        urgency = _component_urgency(status, pct)

        if urgency == "critical":
            critical_count += 1
        if urgency == "urgent":
            urgent_count += 1
        if status == "overdue":
            total_overdue_years += current_year - expected_end

        components.append(
            {
                "name": name,
                "name_fr": COMPONENT_NAMES_FR[name],
                "installed_year": installed_year,
                "expected_end_year": expected_end,
                "age_years": age,
                "lifespan_pct": round(pct, 2),
                "status": status,
                "urgency": urgency,
            }
        )

    return {
        "components": components,
        "critical_count": critical_count,
        "urgent_count": urgent_count,
        "total_overdue_years": total_overdue_years,
    }


# ---------------------------------------------------------------------------
# 5o. Renovation plan generator (pure computation)
# ---------------------------------------------------------------------------

RENOVATION_COSTS_CHF_M2: dict[str, float] = {
    "facade_insulation": 280,
    "roof_insulation": 200,
    "window_replacement": 1200,
    "heating_replacement": 350,
    "electrical_renovation": 80,
    "plumbing_renovation": 100,
    "elevator_replacement": 120_000,  # forfait
    "asbestos_removal": 100,
    "pcb_remediation": 80,
    "lead_paint_removal": 60,
    "waterproofing": 150,
    "fire_protection": 40,
    "accessibility": 50_000,  # forfait
}


def generate_renovation_plan(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Generate a 10-year renovation plan from component lifecycle + subsidies + costs.

    Pure function — no API calls.
    All cost estimates are indicative (estimation) and should be confirmed by professional quotes.
    """
    surface = building_data.get("surface_area_m2") or 200  # default 200m2
    current_year = datetime.now(UTC).year

    lifecycle = enrichment_data.get("component_lifecycle", {})
    components = lifecycle.get("components", [])
    pollutant_risk = enrichment_data.get("pollutant_risk", {})

    plan_items: list[dict[str, Any]] = []

    def _add_item(
        year_rec: int,
        component: str,
        desc_fr: str,
        cost_key: str,
        priority: str,
        *,
        is_forfait: bool = False,
        regulatory_trigger: str = "",
        subsidy_pct: float = 0.0,
    ) -> None:
        if is_forfait:
            cost = RENOVATION_COSTS_CHF_M2[cost_key]
        else:
            cost = int(RENOVATION_COSTS_CHF_M2[cost_key] * surface)
        subsidy = int(cost * subsidy_pct)
        plan_items.append(
            {
                "year_recommended": year_rec,
                "component": component,
                "work_description_fr": f"{desc_fr} (estimation)",
                "estimated_cost_chf": cost,
                "available_subsidy_chf": subsidy,
                "net_cost_chf": cost - subsidy,
                "priority": priority,
                "regulatory_trigger": regulatory_trigger,
            }
        )

    # --- Year 1-2: Urgent — critical/overdue + pollutant remediation ---
    for comp in components:
        if comp.get("urgency") in ("critical", "urgent"):
            name = comp["name"]
            name_fr = comp.get("name_fr", name)
            if "roof" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Remplacement {name_fr}",
                    "roof_insulation",
                    "critical",
                    subsidy_pct=0.15,
                )
            elif "facade" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Renovation {name_fr}",
                    "facade_insulation",
                    "critical",
                    subsidy_pct=0.20,
                    regulatory_trigger="MoPEC: isolation obligatoire si renovation > 10% de l'enveloppe",
                )
            elif "heating" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Remplacement {name_fr}",
                    "heating_replacement",
                    "critical",
                    subsidy_pct=0.25,
                    regulatory_trigger="OEne: remplacement obligatoire chauffage fossile",
                )
            elif "window" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Remplacement {name_fr}",
                    "window_replacement",
                    "critical",
                    subsidy_pct=0.10,
                )
            elif "elevator" in name:
                _add_item(
                    current_year + 2,
                    name,
                    f"Remplacement {name_fr}",
                    "elevator_replacement",
                    "critical",
                    is_forfait=True,
                )
            elif "electrical" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Renovation {name_fr}",
                    "electrical_renovation",
                    "critical",
                    regulatory_trigger="OIBT: mise en conformite obligatoire",
                )
            elif "water_pipes" in name or "drainage" in name:
                _add_item(
                    current_year + 2,
                    name,
                    f"Renovation {name_fr}",
                    "plumbing_renovation",
                    "high",
                )
            elif "waterproofing" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Refection {name_fr}",
                    "waterproofing",
                    "critical",
                )
            elif "fire_protection" in name:
                _add_item(
                    current_year + 1,
                    name,
                    f"Mise aux normes {name_fr}",
                    "fire_protection",
                    "critical",
                    regulatory_trigger="AEAI: conformite obligatoire",
                )

    # Pollutant remediation (Year 1-2)
    asbestos_prob = pollutant_risk.get("asbestos_probability", 0)
    pcb_prob = pollutant_risk.get("pcb_probability", 0)
    lead_prob = pollutant_risk.get("lead_probability", 0)

    if asbestos_prob > 0.5:
        _add_item(
            current_year + 1,
            "asbestos",
            "Desamiantage",
            "asbestos_removal",
            "critical",
            regulatory_trigger="OTConst Art. 60a: desamiantage obligatoire avant travaux",
        )
    if pcb_prob > 0.4:
        _add_item(
            current_year + 2,
            "pcb",
            "Assainissement PCB",
            "pcb_remediation",
            "high",
            regulatory_trigger="ORRChim Annexe 2.15: assainissement si > 50 mg/kg",
        )
    if lead_prob > 0.5:
        _add_item(
            current_year + 2,
            "lead",
            "Decapage peintures au plomb",
            "lead_paint_removal",
            "high",
            regulatory_trigger="ORRChim Annexe 2.18: assainissement si > 5000 mg/kg",
        )

    # --- Year 3-5: Important — end_of_life + energy ---
    for comp in components:
        if comp.get("urgency") == "budget":
            name = comp["name"]
            name_fr = comp.get("name_fr", name)
            year_rec = current_year + 4
            if "roof" in name:
                _add_item(year_rec, name, f"Renovation {name_fr}", "roof_insulation", "medium", subsidy_pct=0.15)
            elif "facade" in name:
                _add_item(year_rec, name, f"Renovation {name_fr}", "facade_insulation", "medium", subsidy_pct=0.20)
            elif "window" in name:
                _add_item(year_rec, name, f"Remplacement {name_fr}", "window_replacement", "medium", subsidy_pct=0.10)
            elif "heating" in name:
                _add_item(
                    current_year + 3,
                    name,
                    f"Remplacement {name_fr}",
                    "heating_replacement",
                    "medium",
                    subsidy_pct=0.25,
                )
            elif "electrical" in name:
                _add_item(year_rec, name, f"Renovation {name_fr}", "electrical_renovation", "medium")
            elif "waterproofing" in name:
                _add_item(year_rec, name, f"Refection {name_fr}", "waterproofing", "medium")

    # --- Year 6-10: Planned — aging components ---
    for comp in components:
        if comp.get("urgency") == "plan":
            name = comp["name"]
            name_fr = comp.get("name_fr", name)
            year_rec = current_year + 8
            if "roof" in name:
                _add_item(year_rec, name, f"Planification renovation {name_fr}", "roof_insulation", "low")
            elif "facade" in name:
                _add_item(year_rec, name, f"Planification renovation {name_fr}", "facade_insulation", "low")
            elif "window" in name:
                _add_item(year_rec, name, f"Planification remplacement {name_fr}", "window_replacement", "low")

    total_estimated = sum(i["estimated_cost_chf"] for i in plan_items)
    total_subsidy = sum(i["available_subsidy_chf"] for i in plan_items)
    total_net = total_estimated - total_subsidy
    critical_items = sum(1 for i in plan_items if i["priority"] == "critical")

    summary_parts: list[str] = []
    if critical_items:
        summary_parts.append(f"{critical_items} intervention(s) critique(s) a realiser sous 2 ans")
    if total_estimated:
        summary_parts.append(f"cout total estime: CHF {total_estimated:,.0f}")
    if total_subsidy:
        summary_parts.append(f"subventions estimees: CHF {total_subsidy:,.0f}")
    summary_fr = ". ".join(summary_parts) + "." if summary_parts else "Aucune renovation urgente identifiee."

    return {
        "plan_items": plan_items,
        "total_estimated_chf": total_estimated,
        "total_subsidy_chf": total_subsidy,
        "total_net_chf": total_net,
        "critical_items_count": critical_items,
        "summary_fr": summary_fr,
    }


# ---------------------------------------------------------------------------
# 5p. Regulatory compliance check (pure computation)
# ---------------------------------------------------------------------------


def _fire_safety_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """AEAI fire protection compliance check."""
    year = building_data.get("construction_year")
    floors = building_data.get("floors_above") or building_data.get("floors") or 0
    lifecycle = enrichment_data.get("component_lifecycle", {})
    comps = {c["name"]: c for c in lifecycle.get("components", [])}
    fire_comp = comps.get("fire_protection", {})

    if fire_comp.get("status") in ("overdue", "end_of_life"):
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Protection incendie en fin de vie ou depassee — verification obligatoire.",
            "action_required_fr": "Mandater un controle AEAI et planifier la mise aux normes.",
            "deadline": None,
            "confidence": "medium",
        }
    if year and year < 1985 and floors > 3:
        return {
            "status": "review_needed",
            "reason_fr": f"Batiment de {year}, {floors} etages — normes AEAI potentiellement non respectees.",
            "action_required_fr": "Verifier la conformite avec les prescriptions AEAI actuelles.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Aucun indicateur de non-conformite incendie detecte.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _electrical_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OIBT electrical installations check."""
    lifecycle = enrichment_data.get("component_lifecycle", {})
    comps = {c["name"]: c for c in lifecycle.get("components", [])}
    elec = comps.get("electrical", {})

    if elec.get("status") == "overdue":
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Installation electrique depassee — controle periodique probablement non conforme.",
            "action_required_fr": "Mandater un controle OIBT par un organisme agree.",
            "deadline": None,
            "confidence": "medium",
        }
    if elec.get("status") == "end_of_life":
        return {
            "status": "review_needed",
            "reason_fr": "Installation electrique en fin de vie — controle OIBT recommande.",
            "action_required_fr": "Planifier un controle OIBT.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Installation electrique dans sa duree de vie estimee.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _noise_protection_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OPB noise protection check."""
    noise = enrichment_data.get("noise", {})
    road_db = noise.get("road_noise_day_db", 0) or 0
    rail = enrichment_data.get("railway_noise", {})
    rail_db = rail.get("railway_noise_day_db", 0) or 0
    max_noise = max(road_db, rail_db)

    if max_noise > 65:
        return {
            "status": "likely_non_compliant",
            "reason_fr": f"Exposition au bruit elevee ({max_noise} dB) — depassement probable des VLI.",
            "action_required_fr": "Evaluer les mesures d'isolation phonique (fenetres, facade).",
            "deadline": None,
            "confidence": "medium",
        }
    if max_noise > 55:
        return {
            "status": "review_needed",
            "reason_fr": f"Exposition au bruit moderee ({max_noise} dB) — verification recommandee.",
            "action_required_fr": "Verifier la conformite avec les valeurs limites OPB.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Niveaux de bruit dans les limites OPB estimees.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _energy_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OEne energy ordinance check."""
    year = building_data.get("construction_year")
    heating = str(building_data.get("heating_type", "") or "").lower()
    oil_gas = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas")

    if any(ind in heating for ind in oil_gas) and year and year < 2000:
        return {
            "status": "likely_non_compliant",
            "reason_fr": f"Chauffage fossile dans un batiment de {year} — non conforme OEne/MoPEC.",
            "action_required_fr": "Planifier le remplacement du chauffage fossile par une energie renouvelable.",
            "deadline": None,
            "confidence": "medium",
        }
    if year and year < 1990:
        return {
            "status": "review_needed",
            "reason_fr": f"Batiment de {year} — performance energetique probablement insuffisante.",
            "action_required_fr": "Realiser un CECB pour evaluer la performance energetique.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Aucun indicateur de non-conformite energetique detecte.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _accessibility_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """LHand accessibility check."""
    acc = enrichment_data.get("accessibility", {})
    status = acc.get("compliance_status", "unknown")

    _status_map = {
        "full_compliance_required": (
            "review_needed",
            "LHand: conformite complete requise pour ce batiment.",
            "Verifier la conformite avec les exigences LHand.",
        ),
        "partial_compliance_required": (
            "review_needed",
            "LHand: conformite partielle requise.",
            "Verifier les exigences minimales d'accessibilite.",
        ),
        "adaptation_required": (
            "review_needed",
            "LHand: adaptation requise suite a renovation majeure.",
            "Evaluer les adaptations d'accessibilite necessaires.",
        ),
    }
    if status in _status_map:
        s, reason, action = _status_map[status]
        return {
            "status": s,
            "reason_fr": reason,
            "action_required_fr": action,
            "deadline": None,
            "confidence": "medium",
        }
    return {
        "status": "not_assessed",
        "reason_fr": "Pas d'obligation LHand identifiee pour ce batiment.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _hazardous_substances_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OTConst hazardous substances check."""
    pollutant_risk = enrichment_data.get("pollutant_risk", {})
    asbestos = pollutant_risk.get("asbestos_probability", 0)
    pcb = pollutant_risk.get("pcb_probability", 0)
    lead = pollutant_risk.get("lead_probability", 0)

    if asbestos > 0.6 or pcb > 0.5:
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Probabilite elevee de presence de substances dangereuses (amiante/PCB).",
            "action_required_fr": "Realiser un diagnostic substances dangereuses avant tout travaux.",
            "deadline": None,
            "confidence": "medium",
        }
    if asbestos > 0.3 or pcb > 0.2 or lead > 0.3:
        return {
            "status": "review_needed",
            "reason_fr": "Probabilite moderee de presence de polluants — verification recommandee.",
            "action_required_fr": "Planifier un diagnostic de polluants du batiment.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Probabilite faible de presence de substances dangereuses.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _air_protection_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """OPAM air protection check."""
    heating = str(building_data.get("heating_type", "") or "").lower()
    oil_indicators = ("oil", "mazout", "heizol")

    if any(ind in heating for ind in oil_indicators):
        return {
            "status": "review_needed",
            "reason_fr": "Chauffage au mazout — conformite OPAM a verifier (emissions).",
            "action_required_fr": "Verifier les emissions du systeme de chauffage.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Aucun indicateur de non-conformite OPAM detecte.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _water_protection_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """LEaux water protection check."""
    water = enrichment_data.get("water_protection", {})
    groundwater = enrichment_data.get("groundwater_zones", {})

    if water.get("in_protection_zone") or groundwater.get("in_protection_zone"):
        return {
            "status": "review_needed",
            "reason_fr": "Batiment en zone de protection des eaux — contraintes LEaux applicables.",
            "action_required_fr": "Verifier les restrictions applicables (stockage, evacuation, travaux).",
            "deadline": None,
            "confidence": "medium",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Pas en zone de protection des eaux identifiee.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _mopec_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """MoPEC cantonal energy prescriptions check."""
    year = building_data.get("construction_year")
    heating = str(building_data.get("heating_type", "") or "").lower()
    oil_gas = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas")

    if year and year < 2000 and any(ind in heating for ind in oil_gas):
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Chauffage fossile dans batiment ancien — objectifs MoPEC non atteints.",
            "action_required_fr": "Planifier la transition vers une source d'energie renouvelable.",
            "deadline": None,
            "confidence": "medium",
        }
    if year and year < 2010:
        return {
            "status": "review_needed",
            "reason_fr": f"Batiment de {year} — verifier la conformite aux prescriptions MoPEC cantonales.",
            "action_required_fr": "Realiser un audit energetique (CECB).",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Batiment recent — probablement conforme MoPEC.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


def _sia500_check(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """SIA 500 accessibility check."""
    year = building_data.get("construction_year")
    dwellings = building_data.get("dwellings") or 0
    has_elevator = building_data.get("has_elevator", False)
    floors = building_data.get("floors_above") or building_data.get("floors") or 0

    if year and year >= 2009 and dwellings >= 8 and not has_elevator and floors > 1:
        return {
            "status": "likely_non_compliant",
            "reason_fr": "Batiment post-2009 avec 8+ logements sans ascenseur — SIA 500 non respectee.",
            "action_required_fr": "Installer un ascenseur conforme SIA 500.",
            "deadline": None,
            "confidence": "medium",
        }
    if dwellings >= 8 and not has_elevator and floors > 2:
        return {
            "status": "review_needed",
            "reason_fr": "Batiment avec 8+ logements et 3+ etages sans ascenseur.",
            "action_required_fr": "Evaluer la faisabilite d'installation d'un ascenseur.",
            "deadline": None,
            "confidence": "low",
        }
    return {
        "status": "likely_compliant",
        "reason_fr": "Aucun indicateur de non-conformite SIA 500 detecte.",
        "action_required_fr": "",
        "deadline": None,
        "confidence": "low",
    }


_REGULATION_CHECKS: list[dict[str, Any]] = [
    {"code": "AEAI", "name": "Protection incendie", "check": _fire_safety_check},
    {"code": "OIBT", "name": "Installations electriques", "check": _electrical_check},
    {"code": "OPB", "name": "Protection contre le bruit", "check": _noise_protection_check},
    {"code": "OEne", "name": "Ordonnance sur l'energie", "check": _energy_check},
    {"code": "LHand", "name": "Egalite pour les handicapes", "check": _accessibility_check},
    {"code": "OTConst", "name": "Substances dangereuses", "check": _hazardous_substances_check},
    {"code": "OPAM", "name": "Protection de l'air", "check": _air_protection_check},
    {"code": "LEaux", "name": "Protection des eaux", "check": _water_protection_check},
    {"code": "MoPEC", "name": "Prescriptions energetiques", "check": _mopec_check},
    {"code": "SIA500", "name": "Accessibilite", "check": _sia500_check},
]


def compute_regulatory_compliance(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Check applicable Swiss regulations against building data.

    Pure function — no API calls.
    Results are indicative estimates — formal compliance requires professional assessment.
    """
    checks: list[dict[str, Any]] = []
    compliant_count = 0
    non_compliant_count = 0
    review_needed_count = 0

    for reg in _REGULATION_CHECKS:
        check_fn = reg["check"]
        result = check_fn(building_data, enrichment_data)
        entry = {
            "code": reg["code"],
            "name": reg["name"],
            "applicable": True,
            **result,
        }
        checks.append(entry)

        status = result.get("status", "not_assessed")
        if status in ("compliant", "likely_compliant"):
            compliant_count += 1
        elif status in ("non_compliant", "likely_non_compliant"):
            non_compliant_count += 1
        elif status == "review_needed":
            review_needed_count += 1

    if non_compliant_count > 0:
        overall_status = "action_required"
    elif review_needed_count > 0:
        overall_status = "review_recommended"
    else:
        overall_status = "satisfactory"

    parts: list[str] = []
    if non_compliant_count:
        parts.append(f"{non_compliant_count} non-conformite(s) probable(s)")
    if review_needed_count:
        parts.append(f"{review_needed_count} verification(s) recommandee(s)")
    if compliant_count:
        parts.append(f"{compliant_count} point(s) conformes")
    summary_fr = (
        "Bilan reglementaire (estimation): " + ", ".join(parts) + "." if parts else "Evaluation non disponible."
    )

    return {
        "checks": checks,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "review_needed_count": review_needed_count,
        "overall_status": overall_status,
        "summary_fr": summary_fr,
    }


# ---------------------------------------------------------------------------
# 5q. Financial impact estimator (pure computation)
# ---------------------------------------------------------------------------


def estimate_financial_impact(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Estimate the financial impact of the current building state.

    Pure function — no API calls.
    All figures are rough estimates for planning purposes only.
    """
    surface = building_data.get("surface_area_m2") or 200
    year = building_data.get("construction_year")
    heating = str(building_data.get("heating_type", "") or "").lower()
    current_year = datetime.now(UTC).year
    age = (current_year - year) if year else 30  # default assumption

    renovation_plan = enrichment_data.get("renovation_plan", {})
    total_reno_cost = renovation_plan.get("total_net_chf", 0)

    oil_gas = ("oil", "gas", "mazout", "gaz", "heizol", "erdgas")
    has_fossil = any(ind in heating for ind in oil_gas)

    # --- Cost of inaction per year ---
    # Energy waste: older buildings waste more
    energy_waste = 0.0
    if year and year < 1980:
        energy_waste = surface * 25  # CHF 25/m2/year excess energy cost
    elif year and year < 2000:
        energy_waste = surface * 15
    elif year and year < 2010:
        energy_waste = surface * 5

    # Maintenance overspend on aging systems
    maintenance_excess = 0.0
    lifecycle = enrichment_data.get("component_lifecycle", {})
    overdue_count = sum(1 for c in lifecycle.get("components", []) if c.get("status") == "overdue")
    maintenance_excess = overdue_count * 500  # CHF 500/year per overdue component

    # Depreciation acceleration
    depreciation = 0.0
    if age > 40:
        depreciation = surface * 10
    elif age > 25:
        depreciation = surface * 5

    cost_of_inaction = round(energy_waste + maintenance_excess + depreciation)

    # --- Renovation ROI ---
    energy_savings = 0.0
    if has_fossil and year and year < 2000:
        energy_savings = surface * 20  # CHF 20/m2/year with full renovation
    elif year and year < 2000:
        energy_savings = surface * 10
    elif year and year < 2010:
        energy_savings = surface * 5

    roi_years = round(total_reno_cost / energy_savings, 1) if energy_savings > 0 and total_reno_cost > 0 else 0.0

    # --- Property value impact ---
    value_increase_pct = 0.0
    if age > 40:
        value_increase_pct = 15.0
    elif age > 25:
        value_increase_pct = 10.0
    elif age > 15:
        value_increase_pct = 5.0

    # --- Insurance premium impact ---
    insurance_impact = 0.0
    if overdue_count > 5:
        insurance_impact = -1500  # premium reduction after renovation
    elif overdue_count > 2:
        insurance_impact = -800

    # --- CO2 reduction ---
    co2_reduction = 0.0
    if has_fossil:
        co2_reduction = round(surface * 0.025, 1)  # ~25 kg CO2/m2/year for fossil → renewable

    summary_parts: list[str] = []
    if cost_of_inaction > 0:
        summary_parts.append(f"Cout de l'inaction estime: CHF {cost_of_inaction:,.0f}/an")
    if energy_savings > 0:
        summary_parts.append(f"economies d'energie estimees: CHF {energy_savings:,.0f}/an")
    if roi_years > 0:
        summary_parts.append(f"retour sur investissement estime: {roi_years} ans")
    if co2_reduction > 0:
        summary_parts.append(f"reduction CO2 estimee: {co2_reduction} t/an")
    summary_fr = ". ".join(summary_parts) + "." if summary_parts else "Estimation financiere non disponible."

    return {
        "cost_of_inaction_chf_per_year": cost_of_inaction,
        "renovation_roi_years": roi_years,
        "value_increase_pct": value_increase_pct,
        "energy_savings_chf": round(energy_savings),
        "insurance_impact_chf": round(insurance_impact),
        "co2_reduction_tons": co2_reduction,
        "summary_fr": summary_fr,
    }


# ---------------------------------------------------------------------------
# 5r. Building narrative generator (pure computation)
# ---------------------------------------------------------------------------


def generate_building_narrative(building_data: dict[str, Any], enrichment_data: dict[str, Any]) -> dict[str, Any]:
    """Generate a template-based narrative in French from structured data.

    Pure function — no API calls, no LLM.
    """
    year = building_data.get("construction_year")
    address = building_data.get("address", "Adresse inconnue")
    city = building_data.get("city", "")
    canton = building_data.get("canton", "")
    floors = building_data.get("floors_above") or building_data.get("floors")
    surface = building_data.get("surface_area_m2")
    dwellings = building_data.get("dwellings")
    heating = building_data.get("heating_type", "")
    current_year = datetime.now(UTC).year

    sections: list[dict[str, str]] = []

    # 1. Identification
    location = f"{address}, {city}" if city else address
    if canton:
        location += f" ({canton})"
    id_body = f"Le batiment situe au {location}"
    if year:
        id_body += f" a ete construit en {year}, ce qui lui confere un age de {current_year - year} ans"
    id_body += "."
    sections.append({"title": "Identification et contexte", "body": id_body})

    # 2. Physical characteristics
    phys_parts: list[str] = []
    if floors:
        phys_parts.append(f"{floors} etage(s) hors sol")
    if surface:
        phys_parts.append(f"une surface estimee de {surface} m2")
    if dwellings:
        phys_parts.append(f"{dwellings} logement(s)")
    if phys_parts:
        phys_body = "L'immeuble comprend " + ", ".join(phys_parts) + "."
    else:
        phys_body = "Les caracteristiques physiques detaillees ne sont pas disponibles."
    sections.append({"title": "Caracteristiques physiques", "body": phys_body})

    # 3. Environmental context
    radon = enrichment_data.get("radon", {})
    noise = enrichment_data.get("noise", {})
    hazards = enrichment_data.get("natural_hazards", {})
    heritage = enrichment_data.get("heritage", {})
    env_parts: list[str] = []
    radon_level = radon.get("radon_level")
    if radon_level:
        _radon_fr = {"high": "eleve", "medium": "moyen", "low": "faible"}
        env_parts.append(f"risque radon {_radon_fr.get(radon_level, radon_level)}")
    road_db = noise.get("road_noise_day_db")
    if road_db:
        env_parts.append(f"bruit routier de {road_db} dB en journee")
    if hazards.get("flood_risk"):
        env_parts.append(f"risque d'inondation: {hazards['flood_risk']}")
    if heritage.get("isos_protected"):
        env_parts.append("site ISOS protege")
    if env_parts:
        env_body = "Contexte environnemental: " + ", ".join(env_parts) + "."
    else:
        env_body = "Les donnees environnementales detaillees ne sont pas disponibles."
    sections.append({"title": "Contexte environnemental", "body": env_body})

    # 4. Energy performance
    energy_parts: list[str] = []
    if heating:
        energy_parts.append(f"systeme de chauffage: {heating}")
    solar = enrichment_data.get("solar", {})
    if solar.get("suitability"):
        _solar_fr = {"high": "elevee", "medium": "moyenne", "low": "faible"}
        energy_parts.append(f"potentiel solaire {_solar_fr.get(solar['suitability'], solar['suitability'])}")
    thermal = enrichment_data.get("thermal_networks", {})
    if thermal.get("has_district_heating"):
        energy_parts.append("raccordement au chauffage a distance possible")
    if energy_parts:
        energy_body = "Performance energetique: " + ", ".join(energy_parts) + "."
    else:
        energy_body = "Les donnees de performance energetique ne sont pas disponibles."
    sections.append({"title": "Performance energetique", "body": energy_body})

    # 5. Pollutant risk
    pollutant_risk = enrichment_data.get("pollutant_risk", {})
    overall_risk = pollutant_risk.get("overall_risk_score", 0)
    if overall_risk > 0.5:
        poll_body = (
            f"Le score de risque polluant est de {overall_risk:.2f}/1.0, indiquant un risque eleve. "
            "Un diagnostic de substances dangereuses est fortement recommande avant tout travaux."
        )
    elif overall_risk > 0.2:
        poll_body = (
            f"Le score de risque polluant est de {overall_risk:.2f}/1.0, indiquant un risque modere. "
            "Un diagnostic preventif est recommande."
        )
    else:
        poll_body = "Le risque de presence de polluants est estime comme faible."
    sections.append({"title": "Evaluation des polluants", "body": poll_body})

    # 6. Regulatory compliance
    compliance = enrichment_data.get("regulatory_compliance", {})
    comp_summary = compliance.get("summary_fr")
    if comp_summary:
        reg_body = comp_summary
    else:
        reg_body = "L'evaluation reglementaire n'est pas disponible."
    sections.append({"title": "Conformite reglementaire", "body": reg_body})

    # 7. Renovation priorities
    reno_plan = enrichment_data.get("renovation_plan", {})
    reno_summary = reno_plan.get("summary_fr")
    if reno_summary:
        reno_body = reno_summary
    else:
        reno_body = "Aucune priorite de renovation identifiee."
    sections.append({"title": "Priorites de renovation", "body": reno_body})

    # 8. Financial outlook
    financial = enrichment_data.get("financial_impact", {})
    fin_summary = financial.get("summary_fr")
    if fin_summary:
        fin_body = fin_summary
    else:
        fin_body = "L'estimation financiere n'est pas disponible."
    sections.append({"title": "Perspectives financieres", "body": fin_body})

    # 9. Neighborhood quality
    ns = enrichment_data.get("neighborhood_score")
    if ns is not None:
        if ns >= 7:
            nb_body = f"Score de quartier: {ns}/10 — environnement de qualite superieure."
        elif ns >= 5:
            nb_body = f"Score de quartier: {ns}/10 — environnement de qualite moyenne."
        else:
            nb_body = f"Score de quartier: {ns}/10 — potentiel d'amelioration identifie."
    else:
        nb_body = "Le score de qualite du quartier n'est pas disponible."
    sections.append({"title": "Qualite du quartier", "body": nb_body})

    # Assemble full narrative
    narrative_parts: list[str] = []
    for section in sections:
        narrative_parts.append(f"{section['title']}\n{section['body']}")
    narrative_fr = "\n\n".join(narrative_parts)

    word_count = len(narrative_fr.split())

    return {
        "narrative_fr": narrative_fr,
        "sections": sections,
        "word_count": word_count,
    }


# ---------------------------------------------------------------------------
# 6. Main orchestrator — enrich single building
# ---------------------------------------------------------------------------


async def enrich_building(
    db: AsyncSession,
    building_id: UUID,
    *,
    skip_geocode: bool = False,
    skip_regbl: bool = False,
    skip_ai: bool = False,
    skip_cadastre: bool = False,
    skip_image: bool = False,
) -> EnrichmentResult:
    """Enrich a single building with all available data sources.

    1. Geocode if no lat/lon
    2. Fetch RegBL if EGID available
    3. Fetch EGRID if missing
    4. Get Swisstopo image URL
    5. Run AI enrichment
    6-13. Fetch geo.admin.ch layers (radon, hazards, noise, solar, heritage, transport, seismic, water)
    14. Compute neighborhood score
    15. Compute pollutant risk prediction
    16. Compute accessibility assessment
    17. Compute subsidy eligibility
    18-32. Fetch extended layers (rail/aircraft noise, zones, contamination, flood, mobile, broadband,
           EV, thermal, monuments, agriculture, forest, military, Seveso)
    33-34. Fetch OSM amenities + building details
    35. Compute climate data
    36. Fetch nearest transport stops
    37-41. Compute scores (connectivity, environmental risk, livability, renovation, overall intelligence)
    44-48. Component lifecycle, renovation plan, regulatory compliance, financial impact, narrative
    42. Persist + 43. Timeline event
    """
    from app.models.building import Building
    from app.models.event import Event

    result = EnrichmentResult(building_id=building_id)

    # Load building
    stmt = select(Building).where(Building.id == building_id)
    row = await db.execute(stmt)
    building = row.scalar_one_or_none()
    if building is None:
        result.errors.append("Building not found")
        return result

    fields_updated: list[str] = []
    enrichment_meta: dict[str, Any] = dict(building.source_metadata_json or {}) if building.source_metadata_json else {}
    source_entries: list[dict[str, Any]] = []
    geocode_quality: str | None = None
    egid_confidence: str | None = None

    # --- Step 1: Geocode (always re-geocode to get precise coords + EGID) ---
    if not skip_geocode:
        geo = await geocode_address(building.address, building.postal_code, getattr(building, "city", "") or "")
        # Collect source entry
        if geo.get("_source_entry"):
            source_entries.append(geo["_source_entry"])

        match_quality = geo.get("match_quality", "no_match")
        geocode_quality = match_quality

        # Only update coordinates if match is exact or partial
        if geo.get("lat") and geo.get("lon") and match_quality in ("exact", "partial"):
            building.latitude = geo["lat"]
            building.longitude = geo["lon"]
            fields_updated.extend(["latitude", "longitude"])
            result.geocoded = True
            enrichment_meta["geocoded_at"] = datetime.now(UTC).isoformat()
            enrichment_meta["geocode_source"] = "geo.admin.ch"
            enrichment_meta["geocode_match_quality"] = match_quality

            # If geocoding found an EGID and building has none
            if geo.get("egid") and building.egid is None:
                building.egid = geo["egid"]
                fields_updated.append("egid")
        elif geo.get("lat") and match_quality in ("weak", "no_match"):
            logger.warning(
                "Skipping coordinate update for building %s: geocode match_quality=%s",
                building_id,
                match_quality,
            )
            result.errors.append(f"Geocode match_quality={match_quality} — coordinates not updated")
    else:
        source_entries.append(_source_entry("geocode", status="skipped", confidence="low"))

    # --- Step 2: RegBL ---
    if not skip_regbl and building.egid is not None:
        regbl = await fetch_regbl_data(building.egid, building.address or "")
        if regbl.get("_source_entry"):
            source_entries.append(regbl["_source_entry"])

        egid_confidence = regbl.get("egid_confidence")

        # Only populate fields if we have actual data (not just _source_entry)
        has_regbl_data = any(k for k in regbl if not k.startswith("_") and k != "egid_confidence")
        if has_regbl_data:
            result.regbl_found = True
            enrichment_meta["regbl_at"] = datetime.now(UTC).isoformat()
            enrichment_meta["egid_confidence"] = egid_confidence

            if regbl.get("construction_year") and building.construction_year is None:
                building.construction_year = int(regbl["construction_year"])
                fields_updated.append("construction_year")
            if regbl.get("floors") and building.floors_above is None:
                building.floors_above = int(regbl["floors"])
                fields_updated.append("floors_above")
            if regbl.get("renovation_year") and building.renovation_year is None:
                building.renovation_year = int(regbl["renovation_year"])
                fields_updated.append("renovation_year")
            if regbl.get("living_area_m2") and building.surface_area_m2 is None:
                building.surface_area_m2 = float(regbl["living_area_m2"])
                fields_updated.append("surface_area_m2")

            # EGRID from RegBL (often more reliable than cadastre lookup)
            if regbl.get("egrid") and building.egrid is None:
                building.egrid = regbl["egrid"]
                fields_updated.append("egid")
                result.egrid_found = True
            # Parcel number
            if regbl.get("parcel_number") and building.parcel_number is None:
                building.parcel_number = regbl["parcel_number"]
                fields_updated.append("parcel_number")
            # Ground area
            if regbl.get("ground_area_m2") and building.surface_area_m2 is None:
                building.surface_area_m2 = float(regbl["ground_area_m2"])
                fields_updated.append("surface_area_m2")

            # Don't overwrite building.egid if egid_confidence is unverified
            # (already set above, just log warning)
            if egid_confidence == "unverified":
                result.errors.append("EGID address mismatch — confidence=unverified")

            # Store full RegBL data in metadata (dwelling details, heating codes, etc.)
            # Exclude internal keys
            regbl_clean = {k: v for k, v in regbl.items() if not k.startswith("_")}
            enrichment_meta["regbl_data"] = regbl_clean
    elif not skip_regbl:
        source_entries.append(_source_entry("regbl", status="skipped", confidence="low", error="no EGID"))
    else:
        source_entries.append(_source_entry("regbl", status="skipped", confidence="low"))

    # --- Step 3: Cadastre EGRID ---
    if not skip_cadastre and building.egrid is None and building.latitude and building.longitude:
        cadastre = await fetch_cadastre_egrid(building.latitude, building.longitude)
        if cadastre.get("egrid"):
            building.egrid = cadastre["egrid"]
            fields_updated.append("egrid")
            result.egrid_found = True
            enrichment_meta["egrid_at"] = datetime.now(UTC).isoformat()
        if cadastre.get("parcel_number") and building.parcel_number is None:
            building.parcel_number = cadastre["parcel_number"]
            fields_updated.append("parcel_number")

    # --- Step 4: Swisstopo image ---
    if not skip_image and building.latitude and building.longitude:
        image_url = fetch_swisstopo_image_url(building.latitude, building.longitude)
        enrichment_meta["image_url"] = image_url
        result.image_url = image_url

    # --- Step 5: AI enrichment ---
    if not skip_ai:
        building_data = {
            "address": building.address,
            "postal_code": building.postal_code,
            "city": building.city,
            "canton": building.canton,
            "construction_year": building.construction_year,
            "building_type": building.building_type,
            "floors_above": building.floors_above,
            "surface_area_m2": building.surface_area_m2,
        }
        ai_result = await enrich_building_with_ai(building_data)
        if ai_result:
            enrichment_meta["ai_enrichment"] = ai_result
            enrichment_meta["ai_at"] = datetime.now(UTC).isoformat()
            result.ai_enriched = True
            fields_updated.append("ai_enrichment")

    has_coords = building.latitude is not None and building.longitude is not None

    # --- Step 6: Radon risk ---
    if has_coords:
        radon = await fetch_radon_risk(building.latitude, building.longitude)
        if radon:
            enrichment_meta["radon"] = radon
            result.radon_fetched = True
            fields_updated.append("radon")

    # --- Step 7: Natural hazards ---
    if has_coords:
        hazards = await fetch_natural_hazards(building.latitude, building.longitude)
        if hazards:
            enrichment_meta["natural_hazards"] = hazards
            result.natural_hazards_fetched = True
            fields_updated.append("natural_hazards")

    # --- Step 8: Noise ---
    if has_coords:
        noise = await fetch_noise_data(building.latitude, building.longitude)
        if noise:
            enrichment_meta["noise"] = noise
            result.noise_fetched = True
            fields_updated.append("noise")

    # --- Step 9: Solar potential ---
    if has_coords:
        solar = await fetch_solar_potential(building.latitude, building.longitude)
        if solar:
            enrichment_meta["solar"] = solar
            result.solar_fetched = True
            fields_updated.append("solar")

    # --- Step 10: Heritage / ISOS ---
    if has_coords:
        heritage = await fetch_heritage_status(building.latitude, building.longitude)
        if heritage:
            enrichment_meta["heritage"] = heritage
            result.heritage_fetched = True
            fields_updated.append("heritage")

    # --- Step 11: Transport quality ---
    if has_coords:
        transport = await fetch_transport_quality(building.latitude, building.longitude)
        if transport:
            enrichment_meta["transport"] = transport
            result.transport_fetched = True
            fields_updated.append("transport")

    # --- Step 12: Seismic zone ---
    if has_coords:
        seismic = await fetch_seismic_zone(building.latitude, building.longitude)
        if seismic:
            enrichment_meta["seismic"] = seismic
            result.seismic_fetched = True
            fields_updated.append("seismic")

    # --- Step 13: Water protection ---
    if has_coords:
        water = await fetch_water_protection(building.latitude, building.longitude)
        if water:
            enrichment_meta["water_protection"] = water
            result.water_protection_fetched = True
            fields_updated.append("water_protection")

    # --- Step 14: Neighborhood score (pure computation) ---
    n_score = compute_neighborhood_score(enrichment_meta)
    enrichment_meta["neighborhood_score"] = n_score
    result.neighborhood_score = n_score
    fields_updated.append("neighborhood_score")

    # --- Step 15: Pollutant risk prediction (pure computation) ---
    risk_input: dict[str, Any] = {
        "construction_year": building.construction_year,
        "building_type": building.building_type,
        "floors_above": building.floors_above,
        "canton": building.canton,
        "renovation_year": building.renovation_year,
        "radon_level": enrichment_meta.get("radon", {}).get("radon_level", "low"),
    }
    pollutant_risk = compute_pollutant_risk_prediction(risk_input)
    enrichment_meta["pollutant_risk"] = pollutant_risk
    result.pollutant_risk_computed = True
    fields_updated.append("pollutant_risk")

    # --- Step 16: Accessibility assessment (pure computation) ---
    accessibility_input: dict[str, Any] = {
        "construction_year": building.construction_year,
        "floors_above": building.floors_above,
        "dwellings": enrichment_meta.get("regbl_data", {}).get("dwellings"),
        "renovation_year": building.renovation_year,
    }
    accessibility = compute_accessibility_assessment(accessibility_input)
    enrichment_meta["accessibility"] = accessibility
    result.accessibility_computed = True
    fields_updated.append("accessibility")

    # --- Step 17: Subsidy eligibility (pure computation) ---
    subsidy_input: dict[str, Any] = {
        "construction_year": building.construction_year,
        "heating_type_code": enrichment_meta.get("regbl_data", {}).get("heating_type_code"),
        "canton": building.canton,
        "solar_suitability": enrichment_meta.get("solar", {}).get("suitability"),
        "solar_potential_kwh": enrichment_meta.get("solar", {}).get("solar_potential_kwh"),
        "surface_area_m2": building.surface_area_m2,
    }
    subsidies = estimate_subsidy_eligibility(subsidy_input)
    enrichment_meta["subsidies"] = subsidies
    result.subsidies_computed = True
    fields_updated.append("subsidies")

    # --- Step 18: Railway noise ---
    if has_coords:
        rail_noise = await fetch_railway_noise(building.latitude, building.longitude)
        if rail_noise:
            enrichment_meta["railway_noise"] = rail_noise
            result.railway_noise_fetched = True
            fields_updated.append("railway_noise")

    # --- Step 19: Aircraft noise ---
    if has_coords:
        air_noise = await fetch_aircraft_noise(building.latitude, building.longitude)
        if air_noise:
            enrichment_meta["aircraft_noise"] = air_noise
            result.aircraft_noise_fetched = True
            fields_updated.append("aircraft_noise")

    # --- Step 20: Building zones ---
    if has_coords:
        zones = await fetch_building_zones(building.latitude, building.longitude)
        if zones:
            enrichment_meta["building_zones"] = zones
            result.building_zones_fetched = True
            fields_updated.append("building_zones")

    # --- Step 21: Contaminated sites ---
    if has_coords:
        contam = await fetch_contaminated_sites(building.latitude, building.longitude)
        if contam:
            enrichment_meta["contaminated_sites"] = contam
            result.contaminated_sites_fetched = True
            fields_updated.append("contaminated_sites")

    # --- Step 22: Groundwater zones ---
    if has_coords:
        gw = await fetch_groundwater_zones(building.latitude, building.longitude)
        if gw:
            enrichment_meta["groundwater_zones"] = gw
            result.groundwater_zones_fetched = True
            fields_updated.append("groundwater_zones")

    # --- Step 23: Flood zones ---
    if has_coords:
        flood = await fetch_flood_zones(building.latitude, building.longitude)
        if flood:
            enrichment_meta["flood_zones"] = flood
            result.flood_zones_fetched = True
            fields_updated.append("flood_zones")

    # --- Step 24: Mobile coverage ---
    if has_coords:
        mobile = await fetch_mobile_coverage(building.latitude, building.longitude)
        if mobile:
            enrichment_meta["mobile_coverage"] = mobile
            result.mobile_coverage_fetched = True
            fields_updated.append("mobile_coverage")

    # --- Step 25: Broadband ---
    if has_coords:
        bb = await fetch_broadband(building.latitude, building.longitude)
        if bb:
            enrichment_meta["broadband"] = bb
            result.broadband_fetched = True
            fields_updated.append("broadband")

    # --- Step 26: EV charging ---
    if has_coords:
        ev = await fetch_ev_charging(building.latitude, building.longitude)
        if ev:
            enrichment_meta["ev_charging"] = ev
            result.ev_charging_fetched = True
            fields_updated.append("ev_charging")

    # --- Step 27: Thermal networks ---
    if has_coords:
        thermal = await fetch_thermal_networks(building.latitude, building.longitude)
        if thermal:
            enrichment_meta["thermal_networks"] = thermal
            result.thermal_networks_fetched = True
            fields_updated.append("thermal_networks")

    # --- Step 28: Protected monuments ---
    if has_coords:
        monuments = await fetch_protected_monuments(building.latitude, building.longitude)
        if monuments:
            enrichment_meta["protected_monuments"] = monuments
            result.protected_monuments_fetched = True
            fields_updated.append("protected_monuments")

    # --- Step 29: Agricultural zones ---
    if has_coords:
        agri = await fetch_agricultural_zones(building.latitude, building.longitude)
        if agri:
            enrichment_meta["agricultural_zones"] = agri
            result.agricultural_zones_fetched = True
            fields_updated.append("agricultural_zones")

    # --- Step 30: Forest reserves ---
    if has_coords:
        forest = await fetch_forest_reserves(building.latitude, building.longitude)
        if forest:
            enrichment_meta["forest_reserves"] = forest
            result.forest_reserves_fetched = True
            fields_updated.append("forest_reserves")

    # --- Step 31: Military zones ---
    if has_coords:
        military = await fetch_military_zones(building.latitude, building.longitude)
        if military:
            enrichment_meta["military_zones"] = military
            result.military_zones_fetched = True
            fields_updated.append("military_zones")

    # --- Step 32: Accident (Seveso) sites ---
    if has_coords:
        seveso = await fetch_accident_sites(building.latitude, building.longitude)
        if seveso:
            enrichment_meta["accident_sites"] = seveso
            result.accident_sites_fetched = True
            fields_updated.append("accident_sites")

    # --- Step 33: OSM amenities ---
    if has_coords:
        amenities = await fetch_osm_amenities(building.latitude, building.longitude)
        if amenities:
            enrichment_meta["osm_amenities"] = amenities
            result.osm_amenities_fetched = True
            fields_updated.append("osm_amenities")

    # --- Step 34: OSM building details ---
    if has_coords:
        osm_bld = await fetch_osm_building_details(building.latitude, building.longitude)
        if osm_bld:
            enrichment_meta["osm_building"] = osm_bld
            result.osm_building_fetched = True
            fields_updated.append("osm_building")

    # --- Step 35: Climate data (pure) ---
    if has_coords:
        climate = fetch_climate_data(building.latitude, building.longitude)
        if climate:
            enrichment_meta["climate"] = climate
            result.climate_computed = True
            fields_updated.append("climate")

    # --- Step 36: Nearest stops ---
    if has_coords:
        stops = await fetch_nearest_stops(building.latitude, building.longitude)
        if stops:
            enrichment_meta["nearest_stops"] = stops
            result.nearest_stops_fetched = True
            fields_updated.append("nearest_stops")

    # --- Step 37: Connectivity score (pure) ---
    conn_score = compute_connectivity_score(enrichment_meta)
    enrichment_meta["connectivity_score"] = conn_score
    result.connectivity_score = conn_score
    fields_updated.append("connectivity_score")

    # --- Step 38: Environmental risk score (pure) ---
    env_score = compute_environmental_risk_score(enrichment_meta)
    enrichment_meta["environmental_risk_score"] = env_score
    result.environmental_risk_score = env_score
    fields_updated.append("environmental_risk_score")

    # --- Step 39: Livability score (pure) ---
    liv_score = compute_livability_score(enrichment_meta)
    enrichment_meta["livability_score"] = liv_score
    result.livability_score = liv_score
    fields_updated.append("livability_score")

    # --- Step 40: Renovation potential (pure) ---
    reno_input: dict[str, Any] = {
        "construction_year": building.construction_year,
        "heating_type_code": enrichment_meta.get("regbl_data", {}).get("heating_type_code"),
        "canton": building.canton,
    }
    reno = compute_renovation_potential(reno_input, enrichment_meta)
    enrichment_meta["renovation_potential"] = reno
    result.renovation_potential_computed = True
    fields_updated.append("renovation_potential")

    # --- Step 41: Overall intelligence score (pure) ---
    overall = compute_overall_building_intelligence_score(enrichment_meta)
    enrichment_meta["overall_intelligence"] = overall
    result.overall_intelligence_computed = True
    result.overall_intelligence_score = overall.get("score_0_100")
    result.overall_intelligence_grade = overall.get("grade")
    fields_updated.append("overall_intelligence")

    # --- Step 44: Component lifecycle prediction (pure) ---
    lifecycle_input: dict[str, Any] = {
        "construction_year": building.construction_year,
        "renovation_year": getattr(building, "renovation_year", None),
        "building_type": getattr(building, "building_type", None),
    }
    lifecycle = compute_component_lifecycle(lifecycle_input)
    enrichment_meta["component_lifecycle"] = lifecycle
    result.component_lifecycle_computed = True
    fields_updated.append("component_lifecycle")

    # --- Step 45: Renovation plan (pure) ---
    reno_plan_input: dict[str, Any] = {
        "construction_year": building.construction_year,
        "surface_area_m2": getattr(building, "surface_area_m2", None),
    }
    reno_plan = generate_renovation_plan(reno_plan_input, enrichment_meta)
    enrichment_meta["renovation_plan"] = reno_plan
    result.renovation_plan_computed = True
    fields_updated.append("renovation_plan")

    # --- Step 46: Regulatory compliance (pure) ---
    compliance_input: dict[str, Any] = {
        "construction_year": building.construction_year,
        "floors_above": getattr(building, "floors_above", None),
        "floors": getattr(building, "floors_above", None),
        "dwellings": getattr(building, "dwellings", None),
        "has_elevator": getattr(building, "has_elevator", False),
        "heating_type": enrichment_meta.get("regbl_data", {}).get("heating_type_code", ""),
        "canton": building.canton,
    }
    compliance = compute_regulatory_compliance(compliance_input, enrichment_meta)
    enrichment_meta["regulatory_compliance"] = compliance
    result.regulatory_compliance_computed = True
    fields_updated.append("regulatory_compliance")

    # --- Step 47: Financial impact (pure) ---
    financial_input: dict[str, Any] = {
        "construction_year": building.construction_year,
        "surface_area_m2": getattr(building, "surface_area_m2", None),
        "heating_type": enrichment_meta.get("regbl_data", {}).get("heating_type_code", ""),
    }
    financial = estimate_financial_impact(financial_input, enrichment_meta)
    enrichment_meta["financial_impact"] = financial
    result.financial_impact_computed = True
    fields_updated.append("financial_impact")

    # --- Step 48: Building narrative (pure) ---
    narrative_input: dict[str, Any] = {
        "construction_year": building.construction_year,
        "address": building.address,
        "city": getattr(building, "city", ""),
        "canton": building.canton,
        "floors_above": getattr(building, "floors_above", None),
        "surface_area_m2": getattr(building, "surface_area_m2", None),
        "dwellings": getattr(building, "dwellings", None),
        "heating_type": enrichment_meta.get("regbl_data", {}).get("heating_type_code", ""),
    }
    narrative = generate_building_narrative(narrative_input, enrichment_meta)
    enrichment_meta["building_narrative"] = narrative
    result.building_narrative_computed = True
    fields_updated.append("building_narrative")

    # --- Collect source entries from layer fetches ---
    # Extract _source_entry from enrichment_meta values that are dicts
    _layer_source_keys = [
        "radon",
        "natural_hazards",
        "noise",
        "solar",
        "heritage",
        "transport",
        "seismic",
        "water_protection",
        "railway_noise",
        "aircraft_noise",
        "building_zones",
        "contaminated_sites",
        "groundwater_zones",
        "flood_zones",
        "mobile_coverage",
        "broadband",
        "ev_charging",
        "thermal_networks",
        "protected_monuments",
        "agricultural_zones",
        "forest_reserves",
        "military_zones",
        "accident_sites",
        "osm_amenities",
        "osm_building",
        "nearest_stops",
    ]
    for key in _layer_source_keys:
        data = enrichment_meta.get(key)
        if isinstance(data, dict) and "_source_entry" in data:
            source_entries.append(data.pop("_source_entry"))

    # --- Enrichment quality summary ---
    quality = compute_enrichment_quality(
        source_entries,
        geocode_quality=geocode_quality,
        egid_confidence=egid_confidence,
    )
    enrichment_meta["enrichment_quality"] = quality
    enrichment_meta["source_entries"] = source_entries

    # --- Step 42: Persist ---
    if fields_updated or result.image_url:
        enrichment_meta["last_enriched_at"] = datetime.now(UTC).isoformat()
        building.source_metadata_json = enrichment_meta
        if "source_metadata_json" not in fields_updated:
            fields_updated.append("source_metadata_json")

    result.fields_updated = fields_updated

    # --- Step 43: Timeline event ---
    if fields_updated:
        event = Event(
            building_id=building_id,
            event_type="enrichment",
            date=date.today(),
            title="Auto-enrichment pipeline",
            description=f"Updated fields: {', '.join(fields_updated)}",
            metadata_json={
                "source": "building_enrichment_service",
                "fields_updated": fields_updated,
                "errors": result.errors,
                "enrichment_quality": quality,
            },
        )
        db.add(event)

    await db.flush()
    return result


# ---------------------------------------------------------------------------
# 7. Batch enrichment
# ---------------------------------------------------------------------------


async def enrich_all_buildings(
    db: AsyncSession,
    org_id: UUID | None = None,
    *,
    skip_geocode: bool = False,
    skip_regbl: bool = False,
    skip_ai: bool = False,
) -> list[EnrichmentResult]:
    """Enrich all buildings (or filtered by org).

    Throttles to 1 request/second to respect API limits.
    """
    from app.models.building import Building

    stmt = select(Building)
    if org_id:
        stmt = stmt.where(Building.organization_id == org_id)

    rows = await db.execute(stmt)
    buildings = rows.scalars().all()

    results: list[EnrichmentResult] = []
    for building in buildings:
        try:
            r = await enrich_building(
                db,
                building.id,
                skip_geocode=skip_geocode,
                skip_regbl=skip_regbl,
                skip_ai=skip_ai,
            )
            results.append(r)
        except Exception as exc:
            logger.error("Enrichment failed for building %s: %s", building.id, exc)
            results.append(
                EnrichmentResult(
                    building_id=building.id,
                    errors=[str(exc)],
                )
            )

    return results
