"""
SwissBuildingOS - Proactive Alert Engine

Generates smart, rule-based proactive alerts for buildings and portfolios.
Each alert rule checks a specific condition and fires if triggered, producing
actionable recommendations.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.inventory_item import InventoryItem
from app.models.lease import Lease
from app.models.obligation import Obligation
from app.models.sample import Sample

# ---------------------------------------------------------------------------
# Alert rule registry
# ---------------------------------------------------------------------------

ALERT_RULES = [
    {
        "id": "missing_diagnostic",
        "check": "building_1960_1990_no_asbestos_diag",
        "message": "Bâtiment construit entre 1960-1990 sans diagnostic amiante",
        "urgency": "high",
    },
    {
        "id": "expiring_warranty",
        "check": "inventory_warranty_30d",
        "message": "Garantie équipement expire dans 30 jours",
        "urgency": "medium",
    },
    {
        "id": "lease_ending_renovation",
        "check": "lease_end_180d_pending_works",
        "message": "Fin de bail dans 6 mois — fenêtre de rénovation",
        "urgency": "low",
    },
    {
        "id": "climate_risk",
        "check": "high_freeze_thaw_friable_asbestos",
        "message": "Matériaux amiantés friables en zone de gel fréquent — dégradation accélérée",
        "urgency": "critical",
    },
    {
        "id": "obligation_approaching",
        "check": "obligation_deadline_60d",
        "message": "Obligation réglementaire dans 60 jours",
        "urgency": "high",
    },
    {
        "id": "similar_building_finding",
        "check": "twin_has_positive_diagnostic",
        "message": "Un bâtiment jumeau a un diagnostic positif — vérifiez le vôtre",
        "urgency": "medium",
    },
]


# ---------------------------------------------------------------------------
# Individual rule checkers
# ---------------------------------------------------------------------------


async def _check_missing_diagnostic(
    db: AsyncSession,
    building: Building,
) -> list[dict]:
    """Buildings built 1960-1990 without an asbestos diagnostic."""
    year = building.construction_year
    if year is None or not (1960 <= year <= 1990):
        return []

    stmt = select(Diagnostic).where(
        Diagnostic.building_id == building.id,
        Diagnostic.diagnostic_type == "asbestos",
    )
    result = await db.execute(stmt)
    if result.scalars().first() is not None:
        return []

    return [
        {
            "id": "missing_diagnostic",
            "message": ALERT_RULES[0]["message"],
            "urgency": "high",
            "triggered_by": f"construction_year={year}, no asbestos diagnostic",
            "recommended_action": "Planifier un diagnostic amiante dans les meilleurs délais",
            "data": {"construction_year": year},
        }
    ]


async def _check_expiring_warranty(
    db: AsyncSession,
    building: Building,
) -> list[dict]:
    """Equipment warranties expiring within 30 days."""
    today = date.today()
    horizon = today + timedelta(days=30)

    stmt = select(InventoryItem).where(
        InventoryItem.building_id == building.id,
        InventoryItem.warranty_end_date.isnot(None),
        InventoryItem.warranty_end_date >= today,
        InventoryItem.warranty_end_date <= horizon,
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    alerts = []
    for item in items:
        days_left = (item.warranty_end_date - today).days
        alerts.append(
            {
                "id": "expiring_warranty",
                "message": f"Garantie de '{item.name}' expire dans {days_left} jours",
                "urgency": "medium",
                "triggered_by": f"inventory_item={item.id}, warranty_end={item.warranty_end_date}",
                "recommended_action": (
                    f"Vérifier l'état de '{item.name}' et envisager une extension de garantie ou un remplacement"
                ),
                "data": {
                    "item_id": str(item.id),
                    "item_name": item.name,
                    "warranty_end_date": item.warranty_end_date.isoformat(),
                    "days_remaining": days_left,
                },
            }
        )
    return alerts


async def _check_lease_ending_renovation(
    db: AsyncSession,
    building: Building,
) -> list[dict]:
    """Leases ending within 180 days where there are pending works."""
    today = date.today()
    horizon = today + timedelta(days=180)

    # Check for ending leases
    lease_stmt = select(Lease).where(
        Lease.building_id == building.id,
        Lease.status == "active",
        Lease.date_end.isnot(None),
        Lease.date_end >= today,
        Lease.date_end <= horizon,
    )
    lease_result = await db.execute(lease_stmt)
    ending_leases = list(lease_result.scalars().all())
    if not ending_leases:
        return []

    # Check for pending interventions
    intervention_stmt = select(Intervention).where(
        Intervention.building_id == building.id,
        Intervention.status.in_(["planned", "in_progress"]),
    )
    intervention_result = await db.execute(intervention_stmt)
    pending = list(intervention_result.scalars().all())

    alerts = []
    for lease in ending_leases:
        days_left = (lease.date_end - today).days
        alerts.append(
            {
                "id": "lease_ending_renovation",
                "message": (
                    f"Bail {lease.reference_code} se termine dans {days_left} jours"
                    + (f" — {len(pending)} travaux en attente" if pending else " — fenêtre de rénovation possible")
                ),
                "urgency": "low" if not pending else "medium",
                "triggered_by": f"lease={lease.id}, end={lease.date_end}",
                "recommended_action": (
                    "Profiter de la fin de bail pour planifier les travaux de rénovation"
                    if not pending
                    else "Coordonner les travaux planifiés avec la fin de bail"
                ),
                "data": {
                    "lease_id": str(lease.id),
                    "lease_end": lease.date_end.isoformat(),
                    "pending_interventions": len(pending),
                },
            }
        )
    return alerts


async def _check_climate_risk(
    db: AsyncSession,
    building: Building,
    climate_stress: dict[str, float] | None = None,
) -> list[dict]:
    """High freeze-thaw exposure + friable asbestos materials."""
    stress = climate_stress or {}
    freeze_thaw = stress.get("freeze_thaw", 0.0)
    if freeze_thaw < 0.6:
        return []

    # Check for friable asbestos samples
    diag_stmt = select(Diagnostic).where(
        Diagnostic.building_id == building.id,
        Diagnostic.diagnostic_type == "asbestos",
    )
    diag_result = await db.execute(diag_stmt)
    diagnostics = list(diag_result.scalars().all())
    if not diagnostics:
        return []

    diag_ids = [d.id for d in diagnostics]
    sample_stmt = select(Sample).where(
        Sample.diagnostic_id.in_(diag_ids),
        Sample.threshold_exceeded.is_(True),
        Sample.pollutant_type == "asbestos",
    )
    sample_result = await db.execute(sample_stmt)
    positive_samples = list(sample_result.scalars().all())

    friable = [
        s for s in positive_samples if (s.material_state or "").lower() in ("friable", "friable_poor", "degraded")
    ]
    if not friable:
        return []

    return [
        {
            "id": "climate_risk",
            "message": ALERT_RULES[3]["message"],
            "urgency": "critical",
            "triggered_by": f"freeze_thaw={freeze_thaw}, friable_asbestos_samples={len(friable)}",
            "recommended_action": (
                "Intervention urgente recommandée — les cycles gel-dégel accélèrent "
                "la dégradation des matériaux amiantés friables"
            ),
            "data": {
                "freeze_thaw_exposure": freeze_thaw,
                "friable_sample_count": len(friable),
            },
        }
    ]


async def _check_obligation_approaching(
    db: AsyncSession,
    building: Building,
) -> list[dict]:
    """Regulatory obligations due within 60 days."""
    today = date.today()
    horizon = today + timedelta(days=60)

    stmt = select(Obligation).where(
        Obligation.building_id == building.id,
        Obligation.status.in_(["upcoming", "due_soon"]),
        Obligation.due_date >= today,
        Obligation.due_date <= horizon,
    )
    result = await db.execute(stmt)
    obligations = list(result.scalars().all())

    alerts = []
    for obl in obligations:
        days_left = (obl.due_date - today).days
        alerts.append(
            {
                "id": "obligation_approaching",
                "message": f"Obligation '{obl.title}' due dans {days_left} jours",
                "urgency": "high" if days_left <= 30 else "medium",
                "triggered_by": f"obligation={obl.id}, due={obl.due_date}",
                "recommended_action": f"Traiter l'obligation '{obl.title}' avant le {obl.due_date}",
                "data": {
                    "obligation_id": str(obl.id),
                    "title": obl.title,
                    "due_date": obl.due_date.isoformat(),
                    "days_remaining": days_left,
                    "obligation_type": obl.obligation_type,
                },
            }
        )
    return alerts


async def _check_twin_building_finding(
    db: AsyncSession,
    building: Building,
) -> list[dict]:
    """Similar building (same canton + similar era) has positive diagnostic that this building lacks."""
    if not building.canton or not building.construction_year:
        return []

    era_start = building.construction_year - 10
    era_end = building.construction_year + 10

    # Find peer buildings
    peer_stmt = (
        select(Building)
        .where(
            Building.id != building.id,
            Building.canton == building.canton,
            Building.construction_year >= era_start,
            Building.construction_year <= era_end,
        )
        .limit(50)
    )
    peer_result = await db.execute(peer_stmt)
    peers = list(peer_result.scalars().all())
    if not peers:
        return []

    peer_ids = [p.id for p in peers]

    # Fetch positive samples from peers
    peer_diag_stmt = select(Diagnostic).where(Diagnostic.building_id.in_(peer_ids))
    peer_diag_result = await db.execute(peer_diag_stmt)
    peer_diags = list(peer_diag_result.scalars().all())

    if not peer_diags:
        return []

    peer_diag_ids = [d.id for d in peer_diags]
    peer_sample_stmt = select(Sample).where(
        Sample.diagnostic_id.in_(peer_diag_ids),
        Sample.threshold_exceeded.is_(True),
        Sample.pollutant_type.isnot(None),
    )
    peer_sample_result = await db.execute(peer_sample_stmt)
    peer_positive_pollutants: set[str] = {s.pollutant_type for s in peer_sample_result.scalars().all()}

    # Our tested pollutants
    our_diag_stmt = select(Diagnostic).where(Diagnostic.building_id == building.id)
    our_diag_result = await db.execute(our_diag_stmt)
    our_diags = list(our_diag_result.scalars().all())
    our_tested: set[str] = set()
    if our_diags:
        our_diag_ids = [d.id for d in our_diags]
        our_sample_stmt = select(Sample).where(
            Sample.diagnostic_id.in_(our_diag_ids),
            Sample.pollutant_type.isnot(None),
        )
        our_sample_result = await db.execute(our_sample_stmt)
        our_tested = {s.pollutant_type for s in our_sample_result.scalars().all()}

    # Find pollutants positive in peers but untested here
    untested_risks = peer_positive_pollutants - our_tested
    if not untested_risks:
        return []

    alerts = []
    for pollutant in sorted(untested_risks):
        alerts.append(
            {
                "id": "similar_building_finding",
                "message": (
                    f"Un bâtiment jumeau ({building.canton}, ~{building.construction_year}) "
                    f"est positif pour {pollutant} — vérifiez le vôtre"
                ),
                "urgency": "medium",
                "triggered_by": f"peer_positive={pollutant}, untested_here",
                "recommended_action": f"Planifier un diagnostic {pollutant} par analogie avec les bâtiments similaires",
                "data": {
                    "pollutant": pollutant,
                    "peer_count": len(peers),
                    "canton": building.canton,
                    "era": f"{era_start}-{era_end}",
                },
            }
        )
    return alerts


# ---------------------------------------------------------------------------
# Rule dispatcher
# ---------------------------------------------------------------------------

_RULE_DISPATCH = {
    "building_1960_1990_no_asbestos_diag": _check_missing_diagnostic,
    "inventory_warranty_30d": _check_expiring_warranty,
    "lease_end_180d_pending_works": _check_lease_ending_renovation,
    "high_freeze_thaw_friable_asbestos": _check_climate_risk,
    "obligation_deadline_60d": _check_obligation_approaching,
    "twin_has_positive_diagnostic": _check_twin_building_finding,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_alerts(
    db: AsyncSession,
    building_id: UUID,
    climate_stress: dict[str, float] | None = None,
) -> list[dict]:
    """Run all alert rules against a building.

    Returns list of triggered alerts with id, message, urgency,
    triggered_by, recommended_action, and data.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    alerts: list[dict] = []

    for rule in ALERT_RULES:
        check_fn = _RULE_DISPATCH.get(rule["check"])
        if check_fn is None:
            continue

        # Climate risk checker needs extra param
        if rule["check"] == "high_freeze_thaw_friable_asbestos":
            rule_alerts = await check_fn(db, building, climate_stress)
        else:
            rule_alerts = await check_fn(db, building)

        alerts.extend(rule_alerts)

    # Sort by urgency: critical > high > medium > low
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda a: urgency_order.get(a.get("urgency", "low"), 4))

    return alerts


async def generate_portfolio_alerts(
    db: AsyncSession,
    org_id: UUID,
    climate_stress: dict[str, float] | None = None,
) -> list[dict]:
    """Generate alerts across all buildings in a portfolio.

    Returns all triggered alerts with building context added.
    """
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)
    if not buildings:
        return []

    all_alerts: list[dict] = []
    for building in buildings:
        building_alerts = await generate_alerts(db, building.id, climate_stress)
        for alert in building_alerts:
            alert["building_id"] = str(building.id)
            alert["building_address"] = building.address
        all_alerts.extend(building_alerts)

    # Sort by urgency
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_alerts.sort(key=lambda a: urgency_order.get(a.get("urgency", "low"), 4))

    return all_alerts
