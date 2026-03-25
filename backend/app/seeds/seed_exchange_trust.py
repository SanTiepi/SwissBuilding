"""BatiConnect — Exchange contract + Partner trust demonstrator seed.

Run: python -m app.seeds.seed_exchange_trust

Creates:
- 3 ExchangeContractVersions (diagnostic_report_v1, authority_pack_v1, building_passport_v1)
- 1 PassportPublication (published to authority)
- 1 ImportReceipt (received from batiscan)
- 1 PartnerTrustProfile (adequate trust)
- 3 PartnerTrustSignals
"""

import asyncio
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.building import Building
from app.models.exchange_contract import ExchangeContractVersion
from app.models.import_receipt import PassportImportReceipt
from app.models.organization import Organization
from app.models.partner_trust import PartnerTrustProfile, PartnerTrustSignal
from app.models.passport_publication import PassportPublication
from app.models.user import User


async def seed():
    async with AsyncSessionLocal() as db:
        # Find admin user
        result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
        admin = result.scalar_one_or_none()
        if not admin:
            print("Admin user not found — run base seed first.")
            return

        org_id = admin.organization_id

        # Find first building
        result = await db.execute(select(Building).limit(1))
        building = result.scalar_one_or_none()
        if not building:
            print("No buildings found — run base seed first.")
            return

        # Find an org for partner trust (use first non-admin org if available)
        result = await db.execute(select(Organization).where(Organization.id != org_id).limit(1))
        partner_org = result.scalar_one_or_none()
        if not partner_org:
            # Create a partner org
            partner_org = Organization(
                id=uuid.uuid4(),
                name="DiagSwiss SA",
                type="diagnostic_lab",
            )
            db.add(partner_org)
            await db.flush()

        # --- 1. Exchange Contract Versions (idempotent) ---
        contracts_data = [
            {
                "contract_code": "diagnostic_report_v1",
                "version": 1,
                "status": "active",
                "audience_type": "authority",
                "payload_type": "diagnostic_report",
                "effective_from": date(2025, 1, 1),
                "compatibility_notes": "Standard diagnostic report format for VD/GE authorities",
            },
            {
                "contract_code": "authority_pack_v1",
                "version": 1,
                "status": "active",
                "audience_type": "authority",
                "payload_type": "authority_pack",
                "effective_from": date(2025, 1, 1),
                "compatibility_notes": "Full authority submission pack with evidence chain",
            },
            {
                "contract_code": "building_passport_v1",
                "version": 1,
                "status": "active",
                "audience_type": "buyer",
                "payload_type": "passport_summary",
                "effective_from": date(2025, 6, 1),
                "compatibility_notes": "Building passport summary for transaction due diligence",
            },
        ]

        contract_ids = []
        for cdata in contracts_data:
            existing = await db.execute(
                select(ExchangeContractVersion).where(
                    ExchangeContractVersion.contract_code == cdata["contract_code"],
                    ExchangeContractVersion.version == cdata["version"],
                )
            )
            contract = existing.scalar_one_or_none()
            if not contract:
                contract = ExchangeContractVersion(id=uuid.uuid4(), **cdata)
                db.add(contract)
                await db.flush()
            contract_ids.append(contract.id)

        # --- 2. Passport Publication (idempotent by content_hash) ---
        pub_hash = "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd"
        existing_pub = await db.execute(select(PassportPublication).where(PassportPublication.content_hash == pub_hash))
        pub = existing_pub.scalar_one_or_none()
        if not pub:
            pub = PassportPublication(
                id=uuid.uuid4(),
                building_id=building.id,
                contract_version_id=contract_ids[1],  # authority_pack_v1
                audience_type="authority",
                publication_type="authority_pack",
                content_hash=pub_hash,
                published_at=datetime.now(UTC),
                published_by_org_id=org_id,
                published_by_user_id=admin.id,
                delivery_state="delivered",
            )
            db.add(pub)
            await db.flush()

        # --- 3. Import Receipt (idempotent by content_hash) ---
        import_hash = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
        existing_receipt = await db.execute(
            select(PassportImportReceipt).where(PassportImportReceipt.content_hash == import_hash)
        )
        if not existing_receipt.scalar_one_or_none():
            receipt = PassportImportReceipt(
                id=uuid.uuid4(),
                building_id=building.id,
                source_system="batiscan-legacy",
                contract_code="diagnostic_report_v1",
                contract_version=1,
                import_reference="IMPORT-2025-001",
                status="integrated",
                content_hash=import_hash,
                matched_publication_id=pub.id,
                notes="Initial diagnostic import from Batiscan legacy system",
            )
            db.add(receipt)

        # --- 4. Partner Trust Profile (idempotent by partner_org_id) ---
        existing_profile = await db.execute(
            select(PartnerTrustProfile).where(PartnerTrustProfile.partner_org_id == partner_org.id)
        )
        if not existing_profile.scalar_one_or_none():
            profile = PartnerTrustProfile(
                id=uuid.uuid4(),
                partner_org_id=partner_org.id,
                delivery_reliability_score=0.85,
                evidence_quality_score=0.7,
                responsiveness_score=0.9,
                overall_trust_level="adequate",
                signal_count=3,
                last_evaluated_at=datetime.now(UTC),
                notes="Reliable diagnostic partner — minor evidence rework needed",
            )
            db.add(profile)

        # --- 5. Partner Trust Signals (idempotent by count check) ---
        existing_signals = await db.execute(
            select(PartnerTrustSignal).where(PartnerTrustSignal.partner_org_id == partner_org.id)
        )
        if not existing_signals.scalars().all():
            for stype, notes, val in [
                ("delivery_success", "Diagnostic report delivered on time", 1.0),
                ("evidence_clean", "Evidence pack validated without rework", 1.0),
                ("response_fast", "Responded to complement request within 24h", 0.9),
            ]:
                db.add(
                    PartnerTrustSignal(
                        id=uuid.uuid4(),
                        partner_org_id=partner_org.id,
                        signal_type=stype,
                        value=val,
                        notes=notes,
                        recorded_at=datetime.now(UTC),
                    )
                )

        await db.commit()
        print("Exchange + Trust seed complete.")
        print(f"  Contracts: {len(contracts_data)}")
        print(f"  Publication: 1 (building={building.id})")
        print("  Import receipt: 1")
        print(f"  Partner profile: 1 (org={partner_org.id})")
        print("  Trust signals: 3")


if __name__ == "__main__":
    asyncio.run(seed())
