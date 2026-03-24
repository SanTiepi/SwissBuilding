from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.event import Event
from app.schemas.timeline import TimelineEntryRead


async def get_building_timeline(
    db: AsyncSession,
    building_id: UUID,
    page: int = 1,
    size: int = 50,
    event_type_filter: str | None = None,
) -> tuple[list[TimelineEntryRead], int]:
    """Build a unified, chronologically sorted timeline for a building.

    Merges data from: building (construction), diagnostics, samples,
    documents, interventions, technical_plans, events.
    Returns (items, total_count) for pagination.
    """
    items: list[TimelineEntryRead] = []

    # --- Construction date ---
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building and building.construction_year:
        items.append(
            TimelineEntryRead(
                id=f"construction-{building.id}",
                date=datetime(building.construction_year, 1, 1),
                event_type="construction",
                title=f"Construction ({building.construction_year})",
                description=f"Building constructed in {building.construction_year}",
                icon_hint="building",
                metadata={"construction_year": building.construction_year},
                source_id=str(building.id),
                source_type="building",
            )
        )

    # --- Diagnostics ---
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    for diag in diag_result.scalars().all():
        occurred_at = diag.created_at
        if diag.date_inspection is not None:
            occurred_at = datetime.combine(diag.date_inspection, time.min)
        items.append(
            TimelineEntryRead(
                id=str(diag.id),
                date=occurred_at,
                event_type="diagnostic",
                title=f"Diagnostic {diag.diagnostic_type} ({diag.status})",
                description=diag.summary,
                icon_hint="microscope",
                metadata={
                    "diagnostic_type": diag.diagnostic_type,
                    "status": diag.status,
                    "context": diag.diagnostic_context,
                },
                source_id=str(diag.id),
                source_type="diagnostic",
            )
        )

        # --- Samples from this diagnostic ---
        from app.models.sample import Sample

        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id == diag.id))
        for sample in sample_result.scalars().all():
            items.append(
                TimelineEntryRead(
                    id=str(sample.id),
                    date=sample.created_at or occurred_at,
                    event_type="sample",
                    title=f"Sample {sample.sample_number} - {sample.pollutant_type or 'unknown'}",
                    description=f"{sample.material_category or ''} - {sample.location_room or ''}".strip(" -"),
                    icon_hint="flask",
                    metadata={
                        "pollutant_type": sample.pollutant_type,
                        "concentration": sample.concentration,
                        "unit": sample.unit,
                        "threshold_exceeded": sample.threshold_exceeded,
                        "risk_level": sample.risk_level,
                    },
                    source_id=str(sample.id),
                    source_type="sample",
                )
            )

    # --- Documents ---
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    for doc in doc_result.scalars().all():
        items.append(
            TimelineEntryRead(
                id=str(doc.id),
                date=doc.created_at,
                event_type="document",
                title=doc.file_name or doc.description or "Document",
                description=doc.description,
                icon_hint="file",
                metadata={
                    "document_type": doc.document_type,
                    "file_size_bytes": doc.file_size_bytes,
                    "mime_type": doc.mime_type,
                },
                source_id=str(doc.id),
                source_type="document",
            )
        )

    # --- Interventions ---
    from app.models.intervention import Intervention

    intervention_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    for intv in intervention_result.scalars().all():
        occurred_at = intv.created_at
        if intv.date_start is not None:
            occurred_at = datetime.combine(intv.date_start, time.min)
        items.append(
            TimelineEntryRead(
                id=str(intv.id),
                date=occurred_at,
                event_type="intervention",
                title=intv.title,
                description=intv.description,
                icon_hint="wrench",
                metadata={
                    "intervention_type": intv.intervention_type,
                    "status": intv.status,
                    "cost_chf": intv.cost_chf,
                    "contractor_name": intv.contractor_name,
                },
                source_id=str(intv.id),
                source_type="intervention",
            )
        )

    # --- Technical Plans ---
    from app.models.technical_plan import TechnicalPlan

    plan_result = await db.execute(select(TechnicalPlan).where(TechnicalPlan.building_id == building_id))
    for plan in plan_result.scalars().all():
        items.append(
            TimelineEntryRead(
                id=str(plan.id),
                date=plan.created_at,
                event_type="plan",
                title=plan.title,
                description=plan.description,
                icon_hint="map",
                metadata={
                    "plan_type": plan.plan_type,
                    "floor_number": plan.floor_number,
                    "version": plan.version,
                },
                source_id=str(plan.id),
                source_type="technical_plan",
            )
        )

    # --- Diagnostic Publications ---
    from app.models.diagnostic_publication import DiagnosticReportPublication

    pub_result = await db.execute(
        select(DiagnosticReportPublication).where(
            DiagnosticReportPublication.building_id == building_id,
            DiagnosticReportPublication.match_state.in_(["auto_matched", "manual_matched"]),
        )
    )
    for pub in pub_result.scalars().all():
        items.append(
            TimelineEntryRead(
                id=str(pub.id),
                date=pub.published_at,
                event_type="diagnostic_publication",
                title=f"Diagnostic publication ({pub.mission_type})",
                description=f"Report from {pub.source_system}, version {pub.current_version}",
                icon_hint="clipboard",
                metadata={
                    "mission_type": pub.mission_type,
                    "source_system": pub.source_system,
                    "current_version": pub.current_version,
                    "match_state": pub.match_state,
                    "source_mission_id": pub.source_mission_id,
                },
                source_id=str(pub.id),
                source_type="diagnostic_publication",
            )
        )

    # --- Events ---
    evt_result = await db.execute(select(Event).where(Event.building_id == building_id))
    for evt in evt_result.scalars().all():
        occurred_at = datetime.combine(evt.date, time.min) if evt.date else evt.created_at
        items.append(
            TimelineEntryRead(
                id=str(evt.id),
                date=occurred_at,
                event_type="event",
                title=evt.title,
                description=evt.description,
                icon_hint="calendar",
                metadata=evt.metadata_json,
                source_id=str(evt.id),
                source_type="event",
            )
        )

    # --- Risk score changes ---
    from app.models.building_risk_score import BuildingRiskScore

    risk_result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_score = risk_result.scalar_one_or_none()
    if risk_score:
        items.append(
            TimelineEntryRead(
                id=str(risk_score.id),
                date=risk_score.last_updated,
                event_type="risk_change",
                title=f"Risk assessment: {risk_score.overall_risk_level}",
                description=f"Overall risk level: {risk_score.overall_risk_level}, confidence: {risk_score.confidence}",
                icon_hint="shield",
                metadata={
                    "overall_risk_level": risk_score.overall_risk_level,
                    "confidence": risk_score.confidence,
                    "data_source": risk_score.data_source,
                },
                source_id=str(risk_score.id),
                source_type="risk_score",
            )
        )

    # --- Apply event_type filter ---
    if event_type_filter:
        items = [item for item in items if item.event_type == event_type_filter]

    # Sort by date descending (newest first)
    items.sort(key=lambda x: x.date, reverse=True)

    total = len(items)
    # Apply pagination
    start = (page - 1) * size
    end = start + size
    paginated_items = items[start:end]

    return paginated_items, total
