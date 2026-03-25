"""BatiConnect — Marketplace RFQ seed (idempotent).

Run: python -m app.seeds.seed_marketplace_rfq

Creates:
- 1 ClientRequest (published, linked to a diagnostic publication + Lausanne building)
- 2 RequestDocuments
- 2 RequestInvitations (1 accepted, 1 pending)
- 2 Quotes (1 submitted, 1 draft)
"""

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.building import Building
from app.models.client_request import ClientRequest
from app.models.company_profile import CompanyProfile
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.quote import Quote
from app.models.request_document import RequestDocument
from app.models.request_invitation import RequestInvitation
from app.models.user import User

# Stable UUIDs for idempotent seed
SEED_REQUEST_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500001")
SEED_DOC1_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500002")
SEED_DOC2_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500003")
SEED_INV1_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500004")
SEED_INV2_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500005")
SEED_QUOTE1_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500006")
SEED_QUOTE2_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500007")


async def seed():
    async with AsyncSessionLocal() as db:
        # Check idempotency
        existing = await db.execute(select(ClientRequest).where(ClientRequest.id == SEED_REQUEST_ID))
        if existing.scalar_one_or_none():
            print("Marketplace RFQ seed already present — skipping.")
            return

        # Find admin user
        admin_result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
        admin = admin_result.scalar_one_or_none()
        if not admin:
            print("Admin user not found — run base seed first.")
            return

        # Find a Lausanne building
        building_result = await db.execute(select(Building).where(Building.city == "Lausanne").limit(1))
        building = building_result.scalar_one_or_none()
        if not building:
            print("No Lausanne building found — run base seed first.")
            return

        # Find a diagnostic publication for this building
        pub_result = await db.execute(
            select(DiagnosticReportPublication).where(DiagnosticReportPublication.building_id == building.id).limit(1)
        )
        pub = pub_result.scalar_one_or_none()
        if not pub:
            print("No diagnostic publication found — run diagnostic seed first.")
            return

        # Find two company profiles
        cp_result = await db.execute(select(CompanyProfile).limit(2))
        company_profiles = list(cp_result.scalars().all())
        if len(company_profiles) < 2:
            print("Need at least 2 company profiles — run marketplace companies seed first.")
            return

        # 1. ClientRequest (published)
        req = ClientRequest(
            id=SEED_REQUEST_ID,
            building_id=building.id,
            requester_user_id=admin.id,
            requester_org_id=admin.organization_id,
            title="Desamiantage facade sud — Rue de Bourg 12",
            description="Retrait amiante en facade sud, 3 etages, acces par echafaudage.",
            pollutant_types=["asbestos"],
            work_category="major",
            estimated_area_m2=320.0,
            deadline=date(2026, 9, 30),
            status="published",
            diagnostic_publication_id=pub.id,
            budget_indication="50k_100k",
            site_access_notes="Cle a retirer a la regie. Acces parking arriere pour camions.",
            published_at=datetime.now(UTC),
        )
        db.add(req)
        await db.flush()

        # 2. RequestDocuments
        doc1 = RequestDocument(
            id=SEED_DOC1_ID,
            client_request_id=SEED_REQUEST_ID,
            filename="cahier-des-charges-desamiantage.pdf",
            file_url="/demo/rfq/cahier-des-charges.pdf",
            document_type="specification",
            uploaded_by_user_id=admin.id,
            notes="Cahier des charges complet avec plans.",
        )
        doc2 = RequestDocument(
            id=SEED_DOC2_ID,
            client_request_id=SEED_REQUEST_ID,
            filename="rapport-diagnostic-amiante.pdf",
            file_url="/demo/rfq/rapport-diagnostic.pdf",
            document_type="diagnostic_report",
            uploaded_by_user_id=admin.id,
        )
        db.add_all([doc1, doc2])

        # 3. RequestInvitations
        inv1 = RequestInvitation(
            id=SEED_INV1_ID,
            client_request_id=SEED_REQUEST_ID,
            company_profile_id=company_profiles[0].id,
            status="accepted",
            sent_at=datetime.now(UTC),
            responded_at=datetime.now(UTC),
        )
        inv2 = RequestInvitation(
            id=SEED_INV2_ID,
            client_request_id=SEED_REQUEST_ID,
            company_profile_id=company_profiles[1].id,
            status="pending",
            sent_at=datetime.now(UTC),
        )
        db.add_all([inv1, inv2])
        await db.flush()

        # 4. Quotes
        quote1_content = {
            "client_request_id": str(SEED_REQUEST_ID),
            "company_profile_id": str(company_profiles[0].id),
            "amount_chf": "78500.00",
            "currency": "CHF",
            "validity_days": 30,
            "description": "Desamiantage complet facade sud, 3 etages.",
            "work_plan": "Phase 1: confinement. Phase 2: retrait. Phase 3: controle air.",
            "timeline_weeks": 6,
            "includes": ["mobilization", "waste_disposal", "air_monitoring", "final_report"],
            "excludes": ["scaffolding"],
        }
        quote1_hash = hashlib.sha256(json.dumps(quote1_content, sort_keys=True).encode()).hexdigest()

        quote1 = Quote(
            id=SEED_QUOTE1_ID,
            client_request_id=SEED_REQUEST_ID,
            company_profile_id=company_profiles[0].id,
            invitation_id=SEED_INV1_ID,
            amount_chf=78500.00,
            currency="CHF",
            validity_days=30,
            description="Desamiantage complet facade sud, 3 etages.",
            work_plan="Phase 1: confinement. Phase 2: retrait. Phase 3: controle air.",
            timeline_weeks=6,
            includes=["mobilization", "waste_disposal", "air_monitoring", "final_report"],
            excludes=["scaffolding"],
            status="submitted",
            submitted_at=datetime.now(UTC),
            content_hash=quote1_hash,
        )
        quote2 = Quote(
            id=SEED_QUOTE2_ID,
            client_request_id=SEED_REQUEST_ID,
            company_profile_id=company_profiles[1].id,
            amount_chf=92000.00,
            currency="CHF",
            validity_days=45,
            description="Offre desamiantage facade — approche conservatrice.",
            timeline_weeks=8,
            includes=["mobilization", "waste_disposal", "air_monitoring", "final_report", "scaffolding"],
            excludes=["permits"],
            status="draft",
        )
        db.add_all([quote1, quote2])

        await db.commit()
        print(f"Marketplace RFQ seed complete: request={SEED_REQUEST_ID}")
        print(f"  Building: {building.address}, {building.city}")
        print("  Documents: 2, Invitations: 2, Quotes: 2")


if __name__ == "__main__":
    asyncio.run(seed())
