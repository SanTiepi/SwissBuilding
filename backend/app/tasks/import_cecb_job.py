"""
CECB batch import job — weekly cron task.

Scans buildings missing CECB data and attempts to fetch
energy certificates from geo.admin.ch (or imported CSV).

Usage:
    python -m app.tasks.import_cecb_job [--limit 100] [--csv path/to/file.csv] [--canton VD]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.database import AsyncSessionLocal
from app.services.cecb_import_service import (
    import_cecb_batch,
    import_cecb_for_missing,
    parse_cecb_csv,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def run_cecb_import(
    *,
    limit: int = 100,
    csv_path: str | None = None,
    canton: str = "VD",
) -> dict[str, int]:
    """Run the CECB import job.

    If csv_path is provided, imports from CSV file.
    Otherwise, fetches from geo.admin.ch for buildings missing CECB data.
    """
    async with AsyncSessionLocal() as db:
        if csv_path:
            logger.info("Importing CECB from CSV: %s (canton=%s)", csv_path, canton)
            content = Path(csv_path).read_text(encoding="utf-8")
            records = parse_cecb_csv(content, canton=canton)
            logger.info("Parsed %d CECB records from CSV", len(records))
            stats = await import_cecb_batch(db, records)
        else:
            logger.info("Fetching CECB from geo.admin.ch for up to %d buildings", limit)
            stats = await import_cecb_for_missing(db, limit=limit)

        await db.commit()

    logger.info(
        "CECB import done: updated=%d, skipped=%d, errors=%d",
        stats["updated"],
        stats["skipped"],
        stats["errors"],
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="CECB batch import job")
    parser.add_argument("--limit", type=int, default=100, help="Max buildings to process (default: 100)")
    parser.add_argument("--csv", dest="csv_path", help="Path to CECB CSV file (cantonal export)")
    parser.add_argument("--canton", default="VD", help="Canton code for CSV source (default: VD)")
    args = parser.parse_args()

    stats = asyncio.run(run_cecb_import(limit=args.limit, csv_path=args.csv_path, canton=args.canton))
    if stats.get("errors", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
