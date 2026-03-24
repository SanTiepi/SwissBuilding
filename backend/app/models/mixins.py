"""BatiConnect - Provenance Mixin for canonical truth entities."""

from sqlalchemy import Column, String


class ProvenanceMixin:
    """Declarative mixin providing provenance tracking fields.

    source_type: import | manual | ai | inferred | official
    confidence: verified | declared | inferred | unknown
    source_ref: optional external reference (import batch ID, API endpoint, document ref)
    """

    source_type = Column(String(30), nullable=True)
    confidence = Column(String(20), nullable=True)
    source_ref = Column(String(255), nullable=True)
