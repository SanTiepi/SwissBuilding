"""
Buildings indexer — batch and single-entity indexing for Meilisearch.

Delegates to search_service for document conversion and client management.
Adds batch-oriented helpers used by the sync script.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.services.search_service import (
    INDEX_BUILDINGS,
    _building_to_doc,
    _get_client,
    index_building,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


class BuildingsIndexer:
    """Batch indexer for the buildings Meilisearch index."""

    @staticmethod
    def index_one(building: Any) -> None:
        """Index a single building (fire-and-forget)."""
        index_building(building)

    @staticmethod
    async def count(db: AsyncSession) -> int:
        """Return total indexable buildings count."""
        result = await db.execute(
            select(func.count(Building.id)).where(Building.status != "deleted")
        )
        return result.scalar_one()

    @staticmethod
    async def reindex_all(db: AsyncSession) -> int:
        """Batch-reindex all buildings. Returns count indexed."""
        client = _get_client()
        if client is None:
            return 0

        result = await db.execute(
            select(Building).where(Building.status != "deleted")
        )
        buildings = result.scalars().all()
        docs = [_building_to_doc(b) for b in buildings]

        if docs:
            # Send in batches to avoid oversized payloads
            for i in range(0, len(docs), BATCH_SIZE):
                batch = docs[i : i + BATCH_SIZE]
                client.index(INDEX_BUILDINGS).add_documents(batch)

        logger.info("Indexed %d buildings", len(docs))
        return len(docs)
