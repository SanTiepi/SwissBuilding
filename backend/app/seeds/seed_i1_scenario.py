"""Seed scenario for I1 -- Insurance-Ready Dossier.

One building preparing for insurance review:
- VD building, 1975, residential
- Valid asbestos diagnostic (traces found in 1 location -- managed)
- Valid PCB diagnostic (clear)
- No radon measurement (unknown -- coverage gap)
- 2 incidents: water damage (resolved, CHF 8000) + recurring mold (unresolved)
- 1 insurance claim filed for the water damage
- 1 caveat: radon coverage gap
- 1 caveat: recurring mold pattern
- Expected verdict: conditional (unresolved incident + radon unknown)

Idempotent: uses fixed UUIDs.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.commitment import Caveat
from app.models.diagnostic import Diagnostic
from app.models.incident import IncidentEpisode
from app.models.organization import Organization
from app.models.sample import Sample

# Fixed UUIDs for idempotency
_ORG_ID = uuid.UUID("a1b2c3d4-0001-4000-8000-000000000001")
_BUILDING_ID = uuid.UUID("a1b2c3d4-0002-4000-8000-000000000001")
_DIAG_ASBESTOS_ID = uuid.UUID("a1b2c3d4-0003-4000-8000-000000000001")
_DIAG_PCB_ID = uuid.UUID("a1b2c3d4-0003-4000-8000-000000000002")
_SAMPLE_ASB_1 = uuid.UUID("a1b2c3d4-0004-4000-8000-000000000001")
_SAMPLE_ASB_2 = uuid.UUID("a1b2c3d4-0004-4000-8000-000000000002")
_SAMPLE_PCB_1 = uuid.UUID("a1b2c3d4-0004-4000-8000-000000000003")
_INCIDENT_WATER = uuid.UUID("a1b2c3d4-0005-4000-8000-000000000001")
_INCIDENT_MOLD = uuid.UUID("a1b2c3d4-0005-4000-8000-000000000002")
_CAVEAT_RADON = uuid.UUID("a1b2c3d4-0007-4000-8000-000000000001")
_CAVEAT_MOLD = uuid.UUID("a1b2c3d4-0007-4000-8000-000000000002")


async def _exists(db: AsyncSession, model, id_val: uuid.UUID) -> bool:
    result = await db.execute(select(model).where(model.id == id_val))
    return result.scalar_one_or_none() is not None


async def seed_i1_scenario(db: AsyncSession, created_by_id: uuid.UUID | None = None) -> dict:
    """Seed the I1 insurance readiness scenario. Idempotent."""
    created = []

    # 1. Organization
    if not await _exists(db, Organization, _ORG_ID):
        org = Organization(
            id=_ORG_ID,
            name="Regie Assurance Demo SA",
            type="property_management",
        )
        db.add(org)
        created.append("organization")

    # 2. Building -- VD, 1975, residential
    if not await _exists(db, Building, _BUILDING_ID):
        building = Building(
            id=_BUILDING_ID,
            address="Chemin des Assurances 12",
            postal_code="1003",
            city="Lausanne",
            canton="VD",
            construction_year=1975,
            building_type="residential",
            status="active",
            organization_id=_ORG_ID,
            created_by=created_by_id,
        )
        db.add(building)
        created.append("building")

    # 3. Asbestos diagnostic -- completed, traces found
    if not await _exists(db, Diagnostic, _DIAG_ASBESTOS_ID):
        diag_asb = Diagnostic(
            id=_DIAG_ASBESTOS_ID,
            building_id=_BUILDING_ID,
            diagnostic_type="asbestos",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2025, 6, 15),
        )
        db.add(diag_asb)
        created.append("diagnostic_asbestos")

    # Asbestos samples: one clear, one with traces (managed)
    if not await _exists(db, Sample, _SAMPLE_ASB_1):
        db.add(
            Sample(
                id=_SAMPLE_ASB_1,
                diagnostic_id=_DIAG_ASBESTOS_ID,
                sample_number="I1-ASB-001",
                pollutant_type="asbestos",
                concentration=0.0,
                unit="percent_weight",
                risk_level="low",
                threshold_exceeded=False,
                location="Sous-sol, local technique",
            )
        )
        created.append("sample_asb_clear")

    if not await _exists(db, Sample, _SAMPLE_ASB_2):
        db.add(
            Sample(
                id=_SAMPLE_ASB_2,
                diagnostic_id=_DIAG_ASBESTOS_ID,
                sample_number="I1-ASB-002",
                pollutant_type="asbestos",
                concentration=2.5,
                unit="percent_weight",
                risk_level="medium",
                threshold_exceeded=False,  # traces, managed in place
                location="2eme etage, faux plafond",
            )
        )
        created.append("sample_asb_traces")

    # 4. PCB diagnostic -- completed, clear
    if not await _exists(db, Diagnostic, _DIAG_PCB_ID):
        diag_pcb = Diagnostic(
            id=_DIAG_PCB_ID,
            building_id=_BUILDING_ID,
            diagnostic_type="pcb",
            diagnostic_context="AvT",
            status="completed",
            date_inspection=date(2025, 7, 10),
        )
        db.add(diag_pcb)
        created.append("diagnostic_pcb")

    if not await _exists(db, Sample, _SAMPLE_PCB_1):
        db.add(
            Sample(
                id=_SAMPLE_PCB_1,
                diagnostic_id=_DIAG_PCB_ID,
                sample_number="I1-PCB-001",
                pollutant_type="pcb",
                concentration=5.0,
                unit="mg_per_kg",
                risk_level="low",
                threshold_exceeded=False,
                location="Joints facade est",
            )
        )
        created.append("sample_pcb_clear")

    # 5. Incident: water damage (resolved, claim filed)
    if not await _exists(db, IncidentEpisode, _INCIDENT_WATER):
        db.add(
            IncidentEpisode(
                id=_INCIDENT_WATER,
                building_id=_BUILDING_ID,
                organization_id=_ORG_ID,
                incident_type="flooding",
                title="Degat d'eau -- cave inondee",
                description="Rupture de canalisation causant une inondation de la cave.",
                severity="major",
                status="resolved",
                discovered_at=datetime(2025, 9, 15, tzinfo=UTC),
                resolved_at=datetime(2025, 10, 5, tzinfo=UTC),
                response_description="Canalisation reparee, cave assechee et desinfectee.",
                repair_cost_chf=8000.0,
                insurance_claim_filed=True,
                cause_category="wear",
                location_description="Cave, local stockage",
                created_by=created_by_id,
            )
        )
        created.append("incident_water_resolved")

    # 6. Incident: recurring mold (unresolved)
    if not await _exists(db, IncidentEpisode, _INCIDENT_MOLD):
        db.add(
            IncidentEpisode(
                id=_INCIDENT_MOLD,
                building_id=_BUILDING_ID,
                organization_id=_ORG_ID,
                incident_type="mold",
                title="Moisissure recurrente -- salle de bain 3eme",
                description="Moisissure reapparait malgre traitement precedent. Ventilation insuffisante.",
                severity="moderate",
                status="recurring_unresolved",
                discovered_at=datetime(2025, 11, 1, tzinfo=UTC),
                recurring=True,
                cause_category="defect",
                occupant_impact=True,
                location_description="3eme etage, salle de bain apt 3.2",
                created_by=created_by_id,
            )
        )
        created.append("incident_mold_recurring")

    # 7. Caveat: radon coverage gap
    if not await _exists(db, Caveat, _CAVEAT_RADON):
        db.add(
            Caveat(
                id=_CAVEAT_RADON,
                building_id=_BUILDING_ID,
                caveat_type="coverage_gap",
                subject="Mesure radon manquante",
                description="Aucune mesure de radon n'a ete effectuee. Lacune pour l'assurance.",
                severity="warning",
                applies_to_pack_types=["insurer", "authority"],
                applies_to_audiences=["insurer"],
                source_type="system_generated",
                active=True,
            )
        )
        created.append("caveat_radon")

    # 8. Caveat: recurring mold pattern
    if not await _exists(db, Caveat, _CAVEAT_MOLD):
        db.add(
            Caveat(
                id=_CAVEAT_MOLD,
                building_id=_BUILDING_ID,
                caveat_type="insurer_exclusion",
                subject="Schema de moisissure recurrente",
                description="Moisissure recurrente au 3eme etage. Exclusion potentielle de la couverture.",
                severity="warning",
                applies_to_pack_types=["insurer"],
                applies_to_audiences=["insurer"],
                source_type="system_generated",
                active=True,
            )
        )
        created.append("caveat_mold")

    await db.commit()

    return {
        "scenario": "i1_insurance_readiness",
        "building_id": str(_BUILDING_ID),
        "org_id": str(_ORG_ID),
        "created": created,
        "expected_verdict": "conditional",
    }
