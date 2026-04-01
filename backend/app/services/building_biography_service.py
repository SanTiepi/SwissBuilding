"""
BatiConnect - Building Biography Service

Generates a comprehensive building biography: the complete life story
of a building compiled from transformations, ownership, diagnostics,
interventions, and component ages.

LLM-free narrative generation — deterministic text from structured data.
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_genealogy import OwnershipEpisode, TransformationEpisode
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.component_age_tracker import compute_component_ages

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Narrative helpers
# ---------------------------------------------------------------------------

_TYPE_LABELS_FR = {
    "construction": "Construit",
    "renovation": "Rénovation",
    "extension": "Extension",
    "demolition_partial": "Démolition partielle",
    "change_of_use": "Changement d'affectation",
    "merger": "Fusion",
    "split": "Division",
    "restoration": "Restauration",
    "modernization": "Modernisation",
    "remediation": "Assainissement",
    "other": "Autre intervention",
}

_BUILDING_TYPE_FR = {
    "residential": "résidentiel",
    "commercial": "commercial",
    "industrial": "industriel",
    "mixed": "mixte",
    "public": "public",
    "agricultural": "agricole",
}


def _year_from_date(d: date | None) -> int | None:
    """Extract year from a date, returning None if date is None."""
    return d.year if d else None


def _generate_narrative(
    building: Building,
    chapters: list[dict],
    ownership_chain: list[dict],
    component_ages: dict,
) -> str:
    """Generate a deterministic narrative from structured biography data."""
    parts: list[str] = []

    # Opening
    btype = _BUILDING_TYPE_FR.get(building.building_type, building.building_type)
    if building.construction_year:
        parts.append(f"Construit en {building.construction_year} en tant que bâtiment {btype}")
    else:
        parts.append(f"Bâtiment {btype} dont l'année de construction est inconnue")

    if building.floors_above:
        parts[-1] += f" de {building.floors_above} étages"
    parts[-1] += f", situé au {building.address}, {building.postal_code} {building.city}."

    # Ownership summary
    if ownership_chain:
        count = len(ownership_chain)
        parts.append(f"Le bâtiment a connu {count} propriétaire{'s' if count > 1 else ''}.")

    # Key transformations
    transformations = [c for c in chapters if c["type"] in ("renovation", "extension", "modernization", "restoration")]
    if transformations:
        parts.append(
            f"Il a fait l'objet de {len(transformations)} transformation{'s' if len(transformations) > 1 else ''} majeure{'s' if len(transformations) > 1 else ''}."
        )

    # Diagnostics
    diagnostics = [c for c in chapters if c["type"] == "diagnostic"]
    if diagnostics:
        parts.append(
            f"{len(diagnostics)} diagnostic{'s' if len(diagnostics) > 1 else ''} réalisé{'s' if len(diagnostics) > 1 else ''}."
        )

    # Remediations
    remediations = [c for c in chapters if c["type"] == "remediation"]
    if remediations:
        parts.append(
            f"{len(remediations)} assainissement{'s' if len(remediations) > 1 else ''} effectué{'s' if len(remediations) > 1 else ''}."
        )

    # Component age insight
    original_components = [k for k, v in component_ages.items() if v.get("is_original")]
    if original_components and building.construction_year:
        today_year = date.today().year
        age = today_year - building.construction_year
        parts.append(
            f"{len(original_components)} composant{'s' if len(original_components) > 1 else ''} "
            f"d'origine ({age} ans): {', '.join(original_components)}."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_biography(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Compile the complete life story of a building.

    Returns a structured biography with identity, chapters, ownership chain,
    component ages, event counts, and a deterministic narrative.
    """
    # ── Load building ───────────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")

    # ── Identity ────────────────────────────────────────────────
    identity = {
        "egid": building.egid,
        "address": building.address,
        "postal_code": building.postal_code,
        "city": building.city,
        "canton": building.canton,
        "construction_year": building.construction_year,
        "building_type": building.building_type,
        "floors_above": building.floors_above,
        "floors_below": building.floors_below,
    }

    # ── Chapters (chronological events) ─────────────────────────
    chapters: list[dict] = []

    # Construction chapter
    if building.construction_year:
        btype = _BUILDING_TYPE_FR.get(building.building_type, building.building_type)
        chapters.append(
            {
                "year": building.construction_year,
                "type": "construction",
                "description": f"Construction du bâtiment {btype}",
            }
        )

    # Transformation episodes
    t_result = await db.execute(
        select(TransformationEpisode)
        .where(TransformationEpisode.building_id == building_id)
        .order_by(TransformationEpisode.period_start.asc().nullslast())
    )
    for t in t_result.scalars().all():
        year = _year_from_date(t.period_start)
        label = _TYPE_LABELS_FR.get(t.episode_type, t.episode_type)
        chapters.append(
            {
                "year": year,
                "type": t.episode_type,
                "description": t.description or f"{label}: {t.title}",
            }
        )

    # Diagnostics
    d_result = await db.execute(
        select(Diagnostic)
        .where(Diagnostic.building_id == building_id)
        .order_by(Diagnostic.date_inspection.asc().nullslast())
    )
    diagnostics_list = list(d_result.scalars().all())
    for d in diagnostics_list:
        year = _year_from_date(d.date_inspection)
        # Fetch positive samples for this diagnostic
        s_result = await db.execute(
            select(Sample).where(Sample.diagnostic_id == d.id, Sample.threshold_exceeded.is_(True))
        )
        positive_samples = list(s_result.scalars().all())
        if positive_samples:
            materials = list(
                {s.material_category or s.material_description or "matériau inconnu" for s in positive_samples}
            )
            desc = f"Diagnostic {d.diagnostic_type}: positif dans {', '.join(materials[:3])}"
        else:
            desc = f"Diagnostic {d.diagnostic_type}: {d.conclusion or d.status}"
        chapters.append(
            {
                "year": year,
                "type": "diagnostic",
                "description": desc,
            }
        )

    # Interventions
    i_result = await db.execute(
        select(Intervention)
        .where(Intervention.building_id == building_id)
        .order_by(Intervention.date_start.asc().nullslast())
    )
    interventions_list = list(i_result.scalars().all())
    for i in interventions_list:
        year = _year_from_date(i.date_start)
        chapters.append(
            {
                "year": year,
                "type": "remediation"
                if "remedia" in (i.intervention_type or "").lower() or "assaini" in (i.intervention_type or "").lower()
                else "intervention",
                "description": i.description or i.title,
            }
        )

    # Sort chapters chronologically (None years at end)
    chapters.sort(key=lambda c: c["year"] if c["year"] is not None else 9999)

    # ── Ownership chain ─────────────────────────────────────────
    o_result = await db.execute(
        select(OwnershipEpisode)
        .where(OwnershipEpisode.building_id == building_id)
        .order_by(OwnershipEpisode.period_start.asc().nullslast())
    )
    ownership_chain = []
    for o in o_result.scalars().all():
        ownership_chain.append(
            {
                "owner": o.owner_name or "Inconnu",
                "from_date": o.period_start.isoformat() if o.period_start else None,
                "to_date": o.period_end.isoformat() if o.period_end else None,
                "type": o.owner_type,
                "acquisition_type": o.acquisition_type,
            }
        )

    # ── Component ages ──────────────────────────────────────────
    component_ages = await compute_component_ages(db, building_id)

    # ── Key events count ────────────────────────────────────────
    transformation_count = (
        await db.scalar(
            select(func.count())
            .select_from(TransformationEpisode)
            .where(TransformationEpisode.building_id == building_id)
        )
        or 0
    )
    diagnostic_count = len(diagnostics_list)
    intervention_count = len(interventions_list)
    incident_count = 0  # Future: count from IncidentEpisode when available

    key_events_count = {
        "transformations": transformation_count,
        "diagnostics": diagnostic_count,
        "interventions": intervention_count,
        "incidents": incident_count,
    }

    # ── Narrative ───────────────────────────────────────────────
    narrative = _generate_narrative(building, chapters, ownership_chain, component_ages)

    return {
        "building_id": str(building_id),
        "identity": identity,
        "chapters": chapters,
        "ownership_chain": ownership_chain,
        "component_ages": component_ages,
        "key_events_count": key_events_count,
        "narrative": narrative,
    }
