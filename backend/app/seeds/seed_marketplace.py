"""BatiConnect — Marketplace seed (idempotent).

Run: python -m app.seeds.seed_marketplace

Creates:
- 3 CompanyProfiles (fully verified+subscribed, pending verification, rejected)
- 3 CompanyVerifications (approved, pending, rejected)
- 2 CompanySubscriptions (1 active professional, 1 expired basic)
"""

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

from app.database import AsyncSessionLocal
from app.models.company_profile import CompanyProfile
from app.models.company_subscription import CompanySubscription
from app.models.company_verification import CompanyVerification
from app.models.organization import Organization
from app.models.user import User
from app.services.marketplace_service import compute_profile_completeness


async def seed():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        # Find admin user
        result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
        admin = result.scalar_one_or_none()
        if not admin:
            print("Admin user not found — run base seed first")
            return

        # Check idempotency
        existing = await db.execute(select(CompanyProfile).limit(1))
        if existing.scalar_one_or_none():
            print("Marketplace seed already present — skipping")
            return

        # 1. Organizations for marketplace companies (contractor type)
        orgs = []
        for name, otype in [
            ("SanaCore Assainissement SA", "contractor"),
            ("EcoDecon Sarl", "contractor"),
            ("AlpenClean GmbH", "contractor"),
        ]:
            org = Organization(id=uuid.uuid4(), name=name, type=otype)
            db.add(org)
            orgs.append(org)
        await db.flush()

        now = datetime.now(UTC)

        # 2. Company Profiles
        profile_1 = CompanyProfile(
            id=uuid.uuid4(),
            organization_id=orgs[0].id,
            company_name="SanaCore Assainissement SA",
            legal_form="SA",
            uid_number="CHE-123.456.789",
            address="Route de Geneve 42",
            city="Lausanne",
            postal_code="1003",
            canton="VD",
            contact_email="info@sanacore.ch",
            contact_phone="+41 21 312 45 67",
            website="https://sanacore.ch",
            description="Specialiste en desamiantage et decontamination de batiments depuis 2005.",
            work_categories=["asbestos_removal", "pcb_remediation", "decontamination", "waste_management"],
            certifications=[
                {"name": "SUVA Amiante Cat. A", "issuer": "SUVA", "valid_until": "2027-12-31"},
                {"name": "ISO 14001", "issuer": "SQS", "valid_until": "2026-06-30"},
            ],
            regions_served=["VD", "GE", "FR", "VS"],
            employee_count=45,
            years_experience=20,
            insurance_info={"rc_policy": "RC-2024-001", "rc_amount_chf": 5000000, "rc_valid_until": "2026-12-31"},
            is_active=True,
        )
        profile_1.profile_completeness = compute_profile_completeness(profile_1)

        profile_2 = CompanyProfile(
            id=uuid.uuid4(),
            organization_id=orgs[1].id,
            company_name="EcoDecon Sarl",
            legal_form="Sarl",
            uid_number="CHE-987.654.321",
            address="Rue du Marche 8",
            city="Geneve",
            postal_code="1204",
            canton="GE",
            contact_email="contact@ecodecon.ch",
            contact_phone="+41 22 700 88 99",
            description="Decontamination et gestion des dechets speciaux.",
            work_categories=["lead_abatement", "hap_treatment", "demolition"],
            regions_served=["GE", "VD"],
            employee_count=18,
            years_experience=8,
            is_active=True,
        )
        profile_2.profile_completeness = compute_profile_completeness(profile_2)

        profile_3 = CompanyProfile(
            id=uuid.uuid4(),
            organization_id=orgs[2].id,
            company_name="AlpenClean GmbH",
            legal_form="other",
            address="Bahnhofstrasse 15",
            city="Bern",
            postal_code="3001",
            canton="BE",
            contact_email="info@alpenclean.ch",
            work_categories=["asbestos_removal"],
            is_active=True,
        )
        profile_3.profile_completeness = compute_profile_completeness(profile_3)

        db.add_all([profile_1, profile_2, profile_3])
        await db.flush()

        # 3. Verifications
        verif_approved = CompanyVerification(
            id=uuid.uuid4(),
            company_profile_id=profile_1.id,
            status="approved",
            verified_by_user_id=admin.id,
            verified_at=now - timedelta(days=30),
            verification_type="initial",
            checks_performed=[
                {"check_type": "uid_valid", "result": "pass", "notes": "CHE verified on Zefix"},
                {"check_type": "insurance_valid", "result": "pass", "notes": "RC policy confirmed"},
                {"check_type": "certifications_confirmed", "result": "pass", "notes": "SUVA cert verified"},
            ],
            valid_until=date(2027, 3, 25),
        )
        verif_pending = CompanyVerification(
            id=uuid.uuid4(),
            company_profile_id=profile_2.id,
            status="pending",
            verification_type="initial",
        )
        verif_rejected = CompanyVerification(
            id=uuid.uuid4(),
            company_profile_id=profile_3.id,
            status="rejected",
            verified_by_user_id=admin.id,
            verified_at=now - timedelta(days=10),
            verification_type="initial",
            checks_performed=[
                {"check_type": "uid_valid", "result": "fail", "notes": "No UID provided"},
                {"check_type": "insurance_valid", "result": "fail", "notes": "No insurance info"},
            ],
            rejection_reason="Missing UID and insurance documentation",
        )
        db.add_all([verif_approved, verif_pending, verif_rejected])

        # 4. Subscriptions
        sub_active = CompanySubscription(
            id=uuid.uuid4(),
            company_profile_id=profile_1.id,
            plan_type="professional",
            status="active",
            started_at=now - timedelta(days=90),
            expires_at=now + timedelta(days=275),
            is_network_eligible=True,
            billing_reference="INV-2026-001",
        )
        sub_expired = CompanySubscription(
            id=uuid.uuid4(),
            company_profile_id=profile_2.id,
            plan_type="basic",
            status="expired",
            started_at=now - timedelta(days=365),
            expires_at=now - timedelta(days=5),
            is_network_eligible=False,
        )
        db.add_all([sub_active, sub_expired])

        await db.commit()
        print("Marketplace seed complete:")
        print(f"  Profiles: 3 ({profile_1.company_name}, {profile_2.company_name}, {profile_3.company_name})")
        print("  Verifications: 3 (approved, pending, rejected)")
        print("  Subscriptions: 2 (active professional, expired basic)")


if __name__ == "__main__":
    asyncio.run(seed())
