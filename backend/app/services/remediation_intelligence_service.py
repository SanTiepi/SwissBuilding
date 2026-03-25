"""BatiConnect — Remediation Intelligence / Flywheel service.

Org-scoped benchmarks, flywheel trends, knowledge density, and learning overview.
Never cross-org unless anonymized.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_extraction_log import AIExtractionLog
from app.models.ai_feedback import AIFeedback
from app.models.ai_rule_pattern import AIRulePattern
from app.models.building import Building
from app.models.intervention import Intervention
from app.schemas.intelligence_stack import (
    FlywheelTrendPoint,
    KnowledgeDensityTrend,
    ModuleLearningOverview,
    PollutantBenchmark,
    RemediationBenchmarkSnapshot,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


async def get_benchmark(db: AsyncSession, org_id: uuid.UUID) -> RemediationBenchmarkSnapshot:
    """Avg remediation cost by pollutant, avg cycle time, completion rate. Org-scoped."""
    # Get buildings for this org
    bld_ids_result = await db.execute(select(Building.id).where(Building.organization_id == org_id))
    bld_ids = [row[0] for row in bld_ids_result.all()]

    benchmarks: list[PollutantBenchmark] = []
    all_costs: list[float] = []
    all_cycles: list[float] = []
    total_completed = 0
    total_interventions = 0

    if bld_ids:
        # Group interventions by pollutant_type (derived from intervention_type for simplicity)
        intv_result = await db.execute(select(Intervention).where(Intervention.building_id.in_(bld_ids)))
        interventions = intv_result.scalars().all()

        # Group by intervention_type as proxy for pollutant
        by_type: dict[str, list] = {}
        for intv in interventions:
            key = intv.intervention_type or "unknown"
            by_type.setdefault(key, []).append(intv)

        for pollutant, intvs in by_type.items():
            costs = [float(i.cost_chf or 0) for i in intvs if i.cost_chf]
            completed = [i for i in intvs if i.status == "completed"]
            total_interventions += len(intvs)
            total_completed += len(completed)

            avg_cost = sum(costs) / len(costs) if costs else 0.0
            all_costs.extend(costs)

            # Cycle time: completed_at - created_at
            cycle_days = []
            for c in completed:
                if c.updated_at and c.created_at:
                    delta = (c.updated_at - c.created_at).days
                    cycle_days.append(float(delta))
            avg_cycle = sum(cycle_days) / len(cycle_days) if cycle_days else 0.0
            all_cycles.extend(cycle_days)

            completion_rate = len(completed) / len(intvs) if intvs else 0.0

            benchmarks.append(
                PollutantBenchmark(
                    pollutant=pollutant,
                    avg_cost_chf=round(avg_cost, 2),
                    avg_cycle_days=round(avg_cycle, 1),
                    completion_rate=round(completion_rate, 2),
                    sample_size=len(intvs),
                )
            )

    overall_cost = sum(all_costs) / len(all_costs) if all_costs else 0.0
    overall_cycle = sum(all_cycles) / len(all_cycles) if all_cycles else 0.0
    overall_completion = total_completed / total_interventions if total_interventions else 0.0

    return RemediationBenchmarkSnapshot(
        org_id=org_id,
        benchmarks=benchmarks,
        overall_avg_cost_chf=round(overall_cost, 2),
        overall_avg_cycle_days=round(overall_cycle, 1),
        overall_completion_rate=round(overall_completion, 2),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Flywheel Trends
# ---------------------------------------------------------------------------


async def get_flywheel_trends(
    db: AsyncSession,
    org_id: uuid.UUID,
    days: int = 90,
) -> list[FlywheelTrendPoint]:
    """Time series: extraction quality, correction rate, cycle time, knowledge density."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Get extraction logs after cutoff
    ext_result = await db.execute(
        select(AIExtractionLog).where(AIExtractionLog.created_at >= cutoff).order_by(AIExtractionLog.created_at)
    )
    logs = ext_result.scalars().all()

    # Group by week
    weeks: dict[str, list] = {}
    for log in logs:
        if log.created_at:
            week_key = log.created_at.strftime("%Y-W%W")
            weeks.setdefault(week_key, []).append(log)

    # Get feedback counts for correction rate
    fb_result = await db.execute(
        select(AIFeedback.feedback_type, func.count(AIFeedback.id))
        .where(AIFeedback.created_at >= cutoff)
        .group_by(AIFeedback.feedback_type)
    )
    feedback_counts = {row[0]: row[1] for row in fb_result.all()}
    total_fb = sum(feedback_counts.values())
    correction_rate = feedback_counts.get("correct", 0) / total_fb if total_fb > 0 else 0.0

    # Knowledge density
    density = await get_knowledge_density(db, org_id)

    points: list[FlywheelTrendPoint] = []
    for week_key in sorted(weeks.keys()):
        week_logs = weeks[week_key]
        avg_conf = sum(wl.confidence_score or 0 for wl in week_logs) / len(week_logs) if week_logs else 0
        avg_latency = sum(wl.latency_ms or 0 for wl in week_logs) / len(week_logs) if week_logs else 0

        points.append(
            FlywheelTrendPoint(
                date=week_key,
                extraction_quality=round(avg_conf, 3),
                correction_rate=round(correction_rate, 3),
                cycle_time_days=round(avg_latency / 1000 / 86400, 2) if avg_latency else None,
                knowledge_density=round(density, 3),
            )
        )

    return points


# ---------------------------------------------------------------------------
# Knowledge Density
# ---------------------------------------------------------------------------


async def get_knowledge_density(db: AsyncSession, org_id: uuid.UUID) -> float:
    """completed_cycles / total_buildings_with_remediation."""
    bld_ids_result = await db.execute(select(Building.id).where(Building.organization_id == org_id))
    bld_ids = [row[0] for row in bld_ids_result.all()]

    if not bld_ids:
        return 0.0

    # Buildings with at least one intervention
    bld_with_intv = await db.execute(
        select(func.count(func.distinct(Intervention.building_id))).where(Intervention.building_id.in_(bld_ids))
    )
    total_with = bld_with_intv.scalar() or 0

    # Completed interventions
    completed_result = await db.execute(
        select(func.count(Intervention.id)).where(
            Intervention.building_id.in_(bld_ids),
            Intervention.status == "completed",
        )
    )
    completed = completed_result.scalar() or 0

    if total_with == 0:
        return 0.0

    return completed / total_with


async def get_knowledge_density_trend(db: AsyncSession, org_id: uuid.UUID) -> KnowledgeDensityTrend:
    """Knowledge density with context."""
    density = await get_knowledge_density(db, org_id)

    bld_ids_result = await db.execute(select(Building.id).where(Building.organization_id == org_id))
    bld_ids = [row[0] for row in bld_ids_result.all()]

    completed_result = await db.execute(
        select(func.count(Intervention.id)).where(
            Intervention.building_id.in_(bld_ids) if bld_ids else Intervention.id.is_(None),
            Intervention.status == "completed",
        )
    )
    completed = completed_result.scalar() or 0

    bld_with_intv = await db.execute(
        select(func.count(func.distinct(Intervention.building_id))).where(
            Intervention.building_id.in_(bld_ids) if bld_ids else Intervention.id.is_(None),
        )
    )
    total_with = bld_with_intv.scalar() or 0

    return KnowledgeDensityTrend(
        org_id=org_id,
        density=round(density, 3),
        completed_cycles=completed,
        total_buildings=total_with,
    )


# ---------------------------------------------------------------------------
# Module Learning Overview (admin-only)
# ---------------------------------------------------------------------------


async def get_learning_overview(db: AsyncSession) -> ModuleLearningOverview:
    """Admin-only: total patterns, extraction success rate, avg confidence, top corrections."""
    # Total patterns
    pattern_count = await db.execute(select(func.count(AIRulePattern.id)).where(AIRulePattern.is_active.is_(True)))
    total_patterns = pattern_count.scalar() or 0

    # Total extractions
    ext_count = await db.execute(select(func.count(AIExtractionLog.id)))
    total_extractions = ext_count.scalar() or 0

    # Success rate (non-failed / total)
    success_count = await db.execute(select(func.count(AIExtractionLog.id)).where(AIExtractionLog.status != "failed"))
    successes = success_count.scalar() or 0
    success_rate = successes / total_extractions if total_extractions > 0 else 0.0

    # Avg confidence
    avg_conf = await db.execute(
        select(func.avg(AIExtractionLog.confidence_score)).where(AIExtractionLog.confidence_score.isnot(None))
    )
    avg_confidence = float(avg_conf.scalar() or 0.0)

    # Total feedbacks
    fb_count = await db.execute(select(func.count(AIFeedback.id)))
    total_feedbacks = fb_count.scalar() or 0

    # Top correction categories
    correction_result = await db.execute(
        select(AIFeedback.entity_type, func.count(AIFeedback.id))
        .where(AIFeedback.feedback_type == "correct")
        .group_by(AIFeedback.entity_type)
        .order_by(func.count(AIFeedback.id).desc())
        .limit(5)
    )
    top_corrections = [{"category": row[0], "count": row[1]} for row in correction_result.all()]

    return ModuleLearningOverview(
        total_patterns=total_patterns,
        extraction_success_rate=round(success_rate, 3),
        avg_confidence=round(avg_confidence, 3),
        top_correction_categories=top_corrections,
        total_extractions=total_extractions,
        total_feedbacks=total_feedbacks,
    )
