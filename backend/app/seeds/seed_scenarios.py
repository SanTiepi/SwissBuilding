"""
SwissBuildingOS - Scenario Building Generators

Runs the 7 downstream generators (actions, post-works, readiness, trust,
unknowns, signals, contradictions) on the 5 scenario buildings seeded by
seed_data.py.

Idempotent: all generators use upsert / skip-existing logic.

Usage:
    python -m app.seeds.seed_scenarios
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.building import Building
from app.seeds.seed_data import SCENARIO_IDS

logger = logging.getLogger(__name__)

# Scenario buildings that have diagnostics (empty_dossier & portfolio_cluster don't)
_BUILDINGS_WITH_DIAGS: list[tuple[str, uuid.UUID, uuid.UUID | None]] = [
    ("contradiction", SCENARIO_IDS["contradiction"], SCENARIO_IDS["contradiction_diag_pos"]),
    ("nearly_ready", SCENARIO_IDS["nearly_ready"], SCENARIO_IDS["nearly_ready_diag"]),
    ("post_works", SCENARIO_IDS["post_works"], SCENARIO_IDS["post_works_diag"]),
]

_ALL_BUILDING_IDS: list[tuple[str, uuid.UUID]] = [
    ("contradiction", SCENARIO_IDS["contradiction"]),
    ("nearly_ready", SCENARIO_IDS["nearly_ready"]),
    ("post_works", SCENARIO_IDS["post_works"]),
    ("portfolio_cluster", SCENARIO_IDS["portfolio_cluster"]),
    ("empty_dossier", SCENARIO_IDS["empty_dossier"]),
]


async def _run_generators_for_building(
    db,
    name: str,
    building_id: uuid.UUID,
    diagnostic_id: uuid.UUID | None,
) -> dict:
    """Run all 7 generators for a single building, tolerating failures."""
    summary: dict[str, int | float | None] = {}

    # 1. Actions (needs diagnostic)
    if diagnostic_id:
        try:
            from app.services.action_generator import generate_actions_from_diagnostic

            actions = await generate_actions_from_diagnostic(db, building_id, diagnostic_id)
            summary["actions"] = len(actions)
        except Exception:
            logger.exception("[%s] Failed to generate actions", name)
            summary["actions"] = 0

    # 2. Post-works (only for post_works scenario with completed intervention)
    if name == "post_works":
        try:
            from app.services.post_works_service import generate_post_works_states

            pws = await generate_post_works_states(db, building_id, SCENARIO_IDS["post_works_intervention"])
            summary["post_works"] = len(pws)
        except Exception:
            logger.exception("[%s] Failed to generate post-works states", name)
            summary["post_works"] = 0

    # 3. Readiness
    try:
        from app.services.readiness_reasoner import evaluate_all_readiness

        assessments = await evaluate_all_readiness(db, building_id)
        summary["readiness"] = len(assessments)
    except Exception:
        logger.exception("[%s] Failed to evaluate readiness", name)
        summary["readiness"] = 0

    # 4. Trust score
    try:
        from app.services.trust_score_calculator import calculate_trust_score

        trust = await calculate_trust_score(db, building_id, assessed_by="seed_scenarios")
        summary["trust_score"] = trust.overall_score
    except Exception:
        logger.exception("[%s] Failed to calculate trust score", name)
        summary["trust_score"] = None

    # 5. Unknowns
    try:
        from app.services.unknown_generator import generate_unknowns

        unknowns = await generate_unknowns(db, building_id)
        summary["unknowns"] = len(unknowns)
    except Exception:
        logger.exception("[%s] Failed to generate unknowns", name)
        summary["unknowns"] = 0

    # 6. Change signals — migrated to canonical detect_signals (2026-03-28, Rail 1)
    # Uses change_tracker_service.detect_signals() which bridges: populates both
    # ChangeSignal (legacy) and BuildingSignal (canonical) tables.
    try:
        from app.services.change_tracker_service import detect_signals

        signals = await detect_signals(db, building_id)
        summary["signals"] = len(signals)
    except Exception:
        logger.exception("[%s] Failed to generate change signals", name)
        summary["signals"] = 0

    # 7. Contradictions
    try:
        from app.services.contradiction_detector import detect_contradictions

        contradictions = await detect_contradictions(db, building_id)
        summary["contradictions"] = len(contradictions)
    except Exception:
        logger.exception("[%s] Failed to detect contradictions", name)
        summary["contradictions"] = 0

    return summary


async def seed_scenarios() -> dict:
    """
    Run generators on all scenario buildings.
    Returns a summary dict keyed by scenario name.
    """
    async with AsyncSessionLocal() as db:
        # Verify at least one scenario building exists
        result = await db.execute(select(Building).where(Building.id == SCENARIO_IDS["contradiction"]))
        if result.scalar_one_or_none() is None:
            print("[SEED-SCENARIOS] Scenario buildings not found — run seed_data first.")
            return {"status": "skipped", "reason": "scenario buildings not seeded"}

        results: dict = {}

        # Run generators for buildings with diagnostics
        for name, b_id, d_id in _BUILDINGS_WITH_DIAGS:
            print(f"[SEED-SCENARIOS] Running generators for: {name}")
            summary = await _run_generators_for_building(db, name, b_id, d_id)
            results[name] = summary
            await db.commit()

        # Run generators for buildings without diagnostics (portfolio_cluster, empty_dossier)
        for name, b_id in _ALL_BUILDING_IDS:
            if name in results:
                continue
            print(f"[SEED-SCENARIOS] Running generators for: {name}")
            summary = await _run_generators_for_building(db, name, b_id, None)
            results[name] = summary
            await db.commit()

        print("[SEED-SCENARIOS] Done.")
        for name, summary in results.items():
            print(f"  {name}: {summary}")

        return {"status": "completed", **results}


if __name__ == "__main__":
    asyncio.run(seed_scenarios())
