from __future__ import annotations

import argparse
import asyncio
import json
import unicodedata
import uuid as _uuid
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

import httpx

from app.constants import SOURCE_DATASET_VAUD_PUBLIC

ARCGIS_BASE_URL = "https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/Mapserver"
ADDRESS_LAYER_ID = 241
RCB_LAYER_ID = 39
BATIMENT_LAYER_ID = 276
DEFAULT_TIMEOUT = 30.0
T = TypeVar("T")

# Capture all available fields from each layer
_ADDRESS_OUT_FIELDS = "*"
_RCB_OUT_FIELDS = "*"

# Fields that influence risk scoring — upsert must recalculate when these change
_RISK_INFLUENCING_FIELDS = ("construction_year", "building_type", "canton")


@dataclass(slots=True)
class AddressRecord:
    object_id: int
    egid: int
    edid: int | None
    street: str | None
    house_number: str | None
    postal_code: str
    locality: str
    commune: str
    municipality_ofs: int | None = None
    raw_attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RcbRecord:
    egid: int
    building_number: str | None
    category: str | None
    building_class: str | None
    status: str | None
    construction_year: int | None
    construction_period: str | None
    ground_surface_m2: float | None
    floors_total: int | None
    sre_m2: float | None
    heating_system: str | None
    heating_energy: str | None
    heating2_system: str | None
    heating2_energy: str | None
    hot_water_system: str | None
    hot_water_energy: str | None
    hot_water2_system: str | None
    hot_water2_energy: str | None
    shelter_pci: str | None
    camac_number: str | None
    latitude: float | None
    longitude: float | None
    raw_attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NormalizedBuildingRecord:
    egid: int
    official_id: str
    address: str
    postal_code: str
    city: str
    canton: str
    municipality_ofs: int | None
    latitude: float | None
    longitude: float | None
    construction_year: int | None
    building_type: str
    floors_above: int | None
    surface_area_m2: float | None
    source_metadata: dict[str, Any]

    def to_building_create_payload(self) -> dict[str, Any]:
        return {
            "egrid": None,
            "egid": self.egid,
            "official_id": self.official_id,
            "address": self.address,
            "postal_code": self.postal_code,
            "city": self.city,
            "canton": self.canton,
            "municipality_ofs": self.municipality_ofs,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "parcel_number": None,
            "construction_year": self.construction_year,
            "renovation_year": None,
            "building_type": self.building_type,
            "floors_above": self.floors_above,
            "floors_below": None,
            "surface_area_m2": self.surface_area_m2,
            "volume_m3": None,
            "owner_id": None,
            "source_dataset": SOURCE_DATASET_VAUD_PUBLIC,
            "source_imported_at": datetime.now(UTC),
            "source_metadata_json": self.source_metadata,
        }


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = text.encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().split())


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _chunks(values: Iterable[int], size: int) -> Iterable[list[int]]:
    batch: list[int] = []
    for value in values:
        batch.append(value)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _strip_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def build_address_where(
    commune: str | None,
    municipality_ofs: int | None,
    postal_code: str | None,
) -> str:
    clauses: list[str] = []
    if municipality_ofs is not None:
        clauses.append(f"NUM_COM_OFS = {municipality_ofs}")
    if commune:
        clauses.append(f"COMMUNE = '{_escape_sql_literal(commune)}'")
    if postal_code:
        clauses.append(f"NPA = {int(postal_code)}")
    return " AND ".join(clauses) if clauses else "1=1"


def build_address_line(street: str | None, house_number: str | None) -> str:
    parts = [part.strip() for part in [street or "", house_number or ""] if part and part.strip()]
    return " ".join(parts)


def map_building_type(category: str | None, building_class: str | None) -> str:
    category_norm = _normalize_text(category)
    class_norm = _normalize_text(building_class)
    combined = f"{category_norm} {class_norm}".strip()

    if "exclusivement" in category_norm and "habitation" in category_norm:
        return "residential"
    if "partiellement" in category_norm and "habitation" in category_norm:
        return "mixed"

    public_keywords = (
        "culturel",
        "recreatif",
        "educatif",
        "sanitaire",
        "ecole",
        "administration",
        "hospital",
        "sante",
        "public",
        "collectiv",
        "sport",
        "relig",
    )
    industrial_keywords = (
        "industri",
        "artisan",
        "agricol",
        "exploitation",
        "atelier",
        "usine",
        "entrepot",
        "logistique",
        "hangar",
        "depot",
        "technique",
    )
    commercial_keywords = (
        "commercial",
        "commerce",
        "bureau",
        "vente",
        "hotel",
        "restaurant",
        "service",
        "gare",
        "parking",
        "banque",
    )

    if any(keyword in combined for keyword in public_keywords):
        return "public"
    if any(keyword in combined for keyword in industrial_keywords):
        return "industrial"
    if any(keyword in combined for keyword in commercial_keywords):
        return "commercial"
    if "sans usage d'habitation" in (category or "").lower():
        return "commercial"
    if "habitation" in combined:
        return "residential"
    return "mixed"


def _address_rank(record: AddressRecord) -> tuple[int, int, int]:
    return (
        0 if record.edid == 0 else 1,
        0 if record.house_number else 1,
        record.object_id,
    )


def pick_primary_addresses(records: Iterable[AddressRecord], limit: int | None = None) -> list[AddressRecord]:
    selected: OrderedDict[int, AddressRecord] = OrderedDict()
    for record in records:
        current = selected.get(record.egid)
        if current is None or _address_rank(record) < _address_rank(current):
            selected[record.egid] = record
    result = list(selected.values())
    if limit is not None:
        return result[:limit]
    return result


def _build_source_metadata(
    primary_address: AddressRecord,
    all_addresses: list[AddressRecord],
    rcb: RcbRecord,
    *,
    batiment: dict[str, Any] | None = None,
    batch_id: str | None = None,
) -> dict[str, Any]:
    # Separate geometry from RCB attrs for clarity
    rcb_raw = dict(rcb.raw_attrs)
    rcb_geometry = rcb_raw.pop("_geometry", None)

    source_layers: dict[str, str] = {
        "address": f"vd.adresse (layer {ADDRESS_LAYER_ID})",
        "rcb": f"vd.batiment_rcb (layer {RCB_LAYER_ID})",
    }
    if batiment is not None:
        source_layers["batiment"] = f"vd.batiment (layer {BATIMENT_LAYER_ID})"

    meta: dict[str, Any] = {
        "source_layers": source_layers,
        "address_primary": _strip_none(primary_address.raw_attrs) or None,
        "addresses": [_strip_none(a.raw_attrs) for a in all_addresses if a.raw_attrs],
        "rcb_raw": _strip_none(rcb_raw) or None,
    }
    if rcb_geometry:
        meta["rcb_geometry"] = rcb_geometry
    if batiment is not None:
        meta["batiment"] = batiment
    if batch_id:
        meta["batch_id"] = batch_id
    return {k: v for k, v in meta.items() if v is not None}


def normalize_building_record(
    address: AddressRecord,
    rcb: RcbRecord,
    *,
    municipality_ofs: int | None = None,
    all_addresses: list[AddressRecord] | None = None,
    batiment: dict[str, Any] | None = None,
    batch_id: str | None = None,
) -> NormalizedBuildingRecord | None:
    status_norm = _normalize_text(rcb.status)
    if status_norm and status_norm != "existant":
        return None

    address_line = build_address_line(address.street, address.house_number)
    if not address_line:
        return None

    surface_area = rcb.sre_m2 if rcb.sre_m2 not in (None, 0) else rcb.ground_surface_m2
    source_metadata = _build_source_metadata(
        address,
        all_addresses or [address],
        rcb,
        batiment=batiment,
        batch_id=batch_id,
    )

    return NormalizedBuildingRecord(
        egid=rcb.egid,
        official_id=str(rcb.egid),
        address=address_line,
        postal_code=address.postal_code,
        city=address.locality,
        canton="VD",
        municipality_ofs=municipality_ofs,
        latitude=rcb.latitude,
        longitude=rcb.longitude,
        construction_year=rcb.construction_year,
        building_type=map_building_type(rcb.category, rcb.building_class),
        floors_above=rcb.floors_total,
        surface_area_m2=surface_area,
        source_metadata=source_metadata,
    )


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


async def _request_json(
    client: httpx.AsyncClient,
    path: str,
    params: dict[str, Any],
    *,
    retries: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # pragma: no cover - network failure branch
            last_error = exc
            if attempt == retries:
                raise
            await asyncio.sleep(0.25 * attempt)
    raise RuntimeError(f"Request failed without explicit exception: {last_error}")


def _layer_query_path(layer_id: int) -> str:
    return f"{ARCGIS_BASE_URL}/{layer_id}/query"


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------


async def fetch_object_ids(
    client: httpx.AsyncClient,
    *,
    layer_id: int,
    where: str,
) -> list[int]:
    data = await _request_json(
        client,
        _layer_query_path(layer_id),
        {
            "where": where,
            "returnIdsOnly": "true",
            "f": "json",
        },
    )
    return list(data.get("objectIds") or [])


async def fetch_address_record(client: httpx.AsyncClient, object_id: int) -> AddressRecord | None:
    data = await _request_json(
        client,
        _layer_query_path(ADDRESS_LAYER_ID),
        {
            "where": f"OBJECTID = {object_id}",
            "outFields": _ADDRESS_OUT_FIELDS,
            "returnGeometry": "false",
            "f": "json",
        },
    )
    features = data.get("features") or []
    if not features:
        return None
    attrs = features[0]["attributes"]
    egid = attrs.get("EGID")
    if egid is None:
        return None
    postal_code = attrs.get("NPA")
    locality = (attrs.get("LOCALITE") or "").strip()
    commune = (attrs.get("COMMUNE") or "").strip()
    if postal_code in (None, "") or not locality:
        return None
    return AddressRecord(
        object_id=int(attrs["OBJECTID"]),
        egid=int(egid),
        edid=int(attrs["EDID"]) if attrs.get("EDID") is not None else None,
        street=(attrs.get("VOIE_TXT") or "").strip() or None,
        house_number=(attrs.get("NO_ENTREE") or "").strip() or None,
        postal_code=str(postal_code).zfill(4),
        locality=locality,
        commune=commune,
        municipality_ofs=int(attrs["NUM_COM_OFS"]) if attrs.get("NUM_COM_OFS") is not None else None,
        raw_attrs=dict(attrs),
    )


async def fetch_rcb_record(client: httpx.AsyncClient, egid: int) -> RcbRecord | None:
    data = await _request_json(
        client,
        _layer_query_path(RCB_LAYER_ID),
        {
            "where": f"EGID = {egid}",
            "outFields": _RCB_OUT_FIELDS,
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "json",
        },
    )
    features = data.get("features") or []
    if not features:
        return None
    feature = features[0]
    attrs = feature["attributes"]
    geom = feature.get("geometry") or {}

    def _str(key: str) -> str | None:
        v = attrs.get(key)
        return v.strip() or None if isinstance(v, str) else None

    def _int(key: str) -> int | None:
        v = attrs.get(key)
        return int(v) if v is not None else None

    def _float(key: str) -> float | None:
        v = attrs.get(key)
        return float(v) if v is not None else None

    # Store all attrs + geometry together for complete raw capture
    raw = dict(attrs)
    if geom:
        raw["_geometry"] = dict(geom)

    return RcbRecord(
        egid=int(attrs["EGID"]),
        building_number=_str("NO_CADASTR"),
        category=_str("CATEGORIE_TXT"),
        building_class=_str("CLASSE_TXT"),
        status=_str("STATUT_TXT"),
        construction_year=_int("CONS_ANNEE"),
        construction_period=_str("CONS_PERIO_TXT"),
        ground_surface_m2=_float("SURFACE"),
        floors_total=_int("NB_NIV_TOT"),
        sre_m2=_float("SRE"),
        heating_system=_str("CHAUF1_SYS_TXT"),
        heating_energy=_str("CHAUF1_NRG_TXT"),
        heating2_system=_str("CHAUF2_SYS_TXT"),
        heating2_energy=_str("CHAUF2_NRG_TXT"),
        hot_water_system=_str("EAU1_SYS_TXT"),
        hot_water_energy=_str("EAU1_NRG_TXT"),
        hot_water2_system=_str("EAU2_SYS_TXT"),
        hot_water2_energy=_str("EAU2_NRG_TXT"),
        shelter_pci=_str("ABRI_PCI"),
        camac_number=_str("NO_CAMAC"),
        longitude=float(geom["x"]) if geom.get("x") is not None else None,
        latitude=float(geom["y"]) if geom.get("y") is not None else None,
        raw_attrs=raw,
    )


async def fetch_batiment_record(client: httpx.AsyncClient, egid: int) -> dict[str, Any] | None:
    """Fetch polygon footprint + cadastral attrs from vd.batiment (layer 276) by EGID."""
    data = await _request_json(
        client,
        _layer_query_path(BATIMENT_LAYER_ID),
        {
            "where": f"EGID = {egid}",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "json",
        },
    )
    features = data.get("features") or []
    if not features:
        return None
    feature = features[0]
    attrs = dict(feature.get("attributes") or {})
    geom = feature.get("geometry")
    result: dict[str, Any] = {"attributes": attrs}
    if geom:
        result["geometry"] = geom
    return result


async def _gather_in_chunks(
    values: Iterable[int],
    worker: Callable[[int], Awaitable[T | None]],
    *,
    chunk_size: int,
) -> list[T]:
    results: list[T] = []
    for chunk in _chunks(values, chunk_size):
        batch = await asyncio.gather(*(worker(value) for value in chunk))
        results.extend(item for item in batch if item is not None)
    return results


# ---------------------------------------------------------------------------
# Harvest
# ---------------------------------------------------------------------------


async def _fetch_all_addresses_for_egid(
    client: httpx.AsyncClient,
    egid: int,
    *,
    layer_id: int = ADDRESS_LAYER_ID,
) -> list[AddressRecord]:
    """Fetch all address records for a given EGID via objectIds query + per-record fetch."""
    oids = await fetch_object_ids(client, layer_id=layer_id, where=f"EGID = {egid}")
    if not oids:
        return []
    results: list[AddressRecord] = []
    for oid in oids:
        record = await fetch_address_record(client, oid)
        if record is not None:
            results.append(record)
    return results


async def harvest_vd_buildings(
    *,
    commune: str | None,
    municipality_ofs: int | None,
    postal_code: str | None,
    limit: int,
    concurrency: int,
) -> tuple[list[NormalizedBuildingRecord], dict[str, int]]:
    where = build_address_where(commune, municipality_ofs, postal_code)
    batch_id = _uuid.uuid4().hex[:12]

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        address_object_ids = await fetch_object_ids(client, layer_id=ADDRESS_LAYER_ID, where=where)
        if not address_object_ids:
            return [], {"address_ids": 0, "address_records": 0, "unique_egids": 0, "normalized": 0, "skipped": 0}

        target_unique = max(limit * 3, limit)

        # Phase 1: scan address OIDs to discover unique EGIDs
        all_addresses_by_egid: dict[int, list[AddressRecord]] = {}
        primary_by_egid: OrderedDict[int, AddressRecord] = OrderedDict()

        for chunk in _chunks(address_object_ids, max(1, concurrency)):
            fetched = await asyncio.gather(*(fetch_address_record(client, oid) for oid in chunk))
            for record in fetched:
                if record is None:
                    continue
                all_addresses_by_egid.setdefault(record.egid, []).append(record)
                current = primary_by_egid.get(record.egid)
                if current is None or _address_rank(record) < _address_rank(current):
                    primary_by_egid[record.egid] = record
            if len(primary_by_egid) >= target_unique:
                break

        # Phase 2: for each selected EGID, ensure we have ALL its addresses
        # (phase 1 may have missed some if the scan stopped early)
        selected_egids = list(primary_by_egid.keys())[:target_unique]
        for egid_chunk in _chunks(selected_egids, max(1, concurrency)):
            tasks = []
            egids_to_complete: list[int] = []
            for egid in egid_chunk:
                # Only refetch if we might have incomplete data
                # (we have addresses but the scan may have stopped before seeing all OIDs)
                egids_to_complete.append(egid)
                tasks.append(_fetch_all_addresses_for_egid(client, egid))
            if tasks:
                results = await asyncio.gather(*tasks)
                for egid, full_addresses in zip(egids_to_complete, results, strict=False):
                    if full_addresses:
                        # Merge: keep all unique addresses by object_id
                        existing_oids = {a.object_id for a in all_addresses_by_egid.get(egid, [])}
                        for addr in full_addresses:
                            if addr.object_id not in existing_oids:
                                all_addresses_by_egid.setdefault(egid, []).append(addr)
                                existing_oids.add(addr.object_id)
                        # Update primary if a better one was found
                        for addr in full_addresses:
                            current = primary_by_egid.get(egid)
                            if current is None or _address_rank(addr) < _address_rank(current):
                                primary_by_egid[egid] = addr

        selected_primaries = [primary_by_egid[egid] for egid in selected_egids]
        rcb_records = await _gather_in_chunks(
            selected_egids,
            lambda egid: fetch_rcb_record(client, egid),
            chunk_size=max(1, concurrency),
        )
        batiment_records = await _gather_in_chunks(
            selected_egids,
            lambda egid: fetch_batiment_record(client, egid),
            chunk_size=max(1, concurrency),
        )

    normalized: list[NormalizedBuildingRecord] = []
    skipped = 0
    for address_record, rcb_record, bat_record in zip(selected_primaries, rcb_records, batiment_records, strict=False):
        if rcb_record is None:
            skipped += 1
            continue
        normalized_record = normalize_building_record(
            address_record,
            rcb_record,
            municipality_ofs=address_record.municipality_ofs,
            all_addresses=all_addresses_by_egid.get(address_record.egid),
            batiment=bat_record,
            batch_id=batch_id,
        )
        if normalized_record is None:
            skipped += 1
            continue
        normalized.append(normalized_record)
        if len(normalized) >= limit:
            break

    stats = {
        "address_ids": len(address_object_ids),
        "address_records": sum(len(v) for v in all_addresses_by_egid.values()),
        "unique_egids": len(primary_by_egid),
        "normalized": len(normalized),
        "skipped": skipped,
    }
    return normalized, stats


# ---------------------------------------------------------------------------
# Apply (upsert by EGID)
# ---------------------------------------------------------------------------

# Business fields: used to determine if a record has meaningfully changed
_UPSERT_BUSINESS_FIELDS = (
    "official_id",
    "address",
    "postal_code",
    "city",
    "canton",
    "municipality_ofs",
    "latitude",
    "longitude",
    "construction_year",
    "building_type",
    "floors_above",
    "surface_area_m2",
    "source_dataset",
)

# Provenance fields: always updated silently (don't count as "changed")
_UPSERT_PROVENANCE_FIELDS = (
    "source_imported_at",
    "source_metadata_json",
)


async def apply_records(
    records: list[NormalizedBuildingRecord],
    *,
    created_by_email: str,
) -> tuple[int, int, int]:
    """Returns (created, updated, unchanged)."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.building import Building
    from app.models.user import User
    from app.schemas.building import BuildingCreate
    from app.services.building_service import create_building
    from app.services.risk_engine import update_risk_score

    async with AsyncSessionLocal() as db:
        user_result = await db.execute(select(User).where(User.email == created_by_email))
        user = user_result.scalar_one_or_none()
        if user is None:
            raise RuntimeError(
                f"Created-by user not found: {created_by_email}. Seed the demo users first or pass another email."
            )

        created = 0
        updated = 0
        unchanged = 0
        for record in records:
            payload = record.to_building_create_payload()

            existing_result = await db.execute(select(Building).where(Building.egid == record.egid))
            existing = existing_result.scalar_one_or_none()

            if existing is not None:
                changed = False
                risk_changed = False
                for field_name in _UPSERT_BUSINESS_FIELDS:
                    new_value = payload.get(field_name)
                    old_value = getattr(existing, field_name, None)
                    if new_value != old_value:
                        setattr(existing, field_name, new_value)
                        changed = True
                        if field_name in _RISK_INFLUENCING_FIELDS:
                            risk_changed = True
                # Always update provenance fields silently
                for field_name in _UPSERT_PROVENANCE_FIELDS:
                    new_value = payload.get(field_name)
                    setattr(existing, field_name, new_value)
                if changed:
                    await db.commit()
                    if risk_changed:
                        await update_risk_score(db, existing.id)
                        await db.commit()
                    updated += 1
                else:
                    await db.commit()
                    unchanged += 1
                continue

            bc = BuildingCreate(**payload)
            await create_building(db, bc, user.id)
            created += 1

    return created, updated, unchanged


def write_output_json(records: list[NormalizedBuildingRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _serialize(record: NormalizedBuildingRecord) -> dict[str, Any]:
        d = asdict(record)
        return d

    output_path.write_text(
        json.dumps([_serialize(r) for r in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch a small PoC dataset of Vaud public building data from official public geoservices "
            "and optionally import it into SwissBuilding."
        )
    )
    parser.add_argument("--commune", help="Municipality name as exposed by the public address layer, e.g. Lausanne.")
    parser.add_argument("--municipality-ofs", type=int, help="Federal municipality code (NUM_COM_OFS).")
    parser.add_argument("--postal-code", help="Optional postal code filter.")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of normalized buildings to harvest. Default: 100.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=12,
        help="Concurrent requests used while harvesting the public layers. Default: 12.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path where the normalized records will be written as JSON.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Import the normalized buildings into the local SwissBuilding database.",
    )
    parser.add_argument(
        "--created-by-email",
        default="admin@swissbuildingos.ch",
        help="User email used as created_by when --apply is set. Default: admin@swissbuildingos.ch.",
    )
    args = parser.parse_args()
    if not any([args.commune, args.municipality_ofs, args.postal_code]):
        parser.error("Provide at least one filter: --commune, --municipality-ofs, or --postal-code.")
    if args.limit <= 0:
        parser.error("--limit must be > 0.")
    if args.concurrency <= 0:
        parser.error("--concurrency must be > 0.")
    return args


async def async_main() -> int:
    args = parse_args()
    records, stats = await harvest_vd_buildings(
        commune=args.commune,
        municipality_ofs=args.municipality_ofs,
        postal_code=args.postal_code,
        limit=args.limit,
        concurrency=args.concurrency,
    )

    print(
        "[vaud-public] Harvested "
        f"{stats['normalized']} buildings "
        f"(address ids={stats['address_ids']}, unique egids={stats['unique_egids']}, skipped={stats['skipped']})."
    )

    if not records:
        print("[vaud-public] No normalized buildings matched the requested filters.")
        return 1

    if args.output_json:
        write_output_json(records, args.output_json)
        print(f"[vaud-public] Wrote normalized JSON to {args.output_json}")

    for sample in records[: min(3, len(records))]:
        print(
            "[vaud-public] Sample: "
            f"EGID={sample.egid} | {sample.address}, {sample.postal_code} {sample.city} | "
            f"{sample.building_type} | year={sample.construction_year}"
        )

    if args.apply:
        created, updated, unchanged = await apply_records(
            records,
            created_by_email=args.created_by_email,
        )
        print(f"[vaud-public] Apply completed: created={created}, updated={updated}, unchanged={unchanged}")

    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
