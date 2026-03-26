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

        # EGID (may be present in feature_id or detail)
        if "featureId" in attrs:
            with contextlib.suppress(ValueError, TypeError):
                result["egid"] = int(attrs["featureId"])

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
    """Fetch building data from the Swiss Register of Buildings (RegBL/GWR).

    Returns dict with construction_year, floors, dwellings, etc.
    Returns empty dict on 404 or error.
    """
    await _throttle()
    url = f"https://madd.bfs.admin.ch/api/v1/en/objects/building/{egid}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                logger.info("RegBL: EGID %d not found (404)", egid)
                return {}
            resp.raise_for_status()
            data = resp.json()

        result: dict[str, Any] = {}
        building = data if isinstance(data, dict) else {}

        # Map known RegBL fields
        field_map = {
            "constructionYear": "construction_year",
            "buildingConstructionYear": "construction_year",
            "gbauj": "construction_year",
            "numberOfFloors": "floors",
            "gastw": "floors",
            "numberOfDwellings": "dwellings",
            "ganzwhg": "dwellings",
            "livingArea": "living_area_m2",
            "gebf": "living_area_m2",
            "heatingType": "heating_type",
            "ghetefText": "heating_type",
            "energySource": "energy_source",
            "genergText": "energy_source",
            "buildingClass": "building_class",
            "gklas": "building_class",
            "buildingCategory": "building_category",
            "gkatText": "building_category",
            "renovationYear": "renovation_year",
            "gbaup": "renovation_year",
        }

        for src_key, dst_key in field_map.items():
            if src_key in building and building[src_key] is not None:
                result[dst_key] = building[src_key]

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
    6. Update building record
    7. Create timeline event
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

    # --- Step 1: Geocode ---
    if not skip_geocode and (building.latitude is None or building.longitude is None):
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

            # Store extra RegBL data in metadata
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

    # --- Step 6: Persist ---
    if fields_updated or result.image_url:
        enrichment_meta["last_enriched_at"] = datetime.now(UTC).isoformat()
        building.source_metadata_json = enrichment_meta
        if "source_metadata_json" not in fields_updated:
            fields_updated.append("source_metadata_json")

    result.fields_updated = fields_updated

    # --- Step 7: Timeline event ---
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
