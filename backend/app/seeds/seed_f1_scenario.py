"""Seed scenario for F1 -- Finance/Lender-Ready Dossier.

One building preparing for finance/lending review:
- VD building, 1960, commercial
- Valid asbestos diagnostic (clear after remediation)
- Valid PCB diagnostic (clear)
- Missing energy performance certificate (CECB/GEAK)
- Ownership documented but with pending co-ownership question
- 1 resolved structural incident (foundation repair, CHF 45k)
- High completeness but weak trust on valuation
- 1 caveat: co-ownership question unresolved
- Expected verdict: conditional (co-ownership question + missing energy cert)

Idempotent: uses fixed UUIDs.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.commitment import Caveat
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.incident import IncidentEpisode
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.unknowns_ledger import UnknownEntry

# Fixed UUIDs for idempotency
_ORG_ID = uuid.UUID("f1a2b3c4-0001-4000-8000-000000000001")
_BUILDING_ID = uuid.UUID("f1a2b3c4-0002-4000-8000-000000000001")
_DIAG_ASBESTOS_ID = uuid.UUID("f1a2b3c4-0003-4000-8000-000000000001")
_DIAG_PCB_ID = uuid.UUID("f1a2b3c4-0003-4000-8000-000000000002")
_SAMPLE_ASB_1 = uuid.UUID("f1a2b3c4-0004-4000-8000-000000000001")
_SAMPLE_PCB_1 = uuid.UUID("f1a2b3c4-0004-4000-8000-000000000002")
_INCIDENT_FOUNDATION = uuid.UUID("f1a2b3c4-0005-4000-8000-000000000001")
_CAVEAT_COOWNERSHIP = uuid.UUID("f1a2b3c4-0007-4000-8000-000000000001")
_UNKNOWN_ENERGY = uuid.UUID("f1a2b3c4-0008-4000-8000-000000000001")
_CONTRADICTION_VALUATION = uuid.UUID("f1a2b3c4-0009-4000-8000-000000000001")


async def _exists(db: AsyncSession, model, id_val: uuid.UUID) -> bool:
    result = await db.execute(select(model).where(model.id == id_val))
    return result.scalar_one_or_none() is not None


async def seed_f1_scenario(db: AsyncSession, created_by_id: uuid.UUID | None = None) -> dict:
    """Seed the F1 finance readiness scenario. Idempotent."""
    created = []

    # 1. Organization
    if not await _exists(db, Organization, _ORG_ID):
        org = Organization(
            id=_ORG_ID,
            name="Regie Finance Demo SA",
            type="property_management",
        )
        db.add(org)
        created.append("organization")

    # 2. Building -- VD, 1960, commercial
    if not await _exists(db, Building, _BUILDING_ID):
        building = Building(
            id=_BUILDING_ID,
            address="Rue du Credit 8",
            postal_code="1003",
            city="Lausanne",
            canton="VD",
            construction_year=1960,
            building_type="commercial",
            status="active",
            organization_id=_ORG_ID,
            created_by=created_by_id,
        )
        db.add(building)
        created.append("building")

    # 3. Asbestos diagnostic -- completed, clear after remediation
    if not await _exists(db, Diagnostic, _DIAG_ASBESTOS_ID):
        db.add(
            Diagnostic(
                id=_DIAG_ASBESTOS_ID,
                building_id=_BUILDING_ID,
                diagnostic_type="asbestos",
                diagnostic_context="AvT",
                status="completed",
                date_inspection=date(2025, 3, 20),
            )
        )
        created.append("diagnostic_asbestos")

    # Asbestos sample: clear (post-remediation)
    if not await _exists(db, Sample, _SAMPLE_ASB_1):
        db.add(
            Sample(
                id=_SAMPLE_ASB_1,
                diagnostic_id=_DIAG_ASBESTOS_ID,
                sample_number="F1-ASB-001",
                pollutant_type="asbestos",
                concentration=0.0,
                unit="percent_weight",
                risk_level="low",
                threshold_exceeded=False,
                location="Ensemble du batiment (post-assainissement)",
            )
        )
        created.append("sample_asb_clear")

    # 4. PCB diagnostic -- completed, clear
    if not await _exists(db, Diagnostic, _DIAG_PCB_ID):
        db.add(
            Diagnostic(
                id=_DIAG_PCB_ID,
                building_id=_BUILDING_ID,
                diagnostic_type="pcb",
                diagnostic_context="AvT",
                status="completed",
                date_inspection=date(2025, 4, 10),
            )
        )
        created.append("diagnostic_pcb")

    if not await _exists(db, Sample, _SAMPLE_PCB_1):
        db.add(
            Sample(
                id=_SAMPLE_PCB_1,
                diagnostic_id=_DIAG_PCB_ID,
                sample_number="F1-PCB-001",
                pollutant_type="pcb",
                concentration=3.0,
                unit="mg_per_kg",
                risk_level="low",
                threshold_exceeded=False,
                location="Joints facade nord",
            )
        )
        created.append("sample_pcb_clear")

    # 5. Incident: foundation repair (resolved, CHF 45k)
    if not await _exists(db, IncidentEpisode, _INCIDENT_FOUNDATION):
        db.add(
            IncidentEpisode(
                id=_INCIDENT_FOUNDATION,
                building_id=_BUILDING_ID,
                organization_id=_ORG_ID,
                incident_type="structural",
                title="Reparation fondations -- fissures portantes",
                description="Fissures detectees dans les fondations. Reparation structurelle realisee.",
                severity="major",
                status="resolved",
                discovered_at=datetime(2024, 6, 1, tzinfo=UTC),
                resolved_at=datetime(2024, 11, 15, tzinfo=UTC),
                response_description="Injection resine + renfort acier. Controle OK par ingenieur.",
                repair_cost_chf=45000.0,
                insurance_claim_filed=False,
                cause_category="wear",
                location_description="Fondations, facade ouest",
                created_by=created_by_id,
            )
        )
        created.append("incident_foundation_resolved")

    # 6. Caveat: co-ownership question unresolved
    if not await _exists(db, Caveat, _CAVEAT_COOWNERSHIP):
        db.add(
            Caveat(
                id=_CAVEAT_COOWNERSHIP,
                building_id=_BUILDING_ID,
                caveat_type="scope_limitation",
                subject="Question de copropriete non resolue",
                description="La repartition de copropriete est contestee par un co-proprietaire. "
                "Impact potentiel sur la garantie hypothecaire.",
                severity="warning",
                applies_to_pack_types=["owner", "lender"],
                applies_to_audiences=["lender"],
                source_type="system_generated",
                active=True,
            )
        )
        created.append("caveat_coownership")

    # 7. Unknown: missing energy performance certificate
    if not await _exists(db, UnknownEntry, _UNKNOWN_ENERGY):
        db.add(
            UnknownEntry(
                id=_UNKNOWN_ENERGY,
                building_id=_BUILDING_ID,
                unknown_type="coverage_gap",
                subject="Certificat energetique (CECB/GEAK) manquant",
                description="Aucun certificat energetique disponible. Requis pour evaluation financiere.",
                severity="high",
                status="open",
            )
        )
        created.append("unknown_energy_cert")

    # 8. Contradiction: valuation discrepancy
    if not await _exists(db, DataQualityIssue, _CONTRADICTION_VALUATION):
        db.add(
            DataQualityIssue(
                id=_CONTRADICTION_VALUATION,
                building_id=_BUILDING_ID,
                issue_type="contradiction",
                description="Ecart significatif entre valeur fiscale et estimation recente",
                severity="medium",
                status="open",
                detected_by="contradiction_detector",
            )
        )
        created.append("contradiction_valuation")

    await db.commit()

    return {
        "scenario": "f1_finance_readiness",
        "building_id": str(_BUILDING_ID),
        "org_id": str(_ORG_ID),
        "created": created,
        "expected_verdict": "conditional",
    }
