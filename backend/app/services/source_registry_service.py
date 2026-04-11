"""Source registry service — manages source catalogue and health events."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source_registry import SourceHealthEvent, SourceRegistryEntry

logger = logging.getLogger(__name__)


class SourceRegistryService:
    """Service for source registry CRUD and health monitoring."""

    @staticmethod
    async def get_all_sources(
        db: AsyncSession,
        *,
        family: str | None = None,
        circle: int | None = None,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[SourceRegistryEntry]:
        """List sources with optional filters."""
        stmt = select(SourceRegistryEntry).where(SourceRegistryEntry.active.is_(True))
        if family:
            stmt = stmt.where(SourceRegistryEntry.family == family)
        if circle is not None:
            stmt = stmt.where(SourceRegistryEntry.circle == circle)
        if status:
            stmt = stmt.where(SourceRegistryEntry.status == status)
        if priority:
            stmt = stmt.where(SourceRegistryEntry.priority == priority)
        stmt = stmt.order_by(SourceRegistryEntry.circle, SourceRegistryEntry.family, SourceRegistryEntry.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_source(db: AsyncSession, source_name: str) -> SourceRegistryEntry | None:
        """Get a specific source by name."""
        stmt = select(SourceRegistryEntry).where(SourceRegistryEntry.name == source_name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def record_health_event(
        db: AsyncSession,
        source_name: str,
        event_type: str,
        *,
        description: str | None = None,
        error: str | None = None,
        affected_buildings_count: int | None = None,
        fallback_used: bool = False,
        fallback_source_name: str | None = None,
    ) -> SourceHealthEvent | None:
        """Record a health event for a source. Returns the event or None if source not found."""
        source = await SourceRegistryService.get_source(db, source_name)
        if source is None:
            logger.warning("Cannot record health event: source '%s' not found in registry", source_name)
            return None

        event = SourceHealthEvent(
            source_id=source.id,
            event_type=event_type,
            description=description,
            error_detail=error,
            affected_buildings_count=affected_buildings_count,
            fallback_used=fallback_used,
            fallback_source_name=fallback_source_name,
        )
        db.add(event)

        # Update source status based on event type
        status_map = {
            "healthy": "active",
            "recovered": "active",
            "degraded": "degraded",
            "unavailable": "unavailable",
            "error": "degraded",
            "timeout": "degraded",
            "schema_drift": "degraded",
        }
        new_status = status_map.get(event_type)
        if new_status and source.status != new_status:
            source.status = new_status

        await db.flush()
        return event

    @staticmethod
    async def get_source_health(
        db: AsyncSession,
        source_name: str,
        *,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get current health status and recent events for a source."""
        source = await SourceRegistryService.get_source(db, source_name)
        if source is None:
            return {"error": "source_not_found"}

        stmt = (
            select(SourceHealthEvent)
            .where(SourceHealthEvent.source_id == source.id)
            .order_by(desc(SourceHealthEvent.detected_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())

        # Count events in last 24h
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        events_24h = [e for e in events if e.detected_at and e.detected_at.replace(tzinfo=UTC) > cutoff]
        errors_24h = [e for e in events_24h if e.event_type in ("error", "timeout", "unavailable")]

        return {
            "source_name": source.name,
            "display_name": source.display_name,
            "status": source.status,
            "last_event_type": events[0].event_type if events else None,
            "last_event_at": events[0].detected_at.isoformat() if events and events[0].detected_at else None,
            "events_24h": len(events_24h),
            "errors_24h": len(errors_24h),
            "recent_events": events,
        }

    @staticmethod
    async def get_health_dashboard(db: AsyncSession) -> dict[str, Any]:
        """Get health overview across all active sources."""
        sources = await SourceRegistryService.get_all_sources(db)

        total = len(sources)
        active_count = sum(1 for s in sources if s.status == "active")
        degraded_count = sum(1 for s in sources if s.status == "degraded")
        unavailable_count = sum(1 for s in sources if s.status == "unavailable")

        # Get last event for each source
        source_summaries = []
        cutoff = datetime.now(UTC) - timedelta(hours=24)

        for source in sources:
            stmt = (
                select(SourceHealthEvent)
                .where(SourceHealthEvent.source_id == source.id)
                .order_by(desc(SourceHealthEvent.detected_at))
                .limit(1)
            )
            result = await db.execute(stmt)
            last_event = result.scalar_one_or_none()

            # Count 24h events
            stmt_24h = (
                select(func.count())
                .select_from(SourceHealthEvent)
                .where(
                    SourceHealthEvent.source_id == source.id,
                    SourceHealthEvent.detected_at >= cutoff,
                )
            )
            result_24h = await db.execute(stmt_24h)
            events_24h = result_24h.scalar() or 0

            stmt_errors = (
                select(func.count())
                .select_from(SourceHealthEvent)
                .where(
                    SourceHealthEvent.source_id == source.id,
                    SourceHealthEvent.detected_at >= cutoff,
                    SourceHealthEvent.event_type.in_(["error", "timeout", "unavailable"]),
                )
            )
            result_errors = await db.execute(stmt_errors)
            errors_24h = result_errors.scalar() or 0

            source_summaries.append(
                {
                    "source_name": source.name,
                    "display_name": source.display_name,
                    "status": source.status,
                    "last_event_type": last_event.event_type if last_event else None,
                    "last_event_at": (
                        last_event.detected_at.isoformat() if last_event and last_event.detected_at else None
                    ),
                    "events_24h": events_24h,
                    "errors_24h": errors_24h,
                }
            )

        return {
            "total_sources": total,
            "active": active_count,
            "degraded": degraded_count,
            "unavailable": unavailable_count,
            "sources": source_summaries,
        }

    @staticmethod
    async def check_source_freshness(
        db: AsyncSession,
        source_name: str,
        building_id: UUID,
    ) -> dict[str, Any]:
        """Check if cached data from this source is still fresh for a building."""
        source = await SourceRegistryService.get_source(db, source_name)
        if source is None:
            return {"source_name": source_name, "is_fresh": False, "error": "source_not_found"}

        ttl = source.cache_ttl_hours
        if ttl is None:
            # No TTL configured — always considered fresh (on-demand)
            return {
                "source_name": source_name,
                "is_fresh": True,
                "cache_ttl_hours": None,
                "last_fetched_at": None,
                "age_hours": None,
            }

        # Check source-specific cache tables
        # For geo context, check BuildingGeoContext.fetched_at
        # For identity chain, check BuildingIdentityChain timestamps
        # Generic approach: check latest healthy event referencing this source
        from app.models.building_geo_context import BuildingGeoContext
        from app.models.building_identity import BuildingIdentityChain

        last_fetched: datetime | None = None

        if source_name.startswith("geo_admin_"):
            stmt = select(BuildingGeoContext.fetched_at).where(BuildingGeoContext.building_id == building_id)
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                last_fetched = row

        elif source_name in ("madd", "geo_admin_madd"):
            stmt = select(BuildingIdentityChain.egid_resolved_at).where(
                BuildingIdentityChain.building_id == building_id
            )
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                last_fetched = row

        if last_fetched is None:
            return {
                "source_name": source_name,
                "is_fresh": False,
                "cache_ttl_hours": ttl,
                "last_fetched_at": None,
                "age_hours": None,
            }

        now = datetime.now(UTC)
        age = now - last_fetched.replace(tzinfo=UTC)
        age_hours = age.total_seconds() / 3600

        return {
            "source_name": source_name,
            "is_fresh": age_hours < ttl,
            "cache_ttl_hours": ttl,
            "last_fetched_at": last_fetched.isoformat(),
            "age_hours": round(age_hours, 1),
        }
