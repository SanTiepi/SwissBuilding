"""Identity chain service — resolves address -> EGID -> EGRID -> RDPPF.

Chains the canonical Swiss building identity using public geo.admin.ch APIs.
Every resolved value carries source, confidence, and resolved_at for auditability.

Reliability features:
- Explicit fallback chains (primary -> coordinate-based -> partial with gap)
- Freshness enforcement (TTL-based staleness check per component)
- Schema-drift detection (validates API response shape)
"""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.source_registry_service import SourceRegistryService

logger = logging.getLogger(__name__)

# API endpoints
MADD_API = "https://api3.geo.admin.ch/rest/services/api/MapServer/find"
CADASTRE_IDENTIFY_API = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
RDPPF_EXTRACT_API = "https://rdppf.geo.admin.ch/api/v1/full"

# Timeouts
_TIMEOUT = 15.0

# ---------------------------------------------------------------------------
# Schema-drift detection: expected fields per API response type
# ---------------------------------------------------------------------------
EXPECTED_EGID_FIELDS = {"egid", "address", "municipality", "canton"}
EXPECTED_EGRID_FIELDS = {"egrid", "coordinates", "source"}
EXPECTED_RDPPF_FIELDS = {"restrictions", "themes", "parcel_info", "source"}

# Known optional fields per response type (not flagged as unexpected)
_EGID_OPTIONAL = {"coordinates", "confidence", "source", "fallback_used", "gap"}
_EGRID_OPTIONAL = {"parcel_number", "municipality", "area_m2", "fallback_used", "gap"}
_RDPPF_OPTIONAL = {"fallback_used", "gap"}


def validate_response_schema(
    response_data: dict[str, Any],
    expected_fields: set[str],
    optional_fields: set[str] | None = None,
) -> dict[str, Any]:
    """Validate that an API response contains expected fields. Detect schema drift.

    Returns: {valid: bool, missing_fields: [...], unexpected_fields: [...]}
    """
    if not response_data:
        return {"valid": False, "missing_fields": list(expected_fields), "unexpected_fields": []}

    actual = set(response_data.keys())
    missing = expected_fields - actual
    known = expected_fields | (optional_fields or set())
    unexpected = actual - known

    return {
        "valid": len(missing) == 0,
        "missing_fields": sorted(missing),
        "unexpected_fields": sorted(unexpected),
    }


async def _record_schema_drift(
    db: AsyncSession | None,
    source_name: str,
    validation: dict[str, Any],
) -> None:
    """Record a schema_drift health event if validation failed."""
    if db is None or validation["valid"]:
        return
    try:
        desc = f"Missing: {validation['missing_fields']}, Unexpected: {validation['unexpected_fields']}"
        await SourceRegistryService.record_health_event(
            db,
            source_name,
            "schema_drift",
            description=desc,
        )
    except Exception:
        logger.debug("Failed to record schema drift event for %s", source_name, exc_info=True)


# ---------------------------------------------------------------------------
# Low-level HTTP fetch
# ---------------------------------------------------------------------------


async def _fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """Fetch JSON from a URL with error handling."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("Identity chain API request failed: %s — %s", url, exc)
        return {}


# ---------------------------------------------------------------------------
# Internal helpers for coordinate-based fallback
# ---------------------------------------------------------------------------


async def _egid_from_coordinates(coordinates: tuple[float, float]) -> dict[str, Any]:
    """Resolve EGID from coordinates via the identify API (fallback path)."""
    lat, lon = coordinates
    data = await _fetch_json(
        CADASTRE_IDENTIFY_API,
        {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "layers": "all:ch.bfs.gebaeude_wohnungs_register",
            "tolerance": 10,
            "sr": 4326,
            "returnGeometry": "false",
            "limit": 1,
        },
    )
    results = data.get("results", [])
    if results:
        attrs = results[0].get("attributes", {})
        if attrs.get("egid"):
            return {
                "egid": int(attrs["egid"]),
                "address": attrs.get("strname_deinr"),
                "municipality": attrs.get("gdename"),
                "canton": attrs.get("gkanton"),
                "coordinates": coordinates,
                "source": "madd",
                "confidence": 0.85,
            }
    return {}


# ---------------------------------------------------------------------------
# EGID resolution (with fallback)
# ---------------------------------------------------------------------------


async def resolve_egid(
    *,
    address: str | None = None,
    coordinates: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Resolve EGID from address or coordinates via geo.admin.ch.

    Returns: {egid, address, coordinates, municipality, canton, confidence, source}
    """
    result: dict[str, Any] = {}

    # Try address search first
    if address:
        data = await _fetch_json(
            MADD_API,
            {
                "layer": "ch.bfs.gebaeude_wohnungs_register",
                "searchField": "strname_deinr",
                "searchText": address,
                "returnGeometry": "true",
                "contains": "true",
            },
        )
        features = data.get("results", [])
        if features:
            attrs = features[0].get("attributes", {})
            geom = features[0].get("geometry", {})
            if attrs.get("egid"):
                result = {
                    "egid": int(attrs["egid"]),
                    "address": attrs.get("strname_deinr", address),
                    "municipality": attrs.get("gdename"),
                    "canton": attrs.get("gkanton"),
                    "source": "madd",
                    "confidence": 0.9 if len(features) == 1 else 0.7,
                }
                if geom.get("x") is not None and geom.get("y") is not None:
                    result["coordinates"] = (geom["y"], geom["x"])
                return result

    # Fallback: coordinate-based lookup
    if coordinates:
        lat, lon = coordinates
        data = await _fetch_json(
            CADASTRE_IDENTIFY_API,
            {
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "layers": "all:ch.bfs.gebaeude_wohnungs_register",
                "tolerance": 10,
                "sr": 4326,
                "returnGeometry": "false",
                "limit": 1,
            },
        )
        results = data.get("results", [])
        if results:
            attrs = results[0].get("attributes", {})
            if attrs.get("egid"):
                return {
                    "egid": int(attrs["egid"]),
                    "address": attrs.get("strname_deinr"),
                    "municipality": attrs.get("gdename"),
                    "canton": attrs.get("gkanton"),
                    "coordinates": coordinates,
                    "source": "madd",
                    "confidence": 0.85,
                }

    return result


async def resolve_egid_with_fallback(
    db: AsyncSession | None = None,
    *,
    address: str | None = None,
    coordinates: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Resolve EGID with explicit fallback chain and health events.

    Fallback chain:
    1. Primary: MADD API address search
    2. Fallback: coordinate-based identify API
    3. Partial: return gap descriptor

    Returns dict with egid or gap description. Always includes fallback_used flag.
    """
    try:
        result = await resolve_egid(address=address, coordinates=coordinates)
        if result.get("egid"):
            if db:
                with contextlib.suppress(Exception):
                    await SourceRegistryService.record_health_event(db, "geo_admin_madd", "healthy")
            # Validate schema
            schema_check = validate_response_schema(result, EXPECTED_EGID_FIELDS, _EGID_OPTIONAL)
            if not schema_check["valid"]:
                await _record_schema_drift(db, "geo_admin_madd", schema_check)
            return result
    except Exception as e:
        logger.warning("EGID primary resolution failed: %s", e)
        if db:
            with contextlib.suppress(Exception):
                await SourceRegistryService.record_health_event(db, "geo_admin_madd", "error", error=str(e))

    # Fallback: try coordinate-based lookup if address failed or returned empty
    if coordinates:
        try:
            result = await _egid_from_coordinates(coordinates)
            if result.get("egid"):
                if db:
                    with contextlib.suppress(Exception):
                        await SourceRegistryService.record_health_event(
                            db,
                            "geo_admin_madd",
                            "degraded",
                            description="Primary MADD failed, fell back to coordinate lookup",
                            fallback_used=True,
                        )
                return {**result, "fallback_used": True}
        except Exception:
            pass

    # All paths exhausted
    return {
        "egid": None,
        "source": "unavailable",
        "confidence": 0.0,
        "fallback_used": True,
        "gap": "EGID resolution failed on both primary and fallback paths",
    }


# ---------------------------------------------------------------------------
# EGRID resolution (with fallback)
# ---------------------------------------------------------------------------


async def resolve_egrid(
    *,
    egid: int | None = None,
    coordinates: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Resolve EGRID (parcel identifier) from EGID or coordinates.

    Uses geo.admin.ch cadastral survey identify API.
    Returns: {egrid, parcel_number, municipality, area_m2, coordinates, source}
    """
    # Determine coordinates from EGID if needed
    lookup_coords = coordinates

    if egid and not lookup_coords:
        # First resolve EGID to coordinates
        data = await _fetch_json(
            CADASTRE_IDENTIFY_API,
            {
                "geometry": "0,0,1000000,1000000",
                "geometryType": "esriGeometryEnvelope",
                "layers": "all:ch.bfs.gebaeude_wohnungs_register",
                "tolerance": 0,
                "sr": 21781,
                "returnGeometry": "true",
                "where": f"egid = {egid}",
                "limit": 1,
            },
        )
        # Fallback: use the find API to get coordinates for this EGID
        find_data = await _fetch_json(
            MADD_API,
            {
                "layer": "ch.bfs.gebaeude_wohnungs_register",
                "searchField": "egid",
                "searchText": str(egid),
                "returnGeometry": "true",
            },
        )
        features = find_data.get("results", [])
        if features:
            geom = features[0].get("geometry", {})
            if geom.get("x") is not None and geom.get("y") is not None:
                lookup_coords = (geom["y"], geom["x"])

    if not lookup_coords:
        return {}

    lat, lon = lookup_coords

    # Look up cadastral parcel via identify on the cadastral survey layer
    data = await _fetch_json(
        CADASTRE_IDENTIFY_API,
        {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "layers": "all:ch.bfs.gebaeude_wohnungs_register",
            "tolerance": 10,
            "sr": 4326,
            "returnGeometry": "false",
            "limit": 1,
        },
    )
    results = data.get("results", [])
    result: dict[str, Any] = {}

    if results:
        attrs = results[0].get("attributes", {})
        if attrs.get("egrid"):
            result["egrid"] = str(attrs["egrid"])
        if attrs.get("grundstueckNr") or attrs.get("lparz"):
            result["parcel_number"] = str(attrs.get("grundstueckNr") or attrs.get("lparz", ""))
        if attrs.get("gdename") or attrs.get("gemeindename"):
            result["municipality"] = str(attrs.get("gdename") or attrs.get("gemeindename", ""))
        result["coordinates"] = lookup_coords
        result["source"] = "cadastre"

    return result


async def resolve_egrid_with_fallback(
    db: AsyncSession | None = None,
    *,
    egid: int | None = None,
    coordinates: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Resolve EGRID with explicit fallback chain and health events.

    Fallback chain:
    1. Primary: cadastre identify API via EGID
    2. Fallback: coordinate-based lookup (if coordinates provided)
    3. Partial: return gap descriptor

    Returns dict with egrid or gap description. Always includes fallback_used flag.
    """
    try:
        result = await resolve_egrid(egid=egid, coordinates=coordinates)
        if result.get("egrid"):
            if db:
                with contextlib.suppress(Exception):
                    await SourceRegistryService.record_health_event(db, "geo_admin_cadastre", "healthy")
            schema_check = validate_response_schema(result, EXPECTED_EGRID_FIELDS, _EGRID_OPTIONAL)
            if not schema_check["valid"]:
                await _record_schema_drift(db, "geo_admin_cadastre", schema_check)
            return result
    except Exception as e:
        logger.warning("EGRID primary resolution failed: %s", e)
        if db:
            with contextlib.suppress(Exception):
                await SourceRegistryService.record_health_event(db, "geo_admin_cadastre", "error", error=str(e))

    # Fallback: try coordinate-based directly if we have coords and primary failed
    if coordinates and egid:
        try:
            fallback_result = await resolve_egrid(egid=None, coordinates=coordinates)
            if fallback_result.get("egrid"):
                if db:
                    with contextlib.suppress(Exception):
                        await SourceRegistryService.record_health_event(
                            db,
                            "geo_admin_cadastre",
                            "degraded",
                            description="Primary cadastre failed, fell back to coordinate lookup",
                            fallback_used=True,
                        )
                return {**fallback_result, "fallback_used": True}
        except Exception:
            pass

    # All paths exhausted
    return {
        "egrid": None,
        "source": "unavailable",
        "confidence": 0.0,
        "fallback_used": True,
        "gap": "EGRID resolution failed on both primary and fallback paths",
    }


# ---------------------------------------------------------------------------
# RDPPF fetch (with fallback)
# ---------------------------------------------------------------------------


async def fetch_rdppf(egrid: str) -> dict[str, Any]:
    """Fetch RDPPF (public law restrictions on land ownership) for a parcel.

    Uses the federal RDPPF API (api3.geo.admin.ch) with multiple restriction layers.
    Returns: {restrictions: [...], themes: [...], parcel_info: {...}, source}
    """
    if not egrid:
        return {}

    # RDPPF themes available via geo.admin.ch identify
    rdppf_layers = [
        "ch.bav.kataster-belasteter-standorte-oev",  # contaminated transport sites
        "ch.bafu.kataster-belasteter-standorte",  # contaminated sites FOEN
        "ch.bazl.kataster-belasteter-standorte-zivilflugplaetze",  # contaminated airports
        "ch.vbs.kataster-belasteter-standorte-militaer",  # contaminated military
        "ch.are.belastung-personenverkehr-bahn",  # rail traffic
        "ch.bfe.statistik-wasserkraftanlagen",  # hydro stats
    ]

    restrictions: list[dict[str, Any]] = []
    themes: list[str] = []

    # Try the RDPPF extract endpoint (canton-dependent availability)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Federal RDPPF extract (JSON)
            resp = await client.get(
                "https://api3.geo.admin.ch/rest/services/api/MapServer/find",
                params={
                    "layer": "ch.bfs.gebaeude_wohnungs_register",
                    "searchField": "egrid",
                    "searchText": egrid,
                    "returnGeometry": "true",
                },
            )
            resp.raise_for_status()
            find_data = resp.json()

        features = find_data.get("results", [])
        if features:
            geom = features[0].get("geometry", {})
            if geom.get("x") is not None and geom.get("y") is not None:
                lon, lat = geom["x"], geom["y"]

                # Query each RDPPF-relevant layer
                for layer_id in rdppf_layers:
                    layer_data = await _fetch_json(
                        CADASTRE_IDENTIFY_API,
                        {
                            "geometry": f"{lon},{lat}",
                            "geometryType": "esriGeometryPoint",
                            "layers": f"all:{layer_id}",
                            "tolerance": 50,
                            "sr": 4326,
                            "returnGeometry": "false",
                            "limit": 5,
                        },
                    )
                    layer_results = layer_data.get("results", [])
                    for item in layer_results:
                        attrs = item.get("attributes", {})
                        layer_name = item.get("layerBodId", layer_id)
                        theme = layer_name.split(".")[-1] if "." in layer_name else layer_name
                        if theme not in themes:
                            themes.append(theme)
                        restrictions.append(
                            {
                                "type": theme,
                                "layer": layer_name,
                                "description": attrs.get("bezeichnung") or attrs.get("name") or theme,
                                "authority": attrs.get("behoerde") or attrs.get("datenherr") or "geo.admin.ch",
                                "in_force_since": attrs.get("bgdi_created"),
                                "raw_attributes": attrs,
                            }
                        )

    except Exception as exc:
        logger.warning("RDPPF fetch failed for EGRID %s: %s", egrid, exc)

    return {
        "restrictions": restrictions,
        "themes": themes,
        "parcel_info": {"egrid": egrid},
        "source": "geo.admin.ch",
    }


async def fetch_rdppf_with_fallback(
    db: AsyncSession | None = None,
    *,
    egrid: str,
) -> dict[str, Any]:
    """Fetch RDPPF with explicit fallback and health events.

    Fallback chain:
    1. Primary: full RDPPF fetch via geo.admin.ch
    2. Partial: return empty restrictions with gap descriptor

    Returns dict with restrictions or gap description. Always includes fallback_used flag.
    """
    try:
        result = await fetch_rdppf(egrid)
        has_data = bool(result.get("restrictions") or result.get("themes"))
        if has_data:
            if db:
                with contextlib.suppress(Exception):
                    await SourceRegistryService.record_health_event(db, "rdppf_federal", "healthy")
            schema_check = validate_response_schema(result, EXPECTED_RDPPF_FIELDS, _RDPPF_OPTIONAL)
            if not schema_check["valid"]:
                await _record_schema_drift(db, "rdppf_federal", schema_check)
            return result
        # API succeeded but returned no data (not an error per se)
        return result
    except Exception as e:
        logger.warning("RDPPF fallback-aware fetch failed for EGRID %s: %s", egrid, e)
        if db:
            with contextlib.suppress(Exception):
                await SourceRegistryService.record_health_event(db, "rdppf_federal", "error", error=str(e))

    # Return partial with gap
    return {
        "restrictions": [],
        "themes": [],
        "parcel_info": {"egrid": egrid},
        "source": "unavailable",
        "fallback_used": True,
        "gap": "RDPPF fetch failed",
    }


# ---------------------------------------------------------------------------
# Freshness enforcement
# ---------------------------------------------------------------------------


async def check_freshness(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Check if the cached identity chain is still fresh per source registry TTL.

    Returns: {fresh: bool, stale_components: [...], recommended_action: str}
    """
    chain = await get_identity_chain(db, building_id)
    if not chain or chain.get("error"):
        return {
            "fresh": False,
            "stale_components": ["all"],
            "recommended_action": "resolve",
        }

    stale_components: list[str] = []

    # Check EGID freshness
    egid_freshness = await SourceRegistryService.check_source_freshness(db, "geo_admin_madd", building_id)
    if not egid_freshness.get("is_fresh", True):
        stale_components.append("egid")

    # Check EGRID freshness
    egrid_freshness = await SourceRegistryService.check_source_freshness(db, "geo_admin_cadastre", building_id)
    if not egrid_freshness.get("is_fresh", True):
        stale_components.append("egrid")

    # Check RDPPF freshness
    rdppf_freshness = await SourceRegistryService.check_source_freshness(db, "rdppf_federal", building_id)
    if not rdppf_freshness.get("is_fresh", True):
        stale_components.append("rdppf")

    fresh = len(stale_components) == 0

    if not fresh:
        recommended_action = "refresh"
    else:
        recommended_action = "none"

    return {
        "fresh": fresh,
        "stale_components": stale_components,
        "recommended_action": recommended_action,
        "component_freshness": {
            "egid": egid_freshness,
            "egrid": egrid_freshness,
            "rdppf": rdppf_freshness,
        },
    }


# ---------------------------------------------------------------------------
# Full chain resolution (unchanged success path, enhanced error handling)
# ---------------------------------------------------------------------------


async def resolve_full_chain(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Resolve the complete identity chain for a building.

    Steps:
    1. Get building coordinates/address
    2. Resolve/verify EGID
    3. Resolve EGRID from EGID/coordinates
    4. Fetch RDPPF restrictions for the parcel
    5. Store results on BuildingIdentityChain
    """
    from app.models.building import Building
    from app.models.building_identity import BuildingIdentityChain

    # Load building
    stmt = select(Building).where(Building.id == building_id)
    row = await db.execute(stmt)
    building = row.scalar_one_or_none()
    if not building:
        return {"error": "building_not_found", "chain_complete": False, "chain_gaps": ["building_not_found"]}

    now = datetime.now(UTC)
    chain_gaps: list[str] = []
    result: dict[str, Any] = {"egid": {}, "egrid": {}, "rdppf": {}}

    # Step 1: EGID
    egid_value = building.egid
    egid_source = "existing"
    egid_confidence = 1.0

    if not egid_value:
        coords = None
        if building.latitude and building.longitude:
            coords = (building.latitude, building.longitude)

        egid_result = await resolve_egid(
            address=building.address,
            coordinates=coords,
        )
        if egid_result.get("egid"):
            egid_value = egid_result["egid"]
            egid_source = egid_result.get("source", "madd")
            egid_confidence = egid_result.get("confidence", 0.7)
            # Also update the building itself
            building.egid = egid_value
        else:
            chain_gaps.append("egid_not_resolved")

    result["egid"] = {
        "value": egid_value,
        "source": egid_source,
        "confidence": egid_confidence,
        "resolved_at": now.isoformat() if egid_value else None,
    }

    # Step 2: EGRID
    egrid_value = building.egrid
    egrid_source = "existing" if egrid_value else None
    parcel_number = building.parcel_number
    parcel_area: float | None = None

    if not egrid_value:
        coords = None
        if building.latitude and building.longitude:
            coords = (building.latitude, building.longitude)

        egrid_result = await resolve_egrid(
            egid=egid_value,
            coordinates=coords,
        )
        if egrid_result.get("egrid"):
            egrid_value = egrid_result["egrid"]
            egrid_source = egrid_result.get("source", "cadastre")
            parcel_number = egrid_result.get("parcel_number", parcel_number)
            parcel_area = egrid_result.get("area_m2")
            # Update building
            building.egrid = egrid_value
            if parcel_number and not building.parcel_number:
                building.parcel_number = parcel_number
        else:
            chain_gaps.append("egrid_not_resolved")

    result["egrid"] = {
        "value": egrid_value,
        "parcel_number": parcel_number,
        "area_m2": parcel_area,
        "source": egrid_source,
        "resolved_at": now.isoformat() if egrid_value else None,
    }

    # Step 3: RDPPF
    rdppf_data: dict[str, Any] = {}
    if egrid_value:
        rdppf_data = await fetch_rdppf(egrid_value)
        if not rdppf_data.get("restrictions") and not rdppf_data.get("themes"):
            chain_gaps.append("rdppf_no_data")
    else:
        chain_gaps.append("rdppf_skipped_no_egrid")

    result["rdppf"] = {
        "restrictions": rdppf_data.get("restrictions", []),
        "themes": rdppf_data.get("themes", []),
        "source": rdppf_data.get("source"),
        "resolved_at": now.isoformat() if rdppf_data.get("restrictions") or rdppf_data.get("themes") else None,
    }

    # Chain completeness
    chain_complete = len(chain_gaps) == 0
    result["chain_complete"] = chain_complete
    result["chain_gaps"] = chain_gaps

    # Record health events for identity sources
    try:
        if egid_value:
            await SourceRegistryService.record_health_event(db, "geo_admin_madd", "healthy")
        else:
            await SourceRegistryService.record_health_event(
                db, "geo_admin_madd", "degraded", description="EGID not resolved"
            )
        if egrid_value:
            await SourceRegistryService.record_health_event(db, "geo_admin_cadastre", "healthy")
        if rdppf_data.get("restrictions") or rdppf_data.get("themes"):
            await SourceRegistryService.record_health_event(db, "rdppf_federal", "healthy")
    except Exception:
        logger.debug("Failed to record source health event", exc_info=True)

    # Persist to BuildingIdentityChain
    stmt2 = select(BuildingIdentityChain).where(BuildingIdentityChain.building_id == building_id)
    row2 = await db.execute(stmt2)
    identity = row2.scalar_one_or_none()

    if identity is None:
        identity = BuildingIdentityChain(building_id=building_id)
        db.add(identity)

    identity.egid = egid_value
    identity.egid_source = egid_source
    identity.egid_confidence = egid_confidence
    identity.egid_resolved_at = now if egid_value else None

    identity.egrid = egrid_value
    identity.parcel_number = parcel_number
    identity.parcel_area_m2 = parcel_area
    identity.egrid_source = egrid_source
    identity.egrid_resolved_at = now if egrid_value else None

    identity.rdppf_data = rdppf_data if rdppf_data else None
    identity.rdppf_source = rdppf_data.get("source") if rdppf_data else None
    identity.rdppf_resolved_at = now if rdppf_data.get("restrictions") or rdppf_data.get("themes") else None

    identity.chain_complete = chain_complete
    identity.chain_gaps = chain_gaps if chain_gaps else None

    return result


async def get_identity_chain(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Get cached identity chain for a building, or resolve if missing."""
    from app.models.building_identity import BuildingIdentityChain

    stmt = select(BuildingIdentityChain).where(BuildingIdentityChain.building_id == building_id)
    row = await db.execute(stmt)
    identity = row.scalar_one_or_none()

    if identity is not None:
        return {
            "egid": {
                "value": identity.egid,
                "source": identity.egid_source,
                "confidence": identity.egid_confidence,
                "resolved_at": identity.egid_resolved_at.isoformat() if identity.egid_resolved_at else None,
            },
            "egrid": {
                "value": identity.egrid,
                "parcel_number": identity.parcel_number,
                "area_m2": identity.parcel_area_m2,
                "source": identity.egrid_source,
                "resolved_at": identity.egrid_resolved_at.isoformat() if identity.egrid_resolved_at else None,
            },
            "rdppf": {
                "restrictions": (identity.rdppf_data or {}).get("restrictions", []),
                "themes": (identity.rdppf_data or {}).get("themes", []),
                "source": identity.rdppf_source,
                "resolved_at": identity.rdppf_resolved_at.isoformat() if identity.rdppf_resolved_at else None,
            },
            "chain_complete": identity.chain_complete,
            "chain_gaps": identity.chain_gaps or [],
            "cached": True,
        }

    # No cached chain — resolve it
    result = await resolve_full_chain(db, building_id)
    result["cached"] = False
    return result
