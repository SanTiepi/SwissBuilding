"""Seed: T1 Transaction-Ready Dossier scenario.

One VD building preparing for sale:
- 1968 construction, partially renovated
- Valid asbestos diagnostic (clear)
- Valid PCB diagnostic (traces in joint material)
- No lead diagnostic (missing -- blocks transaction)
- One unresolved incident (minor water damage, cosmetic)
- Ownership documented
- 2 caveats: PCB traces, missing lead diagnostic
- Expected verdict: conditional (missing lead diagnostic)
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.commitment import Caveat
from app.models.contact import Contact
from app.models.diagnostic import Diagnostic
from app.models.incident import IncidentEpisode
from app.models.organization import Organization
from app.models.ownership_record import OwnershipRecord
from app.models.sample import Sample
from app.models.user import User

logger = logging.getLogger(__name__)

SCENARIO_TAG = "t1_transaction"


async def seed_t1_scenario(db: AsyncSession) -> dict:
    """Seed the T1 transaction-readiness scenario.

    Idempotent: checks for existing building by address before creating.
    Returns dict with created entity IDs.
    """
    # Check idempotency
    existing = await db.execute(select(Building).where(Building.address == "Route de Berne 18"))
    if existing.scalar_one_or_none():
        logger.info("T1 scenario already seeded, skipping")
        return {"status": "already_seeded"}

    # Get or create admin user
    admin_result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
    admin = admin_result.scalar_one_or_none()
    if not admin:
        logger.warning("Admin user not found, creating minimal user for seed")
        admin = User(
            id=uuid.uuid4(),
            email="admin@swissbuildingos.ch",
            password_hash="$2b$12$placeholder",
            first_name="Admin",
            last_name="Seed",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.flush()

    # Get or create org
    org_result = await db.execute(select(Organization).where(Organization.name == "Regie Vaudoise SA"))
    org = org_result.scalar_one_or_none()
    if not org:
        org = Organization(
            id=uuid.uuid4(),
            name="Regie Vaudoise SA",
            type="property_management",
        )
        db.add(org)
        await db.flush()

    # Building: VD, 1968, partially renovated
    building_id = uuid.uuid4()
    building = Building(
        id=building_id,
        address="Route de Berne 18",
        postal_code="1010",
        city="Lausanne",
        canton="VD",
        construction_year=1968,
        renovation_year=2019,
        building_type="residential",
        floors_above=6,
        floors_below=1,
        surface_area_m2=1850.0,
        created_by=admin.id,
        status="active",
        organization_id=org.id,
    )
    db.add(building)

    # Owner contact
    contact = Contact(
        id=uuid.uuid4(),
        name="Pierre Dumont",
        email="p.dumont@example.ch",
        phone="+41 21 555 00 01",
        contact_type="owner",
        organization_id=org.id,
    )
    db.add(contact)
    await db.flush()

    # Ownership record
    ownership = OwnershipRecord(
        id=uuid.uuid4(),
        building_id=building_id,
        owner_type="contact",
        owner_id=contact.id,
        ownership_type="full",
        acquisition_type="purchase",
        acquisition_date=date(2015, 3, 1),
        status="active",
    )
    db.add(ownership)

    # Diagnostic 1: Asbestos (completed, clear)
    diag_asbestos_id = uuid.uuid4()
    diag_asbestos = Diagnostic(
        id=diag_asbestos_id,
        building_id=building_id,
        diagnostic_type="full",
        diagnostic_context="AvT",
        status="completed",
        date_inspection=date(2024, 6, 15),
    )
    db.add(diag_asbestos)
    await db.flush()

    sample_asbestos = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag_asbestos_id,
        sample_number="T1-ASB-001",
        pollutant_type="asbestos",
        concentration=0.0,
        unit="percent_weight",
        risk_level="low",
        threshold_exceeded=False,
        cfst_work_category=None,
        action_required="none",
        material_category="Joint de facade",
        location_description="Facade est, 3eme etage",
    )
    db.add(sample_asbestos)

    # Diagnostic 2: PCB (completed, traces found)
    diag_pcb_id = uuid.uuid4()
    diag_pcb = Diagnostic(
        id=diag_pcb_id,
        building_id=building_id,
        diagnostic_type="full",
        diagnostic_context="AvT",
        status="completed",
        date_inspection=date(2024, 6, 15),
    )
    db.add(diag_pcb)
    await db.flush()

    sample_pcb = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag_pcb_id,
        sample_number="T1-PCB-001",
        pollutant_type="pcb",
        concentration=35.0,
        unit="mg_per_kg",
        risk_level="medium",
        threshold_exceeded=False,  # below 50 mg/kg ORRChim threshold
        cfst_work_category="minor",
        action_required="monitor",
        material_category="Joint d'etancheite",
        location_description="Joints fenetre, facade nord",
    )
    db.add(sample_pcb)

    # NO lead diagnostic -- this is the gap that blocks the transaction

    # Incident: minor water damage (unresolved, cosmetic)
    incident = IncidentEpisode(
        id=uuid.uuid4(),
        building_id=building_id,
        organization_id=org.id,
        incident_type="water_damage",
        title="Degat d'eau mineur - sous-sol",
        severity="minor",
        status="reported",
        discovered_at=datetime(2025, 11, 1, tzinfo=UTC),
        created_by=admin.id,
    )
    db.add(incident)

    # Caveat 1: PCB traces
    caveat_pcb = Caveat(
        id=uuid.uuid4(),
        building_id=building_id,
        caveat_type="data_quality_warning",
        subject="Traces de PCB dans les joints d'etancheite",
        description=(
            "Concentration PCB de 35 mg/kg detectee dans les joints d'etancheite. "
            "En dessous du seuil ORRChim (50 mg/kg) mais surveillance recommandee."
        ),
        severity="warning",
        applies_to_pack_types=["transfer", "insurer"],
        applies_to_audiences=["buyer", "insurer"],
        source_type="system_generated",
        active=True,
    )
    db.add(caveat_pcb)

    # Caveat 2: Missing lead diagnostic
    caveat_lead = Caveat(
        id=uuid.uuid4(),
        building_id=building_id,
        caveat_type="coverage_gap",
        subject="Diagnostic plomb manquant",
        description=(
            "Aucun diagnostic plomb n'a ete realise pour ce batiment de 1968. "
            "Le plomb est un polluant reglemente pour les batiments construits avant 2006."
        ),
        severity="warning",
        applies_to_pack_types=["transfer", "authority"],
        applies_to_audiences=["buyer", "authority"],
        source_type="system_generated",
        active=True,
    )
    db.add(caveat_lead)

    await db.commit()

    logger.info("T1 scenario seeded: building %s (Route de Berne 18, Lausanne)", building_id)
    return {
        "status": "created",
        "building_id": str(building_id),
        "diagnostics": {
            "asbestos": str(diag_asbestos_id),
            "pcb": str(diag_pcb_id),
        },
        "caveats": 2,
        "incidents": 1,
        "ownership": True,
        "expected_verdict": "conditional",
    }
