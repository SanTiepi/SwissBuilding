"""Financial field redaction helpers for pack sections."""

from app.schemas.pack_builder import PackSection

_REDACTED_PLACEHOLDER = "[confidentiel]"
_REDACTED_COST_MESSAGE = "[Montants masques a la demande du proprietaire]"

# Field names that carry financial amounts
_FINANCIAL_FIELD_NAMES = frozenset(
    {
        "total_amount_chf",
        "cost",
        "amount",
        "price",
        "amount_chf",
        "total_expenses_chf",
        "total_income_chf",
        "expense_by_category",
        "claimed_amount_chf",
        "approved_amount_chf",
        "paid_amount_chf",
        "insured_value_chf",
        "premium_annual_chf",
    }
)

# Sections that are entirely financial -- replace items with redaction notice
_FINANCIAL_SECTION_TYPES = frozenset({"cost_summary"})


def _redact_item(item: dict) -> dict:
    """Return a copy of *item* with financial fields replaced by placeholders."""
    redacted = {}
    for key, value in item.items():
        if key in _FINANCIAL_FIELD_NAMES:
            redacted[key] = _REDACTED_PLACEHOLDER
        else:
            redacted[key] = value
    return redacted


def _redact_section(section: PackSection) -> PackSection:
    """Return a redacted copy of a section, masking financial data."""
    if section.section_type in _FINANCIAL_SECTION_TYPES:
        return PackSection(
            section_name=section.section_name,
            section_type=section.section_type,
            items=[{"notice": _REDACTED_COST_MESSAGE}],
            completeness=section.completeness,
            notes=_REDACTED_COST_MESSAGE,
        )

    # For other sections, redact individual financial fields
    redacted_items = [_redact_item(item) for item in section.items]
    return PackSection(
        section_name=section.section_name,
        section_type=section.section_type,
        items=redacted_items,
        completeness=section.completeness,
        notes=section.notes,
    )
