"""
Collective Field Memory Service — pattern detection across field observations.

Surfaces patterns like "In 1970s buildings in Vaud with flat roofs, PCB is often found in joint sealants."
Groups observations by tags + context (canton, year range, pollutant, material) and returns insights.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.field_observation import FieldObservation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


async def record_observation(
    db: AsyncSession,
    building_id: UUID | None,
    observer_id: UUID,
    observer_role: str | None,
    observation_type: str,
    title: str,
    description: str | None,
    tags: list[str] | None,
    context: dict | None,
    confidence: str,
    photo_ref: str | None = None,
) -> FieldObservation:
    """Create a new field observation with collective-memory fields."""
    obs = FieldObservation(
        building_id=building_id,
        observer_id=observer_id,
        observer_role=observer_role,
        observation_type=observation_type,
        title=title,
        description=description,
        tags=json.dumps(tags) if tags else None,
        context_json=json.dumps(context) if context else None,
        confidence=confidence,
        photo_reference=photo_ref,
        observed_at=datetime.now(UTC),
        status="active",
    )
    db.add(obs)
    await db.commit()
    await db.refresh(obs)
    return obs


# ---------------------------------------------------------------------------
# Per-building observations
# ---------------------------------------------------------------------------


async def get_building_observations(
    db: AsyncSession,
    building_id: UUID,
    page: int = 1,
    size: int = 20,
) -> tuple[list[FieldObservation], int]:
    """List observations for a specific building with pagination."""
    base = select(FieldObservation).where(FieldObservation.building_id == building_id)
    count_q = select(func.count()).select_from(FieldObservation).where(FieldObservation.building_id == building_id)

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    query = base.order_by(FieldObservation.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = list(result.scalars().all())
    return items, total


# ---------------------------------------------------------------------------
# Cross-building search
# ---------------------------------------------------------------------------


async def search_observations(
    db: AsyncSession,
    *,
    tags: list[str] | None = None,
    canton: str | None = None,
    construction_year_min: int | None = None,
    construction_year_max: int | None = None,
    pollutant: str | None = None,
    material: str | None = None,
    observation_type: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[FieldObservation], int]:
    """Search observations across all buildings using tags and context filters."""
    query = select(FieldObservation).where(FieldObservation.status == "active")
    count_q = select(func.count()).select_from(FieldObservation).where(FieldObservation.status == "active")

    if observation_type:
        query = query.where(FieldObservation.observation_type == observation_type)
        count_q = count_q.where(FieldObservation.observation_type == observation_type)

    # Tag filtering: check if any requested tag appears in the JSON array
    if tags:
        for tag in tags:
            like_pattern = f'%"{tag}"%'
            query = query.where(FieldObservation.tags.ilike(like_pattern))
            count_q = count_q.where(FieldObservation.tags.ilike(like_pattern))

    # Context-based filters: search within context_json
    if canton:
        like_pattern = f'%"canton": "{canton}"%'
        # Also handle without spaces
        like_pattern_alt = f'%"canton":"{canton}"%'
        query = query.where(
            FieldObservation.context_json.ilike(like_pattern) | FieldObservation.context_json.ilike(like_pattern_alt)
        )
        count_q = count_q.where(
            FieldObservation.context_json.ilike(like_pattern) | FieldObservation.context_json.ilike(like_pattern_alt)
        )

    if pollutant:
        like_pattern = f'%"pollutant": "{pollutant}"%'
        like_pattern_alt = f'%"pollutant":"{pollutant}"%'
        query = query.where(
            FieldObservation.context_json.ilike(like_pattern) | FieldObservation.context_json.ilike(like_pattern_alt)
        )
        count_q = count_q.where(
            FieldObservation.context_json.ilike(like_pattern) | FieldObservation.context_json.ilike(like_pattern_alt)
        )

    if material:
        like_pattern = f'%"material": "{material}"%'
        like_pattern_alt = f'%"material":"{material}"%'
        query = query.where(
            FieldObservation.context_json.ilike(like_pattern) | FieldObservation.context_json.ilike(like_pattern_alt)
        )
        count_q = count_q.where(
            FieldObservation.context_json.ilike(like_pattern) | FieldObservation.context_json.ilike(like_pattern_alt)
        )

    if construction_year_min is not None or construction_year_max is not None:
        # For year range, we do a broader context_json search
        if construction_year_min and construction_year_max:
            # We filter in-memory after fetch for year range (JSON text search is limited)
            pass  # handled post-query
        elif construction_year_min or construction_year_max:
            pass

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    query = query.order_by(FieldObservation.upvotes.desc(), FieldObservation.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    # Post-filter for year range if needed
    if construction_year_min is not None or construction_year_max is not None:
        filtered = []
        for obs in items:
            if obs.context_json:
                try:
                    ctx = json.loads(obs.context_json)
                    yr_min = ctx.get("construction_year_min")
                    yr_max = ctx.get("construction_year_max")
                    if yr_min is None and yr_max is None:
                        continue
                    obs_min = yr_min or 0
                    obs_max = yr_max or 9999
                    req_min = construction_year_min or 0
                    req_max = construction_year_max or 9999
                    # Overlap check
                    if obs_min <= req_max and obs_max >= req_min:
                        filtered.append(obs)
                except (json.JSONDecodeError, TypeError):
                    continue
            # If no context_json, skip when year filter is active
        items = filtered
        total = len(filtered)

    return items, total


# ---------------------------------------------------------------------------
# Pattern insights
# ---------------------------------------------------------------------------


def _parse_context(context_json_str: str | None) -> dict:
    if not context_json_str:
        return {}
    try:
        return json.loads(context_json_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def _parse_tags(tags_str: str | None) -> list[str]:
    if not tags_str:
        return []
    try:
        result = json.loads(tags_str)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _confidence_from_stats(occurrences: int, verified_count: int, avg_upvotes: float) -> str:
    """Derive pattern confidence from occurrence count, verifications, and upvotes."""
    score = occurrences * 2 + verified_count * 5 + avg_upvotes * 1.5
    if score >= 30:
        return "high"
    if score >= 15:
        return "medium"
    return "low"


async def get_pattern_insights(
    db: AsyncSession,
    building_id: UUID | None = None,
) -> list[dict]:
    """
    Analyze observations and surface recurring patterns.

    Groups by: tag combinations, context (canton + year range + pollutant + material).
    Returns patterns with description, occurrence count, confidence, building count, recommendation.
    """
    query = select(FieldObservation).where(FieldObservation.status == "active")
    if building_id:
        # When scoped to a building, also include general observations (building_id IS NULL)
        query = query.where((FieldObservation.building_id == building_id) | (FieldObservation.building_id.is_(None)))

    result = await db.execute(query)
    observations = list(result.scalars().all())

    if not observations:
        return []

    # Group by context signature: (canton, year_bucket, pollutant, material)
    context_groups: dict[tuple, list[FieldObservation]] = defaultdict(list)
    tag_counter: Counter = Counter()

    for obs in observations:
        ctx = _parse_context(obs.context_json)
        tags = _parse_tags(obs.tags)

        # Update tag counter
        for tag in tags:
            tag_counter[tag] += 1

        canton = ctx.get("canton", "any")
        pollutant = ctx.get("pollutant", "any")
        material_val = ctx.get("material", "any")

        # Bucket construction years into decades
        yr_min = ctx.get("construction_year_min")
        yr_max = ctx.get("construction_year_max")
        if (yr_min and yr_max) or yr_min:
            decade = f"{(yr_min // 10) * 10}s"
        else:
            decade = "any"

        key = (canton, decade, pollutant, material_val)
        context_groups[key].append(obs)

    patterns: list[dict] = []

    for (canton, decade, pollutant, material_val), group in context_groups.items():
        if len(group) < 2:
            continue  # Need at least 2 observations to form a pattern

        building_ids = {str(obs.building_id) for obs in group if obs.building_id}
        verified_count = sum(1 for obs in group if obs.is_verified or obs.verified)
        avg_upvotes = sum(obs.upvotes for obs in group) / len(group) if group else 0

        # Build pattern description
        parts = []
        if pollutant != "any":
            parts.append(pollutant.upper())
        if material_val != "any":
            parts.append(f"in {material_val}")
        if decade != "any":
            parts.append(f"of {decade} buildings")
        if canton != "any":
            parts.append(f"in {canton}")

        if not parts:
            continue

        pattern_desc = " ".join(parts)
        confidence = _confidence_from_stats(len(group), verified_count, avg_upvotes)

        # Build recommendation
        if pollutant != "any" and material_val != "any":
            recommendation = f"Always sample {material_val} for {pollutant} in this building type"
        elif pollutant != "any":
            recommendation = f"Check for {pollutant} in buildings matching this profile"
        else:
            recommendation = "Review observations for this building profile"

        # Collect all tags from the group
        all_tags: list[str] = []
        for obs in group:
            all_tags.extend(_parse_tags(obs.tags))
        unique_tags = list(set(all_tags))

        patterns.append(
            {
                "pattern": pattern_desc,
                "occurrences": len(group),
                "confidence": confidence,
                "buildings_count": len(building_ids),
                "recommendation": recommendation,
                "tags": unique_tags[:10],  # Cap at 10 tags
            }
        )

    # Sort by occurrences descending
    patterns.sort(key=lambda p: p["occurrences"], reverse=True)
    return patterns[:20]  # Return top 20 patterns


# ---------------------------------------------------------------------------
# Upvote
# ---------------------------------------------------------------------------


async def upvote_observation(
    db: AsyncSession,
    observation_id: UUID,
    user_id: UUID,
) -> FieldObservation | None:
    """Increment upvote count on an observation."""
    result = await db.execute(select(FieldObservation).where(FieldObservation.id == observation_id))
    obs = result.scalar_one_or_none()
    if obs is None:
        return None

    obs.upvotes = (obs.upvotes or 0) + 1
    await db.commit()
    await db.refresh(obs)
    return obs


# ---------------------------------------------------------------------------
# Admin verify
# ---------------------------------------------------------------------------


async def verify_observation(
    db: AsyncSession,
    observation_id: UUID,
    verified_by_id: UUID,
) -> FieldObservation | None:
    """Mark an observation as admin-verified."""
    result = await db.execute(select(FieldObservation).where(FieldObservation.id == observation_id))
    obs = result.scalar_one_or_none()
    if obs is None:
        return None

    obs.is_verified = True
    obs.verified = True
    obs.verified_by_id = verified_by_id
    obs.verified_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(obs)
    return obs
