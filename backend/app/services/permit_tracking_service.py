"""Permit tracking service for Swiss building renovation workflows.

Swiss permit requirements for renovation/demolition with pollutants:
- Construction permit (permis de construire): cantonal authority
- Demolition permit (permis de démolir): municipal authority
- SUVA work authorization: required when asbestos is present (OTConst Art. 60a, 82-86)
- Cantonal pollutant handling permit: required for PCB/lead/HAP above thresholds
- Waste transport permit: required for special waste transport (OLED)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.permit_tracking import (
    BuildingPermitSummary,
    PermitDependency,
    PermitDependencyResponse,
    PermitStatus,
    PermitStatusResponse,
    PermitTimeline,
    PortfolioPermitOverview,
    RequiredDocument,
    RequiredPermit,
    RequiredPermitsResponse,
)
from app.services.building_data_loader import load_org_buildings

# Estimated processing times in days per permit type
PROCESSING_TIMES = {
    "construction_permit": 60,
    "demolition_permit": 45,
    "suva_work_authorization": 30,
    "cantonal_pollutant_handling": 21,
    "waste_transport_permit": 14,
}

# Authority responsible for each permit type
PERMIT_AUTHORITIES = {
    "construction_permit": "Service cantonal des constructions",
    "demolition_permit": "Service communal de l'urbanisme",
    "suva_work_authorization": "SUVA (Caisse nationale suisse d'assurance)",
    "cantonal_pollutant_handling": "Service cantonal de l'environnement",
    "waste_transport_permit": "Office cantonal des déchets",
}

# Required documents per permit type
PERMIT_DOCUMENTS: dict[str, list[dict[str, str]]] = {
    "construction_permit": [
        {"name": "Plans de construction", "description": "Plans détaillés des travaux prévus"},
        {"name": "Rapport de diagnostic polluants", "description": "Diagnostic amiante/PCB/plomb complet"},
        {"name": "Plan de gestion des déchets", "description": "PGDC conforme OLED"},
    ],
    "demolition_permit": [
        {"name": "Plans de démolition", "description": "Plans et périmètre de démolition"},
        {"name": "Rapport de diagnostic polluants", "description": "Diagnostic complet avant démolition"},
        {"name": "Permis de construire approuvé", "description": "Si reconstruction prévue"},
    ],
    "suva_work_authorization": [
        {"name": "Rapport diagnostic amiante", "description": "Diagnostic amiante conforme OTConst"},
        {"name": "Plan de désamiantage", "description": "Méthodologie de retrait conforme CFST 6503"},
        {"name": "Plan de protection des travailleurs", "description": "Mesures de sécurité SUVA"},
        {"name": "Attestation entreprise agréée", "description": "Certificat de l'entreprise de désamiantage"},
    ],
    "cantonal_pollutant_handling": [
        {"name": "Résultats d'analyses laboratoire", "description": "Analyses PCB, plomb, HAP"},
        {"name": "Plan d'assainissement", "description": "Méthodologie de traitement des polluants"},
        {"name": "Évaluation des risques sanitaires", "description": "Rapport d'évaluation des risques"},
    ],
    "waste_transport_permit": [
        {"name": "Bordereau de suivi des déchets", "description": "Formulaire LMD pour déchets spéciaux"},
        {"name": "Attestation transporteur agréé", "description": "Certificat ADR du transporteur"},
        {"name": "Convention avec installation d'élimination", "description": "Accord de l'installation agréée"},
    ],
}

# Dependency graph: permit_type -> list of activities it blocks
PERMIT_BLOCKS = {
    "suva_work_authorization": ["remediation", "asbestos_removal", "demolition_with_asbestos"],
    "waste_transport_permit": ["waste_transport", "special_waste_disposal"],
    "construction_permit": ["renovation_works", "structural_changes"],
    "demolition_permit": ["demolition", "partial_demolition"],
    "cantonal_pollutant_handling": ["pollutant_remediation", "contaminated_material_handling"],
}

# Which permits depend on other permits
PERMIT_PREREQUISITES: dict[str, list[str]] = {
    "demolition_permit": ["construction_permit"],
    "waste_transport_permit": ["cantonal_pollutant_handling"],
}


async def _get_building_or_raise(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_building_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


async def _has_interventions(db: AsyncSession, building_id: UUID) -> bool:
    result = await db.execute(
        select(func.count()).select_from(Intervention).where(Intervention.building_id == building_id)
    )
    return (result.scalar() or 0) > 0


def _determine_required_permits(
    samples: list[Sample],
    has_interventions: bool,
    building: Building,
) -> list[RequiredPermit]:
    """Determine which permits are required based on building state."""
    permits: list[RequiredPermit] = []
    has_asbestos = False
    has_special_pollutants = False
    has_any_pollutants = False

    for sample in samples:
        ptype = (sample.pollutant_type or "").lower()
        conc = sample.concentration

        if ptype in ("asbestos", "amiante"):
            has_asbestos = True
            has_any_pollutants = True
        elif (ptype == "pcb" and conc is not None and conc > 50) or (
            ptype in ("lead", "plomb") and conc is not None and conc > 5000
        ):
            has_special_pollutants = True
            has_any_pollutants = True
        elif ptype:
            has_any_pollutants = True

    # Construction permit: always needed for renovation works
    if has_interventions or has_any_pollutants:
        docs = [
            RequiredDocument(name=d["name"], description=d["description"])
            for d in PERMIT_DOCUMENTS["construction_permit"]
        ]
        permits.append(
            RequiredPermit(
                permit_type="construction_permit",
                authority=PERMIT_AUTHORITIES["construction_permit"],
                estimated_processing_days=PROCESSING_TIMES["construction_permit"],
                required_documents=docs,
                reason="Travaux de rénovation ou assainissement prévus",
            )
        )

    # Demolition permit: if building has planned demolition interventions
    # For simplicity, assume needed if interventions exist and pollutants are present
    if has_interventions and has_any_pollutants:
        docs = [
            RequiredDocument(name=d["name"], description=d["description"])
            for d in PERMIT_DOCUMENTS["demolition_permit"]
        ]
        permits.append(
            RequiredPermit(
                permit_type="demolition_permit",
                authority=PERMIT_AUTHORITIES["demolition_permit"],
                estimated_processing_days=PROCESSING_TIMES["demolition_permit"],
                required_documents=docs,
                reason="Travaux de démolition avec présence de polluants",
            )
        )

    # SUVA work authorization: required for asbestos
    if has_asbestos:
        docs = [
            RequiredDocument(name=d["name"], description=d["description"])
            for d in PERMIT_DOCUMENTS["suva_work_authorization"]
        ]
        permits.append(
            RequiredPermit(
                permit_type="suva_work_authorization",
                authority=PERMIT_AUTHORITIES["suva_work_authorization"],
                estimated_processing_days=PROCESSING_TIMES["suva_work_authorization"],
                required_documents=docs,
                reason="Présence d'amiante détectée (OTConst Art. 60a, 82-86)",
            )
        )

    # Cantonal pollutant handling: required for PCB/lead above thresholds
    if has_special_pollutants or has_asbestos:
        docs = [
            RequiredDocument(name=d["name"], description=d["description"])
            for d in PERMIT_DOCUMENTS["cantonal_pollutant_handling"]
        ]
        permits.append(
            RequiredPermit(
                permit_type="cantonal_pollutant_handling",
                authority=PERMIT_AUTHORITIES["cantonal_pollutant_handling"],
                estimated_processing_days=PROCESSING_TIMES["cantonal_pollutant_handling"],
                required_documents=docs,
                reason="Polluants réglementés détectés au-dessus des seuils légaux",
            )
        )

    # Waste transport permit: needed for special waste
    if has_asbestos or has_special_pollutants:
        docs = [
            RequiredDocument(name=d["name"], description=d["description"])
            for d in PERMIT_DOCUMENTS["waste_transport_permit"]
        ]
        permits.append(
            RequiredPermit(
                permit_type="waste_transport_permit",
                authority=PERMIT_AUTHORITIES["waste_transport_permit"],
                estimated_processing_days=PROCESSING_TIMES["waste_transport_permit"],
                required_documents=docs,
                reason="Transport de déchets spéciaux requis (OLED)",
            )
        )

    return permits


async def get_required_permits(db: AsyncSession, building_id: UUID) -> RequiredPermitsResponse:
    """Get list of permits needed based on building state."""
    building = await _get_building_or_raise(db, building_id)
    samples = await _get_building_samples(db, building_id)
    interventions_exist = await _has_interventions(db, building_id)

    permits = _determine_required_permits(samples, interventions_exist, building)

    return RequiredPermitsResponse(
        building_id=building_id,
        permits=permits,
        total_permits=len(permits),
        generated_at=datetime.now(UTC),
    )


async def track_permit_status(db: AsyncSession, building_id: UUID) -> PermitStatusResponse:
    """Track current status of each required permit.

    Since permits are computed (not persisted), we derive status from
    building state: diagnostics, SUVA notification dates, interventions.
    """
    building = await _get_building_or_raise(db, building_id)
    samples = await _get_building_samples(db, building_id)
    interventions_exist = await _has_interventions(db, building_id)

    required = _determine_required_permits(samples, interventions_exist, building)

    # Check diagnostic state for SUVA notification
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    suva_notified = any(d.suva_notification_date is not None for d in diagnostics)
    canton_notified = any(d.canton_notification_date is not None for d in diagnostics)

    statuses: list[PermitStatus] = []
    approved_count = 0

    for permit in required:
        timeline_entries: list[PermitTimeline] = []
        status = "not_started"
        days_since = None
        est_remaining = None

        if permit.permit_type == "suva_work_authorization" and suva_notified:
            status = "application_submitted"
            notif_date = next(
                (str(d.suva_notification_date) for d in diagnostics if d.suva_notification_date),
                None,
            )
            timeline_entries.append(PermitTimeline(event="application_submitted", date=notif_date))
            est_remaining = PROCESSING_TIMES["suva_work_authorization"]

        elif permit.permit_type == "cantonal_pollutant_handling" and canton_notified:
            status = "application_submitted"
            notif_date = next(
                (str(d.canton_notification_date) for d in diagnostics if d.canton_notification_date),
                None,
            )
            timeline_entries.append(PermitTimeline(event="application_submitted", date=notif_date))
            est_remaining = PROCESSING_TIMES["cantonal_pollutant_handling"]

        else:
            timeline_entries.append(PermitTimeline(event="identified", date=str(datetime.now(UTC).date())))
            est_remaining = permit.estimated_processing_days

        if status == "approved":
            approved_count += 1

        statuses.append(
            PermitStatus(
                permit_type=permit.permit_type,
                status=status,
                authority=permit.authority,
                timeline=timeline_entries,
                days_since_submission=days_since,
                estimated_remaining_days=est_remaining,
            )
        )

    # Determine overall readiness
    if not statuses or all(s.status == "approved" for s in statuses):
        overall = "ready"
    elif any(s.status in ("not_started", "rejected") for s in statuses):
        overall = "blocked"
    else:
        overall = "partial"

    return PermitStatusResponse(
        building_id=building_id,
        permits=statuses,
        overall_readiness=overall,
        generated_at=datetime.now(UTC),
    )


async def get_permit_dependencies(db: AsyncSession, building_id: UUID) -> PermitDependencyResponse:
    """Get dependency graph of permits for a building."""
    building = await _get_building_or_raise(db, building_id)
    samples = await _get_building_samples(db, building_id)
    interventions_exist = await _has_interventions(db, building_id)

    required = _determine_required_permits(samples, interventions_exist, building)
    required_types = {p.permit_type for p in required}

    # Get current statuses
    status_response = await track_permit_status(db, building_id)
    status_map = {s.permit_type: s.status for s in status_response.permits}

    dependencies: list[PermitDependency] = []
    blocking: list[str] = []

    for permit in required:
        pt = permit.permit_type
        blocks = PERMIT_BLOCKS.get(pt, [])
        blocked_by = [prereq for prereq in PERMIT_PREREQUISITES.get(pt, []) if prereq in required_types]

        current_status = status_map.get(pt, "not_started")

        # A permit is blocking if it's not approved and it blocks activities
        if current_status != "approved" and blocks:
            blocking.append(pt)

        dependencies.append(
            PermitDependency(
                permit_type=pt,
                blocks=blocks,
                blocked_by=blocked_by,
                status=current_status,
            )
        )

    return PermitDependencyResponse(
        building_id=building_id,
        dependencies=dependencies,
        blocking_permits=blocking,
        generated_at=datetime.now(UTC),
    )


async def get_portfolio_permit_overview(db: AsyncSession, org_id: UUID) -> PortfolioPermitOverview:
    """Get organization-level permit overview across all buildings."""
    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioPermitOverview(
            organization_id=org_id,
            buildings=[],
            total_permits_needed=0,
            total_approved=0,
            total_pending=0,
            approval_rate=0.0,
            avg_processing_days=0,
            buildings_blocked_count=0,
            generated_at=datetime.now(UTC),
        )

    summaries: list[BuildingPermitSummary] = []
    total_needed = 0
    total_approved = 0
    total_pending = 0
    total_processing_days = 0
    blocked_count = 0

    for building in buildings:
        samples = await _get_building_samples(db, building.id)
        interventions_exist = await _has_interventions(db, building.id)
        required = _determine_required_permits(samples, interventions_exist, building)

        # Get statuses
        status_resp = await track_permit_status(db, building.id)
        b_approved = sum(1 for s in status_resp.permits if s.status == "approved")
        b_pending = sum(1 for s in status_resp.permits if s.status in ("application_submitted", "under_review"))
        b_blocked = status_resp.overall_readiness == "blocked"

        for permit in required:
            total_processing_days += permit.estimated_processing_days

        total_needed += len(required)
        total_approved += b_approved
        total_pending += b_pending
        if b_blocked:
            blocked_count += 1

        summaries.append(
            BuildingPermitSummary(
                building_id=building.id,
                address=building.address,
                total_permits=len(required),
                approved_count=b_approved,
                pending_count=b_pending,
                blocked=b_blocked,
            )
        )

    approval_rate = (total_approved / total_needed * 100.0) if total_needed > 0 else 0.0
    avg_days = (total_processing_days // total_needed) if total_needed > 0 else 0

    return PortfolioPermitOverview(
        organization_id=org_id,
        buildings=summaries,
        total_permits_needed=total_needed,
        total_approved=total_approved,
        total_pending=total_pending,
        approval_rate=round(approval_rate, 1),
        avg_processing_days=avg_days,
        buildings_blocked_count=blocked_count,
        generated_at=datetime.now(UTC),
    )
