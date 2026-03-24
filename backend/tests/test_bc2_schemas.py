"""BatiConnect BC2 — Property management schema validation tests."""

import uuid
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.schemas.claim import ClaimCreate
from app.schemas.contract import ContractCreate
from app.schemas.document_link import DocumentLinkCreate
from app.schemas.financial_entry import FinancialEntryCreate
from app.schemas.insurance_policy import InsurancePolicyCreate
from app.schemas.inventory_item import InventoryItemCreate
from app.schemas.lease import LeaseCreate, LeaseEventCreate
from app.schemas.tax_context import TaxContextCreate

_NOW = datetime.now(tz=UTC)
_UUID = uuid.uuid4()


class TestLeaseSchemas:
    def test_create_full(self):
        lease = LeaseCreate(
            building_id=_UUID,
            lease_type="residential",
            reference_code="BAIL-001",
            tenant_type="contact",
            tenant_id=_UUID,
            date_start=date(2023, 1, 1),
            rent_monthly_chf=1800.0,
            rooms=3.5,
            source_type="manual",
            confidence="declared",
        )
        assert lease.lease_type == "residential"

    def test_create_missing_required(self):
        with pytest.raises(ValidationError):
            LeaseCreate(
                building_id=_UUID, lease_type="residential"
            )  # missing reference_code, tenant_type, tenant_id, date_start

    def test_all_lease_types(self):
        for lt in ["residential", "commercial", "mixed", "parking", "storage", "short_term"]:
            lease = LeaseCreate(
                building_id=_UUID,
                lease_type=lt,
                reference_code=f"L-{lt}",
                tenant_type="contact",
                tenant_id=_UUID,
                date_start=date(2023, 1, 1),
            )
            assert lease.lease_type == lt

    def test_all_statuses(self):
        for st in ["draft", "active", "terminated", "expired", "disputed"]:
            lease = LeaseCreate(
                building_id=_UUID,
                lease_type="residential",
                reference_code=f"S-{st}",
                tenant_type="contact",
                tenant_id=_UUID,
                date_start=date(2023, 1, 1),
                status=st,
            )
            assert lease.status == st

    def test_event_create(self):
        e = LeaseEventCreate(
            lease_id=_UUID,
            event_type="rent_adjustment",
            event_date=date(2024, 1, 1),
            old_value_json={"rent": 1800},
            new_value_json={"rent": 1850},
        )
        assert e.event_type == "rent_adjustment"

    def test_all_event_types(self):
        for et in [
            "creation",
            "renewal",
            "rent_adjustment",
            "notice_sent",
            "notice_received",
            "termination",
            "dispute",
            "deposit_return",
        ]:
            e = LeaseEventCreate(lease_id=_UUID, event_type=et, event_date=date(2024, 1, 1))
            assert e.event_type == et


class TestContractSchemas:
    def test_create_full(self):
        c = ContractCreate(
            building_id=_UUID,
            contract_type="maintenance",
            reference_code="CTR-001",
            title="Entretien chauffage",
            counterparty_type="contact",
            counterparty_id=_UUID,
            date_start=date(2023, 1, 1),
            annual_cost_chf=3600.0,
            payment_frequency="quarterly",
            auto_renewal=True,
            source_type="manual",
            confidence="verified",
        )
        assert c.contract_type == "maintenance"

    def test_all_contract_types(self):
        types = [
            "maintenance",
            "management_mandate",
            "concierge",
            "cleaning",
            "elevator",
            "heating",
            "insurance",
            "security",
            "energy",
            "other",
        ]
        for ct in types:
            c = ContractCreate(
                building_id=_UUID,
                contract_type=ct,
                reference_code=f"C-{ct}",
                title=f"Contract {ct}",
                counterparty_type="organization",
                counterparty_id=_UUID,
                date_start=date(2023, 1, 1),
            )
            assert c.contract_type == ct

    def test_all_statuses(self):
        for st in ["draft", "active", "suspended", "terminated", "expired"]:
            c = ContractCreate(
                building_id=_UUID,
                contract_type="other",
                reference_code=f"CS-{st}",
                title="t",
                counterparty_type="contact",
                counterparty_id=_UUID,
                date_start=date(2023, 1, 1),
                status=st,
            )
            assert c.status == st


class TestInsurancePolicySchemas:
    def test_create_full(self):
        p = InsurancePolicyCreate(
            building_id=_UUID,
            policy_type="building_eca",
            policy_number="ECA-VD-001",
            insurer_name="ECA Vaud",
            insured_value_chf=1200000.0,
            premium_annual_chf=850.0,
            date_start=date(2024, 1, 1),
            source_type="official",
            confidence="verified",
        )
        assert p.policy_type == "building_eca"

    def test_all_policy_types(self):
        types = [
            "building_eca",
            "rc_owner",
            "rc_building",
            "natural_hazard",
            "construction_risk",
            "complementary",
            "contents",
        ]
        for pt in types:
            p = InsurancePolicyCreate(
                building_id=_UUID,
                policy_type=pt,
                policy_number=f"P-{pt}",
                insurer_name="X",
                date_start=date(2024, 1, 1),
            )
            assert p.policy_type == pt


class TestClaimSchemas:
    def test_create_full(self):
        c = ClaimCreate(
            insurance_policy_id=_UUID,
            building_id=_UUID,
            claim_type="water_damage",
            incident_date=date(2024, 6, 15),
            claimed_amount_chf=25000.0,
        )
        assert c.claim_type == "water_damage"

    def test_all_claim_types(self):
        for ct in ["water_damage", "fire", "natural_hazard", "liability", "theft", "pollutant_related", "other"]:
            c = ClaimCreate(
                insurance_policy_id=_UUID,
                building_id=_UUID,
                claim_type=ct,
                incident_date=date(2024, 1, 1),
            )
            assert c.claim_type == ct

    def test_all_statuses(self):
        for st in ["open", "in_review", "approved", "rejected", "settled", "closed"]:
            c = ClaimCreate(
                insurance_policy_id=_UUID,
                building_id=_UUID,
                claim_type="other",
                incident_date=date(2024, 1, 1),
                status=st,
            )
            assert c.status == st


class TestFinancialEntrySchemas:
    def test_create_full(self):
        f = FinancialEntryCreate(
            building_id=_UUID,
            entry_type="income",
            category="rent_income",
            amount_chf=1800.0,
            entry_date=date(2024, 3, 1),
            fiscal_year=2024,
            source_type="import",
            confidence="verified",
        )
        assert f.entry_type == "income"

    def test_entry_types(self):
        for et in ["expense", "income"]:
            f = FinancialEntryCreate(
                building_id=_UUID,
                entry_type=et,
                category="other_expense",
                amount_chf=100.0,
                entry_date=date(2024, 1, 1),
            )
            assert f.entry_type == et

    def test_provenance_fields(self):
        for st in ["import", "manual", "ai", "inferred", "official"]:
            f = FinancialEntryCreate(
                building_id=_UUID,
                entry_type="expense",
                category="maintenance",
                amount_chf=100.0,
                entry_date=date(2024, 1, 1),
                source_type=st,
            )
            assert f.source_type == st


class TestTaxContextSchemas:
    def test_create_full(self):
        t = TaxContextCreate(
            building_id=_UUID,
            tax_type="property_tax",
            fiscal_year=2024,
            official_value_chf=950000.0,
            canton="VD",
            municipality="Lausanne",
            source_type="official",
            confidence="verified",
        )
        assert t.tax_type == "property_tax"

    def test_all_tax_types(self):
        for tt in ["property_tax", "impot_foncier", "valeur_locative", "tax_estimation"]:
            t = TaxContextCreate(
                building_id=_UUID,
                tax_type=tt,
                fiscal_year=2024,
                canton="VD",
            )
            assert t.tax_type == tt

    def test_all_statuses(self):
        for st in ["estimated", "assessed", "contested", "final"]:
            t = TaxContextCreate(
                building_id=_UUID,
                tax_type="property_tax",
                fiscal_year=2024,
                canton="VD",
                status=st,
            )
            assert t.status == st


class TestInventoryItemSchemas:
    def test_create_full(self):
        i = InventoryItemCreate(
            building_id=_UUID,
            item_type="elevator",
            name="Ascenseur principal",
            manufacturer="Schindler",
            model="S5500",
            serial_number="SCH-001",
            condition="good",
            purchase_cost_chf=85000.0,
            source_type="manual",
            confidence="declared",
        )
        assert i.item_type == "elevator"

    def test_all_item_types(self):
        types = [
            "hvac",
            "boiler",
            "elevator",
            "fire_system",
            "electrical_panel",
            "solar_panel",
            "heat_pump",
            "ventilation",
            "water_heater",
            "garage_door",
            "intercom",
            "appliance",
            "furniture",
            "other",
        ]
        for it in types:
            i = InventoryItemCreate(building_id=_UUID, item_type=it, name=f"Item {it}")
            assert i.item_type == it

    def test_all_conditions(self):
        for c in ["good", "fair", "poor", "critical", "unknown"]:
            i = InventoryItemCreate(building_id=_UUID, item_type="hvac", name="X", condition=c)
            assert i.condition == c


class TestDocumentLinkSchemas:
    def test_create(self):
        dl = DocumentLinkCreate(
            document_id=_UUID,
            entity_type="building",
            entity_id=_UUID,
            link_type="attachment",
        )
        assert dl.entity_type == "building"

    def test_all_entity_types(self):
        types = [
            "building",
            "diagnostic",
            "intervention",
            "lease",
            "contract",
            "insurance_policy",
            "claim",
            "compliance_artefact",
            "evidence_pack",
        ]
        for et in types:
            dl = DocumentLinkCreate(document_id=_UUID, entity_type=et, entity_id=_UUID, link_type="attachment")
            assert dl.entity_type == et

    def test_all_link_types(self):
        for lt in ["attachment", "report", "proof", "reference", "invoice", "certificate"]:
            dl = DocumentLinkCreate(document_id=_UUID, entity_type="building", entity_id=_UUID, link_type=lt)
            assert dl.link_type == lt
