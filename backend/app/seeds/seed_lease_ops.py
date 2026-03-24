"""BatiConnect — Lease Ops demonstrator seed.

Run: python -m app.seeds.seed_lease_ops

Creates a complete scenario on a dedicated building with:
- 2 owners (via Contact + OwnershipRecord)
- 5 leases (mixed types and statuses)
- 5 units + zones
- 3 contracts
- 1 insurance policy
- financial entries
- documents + DocumentLinks
"""

import asyncio
import uuid
from datetime import date

from app.database import AsyncSessionLocal
from app.models.building import Building
from app.models.contact import Contact
from app.models.contract import Contract
from app.models.document import Document
from app.models.document_link import DocumentLink
from app.models.financial_entry import FinancialEntry
from app.models.insurance_policy import InsurancePolicy
from app.models.lease import Lease
from app.models.organization import Organization
from app.models.ownership_record import OwnershipRecord
from app.models.unit import Unit
from app.models.user import User
from app.models.zone import Zone


async def seed():
    async with AsyncSessionLocal() as db:
        # 1. Find or create admin user + org
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
        admin = result.scalar_one_or_none()

        if not admin:
            org = Organization(id=uuid.uuid4(), name="Demo Regie", type="property_management")
            db.add(org)
            await db.flush()
            admin = User(
                id=uuid.uuid4(),
                email="admin@swissbuildingos.ch",
                password_hash="$2b$12$LJ3m4ys3Lf0WPmMnfQVPteUIXQYyXqkJlgmqz3N3F2j7G3qW0R.MS",
                first_name="Admin",
                last_name="Demo",
                role="admin",
                organization_id=org.id,
            )
            db.add(admin)
            await db.flush()

        org_id = admin.organization_id

        # 2. Building
        building = Building(
            id=uuid.uuid4(),
            address="Avenue de la Gare 12",
            postal_code="1003",
            city="Lausanne",
            canton="VD",
            building_type="residential_mixed",
            construction_year=1965,
            floors_above=6,
            floors_below=1,
            surface_area_m2=1200.0,
            created_by=admin.id,
            organization_id=org_id,
        )
        db.add(building)
        await db.flush()

        # 3. Zones (floors)
        zones = []
        for floor_num in range(0, 6):
            z = Zone(
                id=uuid.uuid4(),
                building_id=building.id,
                zone_type="floor",
                name=f"{floor_num}e etage" if floor_num > 0 else "Rez-de-chaussee",
                floor_number=floor_num,
            )
            db.add(z)
            zones.append(z)
        await db.flush()

        # 4. Units
        units = []
        for _i, (utype, ref, floor, m2, rooms) in enumerate(
            [
                ("commercial", "COM-RDC", 0, 120.0, 1.0),
                ("residential", "APT-201", 2, 85.5, 3.5),
                ("residential", "APT-301", 3, 85.5, 3.5),
                ("residential", "APT-401", 4, 65.0, 2.5),
                ("parking", "P-01", -1, 15.0, None),
            ]
        ):
            u = Unit(
                id=uuid.uuid4(),
                building_id=building.id,
                unit_type=utype,
                reference_code=ref,
                name=ref,
                floor=floor,
                surface_m2=m2,
                rooms=rooms,
                status="active",
            )
            db.add(u)
            units.append(u)
        await db.flush()

        # 5. Contacts (owners + tenants)
        owner1 = Contact(
            id=uuid.uuid4(),
            organization_id=org_id,
            contact_type="person",
            name="Pierre Favre",
            email="pierre.favre@example.ch",
            city="Lausanne",
            canton="VD",
            source_type="manual",
            confidence="verified",
        )
        owner2 = Contact(
            id=uuid.uuid4(),
            organization_id=org_id,
            contact_type="company",
            name="Immofonds SA",
            company_name="Immofonds",
            email="info@immofonds.ch",
            city="Geneve",
            canton="GE",
            source_type="manual",
            confidence="verified",
        )
        tenants = []
        for name, email in [
            ("Cafe du Lac Sarl", "contact@cafedulac.ch"),
            ("Marie Rochat", "marie.rochat@email.ch"),
            ("Jean-Luc Bonvin", "jl.bonvin@email.ch"),
            ("Elena Petrova", "elena.p@email.ch"),
            ("Garage Favre", "garage@favre.ch"),
        ]:
            t = Contact(
                id=uuid.uuid4(),
                organization_id=org_id,
                contact_type="company" if "Sarl" in name or "Garage" in name else "person",
                name=name,
                email=email,
                source_type="manual",
                confidence="declared",
            )
            db.add(t)
            tenants.append(t)
        db.add_all([owner1, owner2])
        await db.flush()

        # 6. Ownership records (co-ownership 60/40)
        db.add(
            OwnershipRecord(
                id=uuid.uuid4(),
                building_id=building.id,
                owner_type="contact",
                owner_id=owner1.id,
                share_pct=60.0,
                ownership_type="co_ownership",
                acquisition_type="purchase",
                acquisition_date=date(2010, 3, 15),
                acquisition_price_chf=720000.0,
                land_register_ref="VD-LAU-2010-4521",
                status="active",
                source_type="official",
                confidence="verified",
            )
        )
        db.add(
            OwnershipRecord(
                id=uuid.uuid4(),
                building_id=building.id,
                owner_type="contact",
                owner_id=owner2.id,
                share_pct=40.0,
                ownership_type="co_ownership",
                acquisition_type="purchase",
                acquisition_date=date(2010, 3, 15),
                acquisition_price_chf=480000.0,
                land_register_ref="VD-LAU-2010-4522",
                status="active",
                source_type="official",
                confidence="verified",
            )
        )

        # 7. Leases (5 — mixed types and statuses)
        lease_data = [
            (
                "BAIL-001",
                "commercial",
                tenants[0],
                units[0],
                "active",
                date(2020, 1, 1),
                date(2030, 12, 31),
                3200.0,
                450.0,
                9600.0,
            ),
            (
                "BAIL-002",
                "residential",
                tenants[1],
                units[1],
                "active",
                date(2022, 4, 1),
                date(2025, 3, 31),
                1850.0,
                250.0,
                5550.0,
            ),
            (
                "BAIL-003",
                "residential",
                tenants[2],
                units[2],
                "active",
                date(2023, 7, 1),
                None,
                1800.0,
                250.0,
                5400.0,
            ),
            (
                "BAIL-004",
                "residential",
                tenants[3],
                units[3],
                "terminated",
                date(2019, 1, 1),
                date(2024, 12, 31),
                1450.0,
                200.0,
                4350.0,
            ),
            (
                "BAIL-005",
                "parking",
                tenants[4],
                units[4],
                "active",
                date(2023, 1, 1),
                date(2025, 12, 31),
                180.0,
                0.0,
                540.0,
            ),
        ]
        leases = []
        for ref, ltype, tenant, unit, st, start, end, rent, charges, deposit in lease_data:
            lease = Lease(
                id=uuid.uuid4(),
                building_id=building.id,
                unit_id=unit.id,
                lease_type=ltype,
                reference_code=ref,
                tenant_type="contact",
                tenant_id=tenant.id,
                date_start=start,
                date_end=end,
                rent_monthly_chf=rent,
                charges_monthly_chf=charges,
                deposit_chf=deposit,
                surface_m2=unit.surface_m2,
                rooms=unit.rooms,
                status=st,
                source_type="manual",
                confidence="declared",
                created_by=admin.id,
            )
            db.add(lease)
            leases.append(lease)
        await db.flush()

        # 8. Contracts
        for ref, ctype, title, cost in [
            ("CTR-ENT-001", "heating", "Entretien chauffage annuel", 4800.0),
            ("CTR-ASC-001", "elevator", "Maintenance ascenseur Schindler", 6000.0),
            ("CTR-NET-001", "cleaning", "Nettoyage parties communes", 3600.0),
        ]:
            db.add(
                Contract(
                    id=uuid.uuid4(),
                    building_id=building.id,
                    contract_type=ctype,
                    reference_code=ref,
                    title=title,
                    counterparty_type="contact",
                    counterparty_id=tenants[4].id,
                    date_start=date(2024, 1, 1),
                    annual_cost_chf=cost,
                    payment_frequency="quarterly",
                    auto_renewal=True,
                    status="active",
                    source_type="manual",
                    confidence="verified",
                    created_by=admin.id,
                )
            )

        # 9. Insurance policy
        db.add(
            InsurancePolicy(
                id=uuid.uuid4(),
                building_id=building.id,
                policy_type="building_eca",
                policy_number="ECA-VD-2024-LAU-12",
                insurer_name="ECA Vaud",
                insured_value_chf=1800000.0,
                premium_annual_chf=920.0,
                deductible_chf=500.0,
                date_start=date(2024, 1, 1),
                date_end=date(2024, 12, 31),
                status="active",
                source_type="official",
                confidence="verified",
                created_by=admin.id,
            )
        )

        # 10. Financial entries (rent income for active leases x 3 months)
        for lease in leases:
            if lease.status != "active":
                continue
            for month in [1, 2, 3]:
                db.add(
                    FinancialEntry(
                        id=uuid.uuid4(),
                        building_id=building.id,
                        entry_type="income",
                        category="rent_income",
                        amount_chf=lease.rent_monthly_chf or 0,
                        entry_date=date(2024, month, 1),
                        fiscal_year=2024,
                        description=f"Loyer {lease.reference_code} - {month}/2024",
                        lease_id=lease.id,
                        status="recorded",
                        source_type="import",
                        confidence="verified",
                        created_by=admin.id,
                    )
                )

        # 11. Documents + DocumentLinks
        doc = Document(
            id=uuid.uuid4(),
            building_id=building.id,
            file_path="/demo/bail-002.pdf",
            file_name="bail-002.pdf",
            document_type="lease_contract",
            uploaded_by=admin.id,
        )
        db.add(doc)
        await db.flush()
        db.add(
            DocumentLink(
                id=uuid.uuid4(),
                document_id=doc.id,
                entity_type="lease",
                entity_id=leases[1].id,
                link_type="proof",
            )
        )

        await db.commit()
        print(f"Lease Ops seed complete: building={building.id}")
        print(f"  Address: {building.address}, {building.postal_code} {building.city}")
        print(f"  Leases: {len(leases)}, Units: {len(units)}, Zones: {len(zones)}")


if __name__ == "__main__":
    asyncio.run(seed())
