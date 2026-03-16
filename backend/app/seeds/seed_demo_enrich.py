"""
SwissBuildingOS - Demo Enrichment

Attaches realistic diagnostics, samples, documents, and events to
existing buildings in the database. Designed to run after seed_data
and the Vaud public import, to make the app rich enough for full
UI/UX testing.

This module is idempotent: it checks for existing enrichment data
before creating new records.

Usage (called by seed_demo.py, not standalone):
    from app.seeds.seed_demo_enrich import enrich_demo_buildings
    await enrich_demo_buildings()
"""

from __future__ import annotations

import random
import uuid
from datetime import date, timedelta

from sqlalchemy import select

from app.constants import SOURCE_DATASET_VAUD_PUBLIC, normalize_sample_unit
from app.database import AsyncSessionLocal
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.event import Event
from app.models.sample import Sample
from app.models.user import User

# Reproducible randomness for consistent demo data
_RNG = random.Random(42)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENRICHMENT_MARKER = "demo-enrichment-v1"

DIAGNOSTIC_SCENARIOS = [
    # (diagnostic_type, context, status, conclusion, has_suva, summary_template)
    (
        "full",
        "AvT",
        "completed",
        "positive",
        True,
        "Diagnostic complet avant travaux. Amiante et PCB détectés dans les matériaux de construction d'époque.",
    ),
    (
        "asbestos",
        "AvT",
        "completed",
        "positive",
        True,
        "Diagnostic amiante avant rénovation. Chrysotile confirmé dans les revêtements de sol et faux-plafonds.",
    ),
    (
        "asbestos",
        "AvT",
        "validated",
        "positive",
        True,
        "Diagnostic amiante validé par l'autorité cantonale. Assainissement planifié.",
    ),
    (
        "pcb",
        "AvT",
        "completed",
        "positive",
        False,
        "Diagnostic PCB avant transformation. Joints de façade contaminés.",
    ),
    (
        "asbestos",
        "UN",
        "in_progress",
        None,
        False,
        "Diagnostic amiante en cours - utilisation normale. Prélèvements effectués, analyses en laboratoire.",
    ),
    (
        "lead",
        "AvT",
        "draft",
        None,
        False,
        "Diagnostic plomb planifié. En attente de la date d'intervention.",
    ),
    (
        "hap",
        "AvT",
        "completed",
        "positive",
        False,
        "Diagnostic HAP. Goudron détecté sous parquet ancien.",
    ),
    (
        "radon",
        "UN",
        "completed",
        "negative",
        False,
        "Mesure radon sur 3 mois. Concentration inférieure à la valeur de référence de 300 Bq/m³.",
    ),
    (
        "full",
        "AvT",
        "completed",
        "negative",
        False,
        "Diagnostic complet avant travaux. Aucun polluant détecté au-dessus des seuils réglementaires.",
    ),
    (
        "asbestos",
        "AvT",
        "in_progress",
        None,
        False,
        "Diagnostic amiante en cours. Flocage suspect identifié dans le sous-sol.",
    ),
]

SAMPLE_TEMPLATES = {
    "asbestos": [
        {
            "floor": "2ème étage",
            "room": "Salon",
            "detail": "Dalles vinyle collées",
            "mat_cat": "floor_covering_vinyl",
            "mat_desc": "Dalles vinyle-amiante 30×30",  # noqa: RUF001
            "subtype": "chrysotile",
            "conc": 12.0,
            "unit": "percent_weight",
            "exceeded": True,
            "risk": "high",
            "cfst": "medium",
            "action": "containment_before_removal",
            "waste": "special",
        },
        {
            "floor": "Sous-sol",
            "room": "Local technique",
            "detail": "Flocage poutre métallique",
            "mat_cat": "flocage",
            "mat_desc": "Flocage fibreux gris-blanc ~3cm",
            "subtype": "chrysotile/amosite",
            "conc": 45.0,
            "unit": "percent_weight",
            "exceeded": True,
            "risk": "critical",
            "cfst": "high",
            "action": "immediate_containment",
            "waste": "special",
        },
        {
            "floor": "Façade",
            "room": "Façade sud",
            "detail": "Plaques fibro-ciment",
            "mat_cat": "facade_panel",
            "mat_desc": "Plaques ondulées fibro-ciment gris",
            "subtype": "chrysotile",
            "conc": 10.0,
            "unit": "percent_weight",
            "exceeded": True,
            "risk": "medium",
            "cfst": "medium",
            "action": "removal_before_works",
            "waste": "special",
        },
        {
            "floor": "RdC",
            "room": "Hall d'entrée",
            "detail": "Colle sous carrelage",
            "mat_cat": "adhesive",
            "mat_desc": "Colle noire bitumineuse",
            "subtype": "chrysotile",
            "conc": 3.5,
            "unit": "percent_weight",
            "exceeded": True,
            "risk": "medium",
            "cfst": "medium",
            "action": "removal_before_works",
            "waste": "special",
        },
    ],
    "pcb": [
        {
            "floor": "3ème étage",
            "room": "Bureau",
            "detail": "Joint de fenêtre",
            "mat_cat": "sealant",
            "mat_desc": "Mastic gris souple entre cadre et maçonnerie",
            "subtype": "Aroclor 1260",
            "conc": 380.0,
            "unit": "mg_per_kg",
            "exceeded": True,
            "risk": "high",
            "cfst": "medium",
            "action": "decontamination",
            "waste": "special",
        },
        {
            "floor": "Sous-sol",
            "room": "Local électrique",
            "detail": "Condensateur fluorescent",
            "mat_cat": "electrical",
            "mat_desc": "Condensateur dans ballast éclairage",
            "subtype": "Aroclor 1254",
            "conc": 8500.0,
            "unit": "mg_per_kg",
            "exceeded": True,
            "risk": "high",
            "cfst": "medium",
            "action": "decontamination",
            "waste": "special",
        },
    ],
    "lead": [
        {
            "floor": "4ème étage",
            "room": "Chambre",
            "detail": "Peinture boiseries fenêtre",
            "mat_cat": "lead_paint",
            "mat_desc": "Peinture blanche multicouche sur bois",
            "subtype": None,
            "conc": 4200.0,
            "unit": "mg_per_kg",
            "exceeded": False,
            "risk": "low",
            "cfst": None,
            "action": "monitoring",
            "waste": "controlled",
        },
        {
            "floor": "1er étage",
            "room": "Cuisine",
            "detail": "Peinture sur radiateur",
            "mat_cat": "lead_paint",
            "mat_desc": "Peinture écaillée grise sur radiateur fonte",
            "subtype": None,
            "conc": 12000.0,
            "unit": "mg_per_kg",
            "exceeded": True,
            "risk": "high",
            "cfst": "medium",
            "action": "controlled_removal",
            "waste": "special",
        },
    ],
    "hap": [
        {
            "floor": "1er étage",
            "room": "Grande salle",
            "detail": "Sous-couche sous parquet",
            "mat_cat": "tar_products",
            "mat_desc": "Colle bitumineuse noire sous lattes",
            "subtype": "B[a]P",
            "conc": 850.0,
            "unit": "mg_per_kg",
            "exceeded": True,
            "risk": "high",
            "cfst": "medium",
            "action": "controlled_removal",
            "waste": "special",
        },
    ],
    "radon": [
        {
            "floor": "RdC",
            "room": "Séjour",
            "detail": "Dosimètre 3 mois",
            "mat_cat": "indoor_air",
            "mat_desc": "Dosimètre radon passif - période hivernale",
            "subtype": None,
            "conc": 180.0,
            "unit": "bq_per_m3",
            "exceeded": False,
            "risk": "low",
            "cfst": None,
            "action": "monitoring",
            "waste": None,
        },
    ],
    "full": [
        {
            "floor": "2ème étage",
            "room": "Salon",
            "detail": "Dalles vinyle collées",
            "mat_cat": "floor_covering_vinyl",
            "mat_desc": "Dalles vinyle-amiante 30×30",  # noqa: RUF001
            "subtype": "chrysotile",
            "conc": 15.0,
            "unit": "percent_weight",
            "exceeded": True,
            "risk": "high",
            "cfst": "medium",
            "action": "containment_before_removal",
            "waste": "special",
        },
        {
            "floor": "Façade",
            "room": "Façade sud",
            "detail": "Joint d'étanchéité",
            "mat_cat": "facade_joint_sealant",
            "mat_desc": "Mastic gris-noir souple",
            "subtype": "Aroclor 1260",
            "conc": 1250.0,
            "unit": "mg_per_kg",
            "exceeded": True,
            "risk": "high",
            "cfst": "medium",
            "action": "decontamination",
            "waste": "special",
        },
    ],
}

DOCUMENT_TEMPLATES = [
    (
        "diagnostic_report",
        "Rapport_diagnostic_{city}_{type}.pdf",
        "application/pdf",
        "Rapport de diagnostic {type} — {address}",
        (1_500_000, 4_000_000),
    ),
    (
        "notification",
        "Notification_SUVA_{date}.pdf",
        "application/pdf",
        "Notification SUVA pour travaux d'assainissement",
        (120_000, 300_000),
    ),
    (
        "photo",
        "Photos_inspection_{city}.zip",
        "application/zip",
        "Photos d'inspection terrain",
        (8_000_000, 25_000_000),
    ),
    ("plan", "Plan_zones_{city}.pdf", "application/pdf", "Plan des zones de prélèvement", (2_000_000, 6_000_000)),
    (
        "lab_analysis",
        "Analyses_labo_{city}_{type}.pdf",
        "application/pdf",
        "Résultats d'analyses laboratoire",
        (800_000, 2_500_000),
    ),
]

LABS = [
    "Laboratoire EMPA Suisse",
    "SGS Schweiz AG",
    "LabAnalytica SA",
    "Asbestos Analytics Zürich",
    "Envilab AG",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=_RNG.randint(0, max(delta, 1)))


def _random_renovation_year(construction_year: int | None) -> int | None:
    if construction_year is None:
        return None
    start_year = max(construction_year + 15, 1970)
    end_year = 2020
    if start_year > end_year:
        return None
    return _RNG.randint(start_year, end_year)


def _make_samples(
    diagnostic_id: uuid.UUID,
    diag_type: str,
    conclusion: str | None,
    city_prefix: str,
) -> list[Sample]:
    templates = SAMPLE_TEMPLATES.get(diag_type, SAMPLE_TEMPLATES["asbestos"])
    if conclusion == "negative":
        # All samples below threshold for negative conclusion
        templates = [
            dict(t, exceeded=False, risk="low", conc=0.0, cfst=None, action="monitoring", waste=None)
            for t in templates[:2]
        ]
    # Pick 1-3 samples randomly
    count = _RNG.randint(1, min(3, len(templates)))
    selected = _RNG.sample(templates, count)
    samples = []
    for i, t in enumerate(selected, 1):
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diagnostic_id,
            sample_number=f"{city_prefix}-DEMO-{i:03d}",
            location_floor=t["floor"],
            location_room=t["room"],
            location_detail=t["detail"],
            material_category=t["mat_cat"],
            material_description=t["mat_desc"],
            material_state=_RNG.choice(["intact", "degraded", "friable"]) if t["exceeded"] else "intact",
            pollutant_type=diag_type if diag_type != "full" else _RNG.choice(["asbestos", "pcb"]),
            pollutant_subtype=t["subtype"],
            concentration=t["conc"],
            unit=normalize_sample_unit(t["unit"], strict=True),
            threshold_exceeded=t["exceeded"],
            risk_level=t["risk"],
            cfst_work_category=t["cfst"],
            action_required=t["action"],
            waste_disposal_type=t["waste"],
        )
        samples.append(s)
    return samples


# ---------------------------------------------------------------------------
# Main enrichment function
# ---------------------------------------------------------------------------


async def enrich_demo_buildings() -> dict[str, int]:
    """
    Attach diagnostics, samples, documents, and events to a subset of
    existing buildings that don't yet have diagnostics.

    Returns a stats dict with counts of created entities.
    """
    async with AsyncSessionLocal() as db:
        # Check if enrichment already ran
        existing = await db.execute(select(Event).where(Event.title.contains(_ENRICHMENT_MARKER)))
        if existing.scalar_one_or_none():
            print("[ENRICH] Demo enrichment already applied — skipping.")
            return {"diagnostics": 0, "samples": 0, "documents": 0, "events": 0}

        # Get diagnostician and admin users
        diag_result = await db.execute(select(User).where(User.email == "jean.muller@diagswiss.ch"))
        diagnostician = diag_result.scalar_one_or_none()
        admin_result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
        admin = admin_result.scalar_one_or_none()

        if not diagnostician or not admin:
            print("[ENRICH] Required users not found. Run seed_data first.")
            return {"diagnostics": 0, "samples": 0, "documents": 0, "events": 0}

        # Get buildings without diagnostics (candidates for enrichment)
        # Prioritize Vaud-imported buildings, then synthetics
        subq = select(Diagnostic.building_id).distinct().subquery()
        candidates_result = await db.execute(
            select(Building)
            .where(Building.status == "active")
            .where(Building.id.notin_(select(subq)))
            .order_by(
                (Building.source_dataset == SOURCE_DATASET_VAUD_PUBLIC).desc(),
                Building.created_at,
            )
        )
        candidates = list(candidates_result.scalars().all())

        if not candidates:
            print("[ENRICH] No unenriched buildings found.")
            return {"diagnostics": 0, "samples": 0, "documents": 0, "events": 0}

        # Target: enrich up to 25 buildings with varied scenarios
        target_count = min(25, len(candidates))
        selected = candidates[:target_count]

        stats = {"diagnostics": 0, "samples": 0, "documents": 0, "events": 0}

        for i, building in enumerate(selected):
            scenario = DIAGNOSTIC_SCENARIOS[i % len(DIAGNOSTIC_SCENARIOS)]
            diag_type, context, status, conclusion, has_suva, summary_tpl = scenario

            # Skip if building is too new for the pollutant type
            year = building.construction_year
            if year and year > 1995 and diag_type in ("asbestos", "pcb", "hap"):
                # Make it a negative result instead
                conclusion = "negative"
                summary_tpl = f"Diagnostic {diag_type} — bâtiment post-1995. Aucune substance dangereuse détectée."

            inspection_date = _random_date(date(2024, 6, 1), date(2026, 2, 28))
            report_date = (
                inspection_date + timedelta(days=_RNG.randint(10, 30)) if status in ("completed", "validated") else None
            )
            lab = _RNG.choice(LABS) if status in ("completed", "validated") else None
            lab_number = (
                f"{lab.split()[0][:3].upper()}-{inspection_date.year}-{_RNG.randint(1000, 9999):04d}" if lab else None
            )

            diag = Diagnostic(
                id=uuid.uuid4(),
                building_id=building.id,
                diagnostic_type=diag_type,
                diagnostic_context=context,
                status=status,
                diagnostician_id=diagnostician.id,
                laboratory=lab,
                laboratory_report_number=lab_number,
                date_inspection=inspection_date,
                date_report=report_date,
                summary=summary_tpl,
                conclusion=conclusion,
                methodology="VDI 3866 / SIA 118/430" if diag_type != "radon" else "Dosimétrie passive",
                suva_notification_required=has_suva,
                suva_notification_date=(report_date + timedelta(days=3) if has_suva and report_date else None),
            )
            db.add(diag)
            await db.flush()
            stats["diagnostics"] += 1

            # Samples (only for in_progress, completed, validated)
            if status in ("in_progress", "completed", "validated"):
                city_prefix = (building.city or "XX")[:3].upper()
                samples = _make_samples(diag.id, diag_type, conclusion, city_prefix)
                db.add_all(samples)
                stats["samples"] += len(samples)

            # Documents (for completed and validated diagnostics)
            if status in ("completed", "validated"):
                doc_count = _RNG.randint(1, 3)
                doc_templates = _RNG.sample(DOCUMENT_TEMPLATES, min(doc_count, len(DOCUMENT_TEMPLATES)))
                for dt_type, dt_name, dt_mime, dt_desc, (size_min, size_max) in doc_templates:
                    fname = dt_name.format(
                        city=building.city or "Unknown",
                        type=diag_type,
                        date=inspection_date.strftime("%Y%m%d"),
                    )
                    doc = Document(
                        id=uuid.uuid4(),
                        building_id=building.id,
                        file_path=f"/documents/demo/{fname}",
                        file_name=fname,
                        file_size_bytes=_RNG.randint(size_min, size_max),
                        mime_type=dt_mime,
                        document_type=dt_type,
                        description=dt_desc.format(
                            type=diag_type,
                            address=building.address or "",
                        ),
                        uploaded_by=diagnostician.id,
                    )
                    db.add(doc)
                    stats["documents"] += 1

            # Events
            evt_type = {
                "draft": "diagnostic_planned",
                "in_progress": "diagnostic_started",
                "completed": "diagnostic_completed",
                "validated": "diagnostic_validated",
            }.get(status, "diagnostic_planned")

            evt = Event(
                id=uuid.uuid4(),
                building_id=building.id,
                event_type=evt_type,
                date=report_date or inspection_date,
                title=f"Diagnostic {diag_type} — {building.city}",
                description=summary_tpl,
                created_by=diagnostician.id,
                metadata_json={
                    "diagnostic_id": str(diag.id),
                    "diagnostic_type": diag_type,
                    "status": status,
                    "conclusion": conclusion,
                },
            )
            db.add(evt)
            stats["events"] += 1

            # Renovation event for some buildings
            if _RNG.random() < 0.3:
                reno_year = _random_renovation_year(building.construction_year)
                if reno_year is None:
                    continue
                reno_evt = Event(
                    id=uuid.uuid4(),
                    building_id=building.id,
                    event_type="renovation",
                    date=date(reno_year, _RNG.randint(1, 12), 1),
                    title=f"Rénovation — {building.city}",
                    description=f"Travaux de rénovation réalisés en {reno_year}.",
                    created_by=admin.id,
                    metadata_json={"renovation_year": reno_year},
                )
                db.add(reno_evt)
                stats["events"] += 1

        # Marker event to prevent re-enrichment
        marker = Event(
            id=uuid.uuid4(),
            building_id=selected[0].id,
            event_type="system",
            date=date.today(),
            title=f"[{_ENRICHMENT_MARKER}] Demo data enrichment applied",
            description=f"Enriched {stats['diagnostics']} buildings with demo data.",
            created_by=admin.id,
        )
        db.add(marker)

        await db.commit()

    return stats
