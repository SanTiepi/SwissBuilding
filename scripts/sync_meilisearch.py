#!/usr/bin/env python3
"""
Meilisearch sync script — initial import / reindex of all entities.

Usage:
    python scripts/sync_meilisearch.py           # full reindex
    python scripts/sync_meilisearch.py --test     # validate indexing (dry-run counts)
    python scripts/sync_meilisearch.py --status   # show index stats
"""

import argparse
import asyncio
import logging
import sys
import time

# Ensure backend is importable when running from repo root
sys.path.insert(0, "backend")

from app.config import settings  # noqa: E402
from app.database import async_session_factory  # noqa: E402
from app.services.search_service import _get_client, init_indexes  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def get_db_counts(db):
    """Return entity counts from DB without indexing."""
    from app.indexing import BuildingsIndexer, DiagnosticsIndexer, DocumentsIndexer

    return {
        "buildings": await BuildingsIndexer.count(db),
        "diagnostics": await DiagnosticsIndexer.count(db),
        "documents": await DocumentsIndexer.count(db),
    }


async def full_reindex(db):
    """Reindex all entities from DB into Meilisearch."""
    from app.indexing import BuildingsIndexer, DiagnosticsIndexer, DocumentsIndexer

    results = {}
    results["buildings"] = await BuildingsIndexer.reindex_all(db)
    results["diagnostics"] = await DiagnosticsIndexer.reindex_all(db)
    results["documents"] = await DocumentsIndexer.reindex_all(db)
    return results


def show_status():
    """Show current Meilisearch index stats."""
    client = _get_client()
    if client is None:
        logger.error("Meilisearch not available (MEILISEARCH_ENABLED=%s)", settings.MEILISEARCH_ENABLED)
        return False

    for index_name in ("buildings", "diagnostics", "documents"):
        try:
            stats = client.index(index_name).get_stats()
            logger.info("  %s: %d documents", index_name, stats.get("numberOfDocuments", 0))
        except Exception:
            logger.warning("  %s: index not found or error", index_name)
    return True


async def run_test():
    """Validate that DB entities are countable and Meilisearch is reachable."""
    client = _get_client()
    if client is None:
        logger.error("Meilisearch not reachable — check MEILISEARCH_ENABLED and connection")
        return False

    async with async_session_factory() as db:
        counts = await get_db_counts(db)

    logger.info("DB counts: %s", counts)
    logger.info("Meilisearch connection: OK")

    # Verify indexes exist
    for index_name in ("buildings", "diagnostics", "documents"):
        try:
            client.index(index_name).get_stats()
            logger.info("  Index '%s': OK", index_name)
        except Exception:
            logger.warning("  Index '%s': not found (run full sync first)", index_name)

    return True


async def main():
    parser = argparse.ArgumentParser(description="Sync entities to Meilisearch")
    parser.add_argument("--test", action="store_true", help="Validate connectivity and counts")
    parser.add_argument("--status", action="store_true", help="Show index stats")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.test:
        ok = await run_test()
        sys.exit(0 if ok else 1)

    # Full reindex
    logger.info("Initializing Meilisearch indexes...")
    init_indexes()

    logger.info("Starting full reindex...")
    start = time.time()

    async with async_session_factory() as db:
        results = await full_reindex(db)

    elapsed = time.time() - start
    total = sum(results.values())
    logger.info("Reindex complete: %d total entities in %.1fs", total, elapsed)
    for entity, count in results.items():
        logger.info("  %s: %d", entity, count)


if __name__ == "__main__":
    asyncio.run(main())
