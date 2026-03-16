"""
SwissBuildingOS - Meilisearch Full-Text Search Service

Manages indexing and searching across buildings, diagnostics, and documents.
All operations are guarded by MEILISEARCH_ENABLED and gracefully degrade
when Meilisearch is unavailable.
"""

import logging
from typing import Any

import meilisearch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings

logger = logging.getLogger(__name__)

# Index names
INDEX_BUILDINGS = "buildings"
INDEX_DIAGNOSTICS = "diagnostics"
INDEX_DOCUMENTS = "documents"

# Index configurations: searchable and filterable attributes
INDEX_CONFIG: dict[str, dict[str, list[str]]] = {
    INDEX_BUILDINGS: {
        "searchableAttributes": [
            "address",
            "city",
            "postal_code",
            "egid",
            "building_type",
            "organization_name",
            "status",
        ],
        "filterableAttributes": [
            "city",
            "postal_code",
            "building_type",
            "status",
            "risk_level",
            "construction_year",
        ],
    },
    INDEX_DIAGNOSTICS: {
        "searchableAttributes": [
            "building_address",
            "diagnostic_type",
            "diagnostician_name",
            "pollutants_found",
            "status",
        ],
        "filterableAttributes": [
            "building_id",
            "diagnostic_type",
            "status",
            "date_diagnostic",
        ],
    },
    INDEX_DOCUMENTS: {
        "searchableAttributes": [
            "building_address",
            "title",
            "document_type",
            "file_name",
            "uploaded_by_name",
        ],
        "filterableAttributes": [
            "building_id",
            "document_type",
        ],
    },
}


def _get_client() -> meilisearch.Client | None:
    """Return a Meilisearch client if enabled, else None."""
    if not settings.MEILISEARCH_ENABLED:
        return None
    try:
        url = f"http://{settings.MEILISEARCH_HOST}:{settings.MEILISEARCH_PORT}"
        return meilisearch.Client(url, settings.MEILISEARCH_MASTER_KEY)
    except Exception:
        logger.warning("Failed to create Meilisearch client", exc_info=True)
        return None


def init_indexes() -> None:
    """Create indexes and configure searchable/filterable attributes."""
    client = _get_client()
    if client is None:
        return
    try:
        for index_name, config in INDEX_CONFIG.items():
            client.create_index(index_name, {"primaryKey": "id"})
            index = client.index(index_name)
            index.update_searchable_attributes(config["searchableAttributes"])
            index.update_filterable_attributes(config["filterableAttributes"])
        logger.info("Meilisearch indexes initialized")
    except Exception:
        logger.warning("Failed to initialize Meilisearch indexes", exc_info=True)


def _building_to_doc(building: Any) -> dict[str, Any]:
    """Convert a Building ORM object to a Meilisearch document."""
    return {
        "id": str(building.id),
        "address": building.address,
        "city": building.city,
        "postal_code": building.postal_code,
        "egid": str(building.egid) if building.egid else None,
        "building_type": building.building_type,
        "construction_year": building.construction_year,
        "status": building.status,
        "risk_level": getattr(getattr(building, "risk_scores", None), "risk_level", None),
        "organization_name": None,
    }


def _diagnostic_to_doc(diagnostic: Any) -> dict[str, Any]:
    """Convert a Diagnostic ORM object to a Meilisearch document."""
    building_address = getattr(getattr(diagnostic, "building", None), "address", None)
    diagnostician = getattr(diagnostic, "diagnostician", None)
    diagnostician_name = f"{diagnostician.first_name} {diagnostician.last_name}" if diagnostician else None
    # Collect pollutant types from samples
    samples = getattr(diagnostic, "samples", None) or []
    pollutants = list({s.pollutant_type for s in samples if getattr(s, "pollutant_type", None)})
    return {
        "id": str(diagnostic.id),
        "building_id": str(diagnostic.building_id),
        "building_address": building_address,
        "diagnostic_type": diagnostic.diagnostic_type,
        "status": diagnostic.status,
        "diagnostician_name": diagnostician_name,
        "pollutants_found": ", ".join(pollutants) if pollutants else None,
        "date_diagnostic": str(diagnostic.date_inspection) if diagnostic.date_inspection else None,
    }


def _document_to_doc(document: Any) -> dict[str, Any]:
    """Convert a Document ORM object to a Meilisearch document."""
    building_address = getattr(getattr(document, "building", None), "address", None)
    return {
        "id": str(document.id),
        "building_id": str(document.building_id),
        "building_address": building_address,
        "title": document.description or document.file_name,
        "document_type": document.document_type,
        "file_name": document.file_name,
        "uploaded_by_name": None,
    }


def index_building(building: Any) -> None:
    """Index a single building. Fire-and-forget."""
    client = _get_client()
    if client is None:
        return
    try:
        doc = _building_to_doc(building)
        client.index(INDEX_BUILDINGS).add_documents([doc])
    except Exception:
        logger.warning("Failed to index building %s", building.id, exc_info=True)


def index_diagnostic(diagnostic: Any) -> None:
    """Index a single diagnostic. Fire-and-forget."""
    client = _get_client()
    if client is None:
        return
    try:
        doc = _diagnostic_to_doc(diagnostic)
        client.index(INDEX_DIAGNOSTICS).add_documents([doc])
    except Exception:
        logger.warning("Failed to index diagnostic %s", diagnostic.id, exc_info=True)


def index_document(document: Any) -> None:
    """Index a single document. Fire-and-forget."""
    client = _get_client()
    if client is None:
        return
    try:
        doc = _document_to_doc(document)
        client.index(INDEX_DOCUMENTS).add_documents([doc])
    except Exception:
        logger.warning("Failed to index document %s", document.id, exc_info=True)


def delete_building(building_id: str) -> None:
    """Remove a building from the search index."""
    client = _get_client()
    if client is None:
        return
    try:
        client.index(INDEX_BUILDINGS).delete_document(building_id)
    except Exception:
        logger.warning("Failed to delete building %s from index", building_id, exc_info=True)


def delete_diagnostic(diagnostic_id: str) -> None:
    """Remove a diagnostic from the search index."""
    client = _get_client()
    if client is None:
        return
    try:
        client.index(INDEX_DIAGNOSTICS).delete_document(diagnostic_id)
    except Exception:
        logger.warning("Failed to delete diagnostic %s from index", diagnostic_id, exc_info=True)


def delete_document(document_id: str) -> None:
    """Remove a document from the search index."""
    client = _get_client()
    if client is None:
        return
    try:
        client.index(INDEX_DOCUMENTS).delete_document(document_id)
    except Exception:
        logger.warning("Failed to delete document %s from index", document_id, exc_info=True)


def search_all(
    query: str,
    index_filter: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Search across one or all indexes.

    Returns:
        {
            "query": str,
            "results": [{"index": str, "id": str, "title": str, "subtitle": str, "url": str, "score": float}],
            "total": int,
        }
    """
    client = _get_client()
    if client is None:
        return {"query": query, "results": [], "total": 0}

    indexes_to_search = [index_filter] if index_filter and index_filter in INDEX_CONFIG else list(INDEX_CONFIG.keys())

    results: list[dict[str, Any]] = []
    per_index_limit = limit if index_filter else max(limit // len(indexes_to_search), 5)

    try:
        for idx_name in indexes_to_search:
            try:
                search_result = client.index(idx_name).search(query, {"limit": per_index_limit})
                for hit in search_result.get("hits", []):
                    result_item = _hit_to_result(idx_name, hit)
                    results.append(result_item)
            except Exception:
                logger.warning("Search failed on index %s", idx_name, exc_info=True)
    except Exception:
        logger.warning("Multi-index search failed", exc_info=True)

    # Sort by score descending, limit
    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    results = results[:limit]

    return {"query": query, "results": results, "total": len(results)}


def _hit_to_result(index_name: str, hit: dict[str, Any]) -> dict[str, Any]:
    """Convert a Meilisearch hit to a unified result item."""
    ranking = hit.get("_rankingScore", 0.0)

    if index_name == INDEX_BUILDINGS:
        title = hit.get("address", "")
        subtitle = f"{hit.get('postal_code', '')} {hit.get('city', '')}".strip()
        url = f"/buildings/{hit['id']}"
    elif index_name == INDEX_DIAGNOSTICS:
        title = f"{hit.get('diagnostic_type', 'Diagnostic')} — {hit.get('building_address', '')}"
        subtitle = hit.get("diagnostician_name") or hit.get("status", "")
        url = f"/diagnostics/{hit['id']}"
    else:  # documents
        title = hit.get("title") or hit.get("file_name", "")
        subtitle = hit.get("building_address") or hit.get("document_type", "")
        url = f"/documents/{hit['id']}/download"

    return {
        "index": index_name,
        "id": hit["id"],
        "title": title,
        "subtitle": subtitle,
        "url": url,
        "score": ranking,
    }


async def reindex_all(db: AsyncSession) -> dict[str, int]:
    """
    Reindex all buildings, diagnostics, and documents from the database.

    Returns a dict with counts per index.
    """
    client = _get_client()
    if client is None:
        return {"buildings": 0, "diagnostics": 0, "documents": 0}

    from app.models.building import Building
    from app.models.diagnostic import Diagnostic
    from app.models.document import Document

    counts: dict[str, int] = {}

    # Buildings
    try:
        result = await db.execute(select(Building).where(Building.status != "deleted"))
        buildings = result.scalars().all()
        docs = [_building_to_doc(b) for b in buildings]
        if docs:
            client.index(INDEX_BUILDINGS).add_documents(docs)
        counts["buildings"] = len(docs)
    except Exception:
        logger.warning("Failed to reindex buildings", exc_info=True)
        counts["buildings"] = 0

    # Diagnostics
    try:
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
            client.index(INDEX_DIAGNOSTICS).add_documents(docs)
        counts["diagnostics"] = len(docs)
    except Exception:
        logger.warning("Failed to reindex diagnostics", exc_info=True)
        counts["diagnostics"] = 0

    # Documents
    try:
        result = await db.execute(select(Document).options(selectinload(Document.building)))
        documents = result.scalars().all()
        docs = [_document_to_doc(d) for d in documents]
        if docs:
            client.index(INDEX_DOCUMENTS).add_documents(docs)
        counts["documents"] = len(docs)
    except Exception:
        logger.warning("Failed to reindex documents", exc_info=True)
        counts["documents"] = 0

    logger.info("Reindex complete: %s", counts)
    return counts
