"""Eco clause template service for authority pack consumption.

Generates structured contractual clause templates related to environmental and
pollutant management during renovation or demolition. Clauses reference the Swiss
regulatory framework (OTConst, CFST, ORRChim, OLED, ORaP) and are deterministic:
same building state + context → identical output.

No external API calls or web scraping — all clause content is derived from the
building's pollutant data and static regulatory references.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import ALL_POLLUTANTS
from app.models.building import Building
from app.models.diagnostic import Diagnostic

# ---------------------------------------------------------------------------
# Payload types (plain dataclasses — no Pydantic needed for internal use)
# ---------------------------------------------------------------------------

EcoClauseContext = Literal["renovation", "demolition"]


@dataclass(frozen=True)
class EcoClause:
    """A single contractual clause."""

    clause_id: str
    title: str
    body: str
    legal_references: list[str]
    applicability: str  # Human-readable condition description
    pollutants: list[str]  # Which pollutants trigger this clause


@dataclass(frozen=True)
class EcoClauseSection:
    """A group of related clauses."""

    section_id: str
    title: str
    clauses: list[EcoClause]


@dataclass(frozen=True)
class EcoClausePayload:
    """Full eco clause output for a building + context."""

    building_id: uuid.UUID
    context: EcoClauseContext
    generated_at: datetime
    sections: list[EcoClauseSection]
    total_clauses: int
    detected_pollutants: list[str]
    provenance: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Regulatory reference constants (deterministic, no scraping)
# ---------------------------------------------------------------------------

_LEGAL_REFS = {
    "otconst_60a": "OTConst Art. 60a",
    "otconst_82_86": "OTConst Art. 82-86",
    "cfst_6503": "CFST 6503 (categories de travaux)",
    "orrchim_2_15": "ORRChim Annexe 2.15 (PCB > 50 mg/kg)",
    "orrchim_2_18": "ORRChim Annexe 2.18 (plomb > 5000 mg/kg)",
    "oled_waste": "OLED (elimination des dechets: type_b / type_e / special)",
    "orap_110": "ORaP Art. 110 (radon: 300 / 1000 Bq/m3)",
}


# ---------------------------------------------------------------------------
# Clause catalogue — static, keyed by (context, pollutant-presence)
# ---------------------------------------------------------------------------


def _common_clauses(detected: set[str]) -> list[EcoClauseSection]:
    """Clauses applicable to both renovation and demolition."""
    sections: list[EcoClauseSection] = []

    # --- General obligation section (always present) ---
    general_clauses: list[EcoClause] = [
        EcoClause(
            clause_id="GEN-01",
            title="Diagnostic prealable obligatoire",
            body=(
                "Avant le debut des travaux, un diagnostic polluants complet doit etre "
                "realise par un diagnostiqueur certifie. Le rapport doit couvrir l'ensemble "
                "des substances reglementees (amiante, PCB, plomb, HAP, radon) conformement "
                "aux exigences cantonales."
            ),
            legal_references=[_LEGAL_REFS["otconst_60a"]],
            applicability="Toujours applicable avant travaux",
            pollutants=[],
        ),
        EcoClause(
            clause_id="GEN-02",
            title="Plan d'elimination des dechets",
            body=(
                "Un plan d'elimination des dechets de chantier doit etre etabli avant "
                "le demarrage des travaux. Les dechets contenant des polluants doivent "
                "etre tries, stockes separement et elimines conformement a l'OLED."
            ),
            legal_references=[_LEGAL_REFS["oled_waste"]],
            applicability="Toujours applicable",
            pollutants=[],
        ),
    ]
    sections.append(
        EcoClauseSection(
            section_id="SEC-GEN",
            title="Obligations generales",
            clauses=general_clauses,
        )
    )

    # --- Asbestos section ---
    if "asbestos" in detected:
        asbestos_clauses: list[EcoClause] = [
            EcoClause(
                clause_id="AMI-01",
                title="Notification SUVA obligatoire",
                body=(
                    "L'entrepreneur doit notifier la SUVA avant le debut de tout travail "
                    "susceptible de liberer des fibres d'amiante. La notification doit "
                    "inclure le plan de travail, les mesures de protection et le calendrier."
                ),
                legal_references=[
                    _LEGAL_REFS["otconst_82_86"],
                    _LEGAL_REFS["cfst_6503"],
                ],
                applicability="Presence d'amiante confirmee par diagnostic",
                pollutants=["asbestos"],
            ),
            EcoClause(
                clause_id="AMI-02",
                title="Mesures de protection des travailleurs",
                body=(
                    "Les travaux en presence d'amiante doivent etre realises conformement "
                    "a la directive CFST 6503. Selon la categorie de travaux (mineur, moyen, "
                    "majeur), les mesures de protection incluent: confinement, ventilation "
                    "en depression, equipements de protection individuelle, et decontamination."
                ),
                legal_references=[_LEGAL_REFS["cfst_6503"]],
                applicability="Presence d'amiante confirmee par diagnostic",
                pollutants=["asbestos"],
            ),
            EcoClause(
                clause_id="AMI-03",
                title="Elimination des dechets amiantiferes",
                body=(
                    "Les dechets contenant de l'amiante doivent etre conditionnes dans "
                    "des emballages hermetiques etiquetes et elimines en tant que dechets "
                    "speciaux via une filiere agreee. Un bordereau de suivi des dechets "
                    "doit etre conserve."
                ),
                legal_references=[
                    _LEGAL_REFS["oled_waste"],
                    _LEGAL_REFS["otconst_82_86"],
                ],
                applicability="Presence d'amiante confirmee par diagnostic",
                pollutants=["asbestos"],
            ),
        ]
        sections.append(
            EcoClauseSection(
                section_id="SEC-AMI",
                title="Clauses amiante",
                clauses=asbestos_clauses,
            )
        )

    # --- PCB section ---
    if "pcb" in detected:
        pcb_clauses: list[EcoClause] = [
            EcoClause(
                clause_id="PCB-01",
                title="Gestion des materiaux contenant des PCB",
                body=(
                    "Les materiaux contenant des PCB a une concentration superieure a "
                    "50 mg/kg doivent etre retires par une entreprise specialisee et "
                    "elimines en tant que dechets speciaux. Aucun broyage ou decoupe "
                    "thermique n'est autorise sur ces materiaux."
                ),
                legal_references=[
                    _LEGAL_REFS["orrchim_2_15"],
                    _LEGAL_REFS["oled_waste"],
                ],
                applicability="Presence de PCB confirmee (> 50 mg/kg)",
                pollutants=["pcb"],
            ),
        ]
        sections.append(
            EcoClauseSection(
                section_id="SEC-PCB",
                title="Clauses PCB",
                clauses=pcb_clauses,
            )
        )

    # --- Lead section ---
    if "lead" in detected:
        lead_clauses: list[EcoClause] = [
            EcoClause(
                clause_id="PB-01",
                title="Gestion des peintures au plomb",
                body=(
                    "Les peintures et revetements contenant du plomb a une concentration "
                    "superieure a 5000 mg/kg doivent etre retires avec precaution. Les "
                    "techniques generant des poussieres (poncage a sec, decapage thermique) "
                    "sont interdites sans confinement et aspiration adaptee."
                ),
                legal_references=[
                    _LEGAL_REFS["orrchim_2_18"],
                    _LEGAL_REFS["oled_waste"],
                ],
                applicability="Presence de plomb confirmee (> 5000 mg/kg)",
                pollutants=["lead"],
            ),
        ]
        sections.append(
            EcoClauseSection(
                section_id="SEC-PB",
                title="Clauses plomb",
                clauses=lead_clauses,
            )
        )

    # --- HAP section ---
    if "hap" in detected:
        hap_clauses: list[EcoClause] = [
            EcoClause(
                clause_id="HAP-01",
                title="Gestion des materiaux contenant des HAP",
                body=(
                    "Les materiaux contenant des hydrocarbures aromatiques polycycliques "
                    "(HAP) doivent etre retires et elimines en tant que dechets speciaux. "
                    "Les travaux doivent minimiser la liberation de poussieres et vapeurs."
                ),
                legal_references=[_LEGAL_REFS["oled_waste"]],
                applicability="Presence de HAP confirmee par diagnostic",
                pollutants=["hap"],
            ),
        ]
        sections.append(
            EcoClauseSection(
                section_id="SEC-HAP",
                title="Clauses HAP",
                clauses=hap_clauses,
            )
        )

    # --- Radon section ---
    if "radon" in detected:
        radon_clauses: list[EcoClause] = [
            EcoClause(
                clause_id="RN-01",
                title="Mesures de protection contre le radon",
                body=(
                    "Si la concentration de radon depasse 300 Bq/m3, des mesures "
                    "d'assainissement doivent etre prevues dans le cadre des travaux "
                    "(ventilation, etancheite du radier). Au-dela de 1000 Bq/m3, "
                    "l'assainissement est obligatoire dans un delai de 3 ans."
                ),
                legal_references=[_LEGAL_REFS["orap_110"]],
                applicability="Concentration radon > 300 Bq/m3",
                pollutants=["radon"],
            ),
        ]
        sections.append(
            EcoClauseSection(
                section_id="SEC-RN",
                title="Clauses radon",
                clauses=radon_clauses,
            )
        )

    return sections


def _renovation_clauses(detected: set[str]) -> list[EcoClauseSection]:
    """Additional clauses specific to renovation context."""
    clauses: list[EcoClause] = [
        EcoClause(
            clause_id="REN-01",
            title="Preservation des zones non concernees",
            body=(
                "Les zones du batiment non concernees par les travaux de renovation "
                "doivent etre protegees contre toute contamination croisee. Des sas de "
                "decontamination et des barrieres physiques doivent etre installes "
                "conformement a la categorie de travaux applicable."
            ),
            legal_references=[_LEGAL_REFS["cfst_6503"]],
            applicability="Renovation partielle en presence de polluants",
            pollutants=[],
        ),
    ]

    if "asbestos" in detected:
        clauses.append(
            EcoClause(
                clause_id="REN-02",
                title="Mesure de liberation de fibres post-renovation",
                body=(
                    "Apres l'achevement des travaux de renovation impliquant de l'amiante, "
                    "une mesure de liberation de fibres doit etre realisee par un laboratoire "
                    "accredite. La restitution des locaux n'est autorisee qu'apres obtention "
                    "d'un resultat conforme (< 1000 fibres/m3 VLE)."
                ),
                legal_references=[
                    _LEGAL_REFS["otconst_82_86"],
                    _LEGAL_REFS["cfst_6503"],
                ],
                applicability="Renovation en presence d'amiante",
                pollutants=["asbestos"],
            )
        )

    return [
        EcoClauseSection(
            section_id="SEC-REN",
            title="Clauses specifiques renovation",
            clauses=clauses,
        )
    ]


def _demolition_clauses(detected: set[str]) -> list[EcoClauseSection]:
    """Additional clauses specific to demolition context."""
    clauses: list[EcoClause] = [
        EcoClause(
            clause_id="DEM-01",
            title="Decontamination prealable a la demolition",
            body=(
                "Avant la demolition, tous les materiaux contenant des polluants identifies "
                "doivent etre retires selectivement (desamiantage, retrait PCB, plomb, HAP). "
                "La demolition ne peut debuter qu'apres validation du retrait complet."
            ),
            legal_references=[
                _LEGAL_REFS["otconst_82_86"],
                _LEGAL_REFS["oled_waste"],
            ],
            applicability="Demolition en presence de polluants identifies",
            pollutants=[],
        ),
        EcoClause(
            clause_id="DEM-02",
            title="Tri et elimination des dechets de demolition",
            body=(
                "Les dechets de demolition doivent etre tries sur site selon leur nature "
                "(inertes, non pollues, pollues, speciaux). Chaque categorie doit suivre "
                "la filiere d'elimination appropriee conformement a l'OLED. Un bordereau "
                "de suivi est obligatoire pour les dechets speciaux."
            ),
            legal_references=[_LEGAL_REFS["oled_waste"]],
            applicability="Toute demolition",
            pollutants=[],
        ),
    ]

    if "asbestos" in detected:
        clauses.append(
            EcoClause(
                clause_id="DEM-03",
                title="Desamiantage integral avant demolition",
                body=(
                    "L'ensemble des materiaux contenant de l'amiante doit etre retire "
                    "avant le debut des operations de demolition mecanique. Un controle "
                    "visuel et une mesure d'empoussierement doivent confirmer l'absence "
                    "d'amiante residuel."
                ),
                legal_references=[
                    _LEGAL_REFS["otconst_82_86"],
                    _LEGAL_REFS["cfst_6503"],
                ],
                applicability="Demolition en presence d'amiante",
                pollutants=["asbestos"],
            )
        )

    return [
        EcoClauseSection(
            section_id="SEC-DEM",
            title="Clauses specifiques demolition",
            clauses=clauses,
        )
    ]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


async def _detect_pollutants(db: AsyncSession, building_id: uuid.UUID) -> set[str]:
    """Return the set of pollutant types with threshold-exceeding samples."""
    result = await db.execute(
        select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.building_id == building_id)
    )
    diagnostics = result.scalars().all()

    detected: set[str] = set()
    for diag in diagnostics:
        for sample in diag.samples:
            if sample.threshold_exceeded and sample.pollutant_type and sample.pollutant_type in ALL_POLLUTANTS:
                detected.add(sample.pollutant_type)
    return detected


async def _has_building(db: AsyncSession, building_id: uuid.UUID) -> bool:
    result = await db.execute(select(Building.id).where(Building.id == building_id))
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_VALID_CONTEXTS: set[EcoClauseContext] = {"renovation", "demolition"}


async def generate_eco_clauses(
    building_id: uuid.UUID,
    context: str,
    db: AsyncSession,
) -> EcoClausePayload:
    """Generate eco clause templates for a building and context.

    Args:
        building_id: UUID of the target building.
        context: ``"renovation"`` or ``"demolition"``.
        db: Async database session.

    Returns:
        Deterministic ``EcoClausePayload`` with clause sections.

    Raises:
        ValueError: If building not found or context invalid.
    """
    if context not in _VALID_CONTEXTS:
        valid = ", ".join(sorted(_VALID_CONTEXTS))
        raise ValueError(f"Invalid context '{context}'. Valid contexts: {valid}")

    if not await _has_building(db, building_id):
        raise ValueError("Building not found")

    detected = await _detect_pollutants(db, building_id)

    # Build deterministic clause list
    sections = _common_clauses(detected)
    if context == "renovation":
        sections.extend(_renovation_clauses(detected))
    elif context == "demolition":
        sections.extend(_demolition_clauses(detected))

    total = sum(len(s.clauses) for s in sections)

    # Sorted detected pollutants for deterministic output
    sorted_detected = sorted(detected, key=lambda p: ALL_POLLUTANTS.index(p))

    # Build provenance trail
    provenance: list[str] = [
        f"building_id={building_id}",
        f"context={context}",
        f"detected_pollutants={sorted_detected}",
    ]
    for _ref_key, ref_label in sorted(_LEGAL_REFS.items()):
        # Include only refs actually used
        for section in sections:
            for clause in section.clauses:
                if ref_label in clause.legal_references:
                    provenance.append(f"ref={ref_label}")
                    break
            else:
                continue
            break

    generated_at = datetime.now(UTC)

    return EcoClausePayload(
        building_id=building_id,
        context=context,  # type: ignore[arg-type]
        generated_at=generated_at,
        sections=sections,
        total_clauses=total,
        detected_pollutants=sorted_detected,
        provenance=provenance,
    )
