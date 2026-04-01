"""BatiConnect — Conformance Check service.

Verifies that packs, imports, publications, and exchanges satisfy
named requirement profiles. Results are machine-readable, auditable.
No promise of legal certification.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conformance import ConformanceCheck, RequirementProfile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RequirementProfile CRUD
# ---------------------------------------------------------------------------


async def create_profile(
    db: AsyncSession,
    data: dict,
) -> RequirementProfile:
    """Create a new requirement profile."""
    profile = RequirementProfile(**data)
    db.add(profile)
    await db.flush()
    return profile


async def get_profile_by_name(
    db: AsyncSession,
    name: str,
) -> RequirementProfile | None:
    """Fetch a profile by its unique name."""
    result = await db.execute(
        select(RequirementProfile).where(
            RequirementProfile.name == name,
            RequirementProfile.active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_profiles(
    db: AsyncSession,
    profile_type: str | None = None,
    active_only: bool = True,
) -> list[RequirementProfile]:
    """List requirement profiles, optionally filtered by type."""
    stmt = select(RequirementProfile)
    if active_only:
        stmt = stmt.where(RequirementProfile.active.is_(True))
    if profile_type:
        stmt = stmt.where(RequirementProfile.profile_type == profile_type)
    stmt = stmt.order_by(RequirementProfile.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Run conformance check
# ---------------------------------------------------------------------------


async def run_conformance_check(
    db: AsyncSession,
    building_id: uuid.UUID,
    profile_name: str,
    target_type: str,
    target_id: uuid.UUID | None = None,
    checked_by_id: uuid.UUID | None = None,
) -> ConformanceCheck:
    """Run a conformance check against a named profile.

    Gathers building state (completeness, trust, readiness, unknowns,
    contradictions, pack sections) and evaluates each requirement in the
    profile. Returns a persisted ConformanceCheck with full detail.
    """
    profile = await get_profile_by_name(db, profile_name)
    if profile is None:
        raise ValueError(f"Requirement profile not found: {profile_name}")

    # Gather building state
    state = await _gather_building_state(db, building_id, target_type, target_id)

    # Evaluate each requirement
    passed: list[dict] = []
    failed: list[dict] = []
    warnings: list[dict] = []

    # 1. Required sections
    if profile.required_sections:
        available_sections = state.get("sections", [])
        for section in profile.required_sections:
            if section in available_sections:
                passed.append({"check": f"section:{section}", "status": "pass"})
            else:
                failed.append(
                    {
                        "check": f"section:{section}",
                        "status": "fail",
                        "reason": f"Section manquante: {section}",
                    }
                )

    # 2. Required fields
    if profile.required_fields:
        available_fields = state.get("fields", {})
        for field in profile.required_fields:
            value = available_fields.get(field)
            if value is not None:
                passed.append({"check": f"field:{field}", "status": "pass"})
            else:
                failed.append(
                    {
                        "check": f"field:{field}",
                        "status": "fail",
                        "reason": f"Champ requis manquant ou nul: {field}",
                    }
                )

    # 3. Minimum completeness
    if profile.minimum_completeness is not None:
        actual = state.get("completeness")
        if actual is not None and actual >= profile.minimum_completeness:
            passed.append(
                {
                    "check": "minimum_completeness",
                    "status": "pass",
                }
            )
        elif actual is not None:
            failed.append(
                {
                    "check": "minimum_completeness",
                    "status": "fail",
                    "reason": (f"Completude {actual:.0%} < minimum requis {profile.minimum_completeness:.0%}"),
                }
            )
        else:
            warnings.append(
                {
                    "check": "minimum_completeness",
                    "status": "warning",
                    "reason": "Completude non disponible",
                }
            )

    # 4. Minimum trust
    if profile.minimum_trust is not None:
        actual = state.get("trust")
        if actual is not None and actual >= profile.minimum_trust:
            passed.append({"check": "minimum_trust", "status": "pass"})
        elif actual is not None:
            failed.append(
                {
                    "check": "minimum_trust",
                    "status": "fail",
                    "reason": f"Confiance {actual:.0%} < minimum requis {profile.minimum_trust:.0%}",
                }
            )
        else:
            warnings.append(
                {
                    "check": "minimum_trust",
                    "status": "warning",
                    "reason": "Score de confiance non disponible",
                }
            )

    # 5. Required readiness verdicts
    if profile.required_readiness:
        readiness = state.get("readiness", {})
        for key, expected_status in profile.required_readiness.items():
            actual_status = readiness.get(key)
            if actual_status == expected_status:
                passed.append({"check": f"readiness:{key}", "status": "pass"})
            elif actual_status is not None:
                failed.append(
                    {
                        "check": f"readiness:{key}",
                        "status": "fail",
                        "reason": f"Readiness '{key}' = '{actual_status}', attendu '{expected_status}'",
                    }
                )
            else:
                warnings.append(
                    {
                        "check": f"readiness:{key}",
                        "status": "warning",
                        "reason": f"Readiness '{key}' non evalue",
                    }
                )

    # 6. Max unknowns
    if profile.max_unknowns is not None:
        open_unknowns = state.get("open_unknowns", 0)
        if open_unknowns <= profile.max_unknowns:
            passed.append({"check": "max_unknowns", "status": "pass"})
        else:
            failed.append(
                {
                    "check": "max_unknowns",
                    "status": "fail",
                    "reason": f"{open_unknowns} inconnu(s) ouvert(s) > maximum {profile.max_unknowns}",
                }
            )

    # 7. Max contradictions
    if profile.max_contradictions is not None:
        open_contradictions = state.get("open_contradictions", 0)
        if open_contradictions <= profile.max_contradictions:
            passed.append({"check": "max_contradictions", "status": "pass"})
        else:
            failed.append(
                {
                    "check": "max_contradictions",
                    "status": "fail",
                    "reason": (
                        f"{open_contradictions} contradiction(s) ouverte(s) > maximum {profile.max_contradictions}"
                    ),
                }
            )

    # 8. Redaction check
    if not profile.redaction_allowed:
        has_redaction = state.get("has_redaction", False)
        if not has_redaction:
            passed.append({"check": "no_redaction", "status": "pass"})
        else:
            failed.append(
                {
                    "check": "no_redaction",
                    "status": "fail",
                    "reason": "Ce profil interdit les redactions, mais des donnees sont masquees",
                }
            )

    # Compute score and result
    total = len(passed) + len(failed) + len(warnings)
    score = len(passed) / total if total > 0 else 0.0

    if len(failed) == 0 and len(warnings) == 0:
        result = "pass"
    elif len(failed) == 0:
        result = "partial"
    else:
        result = "fail"

    # Build summary
    summary_parts = [
        f"Profil: {profile.name}",
        f"Resultat: {result}",
        f"Score: {score:.0%}",
        f"Reussis: {len(passed)}, Echoues: {len(failed)}, Avertissements: {len(warnings)}",
    ]
    summary = " | ".join(summary_parts)

    # Persist
    check = ConformanceCheck(
        building_id=building_id,
        profile_id=profile.id,
        checked_by_id=checked_by_id,
        target_type=target_type,
        target_id=target_id,
        result=result,
        score=round(score, 4),
        checks_passed=passed,
        checks_failed=failed,
        checks_warning=warnings,
        summary=summary,
        checked_at=datetime.now(UTC),
    )
    db.add(check)
    await db.flush()
    return check


# ---------------------------------------------------------------------------
# Query checks
# ---------------------------------------------------------------------------


async def get_building_checks(
    db: AsyncSession,
    building_id: uuid.UUID,
    limit: int = 20,
) -> list[ConformanceCheck]:
    """List conformance checks for a building, most recent first."""
    stmt = (
        select(ConformanceCheck)
        .where(ConformanceCheck.building_id == building_id)
        .order_by(ConformanceCheck.checked_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_check_summary(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> dict:
    """Summary counts of conformance checks for a building."""
    stmt = select(
        func.count(ConformanceCheck.id).label("total"),
        func.sum(func.cast(ConformanceCheck.result == "pass", Integer)).label("passed"),
        func.sum(func.cast(ConformanceCheck.result == "fail", Integer)).label("failed"),
        func.sum(func.cast(ConformanceCheck.result == "partial", Integer)).label("partial"),
    ).where(ConformanceCheck.building_id == building_id)
    result = await db.execute(stmt)
    row = result.one()

    # Latest check
    latest_stmt = (
        select(ConformanceCheck)
        .where(ConformanceCheck.building_id == building_id)
        .order_by(ConformanceCheck.checked_at.desc())
        .limit(1)
    )
    latest_result = await db.execute(latest_stmt)
    latest = latest_result.scalar_one_or_none()

    return {
        "building_id": building_id,
        "total_checks": row.total or 0,
        "passed": row.passed or 0,
        "failed": row.failed or 0,
        "partial": row.partial or 0,
        "latest_check": latest,
    }


# ---------------------------------------------------------------------------
# Internal: gather building state for conformance evaluation
# ---------------------------------------------------------------------------


async def _gather_building_state(
    db: AsyncSession,
    building_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID | None,
) -> dict:
    """Gather relevant building state for conformance checking.

    Pulls completeness, trust, readiness, unknowns, contradictions,
    and available pack sections from existing services.
    """
    state: dict = {
        "sections": [],
        "fields": {},
        "completeness": None,
        "trust": None,
        "readiness": {},
        "open_unknowns": 0,
        "open_contradictions": 0,
        "has_redaction": False,
    }

    # 1. Passport summary (completeness, trust, readiness, grade)
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            # Completeness
            comp = passport.get("completeness", {})
            if isinstance(comp, dict) and "overall_score" in comp:
                state["completeness"] = comp["overall_score"]

            # Trust
            ks = passport.get("knowledge_state", {})
            if isinstance(ks, dict) and "overall_trust" in ks:
                state["trust"] = ks["overall_trust"]

            # Readiness
            readiness = passport.get("readiness", {})
            if isinstance(readiness, dict):
                for key, val in readiness.items():
                    if isinstance(val, dict):
                        state["readiness"][key] = val.get("status")
                    else:
                        state["readiness"][key] = val

            # Fields from passport
            state["fields"]["passport_grade"] = passport.get("passport_grade")
            state["fields"]["address"] = passport.get("address")
            state["fields"]["canton"] = passport.get("canton")

            # Sections from passport
            for section_key in [
                "knowledge_state",
                "completeness",
                "readiness",
                "blind_spots",
                "contradictions",
                "evidence_coverage",
            ]:
                if passport.get(section_key) is not None:
                    state["sections"].append(section_key)
    except Exception:
        logger.debug("Passport summary not available for %s", building_id)

    # 2. Pack sections (if target_type is pack)
    if target_type == "pack":
        try:
            from app.services.pack_builder_service import PACK_TYPES

            for _pack_name, pack_def in PACK_TYPES.items():
                for section in pack_def.get("sections", []):
                    if section not in state["sections"]:
                        state["sections"].append(section)
        except Exception:
            pass

    # 3. Open unknowns count
    try:
        from app.models.unknowns_ledger import UnknownEntry

        result = await db.execute(
            select(func.count(UnknownEntry.id)).where(
                UnknownEntry.building_id == building_id,
                UnknownEntry.status.in_(["open", "investigating"]),
            )
        )
        state["open_unknowns"] = result.scalar() or 0
    except Exception:
        pass

    # 4. Open contradictions count
    try:
        from app.models.data_quality_issue import DataQualityIssue

        result = await db.execute(
            select(func.count(DataQualityIssue.id)).where(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
                DataQualityIssue.status != "resolved",
            )
        )
        state["open_contradictions"] = result.scalar() or 0
    except Exception:
        pass

    # 5. Building basic fields
    try:
        from app.models.building import Building

        result = await db.execute(select(Building).where(Building.id == building_id))
        building = result.scalar_one_or_none()
        if building:
            state["fields"]["address"] = building.address
            state["fields"]["city"] = building.city
            state["fields"]["canton"] = building.canton
            state["fields"]["construction_year"] = building.construction_year
            state["fields"]["building_type"] = building.building_type
    except Exception:
        pass

    return state
