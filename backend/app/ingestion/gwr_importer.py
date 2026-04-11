"""
GWR (Registre fédéral des bâtiments) bulk importer.

Imports building data from geo.admin.ch GWR API with:
- Idempotent upsert via egid (unique federal identifier)
- Batch processing: 1000 buildings per transaction
- Source tracking: all fields tagged with source="gwr", fetched_at=ISO timestamp
- Merge logic: update missing fields only, don't overwrite existing data
- No deletes, only create/update
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.constants import SOURCE_DATASET_GWR
from app.models import Building
from app.database import SessionLocal


logger = logging.getLogger(__name__)


# GWR API endpoint for building data
GWR_API_BASE = "https://data.geo.admin.ch/api/v1"
GWR_API_ENDPOINT = f"{GWR_API_BASE}/building_gwr"

# Batch size for database transactions
BATCH_SIZE = 1000
LOG_INTERVAL = 10000

# Map GWR heat source codes to normalized values
HEAT_SOURCE_MAP = {
    "E01": "electric",
    "E02": "gas",
    "E03": "oil",
    "E04": "heat_pump",
    "E05": "wood",
    "E06": "district",
    "E07": "solar",
    "E08": "biomass",
    "E09": "other",
}

# Map GWR construction periods
CONSTRUCTION_PERIOD_MAP = {
    "1": "before_1800",
    "2": "1800-1850",
    "3": "1850-1900",
    "4": "1900-1920",
    "5": "1920-1945",
    "6": "1945-1960",
    "7": "1960-1975",
    "8": "1975-1985",
    "9": "1985-2000",
    "10": "2000-2010",
    "11": "2010-2025",
}

# Map GWR primary use codes
PRIMARY_USE_MAP = {
    "10": "habitation",
    "20": "commerce",
    "30": "industry",
    "40": "agriculture",
    "50": "public",
    "60": "transport",
    "70": "storage",
    "80": "other",
}

# Map GWR hot water source codes
HOT_WATER_SOURCE_MAP = {
    "1": "centralized",
    "2": "decentralized",
    "3": "none",
}


class GWRImporter:
    """Bulk importer for GWR building data with idempotent upsert."""

    def __init__(self, session: Session | None = None):
        """Initialize the importer.

        Args:
            session: Optional SQLAlchemy session. If None, creates a new one.
        """
        self.session = session or SessionLocal()
        self.imported_count = 0
        self.updated_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.fetched_at = datetime.now(UTC)

    async def fetch_buildings_for_cantons(
        self,
        cantons: list[str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch buildings from GWR API for specified cantons.

        Args:
            cantons: List of canton codes (e.g., ["VD", "GE"]). If None, fetches all.
            limit: Maximum number of buildings to fetch. For testing.

        Returns:
            List of building records from GWR API.
        """
        buildings = []

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # GWR API uses pagination via offset parameter
                offset = 0
                page_size = 1000

                while True:
                    params = {"limit": page_size, "offset": offset}

                    if cantons:
                        params["canton"] = ",".join(cantons)

                    logger.info(f"Fetching GWR buildings: offset={offset}, limit={page_size}")

                    response = await client.get(
                        GWR_API_ENDPOINT,
                        params=params,
                        follow_redirects=True,
                    )
                    response.raise_for_status()

                    data = response.json()
                    features = data.get("features", [])

                    if not features:
                        break

                    # Extract properties from GeoJSON features
                    for feature in features:
                        props = feature.get("properties", {})
                        if props:
                            buildings.append(props)

                    if limit and len(buildings) >= limit:
                        buildings = buildings[:limit]
                        break

                    offset += page_size

                    if len(features) < page_size:
                        # Last page
                        break

        except Exception as e:
            logger.error(f"Error fetching GWR buildings: {e}")
            self.error_count += 1
            raise

        logger.info(f"Fetched {len(buildings)} buildings from GWR API")
        return buildings

    def _normalize_heat_source(self, value: str | None) -> str | None:
        """Map GWR heat source code to normalized value."""
        if not value:
            return None
        return HEAT_SOURCE_MAP.get(value, value)

    def _normalize_construction_period(self, value: str | None) -> str | None:
        """Map GWR construction period code to normalized value."""
        if not value:
            return None
        return CONSTRUCTION_PERIOD_MAP.get(value, value)

    def _normalize_primary_use(self, value: str | None) -> str | None:
        """Map GWR primary use code to normalized value."""
        if not value:
            return None
        return PRIMARY_USE_MAP.get(value, value)

    def _normalize_hot_water_source(self, value: str | None) -> str | None:
        """Map GWR hot water source code to normalized value."""
        if not value:
            return None
        return HOT_WATER_SOURCE_MAP.get(value, value)

    def _extract_gwr_data(self, gwr_record: dict[str, Any]) -> dict[str, Any]:
        """Extract and normalize GWR building data.

        Args:
            gwr_record: Raw GWR API record

        Returns:
            Normalized building data ready for upsert
        """
        # Extract egid (federal building identifier) - REQUIRED
        egid = gwr_record.get("egid")
        if not egid:
            logger.warning(f"Skipping record without egid: {gwr_record}")
            self.skipped_count += 1
            return {}

        # Extract all available fields
        return {
            "egid": egid,
            "address": self._safe_str(gwr_record.get("address")),
            "postal_code": self._safe_str(gwr_record.get("postal_code", "")),
            "city": self._safe_str(gwr_record.get("city", "")),
            "canton": self._safe_str(gwr_record.get("canton")),
            "latitude": self._safe_float(gwr_record.get("latitude")),
            "longitude": self._safe_float(gwr_record.get("longitude")),
            "municipality_ofs": self._safe_int(gwr_record.get("municipality_ofs")),
            "construction_year": self._safe_int(gwr_record.get("construction_year")),
            "building_type": self._safe_str(gwr_record.get("building_type", "unknown")),
            "floors_above": self._safe_int(gwr_record.get("floors_above")),
            "surface_area_m2": self._safe_float(gwr_record.get("surface_area_m2")),
            "volume_m3": self._safe_float(gwr_record.get("volume_m3")),
            "heat_source": self._normalize_heat_source(gwr_record.get("heat_source")),
            "construction_period": self._normalize_construction_period(
                gwr_record.get("construction_period")
            ),
            "primary_use": self._normalize_primary_use(gwr_record.get("primary_use")),
            "hot_water_source": self._normalize_hot_water_source(
                gwr_record.get("hot_water_source")
            ),
            "num_households": self._safe_int(gwr_record.get("num_households")),
            "source_dataset": SOURCE_DATASET_GWR,
            "source_imported_at": self.fetched_at,
            "source_metadata_json": {
                "gwr_source": "geo.admin.ch",
                "fetched_at": self.fetched_at.isoformat(),
                "raw_data": gwr_record,
            },
        }

    def _safe_str(self, value: Any, default: str = "") -> str:
        """Safely convert value to string."""
        if value is None:
            return default
        return str(value).strip()

    def _safe_int(self, value: Any) -> int | None:
        """Safely convert value to int."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _safe_float(self, value: Any) -> float | None:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _upsert_building(self, building_data: dict[str, Any]) -> bool:
        """Upsert a single building record (idempotent).

        Merge logic:
        - If building exists (by egid): update ONLY missing fields
        - If building doesn't exist: create new

        Args:
            building_data: Normalized building data from GWR

        Returns:
            True if created/updated, False if skipped
        """
        if not building_data or "egid" not in building_data:
            self.skipped_count += 1
            return False

        egid = building_data["egid"]

        # Find existing building by egid
        stmt = select(Building).where(Building.egid == egid)
        existing = self.session.execute(stmt).scalars().first()

        if existing:
            # Update: only set fields that are None in existing record
            updated = False
            for field, value in building_data.items():
                if field in ("source_dataset", "source_imported_at", "source_metadata_json"):
                    # Always update source tracking
                    setattr(existing, field, value)
                    updated = True
                elif value is not None:
                    current = getattr(existing, field, None)
                    # Only update if current value is None (merge logic)
                    if current is None:
                        setattr(existing, field, value)
                        updated = True

            if updated:
                self.updated_count += 1
                return True
            else:
                self.skipped_count += 1
                return False
        else:
            # Create new building
            building = Building(
                **{
                    k: v
                    for k, v in building_data.items()
                    if k not in ("source_metadata_json",)
                }
            )
            # Handle JSON field separately
            building.source_metadata_json = building_data.get("source_metadata_json")
            self.session.add(building)
            self.imported_count += 1
            return True

    async def import_bulk(
        self,
        cantons: list[str] | None = None,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Bulk import buildings from GWR API.

        Args:
            cantons: List of canton codes (e.g., ["VD", "GE"]). If None, imports all.
            limit: Maximum number of buildings to import. For testing.
            dry_run: If True, don't commit changes to database.

        Returns:
            Dictionary with import statistics
        """
        logger.info(f"Starting GWR bulk import (cantons={cantons}, limit={limit}, dry_run={dry_run})")

        # Fetch all buildings from GWR API
        gwr_buildings = await self.fetch_buildings_for_cantons(cantons=cantons, limit=limit)

        if not gwr_buildings:
            logger.warning("No buildings fetched from GWR API")
            return {
                "imported": self.imported_count,
                "updated": self.updated_count,
                "skipped": self.skipped_count,
                "errors": self.error_count,
            }

        # Process in batches with transaction control
        batch = []
        for idx, gwr_record in enumerate(gwr_buildings):
            try:
                building_data = self._extract_gwr_data(gwr_record)
                if building_data:
                    batch.append(building_data)

                # Process batch when full
                if len(batch) >= BATCH_SIZE or idx == len(gwr_buildings) - 1:
                    self._process_batch(batch, dry_run=dry_run)
                    batch = []

                # Log progress
                if (idx + 1) % LOG_INTERVAL == 0:
                    logger.info(
                        f"Progress: {idx + 1}/{len(gwr_buildings)} "
                        f"(imported={self.imported_count}, updated={self.updated_count}, "
                        f"skipped={self.skipped_count}, errors={self.error_count})"
                    )

            except Exception as e:
                logger.error(f"Error processing building {idx}: {e}")
                self.error_count += 1
                continue

        logger.info(
            f"GWR import complete: imported={self.imported_count}, updated={self.updated_count}, "
            f"skipped={self.skipped_count}, errors={self.error_count}"
        )

        return {
            "imported": self.imported_count,
            "updated": self.updated_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
        }

    def _process_batch(self, batch: list[dict[str, Any]], dry_run: bool = False) -> None:
        """Process a batch of buildings with transaction control.

        Args:
            batch: List of normalized building data
            dry_run: If True, don't commit to database
        """
        if not batch:
            return

        try:
            for building_data in batch:
                self._upsert_building(building_data)

            # Commit batch transaction
            if not dry_run:
                self.session.commit()
                logger.debug(f"Committed batch of {len(batch)} buildings")
            else:
                self.session.rollback()
                logger.debug(f"Dry-run: rolled back batch of {len(batch)} buildings")

        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            self.session.rollback()
            self.error_count += len(batch)
            raise

    def close(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


async def import_gwr_bulk(
    cantons: list[str] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Convenience function to run GWR bulk import.

    Args:
        cantons: List of canton codes (e.g., ["VD", "GE"])
        limit: Maximum number of buildings to import
        dry_run: If True, don't commit changes

    Returns:
        Import statistics
    """
    importer = GWRImporter()
    try:
        return await importer.import_bulk(cantons=cantons, limit=limit, dry_run=dry_run)
    finally:
        importer.close()
