"""
Diagnostics indexer — batch and single-entity indexing for Meilisearch.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.diagnostic import Diagnostic
from app.services.search_service import (
    INDEX_DIAGNOSTICS,
    _diagnostic_to_doc,
    _get_client,
    index_diagnostic,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


class DiagnosticsIndexer:
    """Batch indexer for the diagnostics Meilisearch index."""

    @staticmethod
    def index_one(diagnostic: Any) -> None:
        """Index a single diagnostic (fire-and-forget)."""
        index_diagnostic(diagnostic)

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(Diagnostic.id)))
        return result.scalar_one()

    @staticmethod
    async def reindex_all(db: AsyncSession) -> int:
        """Batch-reindex all diagnostics. Returns count indexed."""
        client = _get_client()
        if client is None:
            return 0

        result = await db.execute(
            select(Diagnostic).options(
                selectinload(Diagnostic.building),
                selectinload(Diagnostic.diagnostician),
                selectinload(Diagnostic.samples),
            )
        )
        diagnostics = result.scalars().all()
        docs = [_diagnostic_to_doc(d) for d in diagnostics]

        if docs:
            for i in range(0, len(docs), BATCH_SIZE):
                batch = docs[i : i + BATCH_SIZE]
                client.index(INDEX_DIAGNOSTICS).add_documents(batch)

        logger.info("Indexed %d diagnostics", len(docs))
        return len(docs)
