"""
SwissBuildingOS - Generic Import Service (Programme L)

CSV/Excel generic importer for buildings, inventory items, and contacts.
Provides validation (preview + error reporting) and execution (bulk upsert).
"""

from __future__ import annotations

import csv
import io
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.contact import Contact
from app.models.inventory_item import InventoryItem

# ---------------------------------------------------------------------------
# Import schemas — define required/optional fields per entity type
# ---------------------------------------------------------------------------

IMPORT_SCHEMAS: dict[str, dict[str, Any]] = {
    "buildings": {
        "required": ["address", "city"],
        "optional": [
            "egid",
            "construction_year",
            "floors",
            "surface_m2",
            "building_type",
            "canton",
            "postal_code",
        ],
        "model": "Building",
    },
    "inventory": {
        "required": ["building_address", "item_type", "description"],
        "optional": [
            "installation_date",
            "warranty_end_date",
            "condition",
            "replacement_cost",
            "manufacturer",
            "model_number",
        ],
        "model": "InventoryItem",
    },
    "contacts": {
        "required": ["name", "email"],
        "optional": ["phone", "role", "organization", "address"],
        "model": "Contact",
    },
}

# Column name aliases for fuzzy mapping
_COLUMN_ALIASES: dict[str, str] = {
    "adresse": "address",
    "adress": "address",
    "rue": "address",
    "strasse": "address",
    "ville": "city",
    "stadt": "city",
    "ort": "city",
    "code_postal": "postal_code",
    "npa": "postal_code",
    "plz": "postal_code",
    "annee_construction": "construction_year",
    "baujahr": "construction_year",
    "year_built": "construction_year",
    "etages": "floors",
    "floors_above": "floors",
    "stockwerke": "floors",
    "surface": "surface_m2",
    "area": "surface_m2",
    "flache": "surface_m2",
    "type": "building_type",
    "typ": "building_type",
    "nom": "name",
    "vorname": "name",
    "courriel": "email",
    "e_mail": "email",
    "mail": "email",
    "telephone": "phone",
    "telefon": "phone",
    "tel": "phone",
    "fonction": "role",
    "rolle": "role",
    "organisation": "organization",
    "firma": "organization",
    "company": "organization",
    "adresse_building": "building_address",
    "batiment": "building_address",
    "gebaude": "building_address",
    "type_item": "item_type",
    "item": "item_type",
    "bezeichnung": "description",
    "beschreibung": "description",
    "date_installation": "installation_date",
    "date_garantie": "warranty_end_date",
    "etat": "condition",
    "zustand": "condition",
    "cout_remplacement": "replacement_cost",
    "fabricant": "manufacturer",
    "hersteller": "manufacturer",
    "modele": "model_number",
    "modell": "model_number",
    "kanton": "canton",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_csv(file_content: bytes) -> list[dict[str, str]]:
    """Parse CSV bytes into a list of row dicts."""
    text = file_content.decode("utf-8-sig")  # Handle BOM
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _parse_excel(file_content: bytes) -> list[dict[str, str]]:
    """Parse Excel bytes into a list of row dicts.

    Uses openpyxl if available, otherwise raises ValueError.
    """
    try:
        import openpyxl
    except ImportError:
        raise ValueError("Excel import requires openpyxl. Install with: pip install openpyxl") from None

    wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return []

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [str(h).strip() if h else "" for h in rows[0]]
    result = []
    for row in rows[1:]:
        row_dict = {}
        for idx, val in enumerate(row):
            if idx < len(headers) and headers[idx]:
                row_dict[headers[idx]] = str(val).strip() if val is not None else ""
        if any(v for v in row_dict.values()):  # skip completely empty rows
            result.append(row_dict)
    return result


def _normalize_column(col: str) -> str:
    """Normalize a column name to a canonical form."""
    normalized = col.strip().lower().replace(" ", "_").replace("-", "_")
    return _COLUMN_ALIASES.get(normalized, normalized)


def _auto_map_columns(detected: list[str], schema_fields: list[str]) -> dict[str, str]:
    """Auto-map detected column names to target schema fields."""
    mapping: dict[str, str] = {}
    for col in detected:
        normalized = _normalize_column(col)
        if normalized in schema_fields:
            mapping[col] = normalized
    return mapping


def _validate_row(
    row: dict[str, str],
    row_num: int,
    required: list[str],
    column_mapping: dict[str, str],
) -> list[dict[str, str]]:
    """Validate a single row, returning list of error dicts."""
    errors: list[dict[str, str]] = []
    # Build mapped row
    mapped = {}
    for src_col, target_field in column_mapping.items():
        mapped[target_field] = row.get(src_col, "").strip()

    for field in required:
        val = mapped.get(field, "").strip()
        if not val:
            errors.append({"row": str(row_num), "field": field, "error": f"Missing required field: {field}"})

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def validate_import(
    file_content: bytes,
    import_type: str,
    file_format: str = "csv",
) -> dict:
    """Validate an import file before processing.

    Returns validation result with row counts, errors, preview, and column mapping.
    """
    if import_type not in IMPORT_SCHEMAS:
        return {
            "valid": False,
            "rows_total": 0,
            "rows_valid": 0,
            "rows_with_errors": 0,
            "errors": [{"row": 0, "field": "import_type", "error": f"Unknown import type: {import_type}"}],
            "preview": [],
            "columns_detected": [],
            "columns_mapped": {},
        }

    schema = IMPORT_SCHEMAS[import_type]
    all_fields = schema["required"] + schema["optional"]

    # Parse file
    try:
        if file_format == "excel":
            rows = _parse_excel(file_content)
        else:
            rows = _parse_csv(file_content)
    except Exception as e:
        return {
            "valid": False,
            "rows_total": 0,
            "rows_valid": 0,
            "rows_with_errors": 0,
            "errors": [{"row": 0, "field": "file", "error": f"Parse error: {e!s}"}],
            "preview": [],
            "columns_detected": [],
            "columns_mapped": {},
        }

    if not rows:
        return {
            "valid": False,
            "rows_total": 0,
            "rows_valid": 0,
            "rows_with_errors": 0,
            "errors": [{"row": 0, "field": "file", "error": "File is empty or has no data rows"}],
            "preview": [],
            "columns_detected": [],
            "columns_mapped": {},
        }

    # Detect columns and auto-map
    columns_detected = list(rows[0].keys())
    columns_mapped = _auto_map_columns(columns_detected, all_fields)

    # Validate each row
    all_errors: list[dict[str, str]] = []
    rows_with_errors = 0

    for idx, row in enumerate(rows, start=1):
        row_errors = _validate_row(row, idx, schema["required"], columns_mapped)
        if row_errors:
            rows_with_errors += 1
            all_errors.extend(row_errors)

    rows_valid = len(rows) - rows_with_errors

    # Preview first 5 rows
    preview = rows[:5]

    return {
        "valid": rows_with_errors == 0,
        "rows_total": len(rows),
        "rows_valid": rows_valid,
        "rows_with_errors": rows_with_errors,
        "errors": all_errors,
        "preview": preview,
        "columns_detected": columns_detected,
        "columns_mapped": columns_mapped,
    }


async def execute_import(
    db: AsyncSession,
    file_content: bytes,
    import_type: str,
    org_id: UUID,
    column_mapping: dict[str, str] | None = None,
    *,
    file_format: str = "csv",
    created_by: UUID | None = None,
) -> dict:
    """Execute a validated import, creating records in the database.

    Returns import result with counts and created IDs.
    """
    if import_type not in IMPORT_SCHEMAS:
        return {
            "imported": 0,
            "skipped": 0,
            "errors": [{"row": 0, "error": f"Unknown type: {import_type}"}],
            "created_ids": [],
        }

    schema = IMPORT_SCHEMAS[import_type]
    all_fields = schema["required"] + schema["optional"]

    # Parse
    try:
        if file_format == "excel":
            rows = _parse_excel(file_content)
        else:
            rows = _parse_csv(file_content)
    except Exception as e:
        return {"imported": 0, "skipped": 0, "errors": [{"row": 0, "error": str(e)}], "created_ids": []}

    # Build column mapping if not provided
    if column_mapping is None:
        columns_detected = list(rows[0].keys()) if rows else []
        column_mapping = _auto_map_columns(columns_detected, all_fields)

    imported = 0
    skipped = 0
    errors: list[dict] = []
    created_ids: list[str] = []

    for idx, row in enumerate(rows, start=1):
        # Map columns
        mapped: dict[str, str] = {}
        for src_col, target_field in column_mapping.items():
            mapped[target_field] = row.get(src_col, "").strip()

        # Check required fields
        missing = [f for f in schema["required"] if not mapped.get(f, "").strip()]
        if missing:
            errors.append({"row": idx, "error": f"Missing required: {', '.join(missing)}"})
            skipped += 1
            continue

        try:
            record_id = uuid.uuid4()

            if import_type == "buildings":
                record = Building(
                    id=record_id,
                    address=mapped["address"],
                    city=mapped["city"],
                    postal_code=mapped.get("postal_code", "0000"),
                    canton=mapped.get("canton", "VD"),
                    construction_year=int(mapped["construction_year"]) if mapped.get("construction_year") else None,
                    floors_above=int(mapped["floors"]) if mapped.get("floors") else None,
                    surface_area_m2=float(mapped["surface_m2"]) if mapped.get("surface_m2") else None,
                    building_type=mapped.get("building_type", "residential"),
                    egid=int(mapped["egid"]) if mapped.get("egid") else None,
                    created_by=created_by or uuid.uuid4(),
                    organization_id=org_id,
                    status="active",
                    source_dataset="csv-import",
                )
                db.add(record)

            elif import_type == "inventory":
                # Look up building by address to link inventory
                building_addr = mapped.get("building_address", "")
                building_result = await db.execute(
                    select(Building).where(
                        Building.address == building_addr,
                        Building.organization_id == org_id,
                    )
                )
                building = building_result.scalar_one_or_none()
                if not building:
                    errors.append({"row": idx, "error": f"Building not found: {building_addr}"})
                    skipped += 1
                    continue

                record = InventoryItem(
                    id=record_id,
                    building_id=building.id,
                    item_type=mapped["item_type"],
                    name=mapped["description"],
                    manufacturer=mapped.get("manufacturer"),
                    model=mapped.get("model_number"),
                    condition=mapped.get("condition"),
                    replacement_cost_chf=float(mapped["replacement_cost"]) if mapped.get("replacement_cost") else None,
                    created_by=created_by,
                )
                db.add(record)

            elif import_type == "contacts":
                # Check for duplicate email in org
                existing = await db.execute(
                    select(Contact).where(
                        Contact.email == mapped["email"],
                        Contact.organization_id == org_id,
                    )
                )
                if existing.scalar_one_or_none():
                    errors.append({"row": idx, "error": f"Duplicate email: {mapped['email']}"})
                    skipped += 1
                    continue

                record = Contact(
                    id=record_id,
                    name=mapped["name"],
                    email=mapped["email"],
                    phone=mapped.get("phone"),
                    contact_type=mapped.get("role", "person"),
                    organization_id=org_id,
                    address=mapped.get("address"),
                    created_by=created_by,
                )
                db.add(record)

            created_ids.append(str(record_id))
            imported += 1

        except Exception as e:
            errors.append({"row": idx, "error": str(e)})
            skipped += 1

    await db.flush()

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "created_ids": created_ids,
    }
