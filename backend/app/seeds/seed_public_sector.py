"""BatiConnect — Public Sector seed data.

Run: python -m app.seeds.seed_public_sector

Creates:
- 1 PublicOwnerOperatingMode (municipal, enhanced governance)
- 1 MunicipalityReviewPack (ready, circulated)
- 1 CommitteeDecisionPack (decided)
- 2 ReviewDecisionTraces (1 approved, 1 deferred with conditions)
- 3 GovernanceSignals (1 resolved, 2 active)
"""

import asyncio
import uuid
from datetime import UTC, date, datetime

from app.database import AsyncSessionLocal
from app.models.building import Building
from app.models.committee_decision import CommitteeDecisionPack, ReviewDecisionTrace
from app.models.governance_signal import PublicAssetGovernanceSignal
from app.models.municipality_review_pack import MunicipalityReviewPack
from app.models.organization import Organization
from app.models.public_owner_mode import PublicOwnerOperatingMode
from app.models.user import User


async def seed():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        # Find admin user + org
        result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
        admin = result.scalar_one_or_none()

        if not admin:
            org = Organization(id=uuid.uuid4(), name="Commune de Lausanne", type="authority")
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

        # Find or create a building
        result = await db.execute(select(Building).limit(1))
        building = result.scalar_one_or_none()
        if not building:
            building = Building(
                id=uuid.uuid4(),
                address="Place de la Palud 2",
                postal_code="1003",
                city="Lausanne",
                canton="VD",
                building_type="administrative",
                construction_year=1920,
                created_by=admin.id,
                organization_id=org_id,
            )
            db.add(building)
            await db.flush()

        # Check idempotency
        result = await db.execute(
            select(PublicOwnerOperatingMode).where(PublicOwnerOperatingMode.organization_id == org_id)
        )
        if result.scalar_one_or_none():
            print("Public sector seed already present — skipping.")
            return

        # 1. PublicOwnerOperatingMode
        mode = PublicOwnerOperatingMode(
            id=uuid.uuid4(),
            organization_id=org_id,
            mode_type="municipal",
            is_active=True,
            governance_level="enhanced",
            requires_committee_review=True,
            requires_review_pack=True,
            default_review_audience=["committee", "municipal_council"],
            notes="Configuration pour commune VD",
            activated_at=datetime(2025, 1, 15, tzinfo=UTC),
        )
        db.add(mode)

        # 2. MunicipalityReviewPack (ready, circulated)
        review_pack = MunicipalityReviewPack(
            id=uuid.uuid4(),
            building_id=building.id,
            generated_by_user_id=admin.id,
            pack_version=1,
            status="circulating",
            sections=[
                {"section_type": "building_identity", "title": "Identite du batiment", "content_summary": "Assembled"},
                {
                    "section_type": "diagnostics_summary",
                    "title": "Resume des diagnostics",
                    "content_summary": "3 diagnostics amiante completes",
                },
                {"section_type": "procedure_state", "title": "Etat des procedures", "content_summary": "Assembled"},
                {"section_type": "proof_inventory", "title": "Inventaire des preuves", "content_summary": "Assembled"},
                {
                    "section_type": "obligations_summary",
                    "title": "Resume des obligations",
                    "content_summary": "Assembled",
                },
                {"section_type": "commune_context", "title": "Contexte communal", "content_summary": "Assembled"},
            ],
            content_hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            review_deadline=date(2026, 6, 30),
            circulated_to=[
                {"org_name": "Commission des travaux", "role": "committee", "sent_at": "2026-03-10T10:00:00Z"},
                {"org_name": "Service de l'urbanisme", "role": "cantonal_authority", "sent_at": "2026-03-10T10:00:00Z"},
            ],
            notes="Dossier amiante - revue annuelle",
            generated_at=datetime(2026, 3, 10, 10, 0, 0, tzinfo=UTC),
        )
        db.add(review_pack)

        # 3. CommitteeDecisionPack (decided)
        committee_pack = CommitteeDecisionPack(
            id=uuid.uuid4(),
            building_id=building.id,
            committee_name="Commission des travaux publics",
            committee_type="building_committee",
            pack_version=1,
            status="decided",
            sections=[
                {"section_type": "building_identity", "title": "Identite du batiment", "content_summary": "Assembled"},
                {"section_type": "risk_assessment", "title": "Evaluation des risques", "content_summary": "Assembled"},
                {"section_type": "financial_impact", "title": "Impact financier", "content_summary": "CHF 180'000"},
                {"section_type": "legal_obligations", "title": "Obligations legales", "content_summary": "OTConst 82"},
            ],
            procurement_clauses=[
                {
                    "clause_id": "ECO-001",
                    "clause_text": "Entreprise certifiee SUVA pour travaux amiante",
                    "legal_ref": "OTConst Art. 82",
                    "scope": "desamiantage",
                },
            ],
            content_hash="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
            decision_deadline=date(2026, 4, 15),
            submitted_at=datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC),
            decided_at=datetime(2026, 3, 20, 16, 30, 0, tzinfo=UTC),
        )
        db.add(committee_pack)
        await db.flush()

        # 4. ReviewDecisionTraces
        trace1 = ReviewDecisionTrace(
            id=uuid.uuid4(),
            pack_type="committee",
            pack_id=committee_pack.id,
            reviewer_name="Marc Dupont",
            reviewer_role="President de commission",
            decision="approved",
            notes="Approuve a l'unanimite. Travaux a planifier Q3 2026.",
            evidence_refs=[{"entity_type": "diagnostic", "entity_id": str(uuid.uuid4()), "label": "Diag amiante 2025"}],
            confidence_level="high",
            decided_at=datetime(2026, 3, 20, 16, 30, 0, tzinfo=UTC),
        )
        trace2 = ReviewDecisionTrace(
            id=uuid.uuid4(),
            pack_type="committee",
            pack_id=committee_pack.id,
            reviewer_name="Isabelle Morel",
            reviewer_role="Membre",
            decision="deferred",
            conditions="Demande de devis supplementaire aupres d'un deuxieme prestataire certifie SUVA.",
            notes="Report de decision sur le lot 2 (facade nord).",
            confidence_level="medium",
            decided_at=datetime(2026, 3, 20, 16, 45, 0, tzinfo=UTC),
        )
        db.add_all([trace1, trace2])

        # 5. GovernanceSignals (1 resolved, 2 active)
        signal1 = PublicAssetGovernanceSignal(
            id=uuid.uuid4(),
            organization_id=org_id,
            building_id=building.id,
            signal_type="review_overdue",
            severity="warning",
            title="Revue annuelle amiante en retard",
            description="La revue annuelle du dossier amiante devait etre completee avant le 31.12.2025.",
            resolved=True,
            resolved_at=datetime(2026, 1, 15, 9, 0, 0, tzinfo=UTC),
        )
        signal2 = PublicAssetGovernanceSignal(
            id=uuid.uuid4(),
            organization_id=org_id,
            building_id=building.id,
            signal_type="decision_pending",
            severity="info",
            title="Decision commission en attente — lot 2 facade nord",
            description="Le lot 2 est en attente d'un devis supplementaire.",
        )
        signal3 = PublicAssetGovernanceSignal(
            id=uuid.uuid4(),
            organization_id=org_id,
            signal_type="governance_gap",
            severity="critical",
            title="Mode public non active pour 3 batiments du portefeuille",
            description="3 batiments n'ont pas de mode de gouvernance publique configure.",
        )
        db.add_all([signal1, signal2, signal3])

        await db.commit()
        print(f"Public sector seed complete: org={org_id}, building={building.id}")
        print(f"  Mode: {mode.mode_type}/{mode.governance_level}")
        print(f"  Review pack: {review_pack.id} ({review_pack.status})")
        print(f"  Committee pack: {committee_pack.id} ({committee_pack.status})")
        print("  Traces: 2, Signals: 3")


if __name__ == "__main__":
    asyncio.run(seed())
