"""Multi-audience Pack Builder service.

Generates audience-specific packs from a single canonical evidence base.
Each pack is a VIEW of the same building truth, filtered and shaped for
its target audience: authority, owner, insurer, contractor, notary, transfer.

Reuses existing section builders from authority_pack_service and adds
audience-specific section builders for cost, insurance, safety, etc.
"""

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.claim import Claim
from app.models.evidence_pack import EvidencePack
from app.models.financial_entry import FinancialEntry
from app.models.insurance_policy import InsurancePolicy
from app.models.intervention import Intervention
from app.models.obligation import Obligation
from app.models.zone import Zone
from app.schemas.pack_builder import (
    AvailablePacksResponse,
    PackConformanceResult,
    PackResult,
    PackSection,
    PackTypeInfo,
)

logger = logging.getLogger(__name__)

PACK_BUILDER_VERSION = "1.0.0"

# Map pack_type to conformance requirement profile name
PACK_TO_PROFILE: dict[str, str] = {
    "authority": "authority_pack",
    "insurer": "insurer_pack",
    "transfer": "transfer",
    "owner": "publication",
    "contractor": "publication",
    "notary": "transfer",
}

# ---------------------------------------------------------------------------
# Financial field redaction
# ---------------------------------------------------------------------------

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

# Sections that are entirely financial — replace items with redaction notice
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


PACK_TYPES = {
    "authority": {
        "name": "Pack Autorite",
        "sections": [
            "passport_summary",
            "completeness_report",
            "readiness_verdict",
            "pollutant_inventory",
            "diagnostic_summary",
            "compliance_status",
            "document_inventory",
            "contradictions",
            "caveats",
        ],
        "includes_trust": True,
        "includes_provenance": True,
    },
    "owner": {
        "name": "Pack Proprietaire",
        "sections": [
            "passport_summary",
            "completeness_report",
            "readiness_verdict",
            "cost_summary",
            "intervention_history",
            "upcoming_obligations",
            "insurance_status",
            "document_inventory",
            "caveats",
        ],
        "includes_trust": True,
        "includes_provenance": False,
    },
    "insurer": {
        "name": "Pack Assureur",
        "sections": [
            "passport_summary",
            "pollutant_inventory",
            "risk_summary",
            "intervention_history",
            "compliance_status",
            "claims_history",
            "readiness_verdict",
            "caveats",
        ],
        "includes_trust": True,
        "includes_provenance": True,
    },
    "contractor": {
        "name": "Pack Entreprise",
        "sections": [
            "scope_summary",
            "pollutant_inventory",
            "zones_concerned",
            "regulatory_requirements",
            "safety_requirements",
            "document_inventory",
            "work_conditions",
        ],
        "includes_trust": False,
        "includes_provenance": False,
    },
    "notary": {
        "name": "Pack Notaire / Transaction",
        "sections": [
            "passport_summary",
            "completeness_report",
            "pollutant_inventory",
            "intervention_history",
            "compliance_status",
            "upcoming_obligations",
            "contradictions",
            "caveats",
        ],
        "includes_trust": True,
        "includes_provenance": True,
    },
    "transfer": {
        "name": "Pack Transmission",
        "sections": ["full"],
        "includes_trust": True,
        "includes_provenance": True,
    },
}

_SECTION_NAMES = {
    "passport_summary": "Resume du passeport batiment",
    "completeness_report": "Rapport de completude du dossier",
    "readiness_verdict": "Verdict de readiness reglementaire",
    "pollutant_inventory": "Inventaire des polluants",
    "diagnostic_summary": "Synthese des diagnostics",
    "compliance_status": "Statut de conformite",
    "document_inventory": "Inventaire des documents",
    "contradictions": "Contradictions detectees",
    "caveats": "Reserves et limites",
    "intervention_history": "Historique des interventions",
    "cost_summary": "Synthese des couts",
    "upcoming_obligations": "Obligations a venir",
    "insurance_status": "Statut assurances",
    "risk_summary": "Synthese des risques",
    "claims_history": "Historique des sinistres",
    "scope_summary": "Perimetre des travaux",
    "zones_concerned": "Zones concernees",
    "regulatory_requirements": "Exigences reglementaires",
    "safety_requirements": "Exigences de securite",
    "work_conditions": "Conditions de travail",
}


# ---------------------------------------------------------------------------
# Section builders — new audience-specific sections
# (authority_pack_service sections are reused via delegation)
# ---------------------------------------------------------------------------


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


async def _build_pack_caveats(
    sections: list[PackSection], building: Building, pack_type: str, db: AsyncSession | None = None
) -> PackSection:
    """Build explicit caveats listing what is NOT covered or NOT verified.

    Includes first-class Caveat records from the database when db is provided.
    """
    caveats: list[dict] = []

    # 1. First-class caveats from the database (Commitment & Caveat graph)
    if db is not None:
        try:
            from app.services.commitment_service import get_caveats_for_pack

            db_caveats = await get_caveats_for_pack(db, building.id, pack_type)
            for c in db_caveats:
                caveats.append(
                    {
                        "caveat_type": c.caveat_type,
                        "message": f"{c.subject}: {c.description}" if c.description else c.subject,
                        "severity": c.severity,
                        "source": "commitment_graph",
                        "caveat_id": str(c.id),
                    }
                )
        except Exception:
            logger.warning("Failed to load first-class caveats for building %s", building.id)

    # Universal liability caveat
    caveats.append(
        {
            "caveat_type": "liability",
            "message": (
                "Ce pack ne constitue pas une garantie de conformite legale. "
                "Il s'agit d'un outil d'aide a la decision base sur les donnees disponibles."
            ),
            "severity": "info",
        }
    )

    # Low-completeness sections
    for s in sections:
        if s.completeness < 0.5 and s.section_type not in ("caveats",):
            caveats.append(
                {
                    "caveat_type": "incomplete_section",
                    "message": f"Section '{s.section_name}' incomplete ({round(s.completeness * 100)}%)",
                    "severity": "warning",
                    "section_type": s.section_type,
                }
            )

    # Building age warning
    if building.construction_year and building.construction_year < 1990:
        caveats.append(
            {
                "caveat_type": "building_age",
                "message": f"Batiment construit en {building.construction_year} — verifier la couverture amiante, PCB et plomb",
                "severity": "info",
            }
        )

    # Missing EGID
    if not building.egid:
        caveats.append(
            {
                "caveat_type": "missing_identity",
                "message": "EGID manquant — identification officielle incomplete",
                "severity": "warning",
            }
        )

    # PFAS caveat
    caveats.append(
        {
            "caveat_type": "regulatory",
            "message": (
                "Le cadre reglementaire PFAS est encore provisoire (OSEC/OFEV). "
                "Les seuils et obligations peuvent evoluer."
            ),
            "severity": "info",
        }
    )

    # Audience-specific caveats
    if pack_type == "notary":
        caveats.append(
            {
                "caveat_type": "transaction",
                "message": (
                    "Ce pack ne remplace pas un due diligence complet. "
                    "Les informations refletent l'etat connu a la date de generation."
                ),
                "severity": "warning",
            }
        )
    elif pack_type == "insurer":
        caveats.append(
            {
                "caveat_type": "insurance",
                "message": (
                    "L'evaluation des risques est basee sur les donnees declarees et les diagnostics disponibles. "
                    "Une inspection complementaire peut etre necessaire."
                ),
                "severity": "info",
            }
        )
    elif pack_type == "contractor":
        caveats.append(
            {
                "caveat_type": "scope",
                "message": (
                    "Le perimetre des travaux doit etre confirme par une visite de chantier. "
                    "Les quantites et conditions reelles peuvent differer."
                ),
                "severity": "warning",
            }
        )

    # Format caveat
    caveats.append(
        {
            "caveat_type": "format",
            "message": "Le pack est genere au format JSON. La generation PDF est prevue dans une version ulterieure.",
            "severity": "info",
        }
    )

    return PackSection(
        section_name=_SECTION_NAMES["caveats"],
        section_type="caveats",
        items=caveats,
        completeness=1.0,
        notes=f"{len(caveats)} reserve(s) identifiee(s)",
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
# Core pack builder
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


async def _run_auto_conformance(
    db: AsyncSession,
    building_id: uuid.UUID,
    pack_type: str,
    pack_id: uuid.UUID,
    checked_by_id: uuid.UUID | None = None,
) -> PackConformanceResult | None:
    """Run conformance check for a pack type. Advisory only — never blocks pack generation."""
    profile_name = PACK_TO_PROFILE.get(pack_type)
    if not profile_name:
        return None
    try:
        from app.services.conformance_service import run_conformance_check

        check = await run_conformance_check(
            db,
            building_id,
            profile_name,
            target_type="pack",
            target_id=pack_id,
            checked_by_id=checked_by_id,
        )
        return PackConformanceResult(
            profile=profile_name,
            result=check.result,
            score=check.score,
            failed_checks=check.checks_failed or [],
        )
    except Exception:
        logger.warning("Auto-conformance check failed for pack %s (profile=%s)", pack_id, profile_name)
        return None


async def generate_pack(
    db: AsyncSession,
    building_id: uuid.UUID,
    pack_type: str,
    org_id: uuid.UUID | None = None,
    created_by_id: uuid.UUID | None = None,
    redact_financials: bool = False,
) -> PackResult:
    """Generate an audience-specific pack from the canonical building data.

    Reuses passport_service, completeness_engine, readiness_reasoner.
    Each pack type includes different sections relevant to that audience.
    All packs share the same underlying truth -- only the view changes.
    """
    if pack_type not in PACK_TYPES:
        raise ValueError(f"Unknown pack type: {pack_type}")

    pack_config = PACK_TYPES[pack_type]

    # Handle transfer pack delegation
    if pack_type == "transfer":
        return await _generate_transfer_pack(db, building_id, created_by_id)

    # Fetch building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError("Building not found")

    section_types = pack_config["sections"]

    # Build sections
    sections: list[PackSection] = []
    warnings: list[str] = []

    for section_type in section_types:
        if section_type == "caveats":
            continue  # Built after all other sections

        section = await _build_section(db, building, section_type)
        if section:
            sections.append(section)
        else:
            warnings.append(f"Section non disponible: {section_type}")

    # Build caveats if applicable (includes first-class caveats from DB)
    if "caveats" in section_types:
        caveats_section = await _build_pack_caveats(sections, building, pack_type, db=db)
        sections.append(caveats_section)

    # Compute overall completeness (exclude caveats)
    scorable = [s for s in sections if s.section_type != "caveats"]
    overall_completeness = sum(s.completeness for s in scorable) / len(scorable) if scorable else 0.0

    # Count caveats
    caveats_section_data = next((s for s in sections if s.section_type == "caveats"), None)
    caveats_count = len(caveats_section_data.items) if caveats_section_data else 0

    # Apply financial redaction to the exported view if requested
    output_sections = sections
    if redact_financials:
        output_sections = [_redact_section(s) for s in sections]

    generated_at = datetime.now(UTC)
    pack_id = uuid.uuid4()

    # Build metadata and hash
    metadata = {
        "pack_type": pack_type,
        "pack_name": pack_config["name"],
        "overall_completeness": overall_completeness,
        "total_sections": len(sections),
        "warnings": warnings,
        "includes_trust": pack_config["includes_trust"],
        "includes_provenance": pack_config["includes_provenance"],
        "sections": [
            {
                "section_type": s.section_type,
                "section_name": s.section_name,
                "completeness": s.completeness,
                "item_count": len(s.items),
            }
            for s in sections
        ],
        "caveats_count": caveats_count,
        "pack_version": PACK_BUILDER_VERSION,
        "generated_by": str(created_by_id) if created_by_id else None,
        "generation_date": generated_at.isoformat(),
        "financials_redacted": redact_financials,
    }

    content_for_hash = json.dumps(metadata, sort_keys=True, default=str)
    content_hash = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()
    metadata["sha256_hash"] = content_hash

    # Create EvidencePack record
    pack_record = EvidencePack(
        id=pack_id,
        building_id=building_id,
        pack_type=f"pack_builder_{pack_type}",
        title=f"{pack_config['name']} - {building.address}",
        status="complete",
        created_by=created_by_id,
        assembled_at=generated_at,
        required_sections_json=[
            {"section_type": s.section_type, "label": s.section_name, "required": True, "included": True}
            for s in sections
        ],
        notes=json.dumps(metadata),
    )
    db.add(pack_record)
    await db.commit()

    # Auto-conformance check (advisory — does not block pack generation)
    conformance = await _run_auto_conformance(db, building_id, pack_type, pack_id, created_by_id)

    return PackResult(
        pack_id=pack_id,
        building_id=building_id,
        pack_type=pack_type,
        pack_name=pack_config["name"],
        sections=output_sections,
        total_sections=len(output_sections),
        overall_completeness=overall_completeness,
        includes_trust=pack_config["includes_trust"],
        includes_provenance=pack_config["includes_provenance"],
        generated_at=generated_at,
        warnings=warnings,
        caveats_count=caveats_count,
        pack_version=PACK_BUILDER_VERSION,
        sha256_hash=content_hash,
        financials_redacted=redact_financials,
        conformance=conformance,
    )


async def _generate_transfer_pack(
    db: AsyncSession,
    building_id: uuid.UUID,
    created_by_id: uuid.UUID | None,
) -> PackResult:
    """Delegate transfer pack to transfer_package_service and wrap result."""
    from app.services.transfer_package_service import generate_transfer_package

    transfer = await generate_transfer_package(db, building_id)
    if not transfer:
        raise ValueError("Building not found")

    generated_at = datetime.now(UTC)
    pack_id = uuid.uuid4()

    # Wrap transfer package sections into PackSection format
    sections: list[PackSection] = []
    transfer_dict = transfer.model_dump()
    for key, value in transfer_dict.items():
        if key in ("package_id", "building_id", "generated_at", "package_version", "sha256_hash"):
            continue
        if value and isinstance(value, (dict, list)):
            section_items = value if isinstance(value, list) else [value]
            sections.append(
                PackSection(
                    section_name=key.replace("_", " ").title(),
                    section_type=key,
                    items=[item if isinstance(item, dict) else {"value": item} for item in section_items],
                    completeness=1.0,
                )
            )

    overall_completeness = sum(s.completeness for s in sections) / len(sections) if sections else 0.0
    content_hash = transfer_dict.get("sha256_hash", "")

    # Auto-conformance check (advisory)
    conformance = await _run_auto_conformance(db, building_id, "transfer", pack_id, created_by_id)

    return PackResult(
        pack_id=pack_id,
        building_id=building_id,
        pack_type="transfer",
        pack_name="Pack Transmission",
        sections=sections,
        total_sections=len(sections),
        overall_completeness=overall_completeness,
        includes_trust=True,
        includes_provenance=True,
        generated_at=generated_at,
        warnings=[],
        caveats_count=0,
        pack_version=PACK_BUILDER_VERSION,
        sha256_hash=content_hash,
        conformance=conformance,
    )


async def list_available_packs(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> AvailablePacksResponse:
    """Return which pack types are available/ready for a building.

    Readiness is based on passport grade and completeness score.
    """
    # Check building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError("Building not found")

    # Get completeness score for readiness estimate
    completeness_score = 0.0
    try:
        from app.services.completeness_engine import evaluate_completeness

        comp_result = await evaluate_completeness(db, building_id)
        completeness_score = comp_result.overall_score
    except Exception:
        pass

    # Get passport grade
    passport_grade = "F"
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            passport_grade = passport.get("passport_grade", "F")
    except Exception:
        pass

    grade_score = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2}.get(passport_grade, 0.1)
    base_readiness = (completeness_score + grade_score) / 2

    packs: list[PackTypeInfo] = []
    for pack_type, config in PACK_TYPES.items():
        # Adjust readiness per pack type
        readiness_score = base_readiness
        if pack_type == "authority":
            # Authority packs need higher completeness
            readiness_score = min(base_readiness, completeness_score)
        elif pack_type == "contractor":
            # Contractor packs are less demanding
            readiness_score = min(1.0, base_readiness + 0.2)
        elif pack_type == "transfer":
            # Transfer packs need good overall data
            readiness_score = base_readiness

        if readiness_score >= 0.7:
            readiness = "ready"
        elif readiness_score >= 0.4:
            readiness = "partial"
        else:
            readiness = "not_ready"

        section_count = len(config["sections"])
        if pack_type == "transfer":
            section_count = 11  # transfer package has 11 sections

        packs.append(
            PackTypeInfo(
                pack_type=pack_type,
                name=config["name"],
                section_count=section_count,
                includes_trust=config["includes_trust"],
                includes_provenance=config["includes_provenance"],
                readiness=readiness,
                readiness_score=round(readiness_score, 2),
            )
        )

    return AvailablePacksResponse(building_id=building_id, packs=packs)
