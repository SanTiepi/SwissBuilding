"""
SwissBuildingOS - Risk Aggregation Service

Computes a unified multi-dimensional risk score (0-100) for buildings by
combining five risk dimensions:
  - Pollutant risk (40%)
  - Compliance risk (25%)
  - Structural risk (15%)
  - Financial risk (10%)
  - Operational risk (10%)

Provides decomposition, correlation mapping, and portfolio-level heatmaps.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.schemas.risk_aggregation import (
    BuildingRiskCell,
    PortfolioRiskMatrix,
    RiskContributor,
    RiskCorrelation,
    RiskCorrelationMap,
    RiskDecomposition,
    RiskDimensionDetail,
    RiskHotspot,
    UnifiedRiskScore,
    WaterfallSegment,
)

# ---------------------------------------------------------------------------
# Dimension weights
# ---------------------------------------------------------------------------

DIMENSION_WEIGHTS: dict[str, float] = {
    "pollutant": 0.40,
    "compliance": 0.25,
    "structural": 0.15,
    "financial": 0.10,
    "operational": 0.10,
}

GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (40, "D"),
    (20, "E"),
    (0, "F"),
]


def _score_to_grade(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Per-dimension raw score calculators (0-100, higher = MORE risk)
# ---------------------------------------------------------------------------


async def _calc_pollutant_score(db: AsyncSession, building_id: UUID) -> tuple[float, list[RiskContributor]]:
    """Pollutant risk from BuildingRiskScore probabilities."""
    result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk = result.scalar_one_or_none()

    if not risk:
        return 50.0, [RiskContributor(name="no_data", impact=50.0, description="No risk assessment available")]

    probs = {
        "asbestos": risk.asbestos_probability or 0.0,
        "pcb": risk.pcb_probability or 0.0,
        "lead": risk.lead_probability or 0.0,
        "hap": risk.hap_probability or 0.0,
        "radon": risk.radon_probability or 0.0,
    }
    # Weighted average of probabilities scaled to 0-100
    weights = {"asbestos": 0.30, "pcb": 0.20, "lead": 0.20, "hap": 0.15, "radon": 0.15}
    score = sum(probs[p] * weights[p] for p in probs) * 100
    score = max(0.0, min(100.0, score))

    contributors = sorted(
        [
            RiskContributor(name=p, impact=round(probs[p] * 100, 1), description=f"{p} probability {probs[p]:.0%}")
            for p in probs
        ],
        key=lambda c: c.impact,
        reverse=True,
    )[:3]

    return round(score, 1), contributors


async def _calc_compliance_score(db: AsyncSession, building_id: UUID) -> tuple[float, list[RiskContributor]]:
    """Compliance risk based on overdue / pending actions and diagnostic coverage."""
    result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(result.scalars().all())

    if not actions:
        return 40.0, [RiskContributor(name="no_actions", impact=40.0, description="No action items recorded")]

    total = len(actions)
    overdue = sum(1 for a in actions if getattr(a, "status", "") == "overdue")
    pending = sum(1 for a in actions if getattr(a, "status", "") in ("pending", "open"))

    score = min(100.0, (overdue / max(total, 1)) * 60 + (pending / max(total, 1)) * 30 + 10)

    contributors = [
        RiskContributor(
            name="overdue_actions",
            impact=round(overdue / max(total, 1) * 60, 1),
            description=f"{overdue}/{total} actions overdue",
        ),
        RiskContributor(
            name="pending_actions",
            impact=round(pending / max(total, 1) * 30, 1),
            description=f"{pending}/{total} actions pending",
        ),
    ]
    return round(score, 1), sorted(contributors, key=lambda c: c.impact, reverse=True)[:3]


async def _calc_structural_score(db: AsyncSession, building_id: UUID) -> tuple[float, list[RiskContributor]]:
    """Structural risk from building elements condition."""
    from app.models.zone import Zone

    result = await db.execute(
        select(BuildingElement).join(Zone, BuildingElement.zone_id == Zone.id).where(Zone.building_id == building_id)
    )
    elements = list(result.scalars().all())

    if not elements:
        return 30.0, [RiskContributor(name="no_elements", impact=30.0, description="No structural data available")]

    condition_scores = {"good": 10, "fair": 40, "degraded": 70, "critical": 95}
    total_score = sum(condition_scores.get(getattr(e, "condition", "fair"), 40) for e in elements)
    score = min(100.0, total_score / len(elements))

    degraded = sum(1 for e in elements if getattr(e, "condition", "") in ("degraded", "critical"))
    contributors = [
        RiskContributor(
            name="degraded_elements",
            impact=round(degraded / max(len(elements), 1) * 100, 1),
            description=f"{degraded}/{len(elements)} elements in poor condition",
        ),
    ]
    return round(score, 1), contributors[:3]


async def _calc_financial_score(db: AsyncSession, building_id: UUID) -> tuple[float, list[RiskContributor]]:
    """Financial risk from pending interventions and remediation costs."""
    result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.status.in_(["planned", "in_progress"]),
        )
    )
    interventions = list(result.scalars().all())

    if not interventions:
        return 20.0, [RiskContributor(name="no_interventions", impact=20.0, description="No planned interventions")]

    # More pending interventions = higher financial risk
    score = min(100.0, len(interventions) * 20)
    contributors = [
        RiskContributor(
            name="pending_interventions",
            impact=round(score, 1),
            description=f"{len(interventions)} interventions planned or in progress",
        ),
    ]
    return round(score, 1), contributors[:3]


async def _calc_operational_score(db: AsyncSession, building_id: UUID) -> tuple[float, list[RiskContributor]]:
    """Operational risk from documentation gaps and diagnostic freshness."""
    doc_result = await db.execute(
        select(sa_func.count()).select_from(Document).where(Document.building_id == building_id)
    )
    doc_count = doc_result.scalar() or 0

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    contributors: list[RiskContributor] = []

    # Fewer docs = higher operational risk
    doc_risk = max(0.0, 60 - doc_count * 10)
    contributors.append(
        RiskContributor(name="documentation", impact=round(doc_risk, 1), description=f"{doc_count} documents on file")
    )

    # No diagnostics or only drafts = higher risk
    completed = sum(1 for d in diagnostics if getattr(d, "status", "") in ("completed", "validated"))
    diag_risk = 60.0 if not completed else max(0.0, 40 - completed * 15)
    contributors.append(
        RiskContributor(
            name="diagnostics", impact=round(diag_risk, 1), description=f"{completed} completed diagnostics"
        )
    )

    score = min(100.0, (doc_risk + diag_risk) / 2)
    return round(score, 1), sorted(contributors, key=lambda c: c.impact, reverse=True)[:3]


# ---------------------------------------------------------------------------
# Dimension calculators registry
# ---------------------------------------------------------------------------

_CALCULATORS = {
    "pollutant": _calc_pollutant_score,
    "compliance": _calc_compliance_score,
    "structural": _calc_structural_score,
    "financial": _calc_financial_score,
    "operational": _calc_operational_score,
}


async def _compute_all_dimensions(
    db: AsyncSession,
    building_id: UUID,
) -> dict[str, tuple[float, list[RiskContributor]]]:
    results: dict[str, tuple[float, list[RiskContributor]]] = {}
    for dim, calc in _CALCULATORS.items():
        results[dim] = await calc(db, building_id)
    return results


# ---------------------------------------------------------------------------
# FN1: get_unified_risk_score
# ---------------------------------------------------------------------------


async def get_unified_risk_score(db: AsyncSession, building_id: UUID) -> UnifiedRiskScore:
    """Single composite risk score 0-100 combining all dimensions."""
    # Verify building exists
    bld = await db.execute(select(Building).where(Building.id == building_id))
    building = bld.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")

    dim_results = await _compute_all_dimensions(db, building_id)

    weighted: dict[str, float] = {}
    total = 0.0
    for dim, (raw, _) in dim_results.items():
        w = DIMENSION_WEIGHTS[dim]
        contribution = raw * w
        weighted[dim] = round(contribution, 2)
        total += contribution

    overall = round(min(100.0, max(0.0, total)), 1)
    grade = _score_to_grade(100 - overall)  # invert: high risk score = low grade

    # Peer comparison: average across buildings in same org
    peer_avg = overall  # default to self
    percentile = 50.0

    if building.created_by:
        peer_result = await db.execute(
            select(Building.id).where(
                Building.created_by == building.created_by,
                Building.id != building_id,
            )
        )
        peer_ids = [r[0] for r in peer_result.all()]

        if peer_ids:
            peer_scores: list[float] = []
            for pid in peer_ids[:20]:  # limit to 20 peers for performance
                try:
                    pr = await _compute_all_dimensions(db, pid)
                    ps = sum(raw * DIMENSION_WEIGHTS[d] for d, (raw, _) in pr.items())
                    peer_scores.append(ps)
                except Exception:
                    continue

            if peer_scores:
                peer_avg = round(sum(peer_scores) / len(peer_scores), 1)
                below = sum(1 for s in peer_scores if s >= overall)
                percentile = round(below / len(peer_scores) * 100, 1)

    return UnifiedRiskScore(
        building_id=building_id,
        overall_score=overall,
        grade=grade,
        dimensions=weighted,
        peer_average=peer_avg,
        percentile=percentile,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: get_risk_decomposition
# ---------------------------------------------------------------------------


def _infer_trend(raw_score: float) -> str:
    if raw_score < 30:
        return "improving"
    if raw_score > 70:
        return "worsening"
    return "stable"


_MITIGATION_MAP: dict[str, list[str]] = {
    "pollutant": ["Commission diagnostic complet", "Remediation programme", "Monitor high-risk zones"],
    "compliance": ["Clear overdue actions", "Schedule regulatory review", "Update cantonal filing"],
    "structural": ["Structural assessment", "Repair degraded elements", "Preventive maintenance plan"],
    "financial": ["Budget forecast for interventions", "Phase costly remediations", "Apply for subsidies"],
    "operational": ["Complete documentation", "Schedule periodic diagnostics", "Staff training"],
}


async def get_risk_decomposition(db: AsyncSession, building_id: UUID) -> RiskDecomposition:
    """Per-dimension drill-down with waterfall chart data."""
    bld = await db.execute(select(Building).where(Building.id == building_id))
    if not bld.scalar_one_or_none():
        raise ValueError(f"Building {building_id} not found")

    dim_results = await _compute_all_dimensions(db, building_id)

    dimensions: list[RiskDimensionDetail] = []
    waterfall: list[WaterfallSegment] = []
    cumulative = 0.0

    for dim in DIMENSION_WEIGHTS:
        raw, contribs = dim_results[dim]
        w = DIMENSION_WEIGHTS[dim]
        ws = round(raw * w, 2)
        cumulative += ws

        dimensions.append(
            RiskDimensionDetail(
                dimension=dim,
                raw_score=raw,
                weight=w,
                weighted_score=ws,
                trend=_infer_trend(raw),
                top_contributors=contribs[:3],
                mitigation_options=_MITIGATION_MAP.get(dim, []),
            )
        )
        waterfall.append(
            WaterfallSegment(
                dimension=dim,
                contribution=ws,
                cumulative=round(cumulative, 2),
            )
        )

    overall = round(cumulative, 1)

    return RiskDecomposition(
        building_id=building_id,
        overall_score=overall,
        grade=_score_to_grade(100 - overall),
        dimensions=dimensions,
        waterfall=waterfall,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: get_risk_correlation_map
# ---------------------------------------------------------------------------

_CORRELATION_DEFINITIONS: list[dict] = [
    {
        "source": "pollutant",
        "target": "compliance",
        "base_strength": 0.85,
        "direction": "positive",
        "description": "High pollutant risk drives compliance obligations",
    },
    {
        "source": "compliance",
        "target": "financial",
        "base_strength": 0.70,
        "direction": "positive",
        "description": "Compliance gaps increase financial exposure (fines, remediation)",
    },
    {
        "source": "structural",
        "target": "pollutant",
        "base_strength": 0.55,
        "direction": "positive",
        "description": "Degraded structures release more pollutants (friable asbestos, lead dust)",
    },
    {
        "source": "pollutant",
        "target": "financial",
        "base_strength": 0.60,
        "direction": "positive",
        "description": "Pollutant presence increases remediation costs",
    },
    {
        "source": "operational",
        "target": "compliance",
        "base_strength": 0.50,
        "direction": "positive",
        "description": "Operational gaps (missing docs, stale diagnostics) hinder compliance",
    },
    {
        "source": "structural",
        "target": "financial",
        "base_strength": 0.45,
        "direction": "positive",
        "description": "Structural issues increase maintenance and repair costs",
    },
]

_CASCADE_CHAINS: list[list[str]] = [
    ["pollutant", "compliance", "financial"],
    ["structural", "pollutant", "compliance"],
    ["operational", "compliance", "financial"],
]


async def get_risk_correlation_map(db: AsyncSession, building_id: UUID) -> RiskCorrelationMap:
    """Which risks are correlated for a given building."""
    bld = await db.execute(select(Building).where(Building.id == building_id))
    if not bld.scalar_one_or_none():
        raise ValueError(f"Building {building_id} not found")

    dim_results = await _compute_all_dimensions(db, building_id)

    correlations: list[RiskCorrelation] = []
    for cdef in _CORRELATION_DEFINITIONS:
        src_score = dim_results[cdef["source"]][0]
        tgt_score = dim_results[cdef["target"]][0]

        # Modulate strength: if both dimensions are elevated, correlation is stronger
        avg_risk = (src_score + tgt_score) / 200  # 0-1
        strength = round(min(1.0, cdef["base_strength"] * (0.5 + avg_risk)), 2)

        correlations.append(
            RiskCorrelation(
                source=cdef["source"],
                target=cdef["target"],
                strength=strength,
                direction=cdef["direction"],
                description=cdef["description"],
            )
        )

    return RiskCorrelationMap(
        building_id=building_id,
        correlations=correlations,
        cascade_chains=_CASCADE_CHAINS,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_risk_matrix
# ---------------------------------------------------------------------------

_SEVERITY_THRESHOLDS: list[tuple[float, str]] = [
    (75, "critical"),
    (55, "high"),
    (30, "medium"),
    (0, "low"),
]


def _score_to_severity(score: float) -> str:
    for threshold, severity in _SEVERITY_THRESHOLDS:
        if score >= threshold:
            return severity
    return "low"


async def get_portfolio_risk_matrix(db: AsyncSession, org_id: UUID) -> PortfolioRiskMatrix:
    """2D matrix: buildings x risk dimensions with hotspot identification."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    dim_names = list(DIMENSION_WEIGHTS.keys())
    cells: list[BuildingRiskCell] = []
    dim_scores: dict[str, list[float]] = {d: [] for d in dim_names}

    for building in buildings[:50]:  # limit for performance
        dim_results = await _compute_all_dimensions(db, building.id)
        for dim in dim_names:
            raw = dim_results[dim][0]
            cells.append(
                BuildingRiskCell(
                    building_id=building.id,
                    address=building.address,
                    city=building.city,
                    dimension=dim,
                    score=raw,
                )
            )
            dim_scores[dim].append(raw)

    # Hotspot identification
    hotspots: list[RiskHotspot] = []
    systemic: list[str] = []

    for dim in dim_names:
        scores = dim_scores[dim]
        if not scores:
            continue
        avg = sum(scores) / len(scores)
        high_count = sum(1 for s in scores if s >= 55)

        if high_count > 0:
            hotspots.append(
                RiskHotspot(
                    dimension=dim,
                    affected_building_count=high_count,
                    average_score=round(avg, 1),
                    severity=_score_to_severity(avg),
                )
            )

        # Systemic pattern: ≥50% of buildings have elevated risk in this dimension
        if len(scores) > 0 and high_count / len(scores) >= 0.5:
            systemic.append(f"Systemic {dim} risk: {high_count}/{len(scores)} buildings above threshold")

    return PortfolioRiskMatrix(
        organization_id=org_id,
        building_count=len(buildings),
        dimensions=dim_names,
        cells=cells,
        hotspots=sorted(hotspots, key=lambda h: h.average_score, reverse=True),
        systemic_patterns=systemic,
        evaluated_at=datetime.now(UTC),
    )
