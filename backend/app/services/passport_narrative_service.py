"""BatiConnect — Passport Narrative service.

STUB: builds narrative from structured data templates, not LLM.
Real LLM narrative is Phase 3. Different audiences get different emphasis.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.unknown_issue import UnknownIssue
from app.schemas.intelligence_stack import NarrativeSection, PassportNarrativeResponse

logger = logging.getLogger(__name__)

_AUDIENCES = {"owner", "authority", "contractor"}


async def generate_narrative(
    db: AsyncSession,
    building_id: uuid.UUID,
    audience: str = "owner",
) -> PassportNarrativeResponse:
    """Build structured narrative from building data. STUB — no LLM call."""
    if audience not in _AUDIENCES:
        audience = "owner"

    # Fetch building
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return PassportNarrativeResponse(
            building_id=building_id,
            audience=audience,
            sections=[
                NarrativeSection(
                    title="Building Not Found",
                    body="No building found with this identifier.",
                )
            ],
            generated_at=datetime.now(UTC),
        )

    address = building.address or "Unknown address"
    city = building.city or ""

    sections: list[NarrativeSection] = []

    # Section 1: Building Identity
    sections.append(
        NarrativeSection(
            title="Building Identity",
            body=(
                f"Building located at {address}, {city}. "
                f"Construction year: {building.construction_year or 'unknown'}. "
                f"Type: {building.building_type or 'unknown'}."
            ),
            evidence_refs=[str(building.id)],
        )
    )

    # Section 2: Diagnostic Coverage
    diag_result = await db.execute(
        select(Diagnostic.diagnostic_type, func.count(Diagnostic.id))
        .where(Diagnostic.building_id == building_id)
        .group_by(Diagnostic.diagnostic_type)
    )
    diag_coverage = {row[0]: row[1] for row in diag_result.all() if row[0]}

    if diag_coverage:
        coverage_text = ", ".join(f"{p}: {c} diagnostic(s)" for p, c in sorted(diag_coverage.items()))
    else:
        coverage_text = "No diagnostics on record."

    if audience == "owner":
        diag_body = f"Pollutant diagnostic coverage: {coverage_text}. This determines your remediation obligations."
    elif audience == "authority":
        diag_body = f"Pollutant diagnostic coverage: {coverage_text}. Regulatory completeness depends on full coverage."
    else:
        diag_body = f"Pollutant diagnostic coverage: {coverage_text}. Scope your work based on confirmed findings."

    sections.append(
        NarrativeSection(
            title="Diagnostic Coverage",
            body=diag_body,
            audience_specific=audience != "owner",
        )
    )

    # Section 3: Interventions
    intv_result = await db.execute(
        select(func.count(Intervention.id), Intervention.status)
        .where(Intervention.building_id == building_id)
        .group_by(Intervention.status)
    )
    intv_stats = {row[1]: row[0] for row in intv_result.all()}
    total_intv = sum(intv_stats.values())

    if total_intv > 0:
        intv_text = ", ".join(f"{s}: {c}" for s, c in sorted(intv_stats.items()))
        if audience == "owner":
            intv_body = f"{total_intv} intervention(s) recorded ({intv_text}). Monitor costs and timelines."
        elif audience == "authority":
            intv_body = f"{total_intv} intervention(s) recorded ({intv_text}). Verify completion evidence."
        else:
            intv_body = f"{total_intv} intervention(s) recorded ({intv_text}). Check scope requirements."
    else:
        intv_body = "No interventions recorded for this building."

    sections.append(
        NarrativeSection(
            title="Interventions",
            body=intv_body,
            audience_specific=True,
        )
    )

    # Section 4: Open Issues
    unk_result = await db.execute(
        select(func.count(UnknownIssue.id)).where(
            UnknownIssue.building_id == building_id,
            UnknownIssue.status == "open",
        )
    )
    open_unknowns = unk_result.scalar() or 0

    if open_unknowns > 0:
        caveats = ["Some building data is incomplete or unverified."]
        if audience == "owner":
            issues_body = f"{open_unknowns} unresolved issue(s). These represent gaps in building knowledge that may affect costs."
        elif audience == "authority":
            issues_body = f"{open_unknowns} unresolved issue(s). Completeness may not meet regulatory thresholds."
        else:
            issues_body = f"{open_unknowns} unresolved issue(s). Verify scope assumptions before starting work."
    else:
        caveats = []
        issues_body = "No unresolved issues — building knowledge is complete."

    sections.append(
        NarrativeSection(
            title="Open Issues",
            body=issues_body,
            caveats=caveats,
            audience_specific=True,
        )
    )

    # Section 5: Compliance Status
    comp_result = await db.execute(
        select(ComplianceArtefact.status, func.count(ComplianceArtefact.id))
        .where(ComplianceArtefact.building_id == building_id)
        .group_by(ComplianceArtefact.status)
    )
    comp_stats = {row[0]: row[1] for row in comp_result.all()}

    if comp_stats:
        comp_text = ", ".join(f"{s}: {c}" for s, c in sorted(comp_stats.items()))
        comp_body = f"Compliance artefacts: {comp_text}."
    else:
        comp_body = "No compliance artefacts on record."

    sections.append(
        NarrativeSection(
            title="Compliance Status",
            body=comp_body,
        )
    )

    return PassportNarrativeResponse(
        building_id=building_id,
        audience=audience,
        sections=sections,
        generated_at=datetime.now(UTC),
    )
