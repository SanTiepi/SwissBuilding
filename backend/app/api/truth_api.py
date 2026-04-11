"""External Truth API v1 — read-first, projection-based, role-bounded.

This module exposes canonical read-side projections for external consumers.
It delegates to existing services (passport_service, intent_service, etc.)
and wraps responses in versioned, HATEOAS-enriched envelopes.

NO mutations — all endpoints are GET-only.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.truth_api import (
    AlertsV1,
    AlertV1,
    BuildingSummaryDiagnosticsV1,
    BuildingSummaryGradeV1,
    BuildingSummaryIdentityV1,
    BuildingSummaryPollutantsV1,
    BuildingSummaryReadinessV1,
    BuildingSummaryV1,
    ChangeEntryV1,
    ChangeTimelineV1,
    IdentityChainV1,
    PackV1,
    PassportV1,
    PortfolioBuildingRowV1,
    PortfolioOverviewV1,
    SafeToXSummaryV1,
    SafeToXVerdictV1,
    UnknownEntryV1,
    UnknownsV1,
)

router = APIRouter(prefix="/v1/truth", tags=["Truth API v1"])

ALL_SAFE_TO_TYPES = ["start", "tender", "reopen", "requalify", "sell", "insure", "finance", "lease"]

ALL_SUMMARY_SECTIONS = [
    "identity",
    "spatial",
    "grade",
    "completeness",
    "readiness",
    "trust",
    "pollutants",
    "diagnostics_summary",
]


def _base_url(building_id: str) -> str:
    return f"/api/v1/truth/buildings/{building_id}"


def _building_links(building_id: str) -> dict[str, str]:
    base = _base_url(building_id)
    return {
        "self_summary": f"{base}/summary",
        "identity_chain": f"{base}/identity-chain",
        "safe_to_x": f"{base}/safe-to-x",
        "unknowns": f"{base}/unknowns",
        "changes": f"{base}/changes",
        "passport": f"{base}/passport",
    }


async def _get_building_or_404(db: AsyncSession, building_id: UUID):
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Building Summary
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/summary",
    response_model=BuildingSummaryV1,
)
async def get_building_summary(
    building_id: UUID,
    include_sections: list[str] | None = Query(default=None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Public building summary projection.

    Sections: identity, spatial, grade, completeness, readiness, trust, pollutants, diagnostics_summary.
    If include_sections is omitted, all sections are returned.
    """
    building = await _get_building_or_404(db, building_id)

    from app.services.passport_service import get_passport_summary

    passport = await get_passport_summary(db, building_id)
    if passport is None:
        raise HTTPException(status_code=404, detail="Passport data not available")

    sections = include_sections or ALL_SUMMARY_SECTIONS
    now = datetime.now(UTC)

    result: dict = {
        "api_version": "1.0",
        "generated_at": now,
        "links": _building_links(str(building_id)),
        "building_id": str(building_id),
        "sections_included": sections,
    }

    if "identity" in sections:
        result["identity"] = BuildingSummaryIdentityV1(
            building_id=str(building_id),
            address=building.address,
            postal_code=building.postal_code,
            city=building.city,
            canton=building.canton,
            egid=building.egid,
        )

    if "spatial" in sections:
        result["spatial"] = {
            "latitude": float(building.latitude) if building.latitude else None,
            "longitude": float(building.longitude) if building.longitude else None,
            "municipality": building.city,
            "canton": building.canton,
        }

    if "grade" in sections:
        result["grade"] = BuildingSummaryGradeV1(
            passport_grade=passport["passport_grade"],
            overall_trust=passport["knowledge_state"]["overall_trust"],
            overall_completeness=passport["completeness"]["overall_score"],
        )

    if "completeness" in sections:
        result["completeness"] = passport["completeness"]

    if "readiness" in sections:
        r = passport["readiness"]
        result["readiness"] = BuildingSummaryReadinessV1(
            safe_to_start=r.get("safe_to_start", {}),
            safe_to_tender=r.get("safe_to_tender", {}),
            safe_to_reopen=r.get("safe_to_reopen", {}),
            safe_to_requalify=r.get("safe_to_requalify", {}),
        )

    if "trust" in sections:
        result["trust"] = passport["knowledge_state"]

    if "pollutants" in sections:
        pc = passport["pollutant_coverage"]
        result["pollutants"] = BuildingSummaryPollutantsV1(
            total_pollutants=pc["total_pollutants"],
            covered_count=pc["covered_count"],
            missing_count=pc["missing_count"],
            covered=pc["covered"],
            missing=pc["missing"],
            coverage_ratio=pc["coverage_ratio"],
        )

    if "diagnostics_summary" in sections:
        ec = passport["evidence_coverage"]
        result["diagnostics_summary"] = BuildingSummaryDiagnosticsV1(
            diagnostics_count=ec["diagnostics_count"],
            samples_count=ec["samples_count"],
            latest_diagnostic_date=ec["latest_diagnostic_date"],
        )

    return result


# ---------------------------------------------------------------------------
# Identity Chain
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/identity-chain",
    response_model=IdentityChainV1,
)
async def get_identity_chain(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """EGID, EGRID, RDPPF, parcel -- auditable identity chain."""
    await _get_building_or_404(db, building_id)

    from app.services.identity_chain_service import get_identity_chain as _get_chain

    try:
        chain = await _get_chain(db, building_id)
    except Exception as e:
        logging.getLogger(__name__).exception("Identity chain resolution failed for building %s", building_id)
        raise HTTPException(status_code=500, detail="Identity chain resolution failed") from e

    if chain.get("error") == "building_not_found":
        raise HTTPException(status_code=404, detail="Building not found")

    await db.commit()

    return IdentityChainV1(
        api_version="1.0",
        generated_at=datetime.now(UTC),
        links=_building_links(str(building_id)),
        building_id=str(building_id),
        egid=chain.get("egid", {}),
        egrid=chain.get("egrid", {}),
        rdppf=chain.get("rdppf", {}),
        chain_complete=chain.get("chain_complete", False),
        chain_gaps=chain.get("chain_gaps", []),
    )


# ---------------------------------------------------------------------------
# SafeToX
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/safe-to-x",
    response_model=SafeToXSummaryV1,
)
async def get_safe_to_x(
    building_id: UUID,
    types: list[str] | None = Query(default=None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """SafeToX verdicts: start, sell, insure, finance, lease, transfer, tender.

    Each verdict includes verdict, blockers, conditions, confidence, basis.
    Filter with ?types=start&types=sell to get specific types only.
    """
    await _get_building_or_404(db, building_id)

    from app.services.intent_service import get_safe_to_x_summary

    summary = await get_safe_to_x_summary(db, building_id)

    requested_types = types or ALL_SAFE_TO_TYPES
    filtered_verdicts = [v for v in summary.get("verdicts", []) if v["safe_to_type"] in requested_types]

    return SafeToXSummaryV1(
        api_version="1.0",
        generated_at=datetime.now(UTC),
        links=_building_links(str(building_id)),
        building_id=str(building_id),
        verdicts=[SafeToXVerdictV1(**v) for v in filtered_verdicts],
        types_included=requested_types,
    )


# ---------------------------------------------------------------------------
# Unknowns
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/unknowns",
    response_model=UnknownsV1,
)
async def get_unknowns(
    building_id: UUID,
    current_user: User = Depends(require_permission("unknowns", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Unknowns ledger: what is missing, stale, unverified, contradicted."""
    await _get_building_or_404(db, building_id)

    from collections import defaultdict

    from app.models.unknown_issue import UnknownIssue

    result = await db.execute(
        select(UnknownIssue).where(
            and_(
                UnknownIssue.building_id == building_id,
                UnknownIssue.status == "open",
            )
        )
    )
    open_unknowns = list(result.scalars().all())

    by_type: dict[str, int] = defaultdict(int)
    blocking_count = 0
    entries = []
    for u in open_unknowns:
        by_type[u.unknown_type] += 1
        if u.blocks_readiness:
            blocking_count += 1
        entries.append(
            UnknownEntryV1(
                unknown_type=u.unknown_type,
                status=u.status,
                blocks_readiness=u.blocks_readiness or False,
                description=u.description if hasattr(u, "description") else None,
                severity=u.severity if hasattr(u, "severity") else None,
            )
        )

    return UnknownsV1(
        api_version="1.0",
        generated_at=datetime.now(UTC),
        links=_building_links(str(building_id)),
        building_id=str(building_id),
        total_open=len(open_unknowns),
        blocking=blocking_count,
        by_type=dict(by_type),
        entries=entries,
    )


# ---------------------------------------------------------------------------
# Changes
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/changes",
    response_model=ChangeTimelineV1,
)
async def get_changes(
    building_id: UUID,
    since: datetime | None = Query(default=None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Change timeline: observations, events, deltas, signals since a date."""
    await _get_building_or_404(db, building_id)

    from app.services.change_tracker_service import get_change_timeline

    try:
        timeline = await get_change_timeline(db, building_id, since=since)
    except Exception:
        timeline = []

    entries = []
    for item in timeline:
        entries.append(
            ChangeEntryV1(
                change_type=item.get("type", "unknown"),
                timestamp=item.get("timestamp"),
                description=item.get("description") or item.get("title"),
                source=item.get("source"),
                metadata={k: v for k, v in item.items() if k not in ("type", "timestamp", "description", "source")},
            )
        )

    return ChangeTimelineV1(
        api_version="1.0",
        generated_at=datetime.now(UTC),
        links=_building_links(str(building_id)),
        building_id=str(building_id),
        since=since.isoformat() if since else None,
        total_changes=len(entries),
        entries=entries,
    )


# ---------------------------------------------------------------------------
# Passport
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/passport",
    response_model=PassportV1,
)
async def get_passport(
    building_id: UUID,
    redaction_profile: str = Query(default="none"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Latest sovereign passport envelope with optional redaction."""
    await _get_building_or_404(db, building_id)

    from app.services.passport_service import get_passport_summary

    passport = await get_passport_summary(db, building_id)
    if passport is None:
        raise HTTPException(status_code=404, detail="Passport data not available")

    # Apply redaction if requested
    knowledge_state = passport["knowledge_state"]
    completeness = passport["completeness"]
    readiness = passport["readiness"]
    blind_spots = passport["blind_spots"]
    contradictions = passport["contradictions"]
    evidence_coverage = passport["evidence_coverage"]
    pollutant_coverage = passport["pollutant_coverage"]

    if redaction_profile == "external":
        # Strip detailed trust breakdown for external consumers
        knowledge_state = {
            "overall_trust": knowledge_state["overall_trust"],
            "trend": knowledge_state.get("trend"),
        }

    return PassportV1(
        api_version="1.0",
        generated_at=datetime.now(UTC),
        links=_building_links(str(building_id)),
        building_id=str(building_id),
        redaction_profile=redaction_profile,
        passport_grade=passport["passport_grade"],
        knowledge_state=knowledge_state,
        completeness=completeness,
        readiness=readiness,
        blind_spots=blind_spots,
        contradictions=contradictions,
        evidence_coverage=evidence_coverage,
        pollutant_coverage=pollutant_coverage,
    )


# ---------------------------------------------------------------------------
# Packs
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/packs/{pack_type}",
    response_model=PackV1,
)
async def get_pack(
    building_id: UUID,
    pack_type: str,
    redaction_profile: str = Query(default="none"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Audience-specific pack: authority, owner, insurer, contractor, notary, transfer."""
    await _get_building_or_404(db, building_id)

    from app.services.pack_builder_service import generate_pack

    try:
        pack_result = await generate_pack(
            db,
            building_id,
            pack_type,
            org_id=current_user.organization_id if hasattr(current_user, "organization_id") else None,
            created_by_id=current_user.id,
            redact_financials=(redaction_profile != "none"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    sections_data = []
    if hasattr(pack_result, "sections"):
        for s in pack_result.sections:
            sections_data.append(
                {
                    "section_name": s.section_name,
                    "section_type": s.section_type,
                    "items": s.items,
                    "completeness": s.completeness,
                    "notes": s.notes,
                }
            )

    return PackV1(
        api_version="1.0",
        generated_at=datetime.now(UTC),
        links=_building_links(str(building_id)),
        building_id=str(building_id),
        pack_type=pack_type,
        redaction_profile=redaction_profile,
        pack_version=getattr(pack_result, "pack_version", None),
        sections=sections_data,
        integrity_hash=getattr(pack_result, "integrity_hash", None),
        completeness_score=getattr(pack_result, "completeness_score", None),
    )


# ---------------------------------------------------------------------------
# Portfolio Overview
# ---------------------------------------------------------------------------


@router.get(
    "/portfolio/overview",
    response_model=PortfolioOverviewV1,
)
async def get_portfolio_overview(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio-level overview: grades, readiness, priorities, budget horizon."""
    from app.services.portfolio_command_service import get_portfolio_overview as _get_overview

    org_id = current_user.organization_id if hasattr(current_user, "organization_id") else None
    overview = await _get_overview(db, org_id=org_id)

    buildings = []
    for b in overview.get("buildings", []):
        buildings.append(
            PortfolioBuildingRowV1(
                building_id=b["id"],
                building_name=b["name"],
                passport_grade=b["passport_grade"],
                completeness_pct=b["completeness_pct"],
                trust_pct=b["trust_pct"],
                readiness_status=b["readiness_status"],
                open_actions_count=b.get("open_actions_count", 0),
                risk_level=b.get("risk_level", "unknown"),
            )
        )

    agg = overview.get("aggregates", {})

    return PortfolioOverviewV1(
        api_version="1.0",
        generated_at=datetime.now(UTC),
        links={
            "self": "/api/v1/truth/portfolio/overview",
            "alerts": "/api/v1/truth/portfolio/alerts",
        },
        org_id=str(org_id) if org_id else None,
        total_buildings=agg.get("total_buildings", 0),
        grade_distribution=agg.get("grade_distribution", {}),
        readiness_distribution=agg.get("readiness_distribution", {}),
        avg_completeness=agg.get("avg_completeness", 0.0),
        avg_trust=agg.get("avg_trust", 0.0),
        top_priorities=overview.get("top_priorities", []),
        budget_horizon=overview.get("budget_horizon", {}),
        buildings=buildings,
    )


# ---------------------------------------------------------------------------
# Portfolio Alerts
# ---------------------------------------------------------------------------


@router.get(
    "/portfolio/alerts",
    response_model=AlertsV1,
)
async def get_portfolio_alerts(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Predictive alerts across portfolio: overdue actions, expiring diagnostics, blocked readiness."""
    from app.services.today_service import get_today_feed

    org_id = current_user.organization_id if hasattr(current_user, "organization_id") else None
    feed = await get_today_feed(db, org_id=org_id, user_id=current_user.id)

    alerts: list[AlertV1] = []

    # Urgent items become critical/high alerts
    for item in feed.get("urgent", []):
        alerts.append(
            AlertV1(
                alert_type="urgent_action",
                severity=item.get("priority", "high"),
                building_id=item.get("building_id"),
                building_name=item.get("building_name"),
                title=item.get("title", "Action urgente"),
                description=item.get("description"),
                deadline=item.get("deadline"),
            )
        )

    # Blocked items
    for item in feed.get("blocked", []):
        alerts.append(
            AlertV1(
                alert_type="blocked",
                severity=item.get("impact", "high"),
                building_id=item.get("building_id"),
                building_name=item.get("building_name"),
                title=item.get("blocker_description", "Action bloquee"),
                description=f"Blocked since {item.get('blocked_since', '?')}",
            )
        )

    # Expiring diagnostics
    for item in feed.get("expiring_soon", []):
        alerts.append(
            AlertV1(
                alert_type="expiring_diagnostic",
                severity="medium" if (item.get("days_remaining", 90) > 30) else "high",
                building_id=item.get("building_id"),
                building_name=item.get("building_name"),
                title=f"Diagnostic {item.get('document_type', '')} expiring",
                description=f"Expires {item.get('expiry_date', '?')}",
                deadline=item.get("expiry_date"),
                days_remaining=item.get("days_remaining"),
            )
        )

    # Upcoming deadlines
    for item in feed.get("upcoming_deadlines", []):
        alerts.append(
            AlertV1(
                alert_type="upcoming_deadline",
                severity="high" if (item.get("days_remaining", 30) <= 7) else "medium",
                building_id=item.get("building_id"),
                building_name=item.get("building_name"),
                title=item.get("description", "Echeance"),
                deadline=item.get("deadline"),
                days_remaining=item.get("days_remaining"),
            )
        )

    return AlertsV1(
        api_version="1.0",
        generated_at=datetime.now(UTC),
        links={
            "self": "/api/v1/truth/portfolio/alerts",
            "overview": "/api/v1/truth/portfolio/overview",
        },
        org_id=str(org_id) if org_id else None,
        total_alerts=len(alerts),
        alerts=alerts,
    )
