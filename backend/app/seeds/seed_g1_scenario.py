"""G1 Demo Scenario Seed: VD building with partial pollutant dossier.

The building looks 'partially documented' but is NOT ready:
1. Asbestos diagnostic expired (2021, >3 years)
2. PCB diagnostic valid (2024)
3. No waste disposal plan
4. No SUVA notification
5. Basement not covered by asbestos diagnostic (scope gap)

Usage:
    python -m app.seeds.seed_g1_scenario
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fixed IDs for demo stability
# ---------------------------------------------------------------------------
G1_ORG_ID = uuid.UUID("a1b2c3d4-0001-0001-0001-000000000001")
G1_BUILDING_ID = uuid.UUID("a1b2c3d4-0001-0001-0002-000000000001")
G1_DIAG_ASBESTOS_ID = uuid.UUID("a1b2c3d4-0001-0001-0003-000000000001")
G1_DIAG_PCB_ID = uuid.UUID("a1b2c3d4-0001-0001-0003-000000000002")
G1_ZONE_BASEMENT_ID = uuid.UUID("a1b2c3d4-0001-0001-0004-000000000001")
G1_ZONE_GROUND_ID = uuid.UUID("a1b2c3d4-0001-0001-0004-000000000002")
G1_ZONE_UPPER_ID = uuid.UUID("a1b2c3d4-0001-0001-0004-000000000003")


async def seed_g1_scenario(db: AsyncSession) -> dict:
    """Seed the G1 demo scenario: VD building with partial pollutant dossier.

    Returns a summary dict describing what was created.
    """
    # Check if already seeded
    existing = await db.execute(select(Building).where(Building.id == G1_BUILDING_ID))
    if existing.scalar_one_or_none() is not None:
        logger.info("G1 scenario already seeded, skipping")
        return {"status": "already_seeded"}

    # Find or create admin user
    user_result = await db.execute(select(User).where(User.role == "admin").limit(1))
    admin = user_result.scalar_one_or_none()
    admin_id = admin.id if admin else uuid.uuid4()

    # 1. Organization
    org = Organization(
        id=G1_ORG_ID,
        name="Regie du Leman SA",
        type="property_management",
        address="Avenue de la Gare 15",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        email="contact@regieduleman.ch",
    )
    db.add(org)

    # 2. Building: pre-1990 Lausanne
    building = Building(
        id=G1_BUILDING_ID,
        address="Chemin des Alpes 28",
        postal_code="1006",
        city="Lausanne",
        canton="VD",
        construction_year=1972,
        building_type="residential",
        egid="123456789",
        status="active",
        created_by=admin_id,
        organization_id=G1_ORG_ID,
    )
    db.add(building)

    # 3. Zones
    zone_basement = Zone(
        id=G1_ZONE_BASEMENT_ID,
        building_id=G1_BUILDING_ID,
        zone_type="floor",
        name="Sous-sol / Cave",
    )
    zone_ground = Zone(
        id=G1_ZONE_GROUND_ID,
        building_id=G1_BUILDING_ID,
        zone_type="floor",
        name="Rez-de-chaussee",
    )
    zone_upper = Zone(
        id=G1_ZONE_UPPER_ID,
        building_id=G1_BUILDING_ID,
        zone_type="floor",
        name="Etages superieurs (1-3)",
    )
    db.add_all([zone_basement, zone_ground, zone_upper])

    # 4. EXPIRED asbestos diagnostic (2021 -- > 3 years old)
    diag_asbestos = Diagnostic(
        id=G1_DIAG_ASBESTOS_ID,
        building_id=G1_BUILDING_ID,
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="completed",
        date_inspection=date(2021, 3, 15),
        date_report=date(2021, 4, 10),
        laboratory="Analytica SA",
        suva_notification_required=True,
        suva_notification_date=None,  # NOT notified -- blocker
    )
    db.add(diag_asbestos)

    # Asbestos samples (from ground + upper floors only -- basement NOT covered)
    asbestos_samples = [
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=G1_DIAG_ASBESTOS_ID,
            sample_number="G1-AMI-001",
            pollutant_type="asbestos",
            material_category="flocage",
            location_description="Rez-de-chaussee, faux plafond hall",
            concentration=25.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="major",
            action_required="remove_planned",
            waste_disposal_type="type_e",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=G1_DIAG_ASBESTOS_ID,
            sample_number="G1-AMI-002",
            pollutant_type="asbestos",
            material_category="colle_carrelage",
            location_description="Etage 2, cuisine",
            concentration=3.5,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="medium",
            cfst_work_category="medium",
            action_required="remove_planned",
            waste_disposal_type="type_e",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=G1_DIAG_ASBESTOS_ID,
            sample_number="G1-AMI-003",
            pollutant_type="asbestos",
            material_category="joint_fenetre",
            location_description="Etage 1, salon",
            concentration=0.5,
            unit="percent_weight",
            threshold_exceeded=False,
            risk_level="low",
            cfst_work_category=None,
            action_required="none",
            waste_disposal_type=None,
        ),
    ]
    db.add_all(asbestos_samples)

    # 5. VALID PCB diagnostic (2024)
    diag_pcb = Diagnostic(
        id=G1_DIAG_PCB_ID,
        building_id=G1_BUILDING_ID,
        diagnostic_type="pcb",
        diagnostic_context="AvT",
        status="completed",
        date_inspection=date(2024, 6, 20),
        date_report=date(2024, 7, 5),
        laboratory="EnviroLab Suisse",
    )
    db.add(diag_pcb)

    pcb_samples = [
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=G1_DIAG_PCB_ID,
            sample_number="G1-PCB-001",
            pollutant_type="pcb",
            material_category="joint_etancheite",
            location_description="Facade nord, joints de dilatation",
            concentration=85.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            action_required="remove_planned",
            waste_disposal_type="type_e",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=G1_DIAG_PCB_ID,
            sample_number="G1-PCB-002",
            pollutant_type="pcb",
            material_category="condensateur",
            location_description="Sous-sol, local technique",
            concentration=12.0,
            unit="mg_per_kg",
            threshold_exceeded=False,
            risk_level="low",
            action_required="none",
            waste_disposal_type=None,
        ),
    ]
    db.add_all(pcb_samples)

    # 6. Documents -- diagnostic reports exist but NO waste plan
    doc_asbestos_report = Document(
        id=uuid.uuid4(),
        building_id=G1_BUILDING_ID,
        file_path="/docs/g1/rapport_amiante_2021.pdf",
        file_name="rapport_amiante_2021.pdf",
        document_type="diagnostic_report",
        file_size=2_500_000,
    )
    doc_pcb_report = Document(
        id=uuid.uuid4(),
        building_id=G1_BUILDING_ID,
        file_path="/docs/g1/rapport_pcb_2024.pdf",
        file_name="rapport_pcb_2024.pdf",
        document_type="diagnostic_report",
        file_size=1_800_000,
    )
    db.add_all([doc_asbestos_report, doc_pcb_report])
    # NOTE: No waste_elimination_plan document
    # NOTE: No SUVA notification document

    # 7. Actions -- open high-priority actions
    actions = [
        ActionItem(
            id=uuid.uuid4(),
            building_id=G1_BUILDING_ID,
            source_type="diagnostic",
            action_type="notification",
            title="Notifier la SUVA pour amiante positif",
            description="Echantillons G1-AMI-001 et G1-AMI-002 positifs, notification SUVA obligatoire (OTConst Art. 82-86)",
            priority="critical",
            status="open",
        ),
        ActionItem(
            id=uuid.uuid4(),
            building_id=G1_BUILDING_ID,
            source_type="diagnostic",
            action_type="documentation",
            title="Etablir le plan de gestion des dechets",
            description="Aucun plan d'elimination des dechets disponible -- requis avant travaux (OLED)",
            priority="high",
            status="open",
        ),
        ActionItem(
            id=uuid.uuid4(),
            building_id=G1_BUILDING_ID,
            source_type="diagnostic",
            action_type="investigation",
            title="Diagnostic sous-sol manquant",
            description="Le sous-sol / cave n'a pas ete couvert par le diagnostic amiante 2021. Zone a risque potentiel.",
            priority="high",
            status="open",
        ),
    ]
    db.add_all(actions)

    await db.commit()

    summary = {
        "status": "seeded",
        "building_id": str(G1_BUILDING_ID),
        "org_id": str(G1_ORG_ID),
        "diagnostics": 2,
        "samples": len(asbestos_samples) + len(pcb_samples),
        "documents": 2,
        "zones": 3,
        "actions": len(actions),
        "blockers": [
            "Diagnostic amiante expire (2021, > 3 ans)",
            "Notification SUVA manquante",
            "Plan de gestion des dechets manquant",
            "Sous-sol non couvert par le diagnostic",
        ],
    }
    logger.info("G1 scenario seeded: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


async def _main():
    from app.database import async_session_factory

    async with async_session_factory() as db:
        result = await seed_g1_scenario(db)
        print(f"G1 scenario seed result: {result}")


if __name__ == "__main__":
    asyncio.run(_main())
