"""Onboarding wizard API — EGID lookup + guided building creation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.onboarding import EgidLookupRequest, EgidLookupResult, OnboardingCreateRequest

router = APIRouter()


@router.post("/onboarding/egid-lookup", response_model=EgidLookupResult)
async def egid_lookup(
    body: EgidLookupRequest,
    current_user: User = Depends(require_permission("buildings", "create")),
):
    """Look up building data by EGID from Vaud public sources (no DB write)."""
    from app.importers.vaud_public import (
        _fetch_all_addresses_for_egid,
        fetch_rcb_record,
        normalize_building_record,
        pick_primary_addresses,
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch address records for this EGID
            addresses = await _fetch_all_addresses_for_egid(client, body.egid)
            rcb = await fetch_rcb_record(client, body.egid)

        if not addresses and not rcb:
            return EgidLookupResult(found=False, egid=body.egid)

        # Normalize the building record if we have both address + rcb
        if addresses and rcb:
            primaries = pick_primary_addresses(addresses, limit=1)
            primary = primaries[0] if primaries else addresses[0]
            normalized = normalize_building_record(
                primary,
                rcb,
                municipality_ofs=primary.municipality_ofs,
                all_addresses=addresses,
            )
            if normalized:
                return EgidLookupResult(
                    found=True,
                    egid=normalized.egid,
                    address=normalized.address,
                    postal_code=normalized.postal_code,
                    city=normalized.city,
                    canton=normalized.canton,
                    municipality_ofs=normalized.municipality_ofs,
                    latitude=normalized.latitude,
                    longitude=normalized.longitude,
                    construction_year=normalized.construction_year,
                    building_type=normalized.building_type,
                    floors_above=normalized.floors_above,
                    surface_area_m2=normalized.surface_area_m2,
                    source_metadata=normalized.source_metadata,
                    has_address=bool(normalized.address),
                    has_coordinates=normalized.latitude is not None and normalized.longitude is not None,
                    has_construction_year=normalized.construction_year is not None,
                    has_building_type=bool(normalized.building_type),
                    has_floors=normalized.floors_above is not None,
                    has_surface_area=normalized.surface_area_m2 is not None,
                )

        # Partial data — we have RCB but no address, or address but no RCB
        if rcb:
            return EgidLookupResult(
                found=True,
                egid=body.egid,
                construction_year=rcb.construction_year,
                latitude=rcb.latitude,
                longitude=rcb.longitude,
                has_coordinates=rcb.latitude is not None and rcb.longitude is not None,
                has_construction_year=rcb.construction_year is not None,
            )

        # Address-only fallback
        primary = addresses[0]
        return EgidLookupResult(
            found=True,
            egid=body.egid,
            postal_code=primary.postal_code,
            city=primary.locality,
            has_address=False,
        )

    except httpx.HTTPError as e:
        logging.getLogger(__name__).exception("Public data source unavailable during EGID lookup")
        raise HTTPException(status_code=502, detail="Public data source unavailable") from e
    except Exception as e:
        logging.getLogger(__name__).exception("EGID lookup failed")
        raise HTTPException(status_code=500, detail="EGID lookup failed") from e


@router.post("/onboarding/create-building", status_code=201)
async def onboarding_create_building(
    body: OnboardingCreateRequest,
    current_user: User = Depends(require_permission("buildings", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a building from onboarding wizard data + trigger enrichment."""
    from app.constants import SOURCE_DATASET_VAUD_PUBLIC
    from app.schemas.building import BuildingCreate
    from app.services.audit_service import log_action
    from app.services.building_service import create_building

    building_data = BuildingCreate(
        egid=body.egid,
        address=body.address,
        postal_code=body.postal_code,
        city=body.city,
        canton=body.canton,
        municipality_ofs=body.municipality_ofs,
        latitude=body.latitude,
        longitude=body.longitude,
        construction_year=body.construction_year,
        building_type=body.building_type,
        floors_above=body.floors_above,
        surface_area_m2=body.surface_area_m2,
        source_dataset=SOURCE_DATASET_VAUD_PUBLIC,
        source_imported_at=datetime.now(UTC),
        source_metadata_json=body.source_metadata,
    )

    building = await create_building(
        db,
        building_data,
        current_user.id,
        organization_id=current_user.organization_id,
    )
    await log_action(db, current_user.id, "create", "building", building.id)

    # Try enrichment (best-effort, non-blocking)
    try:
        from app.services.building_enrichment_service import enrich_building

        await enrich_building(db, building.id)
    except Exception:
        pass  # Enrichment failure should not block building creation

    await db.commit()

    # Try search indexing (best-effort)
    try:
        from app.services.search_service import index_building

        index_building(building)
    except Exception:
        pass

    return {
        "id": str(building.id),
        "address": building.address,
        "city": building.city,
        "canton": building.canton,
        "egid": building.egid,
    }
