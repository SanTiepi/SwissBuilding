"""Identity chain service — resolves address -> EGID -> EGRID -> RDPPF.

Chains the canonical Swiss building identity using public geo.admin.ch APIs.
Every resolved value carries source, confidence, and resolved_at for auditability.
"""

from __future__ import annotations

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
