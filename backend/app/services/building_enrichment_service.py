"""Backward-compatibility shim -- real implementation in app.services.enrichment package.

All public functions are re-exported from the enrichment package.
This file exists solely so existing ``from app.services.building_enrichment_service import X``
continues to work.  Mock paths like ``app.services.building_enrichment_service.httpx.AsyncClient``
also remain valid because we import httpx at module level.
"""

# ruff: noqa: F401, F403

# httpx must be importable from this module for test mocks that patch
# "app.services.building_enrichment_service.httpx.AsyncClient"
import httpx

from app.services.enrichment import *
