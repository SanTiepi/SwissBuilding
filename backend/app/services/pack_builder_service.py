"""Backward-compatibility shim -- real implementation in app.services.pack_builder package.

All public functions are re-exported from the pack_builder package.
This file exists solely so existing ``from app.services.pack_builder_service import X``
continues to work.
"""

# ruff: noqa: F403

from app.services.pack_builder import *
