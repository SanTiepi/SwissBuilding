"""Tests for multi-audience pack builder service and API."""

import uuid
from datetime import datetime

import pytest

from app.models.building import Building
from app.models.claim import Claim
from app.models.financial_entry import FinancialEntry
from app.models.insurance_policy import InsurancePolicy
from app.models.intervention import Intervention
from app.models.obligation import Obligation
from app.models.zone import Zone
from app.services.pack_builder_service import (
    PACK_TYPES,
    generate_pack,
    list_available_packs,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db_session, **kwargs):
    created_by = kwargs.get("created_by", uuid.uuid4())
    building = Building(
        id=kwargs.get("id", uuid.uuid4()),
        address=kwargs.get("address", "10 Rue du Test"),
        postal_code=kwargs.get("postal_code", "1000"),
        city=kwargs.get("city", "Lausanne"),
        canton=kwargs.get("canton", "VD"),
        egid=kwargs.get("egid", 123456),
        construction_year=kwargs.get("construction_year", 1975),
        building_type=kwargs.get("building_type", "residential"),
        created_by=created_by,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


async def _create_intervention(db_session, building_id, **kwargs):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        title=kwargs.get("title", "Desamiantage facade"),
        intervention_type=kwargs.get("intervention_type", "removal"),
        status=kwargs.get("status", "completed"),
        date_start=kwargs.get("date_start"),
        date_end=kwargs.get("date_end"),
        contractor_name=kwargs.get("contractor_name", "Sanacore SA"),
    )
    db_session.add(intervention)
    await db_session.commit()
    return intervention


async def _create_zone(db_session, building_id, **kwargs):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        name=kwargs.get("name", "Sous-sol"),
        zone_type=kwargs.get("zone_type", "basement"),
        floor_number=kwargs.get("floor_number", -1),
        usage_type=kwargs.get("usage_type", "storage"),
    )
    db_session.add(zone)
    await db_session.commit()
    return zone


async def _create_obligation(db_session, building_id, **kwargs):
    obligation = Obligation(
        id=uuid.uuid4(),
        building_id=building_id,
        title=kwargs.get("title", "Renouvellement assurance"),
        obligation_type=kwargs.get("obligation_type", "insurance_renewal"),
        due_date=kwargs.get("due_date", datetime(2026, 6, 1).date()),
        status=kwargs.get("status", "upcoming"),
        priority=kwargs.get("priority", "medium"),
    )
    db_session.add(obligation)
    await db_session.commit()
    return obligation


async def _create_financial_entry(db_session, building_id, **kwargs):
    entry = FinancialEntry(
        id=uuid.uuid4(),
        building_id=building_id,
        entry_type=kwargs.get("entry_type", "expense"),
        category=kwargs.get("category", "maintenance"),
        amount_chf=kwargs.get("amount_chf", 5000.0),
        entry_date=kwargs.get("entry_date", datetime(2026, 1, 15).date()),
    )
    db_session.add(entry)
    await db_session.commit()
    return entry


async def _create_insurance_policy(db_session, building_id, **kwargs):
    policy = InsurancePolicy(
        id=uuid.uuid4(),
        building_id=building_id,
        policy_type=kwargs.get("policy_type", "building_eca"),
        policy_number=kwargs.get("policy_number", f"POL-{uuid.uuid4().hex[:8]}"),
        insurer_name=kwargs.get("insurer_name", "ECA Vaud"),
        date_start=kwargs.get("date_start", datetime(2025, 1, 1).date()),
        status=kwargs.get("status", "active"),
    )
    db_session.add(policy)
    await db_session.commit()
    return policy


async def _create_claim(db_session, building_id, policy_id, **kwargs):
    claim = Claim(
        id=uuid.uuid4(),
        insurance_policy_id=policy_id,
        building_id=building_id,
        claim_type=kwargs.get("claim_type", "water_damage"),
        incident_date=kwargs.get("incident_date", datetime(2025, 6, 1).date()),
        status=kwargs.get("status", "settled"),
    )
    db_session.add(claim)
    await db_session.commit()
    return claim


# ---------------------------------------------------------------------------
# Pack type configuration tests
# ---------------------------------------------------------------------------


class TestPackTypeConfig:
    def test_all_pack_types_defined(self):
        assert set(PACK_TYPES.keys()) == {"authority", "owner", "insurer", "contractor", "notary", "transfer"}

    def test_each_pack_has_required_fields(self):
        for pack_type, config in PACK_TYPES.items():
            assert "name" in config, f"{pack_type} missing name"
            assert "sections" in config, f"{pack_type} missing sections"
            assert "includes_trust" in config, f"{pack_type} missing includes_trust"
            assert "includes_provenance" in config, f"{pack_type} missing includes_provenance"

    def test_authority_pack_includes_trust_and_provenance(self):
        assert PACK_TYPES["authority"]["includes_trust"] is True
        assert PACK_TYPES["authority"]["includes_provenance"] is True

    def test_contractor_pack_excludes_trust_and_provenance(self):
        assert PACK_TYPES["contractor"]["includes_trust"] is False
        assert PACK_TYPES["contractor"]["includes_provenance"] is False

    def test_owner_pack_excludes_provenance(self):
        assert PACK_TYPES["owner"]["includes_provenance"] is False

    def test_transfer_pack_delegates_to_full(self):
        assert PACK_TYPES["transfer"]["sections"] == ["full"]


# ---------------------------------------------------------------------------
# Pack generation tests
# ---------------------------------------------------------------------------


class TestGeneratePack:
    @pytest.mark.asyncio
    async def test_generate_authority_pack(self, db_session):
        building = await _create_building(db_session)
        result = await generate_pack(db_session, building.id, "authority")

        assert result.pack_type == "authority"
        assert result.pack_name == "Pack Autorite"
        assert result.total_sections > 0
        assert result.sha256_hash is not None
        assert len(result.sha256_hash) == 64
        assert result.includes_trust is True
        assert result.includes_provenance is True

    @pytest.mark.asyncio
    async def test_generate_owner_pack(self, db_session):
        building = await _create_building(db_session)
        await _create_financial_entry(db_session, building.id)
        await _create_obligation(db_session, building.id)
        await _create_insurance_policy(db_session, building.id)

        result = await generate_pack(db_session, building.id, "owner")

        assert result.pack_type == "owner"
        assert result.pack_name == "Pack Proprietaire"
        assert result.includes_provenance is False
        # Should have cost_summary, upcoming_obligations, insurance_status sections
        section_types = [s.section_type for s in result.sections]
        assert "cost_summary" in section_types
        assert "upcoming_obligations" in section_types
        assert "insurance_status" in section_types

    @pytest.mark.asyncio
    async def test_generate_insurer_pack(self, db_session):
        building = await _create_building(db_session)
        policy = await _create_insurance_policy(db_session, building.id)
        await _create_claim(db_session, building.id, policy.id)

        result = await generate_pack(db_session, building.id, "insurer")

        assert result.pack_type == "insurer"
        section_types = [s.section_type for s in result.sections]
        assert "risk_summary" in section_types
        assert "claims_history" in section_types

    @pytest.mark.asyncio
    async def test_generate_contractor_pack(self, db_session):
        building = await _create_building(db_session)
        await _create_zone(db_session, building.id)
        await _create_intervention(db_session, building.id)

        result = await generate_pack(db_session, building.id, "contractor")

        assert result.pack_type == "contractor"
        assert result.includes_trust is False
        section_types = [s.section_type for s in result.sections]
        assert "scope_summary" in section_types
        assert "zones_concerned" in section_types
        assert "safety_requirements" in section_types
        assert "regulatory_requirements" in section_types
        assert "work_conditions" in section_types

    @pytest.mark.asyncio
    async def test_generate_notary_pack(self, db_session):
        building = await _create_building(db_session)
        result = await generate_pack(db_session, building.id, "notary")

        assert result.pack_type == "notary"
        assert result.includes_provenance is True
        section_types = [s.section_type for s in result.sections]
        assert "contradictions" in section_types
        assert "caveats" in section_types

    @pytest.mark.asyncio
    async def test_generate_unknown_type_raises(self, db_session):
        building = await _create_building(db_session)
        with pytest.raises(ValueError, match="Unknown pack type"):
            await generate_pack(db_session, building.id, "invalid_type")

    @pytest.mark.asyncio
    async def test_generate_nonexistent_building_raises(self, db_session):
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="Building not found"):
            await generate_pack(db_session, fake_id, "authority")

    @pytest.mark.asyncio
    async def test_pack_has_sha256_hash(self, db_session):
        building = await _create_building(db_session)
        result = await generate_pack(db_session, building.id, "owner")
        assert result.sha256_hash is not None
        assert len(result.sha256_hash) == 64

    @pytest.mark.asyncio
    async def test_pack_caveats_include_liability(self, db_session):
        building = await _create_building(db_session)
        result = await generate_pack(db_session, building.id, "authority")
        caveats_section = next((s for s in result.sections if s.section_type == "caveats"), None)
        assert caveats_section is not None
        liability_caveats = [c for c in caveats_section.items if c.get("caveat_type") == "liability"]
        assert len(liability_caveats) >= 1

    @pytest.mark.asyncio
    async def test_notary_pack_has_transaction_caveat(self, db_session):
        building = await _create_building(db_session)
        result = await generate_pack(db_session, building.id, "notary")
        caveats_section = next((s for s in result.sections if s.section_type == "caveats"), None)
        assert caveats_section is not None
        transaction_caveats = [c for c in caveats_section.items if c.get("caveat_type") == "transaction"]
        assert len(transaction_caveats) >= 1

    @pytest.mark.asyncio
    async def test_contractor_pack_has_scope_caveat(self, db_session):
        """Contractor pack should NOT have caveats section (not in section list)."""
        building = await _create_building(db_session)
        result = await generate_pack(db_session, building.id, "contractor")
        # Contractor doesn't include caveats in its section list
        section_types = [s.section_type for s in result.sections]
        assert "caveats" not in section_types


# ---------------------------------------------------------------------------
# Section builder tests
# ---------------------------------------------------------------------------


class TestSectionBuilders:
    @pytest.mark.asyncio
    async def test_cost_summary_with_data(self, db_session):
        building = await _create_building(db_session)
        await _create_financial_entry(db_session, building.id, entry_type="expense", amount_chf=1000)
        await _create_financial_entry(
            db_session, building.id, entry_type="income", category="rent_income", amount_chf=2000
        )

        result = await generate_pack(db_session, building.id, "owner")
        cost_section = next((s for s in result.sections if s.section_type == "cost_summary"), None)
        assert cost_section is not None
        assert cost_section.completeness == 1.0
        assert cost_section.items[0]["total_expenses_chf"] == 1000.0
        assert cost_section.items[0]["total_income_chf"] == 2000.0

    @pytest.mark.asyncio
    async def test_cost_summary_empty(self, db_session):
        building = await _create_building(db_session)
        result = await generate_pack(db_session, building.id, "owner")
        cost_section = next((s for s in result.sections if s.section_type == "cost_summary"), None)
        assert cost_section is not None
        assert cost_section.completeness == 0.0

    @pytest.mark.asyncio
    async def test_insurance_status_with_policies(self, db_session):
        building = await _create_building(db_session)
        await _create_insurance_policy(db_session, building.id, status="active")
        await _create_insurance_policy(db_session, building.id, status="expired")

        result = await generate_pack(db_session, building.id, "owner")
        ins_section = next((s for s in result.sections if s.section_type == "insurance_status"), None)
        assert ins_section is not None
        assert ins_section.completeness == 1.0
        assert len(ins_section.items) == 2

    @pytest.mark.asyncio
    async def test_zones_concerned(self, db_session):
        building = await _create_building(db_session)
        await _create_zone(db_session, building.id, name="Cave", zone_type="basement")
        await _create_zone(db_session, building.id, name="RDC", zone_type="ground_floor", floor_number=0)

        result = await generate_pack(db_session, building.id, "contractor")
        zone_section = next((s for s in result.sections if s.section_type == "zones_concerned"), None)
        assert zone_section is not None
        assert len(zone_section.items) == 2

    @pytest.mark.asyncio
    async def test_claims_history(self, db_session):
        building = await _create_building(db_session)
        policy = await _create_insurance_policy(db_session, building.id)
        await _create_claim(db_session, building.id, policy.id, status="settled")
        await _create_claim(db_session, building.id, policy.id, status="open", claim_type="fire")

        result = await generate_pack(db_session, building.id, "insurer")
        claims_section = next((s for s in result.sections if s.section_type == "claims_history"), None)
        assert claims_section is not None
        assert len(claims_section.items) == 2

    @pytest.mark.asyncio
    async def test_safety_requirements_always_populated(self, db_session):
        building = await _create_building(db_session)
        result = await generate_pack(db_session, building.id, "contractor")
        safety_section = next((s for s in result.sections if s.section_type == "safety_requirements"), None)
        assert safety_section is not None
        assert safety_section.completeness == 1.0
        assert len(safety_section.items) >= 5

    @pytest.mark.asyncio
    async def test_regulatory_requirements_for_old_building(self, db_session):
        building = await _create_building(db_session, construction_year=1960)
        result = await generate_pack(db_session, building.id, "contractor")
        reg_section = next((s for s in result.sections if s.section_type == "regulatory_requirements"), None)
        assert reg_section is not None
        # OTConst asbestos should be applicable for pre-1990 buildings
        asbestos_rule = next((i for i in reg_section.items if i.get("domain") == "Amiante"), None)
        assert asbestos_rule is not None
        assert asbestos_rule["applicable"] is True


# ---------------------------------------------------------------------------
# List available packs tests
# ---------------------------------------------------------------------------


class TestListAvailablePacks:
    @pytest.mark.asyncio
    async def test_lists_all_pack_types(self, db_session):
        building = await _create_building(db_session)
        result = await list_available_packs(db_session, building.id)

        assert result.building_id == building.id
        assert len(result.packs) == 6
        pack_types = {p.pack_type for p in result.packs}
        assert pack_types == {"authority", "owner", "insurer", "contractor", "notary", "transfer"}

    @pytest.mark.asyncio
    async def test_each_pack_has_readiness(self, db_session):
        building = await _create_building(db_session)
        result = await list_available_packs(db_session, building.id)

        for pack in result.packs:
            assert pack.readiness in ("ready", "partial", "not_ready")
            assert 0.0 <= pack.readiness_score <= 1.0

    @pytest.mark.asyncio
    async def test_nonexistent_building_raises(self, db_session):
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="Building not found"):
            await list_available_packs(db_session, fake_id)
