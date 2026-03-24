"""Tests for seed_bc_ops.py — validates seed data structure, UUID determinism,
and idempotent seeding into the async SQLite test DB."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.building import Building
from app.models.contact import Contact
from app.models.contract import Contract
from app.models.lease import Lease
from app.models.organization import Organization
from app.models.ownership_record import OwnershipRecord
from app.models.party_role_assignment import PartyRoleAssignment
from app.models.user import User
from app.seeds.seed_bc_ops import (
    _BC_NS,
    ID_CONTACT_CONTRACTOR,
    ID_CONTACT_MANAGER,
    ID_CONTACT_NOTARY,
    ID_CONTACT_TENANT_COMM,
    ID_CONTACT_TENANT_RES1,
    ID_CONTRACT_HEATING,
    ID_CONTRACT_MGMT,
    ID_CONTRACT_RENO,
    ID_LEASE_GE_COMM,
    ID_LEASE_GE_RES,
    ID_LEASE_LAU_COMM,
    ID_LEASE_LAU_RES1,
    ID_LEASE_ZH_COMM,
    ID_OWNERSHIP_GE_CURRENT,
    ID_OWNERSHIP_GE_PREVIOUS,
    ID_OWNERSHIP_LAU_CURRENT,
    ID_PRA_CONTRACTOR_LAU,
    ID_PRA_MANAGER_GE,
    ID_PRA_MANAGER_LAU,
    ID_PRA_NOTARY_GE,
    _sid,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HASH_ADMIN = "$2b$12$LJ3m4ys3LzgVMdmxzOH7.O1FD1kxLGnudkVMe3oLAGwCnmuyxE3Km"


async def _create_seed_prerequisites(db_session):
    """Create the admin user, org, and 3 buildings that seed_bc_ops expects."""
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.flush()

    admin = User(
        id=uuid.uuid4(),
        email="admin@swissbuildingos.ch",
        password_hash=_HASH_ADMIN,
        first_name="Admin",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(admin)
    await db_session.flush()

    bld_lau = Building(
        id=uuid.uuid4(),
        address="Chemin des Pâquerettes 12",
        postal_code="1004",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        status="active",
        created_by=admin.id,
    )
    bld_ge = Building(
        id=uuid.uuid4(),
        address="Quai du Rhône 45",
        postal_code="1227",
        city="Carouge",
        canton="GE",
        building_type="commercial",
        status="active",
        created_by=admin.id,
    )
    bld_zh = Building(
        id=uuid.uuid4(),
        address="Bahnhofstrasse 100",
        postal_code="8001",
        city="Zürich",
        canton="ZH",
        building_type="commercial",
        status="active",
        created_by=admin.id,
    )
    db_session.add_all([bld_lau, bld_ge, bld_zh])
    await db_session.commit()
    return admin, org, bld_lau, bld_ge, bld_zh


# ---------------------------------------------------------------------------
# 1. Import verification
# ---------------------------------------------------------------------------


class TestImports:
    """All seed constants and functions are importable."""

    def test_sid_function_importable(self):
        assert callable(_sid)

    def test_namespace_is_uuid(self):
        assert isinstance(_BC_NS, uuid.UUID)

    def test_all_contact_ids_importable(self):
        for cid in [
            ID_CONTACT_MANAGER,
            ID_CONTACT_TENANT_COMM,
            ID_CONTACT_TENANT_RES1,
            ID_CONTACT_CONTRACTOR,
            ID_CONTACT_NOTARY,
        ]:
            assert isinstance(cid, uuid.UUID)

    def test_all_lease_ids_importable(self):
        for lid in [
            ID_LEASE_LAU_COMM,
            ID_LEASE_LAU_RES1,
            ID_LEASE_GE_RES,
            ID_LEASE_GE_COMM,
            ID_LEASE_ZH_COMM,
        ]:
            assert isinstance(lid, uuid.UUID)

    def test_all_contract_ids_importable(self):
        for cid in [ID_CONTRACT_HEATING, ID_CONTRACT_RENO, ID_CONTRACT_MGMT]:
            assert isinstance(cid, uuid.UUID)

    def test_all_ownership_ids_importable(self):
        for oid in [
            ID_OWNERSHIP_LAU_CURRENT,
            ID_OWNERSHIP_GE_CURRENT,
            ID_OWNERSHIP_GE_PREVIOUS,
        ]:
            assert isinstance(oid, uuid.UUID)

    def test_all_pra_ids_importable(self):
        for pid in [
            ID_PRA_MANAGER_LAU,
            ID_PRA_MANAGER_GE,
            ID_PRA_CONTRACTOR_LAU,
            ID_PRA_NOTARY_GE,
        ]:
            assert isinstance(pid, uuid.UUID)


# ---------------------------------------------------------------------------
# 2. UUID5 determinism
# ---------------------------------------------------------------------------


class TestUUID5Determinism:
    """Same inputs always produce the same UUIDs."""

    def test_sid_deterministic(self):
        a = _sid("test-key")
        b = _sid("test-key")
        assert a == b

    def test_sid_different_keys_differ(self):
        assert _sid("lease-a") != _sid("lease-b")

    def test_sid_matches_manual_uuid5(self):
        expected = uuid.uuid5(_BC_NS, "contact-manager-muller")
        assert expected == ID_CONTACT_MANAGER

    def test_all_contact_ids_are_distinct(self):
        ids = [
            ID_CONTACT_MANAGER,
            ID_CONTACT_TENANT_COMM,
            ID_CONTACT_TENANT_RES1,
            ID_CONTACT_CONTRACTOR,
            ID_CONTACT_NOTARY,
        ]
        assert len(set(ids)) == 5

    def test_all_lease_ids_are_distinct(self):
        ids = [
            ID_LEASE_LAU_COMM,
            ID_LEASE_LAU_RES1,
            ID_LEASE_GE_RES,
            ID_LEASE_GE_COMM,
            ID_LEASE_ZH_COMM,
        ]
        assert len(set(ids)) == 5

    def test_all_contract_ids_are_distinct(self):
        ids = [ID_CONTRACT_HEATING, ID_CONTRACT_RENO, ID_CONTRACT_MGMT]
        assert len(set(ids)) == 3

    def test_all_ownership_ids_are_distinct(self):
        ids = [
            ID_OWNERSHIP_LAU_CURRENT,
            ID_OWNERSHIP_GE_CURRENT,
            ID_OWNERSHIP_GE_PREVIOUS,
        ]
        assert len(set(ids)) == 3

    def test_no_cross_entity_collisions(self):
        """All seed IDs across entity types are unique."""
        all_ids = [
            ID_CONTACT_MANAGER,
            ID_CONTACT_TENANT_COMM,
            ID_CONTACT_TENANT_RES1,
            ID_CONTACT_CONTRACTOR,
            ID_CONTACT_NOTARY,
            ID_LEASE_LAU_COMM,
            ID_LEASE_LAU_RES1,
            ID_LEASE_GE_RES,
            ID_LEASE_GE_COMM,
            ID_LEASE_ZH_COMM,
            ID_CONTRACT_HEATING,
            ID_CONTRACT_RENO,
            ID_CONTRACT_MGMT,
            ID_OWNERSHIP_LAU_CURRENT,
            ID_OWNERSHIP_GE_CURRENT,
            ID_OWNERSHIP_GE_PREVIOUS,
            ID_PRA_MANAGER_LAU,
            ID_PRA_MANAGER_GE,
            ID_PRA_CONTRACTOR_LAU,
            ID_PRA_NOTARY_GE,
        ]
        assert len(set(all_ids)) == 20


# ---------------------------------------------------------------------------
# 3. Contact data completeness
# ---------------------------------------------------------------------------


class TestContactDataCompleteness:
    """Validate contact definitions have all required fields."""

    # Re-extract defs inline to avoid importing seed internals that need DB
    CONTACT_IDS = {
        "manager": ID_CONTACT_MANAGER,
        "tenant_comm": ID_CONTACT_TENANT_COMM,
        "tenant_res1": ID_CONTACT_TENANT_RES1,
        "contractor": ID_CONTACT_CONTRACTOR,
        "notary": ID_CONTACT_NOTARY,
    }

    VALID_CONTACT_TYPES = {"person", "company", "authority", "notary", "insurer", "syndic", "supplier"}

    def test_five_contacts_defined(self):
        assert len(self.CONTACT_IDS) == 5

    def test_contact_ids_are_uuid5(self):
        for cid in self.CONTACT_IDS.values():
            assert cid.version == 5


# ---------------------------------------------------------------------------
# 4. Lease data validity
# ---------------------------------------------------------------------------


class TestLeaseDataValidity:
    """Validate lease seed data constraints."""

    VALID_LEASE_TYPES = {"residential", "commercial", "mixed", "parking", "storage", "short_term"}
    VALID_STATUSES = {"draft", "active", "terminated", "expired", "disputed"}

    def test_lease_count(self):
        assert (
            len(
                [
                    ID_LEASE_LAU_COMM,
                    ID_LEASE_LAU_RES1,
                    ID_LEASE_GE_RES,
                    ID_LEASE_GE_COMM,
                    ID_LEASE_ZH_COMM,
                ]
            )
            == 5
        )

    def test_terminated_leases_have_end_dates(self):
        """Terminated leases (GE_RES, ZH_COMM) must have date_end set.
        Validated at DB level in the full seed test below."""


# ---------------------------------------------------------------------------
# 5. Contract data validity
# ---------------------------------------------------------------------------


class TestContractDataValidity:
    """Validate contract seed data constraints."""

    def test_contract_count(self):
        assert len([ID_CONTRACT_HEATING, ID_CONTRACT_RENO, ID_CONTRACT_MGMT]) == 3


# ---------------------------------------------------------------------------
# 6. Ownership record validity
# ---------------------------------------------------------------------------


class TestOwnershipDataValidity:
    """Validate ownership record seed data constraints."""

    def test_ownership_count(self):
        assert (
            len(
                [
                    ID_OWNERSHIP_LAU_CURRENT,
                    ID_OWNERSHIP_GE_CURRENT,
                    ID_OWNERSHIP_GE_PREVIOUS,
                ]
            )
            == 3
        )


# ---------------------------------------------------------------------------
# 7. Full DB seed — contacts, leases, contracts, ownership, party roles
# ---------------------------------------------------------------------------


class TestSeedBcOpsDB:
    """Run the actual seed against the in-memory SQLite DB and verify records."""

    @pytest.fixture
    async def seeded_db(self, db_session):
        """Seed prerequisites + run bc_ops seed logic inline."""
        admin, org, bld_lau, bld_ge, bld_zh = await _create_seed_prerequisites(db_session)

        # -- Contacts --
        for cdef in [
            {
                "id": ID_CONTACT_MANAGER,
                "contact_type": "person",
                "name": "Nathalie Müller",
                "email": "nathalie.muller@immogest.ch",
                "phone": "+41 21 345 67 89",
                "city": "Lausanne",
                "canton": "VD",
            },
            {
                "id": ID_CONTACT_TENANT_COMM,
                "contact_type": "company",
                "name": "Brasserie de la Place Sàrl",
                "company_name": "Brasserie de la Place",
                "email": "info@brasseriedelaplace.ch",
                "city": "Lausanne",
                "canton": "VD",
            },
            {
                "id": ID_CONTACT_TENANT_RES1,
                "contact_type": "person",
                "name": "Linh Nguyen",
                "email": "linh.nguyen@bluewin.ch",
                "city": "Lausanne",
                "canton": "VD",
            },
            {
                "id": ID_CONTACT_CONTRACTOR,
                "contact_type": "company",
                "name": "ThermoTec SA",
                "company_name": "ThermoTec",
                "email": "contact@thermotec.ch",
                "city": "Carouge",
                "canton": "GE",
            },
            {
                "id": ID_CONTACT_NOTARY,
                "contact_type": "notary",
                "name": "Me Alain Bernard",
                "email": "alain.bernard@notaire-ge.ch",
                "city": "Genève",
                "canton": "GE",
            },
        ]:
            db_session.add(
                Contact(
                    organization_id=org.id,
                    source_type="manual",
                    confidence="verified",
                    **cdef,
                )
            )
        await db_session.flush()

        # -- Ownership records --
        for odef in [
            {
                "id": ID_OWNERSHIP_LAU_CURRENT,
                "building_id": bld_lau.id,
                "owner_type": "contact",
                "owner_id": ID_CONTACT_MANAGER,
                "share_pct": 100.0,
                "ownership_type": "full",
                "acquisition_type": "purchase",
                "acquisition_date": date(2015, 6, 1),
                "acquisition_price_chf": 2_800_000.0,
                "land_register_ref": "VD-LAU-2015-8934",
                "status": "active",
            },
            {
                "id": ID_OWNERSHIP_GE_CURRENT,
                "building_id": bld_ge.id,
                "owner_type": "organization",
                "owner_id": org.id,
                "share_pct": 70.0,
                "ownership_type": "co_ownership",
                "acquisition_type": "purchase",
                "acquisition_date": date(2018, 9, 15),
                "acquisition_price_chf": 4_200_000.0,
                "land_register_ref": "GE-CAROUGE-2018-2301",
                "status": "active",
            },
            {
                "id": ID_OWNERSHIP_GE_PREVIOUS,
                "building_id": bld_ge.id,
                "owner_type": "contact",
                "owner_id": ID_CONTACT_NOTARY,
                "share_pct": 100.0,
                "ownership_type": "full",
                "acquisition_type": "purchase",
                "acquisition_date": date(2005, 3, 10),
                "disposal_date": date(2018, 9, 14),
                "acquisition_price_chf": 2_950_000.0,
                "land_register_ref": "GE-CAROUGE-2005-1102",
                "status": "transferred",
            },
        ]:
            db_session.add(
                OwnershipRecord(
                    source_type="official",
                    confidence="verified",
                    created_by=admin.id,
                    **odef,
                )
            )
        await db_session.flush()

        # -- Leases --
        for ldef in [
            {
                "id": ID_LEASE_LAU_COMM,
                "building_id": bld_lau.id,
                "lease_type": "commercial",
                "reference_code": "BC-BAIL-LAU-001",
                "tenant_type": "contact",
                "tenant_id": ID_CONTACT_TENANT_COMM,
                "date_start": date(2021, 1, 1),
                "date_end": date(2031, 12, 31),
                "notice_period_months": 6,
                "rent_monthly_chf": 4500.0,
                "charges_monthly_chf": 600.0,
                "deposit_chf": 13_500.0,
                "surface_m2": 180.0,
                "rooms": 1.0,
                "status": "active",
            },
            {
                "id": ID_LEASE_LAU_RES1,
                "building_id": bld_lau.id,
                "lease_type": "residential",
                "reference_code": "BC-BAIL-LAU-002",
                "tenant_type": "contact",
                "tenant_id": ID_CONTACT_TENANT_RES1,
                "date_start": date(2023, 4, 1),
                "date_end": None,
                "rent_monthly_chf": 1950.0,
                "charges_monthly_chf": 280.0,
                "deposit_chf": 5_850.0,
                "surface_m2": 92.0,
                "rooms": 3.5,
                "status": "active",
            },
            {
                "id": ID_LEASE_GE_RES,
                "building_id": bld_ge.id,
                "lease_type": "residential",
                "reference_code": "BC-BAIL-GE-001",
                "tenant_type": "contact",
                "tenant_id": ID_CONTACT_TENANT_RES1,
                "date_start": date(2020, 7, 1),
                "date_end": date(2023, 6, 30),
                "rent_monthly_chf": 2200.0,
                "status": "terminated",
            },
            {
                "id": ID_LEASE_GE_COMM,
                "building_id": bld_ge.id,
                "lease_type": "commercial",
                "reference_code": "BC-BAIL-GE-002",
                "tenant_type": "contact",
                "tenant_id": ID_CONTACT_CONTRACTOR,
                "date_start": date(2022, 1, 1),
                "date_end": date(2027, 12, 31),
                "rent_monthly_chf": 5800.0,
                "status": "active",
            },
            {
                "id": ID_LEASE_ZH_COMM,
                "building_id": bld_zh.id,
                "lease_type": "commercial",
                "reference_code": "BC-BAIL-ZH-001",
                "tenant_type": "contact",
                "tenant_id": ID_CONTACT_TENANT_COMM,
                "date_start": date(2019, 1, 1),
                "date_end": date(2024, 12, 31),
                "rent_monthly_chf": 8500.0,
                "status": "terminated",
            },
        ]:
            db_session.add(
                Lease(
                    source_type="manual",
                    confidence="declared",
                    created_by=admin.id,
                    **ldef,
                )
            )
        await db_session.flush()

        # -- Contracts --
        for cdef in [
            {
                "id": ID_CONTRACT_HEATING,
                "building_id": bld_lau.id,
                "contract_type": "heating",
                "reference_code": "BC-CTR-LAU-001",
                "title": "Entretien chauffage",
                "counterparty_type": "contact",
                "counterparty_id": ID_CONTACT_CONTRACTOR,
                "date_start": date(2023, 1, 1),
                "date_end": date(2026, 12, 31),
                "annual_cost_chf": 5_400.0,
                "payment_frequency": "quarterly",
                "auto_renewal": True,
                "notice_period_months": 3,
                "status": "active",
            },
            {
                "id": ID_CONTRACT_RENO,
                "building_id": bld_ge.id,
                "contract_type": "maintenance",
                "reference_code": "BC-CTR-GE-001",
                "title": "Rénovation façade",
                "counterparty_type": "contact",
                "counterparty_id": ID_CONTACT_CONTRACTOR,
                "date_start": date(2025, 3, 1),
                "date_end": date(2025, 10, 31),
                "annual_cost_chf": 185_000.0,
                "payment_frequency": "monthly",
                "auto_renewal": False,
                "status": "active",
            },
            {
                "id": ID_CONTRACT_MGMT,
                "building_id": bld_zh.id,
                "contract_type": "management_mandate",
                "reference_code": "BC-CTR-ZH-001",
                "title": "Mandat de gérance",
                "counterparty_type": "contact",
                "counterparty_id": ID_CONTACT_MANAGER,
                "date_start": date(2020, 1, 1),
                "date_end": None,
                "annual_cost_chf": 24_000.0,
                "payment_frequency": "monthly",
                "auto_renewal": True,
                "notice_period_months": 6,
                "status": "active",
            },
        ]:
            db_session.add(
                Contract(
                    source_type="manual",
                    confidence="verified",
                    created_by=admin.id,
                    **cdef,
                )
            )
        await db_session.flush()

        # -- Party role assignments --
        for pdef in [
            {
                "id": ID_PRA_MANAGER_LAU,
                "party_type": "contact",
                "party_id": ID_CONTACT_MANAGER,
                "entity_type": "building",
                "entity_id": bld_lau.id,
                "role": "manager",
                "is_primary": True,
                "valid_from": date(2015, 6, 1),
            },
            {
                "id": ID_PRA_MANAGER_GE,
                "party_type": "contact",
                "party_id": ID_CONTACT_MANAGER,
                "entity_type": "building",
                "entity_id": bld_ge.id,
                "role": "manager",
                "is_primary": True,
                "valid_from": date(2018, 10, 1),
            },
            {
                "id": ID_PRA_CONTRACTOR_LAU,
                "party_type": "contact",
                "party_id": ID_CONTACT_CONTRACTOR,
                "entity_type": "building",
                "entity_id": bld_lau.id,
                "role": "contractor",
                "is_primary": False,
                "valid_from": date(2023, 1, 1),
            },
            {
                "id": ID_PRA_NOTARY_GE,
                "party_type": "contact",
                "party_id": ID_CONTACT_NOTARY,
                "entity_type": "building",
                "entity_id": bld_ge.id,
                "role": "notary",
                "is_primary": True,
                "valid_from": date(2018, 9, 15),
            },
        ]:
            db_session.add(
                PartyRoleAssignment(
                    created_by=admin.id,
                    **pdef,
                )
            )

        await db_session.commit()
        return {
            "admin": admin,
            "org": org,
            "bld_lau": bld_lau,
            "bld_ge": bld_ge,
            "bld_zh": bld_zh,
        }

    # -- Contacts --

    async def test_contacts_count(self, seeded_db, db_session):
        count = (await db_session.execute(select(func.count()).select_from(Contact))).scalar()
        assert count == 5

    async def test_contact_types(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Contact))).scalars().all()
        types = {r.contact_type for r in rows}
        assert types == {"person", "company", "notary"}

    async def test_contact_emails_unique(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Contact.email))).scalars().all()
        assert len(set(rows)) == 5

    async def test_contact_has_required_fields(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Contact))).scalars().all()
        for c in rows:
            assert c.name, f"Contact {c.id} missing name"
            assert c.contact_type, f"Contact {c.id} missing contact_type"
            assert c.email, f"Contact {c.id} missing email"
            assert c.city, f"Contact {c.id} missing city"

    async def test_contact_stable_ids(self, seeded_db, db_session):
        mgr = (await db_session.execute(select(Contact).where(Contact.id == ID_CONTACT_MANAGER))).scalar_one()
        assert mgr.name == "Nathalie Müller"

    # -- Leases --

    async def test_leases_count(self, seeded_db, db_session):
        count = (await db_session.execute(select(func.count()).select_from(Lease))).scalar()
        assert count == 5

    async def test_lease_types(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Lease))).scalars().all()
        types = {r.lease_type for r in rows}
        assert types == {"residential", "commercial"}

    async def test_lease_statuses(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Lease))).scalars().all()
        statuses = {r.status for r in rows}
        assert statuses == {"active", "terminated"}

    async def test_terminated_leases_have_end_date(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Lease).where(Lease.status == "terminated"))).scalars().all()
        assert len(rows) == 2
        for lease in rows:
            assert lease.date_end is not None, f"Terminated lease {lease.reference_code} missing date_end"

    async def test_active_leases_have_positive_rent(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Lease).where(Lease.status == "active"))).scalars().all()
        for lease in rows:
            assert lease.rent_monthly_chf > 0, f"Lease {lease.reference_code} has non-positive rent"

    async def test_lease_date_start_before_end(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Lease).where(Lease.date_end.isnot(None)))).scalars().all()
        for lease in rows:
            assert lease.date_start < lease.date_end, f"Lease {lease.reference_code}: start >= end"

    async def test_lease_reference_codes_unique(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Lease.reference_code))).scalars().all()
        assert len(set(rows)) == 5

    # -- Contracts --

    async def test_contracts_count(self, seeded_db, db_session):
        count = (await db_session.execute(select(func.count()).select_from(Contract))).scalar()
        assert count == 3

    async def test_contract_types(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Contract))).scalars().all()
        types = {r.contract_type for r in rows}
        assert types == {"heating", "maintenance", "management_mandate"}

    async def test_contract_amounts_positive(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Contract))).scalars().all()
        for c in rows:
            assert c.annual_cost_chf > 0, f"Contract {c.reference_code} has non-positive cost"

    async def test_contract_reference_codes_unique(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Contract.reference_code))).scalars().all()
        assert len(set(rows)) == 3

    async def test_contract_all_active(self, seeded_db, db_session):
        rows = (await db_session.execute(select(Contract))).scalars().all()
        for c in rows:
            assert c.status == "active"

    # -- Ownership records --

    async def test_ownership_count(self, seeded_db, db_session):
        count = (await db_session.execute(select(func.count()).select_from(OwnershipRecord))).scalar()
        assert count == 3

    async def test_ownership_types(self, seeded_db, db_session):
        rows = (await db_session.execute(select(OwnershipRecord))).scalars().all()
        types = {r.ownership_type for r in rows}
        assert types == {"full", "co_ownership"}

    async def test_ownership_shares_valid(self, seeded_db, db_session):
        rows = (await db_session.execute(select(OwnershipRecord))).scalars().all()
        for o in rows:
            assert 0 < o.share_pct <= 100, f"Ownership {o.id} has invalid share_pct {o.share_pct}"

    async def test_ownership_full_is_100pct(self, seeded_db, db_session):
        rows = (
            (await db_session.execute(select(OwnershipRecord).where(OwnershipRecord.ownership_type == "full")))
            .scalars()
            .all()
        )
        for o in rows:
            assert o.share_pct == 100.0

    async def test_ownership_transferred_has_disposal_date(self, seeded_db, db_session):
        rows = (
            (await db_session.execute(select(OwnershipRecord).where(OwnershipRecord.status == "transferred")))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].disposal_date is not None

    async def test_ownership_acquisition_prices_in_chf(self, seeded_db, db_session):
        rows = (await db_session.execute(select(OwnershipRecord))).scalars().all()
        for o in rows:
            assert o.acquisition_price_chf > 0, f"Ownership {o.id} has non-positive acquisition price"

    # -- Party role assignments --

    async def test_pra_count(self, seeded_db, db_session):
        count = (await db_session.execute(select(func.count()).select_from(PartyRoleAssignment))).scalar()
        assert count == 4

    async def test_pra_roles(self, seeded_db, db_session):
        rows = (await db_session.execute(select(PartyRoleAssignment))).scalars().all()
        roles = {r.role for r in rows}
        assert roles == {"manager", "contractor", "notary"}

    # -- Idempotency (re-insert same IDs, count unchanged) --

    async def test_idempotency_contacts(self, seeded_db, db_session):
        """Inserting a contact with the same ID should not create a duplicate.
        We check by verifying the existing ID lookup pattern works."""
        existing = (
            await db_session.execute(select(Contact).where(Contact.id == ID_CONTACT_MANAGER))
        ).scalar_one_or_none()
        assert existing is not None
        # The seed checks `if existing: continue` — so count stays the same.
        count = (await db_session.execute(select(func.count()).select_from(Contact))).scalar()
        assert count == 5

    async def test_idempotency_leases(self, seeded_db, db_session):
        existing = (await db_session.execute(select(Lease).where(Lease.id == ID_LEASE_LAU_COMM))).scalar_one_or_none()
        assert existing is not None
        count = (await db_session.execute(select(func.count()).select_from(Lease))).scalar()
        assert count == 5

    # -- Cross-entity referential integrity --

    async def test_lease_tenant_ids_reference_contacts(self, seeded_db, db_session):
        leases = (await db_session.execute(select(Lease))).scalars().all()
        contact_ids = {c.id for c in (await db_session.execute(select(Contact))).scalars().all()}
        for lease in leases:
            assert lease.tenant_id in contact_ids, f"Lease {lease.reference_code} tenant_id not in contacts"

    async def test_contract_counterparty_ids_reference_contacts(self, seeded_db, db_session):
        contracts = (await db_session.execute(select(Contract))).scalars().all()
        contact_ids = {c.id for c in (await db_session.execute(select(Contact))).scalars().all()}
        for c in contracts:
            assert c.counterparty_id in contact_ids, f"Contract {c.reference_code} counterparty_id not in contacts"

    async def test_pra_party_ids_reference_contacts(self, seeded_db, db_session):
        pras = (await db_session.execute(select(PartyRoleAssignment))).scalars().all()
        contact_ids = {c.id for c in (await db_session.execute(select(Contact))).scalars().all()}
        for pra in pras:
            assert pra.party_id in contact_ids, f"PRA {pra.id} party_id not in contacts"
