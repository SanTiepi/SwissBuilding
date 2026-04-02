"""Tests for the CECB import service — parsing, upsert, and energy class priority."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.building import Building
from app.services.cecb_import_service import (
    CECBRecord,
    import_cecb_batch,
    import_cecb_for_missing,
    parse_cecb_csv,
    parse_cecb_from_csv_row,
    parse_cecb_from_geo_admin,
    parse_energy_class,
    parse_float,
    upsert_cecb_record,
)
from app.services.energy_performance_service import estimate_energy_class

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(
    db_session,
    admin_user,
    egid=None,
    construction_year=1965,
    cecb_class=None,
    cecb_heating_demand=None,
    cecb_source=None,
):
    bld = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        egid=egid,
        cecb_class=cecb_class,
        cecb_heating_demand=cecb_heating_demand,
        cecb_source=cecb_source,
    )
    db_session.add(bld)
    await db_session.commit()
    await db_session.refresh(bld)
    return bld


# ---------------------------------------------------------------------------
# parse_energy_class
# ---------------------------------------------------------------------------


class TestParseEnergyClass:
    def test_valid_classes(self):
        for c in "ABCDEFG":
            assert parse_energy_class(c) == c

    def test_lowercase(self):
        assert parse_energy_class("b") == "B"

    def test_with_whitespace(self):
        assert parse_energy_class("  C  ") == "C"

    def test_invalid_class(self):
        assert parse_energy_class("H") is None
        assert parse_energy_class("X") is None

    def test_empty_string(self):
        assert parse_energy_class("") is None

    def test_none(self):
        assert parse_energy_class(None) is None


# ---------------------------------------------------------------------------
# parse_float
# ---------------------------------------------------------------------------


class TestParseFloat:
    def test_valid_float(self):
        assert parse_float("42.5") == 42.5

    def test_valid_int(self):
        assert parse_float(100) == 100.0

    def test_zero(self):
        assert parse_float(0) == 0.0

    def test_negative(self):
        assert parse_float(-5.0) is None

    def test_none(self):
        assert parse_float(None) is None

    def test_invalid_string(self):
        assert parse_float("n/a") is None


# ---------------------------------------------------------------------------
# parse_cecb_from_geo_admin
# ---------------------------------------------------------------------------


class TestParseCECBFromGeoAdmin:
    def test_valid_feature(self):
        feature = {
            "attributes": {
                "egid": 12345,
                "energy_class": "B",
                "heating_demand": 55.0,
                "cooling_demand": 10.0,
                "dhw_demand": 25.0,
            }
        }
        record = parse_cecb_from_geo_admin(feature)
        assert record is not None
        assert record.egid == 12345
        assert record.energy_class == "B"
        assert record.heating_demand == 55.0
        assert record.cooling_demand == 10.0
        assert record.dhw_demand == 25.0
        assert record.source == "geo.admin.ch CECB"

    def test_french_field_names(self):
        feature = {
            "attributes": {
                "egid": 99999,
                "classe_energie": "D",
                "besoin_chauffage": 120.0,
            }
        }
        record = parse_cecb_from_geo_admin(feature)
        assert record is not None
        assert record.energy_class == "D"
        assert record.heating_demand == 120.0

    def test_no_egid(self):
        feature = {"attributes": {"energy_class": "A"}}
        assert parse_cecb_from_geo_admin(feature) is None

    def test_no_energy_class(self):
        feature = {"attributes": {"egid": 123}}
        assert parse_cecb_from_geo_admin(feature) is None

    def test_properties_key(self):
        feature = {
            "properties": {
                "egid": 555,
                "energy_class": "C",
            }
        }
        record = parse_cecb_from_geo_admin(feature)
        assert record is not None
        assert record.egid == 555


# ---------------------------------------------------------------------------
# parse_cecb_from_csv_row
# ---------------------------------------------------------------------------


class TestParseCECBFromCSVRow:
    def test_valid_row(self):
        row = {
            "egid": "12345",
            "classe": "C",
            "chauffage": "95.0",
            "refroidissement": "15.0",
            "eau_chaude": "30.0",
            "date_certificat": "2024-06-15",
        }
        record = parse_cecb_from_csv_row(row, canton="VD")
        assert record is not None
        assert record.egid == 12345
        assert record.energy_class == "C"
        assert record.heating_demand == 95.0
        assert record.cooling_demand == 15.0
        assert record.dhw_demand == 30.0
        assert record.certificate_date is not None
        assert "CECB VD" in record.source

    def test_swiss_date_format(self):
        row = {"egid": "111", "classe": "B", "date_certificat": "15.06.2024"}
        record = parse_cecb_from_csv_row(row)
        assert record is not None
        assert record.certificate_date.year == 2024

    def test_missing_egid(self):
        row = {"classe": "A"}
        assert parse_cecb_from_csv_row(row) is None

    def test_missing_class(self):
        row = {"egid": "123"}
        assert parse_cecb_from_csv_row(row) is None

    def test_canton_source_label(self):
        row = {"egid": "123", "classe": "D"}
        record = parse_cecb_from_csv_row(row, canton="GE")
        assert record is not None
        assert "CECB GE" in record.source


# ---------------------------------------------------------------------------
# parse_cecb_csv (full CSV)
# ---------------------------------------------------------------------------


class TestParseCECBCSV:
    def test_valid_csv(self):
        csv_content = (
            "egid;classe;chauffage;refroidissement;eau_chaude;date_certificat\n"
            "111;A;30.0;5.0;20.0;2024-01-01\n"
            "222;C;90.0;12.0;28.0;2024-02-15\n"
            "bad;X;nope;nope;nope;nope\n"
        )
        records = parse_cecb_csv(csv_content, canton="VD")
        assert len(records) == 2
        assert records[0].egid == 111
        assert records[0].energy_class == "A"
        assert records[1].egid == 222
        assert records[1].energy_class == "C"

    def test_empty_csv(self):
        csv_content = "egid;classe;chauffage\n"
        records = parse_cecb_csv(csv_content)
        assert len(records) == 0


# ---------------------------------------------------------------------------
# upsert_cecb_record (DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_cecb_updates_building(db_session, admin_user):
    bld = await _make_building(db_session, admin_user, egid=12345)
    assert bld.cecb_class is None

    record = CECBRecord(
        egid=12345,
        energy_class="B",
        heating_demand=55.0,
        cooling_demand=10.0,
        dhw_demand=25.0,
        certificate_date=datetime(2024, 6, 1, tzinfo=UTC),
        source="CECB VD 2024",
    )
    result = await upsert_cecb_record(db_session, record)
    assert result is True

    await db_session.flush()
    await db_session.refresh(bld)
    assert bld.cecb_class == "B"
    assert bld.cecb_heating_demand == 55.0
    assert bld.cecb_cooling_demand == 10.0
    assert bld.cecb_dhw_demand == 25.0
    assert bld.cecb_source == "CECB VD 2024"
    assert bld.cecb_fetch_date is not None


@pytest.mark.asyncio
async def test_upsert_cecb_skips_missing_building(db_session, admin_user):
    record = CECBRecord(
        egid=99999999,
        energy_class="A",
        heating_demand=30.0,
        cooling_demand=None,
        dhw_demand=None,
        certificate_date=None,
        source="CECB VD 2024",
    )
    result = await upsert_cecb_record(db_session, record)
    assert result is False


# ---------------------------------------------------------------------------
# import_cecb_batch (DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_cecb_batch(db_session, admin_user):
    bld1 = await _make_building(db_session, admin_user, egid=1001)
    bld2 = await _make_building(db_session, admin_user, egid=1002)

    records = [
        CECBRecord(
            egid=1001,
            energy_class="B",
            heating_demand=55.0,
            cooling_demand=10.0,
            dhw_demand=25.0,
            certificate_date=None,
            source="CECB VD 2024",
        ),
        CECBRecord(
            egid=1002,
            energy_class="D",
            heating_demand=130.0,
            cooling_demand=20.0,
            dhw_demand=35.0,
            certificate_date=None,
            source="CECB VD 2024",
        ),
        CECBRecord(
            egid=9999,  # does not exist
            energy_class="A",
            heating_demand=30.0,
            cooling_demand=None,
            dhw_demand=None,
            certificate_date=None,
            source="CECB VD 2024",
        ),
    ]
    stats = await import_cecb_batch(db_session, records)
    assert stats["updated"] == 2
    assert stats["skipped"] == 1
    assert stats["errors"] == 0

    await db_session.refresh(bld1)
    await db_session.refresh(bld2)
    assert bld1.cecb_class == "B"
    assert bld2.cecb_class == "D"


# ---------------------------------------------------------------------------
# import_cecb_for_missing (DB + mocked fetch)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_cecb_for_missing(db_session, admin_user):
    bld = await _make_building(db_session, admin_user, egid=5555)
    assert bld.cecb_class is None

    mock_record = CECBRecord(
        egid=5555,
        energy_class="C",
        heating_demand=90.0,
        cooling_demand=12.0,
        dhw_demand=28.0,
        certificate_date=None,
        source="geo.admin.ch CECB",
    )
    with patch(
        "app.services.cecb_import_service.fetch_cecb_by_egid",
        new_callable=AsyncMock,
        return_value=mock_record,
    ):
        stats = await import_cecb_for_missing(db_session, limit=10)

    assert stats["updated"] >= 1
    await db_session.refresh(bld)
    assert bld.cecb_class == "C"


@pytest.mark.asyncio
async def test_import_cecb_for_missing_skips_not_found(db_session, admin_user):
    await _make_building(db_session, admin_user, egid=6666)

    with patch(
        "app.services.cecb_import_service.fetch_cecb_by_egid",
        new_callable=AsyncMock,
        return_value=None,
    ):
        stats = await import_cecb_for_missing(db_session, limit=10)

    assert stats["skipped"] >= 1


# ---------------------------------------------------------------------------
# Energy service prefers real CECB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_energy_class_prefers_cecb(db_session, admin_user):
    """When CECB data exists, energy class should come from CECB, not estimate."""
    bld = await _make_building(
        db_session,
        admin_user,
        egid=7777,
        construction_year=1960,  # would be G by estimation
        cecb_class="B",
        cecb_heating_demand=55.0,
        cecb_source="CECB VD 2024",
    )
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "B"
    assert result.source == "cecb"
    assert result.cecb_heating_demand == 55.0


@pytest.mark.asyncio
async def test_energy_class_falls_back_to_estimate(db_session, admin_user):
    """Without CECB data, energy class should be estimated from construction year."""
    bld = await _make_building(
        db_session,
        admin_user,
        egid=8888,
        construction_year=1960,
    )
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "G"
    assert result.source == "estimated"
    assert result.cecb_heating_demand is None


@pytest.mark.asyncio
async def test_energy_class_cecb_overrides_improvement_potential(db_session, admin_user):
    """CECB B building should still show improvement potential to A."""
    bld = await _make_building(
        db_session,
        admin_user,
        egid=9999,
        construction_year=2020,
        cecb_class="B",
        cecb_heating_demand=60.0,
        cecb_source="CECB VD 2024",
    )
    result = await estimate_energy_class(db_session, bld.id)
    assert result.energy_class == "B"
    assert result.minergie_compatible is True
