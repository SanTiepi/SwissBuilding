"""Data Provenance Tracker — traces origin and transformations of every data entity."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.models.user import User
from app.schemas.data_provenance import (
    DataLineageNode,
    DataLineageTree,
    IntegrityIssue,
    IntegrityReport,
    ProvenanceRecord,
    ProvenanceStatistics,
)

# Supported entity types and their model mapping
_ENTITY_MODELS: dict[str, type] = {
    "building": Building,
    "diagnostic": Diagnostic,
    "sample": Sample,
    "document": Document,
    "action": ActionItem,
}


def _determine_source(entity, entity_type: str) -> str:
    """Determine data source from entity attributes."""
    if entity_type == "building" and getattr(entity, "source_dataset", None):
        return "import"
    if entity_type == "action":
        src = getattr(entity, "source_type", None)
        if src and src in ("auto_generated", "automated"):
            return "automated"
        if src and src in ("import", "imported"):
            return "import"
    return "manual"


def _get_transformations(entity, entity_type: str) -> list[str]:
    """Extract known transformations applied to an entity."""
    transformations: list[str] = []
    if entity_type == "building":
        if getattr(entity, "source_dataset", None):
            transformations.append(f"imported_from:{entity.source_dataset}")
        if getattr(entity, "source_metadata_json", None):
            transformations.append("enriched_with_metadata")
    if entity_type == "document":
        meta = getattr(entity, "processing_metadata", None)
        if meta and isinstance(meta, dict):
            if meta.get("virus_scan"):
                transformations.append("virus_scanned")
            if meta.get("ocr"):
                transformations.append("ocr_processed")
    if entity_type == "diagnostic" and getattr(entity, "status", None) == "validated":
        transformations.append("validated")
    return transformations


def _get_creator_id(entity, entity_type: str) -> UUID | None:
    """Get the creator user ID from an entity."""
    if entity_type == "building":
        return getattr(entity, "created_by", None)
    if entity_type == "diagnostic":
        return getattr(entity, "diagnostician_id", None)
    if entity_type == "document":
        return getattr(entity, "uploaded_by", None)
    if entity_type == "action":
        return getattr(entity, "created_by", None)
    return None


async def _resolve_email(db: AsyncSession, user_id: UUID | None) -> str | None:
    """Resolve a user ID to an email address."""
    if not user_id:
        return None
    result = await db.execute(select(User.email).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_data_provenance(
    db: AsyncSession,
    entity_type: str,
    entity_id: UUID,
) -> ProvenanceRecord | None:
    """Return the provenance chain for a single entity."""
    model = _ENTITY_MODELS.get(entity_type)
    if not model:
        return None

    result = await db.execute(select(model).where(model.id == entity_id))
    entity = result.scalar_one_or_none()
    if not entity:
        return None

    source = _determine_source(entity, entity_type)
    transformations = _get_transformations(entity, entity_type)
    creator_id = _get_creator_id(entity, entity_type)
    creator_email = await _resolve_email(db, creator_id)

    # Determine parent
    parent_type = None
    parent_id = None
    if entity_type == "diagnostic":
        parent_type = "building"
        parent_id = entity.building_id
    elif entity_type == "sample":
        parent_type = "diagnostic"
        parent_id = entity.diagnostic_id
    elif entity_type in ("document", "action"):
        parent_type = "building"
        parent_id = entity.building_id

    return ProvenanceRecord(
        entity_type=entity_type,
        entity_id=entity.id,
        created_at=getattr(entity, "created_at", None),
        updated_at=getattr(entity, "updated_at", None),
        created_by=creator_id,
        created_by_email=creator_email,
        source=source,
        source_dataset=getattr(entity, "source_dataset", None),
        source_imported_at=getattr(entity, "source_imported_at", None),
        transformations=transformations,
        parent_entity_type=parent_type,
        parent_entity_id=parent_id,
    )


async def get_building_data_lineage(
    db: AsyncSession,
    building_id: UUID,
) -> DataLineageTree | None:
    """Build the full DAG-like lineage tree for a building and all related entities."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    entity_counts: dict[str, int] = {"building": 1}
    total_nodes = 1

    # Build root node
    root = DataLineageNode(
        entity_type="building",
        entity_id=building.id,
        label=f"{building.address}, {building.city}",
        source=_determine_source(building, "building"),
        created_at=building.created_at,
        created_by=building.created_by,
    )

    # Diagnostics
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = diag_result.scalars().all()
    entity_counts["diagnostic"] = len(diagnostics)
    total_nodes += len(diagnostics)

    for diag in diagnostics:
        diag_node = DataLineageNode(
            entity_type="diagnostic",
            entity_id=diag.id,
            label=f"{diag.diagnostic_type} ({diag.status})",
            source=_determine_source(diag, "diagnostic"),
            created_at=diag.created_at,
            created_by=diag.diagnostician_id,
        )

        # Samples under this diagnostic
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id == diag.id))
        samples = sample_result.scalars().all()
        entity_counts["sample"] = entity_counts.get("sample", 0) + len(samples)
        total_nodes += len(samples)

        for sample in samples:
            sample_node = DataLineageNode(
                entity_type="sample",
                entity_id=sample.id,
                label=f"{sample.sample_number} - {sample.pollutant_type or 'unknown'}",
                source="manual",
                created_at=sample.created_at,
            )
            diag_node.children.append(sample_node)

        root.children.append(diag_node)

    # Documents
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = doc_result.scalars().all()
    entity_counts["document"] = len(documents)
    total_nodes += len(documents)

    for doc in documents:
        doc_node = DataLineageNode(
            entity_type="document",
            entity_id=doc.id,
            label=doc.file_name,
            source=_determine_source(doc, "document"),
            created_at=doc.created_at,
            created_by=doc.uploaded_by,
        )
        root.children.append(doc_node)

    # Actions
    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = action_result.scalars().all()
    entity_counts["action"] = len(actions)
    total_nodes += len(actions)

    for action in actions:
        action_node = DataLineageNode(
            entity_type="action",
            entity_id=action.id,
            label=action.title,
            source=_determine_source(action, "action"),
            created_at=action.created_at,
            created_by=action.created_by,
        )
        root.children.append(action_node)

    return DataLineageTree(
        building_id=building_id,
        root=root,
        total_nodes=total_nodes,
        entity_counts=entity_counts,
    )


async def verify_data_integrity(
    db: AsyncSession,
    building_id: UUID,
) -> IntegrityReport | None:
    """Verify data consistency for a building. Return an integrity report."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    issues: list[IntegrityIssue] = []

    # 1. Check building has a creator
    if not building.created_by:
        issues.append(
            IntegrityIssue(
                issue_type="missing_creator",
                severity="warning",
                entity_type="building",
                entity_id=building.id,
                description="Building has no creator recorded.",
                field_name="created_by",
            )
        )

    # 2. Check diagnostics
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = diag_result.scalars().all()

    for diag in diagnostics:
        # Diagnostic without diagnostician
        if not diag.diagnostician_id:
            issues.append(
                IntegrityIssue(
                    issue_type="missing_source",
                    severity="warning",
                    entity_type="diagnostic",
                    entity_id=diag.id,
                    description=f"Diagnostic {diag.diagnostic_type} has no diagnostician assigned.",
                    field_name="diagnostician_id",
                )
            )

        # Completed diagnostic without samples
        sample_count_result = await db.execute(
            select(func.count()).select_from(Sample).where(Sample.diagnostic_id == diag.id)
        )
        sample_count = sample_count_result.scalar() or 0

        if diag.status in ("completed", "validated") and sample_count == 0:
            issues.append(
                IntegrityIssue(
                    issue_type="missing_samples",
                    severity="error",
                    entity_type="diagnostic",
                    entity_id=diag.id,
                    description=f"Diagnostic {diag.diagnostic_type} is {diag.status} but has no samples.",
                )
            )

        # Date inconsistency: report date before inspection date
        if diag.date_inspection and diag.date_report and diag.date_report < diag.date_inspection:
            issues.append(
                IntegrityIssue(
                    issue_type="date_inconsistency",
                    severity="error",
                    entity_type="diagnostic",
                    entity_id=diag.id,
                    description="Report date is before inspection date.",
                    field_name="date_report",
                )
            )

    # 3. Check documents without uploader
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = doc_result.scalars().all()

    for doc in documents:
        if not doc.uploaded_by:
            issues.append(
                IntegrityIssue(
                    issue_type="missing_source",
                    severity="info",
                    entity_type="document",
                    entity_id=doc.id,
                    description=f"Document '{doc.file_name}' has no uploader recorded.",
                    field_name="uploaded_by",
                )
            )

    # 4. Check actions referencing non-existent diagnostics
    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = action_result.scalars().all()
    diag_ids = {d.id for d in diagnostics}

    for action in actions:
        if action.diagnostic_id and action.diagnostic_id not in diag_ids:
            issues.append(
                IntegrityIssue(
                    issue_type="orphan",
                    severity="error",
                    entity_type="action",
                    entity_id=action.id,
                    description=f"Action '{action.title}' references non-existent diagnostic.",
                    field_name="diagnostic_id",
                )
            )
        if not action.created_by:
            issues.append(
                IntegrityIssue(
                    issue_type="missing_creator",
                    severity="info",
                    entity_type="action",
                    entity_id=action.id,
                    description=f"Action '{action.title}' has no creator recorded.",
                    field_name="created_by",
                )
            )

    # 5. Check samples referencing non-existent diagnostics (orphans)
    sample_result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    samples = sample_result.scalars().all()

    for sample in samples:
        if not sample.pollutant_type:
            issues.append(
                IntegrityIssue(
                    issue_type="missing_source",
                    severity="warning",
                    entity_type="sample",
                    entity_id=sample.id,
                    description=f"Sample {sample.sample_number} has no pollutant type.",
                    field_name="pollutant_type",
                )
            )

    # Build severity breakdown
    issues_by_severity: dict[str, int] = {}
    for issue in issues:
        issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1

    return IntegrityReport(
        building_id=building_id,
        checked_at=datetime.now(UTC),
        total_issues=len(issues),
        issues_by_severity=issues_by_severity,
        issues=issues,
        is_clean=len(issues) == 0,
    )


async def get_provenance_statistics(
    db: AsyncSession,
    org_id: UUID | None = None,
) -> ProvenanceStatistics:
    """Compute org-level provenance statistics."""
    # Get users belonging to the org (if specified)
    if org_id:
        user_result = await db.execute(select(User.id).where(User.organization_id == org_id))
        user_ids = [row[0] for row in user_result.all()]
    else:
        user_ids = None

    # Count buildings
    bq = select(func.count()).select_from(Building)
    if user_ids is not None:
        bq = bq.where(Building.created_by.in_(user_ids))
    total_buildings = (await db.execute(bq)).scalar() or 0

    # Count imported buildings
    bq_imported = select(func.count()).select_from(Building).where(Building.source_dataset.isnot(None))
    if user_ids is not None:
        bq_imported = bq_imported.where(Building.created_by.in_(user_ids))
    imported_buildings = (await db.execute(bq_imported)).scalar() or 0

    # Count diagnostics
    dq = select(func.count()).select_from(Diagnostic)
    if user_ids is not None:
        dq = dq.where(Diagnostic.diagnostician_id.in_(user_ids))
    total_diagnostics = (await db.execute(dq)).scalar() or 0

    # Count samples (via diagnostics if org-filtered)
    if user_ids is not None:
        sq = (
            select(func.count())
            .select_from(Sample)
            .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
            .where(Diagnostic.diagnostician_id.in_(user_ids))
        )
    else:
        sq = select(func.count()).select_from(Sample)
    total_samples = (await db.execute(sq)).scalar() or 0

    # Count documents
    doc_q = select(func.count()).select_from(Document)
    if user_ids is not None:
        doc_q = doc_q.where(Document.uploaded_by.in_(user_ids))
    total_documents = (await db.execute(doc_q)).scalar() or 0

    # Count actions
    aq = select(func.count()).select_from(ActionItem)
    if user_ids is not None:
        aq = aq.where(ActionItem.created_by.in_(user_ids))
    total_actions = (await db.execute(aq)).scalar() or 0

    # Source breakdown
    source_breakdown: dict[str, int] = {
        "import": imported_buildings,
        "manual": total_buildings - imported_buildings,
    }

    import_pct = (imported_buildings / total_buildings * 100.0) if total_buildings > 0 else 0.0
    manual_pct = 100.0 - import_pct if total_buildings > 0 else 0.0

    # Average freshness: days since last update across buildings
    freshness_q = select(func.avg(func.julianday(func.datetime("now")) - func.julianday(Building.updated_at)))
    if user_ids is not None:
        freshness_q = freshness_q.where(Building.created_by.in_(user_ids))
    avg_freshness_result = await db.execute(freshness_q)
    avg_freshness_raw = avg_freshness_result.scalar()
    avg_freshness = float(avg_freshness_raw) if avg_freshness_raw is not None else None

    # Traceability coverage: % of buildings with a creator
    if total_buildings > 0:
        traceable_q = select(func.count()).select_from(Building).where(Building.created_by.isnot(None))
        if user_ids is not None:
            traceable_q = traceable_q.where(Building.created_by.in_(user_ids))
        traceable_count = (await db.execute(traceable_q)).scalar() or 0
        traceability_coverage = traceable_count / total_buildings * 100.0
    else:
        traceability_coverage = 0.0

    # Data quality score: simple heuristic
    # 100 base, -10 per missing traceability %, weighted by entity coverage
    quality_score = min(100.0, traceability_coverage)
    if total_diagnostics > 0 and total_samples == 0:
        quality_score -= 20.0
    quality_score = max(0.0, quality_score)

    return ProvenanceStatistics(
        organization_id=org_id,
        total_buildings=total_buildings,
        total_diagnostics=total_diagnostics,
        total_samples=total_samples,
        total_documents=total_documents,
        total_actions=total_actions,
        source_breakdown=source_breakdown,
        import_percentage=round(import_pct, 1),
        manual_percentage=round(manual_pct, 1),
        avg_freshness_days=round(avg_freshness, 1) if avg_freshness is not None else None,
        traceability_coverage=round(traceability_coverage, 1),
        data_quality_score=round(quality_score, 1),
    )
