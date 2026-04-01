"""Section builders for audience-specific pack sections.

Each async function builds one PackSection from the database.
The ``_build_section`` dispatcher delegates to the appropriate builder
or falls back to authority_pack_service builders.
"""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.claim import Claim
from app.models.financial_entry import FinancialEntry
from app.models.insurance_policy import InsurancePolicy
from app.models.intervention import Intervention
from app.models.obligation import Obligation
from app.models.zone import Zone
from app.schemas.pack_builder import PackSection
from app.services.pack_builder.pack_types import _SECTION_NAMES

logger = logging.getLogger(__name__)


async def _build_cost_summary(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build cost summary from financial entries."""
    result = await db.execute(
        select(FinancialEntry)
        .where(FinancialEntry.building_id == building_id)
        .order_by(FinancialEntry.entry_date.desc())
    )
    entries = result.scalars().all()

    total_expenses = sum(e.amount_chf for e in entries if e.entry_type == "expense" and e.amount_chf)
    total_income = sum(e.amount_chf for e in entries if e.entry_type == "income" and e.amount_chf)

    # Group expenses by category
    expense_by_cat: dict[str, float] = {}
    for e in entries:
        if e.entry_type == "expense" and e.amount_chf:
            expense_by_cat[e.category] = expense_by_cat.get(e.category, 0) + e.amount_chf

    items: list[dict] = [
        {
            "total_expenses_chf": round(total_expenses, 2),
            "total_income_chf": round(total_income, 2),
            "entry_count": len(entries),
            "expense_by_category": expense_by_cat,
            "source": "financial_entries",
        }
    ]

    completeness = 1.0 if entries else 0.0
    notes = f"{len(entries)} ecriture(s) financiere(s)" if entries else "Aucune donnee financiere"

    return PackSection(
        section_name=_SECTION_NAMES["cost_summary"],
        section_type="cost_summary",
        items=items,
        completeness=completeness,
        notes=notes,
    )


async def _build_upcoming_obligations(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build upcoming obligations section."""
    result = await db.execute(
        select(Obligation)
        .where(
            Obligation.building_id == building_id,
            Obligation.status.in_(["upcoming", "due_soon", "overdue"]),
        )
        .order_by(Obligation.due_date.asc())
    )
    obligations = result.scalars().all()

    items = [
        {
            "obligation_id": str(o.id),
            "title": o.title,
            "obligation_type": o.obligation_type,
            "due_date": str(o.due_date) if o.due_date else None,
            "status": o.status,
            "priority": o.priority,
            "recurrence": o.recurrence,
        }
        for o in obligations
    ]

    overdue_count = sum(1 for o in obligations if o.status == "overdue")
    completeness = 1.0 if not overdue_count else max(0.3, 1.0 - (overdue_count * 0.15))
    notes = f"{len(items)} obligation(s) active(s)"
    if overdue_count:
        notes += f", {overdue_count} en retard"

    return PackSection(
        section_name=_SECTION_NAMES["upcoming_obligations"],
        section_type="upcoming_obligations",
        items=items,
        completeness=completeness,
        notes=notes,
    )


async def _build_insurance_status(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build insurance status section."""
    result = await db.execute(
        select(InsurancePolicy)
        .where(InsurancePolicy.building_id == building_id)
        .order_by(InsurancePolicy.date_start.desc().nulls_last())
    )
    policies = result.scalars().all()

    items = [
        {
            "policy_id": str(p.id),
            "policy_type": p.policy_type,
            "policy_number": p.policy_number,
            "insurer_name": p.insurer_name,
            "insured_value_chf": p.insured_value_chf,
            "premium_annual_chf": p.premium_annual_chf,
            "date_start": str(p.date_start) if p.date_start else None,
            "date_end": str(p.date_end) if p.date_end else None,
            "status": p.status,
        }
        for p in policies
    ]

    active_count = sum(1 for p in policies if p.status == "active")
    completeness = 1.0 if active_count > 0 else 0.0
    notes = f"{active_count} police(s) active(s) sur {len(items)}" if items else "Aucune police d'assurance"

    return PackSection(
        section_name=_SECTION_NAMES["insurance_status"],
        section_type="insurance_status",
        items=items,
        completeness=completeness,
        notes=notes,
    )


async def _build_risk_summary(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build risk summary from risk scores."""
    result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_score = result.scalar_one_or_none()

    items: list[dict] = []
    if risk_score:
        items.append(
            {
                "overall_risk_level": risk_score.overall_risk_level,
                "confidence": risk_score.confidence,
                "asbestos_probability": risk_score.asbestos_probability,
                "pcb_probability": risk_score.pcb_probability,
                "lead_probability": risk_score.lead_probability,
                "hap_probability": risk_score.hap_probability,
                "radon_probability": risk_score.radon_probability,
                "data_source": risk_score.data_source,
                "source": "risk_engine",
            }
        )

    completeness = 1.0 if items else 0.0

    return PackSection(
        section_name=_SECTION_NAMES["risk_summary"],
        section_type="risk_summary",
        items=items,
        completeness=completeness,
        notes="Evaluation des risques disponible" if items else "Aucune evaluation des risques",
    )


async def _build_claims_history(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build claims history section."""
    result = await db.execute(
        select(Claim).where(Claim.building_id == building_id).order_by(Claim.incident_date.desc().nulls_last())
    )
    claims = result.scalars().all()

    items = [
        {
            "claim_id": str(c.id),
            "claim_type": c.claim_type,
            "reference_number": c.reference_number,
            "status": c.status,
            "incident_date": str(c.incident_date) if c.incident_date else None,
            "claimed_amount_chf": c.claimed_amount_chf,
            "approved_amount_chf": c.approved_amount_chf,
            "paid_amount_chf": c.paid_amount_chf,
        }
        for c in claims
    ]

    completeness = 1.0 if not claims else (1.0 if all(c.status in ("settled", "closed") for c in claims) else 0.7)
    open_count = sum(1 for c in claims if c.status in ("open", "in_review"))
    notes = f"{len(items)} sinistre(s)"
    if open_count:
        notes += f", {open_count} en cours"

    return PackSection(
        section_name=_SECTION_NAMES["claims_history"],
        section_type="claims_history",
        items=items,
        completeness=completeness,
        notes=notes if items else "Aucun sinistre enregistre",
    )


async def _build_scope_summary(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build scope summary for contractor pack."""
    # Gather interventions as scope reference
    result = await db.execute(
        select(Intervention)
        .where(Intervention.building_id == building_id)
        .order_by(Intervention.date_start.desc().nulls_last())
    )
    interventions = result.scalars().all()

    # Gather zones count
    zone_count = (
        await db.execute(select(func.count()).select_from(Zone).where(Zone.building_id == building_id))
    ).scalar() or 0

    items: list[dict] = [
        {
            "intervention_count": len(interventions),
            "zone_count": zone_count,
            "interventions": [
                {
                    "title": i.title,
                    "type": i.intervention_type,
                    "status": i.status,
                    "date_start": str(i.date_start) if i.date_start else None,
                    "date_end": str(i.date_end) if i.date_end else None,
                }
                for i in interventions[:10]  # limit for readability
            ],
            "source": "interventions + zones",
        }
    ]

    completeness = 1.0 if interventions else 0.3
    notes = f"{len(interventions)} intervention(s), {zone_count} zone(s)"

    return PackSection(
        section_name=_SECTION_NAMES["scope_summary"],
        section_type="scope_summary",
        items=items,
        completeness=completeness,
        notes=notes,
    )


async def _build_zones_concerned(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build zones concerned section for contractor pack."""
    result = await db.execute(
        select(Zone).where(Zone.building_id == building_id).order_by(Zone.floor_number.asc().nulls_last())
    )
    zones = result.scalars().all()

    items = [
        {
            "zone_id": str(z.id),
            "name": z.name,
            "zone_type": z.zone_type,
            "floor_number": z.floor_number,
            "surface_area_m2": float(z.surface_area_m2) if z.surface_area_m2 else None,
            "usage_type": z.usage_type,
        }
        for z in zones
    ]

    completeness = 1.0 if items else 0.0

    return PackSection(
        section_name=_SECTION_NAMES["zones_concerned"],
        section_type="zones_concerned",
        items=items,
        completeness=completeness,
        notes=f"{len(items)} zone(s) repertoriee(s)" if items else "Aucune zone definie",
    )


async def _build_regulatory_requirements(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build regulatory requirements section (CFST/SUVA/OTConst)."""
    # Derive requirements from building data
    building = (await db.execute(select(Building).where(Building.id == building_id))).scalar_one_or_none()

    items: list[dict] = []
    if building:
        # Always applicable Swiss regulations
        items.append(
            {
                "regulation": "OTConst Art. 60a / 82-86",
                "domain": "Amiante",
                "description": "Obligation de diagnostic amiante avant travaux (batiments avant 1990)",
                "applicable": building.construction_year is not None and building.construction_year < 1990,
            }
        )
        items.append(
            {
                "regulation": "CFST 6503",
                "domain": "Travaux",
                "description": "Classification des travaux (mineur/moyen/majeur) et mesures de protection",
                "applicable": True,
            }
        )
        items.append(
            {
                "regulation": "ORRChim Annexe 2.15",
                "domain": "PCB",
                "description": "Seuil PCB 50 mg/kg — obligation d'assainissement si depasse",
                "applicable": True,
            }
        )
        items.append(
            {
                "regulation": "ORRChim Annexe 2.18",
                "domain": "Plomb",
                "description": "Seuil plomb 5000 mg/kg — obligation d'assainissement si depasse",
                "applicable": True,
            }
        )
        items.append(
            {
                "regulation": "OLED",
                "domain": "Dechets",
                "description": "Classification des dechets (type_b/type_e/special) et elimination conforme",
                "applicable": True,
            }
        )
        items.append(
            {
                "regulation": "ORaP Art. 110",
                "domain": "Radon",
                "description": "Seuils radon 300/1000 Bq/m3 — mesures correctives si depasses",
                "applicable": True,
            }
        )

    completeness = 1.0

    return PackSection(
        section_name=_SECTION_NAMES["regulatory_requirements"],
        section_type="regulatory_requirements",
        items=items,
        completeness=completeness,
        notes=f"{sum(1 for i in items if i.get('applicable'))} reglementations applicables",
    )


async def _build_safety_requirements(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build safety requirements for contractor (CFST/SUVA rules)."""
    items: list[dict] = [
        {
            "requirement": "Port EPI obligatoire",
            "category": "protection_individuelle",
            "description": "Masque FFP3, combinaison type 5/6, gants nitrile selon CFST 6503",
            "severity": "critical",
        },
        {
            "requirement": "Zone de confinement",
            "category": "confinement",
            "description": "Zone hermetique avec depression pour travaux majeurs amiante",
            "severity": "critical",
        },
        {
            "requirement": "Mesures d'air",
            "category": "monitoring",
            "description": "Mesures d'empoussierement avant, pendant et apres travaux",
            "severity": "high",
        },
        {
            "requirement": "Gestion des dechets",
            "category": "dechets",
            "description": "Big-bags doubles, etiquetage OLED, bordereau de suivi",
            "severity": "high",
        },
        {
            "requirement": "Formation du personnel",
            "category": "formation",
            "description": "Attestation SUVA/CFST valide pour tous les intervenants",
            "severity": "critical",
        },
    ]

    return PackSection(
        section_name=_SECTION_NAMES["safety_requirements"],
        section_type="safety_requirements",
        items=items,
        completeness=1.0,
        notes=f"{len(items)} exigences de securite",
    )


async def _build_work_conditions(db: AsyncSession, building_id: uuid.UUID) -> PackSection:
    """Build work conditions section for contractor pack."""
    building = (await db.execute(select(Building).where(Building.id == building_id))).scalar_one_or_none()

    items: list[dict] = []
    if building:
        items.append(
            {
                "building_address": f"{building.address}, {building.postal_code} {building.city}",
                "canton": building.canton,
                "building_type": building.building_type,
                "construction_year": building.construction_year,
                "floors_above": building.floors_above,
                "floors_below": building.floors_below,
                "access_notes": "A definir lors de la visite de chantier",
                "working_hours": "Selon reglementation communale et conventions collectives",
                "parking_available": "A confirmer",
            }
        )

    return PackSection(
        section_name=_SECTION_NAMES["work_conditions"],
        section_type="work_conditions",
        items=items,
        completeness=1.0 if items else 0.0,
        notes="Conditions de travail generales",
    )


# ---------------------------------------------------------------------------
# New section builders registry
# ---------------------------------------------------------------------------

_NEW_SECTION_BUILDERS = {
    "cost_summary": _build_cost_summary,
    "upcoming_obligations": _build_upcoming_obligations,
    "insurance_status": _build_insurance_status,
    "risk_summary": _build_risk_summary,
    "claims_history": _build_claims_history,
    "scope_summary": _build_scope_summary,
    "zones_concerned": _build_zones_concerned,
    "regulatory_requirements": _build_regulatory_requirements,
    "safety_requirements": _build_safety_requirements,
    "work_conditions": _build_work_conditions,
}


# ---------------------------------------------------------------------------
# Section dispatcher
# ---------------------------------------------------------------------------


async def _build_section(db: AsyncSession, building: Building, section_type: str) -> PackSection | None:
    """Build a single section, delegating to authority_pack_service or new builders."""
    building_id = building.id

    # Try new section builders first
    if section_type in _NEW_SECTION_BUILDERS:
        return await _NEW_SECTION_BUILDERS[section_type](db, building_id)

    # Delegate to authority_pack_service section builders
    try:
        from app.services.authority_pack_service import _SECTION_BUILDERS as AUTH_BUILDERS

        if section_type in AUTH_BUILDERS:
            builder = AUTH_BUILDERS[section_type]
            if section_type == "building_identity":
                auth_section = await builder(db, building)
            else:
                auth_section = await builder(db, building_id)
            # Convert AuthorityPackSection to PackSection
            return PackSection(
                section_name=auth_section.section_name,
                section_type=auth_section.section_type,
                items=auth_section.items,
                completeness=auth_section.completeness,
                notes=auth_section.notes,
            )
    except Exception as e:
        logger.warning("Failed to build section %s: %s", section_type, e)

    return None
