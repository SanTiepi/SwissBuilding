"""Tests for the rule_resolver service — jurisdiction-aware regulatory pack resolution."""

import uuid

import pytest

from app.models.jurisdiction import Jurisdiction
from app.models.regulatory_pack import RegulatoryPack
from app.services.rule_resolver import (
    resolve_cantonal_requirements,
    resolve_notification_rules,
    resolve_risk_calibration,
    resolve_threshold,
    resolve_waste_classification,
    resolve_work_categories,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EU_ID = uuid.uuid4()
CH_ID = uuid.uuid4()
VD_ID = uuid.uuid4()


@pytest.fixture
async def jurisdiction_chain(db_session):
    """Create EU → CH → CH-VD jurisdiction chain."""
    eu = Jurisdiction(
        id=EU_ID,
        code="eu",
        name="European Union",
        parent_id=None,
        level="supranational",
    )
    ch = Jurisdiction(
        id=CH_ID,
        code="ch",
        name="Suisse",
        parent_id=EU_ID,
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
    db_session.add_all([eu, ch, vd])
    await db_session.flush()
    return {"eu": eu, "ch": ch, "vd": vd}


@pytest.fixture
async def federal_asbestos_pack(db_session, jurisdiction_chain):
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
        risk_year_start=1920,
        risk_year_end=1990,
        base_probability=0.85,
        work_categories_json={"minor": "≤5m², good condition", "medium": "degraded", "major": "friable"},
        waste_classification_json={"friable": "special", "bonded_good": "type_b", "default": "type_e"},
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
    """Create a cantonal-level asbestos pack (overrides federal for VD)."""
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
# resolve_threshold
# ---------------------------------------------------------------------------


class TestResolveThreshold:
    async def test_returns_none_for_null_jurisdiction(self, db_session):
        result = await resolve_threshold(db_session, None, "asbestos", "percent_weight")
        assert result is None

    async def test_returns_none_when_no_pack(self, db_session, jurisdiction_chain):
        result = await resolve_threshold(db_session, VD_ID, "asbestos", "percent_weight")
        assert result is None

    async def test_resolves_federal_pack(self, db_session, federal_asbestos_pack):
        result = await resolve_threshold(db_session, CH_ID, "asbestos", "percent_weight")
        assert result is not None
        assert result["threshold"] == 1.0
        assert result["unit"] == "percent_weight"
        assert result["legal_ref"] == "OTConst Art. 82"
        assert result["action"] == "remediate"

    async def test_walks_hierarchy_to_federal(self, db_session, federal_asbestos_pack):
        """VD has no pack → should walk up to CH and find federal pack."""
        result = await resolve_threshold(db_session, VD_ID, "asbestos", "percent_weight")
        assert result is not None
        assert result["threshold"] == 1.0

    async def test_cantonal_overrides_federal(self, db_session, federal_asbestos_pack, cantonal_asbestos_pack):
        """VD has its own pack → should use cantonal, not federal."""
        result = await resolve_threshold(db_session, VD_ID, "asbestos", "percent_weight")
        assert result is not None
        assert result["legal_ref"] == "OTConst Art. 82 + Directive VD"

    async def test_unit_mismatch_returns_none(self, db_session, federal_asbestos_pack):
        """Pack has percent_weight, but we ask for mg_per_kg → no match."""
        result = await resolve_threshold(db_session, CH_ID, "asbestos", "mg_per_kg")
        assert result is None

    async def test_inactive_pack_ignored(self, db_session, jurisdiction_chain):
        """Inactive packs should not be returned."""
        pack = RegulatoryPack(
            id=uuid.uuid4(),
            jurisdiction_id=CH_ID,
            pollutant_type="pcb",
            version="1.0",
            is_active=False,
            threshold_value=50.0,
            threshold_unit="mg_per_kg",
        )
        db_session.add(pack)
        await db_session.flush()

        result = await resolve_threshold(db_session, CH_ID, "pcb", "mg_per_kg")
        assert result is None


# ---------------------------------------------------------------------------
# resolve_cantonal_requirements
# ---------------------------------------------------------------------------


class TestResolvCantonalRequirements:
    async def test_returns_none_for_null_jurisdiction(self, db_session):
        result = await resolve_cantonal_requirements(db_session, None)
        assert result is None

    async def test_returns_none_for_unknown_jurisdiction(self, db_session):
        result = await resolve_cantonal_requirements(db_session, uuid.uuid4())
        assert result is None

    async def test_returns_metadata(self, db_session, jurisdiction_chain):
        result = await resolve_cantonal_requirements(db_session, VD_ID)
        assert result is not None
        assert result["authority_name"] == "DGE-DIRNA"
        assert result["diagnostic_required_before_year"] == 1991
        assert result["requires_waste_elimination_plan"] is True
        assert result["form_name"] == "Plan d'elimination des dechets (PED)"

    async def test_includes_notification_from_pack(self, db_session, cantonal_asbestos_pack):
        result = await resolve_cantonal_requirements(db_session, VD_ID)
        assert result is not None
        assert result["notification_delay_days"] == 14
        assert result["notification_authority"] == "DGE-DIRNA"


# ---------------------------------------------------------------------------
# resolve_risk_calibration
# ---------------------------------------------------------------------------


class TestResolveRiskCalibration:
    async def test_returns_none_for_null_jurisdiction(self, db_session):
        result = await resolve_risk_calibration(db_session, None, "asbestos")
        assert result is None

    async def test_returns_calibration_data(self, db_session, federal_asbestos_pack):
        result = await resolve_risk_calibration(db_session, CH_ID, "asbestos")
        assert result is not None
        assert result["risk_year_start"] == 1920
        assert result["risk_year_end"] == 1990
        assert result["base_probability"] == 0.85

    async def test_walks_hierarchy(self, db_session, federal_asbestos_pack):
        """VD → CH should find federal pack."""
        result = await resolve_risk_calibration(db_session, VD_ID, "asbestos")
        assert result is not None
        assert result["base_probability"] == 0.85


# ---------------------------------------------------------------------------
# resolve_work_categories
# ---------------------------------------------------------------------------


class TestResolveWorkCategories:
    async def test_returns_none_for_null(self, db_session):
        result = await resolve_work_categories(db_session, None, "asbestos")
        assert result is None

    async def test_returns_categories(self, db_session, federal_asbestos_pack):
        result = await resolve_work_categories(db_session, CH_ID, "asbestos")
        assert result is not None
        assert "minor" in result
        assert "major" in result


# ---------------------------------------------------------------------------
# resolve_waste_classification
# ---------------------------------------------------------------------------


class TestResolveWasteClassification:
    async def test_returns_none_for_null(self, db_session):
        result = await resolve_waste_classification(db_session, None, "asbestos")
        assert result is None

    async def test_returns_classification(self, db_session, federal_asbestos_pack):
        result = await resolve_waste_classification(db_session, CH_ID, "asbestos")
        assert result is not None
        assert result["friable"] == "special"


# ---------------------------------------------------------------------------
# resolve_notification_rules
# ---------------------------------------------------------------------------


class TestResolveNotificationRules:
    async def test_returns_none_for_null(self, db_session):
        result = await resolve_notification_rules(db_session, None, "asbestos")
        assert result is None

    async def test_returns_rules(self, db_session, federal_asbestos_pack):
        result = await resolve_notification_rules(db_session, CH_ID, "asbestos")
        assert result is not None
        assert result["notification_required"] is True
        assert result["notification_authority"] == "SUVA"
        assert result["notification_delay_days"] == 14

    async def test_returns_none_when_no_pack(self, db_session, jurisdiction_chain):
        result = await resolve_notification_rules(db_session, VD_ID, "pcb")
        assert result is None
