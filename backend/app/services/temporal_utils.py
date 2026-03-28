"""Temporal evaluation utilities for canonical objects with time-window semantics.

Works with any object that has temporal fields (valid_from, valid_until,
stale_after, superseded_at) — typically via TemporalMixin or direct columns.
"""

from datetime import UTC, datetime


def is_valid_as_of(obj: object, as_of: datetime | None = None) -> bool:
    """Check if an object is valid as of a given date.

    Uses valid_from, valid_until, stale_after, superseded_at.
    An object without any temporal fields is considered always valid.
    """
    if as_of is None:
        as_of = datetime.now(UTC)

    if hasattr(obj, "superseded_at") and obj.superseded_at and obj.superseded_at <= as_of:
        return False
    if hasattr(obj, "valid_from") and obj.valid_from and obj.valid_from > as_of:
        return False
    if hasattr(obj, "valid_until") and obj.valid_until and obj.valid_until < as_of:
        return False
    return not (hasattr(obj, "stale_after") and obj.stale_after and obj.stale_after < as_of)


def get_temporal_status(obj: object, as_of: datetime | None = None) -> str:
    """Get temporal status of an object.

    Returns one of: current, future, expired, stale, superseded.
    Checks in priority order (superseded > future > expired > stale > current).
    """
    if as_of is None:
        as_of = datetime.now(UTC)

    if hasattr(obj, "superseded_at") and obj.superseded_at and obj.superseded_at <= as_of:
        return "superseded"
    if hasattr(obj, "valid_from") and obj.valid_from and obj.valid_from > as_of:
        return "future"
    if hasattr(obj, "valid_until") and obj.valid_until and obj.valid_until < as_of:
        return "expired"
    if hasattr(obj, "stale_after") and obj.stale_after and obj.stale_after < as_of:
        return "stale"
    return "current"
