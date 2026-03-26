"""Building auto-enrichment pipeline — Swiss public APIs + AI.

Fills building records with data from geo.admin.ch, RegBL/GWR,
Swisstopo, cadastre, and optionally AI-generated descriptions.
All external calls use httpx with graceful error handling.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import os
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
# 1. Geocode via geo.admin.ch
# ---------------------------------------------------------------------------


async def geocode_address(address: str, npa: str) -> dict[str, Any]:
    """Geocode a Swiss address using geo.admin.ch search API.

    Returns dict with keys: lat, lon, egid, label, detail.
    Returns empty dict on failure.
    """
    await _throttle()
    search_text = f"{address} {npa}".strip()
    url = "https://api3.geo.admin.ch/rest/services/api/SearchServer"
    params = {
        "searchText": search_text,
        "type": "locations",
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

        return result

    except Exception as exc:
        logger.warning("Geocoding failed for '%s %s': %s", address, npa, exc)
        return {}


# ---------------------------------------------------------------------------
# 2. RegBL / GWR data
# ---------------------------------------------------------------------------


async def fetch_regbl_data(egid: int) -> dict[str, Any]:
    """Fetch building data from the Swiss Register of Buildings via geo.admin.ch.

    Uses the GWR layer on geo.admin.ch which returns comprehensive building data
    including EGRID, parcel number, construction year, floors, dwellings, surface,
    heating type, energy source, and individual dwelling details.

    Returns dict with construction_year, floors, dwellings, etc.
    Returns empty dict on 404 or error.
    """
    await _throttle()
    url = f"https://api3.geo.admin.ch/rest/services/ech/MapServer/ch.bfs.gebaeude_wohnungs_register/{egid}_0"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                logger.info("RegBL: EGID %d not found (404)", egid)
                return {}
            resp.raise_for_status()
            data = resp.json()

        # geo.admin.ch wraps data in feature.attributes
        attrs = data
        if isinstance(data, dict) and "feature" in data:
            attrs = data["feature"].get("attributes", data)
        if not isinstance(attrs, dict):
            return {}

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

        # Dwelling details
        if attrs.get("warea") and isinstance(attrs["warea"], list):
            result["dwelling_areas_m2"] = attrs["warea"]
            result["dwelling_rooms"] = attrs.get("wazim", [])
            result["dwelling_floors"] = attrs.get("wstwk", [])

        # Heating update date
        if attrs.get("gwaerdath1"):
            result["heating_updated_at"] = attrs["gwaerdath1"]

        return result

    except Exception as exc:
        logger.warning("RegBL fetch failed for EGID %d: %s", egid, exc)
        return {}


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
    """Generic geo.admin.ch identify call for any layer."""
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
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results", [])
        if results:
            return results[0].get("attributes", results[0].get("properties", {}))
        return {}
    except Exception as exc:
        logger.warning("geo.admin.ch identify failed for layer %s: %s", layer, exc)
        return {}


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
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
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
        return result

    except Exception as exc:
        logger.warning("Overpass amenities fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


# ---------------------------------------------------------------------------
# 5i-18. OSM building details via Overpass API
# ---------------------------------------------------------------------------


async def fetch_osm_building_details(lat: float, lon: float) -> dict[str, Any]:
    """Fetch building footprint details from OSM via Overpass."""
    await _throttle()
    query = f"[out:json][timeout:15];(way[building](around:30,{lat},{lon}););out body 1;"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
            )
            resp.raise_for_status()
            data = resp.json()

        elements = data.get("elements", [])
        if not elements:
            return {}

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
        return result

    except Exception as exc:
        logger.warning("Overpass building details fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


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
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        stations = data.get("stations", [])
        if not stations:
            return {}

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
        return result

    except Exception as exc:
        logger.warning("Transport stops fetch failed for (%s, %s): %s", lat, lon, exc)
        return {}


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

    # --- Step 1: Geocode (always re-geocode to get precise coords + EGID) ---
    if not skip_geocode:
        geo = await geocode_address(building.address, building.postal_code)
        if geo.get("lat") and geo.get("lon"):
            building.latitude = geo["lat"]
            building.longitude = geo["lon"]
            fields_updated.extend(["latitude", "longitude"])
            result.geocoded = True
            enrichment_meta["geocoded_at"] = datetime.now(UTC).isoformat()
            enrichment_meta["geocode_source"] = "geo.admin.ch"

            # If geocoding found an EGID and building has none
            if geo.get("egid") and building.egid is None:
                building.egid = geo["egid"]
                fields_updated.append("egid")

    # --- Step 2: RegBL ---
    if not skip_regbl and building.egid is not None:
        regbl = await fetch_regbl_data(building.egid)
        if regbl:
            result.regbl_found = True
            enrichment_meta["regbl_at"] = datetime.now(UTC).isoformat()

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
                fields_updated.append("egrid")
                result.egrid_found = True
            # Parcel number
            if regbl.get("parcel_number") and building.parcel_number is None:
                building.parcel_number = regbl["parcel_number"]
                fields_updated.append("parcel_number")
            # Ground area
            if regbl.get("ground_area_m2") and building.surface_area_m2 is None:
                building.surface_area_m2 = float(regbl["ground_area_m2"])
                fields_updated.append("surface_area_m2")

            # Store full RegBL data in metadata (dwelling details, heating codes, etc.)
            enrichment_meta["regbl_data"] = regbl

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
