"""
CECB Import Service — fetch real energy certificates from Swiss registries.

Strategy:
- Primary: geo.admin.ch energy layers (EGID lookup)
- Fallback: CSV batch import (cantonal registries)
- Upsert by EGID: enriches Building with cecb_* fields

The CECB (Certificat Energetique Cantonal des Batiments) provides the
official energy class (A-G) and demand breakdowns for Swiss buildings.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.services.enrichment.http_helpers import _retry_request, _throttle

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ENERGY_CLASSES = {"A", "B", "C", "D", "E", "F", "G"}

# geo.admin.ch MapServer identify — energy building layer
GEO_ADMIN_ENERGY_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
GEO_ADMIN_ENERGY_LAYER = "ch.bfe.fernwaerme-verbrauch"

# CECB canton download base (VD, GE — public CSV when available)
CECB_CANTON_SOURCES: dict[str, str] = {
    "VD": "CECB VD",
    "GE": "CECB GE",
    "BE": "CECB BE",
}


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class CECBRecord:
    """Normalized CECB record ready for upsert."""

    egid: int
    energy_class: str  # A-G
    heating_demand: float | None  # kWh/m²/an
    cooling_demand: float | None
    dhw_demand: float | None  # eau chaude sanitaire
    certificate_date: datetime | None
    source: str  # e.g. "CECB VD 2024"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_energy_class(raw: str | None) -> str | None:
    """Normalize an energy class value to A-G or None."""
    if not raw:
        return None
    cleaned = raw.strip().upper()[:1]
    return cleaned if cleaned in VALID_ENERGY_CLASSES else None


def parse_float(raw: Any) -> float | None:
    """Safely parse a float from various input types."""
    if raw is None:
        return None
    try:
        val = float(raw)
        return val if val >= 0 else None
    except (ValueError, TypeError):
        return None


def parse_cecb_from_geo_admin(feature: dict) -> CECBRecord | None:
    """Parse a geo.admin.ch feature into a CECBRecord."""
    attrs = feature.get("attributes") or feature.get("properties", {})
    egid = attrs.get("egid")
    if not egid:
        return None
    try:
        egid = int(egid)
    except (ValueError, TypeError):
        return None

    energy_class = parse_energy_class(attrs.get("energy_class") or attrs.get("classe_energie"))
    if not energy_class:
        return None

    return CECBRecord(
        egid=egid,
        energy_class=energy_class,
        heating_demand=parse_float(attrs.get("heating_demand") or attrs.get("besoin_chauffage")),
        cooling_demand=parse_float(attrs.get("cooling_demand") or attrs.get("besoin_refroidissement")),
        dhw_demand=parse_float(attrs.get("dhw_demand") or attrs.get("besoin_eau_chaude")),
        certificate_date=None,
        source="geo.admin.ch CECB",
    )


def parse_cecb_from_csv_row(row: dict[str, str], canton: str = "VD") -> CECBRecord | None:
    """Parse a CSV row (cantonal CECB export) into a CECBRecord.

    Expected columns (flexible — matches common cantonal export formats):
    - egid / EGID
    - classe / energy_class / classe_energie
    - chauffage / heating_demand / besoin_chauffage
    - refroidissement / cooling_demand / besoin_refroidissement
    - eau_chaude / dhw_demand / besoin_eau_chaude
    - date_certificat / certificate_date
    """

    def _get(keys: list[str]) -> str | None:
        for k in keys:
            val = row.get(k) or row.get(k.upper()) or row.get(k.lower())
            if val:
                return val.strip()
        return None

    raw_egid = _get(["egid", "EGID", "egid_batiment"])
    if not raw_egid:
        return None
    try:
        egid = int(raw_egid)
    except (ValueError, TypeError):
        return None

    energy_class = parse_energy_class(_get(["classe", "energy_class", "classe_energie", "klasse"]))
    if not energy_class:
        return None

    cert_date_raw = _get(["date_certificat", "certificate_date", "datum"])
    cert_date = None
    if cert_date_raw:
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                cert_date = datetime.strptime(cert_date_raw, fmt).replace(tzinfo=UTC)
                break
            except ValueError:
                continue

    source_label = CECB_CANTON_SOURCES.get(canton, f"CECB {canton}")
    year_suffix = cert_date.year if cert_date else datetime.now(UTC).year

    return CECBRecord(
        egid=egid,
        energy_class=energy_class,
        heating_demand=parse_float(_get(["chauffage", "heating_demand", "besoin_chauffage"])),
        cooling_demand=parse_float(_get(["refroidissement", "cooling_demand", "besoin_refroidissement"])),
        dhw_demand=parse_float(_get(["eau_chaude", "dhw_demand", "besoin_eau_chaude"])),
        certificate_date=cert_date,
        source=f"{source_label} {year_suffix}",
    )


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


async def fetch_cecb_by_egid(egid: int) -> CECBRecord | None:
    """Attempt to fetch CECB data for a single EGID from geo.admin.ch.

    Returns None if not found or on error.
    """
    await _throttle()
    params = {
        "geometryType": "esriGeometryPoint",
        "geometry": "",
        "layers": f"all:{GEO_ADMIN_ENERGY_LAYER}",
        "mapExtent": "0,0,1,1",
        "imageDisplay": "1,1,96",
        "tolerance": 0,
        "sr": 2056,
        "searchText": str(egid),
        "searchField": "egid",
        "returnGeometry": "false",
        "lang": "fr",
        "f": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp, _retries = await _retry_request(client, "GET", GEO_ADMIN_ENERGY_URL, params=params)
            if resp.status_code != 200:
                logger.warning("geo.admin CECB lookup failed for EGID %d: HTTP %d", egid, resp.status_code)
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None

            return parse_cecb_from_geo_admin(results[0])

    except Exception:
        logger.exception("Error fetching CECB for EGID %d", egid)
        return None


def parse_cecb_csv(csv_content: str, canton: str = "VD") -> list[CECBRecord]:
    """Parse a full CSV file into a list of CECBRecords.

    Skips rows that cannot be parsed (missing EGID, missing class).
    """
    records: list[CECBRecord] = []
    reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")
    for row in reader:
        record = parse_cecb_from_csv_row(row, canton=canton)
        if record:
            records.append(record)
    return records


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


async def upsert_cecb_record(
    db: AsyncSession,
    record: CECBRecord,
) -> bool:
    """Upsert a CECBRecord into the Building table by EGID.

    Returns True if a building was found and updated, False otherwise.
    """
    stmt = select(Building).where(Building.egid == record.egid)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()

    if building is None:
        logger.debug("CECB: no building found for EGID %d, skipping", record.egid)
        return False

    building.cecb_class = record.energy_class
    building.cecb_heating_demand = record.heating_demand
    building.cecb_cooling_demand = record.cooling_demand
    building.cecb_dhw_demand = record.dhw_demand
    building.cecb_certificate_date = record.certificate_date
    building.cecb_fetch_date = datetime.now(UTC)
    building.cecb_source = record.source

    db.add(building)
    return True


async def import_cecb_batch(
    db: AsyncSession,
    records: list[CECBRecord],
) -> dict[str, int]:
    """Import a batch of CECB records, upserting by EGID.

    Returns stats: {updated, skipped, errors}.
    """
    stats = {"updated": 0, "skipped": 0, "errors": 0}
    for record in records:
        try:
            updated = await upsert_cecb_record(db, record)
            if updated:
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        except Exception:
            logger.exception("Error upserting CECB record for EGID %d", record.egid)
            stats["errors"] += 1

    await db.flush()
    return stats


async def import_cecb_for_missing(
    db: AsyncSession,
    limit: int = 100,
) -> dict[str, int]:
    """Find buildings without CECB data and attempt to fetch from geo.admin.ch.

    Limits to `limit` buildings per run to avoid overload.
    Returns stats: {updated, skipped, errors, total_checked}.
    """
    stmt = (
        select(Building)
        .where(
            Building.egid.isnot(None),
            Building.cecb_class.is_(None),
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    buildings = list(result.scalars().all())

    stats = {"updated": 0, "skipped": 0, "errors": 0, "total_checked": len(buildings)}

    for building in buildings:
        try:
            record = await fetch_cecb_by_egid(building.egid)
            if record:
                updated = await upsert_cecb_record(db, record)
                if updated:
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                stats["skipped"] += 1
        except Exception:
            logger.exception("Error importing CECB for EGID %d", building.egid)
            stats["errors"] += 1

    await db.flush()
    return stats
