"""BatiConnect — Readiness Advisor service.

Pure read/advisory — NEVER writes anything.
Queries unknowns, blockers, proof gaps, pending procedures, stale evidence,
and missing pollutant coverage to generate suggestions.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.evidence_link import EvidenceLink
from app.models.permit_procedure import PermitProcedure
from app.models.unknown_issue import UnknownIssue
from app.schemas.intelligence_stack import ReadinessAdvisorSuggestion

logger = logging.getLogger(__name__)

_ALL_POLLUTANTS = {"asbestos", "pcb", "lead", "hap", "radon"}


async def get_suggestions(db: AsyncSession, building_id: uuid.UUID) -> list[ReadinessAdvisorSuggestion]:
    """Generate advisory suggestions for a building. Pure read — never writes."""
    suggestions: list[ReadinessAdvisorSuggestion] = []

    # 1. Check building exists
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return suggestions

    # 2. Unresolved unknowns → blockers
    unknown_result = await db.execute(
        select(UnknownIssue).where(
            UnknownIssue.building_id == building_id,
            UnknownIssue.status == "open",
        )
    )
    unknowns = unknown_result.scalars().all()
    for unk in unknowns:
        suggestions.append(
            ReadinessAdvisorSuggestion(
                type="blocker",
                title=f"Unresolved unknown: {unk.unknown_type}",
                description=unk.description or f"Unknown issue '{unk.title}' needs resolution.",
                evidence_refs=[str(unk.id)],
                confidence=0.9,
                recommended_action="Resolve the unknown by providing missing information or documentation.",
            )
        )

    # 3. Missing pollutant coverage
    diag_result = await db.execute(
        select(Diagnostic.diagnostic_type).where(Diagnostic.building_id == building_id).distinct()
    )
    covered = {row[0] for row in diag_result.all() if row[0]}
    missing = _ALL_POLLUTANTS - covered
    for pollutant in sorted(missing):
        suggestions.append(
            ReadinessAdvisorSuggestion(
                type="missing_pollutant",
                title=f"No diagnostic for {pollutant}",
                description=f"No diagnostic covering {pollutant} has been performed for this building.",
                confidence=0.95,
                recommended_action=f"Commission a {pollutant} diagnostic to complete pollutant coverage.",
            )
        )

    # 4. Pending permit procedures
    proc_result = await db.execute(
        select(PermitProcedure).where(
            PermitProcedure.building_id == building_id,
            PermitProcedure.status.in_(["pending", "submitted"]),
        )
    )
    pending_procs = proc_result.scalars().all()
    for proc in pending_procs:
        suggestions.append(
            ReadinessAdvisorSuggestion(
                type="pending_procedure",
                title=f"Pending procedure: {proc.procedure_type}",
                description=f"Procedure '{proc.procedure_type}' is in status '{proc.status}' and requires attention.",
                evidence_refs=[str(proc.id)],
                confidence=0.85,
                recommended_action="Follow up on the pending procedure status.",
            )
        )

    # 5. Stale evidence (evidence older than 2 years)
    stale_cutoff = datetime.now(UTC) - timedelta(days=730)
    evidence_result = await db.execute(
        select(func.count(EvidenceLink.id)).where(
            EvidenceLink.target_type == "building",
            EvidenceLink.target_id == building_id,
            EvidenceLink.created_at < stale_cutoff,
        )
    )
    stale_count = evidence_result.scalar() or 0
    if stale_count > 0:
        suggestions.append(
            ReadinessAdvisorSuggestion(
                type="stale",
                title=f"{stale_count} stale evidence link(s)",
                description=f"{stale_count} evidence link(s) are older than 2 years and may need refreshing.",
                confidence=0.7,
                recommended_action="Review and update stale evidence with current documentation.",
            )
        )

    # 6. Proof gaps — compliance artefacts in draft
    artefact_result = await db.execute(
        select(func.count(ComplianceArtefact.id)).where(
            ComplianceArtefact.building_id == building_id,
            ComplianceArtefact.status == "draft",
        )
    )
    draft_artefacts = artefact_result.scalar() or 0
    if draft_artefacts > 0:
        suggestions.append(
            ReadinessAdvisorSuggestion(
                type="proof_gap",
                title=f"{draft_artefacts} draft compliance artefact(s)",
                description=f"{draft_artefacts} compliance artefact(s) remain in draft and are not submitted.",
                confidence=0.8,
                recommended_action="Submit draft compliance artefacts to close proof gaps.",
            )
        )

    return suggestions
