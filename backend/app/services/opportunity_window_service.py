"""Detect and manage opportunity windows for buildings.

Extends the climate_opportunity_service with data-driven window detection
from building operational data: leases, inventory/maintenance, obligations,
and climate exposure profiles. Provides per-building and portfolio-level
queries with graceful degradation when data sources are missing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.climate_exposure import ClimateExposureProfile, OpportunityWindow
from app.models.inventory_item import InventoryItem
from app.models.lease import Lease
from app.models.obligation import Obligation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# How far ahead to look for opportunities (default)
DEFAULT_HORIZON_DAYS = 365

# Lease ending within this many days triggers a window
LEASE_WINDOW_THRESHOLD_DAYS = 180

# Warranty expiring within this many days triggers a window
WARRANTY_WINDOW_THRESHOLD_DAYS = 180

# Obligation due within this many days triggers a window
OBLIGATION_WINDOW_THRESHOLD_DAYS = 180

# Swiss altitude thresholds for weather window sizing
ALTITUDE_MOUNTAIN_THRESHOLD = 1000  # metres

# Lowland dry/construction season (Swiss plateau)
LOWLAND_SEASON_START_MONTH = 5  # May
LOWLAND_SEASON_END_MONTH = 9  # September
LOWLAND_OPTIMAL_MONTH = 7  # July

# Mountain short season
MOUNTAIN_SEASON_START_MONTH = 6  # June
MOUNTAIN_SEASON_END_MONTH = 8  # August
MOUNTAIN_OPTIMAL_MONTH = 7  # July


# ---------------------------------------------------------------------------
# Internal detectors
# ---------------------------------------------------------------------------


def _weather_window_from_profile(
    profile: ClimateExposureProfile | None,
    today: date,
    horizon: date,
) -> list[dict[str, Any]]:
    """Detect weather windows based on ClimateExposureProfile altitude/frost data.

    - Lowland (altitude < 1000 or frost_days < 60): May-Sep
    - Mountain (altitude >= 1000 or frost_days >= 60): Jun-Aug
    Falls back to lowland if no profile data available.
    """
    windows: list[dict[str, Any]] = []

    altitude = profile.altitude_m if profile else None
    frost_days = profile.freeze_thaw_cycles_per_year if profile else None

    is_mountain = (altitude is not None and altitude >= ALTITUDE_MOUNTAIN_THRESHOLD) or (
        frost_days is not None and frost_days >= 60
    )

    if is_mountain:
        start_month = MOUNTAIN_SEASON_START_MONTH
        end_month = MOUNTAIN_SEASON_END_MONTH
        optimal_month = MOUNTAIN_OPTIMAL_MONTH
        label = "montagne"
        confidence = 0.80 if altitude is not None else 0.60
    else:
        start_month = LOWLAND_SEASON_START_MONTH
        end_month = LOWLAND_SEASON_END_MONTH
        optimal_month = LOWLAND_OPTIMAL_MONTH
        label = "plaine"
        confidence = 0.85 if profile is not None else 0.50

    for y in (today.year, today.year + 1):
        w_start = date(y, start_month, 1)
        # Last day of end_month
        if end_month == 12:
            w_end = date(y, 12, 31)
        else:
            w_end = date(y, end_month + 1, 1) - timedelta(days=1)

        if w_end < today or w_start > horizon:
            continue

        eff_start = max(w_start, today)
        eff_end = min(w_end, horizon)
        if eff_start >= eff_end:
            continue

        windows.append(
            {
                "window_type": "weather",
                "title": f"Saison construction {label} {y}",
                "description": (
                    f"Periode favorable pour travaux exterieurs en {label} suisse. "
                    f"Faible pluviometrie et temperatures adequates."
                ),
                "window_start": eff_start,
                "window_end": eff_end,
                "optimal_date": date(y, optimal_month, 15),
                "advantage": f"Saison seche ({label}), conditions favorables",
                "expiry_risk": "medium" if (eff_end - today).days < 60 else "low",
                "cost_of_missing": "Report des travaux exterieurs d'un an",
                "confidence": confidence,
            }
        )

    return windows


async def _lease_windows(
    db: AsyncSession,
    building_id: uuid.UUID,
    today: date,
    horizon: date,
) -> list[dict[str, Any]]:
    """Detect lease-ending windows (renovation opportunity when tenant leaves)."""
    windows: list[dict[str, Any]] = []

    result = await db.execute(
        select(Lease).where(
            and_(
                Lease.building_id == building_id,
                Lease.status.in_(["active", "draft"]),
            )
        )
    )
    leases = list(result.scalars().all())

    for lease in leases:
        if lease.date_end is None:
            continue

        end_date = lease.date_end
        threshold = today + timedelta(days=LEASE_WINDOW_THRESHOLD_DAYS)

        if end_date < today or end_date > threshold:
            continue

        # Renovation window starts 30 days before lease end, extends 60 days after
        window_start = max(end_date - timedelta(days=30), today)
        window_end = min(end_date + timedelta(days=60), horizon)

        if window_start >= window_end:
            continue

        days_until = (end_date - today).days
        expiry_risk = "high" if days_until < 60 else ("medium" if days_until < 120 else "low")

        windows.append(
            {
                "window_type": "occupancy",
                "title": f"Fin de bail {lease.reference_code} — opportunite renovation",
                "description": (
                    f"Le bail {lease.reference_code} ({lease.lease_type}) se termine le {end_date.isoformat()}. "
                    f"Periode ideale pour des travaux de renovation avant la relocation."
                ),
                "window_start": window_start,
                "window_end": window_end,
                "optimal_date": end_date,
                "advantage": "Logement vide, acces libre pour travaux",
                "expiry_risk": expiry_risk,
                "cost_of_missing": "Travaux impossibles avec locataire en place, report au prochain depart",
                "confidence": 0.90,
            }
        )

    return windows


async def _maintenance_windows(
    db: AsyncSession,
    building_id: uuid.UUID,
    today: date,
    horizon: date,
) -> list[dict[str, Any]]:
    """Detect maintenance windows from inventory items with expiring warranties."""
    windows: list[dict[str, Any]] = []

    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.building_id == building_id,
        )
    )
    items = list(result.scalars().all())

    for item in items:
        if item.warranty_end_date is None:
            continue

        warranty_end = item.warranty_end_date
        threshold = today + timedelta(days=WARRANTY_WINDOW_THRESHOLD_DAYS)

        if warranty_end < today or warranty_end > threshold:
            continue

        # Window: from now until warranty end (act before warranty expires)
        window_start = today
        window_end = min(warranty_end, horizon)

        if window_start >= window_end:
            continue

        days_until = (warranty_end - today).days
        expiry_risk = "high" if days_until < 60 else ("medium" if days_until < 120 else "low")

        cost_str = "Perte de la couverture garantie"
        if item.replacement_cost_chf:
            cost_str += f" (remplacement estime: CHF {item.replacement_cost_chf:,.0f})"

        windows.append(
            {
                "window_type": "maintenance",
                "title": f"Garantie {item.name} expire le {warranty_end.isoformat()}",
                "description": (
                    f"La garantie de {item.name} ({item.item_type}) expire le {warranty_end.isoformat()}. "
                    f"Verifier l'etat et planifier un remplacement ou une extension de garantie."
                ),
                "window_start": window_start,
                "window_end": window_end,
                "optimal_date": warranty_end - timedelta(days=30) if days_until > 30 else today,
                "advantage": "Reparation/remplacement encore sous garantie",
                "expiry_risk": expiry_risk,
                "cost_of_missing": cost_str,
                "confidence": 0.95,
            }
        )

    return windows


async def _regulatory_windows(
    db: AsyncSession,
    building_id: uuid.UUID,
    today: date,
    horizon: date,
) -> list[dict[str, Any]]:
    """Detect regulatory windows from upcoming obligations."""
    windows: list[dict[str, Any]] = []

    result = await db.execute(
        select(Obligation).where(
            and_(
                Obligation.building_id == building_id,
                Obligation.status.in_(["upcoming", "due_soon"]),
            )
        )
    )
    obligations = list(result.scalars().all())

    for obl in obligations:
        if obl.due_date is None:
            continue

        due = obl.due_date
        threshold = today + timedelta(days=OBLIGATION_WINDOW_THRESHOLD_DAYS)

        if due < today or due > threshold:
            continue

        # Window opens now, closes at due date
        window_start = today
        window_end = min(due, horizon)

        if window_start >= window_end:
            continue

        days_until = (due - today).days
        expiry_risk = "high" if days_until < 60 else ("medium" if days_until < 120 else "low")

        confidence = (
            0.95
            if obl.obligation_type
            in (
                "regulatory_inspection",
                "authority_submission",
            )
            else 0.85
        )

        windows.append(
            {
                "window_type": "regulatory",
                "title": f"Echeance: {obl.title}",
                "description": (
                    f"L'obligation « {obl.title} » ({obl.obligation_type}) "
                    f"est due le {due.isoformat()}. Priorite: {obl.priority}."
                ),
                "window_start": window_start,
                "window_end": window_end,
                "optimal_date": due - timedelta(days=30) if days_until > 30 else today,
                "advantage": "Anticipation de l'echeance reglementaire",
                "expiry_risk": expiry_risk,
                "cost_of_missing": "Non-conformite reglementaire, risque de sanction ou d'arret de chantier",
                "confidence": confidence,
            }
        )

    return windows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def detect_windows(
    db: AsyncSession,
    building_id: uuid.UUID,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> list[OpportunityWindow]:
    """Detect all currently open opportunity windows for a building.

    Combines climate-based and data-driven detection:
    - Weather windows (from ClimateExposureProfile altitude/frost data)
    - Lease windows (leases ending soon)
    - Maintenance windows (warranties expiring)
    - Regulatory windows (obligations approaching deadline)

    Graceful degradation: if a data source is missing, that window type is skipped.
    """
    # Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    today = datetime.now(UTC).date()
    horizon = today + timedelta(days=horizon_days)

    # Load climate profile (may be None — graceful degradation)
    profile_result = await db.execute(
        select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building_id)
    )
    profile = profile_result.scalar_one_or_none()

    # Collect raw window dicts from all detectors
    raw_windows: list[dict[str, Any]] = []

    # Weather windows (always works, degrades without profile)
    raw_windows.extend(_weather_window_from_profile(profile, today, horizon))

    # Data-driven windows (skip silently on query errors)
    try:
        raw_windows.extend(await _lease_windows(db, building_id, today, horizon))
    except Exception:
        logger.warning("Lease window detection failed for building %s", building_id, exc_info=True)

    try:
        raw_windows.extend(await _maintenance_windows(db, building_id, today, horizon))
    except Exception:
        logger.warning("Maintenance window detection failed for building %s", building_id, exc_info=True)

    try:
        raw_windows.extend(await _regulatory_windows(db, building_id, today, horizon))
    except Exception:
        logger.warning("Regulatory window detection failed for building %s", building_id, exc_info=True)

    # Expire old active windows past their end date
    expired_result = await db.execute(
        select(OpportunityWindow).where(
            and_(
                OpportunityWindow.building_id == building_id,
                OpportunityWindow.status == "active",
                OpportunityWindow.window_end < today,
            )
        )
    )
    for expired in expired_result.scalars().all():
        expired.status = "expired"

    # Idempotent insert: skip if same type+title already active/used
    created: list[OpportunityWindow] = []
    for raw in raw_windows:
        check = await db.execute(
            select(OpportunityWindow).where(
                and_(
                    OpportunityWindow.building_id == building_id,
                    OpportunityWindow.window_type == raw["window_type"],
                    OpportunityWindow.title == raw["title"],
                    OpportunityWindow.status.in_(["active", "used"]),
                )
            )
        )
        if check.scalar_one_or_none() is not None:
            continue

        window = OpportunityWindow(
            building_id=building_id,
            window_type=raw["window_type"],
            title=raw["title"],
            description=raw.get("description"),
            window_start=raw["window_start"],
            window_end=raw["window_end"],
            optimal_date=raw.get("optimal_date"),
            advantage=raw.get("advantage"),
            expiry_risk=raw.get("expiry_risk", "low"),
            cost_of_missing=raw.get("cost_of_missing"),
            detected_by="system",
            confidence=raw.get("confidence", 0.7),
            status="active",
        )
        db.add(window)
        created.append(window)

    await db.flush()
    return created


async def list_building_windows(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> list[OpportunityWindow]:
    """List all active (non-expired) windows for a building."""
    today = datetime.now(UTC).date()
    result = await db.execute(
        select(OpportunityWindow).where(
            and_(
                OpportunityWindow.building_id == building_id,
                OpportunityWindow.status == "active",
                OpportunityWindow.window_end >= today,
            )
        )
    )
    return list(result.scalars().all())


async def list_portfolio_windows(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[OpportunityWindow]:
    """List all active windows across portfolio (org-scoped)."""
    today = datetime.now(UTC).date()
    result = await db.execute(
        select(OpportunityWindow)
        .join(Building, Building.id == OpportunityWindow.building_id)
        .where(
            and_(
                Building.organization_id == org_id,
                OpportunityWindow.status == "active",
                OpportunityWindow.window_end >= today,
            )
        )
    )
    return list(result.scalars().all())
