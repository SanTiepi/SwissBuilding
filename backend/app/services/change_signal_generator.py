"""
SwissBuildingOS - Change Signal Generator Service

Scans building data and generates ChangeSignal records for detected events.
Signals are idempotent: a signal with the same (signal_type, entity_type, entity_id)
is never duplicated.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building_risk_score import BuildingRiskScore
from app.models.change_signal import ChangeSignal
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
_DIAGNOSTIC_EXPIRY_WARN_YEARS = 4  # warn when older than 4 years
_ACTION_OVERDUE_DAYS = 30


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _existing_signal_keys(
    db: AsyncSession,
    building_id: UUID,
) -> set[tuple[str, str | None, UUID | None]]:
    """Return a set of (signal_type, entity_type, entity_id) for active signals."""
    result = await db.execute(
        select(
            ChangeSignal.signal_type,
            ChangeSignal.entity_type,
            ChangeSignal.entity_id,
        ).where(
            and_(
                ChangeSignal.building_id == building_id,
                ChangeSignal.status == "active",
            )
        )
    )
    return {(row[0], row[1], row[2]) for row in result.all()}


def _make_signal(
    building_id: UUID,
    signal_type: str,
    severity: str,
    title: str,
    description: str,
    source: str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    metadata_json: dict | None = None,
) -> ChangeSignal:
    return ChangeSignal(
        building_id=building_id,
        signal_type=signal_type,
        severity=severity,
        status="active",
        title=title,
        description=description,
        source=source,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata_json,
        detected_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Signal detectors
# ---------------------------------------------------------------------------


async def _detect_diagnostic_completed(
    db: AsyncSession,
    building_id: UUID,
    existing: set,
) -> list[ChangeSignal]:
    signals: list[ChangeSignal] = []
    result = await db.execute(
        select(Diagnostic).where(
            and_(
                Diagnostic.building_id == building_id,
                Diagnostic.status.in_(["completed", "validated"]),
            )
        )
    )
    for diag in result.scalars().all():
        key = ("diagnostic_completed", "diagnostic", diag.id)
        if key in existing:
            continue
        signals.append(
            _make_signal(
                building_id=building_id,
                signal_type="diagnostic_completed",
                severity="info",
                title=f"Diagnostic {diag.diagnostic_type} terminé",
                description=f"Le diagnostic {diag.diagnostic_type} est passé au statut {diag.status}.",
                source="diagnostic_service",
                entity_type="diagnostic",
                entity_id=diag.id,
            )
        )
    return signals


async def _detect_positive_samples(
    db: AsyncSession,
    building_id: UUID,
    existing: set,
) -> list[ChangeSignal]:
    signals: list[ChangeSignal] = []
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            and_(
                Diagnostic.building_id == building_id,
                Sample.threshold_exceeded.is_(True),
            )
        )
    )
    for sample in result.scalars().all():
        key = ("new_positive_sample", "sample", sample.id)
        if key in existing:
            continue
        signals.append(
            _make_signal(
                building_id=building_id,
                signal_type="new_positive_sample",
                severity="warning",
                title=f"Échantillon positif: {sample.pollutant_type}",
                description=(
                    f"Échantillon {sample.sample_number} ({sample.pollutant_type}) dépasse le seuil réglementaire."
                ),
                source="sample_analysis",
                entity_type="sample",
                entity_id=sample.id,
                metadata_json={
                    "pollutant_type": sample.pollutant_type,
                    "material_category": sample.material_category,
                },
            )
        )
    return signals


async def _detect_intervention_completed(
    db: AsyncSession,
    building_id: UUID,
    existing: set,
) -> list[ChangeSignal]:
    signals: list[ChangeSignal] = []
    result = await db.execute(
        select(Intervention).where(
            and_(
                Intervention.building_id == building_id,
                Intervention.status == "completed",
            )
        )
    )
    for interv in result.scalars().all():
        key = ("intervention_completed", "intervention", interv.id)
        if key in existing:
            continue
        signals.append(
            _make_signal(
                building_id=building_id,
                signal_type="intervention_completed",
                severity="info",
                title=f"Intervention terminée: {interv.title}",
                description=f"L'intervention « {interv.title} » ({interv.intervention_type}) est terminée.",
                source="intervention_service",
                entity_type="intervention",
                entity_id=interv.id,
            )
        )
    return signals


async def _detect_document_uploaded(
    db: AsyncSession,
    building_id: UUID,
    existing: set,
) -> list[ChangeSignal]:
    signals: list[ChangeSignal] = []
    result = await db.execute(select(Document).where(Document.building_id == building_id))
    for doc in result.scalars().all():
        key = ("document_uploaded", "document", doc.id)
        if key in existing:
            continue
        signals.append(
            _make_signal(
                building_id=building_id,
                signal_type="document_uploaded",
                severity="info",
                title=f"Document ajouté: {doc.file_name}",
                description=f"Le document « {doc.file_name} » ({doc.document_type}) a été ajouté.",
                source="document_service",
                entity_type="document",
                entity_id=doc.id,
            )
        )
    return signals


async def _detect_risk_level_change(
    db: AsyncSession,
    building_id: UUID,
    existing: set,
) -> list[ChangeSignal]:
    signals: list[ChangeSignal] = []
    result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    rs = result.scalar_one_or_none()
    if rs is None:
        return signals
    key = ("risk_level_change", "risk_score", rs.id)
    if key in existing:
        return signals
    severity = "warning" if rs.overall_risk_level in ("high", "critical") else "info"
    signals.append(
        _make_signal(
            building_id=building_id,
            signal_type="risk_level_change",
            severity=severity,
            title=f"Niveau de risque: {rs.overall_risk_level}",
            description=f"Le niveau de risque global du bâtiment est {rs.overall_risk_level}.",
            source="risk_engine",
            entity_type="risk_score",
            entity_id=rs.id,
            metadata_json={"overall_risk_level": rs.overall_risk_level, "confidence": rs.confidence},
        )
    )
    return signals


async def _detect_diagnostic_expiring(
    db: AsyncSession,
    building_id: UUID,
    existing: set,
) -> list[ChangeSignal]:
    signals: list[ChangeSignal] = []
    cutoff = datetime.now(UTC) - timedelta(days=_DIAGNOSTIC_EXPIRY_WARN_YEARS * 365)
    result = await db.execute(
        select(Diagnostic).where(
            and_(
                Diagnostic.building_id == building_id,
                Diagnostic.status.in_(["completed", "validated"]),
            )
        )
    )
    for diag in result.scalars().all():
        # Use date_inspection if available, else created_at
        ref_date = diag.date_inspection or (diag.created_at.date() if diag.created_at else None)
        if ref_date is None:
            continue
        if ref_date > cutoff.date():
            continue
        key = ("diagnostic_expiring", "diagnostic", diag.id)
        if key in existing:
            continue
        signals.append(
            _make_signal(
                building_id=building_id,
                signal_type="diagnostic_expiring",
                severity="warning",
                title=f"Diagnostic {diag.diagnostic_type} bientôt expiré",
                description=(
                    f"Le diagnostic {diag.diagnostic_type} date de {ref_date} "
                    f"et approche la limite de validité de 5 ans."
                ),
                source="requalification_monitor",
                entity_type="diagnostic",
                entity_id=diag.id,
            )
        )
    return signals


async def _detect_action_overdue(
    db: AsyncSession,
    building_id: UUID,
    existing: set,
) -> list[ChangeSignal]:
    signals: list[ChangeSignal] = []
    cutoff = datetime.now(UTC) - timedelta(days=_ACTION_OVERDUE_DAYS)
    result = await db.execute(
        select(ActionItem).where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status == "open",
                ActionItem.priority == "critical",
            )
        )
    )
    for action in result.scalars().all():
        if action.created_at is None or action.created_at > cutoff:
            continue
        key = ("action_overdue", "action_item", action.id)
        if key in existing:
            continue
        signals.append(
            _make_signal(
                building_id=building_id,
                signal_type="action_overdue",
                severity="warning",
                title=f"Action critique en retard: {action.title}",
                description=(
                    f"L'action « {action.title} » (priorité critique) est ouverte "
                    f"depuis plus de {_ACTION_OVERDUE_DAYS} jours."
                ),
                source="action_monitor",
                entity_type="action_item",
                entity_id=action.id,
            )
        )
    return signals


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DETECTORS = [
    _detect_diagnostic_completed,
    _detect_positive_samples,
    _detect_intervention_completed,
    _detect_document_uploaded,
    _detect_risk_level_change,
    _detect_diagnostic_expiring,
    _detect_action_overdue,
]


async def generate_signals_for_building(
    db: AsyncSession,
    building_id: UUID,
) -> list[ChangeSignal]:
    """Scan building data and generate change signals for detected events.

    This function is idempotent: signals with the same (signal_type, entity_type,
    entity_id) are never duplicated.
    """
    existing = await _existing_signal_keys(db, building_id)
    new_signals: list[ChangeSignal] = []

    for detector in _DETECTORS:
        detected = await detector(db, building_id, existing)
        new_signals.extend(detected)

    for sig in new_signals:
        db.add(sig)
    if new_signals:
        await db.flush()

    logger.info(
        "Generated %d change signals for building %s",
        len(new_signals),
        building_id,
    )
    return new_signals


async def acknowledge_signal(
    db: AsyncSession,
    signal_id: UUID,
    acknowledged_by: UUID,
) -> ChangeSignal:
    """Mark a signal as acknowledged."""
    result = await db.execute(select(ChangeSignal).where(ChangeSignal.id == signal_id))
    signal = result.scalar_one()
    signal.acknowledged_by = acknowledged_by
    signal.acknowledged_at = datetime.now(UTC)
    await db.flush()
    return signal


async def get_building_signal_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Return summary of active signals for a building."""
    result = await db.execute(
        select(ChangeSignal).where(
            and_(
                ChangeSignal.building_id == building_id,
                ChangeSignal.status == "active",
            )
        )
    )
    signals = result.scalars().all()

    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    unacknowledged = 0

    for sig in signals:
        by_type[sig.signal_type] = by_type.get(sig.signal_type, 0) + 1
        by_severity[sig.severity] = by_severity.get(sig.severity, 0) + 1
        if sig.acknowledged_at is None:
            unacknowledged += 1

    return {
        "total_active": len(signals),
        "by_type": by_type,
        "by_severity": by_severity,
        "unacknowledged": unacknowledged,
    }
