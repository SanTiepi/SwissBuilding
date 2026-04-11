"""API endpoints for data imports (GWR, CECB, etc.)."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin
from app.ingestion.gwr_importer import import_gwr_bulk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import", tags=["imports"])


@router.post("/gwr/bulk", dependencies=[Depends(require_admin)])
async def import_gwr_bulk_endpoint(
    cantons: list[str] = Query(None, description="Canton codes (e.g., VD, GE)"),
    limit: int = Query(None, description="Maximum buildings to import (for testing)"),
    dry_run: bool = Query(False, description="If true, don't commit changes"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Bulk import buildings from GWR (Registre fédéral des bâtiments).

    Requires admin role.

    **Query Parameters:**
    - `cantons`: Optional list of canton codes (e.g., VD, GE)
    - `limit`: Optional limit for testing (max buildings to import)
    - `dry_run`: If true, rollback changes (preview mode)

    **Returns:**
    ```json
    {
        "imported": 1000,
        "updated": 500,
        "skipped": 100,
        "errors": 5,
        "status": "success"
    }
    ```

    **Example:**
    ```
    POST /api/v1/import/gwr/bulk?cantons=VD&cantons=GE&limit=10000
    ```
    """
    try:
        logger.info(f"Starting GWR bulk import: cantons={cantons}, limit={limit}, dry_run={dry_run}")

        result = await import_gwr_bulk(cantons=cantons, limit=limit, dry_run=dry_run)

        return {
            **result,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"GWR import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
