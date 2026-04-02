"""
Documents indexer — batch and single-entity indexing for Meilisearch.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.services.search_service import (
    INDEX_DOCUMENTS,
    _document_to_doc,
    _get_client,
    index_document,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


class DocumentsIndexer:
    """Batch indexer for the documents Meilisearch index."""

    @staticmethod
    def index_one(document: Any) -> None:
        """Index a single document (fire-and-forget)."""
        index_document(document)

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(Document.id)))
        return result.scalar_one()

    @staticmethod
    async def reindex_all(db: AsyncSession) -> int:
        """Batch-reindex all documents. Returns count indexed."""
        client = _get_client()
        if client is None:
            return 0

        result = await db.execute(
            select(Document).options(selectinload(Document.building))
        )
        documents = result.scalars().all()
        docs = [_document_to_doc(d) for d in documents]

        if docs:
            for i in range(0, len(docs), BATCH_SIZE):
                batch = docs[i : i + BATCH_SIZE]
                client.index(INDEX_DOCUMENTS).add_documents(batch)

        logger.info("Indexed %d documents", len(docs))
        return len(docs)
