from datetime import datetime
from unittest.mock import AsyncMock

import httpx
import pytest

from app.constants import SOURCE_DATASET_VAUD_PUBLIC
from app.importers.vaud_public import (
    _UPSERT_BUSINESS_FIELDS,
    _UPSERT_PROVENANCE_FIELDS,
    AddressRecord,
    RcbRecord,
    _build_source_metadata,
    build_address_line,
    build_address_where,
    fetch_address_record,
    fetch_batiment_record,
    fetch_object_ids,
    fetch_rcb_record,
    map_building_type,
    normalize_building_record,
    pick_primary_addresses,
)

# ---------------------------------------------------------------------------
# Helpers for building mock httpx responses
# ---------------------------------------------------------------------------


def _mock_response(data: dict) -> httpx.Response:
    return httpx.Response(200, json=data, request=httpx.Request("GET", "http://test"))


def _address_feature(
    object_id: int,
    egid: int,
    edid: int = 0,
    street: str = "Rue du Lac",
    house_number: str = "10",
    npa: int = 1000,
    locality: str = "Lausanne",
    commune: str = "Lausanne",
    num_com_ofs: int = 5586,
    **extra,
) -> dict:
    attrs = {
        "OBJECTID": object_id,
        "EGID": egid,
        "EDID": edid,
        "VOIE_TXT": street,
        "NO_ENTREE": house_number,
        "NPA": npa,
        "LOCALITE": locality,
        "COMMUNE": commune,
        "NUM_COM_OFS": num_com_ofs,
    }
    attrs.update(extra)
    return {"attributes": attrs}


def _rcb_feature(
    egid: int,
    *,
    category: str = "Batiment exclusivement a usage d'habitation",
    building_class: str = "Maisons a deux logements",
    status: str = "Existant",
    cons_annee: int = 1965,
    cons_perio: str = "Avant 1919",
    surface: float = 120.0,
    nb_niv_tot: int = 3,
    sre: float = 310.5,
    lat: float = 46.5,
    lon: float = 6.7,
    abri_pci: str | None = None,
    no_camac: str | None = None,
    **extra_attrs,
) -> dict:
    attrs = {
        "EGID": egid,
        "NO_CADASTR": "42",
        "CATEGORIE_TXT": category,
        "CLASSE_TXT": building_class,
        "STATUT_TXT": status,
        "CONS_ANNEE": cons_annee,
        "CONS_PERIO_TXT": cons_perio,
        "SURFACE": surface,
        "NB_NIV_TOT": nb_niv_tot,
        "SRE": sre,
        "CHAUF1_SYS_TXT": "Pompe a chaleur",
        "CHAUF1_NRG_TXT": "Electricite",
        "CHAUF2_SYS_TXT": None,
        "CHAUF2_NRG_TXT": None,
        "EAU1_SYS_TXT": "Pompe a chaleur",
        "EAU1_NRG_TXT": "Electricite",
        "EAU2_SYS_TXT": None,
        "EAU2_NRG_TXT": None,
        "ABRI_PCI": abri_pci,
        "NO_CAMAC": no_camac,
    }
    attrs.update(extra_attrs)
    return {
        "attributes": attrs,
        "geometry": {"x": lon, "y": lat},
    }


def _make_rcb(**kwargs) -> RcbRecord:
    defaults = dict(
        egid=100,
        building_number=None,
        category=None,
        building_class=None,
        status="Existant",
        construction_year=1970,
        construction_period=None,
        ground_surface_m2=100.0,
        floors_total=2,
        sre_m2=None,
        heating_system=None,
        heating_energy=None,
        heating2_system=None,
        heating2_energy=None,
        hot_water_system=None,
        hot_water_energy=None,
        hot_water2_system=None,
        hot_water2_energy=None,
        shelter_pci=None,
        camac_number=None,
        latitude=46.5,
        longitude=6.6,
        raw_attrs={},
    )
    defaults.update(kwargs)
    return RcbRecord(**defaults)


def _make_address(**kwargs) -> AddressRecord:
    defaults = dict(
        object_id=1,
        egid=100,
        edid=0,
        street="Rue du Test",
        house_number="1",
        postal_code="1000",
        locality="Lausanne",
        commune="Lausanne",
        municipality_ofs=5586,
        raw_attrs={},
    )
    defaults.update(kwargs)
    return AddressRecord(**defaults)


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


def test_build_address_where_escapes_commune_name() -> None:
    where = build_address_where("L'Abbaye", None, "1344")
    assert where == "COMMUNE = 'L''Abbaye' AND NPA = 1344"


def test_build_address_where_with_ofs() -> None:
    where = build_address_where(None, 5586, None)
    assert where == "NUM_COM_OFS = 5586"


def test_build_address_line_compacts_missing_parts() -> None:
    assert build_address_line("Route d'Oron", "4") == "Route d'Oron 4"
    assert build_address_line("Route d'Oron", None) == "Route d'Oron"


def test_map_building_type_handles_core_public_categories() -> None:
    assert map_building_type("Batiment exclusivement a usage d'habitation", "Maisons a un logement") == "residential"
    assert map_building_type("Batiment partiellement a usage d'habitation", "Batiments commerciaux") == "mixed"
    assert (
        map_building_type(
            "Batiment sans usage d'habitation", "Batiments a usage culturel, recreatif, educatif ou sanitaire"
        )
        == "public"
    )
    assert map_building_type("Batiment sans usage d'habitation", "Batiment d'exploitation agricole") == "industrial"
    assert map_building_type("Batiment sans usage d'habitation", "Batiments commerciaux") == "commercial"


def test_pick_primary_addresses_prefers_edid_zero() -> None:
    records = [
        _make_address(object_id=2, egid=100, edid=4, house_number="10B"),
        _make_address(object_id=1, egid=100, edid=0, house_number="10"),
    ]
    selected = pick_primary_addresses(records)
    assert len(selected) == 1
    assert selected[0].house_number == "10"


def test_pick_primary_addresses_deduplicates_by_egid() -> None:
    records = [
        _make_address(object_id=1, egid=200, edid=0, house_number="1"),
        _make_address(object_id=2, egid=300, edid=0, house_number="2"),
        _make_address(object_id=3, egid=200, edid=1, house_number="1bis"),
    ]
    selected = pick_primary_addresses(records)
    assert len(selected) == 2
    assert {r.egid for r in selected} == {200, 300}


def test_normalize_building_record_uses_sre_first() -> None:
    address = _make_address(
        egid=821406,
        street="Route d'Oron",
        house_number="4",
        postal_code="1083",
        locality="Mezieres VD",
        commune="Jorat-Mezieres",
    )
    rcb = _make_rcb(
        egid=821406,
        building_number="123",
        category="Batiment exclusivement a usage d'habitation",
        building_class="Maisons a deux logements",
        construction_year=1983,
        ground_surface_m2=149.0,
        floors_total=3,
        sre_m2=310.5,
    )

    normalized = normalize_building_record(address, rcb)
    assert normalized is not None
    assert normalized.egid == 821406
    assert normalized.official_id == "821406"
    assert normalized.address == "Route d'Oron 4"
    assert normalized.building_type == "residential"
    assert normalized.surface_area_m2 == 310.5


def test_normalize_building_record_skips_non_existing_status() -> None:
    address = _make_address(egid=1)
    rcb = _make_rcb(egid=1, status="En projet")
    assert normalize_building_record(address, rcb) is None


def test_normalize_passes_municipality_ofs() -> None:
    address = _make_address(egid=999, municipality_ofs=5586)
    rcb = _make_rcb(egid=999)
    normalized = normalize_building_record(address, rcb, municipality_ofs=5586)
    assert normalized is not None
    assert normalized.municipality_ofs == 5586
    assert normalized.egid == 999


# ---------------------------------------------------------------------------
# Source metadata structure tests
# ---------------------------------------------------------------------------


def test_source_metadata_always_contains_addresses_list() -> None:
    addr = _make_address(egid=100, raw_attrs={"EGID": 100, "VOIE_TXT": "Rue A", "NPA": 1000})
    rcb = _make_rcb(egid=100, raw_attrs={"EGID": 100, "CONS_ANNEE": 1970})

    meta = _build_source_metadata(addr, [addr], rcb)

    assert "address_primary" in meta
    assert meta["address_primary"]["EGID"] == 100
    assert "rcb_raw" in meta
    assert meta["rcb_raw"]["CONS_ANNEE"] == 1970
    # addresses is ALWAYS a list, even with a single entry
    assert "addresses" in meta
    assert isinstance(meta["addresses"], list)
    assert len(meta["addresses"]) == 1


def test_source_metadata_contains_all_addresses_when_multiple() -> None:
    addr1 = _make_address(egid=100, edid=0, house_number="1", raw_attrs={"EGID": 100, "EDID": 0, "NO_ENTREE": "1"})
    addr2 = _make_address(egid=100, edid=1, house_number="1A", raw_attrs={"EGID": 100, "EDID": 1, "NO_ENTREE": "1A"})
    rcb = _make_rcb(egid=100, raw_attrs={"EGID": 100})

    meta = _build_source_metadata(addr1, [addr1, addr2], rcb)

    assert len(meta["addresses"]) == 2
    edids = {a["EDID"] for a in meta["addresses"]}
    assert edids == {0, 1}


def test_source_metadata_includes_batch_id() -> None:
    addr = _make_address(egid=100, raw_attrs={"EGID": 100})
    rcb = _make_rcb(egid=100, raw_attrs={"EGID": 100})

    meta = _build_source_metadata(addr, [addr], rcb, batch_id="abc123")
    assert meta["batch_id"] == "abc123"


def test_source_metadata_includes_source_layers() -> None:
    addr = _make_address(egid=100, raw_attrs={"EGID": 100})
    rcb = _make_rcb(egid=100, raw_attrs={"EGID": 100})

    meta = _build_source_metadata(addr, [addr], rcb)
    assert "source_layers" in meta
    assert "address" in meta["source_layers"]
    assert "rcb" in meta["source_layers"]
    assert "241" in meta["source_layers"]["address"]
    assert "39" in meta["source_layers"]["rcb"]


def test_source_metadata_includes_rcb_geometry() -> None:
    addr = _make_address(egid=100, raw_attrs={"EGID": 100})
    rcb = _make_rcb(
        egid=100,
        raw_attrs={
            "EGID": 100,
            "_geometry": {"x": 6.63, "y": 46.52},
        },
    )

    meta = _build_source_metadata(addr, [addr], rcb)

    assert "rcb_geometry" in meta
    assert meta["rcb_geometry"]["x"] == 6.63
    assert meta["rcb_geometry"]["y"] == 46.52
    # _geometry should NOT leak into rcb_raw
    assert "_geometry" not in meta["rcb_raw"]


def test_to_building_create_payload_includes_structured_metadata() -> None:
    addr = _make_address(egid=555, raw_attrs={"EGID": 555, "NPA": 1003})
    rcb = _make_rcb(
        egid=555,
        category="Batiment exclusivement a usage d'habitation",
        building_class="Maisons a un logement",
        construction_year=1955,
        sre_m2=160.0,
        raw_attrs={"EGID": 555, "SRE": 160.0},
    )

    normalized = normalize_building_record(addr, rcb)
    assert normalized is not None

    payload = normalized.to_building_create_payload()
    assert payload["egid"] == 555
    assert payload["source_dataset"] == SOURCE_DATASET_VAUD_PUBLIC
    assert payload["source_imported_at"] is not None
    assert isinstance(payload["source_imported_at"], datetime)
    assert payload["source_imported_at"].tzinfo is not None
    meta = payload["source_metadata_json"]
    assert "address_primary" in meta
    assert "rcb_raw" in meta
    assert "source_layers" in meta
    assert "addresses" in meta
    assert meta["rcb_raw"]["SRE"] == 160.0


def test_normalize_with_all_addresses_stores_them() -> None:
    addr1 = _make_address(egid=100, edid=0, house_number="1", raw_attrs={"EGID": 100, "EDID": 0})
    addr2 = _make_address(egid=100, edid=1, house_number="1A", raw_attrs={"EGID": 100, "EDID": 1})
    rcb = _make_rcb(egid=100, raw_attrs={"EGID": 100})

    normalized = normalize_building_record(addr1, rcb, all_addresses=[addr1, addr2])
    assert normalized is not None
    assert "addresses" in normalized.source_metadata
    assert len(normalized.source_metadata["addresses"]) == 2


# ---------------------------------------------------------------------------
# Mocked ArcGIS endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_object_ids_returns_ids() -> None:
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"objectIds": [1, 2, 3]})

    ids = await fetch_object_ids(mock_client, layer_id=241, where="COMMUNE = 'Lausanne'")
    assert ids == [1, 2, 3]


@pytest.mark.asyncio
async def test_fetch_object_ids_returns_empty_on_none() -> None:
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"objectIds": None})

    ids = await fetch_object_ids(mock_client, layer_id=241, where="COMMUNE = 'Nowhere'")
    assert ids == []


@pytest.mark.asyncio
async def test_fetch_address_record_parses_attributes() -> None:
    feature = _address_feature(
        42,
        egid=821406,
        street="Route d'Oron",
        house_number="4",
        npa=1083,
        locality="Mezieres VD",
        commune="Jorat-Mezieres",
        num_com_ofs=5822,
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": [feature]})

    record = await fetch_address_record(mock_client, 42)
    assert record is not None
    assert record.egid == 821406
    assert record.street == "Route d'Oron"
    assert record.municipality_ofs == 5822
    assert record.postal_code == "1083"
    assert record.raw_attrs["EGID"] == 821406


@pytest.mark.asyncio
async def test_fetch_address_record_captures_extra_fields() -> None:
    """outFields=* means extra fields from the layer are captured in raw_attrs."""
    feature = _address_feature(1, egid=100, EGAID=9999, ESID=42)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": [feature]})

    record = await fetch_address_record(mock_client, 1)
    assert record is not None
    assert record.raw_attrs["EGAID"] == 9999
    assert record.raw_attrs["ESID"] == 42


@pytest.mark.asyncio
async def test_fetch_address_record_returns_none_on_missing_egid() -> None:
    feature = {
        "attributes": {
            "OBJECTID": 1,
            "EGID": None,
            "EDID": 0,
            "VOIE_TXT": "Test",
            "NO_ENTREE": "1",
            "NPA": 1000,
            "LOCALITE": "Lausanne",
            "COMMUNE": "Lausanne",
            "NUM_COM_OFS": 5586,
        }
    }
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": [feature]})

    record = await fetch_address_record(mock_client, 1)
    assert record is None


@pytest.mark.asyncio
async def test_fetch_rcb_record_parses_enriched_fields() -> None:
    feature = _rcb_feature(
        821406,
        cons_annee=1965,
        cons_perio="Avant 1919",
        sre=310.5,
        lat=46.52,
        lon=6.63,
        abri_pci="oui",
        no_camac="PA-2023-456",
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": [feature]})

    rcb = await fetch_rcb_record(mock_client, 821406)
    assert rcb is not None
    assert rcb.egid == 821406
    assert rcb.construction_year == 1965
    assert rcb.construction_period == "Avant 1919"
    assert rcb.sre_m2 == 310.5
    assert rcb.latitude == 46.52
    assert rcb.longitude == 6.63
    assert rcb.shelter_pci == "oui"
    assert rcb.camac_number == "PA-2023-456"
    assert rcb.raw_attrs["EGID"] == 821406
    assert rcb.raw_attrs["ABRI_PCI"] == "oui"


@pytest.mark.asyncio
async def test_fetch_rcb_record_stores_geometry_in_raw_attrs() -> None:
    feature = _rcb_feature(100, lat=46.5, lon=6.7)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": [feature]})

    rcb = await fetch_rcb_record(mock_client, 100)
    assert rcb is not None
    assert "_geometry" in rcb.raw_attrs
    assert rcb.raw_attrs["_geometry"]["x"] == 6.7
    assert rcb.raw_attrs["_geometry"]["y"] == 46.5


@pytest.mark.asyncio
async def test_fetch_rcb_record_captures_extra_fields() -> None:
    """outFields=* means extra fields from the layer are captured in raw_attrs."""
    feature = _rcb_feature(100, SOME_NEW_FIELD="hello", ANOTHER_INT=42)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": [feature]})

    rcb = await fetch_rcb_record(mock_client, 100)
    assert rcb is not None
    assert rcb.raw_attrs["SOME_NEW_FIELD"] == "hello"
    assert rcb.raw_attrs["ANOTHER_INT"] == 42


@pytest.mark.asyncio
async def test_fetch_rcb_record_returns_none_on_empty() -> None:
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": []})

    rcb = await fetch_rcb_record(mock_client, 999999)
    assert rcb is None


# ---------------------------------------------------------------------------
# ABRI_PCI string type tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_rcb_record_shelter_pci_string_non() -> None:
    """ABRI_PCI is a string ('non'/'oui'), not an integer."""
    feature = _rcb_feature(100, abri_pci="non")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": [feature]})

    rcb = await fetch_rcb_record(mock_client, 100)
    assert rcb is not None
    assert rcb.shelter_pci == "non"
    assert isinstance(rcb.shelter_pci, str)


@pytest.mark.asyncio
async def test_fetch_rcb_record_shelter_pci_none() -> None:
    feature = _rcb_feature(100, abri_pci=None)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": [feature]})

    rcb = await fetch_rcb_record(mock_client, 100)
    assert rcb is not None
    assert rcb.shelter_pci is None


# ---------------------------------------------------------------------------
# Idempotence: business vs provenance field split
# ---------------------------------------------------------------------------


def test_upsert_fields_split_excludes_volatile_from_business() -> None:
    """source_imported_at and source_metadata_json must NOT be in business fields."""
    assert "source_imported_at" not in _UPSERT_BUSINESS_FIELDS
    assert "source_metadata_json" not in _UPSERT_BUSINESS_FIELDS
    assert "source_imported_at" in _UPSERT_PROVENANCE_FIELDS
    assert "source_metadata_json" in _UPSERT_PROVENANCE_FIELDS


def test_upsert_fields_split_covers_all_needed_fields() -> None:
    """Business + provenance fields should cover all data fields we want to sync."""
    all_fields = set(_UPSERT_BUSINESS_FIELDS) | set(_UPSERT_PROVENANCE_FIELDS)
    assert "address" in all_fields
    assert "construction_year" in all_fields
    assert "source_dataset" in all_fields
    assert "source_imported_at" in all_fields
    assert "source_metadata_json" in all_fields


# ---------------------------------------------------------------------------
# Layer 276 (vd.batiment) tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_batiment_record_parses_polygon() -> None:
    feature = {
        "attributes": {
            "EGID": 100,
            "NO_COM_FED": 5586,
            "GENRE_TXT": "batiment",
            "DESIGNATION_TXT": "Habitation",
            "SURFACE": 150.0,
        },
        "geometry": {
            "rings": [[[6.6, 46.5], [6.61, 46.5], [6.61, 46.51], [6.6, 46.51], [6.6, 46.5]]],
        },
    }
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": [feature]})

    bat = await fetch_batiment_record(mock_client, 100)
    assert bat is not None
    assert bat["attributes"]["EGID"] == 100
    assert bat["attributes"]["SURFACE"] == 150.0
    assert "geometry" in bat
    assert "rings" in bat["geometry"]


@pytest.mark.asyncio
async def test_fetch_batiment_record_returns_none_on_empty() -> None:
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"features": []})

    bat = await fetch_batiment_record(mock_client, 999999)
    assert bat is None


def test_source_metadata_includes_batiment_when_provided() -> None:
    addr = _make_address(egid=100, raw_attrs={"EGID": 100})
    rcb = _make_rcb(egid=100, raw_attrs={"EGID": 100})
    bat = {"attributes": {"EGID": 100, "GENRE_TXT": "batiment"}, "geometry": {"rings": []}}

    meta = _build_source_metadata(addr, [addr], rcb, batiment=bat)

    assert "batiment" in meta
    assert meta["batiment"]["attributes"]["EGID"] == 100
    assert "source_layers" in meta
    assert "batiment" in meta["source_layers"]
    assert "276" in meta["source_layers"]["batiment"]


def test_source_metadata_excludes_batiment_when_none() -> None:
    addr = _make_address(egid=100, raw_attrs={"EGID": 100})
    rcb = _make_rcb(egid=100, raw_attrs={"EGID": 100})

    meta = _build_source_metadata(addr, [addr], rcb)

    assert "batiment" not in meta
    assert "batiment" not in meta["source_layers"]


def test_normalize_with_batiment_stores_in_metadata() -> None:
    addr = _make_address(egid=100, raw_attrs={"EGID": 100})
    rcb = _make_rcb(egid=100, raw_attrs={"EGID": 100})
    bat = {"attributes": {"EGID": 100, "SURFACE": 200.0}, "geometry": {"rings": []}}

    normalized = normalize_building_record(addr, rcb, batiment=bat)
    assert normalized is not None
    assert "batiment" in normalized.source_metadata
    assert normalized.source_metadata["batiment"]["attributes"]["SURFACE"] == 200.0
