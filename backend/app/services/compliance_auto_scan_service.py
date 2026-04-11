"""Compliance auto-scan service.

Performs a comprehensive regulatory compliance scan for a building,
evaluating all applicable Swiss rules (OTConst, ORRChim, OFEN, CFST, LCI)
against available evidence (diagnostics, certificates, interventions).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention

# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class ComplianceStatus(StrEnum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ObligationType(StrEnum):
    ANALYSIS = "analysis"
    INSPECTION = "inspection"
    CERTIFICATION = "certification"
    DECLARATION = "declaration"
    REMEDIATION = "remediation"


class NonConformity(BaseModel):
    rule: str
    status: str = ComplianceStatus.NON_COMPLIANT
    evidence_needed: str
    deadline: date | None = None
    severity: str = Severity.HIGH


class ScanObligation(BaseModel):
    rule: str
    deadline: date | None = None
    obligation_type: str


class ComplianceScanResult(BaseModel):
    building_id: UUID
    scan_date: date = Field(default_factory=lambda: datetime.now(UTC).date())
    canton: str
    total_rules_applicable: int = 0
    compliant: int = 0
    non_compliant: int = 0
    unknown: int = 0
    score: float = 0.0
    non_conformities: list[NonConformity] = Field(default_factory=list)
    obligations: list[ScanObligation] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Rule catalogue — static regulatory rules to evaluate
# ---------------------------------------------------------------------------

_SCAN_RULES: list[dict] = [
    # OTConst — Asbestos
    {
        "code": "otconst_82",
        "rule": "OTConst Art. 82 — Analyse amiante avant travaux",
        "evidence": "diagnostic_amiante",
        "evidence_model": "diagnostic",
        "diagnostic_type": "asbestos",
        "severity": "high",
        "obligation_type": "analysis",
        "max_year": 1991,
        "deadline_days": 30,
    },
    {
        "code": "otconst_84",
        "rule": "OTConst Art. 84 — Plan d'assainissement amiante",
        "evidence": "plan_assainissement_amiante",
        "evidence_model": "intervention",
        "intervention_type": "asbestos_remediation",
        "severity": "high",
        "obligation_type": "remediation",
        "max_year": 1991,
        "deadline_days": 180,
        "requires_positive_diagnostic": "asbestos",
    },
    # ORRChim — PCB
    {
        "code": "orrchim_pcb",
        "rule": "ORRChim Annexe 2.15 — Analyse PCB joints/condensateurs",
        "evidence": "diagnostic_pcb",
        "evidence_model": "diagnostic",
        "diagnostic_type": "pcb",
        "severity": "high",
        "obligation_type": "analysis",
        "max_year": 1990,
        "deadline_days": 60,
    },
    # ORRChim — Lead
    {
        "code": "orrchim_lead",
        "rule": "ORRChim Annexe 2.18 — Analyse plomb peintures",
        "evidence": "diagnostic_plomb",
        "evidence_model": "diagnostic",
        "diagnostic_type": "lead",
        "severity": "medium",
        "obligation_type": "analysis",
        "max_year": 1960,
        "deadline_days": 90,
    },
    # HAP
    {
        "code": "orrchim_hap",
        "rule": "ORRChim — Analyse HAP etancheites/colles",
        "evidence": "diagnostic_hap",
        "evidence_model": "diagnostic",
        "diagnostic_type": "hap",
        "severity": "medium",
        "obligation_type": "analysis",
        "max_year": 1990,
        "deadline_days": 90,
    },
    # Radon — ORaP
    {
        "code": "orap_radon",
        "rule": "ORaP Art. 110 — Mesure radon",
        "evidence": "mesure_radon",
        "evidence_model": "diagnostic",
        "diagnostic_type": "radon",
        "severity": "medium",
        "obligation_type": "analysis",
        "cantons": None,  # all cantons
        "deadline_days": 180,
    },
    # PFAS
    {
        "code": "pfas_screening",
        "rule": "OFEV — Screening PFAS sites suspects",
        "evidence": "diagnostic_pfas",
        "evidence_model": "diagnostic",
        "diagnostic_type": "pfas",
        "severity": "medium",
        "obligation_type": "analysis",
        "deadline_days": 180,
    },
    # OFEN / CECB — Energy
    {
        "code": "ofen_cecb",
        "rule": "OFEN / MoPEC — Certificat energetique CECB",
        "evidence": "cecb_certificate",
        "evidence_model": "cecb",
        "severity": "medium",
        "obligation_type": "certification",
        "deadline_days": 365,
    },
    # CFST 6503 — Worker safety
    {
        "code": "cfst_6503",
        "rule": "CFST 6503 — Classification travaux amiante (mineur/moyen/majeur)",
        "evidence": "classification_cfst",
        "evidence_model": "artefact",
        "artefact_type": "cfst_classification",
        "severity": "high",
        "obligation_type": "inspection",
        "max_year": 1991,
        "deadline_days": 30,
        "requires_positive_diagnostic": "asbestos",
    },
    # OLED — Waste
    {
        "code": "oled_waste",
        "rule": "OLED — Bordereau suivi dechets speciaux",
        "evidence": "bordereau_oled",
        "evidence_model": "artefact",
        "artefact_type": "waste_manifest",
        "severity": "high",
        "obligation_type": "declaration",
        "deadline_days": 90,
        "requires_positive_diagnostic": "asbestos",
    },
    # LCI — Canton-level building permit
    {
        "code": "lci_permit",
        "rule": "LCI / LATC — Permis de construire cantonal",
        "evidence": "permis_construire",
        "evidence_model": "artefact",
        "artefact_type": "building_permit",
        "severity": "low",
        "obligation_type": "certification",
        "deadline_days": 365,
    },
    # Fire safety
    {
        "code": "aeai_fire",
        "rule": "AEAI — Concept protection incendie",
        "evidence": "concept_incendie",
        "evidence_model": "artefact",
        "artefact_type": "fire_safety_concept",
        "severity": "medium",
        "obligation_type": "certification",
        "deadline_days": 365,
    },
]


# ---------------------------------------------------------------------------
# Applicability helpers
# ---------------------------------------------------------------------------


def _rule_applies(rule: dict, building: Building) -> bool:
    """Check if a rule applies to a given building based on its attributes."""
    # Construction year filter
    max_year = rule.get("max_year")
    if max_year and building.construction_year and building.construction_year > max_year:
        return False

    # Canton filter
    cantons = rule.get("cantons")
    if cantons is not None:
        return building.canton in cantons

    return True


async def _has_diagnostic(db: AsyncSession, building_id: UUID, diag_type: str) -> bool:
    """Check if building has a diagnostic of the given type (any status)."""
    result = await db.execute(
        select(func.count())
        .select_from(Diagnostic)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.diagnostic_type == diag_type,
        )
    )
    return (result.scalar() or 0) > 0


async def _has_positive_diagnostic(db: AsyncSession, building_id: UUID, diag_type: str) -> bool:
    """Check if building has a completed diagnostic with positive findings."""
    result = await db.execute(
        select(func.count())
        .select_from(Diagnostic)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.diagnostic_type == diag_type,
            Diagnostic.status.in_(["completed", "validated"]),
            Diagnostic.conclusion.in_(["positive", "present", "detected"]),
        )
    )
    return (result.scalar() or 0) > 0


async def _has_intervention(db: AsyncSession, building_id: UUID, intervention_type: str) -> bool:
    """Check if building has an intervention of the given type."""
    result = await db.execute(
        select(func.count())
        .select_from(Intervention)
        .where(
            Intervention.building_id == building_id,
            Intervention.intervention_type == intervention_type,
        )
    )
    return (result.scalar() or 0) > 0


async def _has_artefact(db: AsyncSession, building_id: UUID, artefact_type: str) -> bool:
    """Check if building has a compliance artefact of the given type."""
    result = await db.execute(
        select(func.count())
        .select_from(ComplianceArtefact)
        .where(
            ComplianceArtefact.building_id == building_id,
            ComplianceArtefact.artefact_type == artefact_type,
        )
    )
    return (result.scalar() or 0) > 0


def _has_cecb(building: Building) -> bool:
    """Check if building has a CECB energy certificate."""
    return building.cecb_class is not None


# ---------------------------------------------------------------------------
# Evidence checker dispatch
# ---------------------------------------------------------------------------


async def _check_evidence(db: AsyncSession, building: Building, rule: dict) -> ComplianceStatus:
    """Check if compliance evidence exists for a given rule."""
    # If rule requires a positive diagnostic first, check that
    requires_positive = rule.get("requires_positive_diagnostic")
    if requires_positive:
        has_positive = await _has_positive_diagnostic(db, building.id, requires_positive)
        if not has_positive:
            # Rule only applies if pollutant was found — if no positive diagnostic, rule is N/A
            return ComplianceStatus.COMPLIANT

    model = rule["evidence_model"]

    if model == "diagnostic":
        found = await _has_diagnostic(db, building.id, rule["diagnostic_type"])
        return ComplianceStatus.COMPLIANT if found else ComplianceStatus.NON_COMPLIANT

    if model == "intervention":
        found = await _has_intervention(db, building.id, rule["intervention_type"])
        return ComplianceStatus.COMPLIANT if found else ComplianceStatus.NON_COMPLIANT

    if model == "artefact":
        found = await _has_artefact(db, building.id, rule["artefact_type"])
        return ComplianceStatus.COMPLIANT if found else ComplianceStatus.NON_COMPLIANT

    if model == "cecb":
        return ComplianceStatus.COMPLIANT if _has_cecb(building) else ComplianceStatus.NON_COMPLIANT

    return ComplianceStatus.UNKNOWN


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------


async def scan_compliance(db: AsyncSession, building_id: UUID) -> ComplianceScanResult | None:
    """Run a full compliance scan for a building.

    Returns None if the building does not exist.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    applicable_rules: list[dict] = []
    for rule in _SCAN_RULES:
        if _rule_applies(rule, building):
            applicable_rules.append(rule)

    compliant_count = 0
    non_compliant_count = 0
    unknown_count = 0
    non_conformities: list[NonConformity] = []
    obligations: list[ScanObligation] = []

    today = datetime.now(UTC).date()

    for rule in applicable_rules:
        status = await _check_evidence(db, building, rule)

        if status == ComplianceStatus.COMPLIANT:
            compliant_count += 1
        elif status == ComplianceStatus.NON_COMPLIANT:
            non_compliant_count += 1
            deadline_days = rule.get("deadline_days", 90)
            deadline = today + timedelta(days=deadline_days)
            non_conformities.append(
                NonConformity(
                    rule=rule["rule"],
                    evidence_needed=rule["evidence"],
                    deadline=deadline,
                    severity=rule.get("severity", "medium"),
                )
            )
            obligations.append(
                ScanObligation(
                    rule=rule["rule"],
                    deadline=deadline,
                    obligation_type=rule.get("obligation_type", "analysis"),
                )
            )
        else:
            unknown_count += 1

    total = len(applicable_rules)
    score = round((compliant_count / total) * 100, 1) if total > 0 else 100.0

    return ComplianceScanResult(
        building_id=building_id,
        canton=building.canton,
        total_rules_applicable=total,
        compliant=compliant_count,
        non_compliant=non_compliant_count,
        unknown=unknown_count,
        score=score,
        non_conformities=non_conformities,
        obligations=obligations,
    )
