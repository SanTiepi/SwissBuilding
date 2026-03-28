"""BatiConnect - Mixins for canonical truth entities."""

from sqlalchemy import Column, DateTime, String


class ProvenanceMixin:
    """Declarative mixin providing provenance tracking fields.

    source_type: import | manual | ai | inferred | official
    confidence: verified | declared | inferred | unknown
    source_ref: optional external reference (import batch ID, API endpoint, document ref)
    """

    source_type = Column(String(30), nullable=True)
    confidence = Column(String(20), nullable=True)
    source_ref = Column(String(255), nullable=True)


class TemporalMixin:
    """Temporal validity mixin for canonical objects.

    Adds time-window semantics beyond simple created_at/updated_at.
    Models that already have some of these fields (e.g. observed_at, valid_until)
    should NOT use this mixin — add only the missing fields directly.

    Fields:
        observed_at:  When was this observed/measured
        effective_at: When does this take effect
        valid_from:   Start of validity window
        valid_until:  End of validity window
        stale_after:  When does this become unreliable
    """

    observed_at = Column(DateTime, nullable=True, doc="When was this observed/measured")
    effective_at = Column(DateTime, nullable=True, doc="When does this take effect")
    valid_from = Column(DateTime, nullable=True, doc="Start of validity window")
    valid_until = Column(DateTime, nullable=True, doc="End of validity window")
    stale_after = Column(DateTime, nullable=True, doc="When does this become unreliable")
