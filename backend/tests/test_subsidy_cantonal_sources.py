"""Tests for subsidy source service and cantonal procedure source service."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.source_registry import SourceRegistryEntry

# Pre-computed bcrypt hash for "test123" — avoids slow hashing in tests
_TEST_PASSWORD_HASH = "$2b$12$LJ3m4ys3Lk0TSwHIbQVUne1MkPAlRNmYpLxnqIazHOuVOLEs9griW"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(name: str, **kwargs) -> SourceRegistryEntry:
    defaults = {
        "id": uuid.uuid4(),
        "name": name,
        "display_name": name.replace("_", " ").title(),
        "family": "procedure",
        "circle": 1,
        "source_class": "official",
        "access_mode": "api",
        "trust_posture": "canonical_constraint",
        "status": "active",
    }
    defaults.update(kwargs)
    return SourceRegistryEntry(**defaults)


async def _create_building(db, *, canton: str = "VD", construction_year: int | None = 1975) -> Building:
    from app.models.organization import Organization
    from app.models.user import User

    org = Organization(
        id=uuid.uuid4(),
        name=f"Test Org {uuid.uuid4().hex[:6]}",
        type="diagnostic_lab",
    )
    db.add(org)
    await db.flush()

    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_TEST_PASSWORD_HASH,
        first_name="Test",
        last_name="User",
        role="admin",
        organization_id=org.id,
    )
    db.add(user)
    await db.flush()

    building = Building(
        id=uuid.uuid4(),
        address=f"Rue de Test {uuid.uuid4().hex[:4]}",
        city="Lausanne" if canton == "VD" else "Geneve",
        postal_code="1000",
        canton=canton,
        construction_year=construction_year,
        building_type="residential",
        created_by=user.id,
        organization_id=org.id,
    )
    db.add(building)
    await db.flush()
    return building


# ===========================================================================
# SUBSIDY SOURCE SERVICE — catalog data
# ===========================================================================


def test_subsidy_programs_vd_present():
    """VD subsidy catalog contains expected programs."""
    from app.services.subsidy_source_service import SUBSIDY_PROGRAMS

    vd = SUBSIDY_PROGRAMS["VD"]
    assert vd["name"] == "Programme Batiments VD"
    assert len(vd["programs"]) >= 4
    categories = [p["category"] for p in vd["programs"]]
    assert "energy" in categories
    assert "pollutant" in categories


def test_subsidy_programs_ge_present():
    """GE subsidy catalog contains expected programs."""
    from app.services.subsidy_source_service import SUBSIDY_PROGRAMS

    ge = SUBSIDY_PROGRAMS["GE"]
    assert ge["name"] == "Programme Batiments GE"
    assert len(ge["programs"]) >= 3


def test_subsidy_programs_fr_present():
    """FR subsidy catalog contains expected programs."""
    from app.services.subsidy_source_service import SUBSIDY_PROGRAMS

    fr = SUBSIDY_PROGRAMS["FR"]
    assert fr["name"] == "Programme Batiments FR"
    assert len(fr["programs"]) >= 2


def test_supported_cantons():
    """Service reports correct supported cantons."""
    from app.services.subsidy_source_service import SubsidySourceService

    cantons = SubsidySourceService.get_supported_cantons()
    assert "VD" in cantons
    assert "GE" in cantons
    assert "FR" in cantons


# ===========================================================================
# SUBSIDY SOURCE SERVICE — async operations
# ===========================================================================


@pytest.mark.asyncio
async def test_subsidy_catalog_vd(db_session):
    """Fetch subsidy catalog for VD."""
    from app.services.subsidy_source_service import SubsidySourceService

    # Register the source so health events work
    db_session.add(_make_source("subsidy_programs_vd"))
    await db_session.flush()

    result = await SubsidySourceService.get_subsidy_catalog(db_session, "VD")
    assert result["canton"] == "VD"
    assert result["total_programs"] >= 4
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_subsidy_catalog_unknown_canton(db_session):
    """Unknown canton returns empty programs, not crash."""
    from app.services.subsidy_source_service import SubsidySourceService

    result = await SubsidySourceService.get_subsidy_catalog(db_session, "ZZ")
    assert result["canton"] == "ZZ"
    assert result["programs"] == []
    assert result["error"] == "unknown_canton"


@pytest.mark.asyncio
async def test_subsidy_catalog_cache(db_session):
    """Second fetch uses cache."""
    from app.services.subsidy_source_service import SubsidySourceService

    db_session.add(_make_source("subsidy_programs_ge"))
    await db_session.flush()

    r1 = await SubsidySourceService.get_subsidy_catalog(db_session, "GE")
    assert r1.get("cached") is False or r1.get("cached") is None

    r2 = await SubsidySourceService.get_subsidy_catalog(db_session, "GE")
    assert r2.get("cached") is True


@pytest.mark.asyncio
async def test_subsidy_applicable_building(db_session):
    """get_applicable_subsidies returns programs for a VD building."""
    from app.services.subsidy_source_service import SubsidySourceService

    db_session.add(_make_source("subsidy_programs_vd"))
    await db_session.flush()
    building = await _create_building(db_session, canton="VD", construction_year=1975)

    result = await SubsidySourceService.get_applicable_subsidies(db_session, building.id)
    assert result["canton"] == "VD"
    assert result["total_programs"] >= 1
    assert result["total_potential_chf"] > 0
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_subsidy_applicable_building_not_found(db_session):
    """get_applicable_subsidies with bad building_id returns error."""
    from app.services.subsidy_source_service import SubsidySourceService

    result = await SubsidySourceService.get_applicable_subsidies(db_session, uuid.uuid4())
    assert result["error"] == "building_not_found"


@pytest.mark.asyncio
async def test_subsidy_applicable_filters_by_age(db_session):
    """Building too new for pollutant program gets filtered out."""
    from app.services.subsidy_source_service import SubsidySourceService

    db_session.add(_make_source("subsidy_programs_vd"))
    await db_session.flush()

    # New building (2020) should not match asbestos subsidy (cutoff 1990)
    building = await _create_building(db_session, canton="VD", construction_year=2020)

    result = await SubsidySourceService.get_applicable_subsidies(db_session, building.id)
    pollutant_programs = [p for p in result["programs"] if p.get("category") == "pollutant"]
    assert len(pollutant_programs) == 0


@pytest.mark.asyncio
async def test_subsidy_applicable_old_building_includes_pollutant(db_session):
    """Old building (1960) qualifies for pollutant programs."""
    from app.services.subsidy_source_service import SubsidySourceService

    db_session.add(_make_source("subsidy_programs_vd"))
    await db_session.flush()

    building = await _create_building(db_session, canton="VD", construction_year=1960)

    result = await SubsidySourceService.get_applicable_subsidies(db_session, building.id)
    pollutant_programs = [p for p in result["programs"] if p.get("category") == "pollutant"]
    assert len(pollutant_programs) >= 1


@pytest.mark.asyncio
async def test_subsidy_eligibility_asbestos(db_session):
    """Check eligibility for asbestos_removal work type."""
    from app.services.subsidy_source_service import SubsidySourceService

    db_session.add(_make_source("subsidy_programs_vd"))
    await db_session.flush()

    building = await _create_building(db_session, canton="VD", construction_year=1970)

    result = await SubsidySourceService.get_subsidy_eligibility(db_session, building.id, "asbestos_removal")
    assert result["eligible"] is True
    assert result["work_type"] == "asbestos_removal"
    assert len(result["programs"]) >= 1
    assert result["max_amount"] > 0


@pytest.mark.asyncio
async def test_subsidy_eligibility_no_subsidy_work_type(db_session):
    """Work type with no subsidy category returns not eligible."""
    from app.services.subsidy_source_service import SubsidySourceService

    building = await _create_building(db_session, canton="VD")

    result = await SubsidySourceService.get_subsidy_eligibility(db_session, building.id, "demolition")
    assert result["eligible"] is False
    assert result["reason"] == "no_subsidy_category_for_work_type"


@pytest.mark.asyncio
async def test_subsidy_refresh_forces_fresh(db_session):
    """refresh_subsidy_data bypasses cache."""
    from app.services.subsidy_source_service import SubsidySourceService

    db_session.add(_make_source("subsidy_programs_fr"))
    await db_session.flush()

    result = await SubsidySourceService.refresh_subsidy_data(db_session, "FR")
    assert result["canton"] == "FR"
    assert result.get("cached") is not True


# ===========================================================================
# SUBSIDY — health events
# ===========================================================================


@pytest.mark.asyncio
async def test_subsidy_records_health_event(db_session):
    """Fetching subsidy catalog records a health event."""
    from app.services.source_registry_service import SourceRegistryService
    from app.services.subsidy_source_service import SubsidySourceService

    source = _make_source("subsidy_programs_vd")
    db_session.add(source)
    await db_session.flush()

    # Clear cache to force a fresh fetch
    from app.services.subsidy_source_service import _cache

    _cache.pop("VD", None)

    await SubsidySourceService.get_subsidy_catalog(db_session, "VD", force_refresh=True)

    health = await SourceRegistryService.get_source_health(db_session, "subsidy_programs_vd")
    assert health["source_name"] == "subsidy_programs_vd"
    assert len(health["recent_events"]) >= 1
    assert health["recent_events"][0].event_type == "healthy"


# ===========================================================================
# CANTONAL PROCEDURE SOURCE SERVICE — static data
# ===========================================================================


def test_cantonal_authorities_vd_present():
    """VD authorities include environment, construction, heritage."""
    from app.services.cantonal_procedure_source_service import CANTONAL_AUTHORITIES

    vd = CANTONAL_AUTHORITIES["VD"]
    assert "environment" in vd
    assert "construction" in vd
    assert "heritage" in vd
    assert vd["environment"]["name"] == "DGE-DIREV"
    assert vd["construction"]["name"] == "CAMAC"


def test_cantonal_authorities_ge_present():
    """GE authorities include environment and construction."""
    from app.services.cantonal_procedure_source_service import CANTONAL_AUTHORITIES

    ge = CANTONAL_AUTHORITIES["GE"]
    assert "environment" in ge
    assert "construction" in ge
    assert ge["environment"]["name"] == "OCEV"


def test_cantonal_authorities_fr_present():
    """FR authorities include environment and construction."""
    from app.services.cantonal_procedure_source_service import CANTONAL_AUTHORITIES

    fr = CANTONAL_AUTHORITIES["FR"]
    assert "environment" in fr
    assert "construction" in fr
    assert fr["environment"]["filing"] == "friac"


def test_filing_requirements_exist():
    """Filing requirements exist for VD, GE, FR."""
    from app.services.cantonal_procedure_source_service import FILING_REQUIREMENTS

    for canton in ("VD", "GE", "FR"):
        assert canton in FILING_REQUIREMENTS
        # Each canton should have at least demolition + asbestos procedures
        assert "demolition_permit" in FILING_REQUIREMENTS[canton]
        assert "asbestos_notification" in FILING_REQUIREMENTS[canton]


# ===========================================================================
# CANTONAL PROCEDURE SOURCE SERVICE — async operations
# ===========================================================================


@pytest.mark.asyncio
async def test_authority_context_vd_environment():
    """get_authority_context returns VD environment authority."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    result = await CantonalProcedureSourceService.get_authority_context("VD", "environment")
    assert result["canton"] == "VD"
    assert result["domain"] == "environment"
    assert result["authority"]["name"] == "DGE-DIREV"
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_authority_context_unknown_canton():
    """Unknown canton returns error, not crash."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    result = await CantonalProcedureSourceService.get_authority_context("ZZ", "environment")
    assert result["error"] == "unknown_canton"
    assert result["authority"] is None


@pytest.mark.asyncio
async def test_authority_context_unknown_domain():
    """Unknown domain for valid canton returns error with available domains."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    result = await CantonalProcedureSourceService.get_authority_context("VD", "military")
    assert result["error"] == "unknown_domain"
    assert "available_domains" in result
    assert "environment" in result["available_domains"]


@pytest.mark.asyncio
async def test_filing_requirements_vd_asbestos():
    """get_filing_requirements returns VD asbestos notification details."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    result = await CantonalProcedureSourceService.get_filing_requirements("VD", "asbestos_notification")
    assert result["canton"] == "VD"
    assert result["procedure_type"] == "asbestos_notification"
    reqs = result["requirements"]
    assert reqs is not None
    assert "SUVA" in reqs["authority"]
    assert len(reqs["required_documents"]) >= 3


@pytest.mark.asyncio
async def test_filing_requirements_unknown_procedure():
    """Unknown procedure type returns error with available procedures."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    result = await CantonalProcedureSourceService.get_filing_requirements("VD", "alien_invasion")
    assert result["error"] == "unknown_procedure"
    assert "available_procedures" in result


@pytest.mark.asyncio
async def test_filing_requirements_unknown_canton():
    """Unknown canton returns error."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    result = await CantonalProcedureSourceService.get_filing_requirements("ZZ", "demolition_permit")
    assert result["error"] == "unknown_canton"


@pytest.mark.asyncio
async def test_canton_context_building(db_session):
    """get_canton_context returns full context for a VD building."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    db_session.add(_make_source("cantonal_authorities_vd"))
    await db_session.flush()
    building = await _create_building(db_session, canton="VD")

    result = await CantonalProcedureSourceService.get_canton_context(db_session, building.id)
    assert result["canton"] == "VD"
    assert "environment" in result["authorities"]
    assert "construction" in result["authorities"]
    assert len(result["supported_domains"]) >= 3
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_canton_context_building_not_found(db_session):
    """get_canton_context with bad building_id returns error."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    result = await CantonalProcedureSourceService.get_canton_context(db_session, uuid.uuid4())
    assert result["error"] == "building_not_found"


@pytest.mark.asyncio
async def test_canton_context_unknown_canton_building(db_session):
    """Building with unsupported canton returns graceful error."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    building = await _create_building(db_session, canton="ZH")

    result = await CantonalProcedureSourceService.get_canton_context(db_session, building.id)
    assert result["error"] == "no_data_for_canton"
    assert result["authorities"] == {}


@pytest.mark.asyncio
async def test_canton_context_records_health_event(db_session):
    """get_canton_context records a health event."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService, _cache
    from app.services.source_registry_service import SourceRegistryService

    source = _make_source("cantonal_authorities_vd")
    db_session.add(source)
    await db_session.flush()

    # Clear cache to force fresh fetch
    _cache.pop("VD", None)

    building = await _create_building(db_session, canton="VD")
    await CantonalProcedureSourceService.get_canton_context(db_session, building.id)

    health = await SourceRegistryService.get_source_health(db_session, "cantonal_authorities_vd")
    assert health["source_name"] == "cantonal_authorities_vd"
    assert len(health["recent_events"]) >= 1


@pytest.mark.asyncio
async def test_get_all_authorities_vd(db_session):
    """get_all_authorities returns all VD authorities."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    db_session.add(_make_source("cantonal_authorities_vd"))
    await db_session.flush()

    result = await CantonalProcedureSourceService.get_all_authorities(db_session, "VD")
    assert result["canton"] == "VD"
    assert result["total_authorities"] >= 3
    assert "environment" in result["authorities"]


@pytest.mark.asyncio
async def test_get_all_authorities_unknown_canton(db_session):
    """get_all_authorities for unknown canton returns error."""
    from app.services.cantonal_procedure_source_service import CantonalProcedureSourceService

    result = await CantonalProcedureSourceService.get_all_authorities(db_session, "ZZ")
    assert result["error"] == "unknown_canton"


# ===========================================================================
# SOURCE REGISTRY — seed entries
# ===========================================================================


def test_seed_includes_subsidy_sources():
    """Seed registry includes subsidy program sources for VD/GE/FR."""
    from app.seeds.seed_source_registry import SOURCES

    names = [s["name"] for s in SOURCES]
    assert "subsidy_programs_vd" in names
    assert "subsidy_programs_ge" in names
    assert "subsidy_programs_fr" in names


def test_seed_includes_cantonal_authority_sources():
    """Seed registry includes cantonal authority sources for VD/GE/FR."""
    from app.seeds.seed_source_registry import SOURCES

    names = [s["name"] for s in SOURCES]
    assert "cantonal_authorities_vd" in names
    assert "cantonal_authorities_ge" in names
    assert "cantonal_authorities_fr" in names


def test_seed_subsidy_sources_structure():
    """Subsidy sources have correct family, circle, and consumers."""
    from app.seeds.seed_source_registry import SOURCES

    subsidy_sources = [s for s in SOURCES if s["name"].startswith("subsidy_programs_")]
    assert len(subsidy_sources) == 3
    for s in subsidy_sources:
        assert s["family"] == "procedure"
        assert s["circle"] == 1
        assert s["source_class"] == "official"
        assert "procedure_workspace" in s["workspace_consumers"]


def test_seed_cantonal_authority_sources_structure():
    """Cantonal authority sources have correct family, circle, and consumers."""
    from app.seeds.seed_source_registry import SOURCES

    cantonal_sources = [s for s in SOURCES if s["name"].startswith("cantonal_authorities_")]
    assert len(cantonal_sources) == 3
    for s in cantonal_sources:
        assert s["family"] == "procedure"
        assert s["circle"] == 1
        assert s["source_class"] == "official"
        assert "case_room" in s["workspace_consumers"]
