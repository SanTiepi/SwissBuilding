"""BatiConnect — BC enrichment seed for existing seed_data buildings.

Run: python -m app.seeds.seed_bc_ops

Adds to existing seed_data buildings:
- 5 contacts (property managers, tenants, contractors, notary)
- 4 party role assignments
- 5 leases (mixed types/statuses) across 3 buildings
- 3 contracts (maintenance, renovation, management)
- 3 ownership records (current + historical)
- 6 lease events (creation, renewal, termination, rent adjustment)

Idempotent: uses email-based contact lookup and reference_code uniqueness.
All monetary values in CHF.
"""

import asyncio
import uuid
from datetime import date

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.building import Building
from app.models.contact import Contact
from app.models.contract import Contract
from app.models.lease import Lease, LeaseEvent
from app.models.ownership_record import OwnershipRecord
from app.models.party_role_assignment import PartyRoleAssignment
from app.models.user import User

# Stable namespace for idempotent IDs
_BC_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def _sid(name: str) -> uuid.UUID:
    """Stable UUID5 from a seed-internal name."""
    return uuid.uuid5(_BC_NS, name)


# Pre-computed stable IDs
ID_CONTACT_MANAGER = _sid("contact-manager-muller")
ID_CONTACT_TENANT_COMM = _sid("contact-tenant-brasserie")
ID_CONTACT_TENANT_RES1 = _sid("contact-tenant-nguyen")
ID_CONTACT_CONTRACTOR = _sid("contact-contractor-thermotec")
ID_CONTACT_NOTARY = _sid("contact-notary-bernard")

ID_LEASE_LAU_COMM = _sid("lease-lau-commercial")
ID_LEASE_LAU_RES1 = _sid("lease-lau-residential-1")
ID_LEASE_GE_RES = _sid("lease-ge-residential")
ID_LEASE_GE_COMM = _sid("lease-ge-commercial")
ID_LEASE_ZH_COMM = _sid("lease-zh-commercial-terminated")

ID_CONTRACT_HEATING = _sid("contract-lau-heating")
ID_CONTRACT_RENO = _sid("contract-ge-renovation")
ID_CONTRACT_MGMT = _sid("contract-zh-management")

ID_OWNERSHIP_LAU_CURRENT = _sid("ownership-lau-current")
ID_OWNERSHIP_GE_CURRENT = _sid("ownership-ge-current")
ID_OWNERSHIP_GE_PREVIOUS = _sid("ownership-ge-previous")

ID_PRA_MANAGER_LAU = _sid("pra-manager-lau")
ID_PRA_MANAGER_GE = _sid("pra-manager-ge")
ID_PRA_CONTRACTOR_LAU = _sid("pra-contractor-lau")
ID_PRA_NOTARY_GE = _sid("pra-notary-ge")


async def seed():
    async with AsyncSessionLocal() as db:
        # ── Lookup existing admin + buildings ──────────────────────────
        result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
        admin = result.scalar_one_or_none()
        if not admin:
            print("BC Ops seed: admin user not found — run seed_data first.")
            return

        org_id = admin.organization_id

        # Lookup 3 buildings by address (from seed_data)
        bld_lau = (
            await db.execute(select(Building).where(Building.address == "Chemin des Pâquerettes 12"))
        ).scalar_one_or_none()

        bld_ge = (await db.execute(select(Building).where(Building.address == "Quai du Rhône 45"))).scalar_one_or_none()

        bld_zh = (
            await db.execute(select(Building).where(Building.address == "Bahnhofstrasse 100"))
        ).scalar_one_or_none()

        if not all([bld_lau, bld_ge, bld_zh]):
            print("BC Ops seed: some buildings not found — run seed_data first.")
            return

        # ── 1. Contacts (upsert by stable ID) ─────────────────────────
        contact_defs = [
            {
                "id": ID_CONTACT_MANAGER,
                "contact_type": "person",
                "name": "Nathalie Müller",
                "email": "nathalie.muller@immogest.ch",
                "phone": "+41 21 345 67 89",
                "address": "Rue du Grand-Pont 5",
                "postal_code": "1003",
                "city": "Lausanne",
                "canton": "VD",
            },
            {
                "id": ID_CONTACT_TENANT_COMM,
                "contact_type": "company",
                "name": "Brasserie de la Place Sàrl",
                "company_name": "Brasserie de la Place",
                "email": "info@brasseriedelaplace.ch",
                "phone": "+41 21 312 45 67",
                "address": "Chemin des Pâquerettes 12",
                "postal_code": "1004",
                "city": "Lausanne",
                "canton": "VD",
            },
            {
                "id": ID_CONTACT_TENANT_RES1,
                "contact_type": "person",
                "name": "Linh Nguyen",
                "email": "linh.nguyen@bluewin.ch",
                "phone": "+41 78 234 56 78",
                "city": "Lausanne",
                "canton": "VD",
            },
            {
                "id": ID_CONTACT_CONTRACTOR,
                "contact_type": "company",
                "name": "ThermoTec SA",
                "company_name": "ThermoTec",
                "email": "contact@thermotec.ch",
                "phone": "+41 22 789 01 23",
                "address": "Zone Industrielle 14",
                "postal_code": "1227",
                "city": "Carouge",
                "canton": "GE",
            },
            {
                "id": ID_CONTACT_NOTARY,
                "contact_type": "notary",
                "name": "Me Alain Bernard",
                "email": "alain.bernard@notaire-ge.ch",
                "phone": "+41 22 310 55 00",
                "address": "Boulevard Helvétique 30",
                "postal_code": "1207",
                "city": "Genève",
                "canton": "GE",
            },
        ]

        contacts_by_id = {}
        for cdef in contact_defs:
            cid = cdef["id"]
            existing = (await db.execute(select(Contact).where(Contact.id == cid))).scalar_one_or_none()
            if existing:
                contacts_by_id[cid] = existing
                continue
            c = Contact(
                organization_id=org_id,
                source_type="manual",
                confidence="verified",
                **cdef,
            )
            db.add(c)
            contacts_by_id[cid] = c
        await db.flush()

        # ── 2. Ownership Records (upsert by stable ID) ────────────────
        ownership_defs = [
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
                "owner_id": admin.organization_id,
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
        ]

        for odef in ownership_defs:
            oid = odef["id"]
            existing = (await db.execute(select(OwnershipRecord).where(OwnershipRecord.id == oid))).scalar_one_or_none()
            if existing:
                continue
            db.add(
                OwnershipRecord(
                    source_type="official",
                    confidence="verified",
                    created_by=admin.id,
                    **odef,
                )
            )
        await db.flush()

        # ── 3. Leases (upsert by stable ID) ───────────────────────────
        lease_defs = [
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
                "notes": "Bail commercial 10 ans — brasserie RDC",
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
                "notice_period_months": 3,
                "rent_monthly_chf": 1950.0,
                "charges_monthly_chf": 280.0,
                "deposit_chf": 5_850.0,
                "surface_m2": 92.0,
                "rooms": 3.5,
                "status": "active",
                "notes": "3.5 pièces au 3e étage",
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
                "notice_period_months": 3,
                "rent_monthly_chf": 2200.0,
                "charges_monthly_chf": 350.0,
                "deposit_chf": 6_600.0,
                "surface_m2": 110.0,
                "rooms": 4.5,
                "status": "terminated",
                "notes": "Résiliation par le locataire — déménagement VD",
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
                "notice_period_months": 6,
                "rent_monthly_chf": 5800.0,
                "charges_monthly_chf": 800.0,
                "deposit_chf": 17_400.0,
                "surface_m2": 250.0,
                "rooms": 1.0,
                "status": "active",
                "notes": "Bureaux ThermoTec — 1er et 2e étage",
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
                "notice_period_months": 6,
                "rent_monthly_chf": 8500.0,
                "charges_monthly_chf": 1200.0,
                "deposit_chf": 25_500.0,
                "surface_m2": 320.0,
                "rooms": 1.0,
                "status": "terminated",
                "notes": "Ancien bail Bahnhofstrasse — non renouvelé",
            },
        ]

        leases_by_id = {}
        for ldef in lease_defs:
            lid = ldef["id"]
            existing = (await db.execute(select(Lease).where(Lease.id == lid))).scalar_one_or_none()
            if existing:
                leases_by_id[lid] = existing
                continue
            lease = Lease(
                source_type="manual",
                confidence="declared",
                created_by=admin.id,
                **ldef,
            )
            db.add(lease)
            leases_by_id[lid] = lease
        await db.flush()

        # ── 4. Lease Events ───────────────────────────────────────────
        lease_event_defs = [
            {
                "id": _sid("le-lau-comm-creation"),
                "lease_id": ID_LEASE_LAU_COMM,
                "event_type": "creation",
                "event_date": date(2021, 1, 1),
                "description": "Signature du bail commercial — Brasserie de la Place",
            },
            {
                "id": _sid("le-lau-res1-creation"),
                "lease_id": ID_LEASE_LAU_RES1,
                "event_type": "creation",
                "event_date": date(2023, 4, 1),
                "description": "Entrée du locataire Nguyen — 3.5 pièces",
            },
            {
                "id": _sid("le-lau-comm-rent-adj"),
                "lease_id": ID_LEASE_LAU_COMM,
                "event_type": "rent_adjustment",
                "event_date": date(2024, 1, 1),
                "description": "Ajustement loyer selon indice ISPC (+2.1%)",
                "old_value_json": {"rent_monthly_chf": 4400.0},
                "new_value_json": {"rent_monthly_chf": 4500.0},
            },
            {
                "id": _sid("le-ge-res-creation"),
                "lease_id": ID_LEASE_GE_RES,
                "event_type": "creation",
                "event_date": date(2020, 7, 1),
                "description": "Signature bail résidentiel — 4.5 pièces",
            },
            {
                "id": _sid("le-ge-res-termination"),
                "lease_id": ID_LEASE_GE_RES,
                "event_type": "termination",
                "event_date": date(2023, 3, 31),
                "description": "Résiliation par locataire — préavis 3 mois",
            },
            {
                "id": _sid("le-zh-comm-termination"),
                "lease_id": ID_LEASE_ZH_COMM,
                "event_type": "termination",
                "event_date": date(2024, 6, 30),
                "description": "Fin de bail — non renouvellement mutuel",
            },
        ]

        for edef in lease_event_defs:
            eid = edef["id"]
            existing = (await db.execute(select(LeaseEvent).where(LeaseEvent.id == eid))).scalar_one_or_none()
            if existing:
                continue
            db.add(
                LeaseEvent(
                    created_by=admin.id,
                    **edef,
                )
            )
        await db.flush()

        # ── 5. Contracts (upsert by stable ID) ────────────────────────
        contract_defs = [
            {
                "id": ID_CONTRACT_HEATING,
                "building_id": bld_lau.id,
                "contract_type": "heating",
                "reference_code": "BC-CTR-LAU-001",
                "title": "Entretien chauffage à distance — Lausanne Énergie",
                "counterparty_type": "contact",
                "counterparty_id": ID_CONTACT_CONTRACTOR,
                "date_start": date(2023, 1, 1),
                "date_end": date(2026, 12, 31),
                "annual_cost_chf": 5_400.0,
                "payment_frequency": "quarterly",
                "auto_renewal": True,
                "notice_period_months": 3,
                "status": "active",
                "notes": "Contrat incluant 2 visites/an + dépannage 24h",
            },
            {
                "id": ID_CONTRACT_RENO,
                "building_id": bld_ge.id,
                "contract_type": "maintenance",
                "reference_code": "BC-CTR-GE-001",
                "title": "Rénovation façade et isolation — Phase 1",
                "counterparty_type": "contact",
                "counterparty_id": ID_CONTACT_CONTRACTOR,
                "date_start": date(2025, 3, 1),
                "date_end": date(2025, 10, 31),
                "annual_cost_chf": 185_000.0,
                "payment_frequency": "monthly",
                "auto_renewal": False,
                "notice_period_months": None,
                "status": "active",
                "notes": "Devis accepté 185k CHF — travaux mars-octobre 2025",
            },
            {
                "id": ID_CONTRACT_MGMT,
                "building_id": bld_zh.id,
                "contract_type": "management_mandate",
                "reference_code": "BC-CTR-ZH-001",
                "title": "Mandat de gérance — Régie Romande Immobilier",
                "counterparty_type": "contact",
                "counterparty_id": ID_CONTACT_MANAGER,
                "date_start": date(2020, 1, 1),
                "date_end": None,
                "annual_cost_chf": 24_000.0,
                "payment_frequency": "monthly",
                "auto_renewal": True,
                "notice_period_months": 6,
                "status": "active",
                "notes": "Mandat de gérance complet — 2% du rendement brut",
            },
        ]

        for cdef in contract_defs:
            cid = cdef["id"]
            existing = (await db.execute(select(Contract).where(Contract.id == cid))).scalar_one_or_none()
            if existing:
                continue
            db.add(
                Contract(
                    source_type="manual",
                    confidence="verified",
                    created_by=admin.id,
                    **cdef,
                )
            )
        await db.flush()

        # ── 6. Party Role Assignments (upsert by stable ID) ───────────
        pra_defs = [
            {
                "id": ID_PRA_MANAGER_LAU,
                "party_type": "contact",
                "party_id": ID_CONTACT_MANAGER,
                "entity_type": "building",
                "entity_id": bld_lau.id,
                "role": "manager",
                "is_primary": True,
                "valid_from": date(2015, 6, 1),
                "notes": "Gérante principale — propriétaire",
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
                "notes": "Mandat de gérance Genève",
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
                "notes": "Prestataire chauffage",
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
                "notes": "Notaire acte de vente 2018",
            },
        ]

        for pdef in pra_defs:
            pid = pdef["id"]
            existing = (
                await db.execute(select(PartyRoleAssignment).where(PartyRoleAssignment.id == pid))
            ).scalar_one_or_none()
            if existing:
                continue
            db.add(
                PartyRoleAssignment(
                    created_by=admin.id,
                    **pdef,
                )
            )

        await db.commit()

        print("BC Ops seed complete:")
        print(f"  Lausanne: {bld_lau.address} ({bld_lau.id})")
        print(f"  Genève:   {bld_ge.address} ({bld_ge.id})")
        print(f"  Zürich:   {bld_zh.address} ({bld_zh.id})")
        print("  Contacts: 5, Ownership: 3, Leases: 5, Events: 6")
        print("  Contracts: 3, PartyRoles: 4")


if __name__ == "__main__":
    asyncio.run(seed())
