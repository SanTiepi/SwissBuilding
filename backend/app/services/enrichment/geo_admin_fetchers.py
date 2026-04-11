"""Fetchers that call geo.admin.ch APIs (identify, layers).

NOTE: functions that call ``_geo_identify``, ``_retry_request`` or ``_throttle``
resolve them through ``app.services.building_enrichment_service`` at call time
so that ``unittest.mock.patch`` on that module correctly intercepts the calls.
"""

from __future__ import annotations

import contextlib
import logging
import sys
from typing import Any

import httpx

from app.services.enrichment.http_helpers import _retry_request, _throttle
from app.services.enrichment.source_provenance import _source_entry


def _resolve(name: str, fallback: object) -> object:
    """Resolve *name* from the backward-compat shim module, falling back to *fallback*.

    This allows ``patch("app.services.building_enrichment_service.<name>")``
    to intercept calls made from this sub-module.
    """
    mod = sys.modules.get("app.services.building_enrichment_service")
    if mod is not None:
        return getattr(mod, name, fallback)
    return fallback


logger = logging.getLogger(__name__)

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
# Generic geo.admin.ch identify helper
# ---------------------------------------------------------------------------


async def _geo_identify(lat: float, lon: float, layer: str) -> dict[str, Any]:
    """Generic geo.admin.ch identify call for any layer.

    Returns attributes dict on success, or dict with only '_source_entry' key on failure.
    Handles:
    - 400 -> marks layer as unsupported, returns unavailable status
    - 200 empty -> normal (no data at location), returns empty dict
    - 500/502/503/504 -> retries once
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

    await _resolve("_throttle", _throttle)()
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
            resp, retry_count = await _resolve("_retry_request", _retry_request)(
                client, "GET", url, params=params, timeout=15.0
            )

            # 400 -> layer not supported by identify
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
# Individual layer fetchers
# ---------------------------------------------------------------------------


async def fetch_radon_risk(lat: float, lon: float) -> dict[str, Any]:
    """Fetch radon risk data from BAG radon map via geo.admin.ch.

    Returns dict with radon_zone, radon_probability, radon_level.
    Returns empty dict on failure.
    """
    await _resolve("_throttle", _throttle)()
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


async def fetch_natural_hazards(lat: float, lon: float) -> dict[str, Any]:
    """Fetch natural hazard data (flood, landslide, rockfall) via geo.admin.ch.

    Returns dict with flood_risk, landslide_risk, rockfall_risk.
    Returns empty dict on failure.
    """
    await _resolve("_throttle", _throttle)()
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


async def fetch_noise_data(lat: float, lon: float) -> dict[str, Any]:
    """Fetch road noise exposure data via geo.admin.ch.

    Returns dict with road_noise_day_db, noise_level.
    Returns empty dict on failure.
    """
    await _resolve("_throttle", _throttle)()
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


async def fetch_solar_potential(lat: float, lon: float) -> dict[str, Any]:
    """Fetch solar energy potential for rooftops via geo.admin.ch.

    Returns dict with solar_potential_kwh, roof_area_m2, suitability.
    Returns empty dict on failure.
    """
    await _resolve("_throttle", _throttle)()
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


async def fetch_heritage_status(lat: float, lon: float) -> dict[str, Any]:
    """Fetch heritage/ISOS protection status via geo.admin.ch.

    Returns dict with isos_protected, isos_category, site_name.
    Returns empty dict on failure.
    """
    await _resolve("_throttle", _throttle)()
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


async def fetch_transport_quality(lat: float, lon: float) -> dict[str, Any]:
    """Fetch public transport quality class via geo.admin.ch.

    Returns dict with transport_quality_class (A-D), description.
    Returns empty dict on failure.
    """
    await _resolve("_throttle", _throttle)()
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


async def fetch_seismic_zone(lat: float, lon: float) -> dict[str, Any]:
    """Fetch seismic zone classification via geo.admin.ch.

    Returns dict with seismic_zone, seismic_class.
    Returns empty dict on failure.
    """
    await _resolve("_throttle", _throttle)()
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


async def fetch_water_protection(lat: float, lon: float) -> dict[str, Any]:
    """Fetch groundwater protection zone via geo.admin.ch.

    Returns dict with protection_zone, zone_type.
    Returns empty dict on failure.
    """
    await _resolve("_throttle", _throttle)()
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


async def fetch_railway_noise(lat: float, lon: float) -> dict[str, Any]:
    """Fetch railway noise exposure (day) via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bafu.laerm-bahnlaerm_tag")
    if not attrs:
        return {}
    result: dict[str, Any] = {}
    db_val = attrs.get("lr_tag") or attrs.get("dblr") or attrs.get("db")
    if db_val is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["railway_noise_day_db"] = float(db_val)
    return result


async def fetch_aircraft_noise(lat: float, lon: float) -> dict[str, Any]:
    """Fetch aircraft noise from civil airfield noise cadastre via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bazl.laermbelastungskataster-zivilflugplaetze")
    if not attrs:
        return {}
    result: dict[str, Any] = {}
    db_val = attrs.get("lr_tag") or attrs.get("db") or attrs.get("lrpegel")
    if db_val is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["aircraft_noise_db"] = float(db_val)
    return result


async def fetch_building_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch building zone classification via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.are.bauzonen")
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


async def fetch_contaminated_sites(lat: float, lon: float) -> dict[str, Any]:
    """Fetch contaminated site (Altlasten) info via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bafu.altlasten-kataster")
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


async def fetch_groundwater_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch groundwater protection zone (S1/S2/S3) via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bafu.grundwasserschutzzonen")
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


async def fetch_flood_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch flood danger map data via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bafu.gefahrenkarte-hochwasser")
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


async def fetch_mobile_coverage(lat: float, lon: float) -> dict[str, Any]:
    """Fetch 5G mobile coverage via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bakom.mobilnetz-5g")
    return {"has_5g_coverage": bool(attrs)}


async def fetch_broadband(lat: float, lon: float) -> dict[str, Any]:
    """Fetch broadband technology info via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bakom.breitband-technologien")
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


async def fetch_ev_charging(lat: float, lon: float) -> dict[str, Any]:
    """Fetch EV charging station proximity via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bfe.ladestellen-elektromobilitaet")
    if not attrs:
        return {"ev_stations_nearby": 0}
    result: dict[str, Any] = {"ev_stations_nearby": 1}
    dist = attrs.get("distance") or attrs.get("entfernung")
    if dist is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["nearest_distance_m"] = float(dist)
    return result


async def fetch_thermal_networks(lat: float, lon: float) -> dict[str, Any]:
    """Fetch district heating / thermal network info via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bfe.thermische-netze")
    if not attrs:
        return {"has_district_heating": False}
    result: dict[str, Any] = {"has_district_heating": True}
    name = attrs.get("name") or attrs.get("bezeichnung") or attrs.get("netzname")
    if name is not None:
        result["network_name"] = str(name)
    return result


async def fetch_protected_monuments(lat: float, lon: float) -> dict[str, Any]:
    """Fetch listed monument status via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bak.bundesinventar-schuetzenswerte-denkmaler")
    if not attrs:
        return {"is_listed_monument": False}
    result: dict[str, Any] = {"is_listed_monument": True}
    cat = attrs.get("kategorie") or attrs.get("category") or attrs.get("klasse")
    if cat is not None:
        result["monument_category"] = str(cat)
    return result


async def fetch_agricultural_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch soil quality / agricultural zone info via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.blw.bodeneignungskarte")
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


async def fetch_forest_reserves(lat: float, lon: float) -> dict[str, Any]:
    """Fetch forest reserve status via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bafu.waldreservate")
    if not attrs:
        return {"in_forest_reserve": False}
    result: dict[str, Any] = {"in_forest_reserve": True}
    name = attrs.get("name") or attrs.get("bezeichnung") or attrs.get("reservatname")
    if name is not None:
        result["reserve_name"] = str(name)
    return result


async def fetch_military_zones(lat: float, lon: float) -> dict[str, Any]:
    """Fetch military shooting range proximity via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.vbs.schiessplaetze")
    if not attrs:
        return {"near_shooting_range": False}
    result: dict[str, Any] = {"near_shooting_range": True}
    dist = attrs.get("distance") or attrs.get("entfernung")
    if dist is not None:
        with contextlib.suppress(ValueError, TypeError):
            result["distance_m"] = float(dist)
    return result


async def fetch_accident_sites(lat: float, lon: float) -> dict[str, Any]:
    """Fetch Seveso / major accident site proximity via geo.admin.ch."""
    attrs = await _resolve("_geo_identify", _geo_identify)(lat, lon, "ch.bafu.stoerfallverordnung")
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
