"""Tests for the async resolved variants in compliance_engine.

Verifies that check_threshold_resolved and get_cantonal_requirements_resolved
use regulatory packs when available and fall back to hardcoded defaults otherwise.
"""

import uuid

import pytest

from app.models.jurisdiction import Jurisdiction
from app.models.regulatory_pack import RegulatoryPack
from app.services.compliance_engine import (
    check_threshold_resolved,
    get_cantonal_requirements_resolved,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CH_ID = uuid.uuid4()
VD_ID = uuid.uuid4()


@pytest.fixture
async def jurisdiction_chain(db_session):
    """Create CH → CH-VD jurisdiction chain."""
    ch = Jurisdiction(
        id=CH_ID,
        code="ch",
        name="Suisse",
        parent_id=None,
        level="country",
        country_code="CH",
    )
    vd = Jurisdiction(
        id=VD_ID,
        code="ch-vd",
        name="Canton de Vaud",
        parent_id=CH_ID,
        level="region",
        country_code="CH",
        metadata_json={
            "authority_name": "DGE-DIRNA",
            "diagnostic_required_before_year": 1991,
            "requires_waste_elimination_plan": True,
            "form_name": "Plan d'elimination des dechets (PED)",
        },
    )
    db_session.add_all([ch, vd])
    await db_session.flush()
    return {"ch": ch, "vd": vd}


@pytest.fixture
async def asbestos_pack(db_session, jurisdiction_chain):
    """Create a federal-level asbestos threshold pack."""
    pack = RegulatoryPack(
        id=uuid.uuid4(),
        jurisdiction_id=CH_ID,
        pollutant_type="asbestos",
        version="1.0",
        is_active=True,
        threshold_value=1.0,
        threshold_unit="percent_weight",
        threshold_action="remediate",
        legal_reference="OTConst Art. 82",
        notification_required=True,
        notification_authority="SUVA",
        notification_delay_days=14,
    )
    db_session.add(pack)
    await db_session.flush()
    return pack


@pytest.fixture
async def cantonal_asbestos_pack(db_session, jurisdiction_chain):
    """Create a cantonal-level asbestos pack for VD."""
    pack = RegulatoryPack(
        id=uuid.uuid4(),
        jurisdiction_id=VD_ID,
        pollutant_type="asbestos",
        version="1.0",
        is_active=True,
        threshold_value=1.0,
        threshold_unit="percent_weight",
        threshold_action="remediate",
        legal_reference="OTConst Art. 82 + Directive VD",
        notification_required=True,
        notification_authority="DGE-DIRNA",
        notification_delay_days=14,
    )
    db_session.add(pack)
    await db_session.flush()
    return pack


# ---------------------------------------------------------------------------
# check_threshold_resolved
# ---------------------------------------------------------------------------


class TestCheckThresholdResolved:
    async def test_uses_pack_when_available(self, db_session, asbestos_pack):
        """When a regulatory pack exists, it should be used (source=regulatory_pack)."""
        result = await check_threshold_resolved(db_session, CH_ID, "asbestos", 2.0, "percent_weight")
        assert result["source"] == "regulatory_pack"
        assert result["exceeded"] is True
        assert result["threshold"] == 1.0
        assert result["legal_ref"] == "OTConst Art. 82"

    async def test_falls_back_to_hardcoded(self, db_session, jurisdiction_chain):
        """When no pack exists, should fall back to hardcoded (source=hardcoded)."""
        result = await check_threshold_resolved(db_session, VD_ID, "asbestos", 2.0, "percent_weight")
        assert result["source"] == "hardcoded"
        assert result["exceeded"] is True
        assert result["threshold"] == 1.0

    async def test_falls_back_when_jurisdiction_is_none(self, db_session):
        """When jurisdiction_id is None, should use hardcoded fallback."""
        result = await check_threshold_resolved(db_session, None, "asbestos", 0.5, "percent_weight")
        assert result["source"] == "hardcoded"
        assert result["exceeded"] is False

    async def test_not_exceeded_with_pack(self, db_session, asbestos_pack):
        """Below-threshold concentration via regulatory pack."""
        result = await check_threshold_resolved(db_session, CH_ID, "asbestos", 0.5, "percent_weight")
        assert result["exceeded"] is False
        assert result["action"] == "none"
        assert result["source"] == "regulatory_pack"

    async def test_remove_urgent_with_pack(self, db_session, asbestos_pack):
        """Concentration >= 3x threshold triggers remove_urgent."""
        result = await check_threshold_resolved(db_session, CH_ID, "asbestos", 5.0, "percent_weight")
        assert result["exceeded"] is True
        assert result["action"] == "remove_urgent"
        assert result["source"] == "regulatory_pack"

    async def test_remove_planned_with_pack(self, db_session, asbestos_pack):
        """Concentration >= threshold but < 3x triggers remove_planned."""
        result = await check_threshold_resolved(db_session, CH_ID, "asbestos", 2.0, "percent_weight")
        assert result["exceeded"] is True
        assert result["action"] == "remove_planned"
        assert result["source"] == "regulatory_pack"

    async def test_walks_hierarchy(self, db_session, asbestos_pack):
        """VD → CH hierarchy walk should find federal pack."""
        result = await check_threshold_resolved(db_session, VD_ID, "asbestos", 2.0, "percent_weight")
        assert result["source"] == "regulatory_pack"
        assert result["threshold"] == 1.0

    async def test_cantonal_overrides_federal(self, db_session, asbestos_pack, cantonal_asbestos_pack):
        """When VD has its own pack, it should be used over federal."""
        result = await check_threshold_resolved(db_session, VD_ID, "asbestos", 2.0, "percent_weight")
        assert result["source"] == "regulatory_pack"
        assert result["legal_ref"] == "OTConst Art. 82 + Directive VD"

    async def test_unit_mismatch_falls_back(self, db_session, asbestos_pack):
        """Pack has percent_weight; request with mg_per_kg → no match → hardcoded fallback."""
        result = await check_threshold_resolved(db_session, CH_ID, "asbestos", 50.0, "mg_per_kg")
        # No hardcoded threshold for asbestos in mg_per_kg either
        assert result["source"] == "hardcoded"
        assert result["threshold"] is None

    async def test_pcb_hardcoded_fallback(self, db_session, jurisdiction_chain):
        """PCB with no pack should use hardcoded PCB thresholds."""
        result = await check_threshold_resolved(db_session, VD_ID, "pcb", 100.0, "mg_per_kg")
        assert result["source"] == "hardcoded"
        assert result["exceeded"] is True
        assert result["threshold"] == 50


# ---------------------------------------------------------------------------
# get_cantonal_requirements_resolved
# ---------------------------------------------------------------------------


class TestGetCantonalRequirementsResolved:
    async def test_uses_pack_when_jurisdiction_exists(self, db_session, jurisdiction_chain):
        """When jurisdiction metadata exists, it should be used."""
        result = await get_cantonal_requirements_resolved(db_session, VD_ID, "VD")
        assert result["source"] == "regulatory_pack"
        assert result["authority_name"] == "DGE-DIRNA"
        assert result["diagnostic_required_before_year"] == 1991

    async def test_falls_back_to_hardcoded(self, db_session, jurisdiction_chain):
        """When jurisdiction_id is None, should fall back to hardcoded."""
        result = await get_cantonal_requirements_resolved(db_session, None, "VD")
        assert result["source"] == "hardcoded"
        assert result["authority_name"] == "DGE-DIRNA"
        assert result["canton"] == "VD"

    async def test_falls_back_for_unknown_jurisdiction(self, db_session):
        """When jurisdiction_id doesn't exist, should fall back to hardcoded."""
        result = await get_cantonal_requirements_resolved(db_session, uuid.uuid4(), "GE")
        assert result["source"] == "hardcoded"
        assert result["authority_name"] == "GESDEC"
        assert result["canton"] == "GE"

    async def test_falls_back_for_unknown_canton(self, db_session):
        """When both jurisdiction and canton are unknown, should use default."""
        result = await get_cantonal_requirements_resolved(db_session, uuid.uuid4(), "XX")
        assert result["source"] == "hardcoded"
        assert result["canton"] == "XX"
        assert result["authority_name"] == "Service cantonal de l'environnement"

    async def test_includes_notification_from_pack(self, db_session, cantonal_asbestos_pack):
        """When a cantonal asbestos pack exists, notification info should be included."""
        result = await get_cantonal_requirements_resolved(db_session, VD_ID, "VD")
        assert result["source"] == "regulatory_pack"
        assert result["notification_delay_days"] == 14
        assert result["notification_authority"] == "DGE-DIRNA"
