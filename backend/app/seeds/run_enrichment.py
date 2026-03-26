"""Standalone enrichment runner — enrich all buildings without lat/lon.

Usage:
    python -m app.seeds.run_enrichment

Loads all buildings and enriches them via the building_enrichment_service.
Respects rate limits (1 req/sec) to external APIs.
"""

from __future__ import annotations

import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run enrichment on all buildings."""
    # Ensure we can import app modules
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.models.building import Building

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://swissbuildingos:swissbuildingos_dev_2024@localhost:5432/swissbuildingos",
    )

    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Load all buildings
        stmt = select(Building)
        rows = await db.execute(stmt)
        buildings = rows.scalars().all()

        logger.info("Found %d buildings to process", len(buildings))

        from app.services.building_enrichment_service import enrich_building

        enriched_count = 0
        error_count = 0

        for i, building in enumerate(buildings, 1):
            logger.info(
                "[%d/%d] Enriching: %s (%s %s)",
                i,
                len(buildings),
                building.address,
                building.postal_code,
                building.city,
            )
            try:
                result = await enrich_building(
                    db,
                    building.id,
                    skip_ai=True,  # Skip AI by default for bulk runs
                )
                if result.fields_updated:
                    enriched_count += 1
                    logger.info("  Updated: %s", ", ".join(result.fields_updated))
                else:
                    logger.info("  No new data found")
                if result.errors:
                    logger.warning("  Errors: %s", result.errors)
            except Exception as exc:
                error_count += 1
                logger.error("  FAILED: %s", exc)

        await db.commit()
        logger.info(
            "Done. %d/%d enriched, %d errors.",
            enriched_count,
            len(buildings),
            error_count,
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
