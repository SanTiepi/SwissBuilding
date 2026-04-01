"""Service for generating standardized passport exchange documents.

Includes:
- Standardized JSON export of passport data
- Envelope diffing (compare two envelope versions)
- Machine-readable export with full provenance
- Transfer manifest generation
- Reimport validation
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.passport_envelope import BuildingPassportEnvelope
from app.schemas.passport_exchange import (
    PassportExchangeDocument,
    PassportExchangeMetadata,
)
from app.services.passport_service import get_passport_summary

logger = logging.getLogger(__name__)

EXCHANGE_SCHEMA_VERSION = "1.0.0"

# Sections that map to passport_data top-level keys (mirror from envelope service)
_ENVELOPE_SECTIONS = [
    "knowledge_state",
    "completeness",
    "readiness",
    "blind_spots",
    "contradictions",
    "evidence_coverage",
    "diagnostic_publications",
    "pollutant_coverage",
    "passport_grade",
]

# Required top-level keys for reimport validation
_REQUIRED_REIMPORT_KEYS = {"passport_data", "content_hash"}
_VALID_STATUSES = {"draft", "frozen", "published", "transferred", "acknowledged", "superseded", "archived"}
_VALID_REDACTION_PROFILES = {"none", "financial", "personal", "detailed"}


async def export_passport(
    db: AsyncSession,
    building_id: UUID,
    include_transfer: bool = False,
) -> PassportExchangeDocument | None:
    """Export a building's passport as a standardized exchange document.

    Returns None if the building does not exist.

    When *include_transfer* is True, diagnostics/interventions/actions summaries
    from the transfer package service are included in the document.
    """
    # Fetch building for identity fields
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # Get passport summary
    passport = await get_passport_summary(db, building_id)

    metadata = PassportExchangeMetadata(
        schema_version=EXCHANGE_SCHEMA_VERSION,
        exported_at=datetime.now(UTC),
    )

    # Extract passport sections (passport is guaranteed non-None here since building exists)
    knowledge_state = passport["knowledge_state"] if passport else None
    readiness = passport["readiness"] if passport else None
    completeness = passport["completeness"] if passport else None
    blind_spots = passport["blind_spots"] if passport else None
    contradictions = passport["contradictions"] if passport else None
    evidence_coverage = passport["evidence_coverage"] if passport else None
    passport_grade = passport["passport_grade"] if passport else None

    # Optional transfer package sections
    diagnostics_summary: dict | None = None
    interventions_summary: dict | None = None
    actions_summary: dict | None = None

    if include_transfer:
        from app.services.transfer_package_service import generate_transfer_package

        package = await generate_transfer_package(
            db,
            building_id,
            include_sections=["diagnostics", "interventions", "actions"],
        )
        if package is not None:
            diagnostics_summary = package.diagnostics_summary
            interventions_summary = package.interventions_summary
            actions_summary = package.actions_summary

    return PassportExchangeDocument(
        metadata=metadata,
        building_id=building.id,
        address=building.address,
        city=building.city,
        canton=building.canton,
        construction_year=building.construction_year,
        passport_grade=passport_grade,
        knowledge_state=knowledge_state,
        readiness=readiness,
        completeness=completeness,
        blind_spots=blind_spots,
        contradictions=contradictions,
        evidence_coverage=evidence_coverage,
        diagnostics_summary=diagnostics_summary,
        interventions_summary=interventions_summary,
        actions_summary=actions_summary,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_envelope_or_raise(db: AsyncSession, envelope_id: UUID) -> BuildingPassportEnvelope:
    """Fetch an envelope by ID or raise ValueError."""
    result = await db.execute(select(BuildingPassportEnvelope).where(BuildingPassportEnvelope.id == envelope_id))
    envelope = result.scalar_one_or_none()
    if envelope is None:
        raise ValueError(f"Passport envelope not found: {envelope_id}")
    return envelope


def _flatten_dict(data: dict, prefix: str = "") -> dict[str, object]:
    """Flatten nested dict into dot-separated keys for comparison."""
    flat: dict[str, object] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten_dict(value, full_key))
        else:
            flat[full_key] = value
    return flat


def _diff_passport_data(data_a: dict, data_b: dict) -> list[dict]:
    """Compare two passport_data dicts and return field-level changes."""
    changes: list[dict] = []
    sections_a = set(data_a.keys())
    sections_b = set(data_b.keys())

    # Sections only in A (removed)
    for section in sorted(sections_a - sections_b):
        changes.append(
            {
                "section": section,
                "field": section,
                "old_value": str(data_a[section])[:200] if data_a[section] is not None else None,
                "new_value": None,
                "change_type": "removed",
            }
        )

    # Sections only in B (added)
    for section in sorted(sections_b - sections_a):
        changes.append(
            {
                "section": section,
                "field": section,
                "old_value": None,
                "new_value": str(data_b[section])[:200] if data_b[section] is not None else None,
                "change_type": "added",
            }
        )

    # Sections in both — compare field-by-field
    for section in sorted(sections_a & sections_b):
        val_a = data_a[section]
        val_b = data_b[section]

        if val_a == val_b:
            continue

        # If both are dicts, do field-level diff
        if isinstance(val_a, dict) and isinstance(val_b, dict):
            flat_a = _flatten_dict(val_a)
            flat_b = _flatten_dict(val_b)
            all_keys = sorted(set(flat_a.keys()) | set(flat_b.keys()))

            for field_key in all_keys:
                old_val = flat_a.get(field_key)
                new_val = flat_b.get(field_key)
                if old_val != new_val:
                    change_type = "added" if old_val is None else ("removed" if new_val is None else "modified")
                    changes.append(
                        {
                            "section": section,
                            "field": field_key,
                            "old_value": str(old_val)[:200] if old_val is not None else None,
                            "new_value": str(new_val)[:200] if new_val is not None else None,
                            "change_type": change_type,
                        }
                    )
        else:
            # Non-dict values — treat as whole-section change
            changes.append(
                {
                    "section": section,
                    "field": section,
                    "old_value": str(val_a)[:200] if val_a is not None else None,
                    "new_value": str(val_b)[:200] if val_b is not None else None,
                    "change_type": "modified",
                }
            )

    return changes


def _safe_subtract(a: object, b: object) -> float | None:
    """Safely compute a - b, returning None if either is non-numeric."""
    try:
        return float(a) - float(b)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# diff_envelopes
# ---------------------------------------------------------------------------


async def diff_envelopes(db: AsyncSession, envelope_id_a: UUID, envelope_id_b: UUID) -> dict:
    """Compare two passport envelope versions.

    Returns a structured diff with summary counts, field-level changes,
    and deltas for trust, completeness, and readiness.
    """
    env_a = await _get_envelope_or_raise(db, envelope_id_a)
    env_b = await _get_envelope_or_raise(db, envelope_id_b)

    data_a: dict = env_a.passport_data or {}
    data_b: dict = env_b.passport_data or {}

    changes = _diff_passport_data(data_a, data_b)

    sections_a = set(data_a.keys())
    sections_b = set(data_b.keys())
    sections_added = sorted(sections_b - sections_a)
    sections_removed = sorted(sections_a - sections_b)
    sections_changed = sorted({c["section"] for c in changes if c["change_type"] == "modified"})
    unchanged = sorted((sections_a & sections_b) - {c["section"] for c in changes})

    # Trust delta
    ks_a = data_a.get("knowledge_state", {}) if isinstance(data_a.get("knowledge_state"), dict) else {}
    ks_b = data_b.get("knowledge_state", {}) if isinstance(data_b.get("knowledge_state"), dict) else {}
    trust_delta = {
        "old_trust": ks_a.get("overall_trust"),
        "new_trust": ks_b.get("overall_trust"),
        "trust_change": _safe_subtract(ks_b.get("overall_trust"), ks_a.get("overall_trust")),
    }

    # Completeness delta
    comp_a = data_a.get("completeness", {}) if isinstance(data_a.get("completeness"), dict) else {}
    comp_b = data_b.get("completeness", {}) if isinstance(data_b.get("completeness"), dict) else {}
    completeness_delta = {
        "old_pct": comp_a.get("overall_score"),
        "new_pct": comp_b.get("overall_score"),
    }

    # Readiness delta
    rd_a = data_a.get("readiness", {}) if isinstance(data_a.get("readiness"), dict) else {}
    rd_b = data_b.get("readiness", {}) if isinstance(data_b.get("readiness"), dict) else {}
    readiness_delta = {
        "old_verdicts": {k: v.get("status") if isinstance(v, dict) else v for k, v in rd_a.items()},
        "new_verdicts": {k: v.get("status") if isinstance(v, dict) else v for k, v in rd_b.items()},
    }

    # Grade delta
    grade_a = data_a.get("passport_grade")
    grade_b = data_b.get("passport_grade")

    return {
        "envelope_a_id": str(env_a.id),
        "envelope_b_id": str(env_b.id),
        "envelope_a_version": env_a.version,
        "envelope_b_version": env_b.version,
        "summary": {
            "sections_added": sections_added,
            "sections_removed": sections_removed,
            "sections_changed": sections_changed,
            "unchanged": unchanged,
            "total_changes": len(changes),
        },
        "changes": changes,
        "trust_delta": trust_delta,
        "completeness_delta": completeness_delta,
        "readiness_delta": readiness_delta,
        "grade_delta": {"old_grade": grade_a, "new_grade": grade_b},
    }


# ---------------------------------------------------------------------------
# export_machine_readable
# ---------------------------------------------------------------------------


async def export_machine_readable(
    db: AsyncSession,
    envelope_id: UUID,
    format: str = "json",
) -> dict | str:
    """Export envelope in machine-readable format.

    Supported formats:
    - ``json`` (default): full JSON with metadata, provenance, sections, redaction info
    - ``csv-summary``: CSV string with one row per section summarizing key metrics

    Returns a dict for JSON format, a string for CSV format.
    """
    envelope = await _get_envelope_or_raise(db, envelope_id)

    now = datetime.now(UTC)

    if format == "csv-summary":
        return _export_csv_summary(envelope, now)

    # Default: JSON
    return _export_json(envelope, now)


def _export_json(envelope: BuildingPassportEnvelope, exported_at: datetime) -> dict:
    """Build JSON export payload."""
    data: dict = envelope.passport_data or {}

    return {
        "schema_version": EXCHANGE_SCHEMA_VERSION,
        "format": "json",
        "exported_at": exported_at.isoformat(),
        "source_system": "BatiConnect",
        "envelope": {
            "id": str(envelope.id),
            "building_id": str(envelope.building_id),
            "organization_id": str(envelope.organization_id),
            "version": envelope.version,
            "version_label": envelope.version_label,
            "status": envelope.status,
            "content_hash": envelope.content_hash,
            "is_sovereign": envelope.is_sovereign,
            "created_at": envelope.created_at.isoformat() if envelope.created_at else None,
        },
        "provenance": {
            "created_by_id": str(envelope.created_by_id),
            "frozen_at": envelope.frozen_at.isoformat() if envelope.frozen_at else None,
            "frozen_by_id": str(envelope.frozen_by_id) if envelope.frozen_by_id else None,
            "published_at": envelope.published_at.isoformat() if envelope.published_at else None,
            "published_by_id": str(envelope.published_by_id) if envelope.published_by_id else None,
            "transferred_at": envelope.transferred_at.isoformat() if envelope.transferred_at else None,
            "acknowledged_at": envelope.acknowledged_at.isoformat() if envelope.acknowledged_at else None,
            "receipt_hash": envelope.receipt_hash,
        },
        "redaction": {
            "profile": envelope.redaction_profile,
            "financials_redacted": envelope.financials_redacted,
            "personal_data_redacted": envelope.personal_data_redacted,
        },
        "sections_included": envelope.sections_included or [],
        "passport_data": data,
        "reimport": {
            "reimportable": envelope.reimportable,
            "reimport_format": envelope.reimport_format,
        },
    }


def _export_csv_summary(envelope: BuildingPassportEnvelope, exported_at: datetime) -> str:
    """Build CSV summary with one row per section."""
    data: dict = envelope.passport_data or {}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "key", "value"])

    # Metadata rows
    writer.writerow(["_metadata", "envelope_id", str(envelope.id)])
    writer.writerow(["_metadata", "building_id", str(envelope.building_id)])
    writer.writerow(["_metadata", "version", envelope.version])
    writer.writerow(["_metadata", "status", envelope.status])
    writer.writerow(["_metadata", "content_hash", envelope.content_hash])
    writer.writerow(["_metadata", "exported_at", exported_at.isoformat()])

    for section in _ENVELOPE_SECTIONS:
        val = data.get(section)
        if val is None:
            continue
        if isinstance(val, dict):
            for k, v in _flatten_dict(val).items():
                writer.writerow([section, k, str(v) if v is not None else ""])
        else:
            writer.writerow([section, section, str(val)])

    return output.getvalue()


# ---------------------------------------------------------------------------
# generate_transfer_manifest
# ---------------------------------------------------------------------------


async def generate_transfer_manifest(db: AsyncSession, envelope_id: UUID) -> dict:
    """Generate a transfer manifest describing what is being transferred.

    The manifest lists:
    - Envelope identity and status
    - Which sections are included
    - What is redacted (financial, personal)
    - What the recipient will receive
    - What the recipient needs to acknowledge
    """
    envelope = await _get_envelope_or_raise(db, envelope_id)
    data: dict = envelope.passport_data or {}
    sections = envelope.sections_included or []

    # Determine redacted categories
    redacted_categories: list[str] = []
    if envelope.financials_redacted:
        redacted_categories.append("financial")
    if envelope.personal_data_redacted:
        redacted_categories.append("personal_data")

    # What the recipient will receive
    recipient_receives = {
        "sections": sections,
        "section_count": len(sections),
        "has_passport_grade": "passport_grade" in data,
        "has_knowledge_state": "knowledge_state" in data,
        "has_completeness": "completeness" in data,
        "has_readiness": "readiness" in data,
        "has_evidence_coverage": "evidence_coverage" in data,
        "content_hash": envelope.content_hash,
    }

    # What needs to be acknowledged
    acknowledgment_required = {
        "must_acknowledge_receipt": True,
        "must_verify_hash": True,
        "delivery_method": envelope.transfer_method or "pending",
        "envelope_status": envelope.status,
    }

    return {
        "envelope_id": str(envelope.id),
        "building_id": str(envelope.building_id),
        "version": envelope.version,
        "version_label": envelope.version_label,
        "status": envelope.status,
        "is_sovereign": envelope.is_sovereign,
        "redaction": {
            "profile": envelope.redaction_profile,
            "redacted_categories": redacted_categories,
            "financials_redacted": envelope.financials_redacted,
            "personal_data_redacted": envelope.personal_data_redacted,
        },
        "recipient_receives": recipient_receives,
        "acknowledgment_required": acknowledgment_required,
        "generated_at": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# validate_reimport
# ---------------------------------------------------------------------------


async def validate_reimport(db: AsyncSession, envelope_data: dict) -> dict:
    """Validate that imported envelope data is structurally valid for reimport.

    Checks structure, not content truth. Returns validation result with
    issues (blocking) and warnings (non-blocking).
    """
    issues: list[str] = []
    warnings: list[str] = []

    # 1. Required top-level keys
    for key in sorted(_REQUIRED_REIMPORT_KEYS):
        if key not in envelope_data:
            issues.append(f"Missing required key: '{key}'")

    # 2. passport_data must be a dict
    passport_data = envelope_data.get("passport_data")
    if passport_data is not None and not isinstance(passport_data, dict):
        issues.append("'passport_data' must be a JSON object (dict)")
    elif passport_data is not None:
        # Check for at least one recognized section
        recognized_sections = [s for s in _ENVELOPE_SECTIONS if s in passport_data]
        if not recognized_sections:
            warnings.append("No recognized passport sections found in passport_data")

        # Check passport_grade is a string
        grade = passport_data.get("passport_grade")
        if grade is not None and not isinstance(grade, str):
            warnings.append("passport_grade should be a string (e.g., 'A', 'B', 'C')")

    # 3. content_hash format
    content_hash = envelope_data.get("content_hash")
    if content_hash is not None:
        if not isinstance(content_hash, str):
            issues.append("'content_hash' must be a string")
        elif len(content_hash) < 8:
            warnings.append("content_hash looks unusually short (expected SHA-256)")

    # 4. Optional fields validation
    sections = envelope_data.get("sections_included")
    if sections is not None and not isinstance(sections, list):
        issues.append("'sections_included' must be a list")

    version = envelope_data.get("version")
    if version is not None and not isinstance(version, int):
        warnings.append("'version' should be an integer")

    redaction = envelope_data.get("redaction_profile")
    if redaction is not None and redaction not in _VALID_REDACTION_PROFILES:
        warnings.append(f"Unrecognized redaction_profile: '{redaction}'")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "sections_found": [s for s in _ENVELOPE_SECTIONS if isinstance(passport_data, dict) and s in passport_data],
    }
