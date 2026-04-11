"""Tests for the Generic Import Service (Programme L)."""

import uuid

import pytest

from app.models.building import Building
from app.models.contact import Contact
from app.services.generic_import_service import (
    IMPORT_SCHEMAS,
    execute_import,
    validate_import,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ORG_ID = uuid.uuid4()
_USER_ID = uuid.uuid4()


def _csv_bytes(header: str, *rows: str) -> bytes:
    """Build CSV content bytes from header and row strings."""
    lines = [header, *list(rows)]
    return "\n".join(lines).encode("utf-8")


def _make_building(db_session, *, address="Rue Test 1", org_id=_ORG_ID, created_by=None):
    b = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=created_by or uuid.uuid4(),
        organization_id=org_id,
        status="active",
    )
    db_session.add(b)
    return b


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_buildings_csv_valid():
    """Valid buildings CSV passes validation."""
    content = _csv_bytes(
        "address,city,canton,postal_code",
        "Rue du Lac 1,Lausanne,VD,1000",
        "Bahnhofstrasse 10,Zurich,ZH,8001",
    )
    result = await validate_import(content, "buildings")
    assert result["valid"] is True
    assert result["rows_total"] == 2
    assert result["rows_valid"] == 2
    assert result["rows_with_errors"] == 0
    assert len(result["preview"]) == 2
    assert "address" in result["columns_mapped"].values()
    assert "city" in result["columns_mapped"].values()


@pytest.mark.asyncio
async def test_validate_buildings_csv_missing_required():
    """CSV with missing required fields reports errors."""
    content = _csv_bytes(
        "address,canton",
        "Rue du Lac 1,VD",  # missing city
    )
    result = await validate_import(content, "buildings")
    assert result["valid"] is False
    assert result["rows_with_errors"] == 1
    assert any(e["field"] == "city" for e in result["errors"])


@pytest.mark.asyncio
async def test_validate_unknown_import_type():
    """Unknown import type returns immediate error."""
    content = _csv_bytes("col1,col2", "a,b")
    result = await validate_import(content, "nonexistent")
    assert result["valid"] is False
    assert any("Unknown import type" in e["error"] for e in result["errors"])


@pytest.mark.asyncio
async def test_validate_empty_file():
    """Empty file returns error."""
    result = await validate_import(b"", "buildings")
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_validate_column_mapping_aliases():
    """French column names are auto-mapped to canonical fields."""
    content = _csv_bytes(
        "adresse,ville,kanton",
        "Rue du Lac 1,Lausanne,VD",
    )
    result = await validate_import(content, "buildings")
    assert result["valid"] is True
    assert result["columns_mapped"].get("adresse") == "address"
    assert result["columns_mapped"].get("ville") == "city"
    assert result["columns_mapped"].get("kanton") == "canton"


@pytest.mark.asyncio
async def test_validate_contacts_csv():
    """Contacts CSV with valid data passes."""
    content = _csv_bytes(
        "name,email,phone,role",
        "Jean Dupont,jean@example.ch,+41791234567,person",
        "Marie Curie,marie@example.ch,,person",
    )
    result = await validate_import(content, "contacts")
    assert result["valid"] is True
    assert result["rows_total"] == 2


@pytest.mark.asyncio
async def test_validate_preview_max_5_rows():
    """Preview contains at most 5 rows even with large file."""
    rows = [f"Rue {i},Ville {i}" for i in range(20)]
    content = _csv_bytes("address,city", *rows)
    result = await validate_import(content, "buildings")
    assert len(result["preview"]) == 5


# ---------------------------------------------------------------------------
# Execute import tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_building_import(db_session, admin_user):
    """Buildings are created from valid CSV."""
    content = _csv_bytes(
        "address,city,canton,postal_code,building_type",
        "Rue du Lac 1,Lausanne,VD,1000,residential",
        "Bahnhofstrasse 10,Zurich,ZH,8001,commercial",
    )
    result = await execute_import(
        db_session,
        content,
        "buildings",
        _ORG_ID,
        created_by=admin_user.id,
    )
    assert result["imported"] == 2
    assert result["skipped"] == 0
    assert len(result["created_ids"]) == 2
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_execute_import_skips_bad_rows(db_session, admin_user):
    """Rows missing required fields are skipped."""
    content = _csv_bytes(
        "address,city",
        "Rue du Lac 1,Lausanne",
        ",",  # missing address and city
    )
    result = await execute_import(
        db_session,
        content,
        "buildings",
        _ORG_ID,
        created_by=admin_user.id,
    )
    assert result["imported"] == 1
    assert result["skipped"] == 1
    assert len(result["errors"]) == 1


@pytest.mark.asyncio
async def test_execute_contact_import_duplicate_detection(db_session, admin_user):
    """Duplicate emails within the same org are detected and skipped."""
    # Pre-create a contact
    existing = Contact(
        id=uuid.uuid4(),
        name="Existing",
        email="existing@example.ch",
        contact_type="person",
        organization_id=_ORG_ID,
    )
    db_session.add(existing)
    await db_session.commit()

    content = _csv_bytes(
        "name,email",
        "New Person,new@example.ch",
        "Duplicate,existing@example.ch",
    )
    result = await execute_import(
        db_session,
        content,
        "contacts",
        _ORG_ID,
        created_by=admin_user.id,
    )
    assert result["imported"] == 1
    assert result["skipped"] == 1
    assert any("Duplicate email" in e["error"] for e in result["errors"])


@pytest.mark.asyncio
async def test_execute_inventory_import_building_lookup(db_session, admin_user):
    """Inventory import looks up building by address."""
    _make_building(db_session, address="Rue du Lac 1", org_id=_ORG_ID, created_by=admin_user.id)
    await db_session.commit()

    content = _csv_bytes(
        "building_address,item_type,description",
        "Rue du Lac 1,boiler,Chaudiere principale",
    )
    result = await execute_import(
        db_session,
        content,
        "inventory",
        _ORG_ID,
        created_by=admin_user.id,
    )
    assert result["imported"] == 1
    assert result["skipped"] == 0


@pytest.mark.asyncio
async def test_execute_inventory_import_building_not_found(db_session, admin_user):
    """Inventory import skips row when building address not found."""
    content = _csv_bytes(
        "building_address,item_type,description",
        "Nonexistent Address,boiler,Chaudiere",
    )
    result = await execute_import(
        db_session,
        content,
        "inventory",
        _ORG_ID,
        created_by=admin_user.id,
    )
    assert result["imported"] == 0
    assert result["skipped"] == 1
    assert any("Building not found" in e["error"] for e in result["errors"])


@pytest.mark.asyncio
async def test_import_schemas_structure():
    """Import schemas have correct structure."""
    for _name, schema in IMPORT_SCHEMAS.items():
        assert "required" in schema
        assert "optional" in schema
        assert "model" in schema
        assert isinstance(schema["required"], list)
        assert isinstance(schema["optional"], list)
        assert len(schema["required"]) > 0
