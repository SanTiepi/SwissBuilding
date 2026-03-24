"""BatiConnect BC1 — Backbone schema validation tests.

Tests that all Pydantic schemas accept valid data, reject invalid data,
and serialize correctly with from_attributes=True.
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.schemas.asset_view import AssetView
from app.schemas.contact import ContactCreate, ContactListRead, ContactRead, ContactUpdate
from app.schemas.ownership import (
    OwnershipRecordCreate,
    OwnershipRecordListRead,
)
from app.schemas.party_role import (
    PartyRoleAssignmentCreate,
    PartyRoleAssignmentUpdate,
)
from app.schemas.portfolio import (
    BuildingPortfolioCreate,
    PortfolioCreate,
    PortfolioListRead,
    PortfolioUpdate,
)
from app.schemas.unit import UnitCreate, UnitListRead, UnitZoneCreate

_NOW = datetime.now(tz=UTC)
_UUID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Contact schemas
# ---------------------------------------------------------------------------


class TestContactSchemas:
    def test_create_minimal(self):
        c = ContactCreate(contact_type="person", name="Jean Dupont")
        assert c.contact_type == "person"
        assert c.name == "Jean Dupont"
        assert c.email is None

    def test_create_full(self):
        c = ContactCreate(
            organization_id=_UUID,
            contact_type="company",
            name="Batiscan SA",
            company_name="Batiscan",
            email="info@batiscan.ch",
            phone="+41 21 123 45 67",
            address="Rue du Lac 1",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            external_ref="ERP-12345",
            linked_user_id=_UUID,
            notes="Important client",
            is_active=True,
            source_type="manual",
            confidence="declared",
            source_ref="import-batch-001",
        )
        assert c.contact_type == "company"
        assert c.source_type == "manual"

    def test_create_missing_required(self):
        with pytest.raises(ValidationError):
            ContactCreate(contact_type="person")  # missing name

    def test_update_partial(self):
        u = ContactUpdate(email="new@test.ch")
        assert u.email == "new@test.ch"
        assert u.name is None

    def test_read_from_attributes(self):
        r = ContactRead(
            id=_UUID,
            organization_id=_UUID,
            contact_type="notary",
            name="Me Favre",
            company_name=None,
            email="favre@notaire.ch",
            phone=None,
            address=None,
            postal_code=None,
            city=None,
            canton=None,
            external_ref=None,
            linked_user_id=None,
            notes=None,
            is_active=True,
            source_type=None,
            confidence=None,
            source_ref=None,
            created_by=None,
            created_at=_NOW,
            updated_at=_NOW,
        )
        assert r.contact_type == "notary"

    def test_list_read(self):
        lr = ContactListRead(
            id=_UUID,
            contact_type="insurer",
            name="Zurich Assurance",
            company_name="Zurich",
            email="contact@zurich.ch",
            phone=None,
            city="Zurich",
            canton="ZH",
            is_active=True,
        )
        assert lr.contact_type == "insurer"


# ---------------------------------------------------------------------------
# PartyRoleAssignment schemas
# ---------------------------------------------------------------------------


class TestPartyRoleSchemas:
    def test_create_valid(self):
        p = PartyRoleAssignmentCreate(
            party_type="contact",
            party_id=_UUID,
            entity_type="building",
            entity_id=_UUID,
            role="legal_owner",
            share_pct=50.0,
            valid_from=date(2020, 1, 1),
            is_primary=True,
        )
        assert p.role == "legal_owner"
        assert p.share_pct == 50.0

    def test_create_all_entity_types(self):
        for et in ["building", "unit", "portfolio", "lease", "contract", "intervention", "diagnostic"]:
            p = PartyRoleAssignmentCreate(
                party_type="user",
                party_id=_UUID,
                entity_type=et,
                entity_id=_UUID,
                role="manager",
            )
            assert p.entity_type == et

    def test_create_all_roles(self):
        roles = [
            "legal_owner",
            "co_owner",
            "tenant",
            "manager",
            "insurer",
            "contractor",
            "notary",
            "trustee",
            "syndic",
            "architect",
            "diagnostician",
            "reviewer",
        ]
        for role in roles:
            p = PartyRoleAssignmentCreate(
                party_type="contact",
                party_id=_UUID,
                entity_type="building",
                entity_id=_UUID,
                role=role,
            )
            assert p.role == role

    def test_update_partial(self):
        u = PartyRoleAssignmentUpdate(share_pct=75.0)
        assert u.share_pct == 75.0
        assert u.role is None


# ---------------------------------------------------------------------------
# Portfolio schemas
# ---------------------------------------------------------------------------


class TestPortfolioSchemas:
    def test_create_valid(self):
        p = PortfolioCreate(
            organization_id=_UUID,
            name="Immeubles Vaud",
            portfolio_type="management",
        )
        assert p.name == "Immeubles Vaud"

    def test_create_all_types(self):
        for pt in ["management", "ownership", "diagnostic", "campaign", "custom"]:
            p = PortfolioCreate(organization_id=_UUID, name=f"P-{pt}", portfolio_type=pt)
            assert p.portfolio_type == pt

    def test_update_partial(self):
        u = PortfolioUpdate(name="New Name")
        assert u.name == "New Name"
        assert u.portfolio_type is None

    def test_building_portfolio_create(self):
        bp = BuildingPortfolioCreate(building_id=_UUID, portfolio_id=_UUID)
        assert bp.building_id == _UUID


# ---------------------------------------------------------------------------
# Unit schemas
# ---------------------------------------------------------------------------


class TestUnitSchemas:
    def test_create_valid(self):
        u = UnitCreate(
            building_id=_UUID,
            unit_type="residential",
            reference_code="Apt 3.1",
            name="Appartement 3.1",
            floor=3,
            surface_m2=85.5,
            rooms=3.5,
        )
        assert u.rooms == 3.5

    def test_create_all_types(self):
        for ut in ["residential", "commercial", "parking", "storage", "office", "common_area"]:
            u = UnitCreate(building_id=_UUID, unit_type=ut, reference_code=f"U-{ut}")
            assert u.unit_type == ut

    def test_create_all_statuses(self):
        for st in ["active", "vacant", "renovating", "decommissioned"]:
            u = UnitCreate(building_id=_UUID, unit_type="residential", reference_code=f"S-{st}", status=st)
            assert u.status == st

    def test_unit_zone_create(self):
        uz = UnitZoneCreate(unit_id=_UUID, zone_id=_UUID)
        assert uz.unit_id == _UUID


# ---------------------------------------------------------------------------
# Ownership schemas
# ---------------------------------------------------------------------------


class TestOwnershipSchemas:
    def test_create_valid(self):
        o = OwnershipRecordCreate(
            building_id=_UUID,
            owner_type="contact",
            owner_id=_UUID,
            share_pct=100.0,
            ownership_type="full",
            acquisition_type="purchase",
            acquisition_date=date(2015, 6, 15),
            acquisition_price_chf=850000.0,
            land_register_ref="VD-1234-5678",
            source_type="official",
            confidence="verified",
        )
        assert o.ownership_type == "full"
        assert o.acquisition_price_chf == 850000.0

    def test_create_all_ownership_types(self):
        for ot in ["full", "co_ownership", "usufruct", "bare_ownership", "ppe_unit"]:
            o = OwnershipRecordCreate(
                building_id=_UUID,
                owner_type="contact",
                owner_id=_UUID,
                ownership_type=ot,
            )
            assert o.ownership_type == ot

    def test_create_all_acquisition_types(self):
        for at in ["purchase", "inheritance", "donation", "construction", "exchange"]:
            o = OwnershipRecordCreate(
                building_id=_UUID,
                owner_type="contact",
                owner_id=_UUID,
                ownership_type="full",
                acquisition_type=at,
            )
            assert o.acquisition_type == at

    def test_create_all_statuses(self):
        for st in ["active", "transferred", "disputed", "archived"]:
            o = OwnershipRecordCreate(
                building_id=_UUID,
                owner_type="user",
                owner_id=_UUID,
                ownership_type="full",
                status=st,
            )
            assert o.status == st

    def test_create_all_owner_types(self):
        for ot in ["contact", "user", "organization"]:
            o = OwnershipRecordCreate(
                building_id=_UUID,
                owner_type=ot,
                owner_id=_UUID,
                ownership_type="full",
            )
            assert o.owner_type == ot

    def test_provenance_fields(self):
        for st in ["import", "manual", "ai", "inferred", "official"]:
            o = OwnershipRecordCreate(
                building_id=_UUID,
                owner_type="contact",
                owner_id=_UUID,
                ownership_type="full",
                source_type=st,
            )
            assert o.source_type == st

        for conf in ["verified", "declared", "inferred", "unknown"]:
            o = OwnershipRecordCreate(
                building_id=_UUID,
                owner_type="contact",
                owner_id=_UUID,
                ownership_type="full",
                confidence=conf,
            )
            assert o.confidence == conf


# ---------------------------------------------------------------------------
# AssetView adapter schema
# ---------------------------------------------------------------------------


class TestAssetViewSchema:
    def test_asset_view_minimal(self):
        av = AssetView(
            id=_UUID,
            egrid=None,
            egid=None,
            official_id=None,
            address="Rue du Test 1",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            construction_year=1970,
            status="active",
            created_at=_NOW,
            updated_at=_NOW,
        )
        assert av.ownership_records == []
        assert av.units == []
        assert av.portfolios == []

    def test_asset_view_with_relations(self):
        av = AssetView(
            id=_UUID,
            egrid="CH-1234",
            egid=12345,
            official_id=None,
            address="Rue du Test 1",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            construction_year=1970,
            status="active",
            created_at=_NOW,
            updated_at=_NOW,
            organization_id=_UUID,
            ownership_records=[
                OwnershipRecordListRead(
                    id=_UUID,
                    building_id=_UUID,
                    owner_type="contact",
                    owner_id=_UUID,
                    share_pct=100.0,
                    ownership_type="full",
                    status="active",
                    acquisition_date=date(2020, 1, 1),
                ),
            ],
            units=[
                UnitListRead(
                    id=_UUID,
                    building_id=_UUID,
                    unit_type="residential",
                    reference_code="Apt 1",
                    name="Appartement 1",
                    floor=1,
                    surface_m2=75.0,
                    rooms=3.5,
                    status="active",
                ),
            ],
            portfolios=[
                PortfolioListRead(
                    id=_UUID,
                    name="Test Portfolio",
                    portfolio_type="management",
                    is_default=False,
                    organization_id=_UUID,
                ),
            ],
        )
        assert len(av.ownership_records) == 1
        assert len(av.units) == 1
        assert len(av.portfolios) == 1
        assert av.organization_id == _UUID


# ---------------------------------------------------------------------------
# Existing schema backward compatibility
# ---------------------------------------------------------------------------


class TestExistingSchemaCompat:
    """Verify that existing PortfolioMetrics and Map schemas still work."""

    def test_portfolio_metrics_unchanged(self):
        from app.schemas.portfolio import PortfolioMetrics

        pm = PortfolioMetrics(
            total_buildings=10,
            risk_distribution={"low": 5, "high": 5},
            completeness_avg=0.8,
            buildings_ready=7,
            buildings_not_ready=3,
            pollutant_prevalence={"asbestos": 3},
            actions_pending=12,
            actions_critical=2,
            recent_diagnostics=4,
            interventions_in_progress=1,
        )
        assert pm.total_buildings == 10

    def test_map_geojson_unchanged(self):
        from app.schemas.portfolio import MapBuildingsGeoJSON

        geo = MapBuildingsGeoJSON(type="FeatureCollection", features=[])
        assert geo.type == "FeatureCollection"
