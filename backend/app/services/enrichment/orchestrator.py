"""Main enrichment orchestrator — geocode, RegBL, cadastre, swisstopo, AI, and full pipeline."""

from __future__ import annotations

import contextlib
import json
import logging
import math
import os
import sys
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.enrichment import EnrichmentResult
from app.services.enrichment.address_utils import (
    _normalize_address,
    verify_egid_address,
    verify_geocode_match,
)
from app.services.enrichment.financial_estimator import estimate_financial_impact
from app.services.enrichment.geo_admin_fetchers import (
    fetch_accident_sites,
    fetch_agricultural_zones,
    fetch_aircraft_noise,
    fetch_broadband,
    fetch_building_zones,
    fetch_contaminated_sites,
    fetch_ev_charging,
    fetch_flood_zones,
    fetch_forest_reserves,
    fetch_groundwater_zones,
    fetch_heritage_status,
    fetch_military_zones,
    fetch_mobile_coverage,
    fetch_natural_hazards,
    fetch_noise_data,
    fetch_protected_monuments,
    fetch_radon_risk,
    fetch_railway_noise,
    fetch_seismic_zone,
    fetch_solar_potential,
    fetch_thermal_networks,
    fetch_transport_quality,
    fetch_water_protection,
)
from app.services.enrichment.http_helpers import _retry_request, _throttle
from app.services.enrichment.narrative_generator import generate_building_narrative
from app.services.enrichment.osm_fetchers import (
    fetch_climate_data,
    fetch_nearest_stops,
    fetch_osm_amenities,
    fetch_osm_building_details,
)
from app.services.enrichment.regulatory_checks import compute_regulatory_compliance
from app.services.enrichment.renovation_planner import generate_renovation_plan
from app.services.enrichment.score_computers import (
    compute_accessibility_assessment,
    compute_component_lifecycle,
    compute_connectivity_score,
    compute_environmental_risk_score,
    compute_geo_risk_score,
    compute_livability_score,
    compute_neighborhood_score,
    compute_overall_building_intelligence_score,
    compute_pollutant_risk_prediction,
    compute_renovation_potential,
    estimate_subsidy_eligibility,
)
from app.services.enrichment.source_provenance import (
    _source_entry,
    compute_enrichment_quality,
)
from app.services.spatial_enrichment_service import SpatialEnrichmentService

logger = logging.getLogger(__name__)


def _resolve(name: str, fallback: object) -> object:
    """Resolve *name* from the backward-compat shim module."""
    mod = sys.modules.get("app.services.building_enrichment_service")
    if mod is not None:
        return getattr(mod, name, fallback)
    return fallback


# ---------------------------------------------------------------------------
# 1. Geocode via geo.admin.ch
# ---------------------------------------------------------------------------


async def geocode_address(address: str, npa: str, city: str = "") -> dict[str, Any]:
    """Geocode a Swiss address using geo.admin.ch search API.

    Returns dict with keys: lat, lon, egid, label, detail, match_quality,
    _source_entry (per-source metadata).
    Returns empty dict on failure.
    """
    await _resolve("_throttle", _throttle)()
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
            resp, retry_count = await _resolve("_retry_request", _retry_request)(
                client, "GET", url, params=params, timeout=15.0
            )
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

        # EGID (featureId format is "884846_0" -- take part before underscore)
        if "featureId" in attrs:
            with contextlib.suppress(ValueError, TypeError):
                fid = str(attrs["featureId"]).split("_")[0]
                result["egid"] = int(fid)

        result["label"] = attrs.get("label", "")
        result["detail"] = attrs.get("detail", "")

        # Extract GWR feature URL from links array (canonical chain)
        links = results[0].get("links", [])
        for link in links:
            href = link.get("href", "")
            if "ch.bfs.gebaeude_wohnungs_register" in href:
                result["gwr_feature_url"] = href
                break

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


async def fetch_regbl_data(
    egid: int,
    building_address: str = "",
    *,
    gwr_feature_url: str | None = None,
) -> dict[str, Any]:
    """Fetch building data from the Swiss Register of Buildings via geo.admin.ch.

    Uses the GWR layer on geo.admin.ch which returns comprehensive building data
    including EGRID, parcel number, construction year, floors, dwellings, surface,
    heating type, energy source, and individual dwelling details.

    If ``gwr_feature_url`` is provided (from SearchServer canonical chain), fetch
    directly from that URL -- no guessing needed.  Otherwise, fall back to the
    ``{egid}_0`` pattern.

    Returns dict with construction_year, floors, dwellings, egid_confidence, etc.
    Returns empty dict on 404 or error.
    """
    await _resolve("_throttle", _throttle)()
    if gwr_feature_url:
        # Canonical chain: URL from SearchServer links array
        url = f"https://api3.geo.admin.ch{gwr_feature_url}"
    else:
        # Fallback: construct URL from EGID
        url = f"https://api3.geo.admin.ch/rest/services/ech/MapServer/ch.bfs.gebaeude_wohnungs_register/{egid}_0"
    retry_count = 0
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp, retry_count = await _resolve("_retry_request", _retry_request)(client, "GET", url, timeout=15.0)
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
    await _resolve("_throttle", _throttle)()
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
# 5. AI enrichment (Claude / OpenAI -- graceful if no key)
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
    await _resolve("_throttle", _throttle)()
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
    await _resolve("_throttle", _throttle)()
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
# 5b. Populate ClimateExposureProfile from enrichment_meta
# ---------------------------------------------------------------------------


def _compute_moisture_stress(precipitation_mm: float | None) -> str:
    """Derive moisture stress from annual precipitation."""
    if precipitation_mm is None:
        return "unknown"
    if precipitation_mm > 1500:
        return "high"
    if precipitation_mm > 1000:
        return "moderate"
    return "low"


def _compute_thermal_stress(freeze_thaw_cycles: int | None) -> str:
    """Derive thermal stress from freeze-thaw cycle count."""
    if freeze_thaw_cycles is None:
        return "unknown"
    if freeze_thaw_cycles > 100:
        return "high"
    if freeze_thaw_cycles > 60:
        return "moderate"
    return "low"


def _compute_uv_exposure(altitude_m: float | None) -> str:
    """Derive UV exposure from altitude."""
    if altitude_m is None:
        return "unknown"
    if altitude_m > 1500:
        return "high"
    if altitude_m > 800:
        return "moderate"
    return "low"


def _build_natural_hazard_zones(hazards: dict[str, Any]) -> list[dict[str, str]] | None:
    """Convert natural_hazards dict to list-of-dicts for JSON column."""
    if not hazards:
        return None
    zones: list[dict[str, str]] = []
    for hazard_type in ("flood", "landslide", "rockfall"):
        level = hazards.get(f"{hazard_type}_risk")
        if level and level != "unknown":
            zones.append({"type": hazard_type, "level": str(level)})
    return zones or None


async def populate_climate_exposure_profile(
    db: AsyncSession,
    building_id: UUID,
    enrichment_meta: dict[str, Any],
) -> None:
    """Create or update a ClimateExposureProfile from enrichment pipeline data.

    Maps enrichment_meta keys (climate, radon, noise, natural_hazards, solar,
    heritage, water_protection, contaminated_sites) to structured model fields
    and computes stress indicators.

    This function is idempotent — safe to call multiple times for the same building.
    """
    from app.models.climate_exposure import ClimateExposureProfile

    climate = enrichment_meta.get("climate") or {}
    radon = enrichment_meta.get("radon") or {}
    noise = enrichment_meta.get("noise") or {}
    hazards = enrichment_meta.get("natural_hazards") or {}
    solar = enrichment_meta.get("solar") or {}
    heritage = enrichment_meta.get("heritage") or {}
    water = enrichment_meta.get("water_protection") or {}
    contam = enrichment_meta.get("contaminated_sites") or {}
    rail_noise = enrichment_meta.get("railway_noise") or {}

    # --- Extract values with graceful None handling ---
    altitude_m: float | None = None
    with contextlib.suppress(ValueError, TypeError):
        raw_alt = climate.get("estimated_altitude_m")
        if raw_alt is not None:
            altitude_m = float(raw_alt)

    heating_degree_days: float | None = None
    with contextlib.suppress(ValueError, TypeError):
        raw_hdd = climate.get("heating_degree_days")
        if raw_hdd is not None:
            heating_degree_days = float(raw_hdd)

    precipitation_mm: float | None = None
    with contextlib.suppress(ValueError, TypeError):
        raw_precip = climate.get("precipitation_mm")
        if raw_precip is not None:
            precipitation_mm = float(raw_precip)

    freeze_thaw: int | None = None
    with contextlib.suppress(ValueError, TypeError):
        raw_frost = climate.get("frost_days")
        if raw_frost is not None:
            freeze_thaw = int(raw_frost)

    noise_day_db: float | None = None
    with contextlib.suppress(ValueError, TypeError):
        raw_noise = noise.get("road_noise_day_db")
        if raw_noise is not None:
            noise_day_db = float(raw_noise)

    # Night noise: enrichment pipeline only fetches day road noise.
    # Use railway noise as supplementary night indicator if available.
    noise_night_db: float | None = None
    with contextlib.suppress(ValueError, TypeError):
        raw_rail = rail_noise.get("railway_noise_day_db")
        if raw_rail is not None:
            noise_night_db = float(raw_rail)

    solar_kwh: float | None = None
    with contextlib.suppress(ValueError, TypeError):
        raw_solar = solar.get("solar_potential_kwh")
        if raw_solar is not None:
            solar_kwh = float(raw_solar)

    radon_zone = radon.get("radon_zone")
    if radon_zone is not None:
        radon_zone = str(radon_zone)

    hazard_zones = _build_natural_hazard_zones(hazards)

    groundwater_zone: str | None = None
    zone_val = water.get("protection_zone") or water.get("zone_type")
    if zone_val is not None:
        groundwater_zone = str(zone_val)

    contaminated: bool | None = contam.get("is_contaminated") if contam else None

    heritage_status: str | None = None
    if heritage.get("isos_protected"):
        heritage_status = heritage.get("isos_category") or heritage.get("site_name") or "protected"

    wind_exposure: str | None = None
    if altitude_m is not None:
        if altitude_m > 1500:
            wind_exposure = "exposed"
        elif altitude_m > 800:
            wind_exposure = "moderate"
        else:
            wind_exposure = "sheltered"

    # --- Stress indicators ---
    moisture_stress = _compute_moisture_stress(precipitation_mm)
    thermal_stress = _compute_thermal_stress(freeze_thaw)
    uv_exposure = _compute_uv_exposure(altitude_m)

    # --- Data sources ---
    now = datetime.now(UTC)
    data_sources: list[dict[str, str]] = []
    if climate:
        data_sources.append({"source": "enrichment/climate", "fetched_at": now.isoformat()})
    if radon:
        data_sources.append({"source": "geo.admin/radon", "fetched_at": now.isoformat()})
    if noise:
        data_sources.append({"source": "geo.admin/noise", "fetched_at": now.isoformat()})
    if hazards:
        data_sources.append({"source": "geo.admin/natural_hazards", "fetched_at": now.isoformat()})
    if solar:
        data_sources.append({"source": "geo.admin/solar", "fetched_at": now.isoformat()})
    if heritage:
        data_sources.append({"source": "geo.admin/heritage", "fetched_at": now.isoformat()})
    if water:
        data_sources.append({"source": "geo.admin/water_protection", "fetched_at": now.isoformat()})
    if contam:
        data_sources.append({"source": "geo.admin/contaminated_sites", "fetched_at": now.isoformat()})

    # --- Upsert profile ---
    existing = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building_id))
    profile = existing.scalar_one_or_none()

    if profile is None:
        profile = ClimateExposureProfile(building_id=building_id)
        db.add(profile)

    profile.radon_zone = radon_zone
    profile.noise_exposure_day_db = noise_day_db
    profile.noise_exposure_night_db = noise_night_db
    profile.solar_potential_kwh = solar_kwh
    profile.natural_hazard_zones = hazard_zones
    profile.groundwater_zone = groundwater_zone
    profile.contaminated_site = contaminated
    profile.heritage_status = heritage_status

    profile.heating_degree_days = heating_degree_days
    profile.avg_annual_precipitation_mm = precipitation_mm
    profile.freeze_thaw_cycles_per_year = freeze_thaw
    profile.wind_exposure = wind_exposure
    profile.altitude_m = altitude_m

    profile.moisture_stress = moisture_stress
    profile.thermal_stress = thermal_stress
    profile.uv_exposure = uv_exposure

    profile.data_sources = data_sources
    profile.last_updated = now

    await db.flush()


# ---------------------------------------------------------------------------
# 6. Main orchestrator -- enrich single building
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
    geo: dict[str, Any] = {}  # geocode result, used by RegBL canonical chain

    # --- Step 1: Geocode (always re-geocode to get precise coords + EGID) ---
    if not skip_geocode:
        geo = await _resolve("geocode_address", geocode_address)(
            building.address, building.postal_code, getattr(building, "city", "") or ""
        )
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
        # Prefer canonical chain: use gwr_feature_url from geocode if available
        regbl = await _resolve("fetch_regbl_data", fetch_regbl_data)(
            building.egid,
            building.address or "",
            gwr_feature_url=geo.get("gwr_feature_url"),
        )
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
        cadastre = await _resolve("fetch_cadastre_egrid", fetch_cadastre_egrid)(building.latitude, building.longitude)
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
        ai_result = await _resolve("enrich_building_with_ai", enrich_building_with_ai)(building_data)
        if ai_result:
            enrichment_meta["ai_enrichment"] = ai_result
            enrichment_meta["ai_at"] = datetime.now(UTC).isoformat()
            result.ai_enriched = True
            fields_updated.append("ai_enrichment")

    has_coords = building.latitude is not None and building.longitude is not None

    # --- Step 5b: swissBUILDINGS3D spatial data ---
    if has_coords:
        try:
            spatial = await SpatialEnrichmentService.fetch_building_footprint(building.longitude, building.latitude)
            if spatial and "error" not in spatial:
                enrichment_meta["building_height_m"] = spatial.get("height_m")
                enrichment_meta["building_volume_m3"] = spatial.get("volume_m3")
                enrichment_meta["floor_count_3d"] = spatial.get("floors")
                enrichment_meta["roof_type"] = spatial.get("roof_type")
                enrichment_meta["footprint_area_m2"] = spatial.get("surface_m2")
                enrichment_meta["spatial_source"] = spatial.get("source")
                enrichment_meta["spatial_fetched_at"] = spatial.get("fetched_at")
                # Persist to first-class Building columns
                if spatial.get("footprint_wkt") and not building.footprint_wkt:
                    building.footprint_wkt = spatial["footprint_wkt"]
                if spatial.get("height_m") and not building.building_height:
                    building.building_height = spatial["height_m"]
                if spatial.get("roof_type") and not building.roof_type:
                    building.roof_type = spatial["roof_type"]
                if spatial.get("floors") and not building.floor_count_3d:
                    building.floor_count_3d = spatial["floors"]
                result.spatial_fetched = True
                fields_updated.append("spatial_3d")
        except Exception as exc:
            logger.warning("swissBUILDINGS3D fetch failed for building %s: %s", building_id, exc)

    # --- Step 6: Radon risk ---
    if has_coords:
        try:
            radon = await _resolve("fetch_radon_risk", fetch_radon_risk)(building.latitude, building.longitude)
            if radon:
                enrichment_meta["radon"] = radon
                result.radon_fetched = True
                fields_updated.append("radon")
        except Exception as exc:
            logger.warning("Fetcher fetch_radon_risk failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_radon_risk failed: {exc}")

    # --- Step 7: Natural hazards ---
    if has_coords:
        try:
            hazards = await _resolve("fetch_natural_hazards", fetch_natural_hazards)(
                building.latitude, building.longitude
            )
            if hazards:
                enrichment_meta["natural_hazards"] = hazards
                result.natural_hazards_fetched = True
                fields_updated.append("natural_hazards")
        except Exception as exc:
            logger.warning("Fetcher fetch_natural_hazards failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_natural_hazards failed: {exc}")

    # --- Step 8: Noise ---
    if has_coords:
        try:
            noise = await _resolve("fetch_noise_data", fetch_noise_data)(building.latitude, building.longitude)
            if noise:
                enrichment_meta["noise"] = noise
                result.noise_fetched = True
                fields_updated.append("noise")
        except Exception as exc:
            logger.warning("Fetcher fetch_noise_data failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_noise_data failed: {exc}")

    # --- Step 9: Solar potential ---
    if has_coords:
        try:
            solar = await _resolve("fetch_solar_potential", fetch_solar_potential)(
                building.latitude, building.longitude
            )
            if solar:
                enrichment_meta["solar"] = solar
                result.solar_fetched = True
                fields_updated.append("solar")
        except Exception as exc:
            logger.warning("Fetcher fetch_solar_potential failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_solar_potential failed: {exc}")

    # --- Step 10: Heritage / ISOS ---
    if has_coords:
        try:
            heritage = await _resolve("fetch_heritage_status", fetch_heritage_status)(
                building.latitude, building.longitude
            )
            if heritage:
                enrichment_meta["heritage"] = heritage
                result.heritage_fetched = True
                fields_updated.append("heritage")
        except Exception as exc:
            logger.warning("Fetcher fetch_heritage_status failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_heritage_status failed: {exc}")

    # --- Step 11: Transport quality ---
    if has_coords:
        try:
            transport = await _resolve("fetch_transport_quality", fetch_transport_quality)(
                building.latitude, building.longitude
            )
            if transport:
                enrichment_meta["transport"] = transport
                result.transport_fetched = True
                fields_updated.append("transport")
        except Exception as exc:
            logger.warning("Fetcher fetch_transport_quality failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_transport_quality failed: {exc}")

    # --- Step 12: Seismic zone ---
    if has_coords:
        try:
            seismic = await _resolve("fetch_seismic_zone", fetch_seismic_zone)(building.latitude, building.longitude)
            if seismic:
                enrichment_meta["seismic"] = seismic
                result.seismic_fetched = True
                fields_updated.append("seismic")
        except Exception as exc:
            logger.warning("Fetcher fetch_seismic_zone failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_seismic_zone failed: {exc}")

    # --- Step 13: Water protection ---
    if has_coords:
        try:
            water = await _resolve("fetch_water_protection", fetch_water_protection)(
                building.latitude, building.longitude
            )
            if water:
                enrichment_meta["water_protection"] = water
                result.water_protection_fetched = True
                fields_updated.append("water_protection")
        except Exception as exc:
            logger.warning("Fetcher fetch_water_protection failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_water_protection failed: {exc}")

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
        try:
            rail_noise = await _resolve("fetch_railway_noise", fetch_railway_noise)(
                building.latitude, building.longitude
            )
            if rail_noise:
                enrichment_meta["railway_noise"] = rail_noise
                result.railway_noise_fetched = True
                fields_updated.append("railway_noise")
        except Exception as exc:
            logger.warning("Fetcher fetch_railway_noise failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_railway_noise failed: {exc}")

    # --- Step 19: Aircraft noise ---
    if has_coords:
        try:
            air_noise = await _resolve("fetch_aircraft_noise", fetch_aircraft_noise)(
                building.latitude, building.longitude
            )
            if air_noise:
                enrichment_meta["aircraft_noise"] = air_noise
                result.aircraft_noise_fetched = True
                fields_updated.append("aircraft_noise")
        except Exception as exc:
            logger.warning("Fetcher fetch_aircraft_noise failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_aircraft_noise failed: {exc}")

    # --- Step 20: Building zones ---
    if has_coords:
        try:
            zones = await _resolve("fetch_building_zones", fetch_building_zones)(building.latitude, building.longitude)
            if zones:
                enrichment_meta["building_zones"] = zones
                result.building_zones_fetched = True
                fields_updated.append("building_zones")
        except Exception as exc:
            logger.warning("Fetcher fetch_building_zones failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_building_zones failed: {exc}")

    # --- Step 21: Contaminated sites ---
    if has_coords:
        try:
            contam = await _resolve("fetch_contaminated_sites", fetch_contaminated_sites)(
                building.latitude, building.longitude
            )
            if contam:
                enrichment_meta["contaminated_sites"] = contam
                result.contaminated_sites_fetched = True
                fields_updated.append("contaminated_sites")
        except Exception as exc:
            logger.warning("Fetcher fetch_contaminated_sites failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_contaminated_sites failed: {exc}")

    # --- Step 22: Groundwater zones ---
    if has_coords:
        try:
            gw = await _resolve("fetch_groundwater_zones", fetch_groundwater_zones)(
                building.latitude, building.longitude
            )
            if gw:
                enrichment_meta["groundwater_zones"] = gw
                result.groundwater_zones_fetched = True
                fields_updated.append("groundwater_zones")
        except Exception as exc:
            logger.warning("Fetcher fetch_groundwater_zones failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_groundwater_zones failed: {exc}")

    # --- Step 23: Flood zones ---
    if has_coords:
        try:
            flood = await _resolve("fetch_flood_zones", fetch_flood_zones)(building.latitude, building.longitude)
            if flood:
                enrichment_meta["flood_zones"] = flood
                result.flood_zones_fetched = True
                fields_updated.append("flood_zones")
        except Exception as exc:
            logger.warning("Fetcher fetch_flood_zones failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_flood_zones failed: {exc}")

    # --- Step 24: Mobile coverage ---
    if has_coords:
        try:
            mobile = await _resolve("fetch_mobile_coverage", fetch_mobile_coverage)(
                building.latitude, building.longitude
            )
            if mobile:
                enrichment_meta["mobile_coverage"] = mobile
                result.mobile_coverage_fetched = True
                fields_updated.append("mobile_coverage")
        except Exception as exc:
            logger.warning("Fetcher fetch_mobile_coverage failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_mobile_coverage failed: {exc}")

    # --- Step 25: Broadband ---
    if has_coords:
        try:
            bb = await _resolve("fetch_broadband", fetch_broadband)(building.latitude, building.longitude)
            if bb:
                enrichment_meta["broadband"] = bb
                result.broadband_fetched = True
                fields_updated.append("broadband")
        except Exception as exc:
            logger.warning("Fetcher fetch_broadband failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_broadband failed: {exc}")

    # --- Step 26: EV charging ---
    if has_coords:
        try:
            ev = await _resolve("fetch_ev_charging", fetch_ev_charging)(building.latitude, building.longitude)
            if ev:
                enrichment_meta["ev_charging"] = ev
                result.ev_charging_fetched = True
                fields_updated.append("ev_charging")
        except Exception as exc:
            logger.warning("Fetcher fetch_ev_charging failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_ev_charging failed: {exc}")

    # --- Step 27: Thermal networks ---
    if has_coords:
        try:
            thermal = await _resolve("fetch_thermal_networks", fetch_thermal_networks)(
                building.latitude, building.longitude
            )
            if thermal:
                enrichment_meta["thermal_networks"] = thermal
                result.thermal_networks_fetched = True
                fields_updated.append("thermal_networks")
        except Exception as exc:
            logger.warning("Fetcher fetch_thermal_networks failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_thermal_networks failed: {exc}")

    # --- Step 28: Protected monuments ---
    if has_coords:
        try:
            monuments = await _resolve("fetch_protected_monuments", fetch_protected_monuments)(
                building.latitude, building.longitude
            )
            if monuments:
                enrichment_meta["protected_monuments"] = monuments
                result.protected_monuments_fetched = True
                fields_updated.append("protected_monuments")
        except Exception as exc:
            logger.warning("Fetcher fetch_protected_monuments failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_protected_monuments failed: {exc}")

    # --- Step 29: Agricultural zones ---
    if has_coords:
        try:
            agri = await _resolve("fetch_agricultural_zones", fetch_agricultural_zones)(
                building.latitude, building.longitude
            )
            if agri:
                enrichment_meta["agricultural_zones"] = agri
                result.agricultural_zones_fetched = True
                fields_updated.append("agricultural_zones")
        except Exception as exc:
            logger.warning("Fetcher fetch_agricultural_zones failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_agricultural_zones failed: {exc}")

    # --- Step 30: Forest reserves ---
    if has_coords:
        try:
            forest = await _resolve("fetch_forest_reserves", fetch_forest_reserves)(
                building.latitude, building.longitude
            )
            if forest:
                enrichment_meta["forest_reserves"] = forest
                result.forest_reserves_fetched = True
                fields_updated.append("forest_reserves")
        except Exception as exc:
            logger.warning("Fetcher fetch_forest_reserves failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_forest_reserves failed: {exc}")

    # --- Step 31: Military zones ---
    if has_coords:
        try:
            military = await _resolve("fetch_military_zones", fetch_military_zones)(
                building.latitude, building.longitude
            )
            if military:
                enrichment_meta["military_zones"] = military
                result.military_zones_fetched = True
                fields_updated.append("military_zones")
        except Exception as exc:
            logger.warning("Fetcher fetch_military_zones failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_military_zones failed: {exc}")

    # --- Step 32: Accident (Seveso) sites ---
    if has_coords:
        try:
            seveso = await _resolve("fetch_accident_sites", fetch_accident_sites)(building.latitude, building.longitude)
            if seveso:
                enrichment_meta["accident_sites"] = seveso
                result.accident_sites_fetched = True
                fields_updated.append("accident_sites")
        except Exception as exc:
            logger.warning("Fetcher fetch_accident_sites failed for building %s: %s", building_id, exc)
            result.errors.append(f"fetch_accident_sites failed: {exc}")

    # --- Step 33: OSM amenities ---
    if has_coords:
        amenities = await _resolve("fetch_osm_amenities", fetch_osm_amenities)(building.latitude, building.longitude)
        if amenities:
            enrichment_meta["osm_amenities"] = amenities
            result.osm_amenities_fetched = True
            fields_updated.append("osm_amenities")

    # --- Step 34: OSM building details ---
    if has_coords:
        osm_bld = await _resolve("fetch_osm_building_details", fetch_osm_building_details)(
            building.latitude, building.longitude
        )
        if osm_bld:
            enrichment_meta["osm_building"] = osm_bld
            result.osm_building_fetched = True
            fields_updated.append("osm_building")

    # --- Step 35: Climate data (pure) ---
    if has_coords:
        climate = _resolve("fetch_climate_data", fetch_climate_data)(building.latitude, building.longitude)
        if climate:
            enrichment_meta["climate"] = climate
            result.climate_computed = True
            fields_updated.append("climate")

    # --- Step 36: Nearest stops ---
    if has_coords:
        stops = await _resolve("fetch_nearest_stops", fetch_nearest_stops)(building.latitude, building.longitude)
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

    # --- Step 38b: Geo risk score (pure) ---
    geo_risk = compute_geo_risk_score(enrichment_meta)
    if geo_risk is not None:
        enrichment_meta["geo_risk_score"] = geo_risk
        result.geo_risk_score_computed = True
        fields_updated.append("geo_risk_score")

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

    # --- Step 49: Populate ClimateExposureProfile ---
    await populate_climate_exposure_profile(db, building_id, enrichment_meta)
    fields_updated.append("climate_exposure_profile")

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
            r = await _resolve("enrich_building", enrich_building)(
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
