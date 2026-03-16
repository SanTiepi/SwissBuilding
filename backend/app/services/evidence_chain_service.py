"""Evidence Chain Service — validates chain integrity, provenance gaps, timeline, and strength."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone
from app.schemas.evidence_chain import (
    BrokenLink,
    ChainValidationResult,
    EvidenceStrengthResult,
    EvidenceTimelineEvent,
    EvidenceTimelineResult,
    PollutantEvidenceStrength,
    ProvenanceGap,
    ProvenanceGapsResult,
)

POLLUTANT_TYPES = ["asbestos", "pcb", "lead", "hap", "radon"]


async def validate_evidence_chain(db: AsyncSession, building_id) -> ChainValidationResult:
    """Check evidence completeness for a building.

    Checks:
    1. Every sample has a valid diagnostic
    2. Every diagnostic belongs to this building
    3. Every compliance artefact references valid entities
    4. Every intervention links to a diagnostic finding
    """
    broken_links: list[BrokenLink] = []
    total_checks = 0
    passed_checks = 0

    # 1. Samples → diagnostics
    samples_q = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    samples = list(samples_q.scalars().all())

    diag_ids_q = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = {row[0] for row in diag_ids_q.all()}

    for sample in samples:
        total_checks += 1
        if sample.diagnostic_id in diag_ids:
            passed_checks += 1
        else:
            broken_links.append(
                BrokenLink(
                    entity_type="sample",
                    entity_id=sample.id,
                    issue="Sample references non-existent diagnostic",
                    severity="critical",
                )
            )

    # 2. Diagnostics → building
    diagnostics_q = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diagnostics_q.scalars().all())

    for diag in diagnostics:
        total_checks += 1
        if diag.building_id == building_id:
            passed_checks += 1
        else:
            broken_links.append(
                BrokenLink(
                    entity_type="diagnostic",
                    entity_id=diag.id,
                    issue="Diagnostic does not belong to building",
                    severity="critical",
                )
            )

    # Also check: diagnostics with no samples (weak but not broken)
    for diag in diagnostics:
        total_checks += 1
        diag_samples = [s for s in samples if s.diagnostic_id == diag.id]
        if diag_samples:
            passed_checks += 1
        else:
            broken_links.append(
                BrokenLink(
                    entity_type="diagnostic",
                    entity_id=diag.id,
                    issue="Diagnostic has no samples",
                    severity="medium",
                )
            )

    # 3. Compliance artefacts → valid references
    artefacts_q = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = list(artefacts_q.scalars().all())

    for artefact in artefacts:
        total_checks += 1
        valid = True
        if artefact.diagnostic_id and artefact.diagnostic_id not in diag_ids:
            valid = False
            broken_links.append(
                BrokenLink(
                    entity_type="compliance_artefact",
                    entity_id=artefact.id,
                    issue="Artefact references non-existent diagnostic",
                    severity="high",
                )
            )

        if artefact.intervention_id:
            intervention_q = await db.execute(
                select(Intervention.id).where(Intervention.id == artefact.intervention_id)
            )
            if not intervention_q.scalar_one_or_none():
                valid = False
                broken_links.append(
                    BrokenLink(
                        entity_type="compliance_artefact",
                        entity_id=artefact.id,
                        issue="Artefact references non-existent intervention",
                        severity="high",
                    )
                )

        if valid:
            passed_checks += 1

    # 4. Interventions → diagnostic link
    interventions_q = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(interventions_q.scalars().all())

    for intervention in interventions:
        total_checks += 1
        if intervention.diagnostic_id:
            if intervention.diagnostic_id in diag_ids:
                passed_checks += 1
            else:
                broken_links.append(
                    BrokenLink(
                        entity_type="intervention",
                        entity_id=intervention.id,
                        issue="Intervention references non-existent diagnostic",
                        severity="high",
                    )
                )
        else:
            broken_links.append(
                BrokenLink(
                    entity_type="intervention",
                    entity_id=intervention.id,
                    issue="Intervention has no linked diagnostic",
                    severity="medium",
                )
            )

    integrity_score = round((passed_checks / total_checks) * 100) if total_checks > 0 else 100

    return ChainValidationResult(
        building_id=building_id,
        integrity_score=integrity_score,
        total_checks=total_checks,
        passed_checks=passed_checks,
        broken_links=broken_links,
        validated_at=datetime.now(UTC),
    )


async def get_provenance_gaps(db: AsyncSession, building_id) -> ProvenanceGapsResult:
    """Find evidence provenance gaps for a building."""
    gaps: list[ProvenanceGap] = []

    # 1. Documents without clear source (no uploaded_by)
    docs_q = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(docs_q.scalars().all())
    for doc in documents:
        if not doc.uploaded_by:
            gaps.append(
                ProvenanceGap(
                    entity_type="document",
                    entity_id=doc.id,
                    gap_type="missing_source",
                    severity="medium",
                    description=f"Document '{doc.file_name}' has no recorded uploader",
                    fix_recommendation="Assign the document to the user who uploaded or provided it",
                )
            )

    # 2. Samples without lab reference
    diag_ids_q = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [row[0] for row in diag_ids_q.all()]

    if diag_ids:
        samples_q = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(samples_q.scalars().all())

        # Get diagnostics for lab info lookup
        diags_q = await db.execute(select(Diagnostic).where(Diagnostic.id.in_(diag_ids)))
        diag_map = {d.id: d for d in diags_q.scalars().all()}

        for sample in samples:
            diag = diag_map.get(sample.diagnostic_id)
            if diag and not diag.laboratory:
                gaps.append(
                    ProvenanceGap(
                        entity_type="sample",
                        entity_id=sample.id,
                        gap_type="missing_lab_reference",
                        severity="high",
                        description=f"Sample '{sample.sample_number}' has no laboratory reference on its diagnostic",
                        fix_recommendation="Add laboratory name and report number to the diagnostic",
                    )
                )

    # 3. Diagnostics without author (diagnostician)
    diagnostics_q = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diagnostics_q.scalars().all())
    for diag in diagnostics:
        if not diag.diagnostician_id:
            gaps.append(
                ProvenanceGap(
                    entity_type="diagnostic",
                    entity_id=diag.id,
                    gap_type="missing_author",
                    severity="high",
                    description=f"Diagnostic '{diag.diagnostic_type}' has no assigned diagnostician",
                    fix_recommendation="Assign a qualified diagnostician to this diagnostic",
                )
            )

    # 4. Actions without trigger (no source_type or no diagnostic/sample link)
    actions_q = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(actions_q.scalars().all())
    for action in actions:
        if not action.diagnostic_id and not action.sample_id:
            gaps.append(
                ProvenanceGap(
                    entity_type="action",
                    entity_id=action.id,
                    gap_type="missing_trigger",
                    severity="medium",
                    description=f"Action '{action.title}' has no linked diagnostic or sample trigger",
                    fix_recommendation="Link the action to the diagnostic finding or sample that triggered it",
                )
            )

    return ProvenanceGapsResult(
        building_id=building_id,
        total_gaps=len(gaps),
        gaps=gaps,
        analysed_at=datetime.now(UTC),
    )


async def build_evidence_timeline(db: AsyncSession, building_id) -> EvidenceTimelineResult:
    """Build chronological evidence trail for a building."""
    events: list[EvidenceTimelineEvent] = []

    # Diagnostics
    diagnostics_q = await db.execute(
        select(Diagnostic, User)
        .outerjoin(User, Diagnostic.diagnostician_id == User.id)
        .where(Diagnostic.building_id == building_id)
    )
    for diag, user in diagnostics_q.all():
        date = None
        if diag.date_report:
            date = datetime.combine(diag.date_report, datetime.min.time(), tzinfo=UTC)
        elif diag.date_inspection:
            date = datetime.combine(diag.date_inspection, datetime.min.time(), tzinfo=UTC)
        elif diag.created_at:
            date = diag.created_at if diag.created_at.tzinfo else diag.created_at.replace(tzinfo=UTC)

        if date:
            events.append(
                EvidenceTimelineEvent(
                    event_type="diagnostic_created",
                    entity_type="diagnostic",
                    entity_id=diag.id,
                    date=date,
                    title=f"Diagnostic: {diag.diagnostic_type}",
                    actor_id=diag.diagnostician_id,
                    actor_name=f"{user.first_name} {user.last_name}" if user else None,
                    details=f"Status: {diag.status}",
                )
            )

    # Samples
    diag_ids_q = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [row[0] for row in diag_ids_q.all()]

    if diag_ids:
        samples_q = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        for sample in samples_q.scalars().all():
            if sample.created_at:
                date = sample.created_at if sample.created_at.tzinfo else sample.created_at.replace(tzinfo=UTC)
                events.append(
                    EvidenceTimelineEvent(
                        event_type="sample_collected",
                        entity_type="sample",
                        entity_id=sample.id,
                        date=date,
                        title=f"Sample: {sample.sample_number}",
                        details=f"Pollutant: {sample.pollutant_type or 'N/A'}, "
                        f"Result: {'threshold exceeded' if sample.threshold_exceeded else 'within limits'}",
                    )
                )

    # Documents
    docs_q = await db.execute(
        select(Document, User)
        .outerjoin(User, Document.uploaded_by == User.id)
        .where(Document.building_id == building_id)
    )
    for doc, user in docs_q.all():
        if doc.created_at:
            date = doc.created_at if doc.created_at.tzinfo else doc.created_at.replace(tzinfo=UTC)
            events.append(
                EvidenceTimelineEvent(
                    event_type="document_uploaded",
                    entity_type="document",
                    entity_id=doc.id,
                    date=date,
                    title=f"Document: {doc.file_name}",
                    actor_id=doc.uploaded_by,
                    actor_name=f"{user.first_name} {user.last_name}" if user else None,
                    details=f"Type: {doc.document_type or 'unclassified'}",
                )
            )

    # Interventions
    interventions_q = await db.execute(
        select(Intervention, User)
        .outerjoin(User, Intervention.created_by == User.id)
        .where(Intervention.building_id == building_id)
    )
    for intervention, user in interventions_q.all():
        date = None
        if intervention.date_start:
            date = datetime.combine(intervention.date_start, datetime.min.time(), tzinfo=UTC)
        elif intervention.created_at:
            date = (
                intervention.created_at
                if intervention.created_at.tzinfo
                else intervention.created_at.replace(tzinfo=UTC)
            )

        if date:
            events.append(
                EvidenceTimelineEvent(
                    event_type="intervention_performed",
                    entity_type="intervention",
                    entity_id=intervention.id,
                    date=date,
                    title=f"Intervention: {intervention.title}",
                    actor_id=intervention.created_by,
                    actor_name=f"{user.first_name} {user.last_name}" if user else None,
                    details=f"Type: {intervention.intervention_type}, Status: {intervention.status}",
                )
            )

    # Actions
    actions_q = await db.execute(
        select(ActionItem, User)
        .outerjoin(User, ActionItem.created_by == User.id)
        .where(ActionItem.building_id == building_id)
    )
    for action, user in actions_q.all():
        if action.created_at:
            date = action.created_at if action.created_at.tzinfo else action.created_at.replace(tzinfo=UTC)
            events.append(
                EvidenceTimelineEvent(
                    event_type="action_created",
                    entity_type="action",
                    entity_id=action.id,
                    date=date,
                    title=f"Action: {action.title}",
                    actor_id=action.created_by,
                    actor_name=f"{user.first_name} {user.last_name}" if user else None,
                    details=f"Priority: {action.priority}, Status: {action.status}",
                )
            )

    # Sort by date
    events.sort(key=lambda e: e.date)

    return EvidenceTimelineResult(
        building_id=building_id,
        events=events,
        total_events=len(events),
        generated_at=datetime.now(UTC),
    )


async def assess_evidence_strength(db: AsyncSession, building_id) -> EvidenceStrengthResult:
    """Assess per-pollutant evidence strength for a building."""
    pollutant_results: list[PollutantEvidenceStrength] = []

    # Get diagnostics and samples
    diag_ids_q = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [row[0] for row in diag_ids_q.all()]

    # Get diagnostics for lab info
    diag_map = {}
    if diag_ids:
        diags_q = await db.execute(select(Diagnostic).where(Diagnostic.id.in_(diag_ids)))
        diag_map = {d.id: d for d in diags_q.scalars().all()}

    # Get zones for coverage calculation
    zones_q = await db.execute(select(func.count()).select_from(Zone).where(Zone.building_id == building_id))
    total_zones = zones_q.scalar() or 0

    # Get all samples for this building
    all_samples = []
    if diag_ids:
        samples_q = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        all_samples = list(samples_q.scalars().all())

    for pollutant in POLLUTANT_TYPES:
        # Filter samples for this pollutant
        p_samples = [s for s in all_samples if s.pollutant_type == pollutant]
        sample_count = len(p_samples)

        # Determine claim
        if sample_count == 0:
            claim = "unknown"
        elif any(s.threshold_exceeded for s in p_samples):
            claim = "detected"
        else:
            claim = "not_detected"

        # Most recent sample date
        most_recent = None
        for s in p_samples:
            if s.created_at:
                dt = s.created_at if s.created_at.tzinfo else s.created_at.replace(tzinfo=UTC)
                if most_recent is None or dt > most_recent:
                    most_recent = dt

        # Lab reference check
        has_lab = False
        for s in p_samples:
            diag = diag_map.get(s.diagnostic_id)
            if diag and diag.laboratory:
                has_lab = True
                break

        # Zone coverage: unique floors/rooms sampled vs total zones
        sampled_locations = set()
        for s in p_samples:
            loc = s.location_floor or s.location_room
            if loc:
                sampled_locations.add(loc)
        zone_coverage = (len(sampled_locations) / total_zones * 100) if total_zones > 0 else 0.0

        # Strength scoring
        strength = _compute_strength(sample_count, has_lab, zone_coverage, most_recent)

        details = _build_strength_details(sample_count, has_lab, zone_coverage, most_recent)

        pollutant_results.append(
            PollutantEvidenceStrength(
                pollutant_type=pollutant,
                claim=claim,
                strength=strength,
                sample_count=sample_count,
                most_recent_sample_date=most_recent,
                has_lab_reference=has_lab,
                zone_coverage_pct=round(zone_coverage, 1),
                details=details,
            )
        )

    # Overall strength
    strengths = [p.strength for p in pollutant_results]
    strength_order = {"strong": 3, "moderate": 2, "weak": 1, "insufficient": 0}
    if not strengths:
        overall = "insufficient"
    else:
        avg_score = sum(strength_order.get(s, 0) for s in strengths) / len(strengths)
        if avg_score >= 2.5:
            overall = "strong"
        elif avg_score >= 1.5:
            overall = "moderate"
        elif avg_score >= 0.5:
            overall = "weak"
        else:
            overall = "insufficient"

    return EvidenceStrengthResult(
        building_id=building_id,
        pollutants=pollutant_results,
        overall_strength=overall,
        assessed_at=datetime.now(UTC),
    )


def _compute_strength(sample_count: int, has_lab: bool, zone_coverage: float, most_recent) -> str:
    """Compute evidence strength from factors."""
    score = 0.0

    # Sample count factor (0-30 points)
    if sample_count >= 5:
        score += 30
    elif sample_count >= 3:
        score += 20
    elif sample_count >= 1:
        score += 10

    # Lab accreditation factor (0-25 points)
    if has_lab:
        score += 25

    # Zone coverage factor (0-25 points)
    if zone_coverage >= 80:
        score += 25
    elif zone_coverage >= 50:
        score += 15
    elif zone_coverage > 0:
        score += 8

    # Recency factor (0-20 points)
    if most_recent:
        now = datetime.now(UTC)
        age_days = (now - most_recent).days
        if age_days <= 365:
            score += 20
        elif age_days <= 730:
            score += 12
        elif age_days <= 1825:
            score += 5

    if score >= 75:
        return "strong"
    elif score >= 45:
        return "moderate"
    elif score >= 20:
        return "weak"
    return "insufficient"


def _build_strength_details(sample_count: int, has_lab: bool, zone_coverage: float, most_recent) -> str:
    """Build human-readable strength details."""
    parts = []
    parts.append(f"{sample_count} sample(s)")
    parts.append(f"lab: {'yes' if has_lab else 'no'}")
    parts.append(f"zone coverage: {zone_coverage:.0f}%")
    if most_recent:
        age_days = (datetime.now(UTC) - most_recent).days
        if age_days <= 365:
            parts.append("recent (<1y)")
        elif age_days <= 730:
            parts.append("aging (1-2y)")
        else:
            parts.append(f"old ({age_days // 365}y)")
    else:
        parts.append("no date")
    return ", ".join(parts)
