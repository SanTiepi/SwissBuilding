"""Prospect-grade demo seed: 5 VD buildings across different readiness states.

Creates the FULL demo portfolio for prospect conversion:
  Building 1: "Rue de Bourg 12"         -- partially ready (expired asbestos, missing waste plan)
  Building 2: "Avenue d'Ouchy 45"        -- ready (all diagnostics valid, all docs present)
  Building 3: "Chemin des Vignes 8"      -- not assessed (new acquisition, no diagnostics)
  Building 4: "Place St-Francois 3"      -- pack submitted, awaiting acknowledgment
  Building 5: "Rue du Petit-Chene 21"    -- complement requested (authority returned dossier)

One org "Regie Pilote SA" with 2 users (RT + director).
Idempotent: safe to re-run.

Usage:
    python -m app.seeds.seed_prospect_scenario
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_case import BuildingCase
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_pack import EvidencePack
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone

logger = logging.getLogger(__name__)
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Fixed IDs for demo stability
# ---------------------------------------------------------------------------
PROSPECT_ORG_ID = uuid.UUID("b2c3d4e5-0002-0002-0001-000000000001")

# Users
PROSPECT_USER_RT_ID = uuid.UUID("b2c3d4e5-0002-0002-0010-000000000001")
PROSPECT_USER_DIR_ID = uuid.UUID("b2c3d4e5-0002-0002-0010-000000000002")

# Buildings
B1_ID = uuid.UUID("b2c3d4e5-0002-0002-0100-000000000001")
B2_ID = uuid.UUID("b2c3d4e5-0002-0002-0100-000000000002")
B3_ID = uuid.UUID("b2c3d4e5-0002-0002-0100-000000000003")
B4_ID = uuid.UUID("b2c3d4e5-0002-0002-0100-000000000004")
B5_ID = uuid.UUID("b2c3d4e5-0002-0002-0100-000000000005")

# Diagnostics
B1_DIAG_ASBESTOS_ID = uuid.UUID("b2c3d4e5-0002-0002-0200-000000000001")
B1_DIAG_PCB_ID = uuid.UUID("b2c3d4e5-0002-0002-0200-000000000002")
B2_DIAG_ASBESTOS_ID = uuid.UUID("b2c3d4e5-0002-0002-0200-000000000003")
B2_DIAG_PCB_ID = uuid.UUID("b2c3d4e5-0002-0002-0200-000000000004")
B2_DIAG_LEAD_ID = uuid.UUID("b2c3d4e5-0002-0002-0200-000000000005")
B4_DIAG_ASBESTOS_ID = uuid.UUID("b2c3d4e5-0002-0002-0200-000000000006")
B4_DIAG_PCB_ID = uuid.UUID("b2c3d4e5-0002-0002-0200-000000000007")
B5_DIAG_ASBESTOS_ID = uuid.UUID("b2c3d4e5-0002-0002-0200-000000000008")

# Packs
B4_PACK_ID = uuid.UUID("b2c3d4e5-0002-0002-0300-000000000001")
B5_PACK_ID = uuid.UUID("b2c3d4e5-0002-0002-0300-000000000002")

# Cases
B4_CASE_ID = uuid.UUID("b2c3d4e5-0002-0002-0400-000000000001")
B5_CASE_ID = uuid.UUID("b2c3d4e5-0002-0002-0400-000000000002")


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------


async def seed_prospect_scenario(db: AsyncSession) -> dict:
    """Seed the prospect demo scenario: 5 VD buildings, 1 org, 2 users.

    Returns a summary dict describing what was created.
    """
    # Check if already seeded
    existing = await db.execute(select(Building).where(Building.id == B1_ID))
    if existing.scalar_one_or_none() is not None:
        logger.info("Prospect scenario already seeded, skipping")
        return {"status": "already_seeded"}

    # ------------------------------------------------------------------
    # 1. Organization
    # ------------------------------------------------------------------
    org = Organization(
        id=PROSPECT_ORG_ID,
        name="Regie Pilote SA",
        type="property_management",
        address="Rue du Grand-Pont 4",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        email="contact@regiepilote.ch",
    )
    db.add(org)

    # ------------------------------------------------------------------
    # 2. Users (RT = responsable technique, DIR = directeur)
    # ------------------------------------------------------------------
    user_rt = User(
        id=PROSPECT_USER_RT_ID,
        email="marc.favre@regiepilote.ch",
        password_hash=pwd.hash("pilot123"),
        first_name="Marc",
        last_name="Favre",
        role="owner",
        organization_id=PROSPECT_ORG_ID,
        language="fr",
    )
    user_dir = User(
        id=PROSPECT_USER_DIR_ID,
        email="nathalie.blanc@regiepilote.ch",
        password_hash=pwd.hash("pilot123"),
        first_name="Nathalie",
        last_name="Blanc",
        role="owner",
        organization_id=PROSPECT_ORG_ID,
        language="fr",
    )
    db.add_all([user_rt, user_dir])

    # ------------------------------------------------------------------
    # 3. Buildings
    # ------------------------------------------------------------------
    buildings_data = [
        {
            "id": B1_ID,
            "address": "Rue de Bourg 12",
            "postal_code": "1003",
            "city": "Lausanne",
            "canton": "VD",
            "construction_year": 1968,
            "building_type": "mixed",
            "egid": 190200101,
            "status": "active",
        },
        {
            "id": B2_ID,
            "address": "Avenue d'Ouchy 45",
            "postal_code": "1006",
            "city": "Lausanne",
            "canton": "VD",
            "construction_year": 1975,
            "building_type": "residential",
            "egid": 190200102,
            "status": "active",
        },
        {
            "id": B3_ID,
            "address": "Chemin des Vignes 8",
            "postal_code": "1009",
            "city": "Pully",
            "canton": "VD",
            "construction_year": 1982,
            "building_type": "residential",
            "egid": 190200103,
            "status": "active",
        },
        {
            "id": B4_ID,
            "address": "Place St-Francois 3",
            "postal_code": "1003",
            "city": "Lausanne",
            "canton": "VD",
            "construction_year": 1960,
            "building_type": "commercial",
            "egid": 190200104,
            "status": "active",
        },
        {
            "id": B5_ID,
            "address": "Rue du Petit-Chene 21",
            "postal_code": "1003",
            "city": "Lausanne",
            "canton": "VD",
            "construction_year": 1955,
            "building_type": "mixed",
            "egid": 190200105,
            "status": "active",
        },
    ]

    for bd in buildings_data:
        db.add(
            Building(
                **bd,
                created_by=PROSPECT_USER_RT_ID,
                organization_id=PROSPECT_ORG_ID,
            )
        )

    # ------------------------------------------------------------------
    # 4. Zones (for each building)
    # ------------------------------------------------------------------
    for bid in [B1_ID, B2_ID, B3_ID, B4_ID, B5_ID]:
        db.add_all(
            [
                Zone(id=uuid.uuid4(), building_id=bid, zone_type="floor", name="Sous-sol"),
                Zone(id=uuid.uuid4(), building_id=bid, zone_type="floor", name="Rez-de-chaussee"),
                Zone(id=uuid.uuid4(), building_id=bid, zone_type="floor", name="Etages"),
            ]
        )

    # ==================================================================
    # Building 1: Partially ready
    #   - Expired asbestos diagnostic (2021)
    #   - Valid PCB diagnostic (2024)
    #   - Missing waste plan
    # ==================================================================
    db.add(
        Diagnostic(
            id=B1_DIAG_ASBESTOS_ID,
            building_id=B1_ID,
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2021, 5, 10),
            date_report=date(2021, 6, 1),
            laboratory="Analytica SA",
            suva_notification_required=True,
            suva_notification_date=None,
        )
    )
    db.add_all(
        [
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=B1_DIAG_ASBESTOS_ID,
                sample_number="P-B1-AMI-001",
                pollutant_type="asbestos",
                material_category="flocage",
                location_description="Sous-sol, local technique",
                concentration=18.0,
                unit="percent_weight",
                threshold_exceeded=True,
                risk_level="high",
                cfst_work_category="major",
                action_required="remove_planned",
                waste_disposal_type="type_e",
            ),
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=B1_DIAG_ASBESTOS_ID,
                sample_number="P-B1-AMI-002",
                pollutant_type="asbestos",
                material_category="colle_carrelage",
                location_description="Rez-de-chaussee, cuisine",
                concentration=2.5,
                unit="percent_weight",
                threshold_exceeded=True,
                risk_level="medium",
                cfst_work_category="medium",
                action_required="remove_planned",
                waste_disposal_type="type_e",
            ),
        ]
    )

    db.add(
        Diagnostic(
            id=B1_DIAG_PCB_ID,
            building_id=B1_ID,
            diagnostic_type="pcb",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2024, 9, 15),
            date_report=date(2024, 10, 1),
            laboratory="EnviroLab Suisse",
        )
    )
    db.add(
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=B1_DIAG_PCB_ID,
            sample_number="P-B1-PCB-001",
            pollutant_type="pcb",
            material_category="joint_etancheite",
            location_description="Facade nord",
            concentration=72.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            action_required="remove_planned",
            waste_disposal_type="type_e",
        )
    )

    # Documents for B1
    db.add_all(
        [
            Document(
                id=uuid.uuid4(),
                building_id=B1_ID,
                file_path="/docs/prospect/b1_rapport_amiante_2021.pdf",
                file_name="rapport_amiante_2021.pdf",
                document_type="diagnostic_report",
                file_size_bytes=2_400_000,
            ),
            Document(
                id=uuid.uuid4(),
                building_id=B1_ID,
                file_path="/docs/prospect/b1_rapport_pcb_2024.pdf",
                file_name="rapport_pcb_2024.pdf",
                document_type="diagnostic_report",
                file_size_bytes=1_600_000,
            ),
        ]
    )
    # NOTE: No waste_elimination_plan for B1

    # Actions for B1
    db.add_all(
        [
            ActionItem(
                id=uuid.uuid4(),
                building_id=B1_ID,
                source_type="diagnostic",
                action_type="notification",
                title="Notifier la SUVA pour amiante positif",
                description="Echantillons P-B1-AMI-001 et 002 positifs, notification SUVA obligatoire",
                priority="critical",
                status="open",
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=B1_ID,
                source_type="diagnostic",
                action_type="documentation",
                title="Etablir le plan de gestion des dechets",
                description="Aucun plan d'elimination disponible -- requis avant travaux (OLED)",
                priority="high",
                status="open",
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=B1_ID,
                source_type="readiness",
                action_type="investigation",
                title="Renouveler le diagnostic amiante expire",
                description="Le diagnostic amiante date de 2021 (> 3 ans). A renouveler.",
                priority="high",
                status="open",
            ),
        ]
    )

    # ==================================================================
    # Building 2: Ready -- all diagnostics valid, all docs present
    # ==================================================================
    db.add(
        Diagnostic(
            id=B2_DIAG_ASBESTOS_ID,
            building_id=B2_ID,
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2024, 3, 20),
            date_report=date(2024, 4, 10),
            laboratory="Analytica SA",
            suva_notification_required=True,
            suva_notification_date=date(2024, 4, 25),
        )
    )
    db.add_all(
        [
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=B2_DIAG_ASBESTOS_ID,
                sample_number="P-B2-AMI-001",
                pollutant_type="asbestos",
                material_category="colle_carrelage",
                location_description="Sous-sol, buanderie",
                concentration=4.0,
                unit="percent_weight",
                threshold_exceeded=True,
                risk_level="medium",
                cfst_work_category="medium",
                action_required="remove_planned",
                waste_disposal_type="type_e",
            ),
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=B2_DIAG_ASBESTOS_ID,
                sample_number="P-B2-AMI-002",
                pollutant_type="asbestos",
                material_category="joint_fenetre",
                location_description="Etage 1, salon",
                concentration=0.2,
                unit="percent_weight",
                threshold_exceeded=False,
                risk_level="low",
                action_required="none",
            ),
        ]
    )

    db.add(
        Diagnostic(
            id=B2_DIAG_PCB_ID,
            building_id=B2_ID,
            diagnostic_type="pcb",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2024, 3, 22),
            date_report=date(2024, 4, 12),
            laboratory="EnviroLab Suisse",
        )
    )
    db.add(
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=B2_DIAG_PCB_ID,
            sample_number="P-B2-PCB-001",
            pollutant_type="pcb",
            material_category="condensateur",
            location_description="Sous-sol, local technique",
            concentration=8.0,
            unit="mg_per_kg",
            threshold_exceeded=False,
            risk_level="low",
            action_required="none",
        )
    )

    db.add(
        Diagnostic(
            id=B2_DIAG_LEAD_ID,
            building_id=B2_ID,
            diagnostic_type="lead",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2024, 3, 25),
            date_report=date(2024, 4, 15),
            laboratory="EnviroLab Suisse",
        )
    )
    db.add(
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=B2_DIAG_LEAD_ID,
            sample_number="P-B2-PB-001",
            pollutant_type="lead",
            material_category="peinture",
            location_description="Etage 2, chambre",
            concentration=1200.0,
            unit="mg_per_kg",
            threshold_exceeded=False,
            risk_level="low",
            action_required="none",
        )
    )

    # Documents for B2 (complete set)
    db.add_all(
        [
            Document(
                id=uuid.uuid4(),
                building_id=B2_ID,
                file_path="/docs/prospect/b2_rapport_amiante_2024.pdf",
                file_name="rapport_amiante_2024.pdf",
                document_type="diagnostic_report",
                file_size_bytes=2_100_000,
            ),
            Document(
                id=uuid.uuid4(),
                building_id=B2_ID,
                file_path="/docs/prospect/b2_rapport_pcb_2024.pdf",
                file_name="rapport_pcb_2024.pdf",
                document_type="diagnostic_report",
                file_size_bytes=1_500_000,
            ),
            Document(
                id=uuid.uuid4(),
                building_id=B2_ID,
                file_path="/docs/prospect/b2_rapport_plomb_2024.pdf",
                file_name="rapport_plomb_2024.pdf",
                document_type="diagnostic_report",
                file_size_bytes=1_200_000,
            ),
            Document(
                id=uuid.uuid4(),
                building_id=B2_ID,
                file_path="/docs/prospect/b2_plan_elimination_dechets.pdf",
                file_name="plan_elimination_dechets.pdf",
                document_type="waste_elimination_plan",
                file_size_bytes=800_000,
            ),
            Document(
                id=uuid.uuid4(),
                building_id=B2_ID,
                file_path="/docs/prospect/b2_notification_suva.pdf",
                file_name="notification_suva.pdf",
                document_type="suva_notification",
                file_size_bytes=350_000,
            ),
        ]
    )

    # B2: 1 completed action (already done)
    db.add(
        ActionItem(
            id=uuid.uuid4(),
            building_id=B2_ID,
            source_type="diagnostic",
            action_type="notification",
            title="Notifier la SUVA",
            description="Notification SUVA effectuee le 25.04.2024",
            priority="critical",
            status="done",
            completed_at=datetime(2024, 4, 25, tzinfo=UTC),
        )
    )

    # ==================================================================
    # Building 3: Not assessed (new acquisition, no diagnostics)
    # ==================================================================
    # No diagnostics, no documents, just the building record
    db.add(
        ActionItem(
            id=uuid.uuid4(),
            building_id=B3_ID,
            source_type="system",
            action_type="investigation",
            title="Lancer un diagnostic initial",
            description="Batiment nouvellement acquis. Aucun diagnostic existant.",
            priority="high",
            status="open",
        )
    )

    # ==================================================================
    # Building 4: Pack submitted, awaiting acknowledgment
    # ==================================================================
    db.add(
        Diagnostic(
            id=B4_DIAG_ASBESTOS_ID,
            building_id=B4_ID,
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2024, 1, 10),
            date_report=date(2024, 2, 1),
            laboratory="Analytica SA",
            suva_notification_required=True,
            suva_notification_date=date(2024, 2, 20),
        )
    )
    db.add(
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=B4_DIAG_ASBESTOS_ID,
            sample_number="P-B4-AMI-001",
            pollutant_type="asbestos",
            material_category="flocage",
            location_description="Sous-sol, gaine technique",
            concentration=30.0,
            unit="percent_weight",
            threshold_exceeded=True,
            risk_level="high",
            cfst_work_category="major",
            action_required="remove_planned",
            waste_disposal_type="type_e",
        )
    )

    db.add(
        Diagnostic(
            id=B4_DIAG_PCB_ID,
            building_id=B4_ID,
            diagnostic_type="pcb",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2024, 1, 12),
            date_report=date(2024, 2, 5),
            laboratory="EnviroLab Suisse",
        )
    )
    db.add(
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=B4_DIAG_PCB_ID,
            sample_number="P-B4-PCB-001",
            pollutant_type="pcb",
            material_category="joint_etancheite",
            location_description="Facade ouest",
            concentration=120.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            risk_level="high",
            action_required="remove_planned",
            waste_disposal_type="type_e",
        )
    )

    # Documents for B4 (complete)
    db.add_all(
        [
            Document(
                id=uuid.uuid4(),
                building_id=B4_ID,
                file_path="/docs/prospect/b4_rapport_amiante_2024.pdf",
                file_name="rapport_amiante_2024.pdf",
                document_type="diagnostic_report",
                file_size_bytes=2_300_000,
            ),
            Document(
                id=uuid.uuid4(),
                building_id=B4_ID,
                file_path="/docs/prospect/b4_rapport_pcb_2024.pdf",
                file_name="rapport_pcb_2024.pdf",
                document_type="diagnostic_report",
                file_size_bytes=1_700_000,
            ),
            Document(
                id=uuid.uuid4(),
                building_id=B4_ID,
                file_path="/docs/prospect/b4_plan_elimination.pdf",
                file_name="plan_elimination_dechets.pdf",
                document_type="waste_elimination_plan",
                file_size_bytes=750_000,
            ),
        ]
    )

    # B4: Evidence pack -- submitted
    submitted_at = datetime.now(UTC) - timedelta(days=5)
    db.add(
        EvidencePack(
            id=B4_PACK_ID,
            building_id=B4_ID,
            pack_type="authority_pack",
            title="Pack autorite -- Place St-Francois 3",
            status="submitted",
            assembled_at=submitted_at - timedelta(hours=2),
            submitted_at=submitted_at,
            created_by=PROSPECT_USER_RT_ID,
        )
    )

    # B4: Case -- authority submission
    db.add(
        BuildingCase(
            id=B4_CASE_ID,
            building_id=B4_ID,
            organization_id=PROSPECT_ORG_ID,
            created_by_id=PROSPECT_USER_RT_ID,
            case_type="authority_submission",
            title="Soumission autorite -- amiante + PCB",
            state="in_progress",
            pollutant_scope=["asbestos", "pcb"],
            canton="VD",
            authority="DIREN VD",
            priority="high",
        )
    )

    # B4: Actions (all done)
    db.add_all(
        [
            ActionItem(
                id=uuid.uuid4(),
                building_id=B4_ID,
                source_type="diagnostic",
                action_type="notification",
                title="Notifier la SUVA",
                priority="critical",
                status="done",
                completed_at=datetime(2024, 2, 20, tzinfo=UTC),
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=B4_ID,
                source_type="diagnostic",
                action_type="documentation",
                title="Plan d'elimination des dechets",
                priority="high",
                status="done",
                completed_at=datetime(2024, 3, 5, tzinfo=UTC),
            ),
        ]
    )

    # ==================================================================
    # Building 5: Complement requested (authority returned dossier)
    # ==================================================================
    db.add(
        Diagnostic(
            id=B5_DIAG_ASBESTOS_ID,
            building_id=B5_ID,
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2024, 6, 1),
            date_report=date(2024, 6, 20),
            laboratory="Analytica SA",
            suva_notification_required=True,
            suva_notification_date=date(2024, 7, 5),
        )
    )
    db.add_all(
        [
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=B5_DIAG_ASBESTOS_ID,
                sample_number="P-B5-AMI-001",
                pollutant_type="asbestos",
                material_category="flocage",
                location_description="Sous-sol, plafond parking",
                concentration=22.0,
                unit="percent_weight",
                threshold_exceeded=True,
                risk_level="high",
                cfst_work_category="major",
                action_required="remove_planned",
                waste_disposal_type="type_e",
            ),
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=B5_DIAG_ASBESTOS_ID,
                sample_number="P-B5-AMI-002",
                pollutant_type="asbestos",
                material_category="dalles_vinyl",
                location_description="Rez-de-chaussee, hall d'entree",
                concentration=6.0,
                unit="percent_weight",
                threshold_exceeded=True,
                risk_level="medium",
                cfst_work_category="medium",
                action_required="remove_planned",
                waste_disposal_type="type_e",
            ),
        ]
    )

    # Documents for B5
    db.add_all(
        [
            Document(
                id=uuid.uuid4(),
                building_id=B5_ID,
                file_path="/docs/prospect/b5_rapport_amiante_2024.pdf",
                file_name="rapport_amiante_2024.pdf",
                document_type="diagnostic_report",
                file_size_bytes=2_000_000,
            ),
            Document(
                id=uuid.uuid4(),
                building_id=B5_ID,
                file_path="/docs/prospect/b5_plan_elimination.pdf",
                file_name="plan_elimination_dechets.pdf",
                document_type="waste_elimination_plan",
                file_size_bytes=600_000,
            ),
        ]
    )

    # B5: Evidence pack -- complement requested
    complement_at = datetime.now(UTC) - timedelta(days=3)
    complement_notes = json.dumps(
        {
            "complement_requested": True,
            "complement_details": "Le diagnostic PCB est manquant pour ce type de batiment (construction avant 1975). Veuillez fournir un diagnostic PCB complet.",
            "complement_requested_at": (complement_at).isoformat(),
        },
        default=str,
    )
    db.add(
        EvidencePack(
            id=B5_PACK_ID,
            building_id=B5_ID,
            pack_type="authority_pack",
            title="Pack autorite -- Rue du Petit-Chene 21",
            status="submitted",
            assembled_at=complement_at - timedelta(days=5),
            submitted_at=complement_at - timedelta(days=4),
            notes=complement_notes,
            created_by=PROSPECT_USER_RT_ID,
        )
    )

    # B5: Case -- authority submission with complement
    db.add(
        BuildingCase(
            id=B5_CASE_ID,
            building_id=B5_ID,
            organization_id=PROSPECT_ORG_ID,
            created_by_id=PROSPECT_USER_RT_ID,
            case_type="authority_submission",
            title="Soumission autorite -- amiante (complement PCB demande)",
            state="blocked",
            pollutant_scope=["asbestos"],
            canton="VD",
            authority="DIREN VD",
            priority="high",
        )
    )

    # B5: Actions (mix of done and open due to complement)
    db.add_all(
        [
            ActionItem(
                id=uuid.uuid4(),
                building_id=B5_ID,
                source_type="diagnostic",
                action_type="notification",
                title="Notifier la SUVA",
                priority="critical",
                status="done",
                completed_at=datetime(2024, 7, 5, tzinfo=UTC),
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=B5_ID,
                source_type="dossier_workflow",
                action_type="documentation",
                title="Complement autorite requis",
                description="Le diagnostic PCB est manquant. Fournir un diagnostic PCB complet.",
                priority="high",
                status="open",
            ),
            ActionItem(
                id=uuid.uuid4(),
                building_id=B5_ID,
                source_type="diagnostic",
                action_type="investigation",
                title="Planifier diagnostic PCB",
                description="Batiment construit en 1955, diagnostic PCB obligatoire.",
                priority="high",
                status="open",
            ),
        ]
    )

    await db.commit()

    summary = {
        "status": "seeded",
        "org_id": str(PROSPECT_ORG_ID),
        "org_name": "Regie Pilote SA",
        "users": 2,
        "buildings": 5,
        "building_ids": [str(b) for b in [B1_ID, B2_ID, B3_ID, B4_ID, B5_ID]],
        "building_states": {
            "Rue de Bourg 12": "partially_ready",
            "Avenue d'Ouchy 45": "ready",
            "Chemin des Vignes 8": "not_assessed",
            "Place St-Francois 3": "submitted",
            "Rue du Petit-Chene 21": "complement_requested",
        },
        "diagnostics": 8,
        "documents": 10,
        "actions": 12,
        "packs": 2,
        "cases": 2,
    }
    logger.info("Prospect scenario seeded: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


async def _main():
    from app.database import async_session_factory

    async with async_session_factory() as db:
        result = await seed_prospect_scenario(db)
        print(f"Prospect scenario seed result: {result}")


if __name__ == "__main__":
    asyncio.run(_main())
