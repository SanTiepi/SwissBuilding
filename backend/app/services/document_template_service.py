"""Document template generation service.

Generates pre-filled authority forms and document templates from building data.
Leverages existing dossier/compliance infrastructure to produce ready-to-submit documents.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.document_template import (
    GeneratedTemplate,
    TemplateField,
    TemplateInfo,
    TemplateSection,
)

# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

_TEMPLATE_DEFS: dict[str, dict] = {
    "suva_notification": {
        "title": "Notification SUVA amiante",
        "description": "Formulaire de notification SUVA pour presence d'amiante confirmee",
        "required_data": ["asbestos positive samples"],
        "legal_basis": "OTConst Art. 60a, CFST 6503",
    },
    "cantonal_notification": {
        "title": "Notification autorite cantonale",
        "description": "Formulaire de notification a l'autorite cantonale competente",
        "required_data": ["any positive samples"],
        "legal_basis": "Legislation cantonale (VD/GE)",
    },
    "waste_elimination_plan": {
        "title": "Plan d'elimination des dechets",
        "description": "Plan d'elimination des dechets selon classification OLED",
        "required_data": ["classified waste types"],
        "legal_basis": "OLED",
    },
    "work_authorization_request": {
        "title": "Demande d'autorisation de travaux",
        "description": "Formulaire de demande d'autorisation de travaux de desamiantage",
        "required_data": ["diagnostic completed"],
        "legal_basis": "OTConst Art. 82-86",
    },
    "air_clearance_request": {
        "title": "Demande de mesure de liberation",
        "description": "Demande de mesure de liberation de l'air apres intervention amiante",
        "required_data": ["asbestos intervention completed"],
        "legal_basis": "CFST 6503",
    },
    "building_summary": {
        "title": "Fiche de synthese batiment",
        "description": "Fiche recapitulative des donnees du batiment",
        "required_data": [],
        "legal_basis": None,
    },
    "diagnostic_summary": {
        "title": "Synthese des diagnostics",
        "description": "Resume des resultats de diagnostics et analyses",
        "required_data": ["at least one diagnostic"],
        "legal_basis": None,
    },
}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


async def _fetch_building_with_relations(db: AsyncSession, building_id: UUID) -> dict | None:
    """Fetch building with diagnostics, samples, and interventions."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None

    diag_result = await db.execute(
        select(Diagnostic)
        .options(selectinload(Diagnostic.samples))
        .where(Diagnostic.building_id == building_id)
        .order_by(Diagnostic.created_at.desc())
    )
    diagnostics = list(diag_result.scalars().all())

    interv_result = await db.execute(
        select(Intervention)
        .where(Intervention.building_id == building_id)
        .order_by(Intervention.date_start.desc().nulls_last())
    )
    interventions = list(interv_result.scalars().all())

    # Flatten samples
    all_samples: list[Sample] = []
    for diag in diagnostics:
        all_samples.extend(diag.samples or [])

    return {
        "building": building,
        "diagnostics": diagnostics,
        "samples": all_samples,
        "interventions": interventions,
    }


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------


def _has_positive_asbestos(samples: list[Sample]) -> bool:
    return any((s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded for s in samples)


def _has_any_positive(samples: list[Sample]) -> bool:
    return any(s.threshold_exceeded for s in samples)


def _has_classified_waste(samples: list[Sample]) -> bool:
    return any(s.threshold_exceeded and s.waste_disposal_type for s in samples)


def _has_completed_diagnostic(diagnostics: list[Diagnostic]) -> bool:
    return any(d.status in ("completed", "validated") for d in diagnostics)


def _has_completed_asbestos_intervention(interventions: list[Intervention]) -> bool:
    return any(
        i.status == "completed" and (i.intervention_type or "").lower() in ("asbestos_removal", "desamiantage")
        for i in interventions
    )


def _check_template_available(
    template_type: str,
    diagnostics: list[Diagnostic],
    samples: list[Sample],
    interventions: list[Intervention],
) -> bool:
    """Check if a template is available based on building data."""
    if template_type == "building_summary":
        return True
    if template_type == "diagnostic_summary":
        return len(diagnostics) > 0
    if template_type == "suva_notification":
        return _has_positive_asbestos(samples)
    if template_type == "cantonal_notification":
        return _has_any_positive(samples)
    if template_type == "waste_elimination_plan":
        return _has_classified_waste(samples)
    if template_type == "work_authorization_request":
        return _has_completed_diagnostic(diagnostics)
    if template_type == "air_clearance_request":
        return _has_completed_asbestos_intervention(interventions)
    return False


# ---------------------------------------------------------------------------
# Template generators
# ---------------------------------------------------------------------------


def _generate_building_summary(data: dict) -> tuple[list[TemplateSection], list[str]]:
    """Generate building summary template sections."""
    building = data["building"]
    warnings: list[str] = []

    # Identity section
    identity_fields = [
        TemplateField(label="Adresse", value=building.address, editable=False),
        TemplateField(label="Code postal", value=building.postal_code, editable=False),
        TemplateField(label="Ville", value=building.city, editable=False),
        TemplateField(label="Canton", value=building.canton, editable=False),
        TemplateField(
            label="EGID",
            value=str(building.egid) if building.egid else None,
            editable=building.egid is None,
        ),
        TemplateField(
            label="EGRID",
            value=getattr(building, "egrid", None),
            editable=getattr(building, "egrid", None) is None,
        ),
        TemplateField(
            label="Annee de construction",
            value=str(building.construction_year) if building.construction_year else None,
            editable=building.construction_year is None,
            field_type="number",
        ),
        TemplateField(
            label="Type de batiment",
            value=building.building_type or None,
            editable=not building.building_type,
        ),
    ]

    if not building.egid:
        warnings.append("EGID manquant")
    if not building.construction_year:
        warnings.append("Annee de construction manquante")

    # Owner section
    owner_fields = [
        TemplateField(label="Nom du proprietaire", value=None, editable=True),
        TemplateField(label="Adresse du proprietaire", value=None, editable=True),
        TemplateField(label="Telephone", value=None, editable=True),
        TemplateField(label="Email", value=None, editable=True),
    ]
    warnings.append("Coordonnees du proprietaire a completer")

    sections = [
        TemplateSection(name="identity", title="Identification du batiment", fields=identity_fields),
        TemplateSection(name="owner", title="Proprietaire", fields=owner_fields),
    ]

    return sections, warnings


def _generate_suva_notification(data: dict) -> tuple[list[TemplateSection], list[str]]:
    """Generate SUVA asbestos notification template."""
    building = data["building"]
    samples = data["samples"]
    diagnostics = data["diagnostics"]
    warnings: list[str] = []

    # Building identification
    building_fields = [
        TemplateField(
            label="Adresse du chantier",
            value=f"{building.address}, {building.postal_code} {building.city}",
            editable=False,
        ),
        TemplateField(label="Canton", value=building.canton, editable=False),
        TemplateField(
            label="EGID", value=str(building.egid) if building.egid else None, editable=building.egid is None
        ),
        TemplateField(
            label="Annee de construction",
            value=str(building.construction_year) if building.construction_year else None,
            editable=building.construction_year is None,
            field_type="number",
        ),
    ]

    if not building.egid:
        warnings.append("EGID manquant pour la notification SUVA")

    # Asbestos findings
    asbestos_samples = [s for s in samples if (s.pollutant_type or "").lower() == "asbestos" and s.threshold_exceeded]
    findings_fields = []
    for s in asbestos_samples:
        loc = " / ".join(filter(None, [s.location_floor, s.location_room, s.location_detail]))
        findings_fields.append(
            TemplateField(
                label=f"Echantillon {s.sample_number}",
                value=f"{loc} - {s.material_category or 'N/A'} - {s.concentration} {s.unit or ''}",
                editable=False,
            )
        )

    # Work category
    work_fields = []
    for s in asbestos_samples:
        work_fields.append(
            TemplateField(
                label=f"Categorie CFST ({s.sample_number})",
                value=s.cfst_work_category,
                editable=not s.cfst_work_category,
                field_type="choice",
                choices=["minor", "medium", "major"],
            )
        )
        if not s.cfst_work_category:
            warnings.append(f"Categorie CFST manquante pour echantillon {s.sample_number}")

    # Diagnostic reference
    diag_fields = []
    for d in diagnostics:
        diag_fields.append(TemplateField(label="Laboratoire", value=d.laboratory, editable=not d.laboratory))
        diag_fields.append(
            TemplateField(
                label="Numero de rapport", value=d.laboratory_report_number, editable=not d.laboratory_report_number
            )
        )
        if not d.laboratory:
            warnings.append("Laboratoire non renseigne")
        break  # Use first diagnostic

    # Responsible person
    responsible_fields = [
        TemplateField(label="Nom du responsable", value=None, editable=True),
        TemplateField(label="Fonction", value=None, editable=True),
        TemplateField(label="Telephone", value=None, editable=True),
        TemplateField(label="Date de notification", value=None, editable=True, field_type="date"),
    ]
    warnings.append("Responsable de notification a completer")

    sections = [
        TemplateSection(name="building", title="Identification du chantier", fields=building_fields),
        TemplateSection(name="findings", title="Resultats amiante", fields=findings_fields),
        TemplateSection(name="work_category", title="Categories de travaux CFST", fields=work_fields),
        TemplateSection(name="diagnostic_ref", title="Reference du diagnostic", fields=diag_fields),
        TemplateSection(name="responsible", title="Personne responsable", fields=responsible_fields),
    ]

    return sections, warnings


def _generate_cantonal_notification(data: dict) -> tuple[list[TemplateSection], list[str]]:
    """Generate cantonal authority notification template."""
    building = data["building"]
    samples = data["samples"]
    warnings: list[str] = []

    building_fields = [
        TemplateField(
            label="Adresse", value=f"{building.address}, {building.postal_code} {building.city}", editable=False
        ),
        TemplateField(label="Canton", value=building.canton, editable=False),
        TemplateField(
            label="EGID", value=str(building.egid) if building.egid else None, editable=building.egid is None
        ),
    ]

    positive = [s for s in samples if s.threshold_exceeded]
    pollutant_types = sorted({(s.pollutant_type or "inconnu") for s in positive})
    findings_fields = [
        TemplateField(label="Polluants detectes", value=", ".join(pollutant_types), editable=False),
        TemplateField(
            label="Nombre d'echantillons positifs", value=str(len(positive)), editable=False, field_type="number"
        ),
    ]

    authority_fields = [
        TemplateField(label="Autorite destinataire", value=None, editable=True),
        TemplateField(label="Reference du dossier", value=None, editable=True),
        TemplateField(label="Date de notification", value=None, editable=True, field_type="date"),
    ]
    warnings.append("Autorite destinataire a completer")

    sections = [
        TemplateSection(name="building", title="Identification du batiment", fields=building_fields),
        TemplateSection(name="findings", title="Polluants identifies", fields=findings_fields),
        TemplateSection(name="authority", title="Autorite cantonale", fields=authority_fields),
    ]

    return sections, warnings


def _generate_waste_elimination_plan(data: dict) -> tuple[list[TemplateSection], list[str]]:
    """Generate waste elimination plan template."""
    building = data["building"]
    samples = data["samples"]
    warnings: list[str] = []

    building_fields = [
        TemplateField(
            label="Adresse", value=f"{building.address}, {building.postal_code} {building.city}", editable=False
        ),
        TemplateField(label="Canton", value=building.canton, editable=False),
    ]

    waste_samples = [s for s in samples if s.threshold_exceeded and s.waste_disposal_type]
    waste_fields = []
    for s in waste_samples:
        loc = " / ".join(filter(None, [s.location_floor, s.location_room]))
        waste_fields.append(
            TemplateField(
                label=f"{s.pollutant_type} - {s.material_category or 'N/A'}",
                value=f"Type: {s.waste_disposal_type} | Localisation: {loc or 'N/A'}",
                editable=False,
            )
        )

    # Check for positive samples missing waste classification
    unclassified = [s for s in samples if s.threshold_exceeded and not s.waste_disposal_type]
    if unclassified:
        warnings.append(f"{len(unclassified)} echantillon(s) positif(s) sans classification de dechets")

    logistics_fields = [
        TemplateField(label="Entreprise d'elimination", value=None, editable=True),
        TemplateField(label="Site d'elimination", value=None, editable=True),
        TemplateField(label="Date prevue d'elimination", value=None, editable=True, field_type="date"),
        TemplateField(label="Quantite estimee (kg)", value=None, editable=True, field_type="number"),
    ]
    warnings.append("Logistique d'elimination a completer")

    sections = [
        TemplateSection(name="building", title="Identification du chantier", fields=building_fields),
        TemplateSection(name="waste", title="Dechets a eliminer", fields=waste_fields),
        TemplateSection(name="logistics", title="Logistique d'elimination", fields=logistics_fields),
    ]

    return sections, warnings


def _generate_work_authorization_request(data: dict) -> tuple[list[TemplateSection], list[str]]:
    """Generate work authorization request template."""
    building = data["building"]
    diagnostics = data["diagnostics"]
    warnings: list[str] = []

    building_fields = [
        TemplateField(
            label="Adresse", value=f"{building.address}, {building.postal_code} {building.city}", editable=False
        ),
        TemplateField(label="Canton", value=building.canton, editable=False),
        TemplateField(
            label="EGID", value=str(building.egid) if building.egid else None, editable=building.egid is None
        ),
    ]

    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    diag_fields = []
    for d in completed:
        diag_fields.append(TemplateField(label="Type de diagnostic", value=d.diagnostic_type, editable=False))
        diag_fields.append(
            TemplateField(
                label="Date d'inspection",
                value=str(d.date_inspection) if d.date_inspection else None,
                editable=d.date_inspection is None,
                field_type="date",
            )
        )
        diag_fields.append(TemplateField(label="Laboratoire", value=d.laboratory, editable=not d.laboratory))

    work_fields = [
        TemplateField(label="Description des travaux", value=None, editable=True),
        TemplateField(label="Date de debut prevue", value=None, editable=True, field_type="date"),
        TemplateField(label="Date de fin prevue", value=None, editable=True, field_type="date"),
        TemplateField(label="Entreprise executante", value=None, editable=True),
    ]
    warnings.append("Description des travaux a completer")

    sections = [
        TemplateSection(name="building", title="Identification du batiment", fields=building_fields),
        TemplateSection(name="diagnostic", title="Diagnostics de reference", fields=diag_fields),
        TemplateSection(name="work", title="Travaux prevus", fields=work_fields),
    ]

    return sections, warnings


def _generate_air_clearance_request(data: dict) -> tuple[list[TemplateSection], list[str]]:
    """Generate air clearance measurement request template."""
    building = data["building"]
    interventions = data["interventions"]
    warnings: list[str] = []

    building_fields = [
        TemplateField(
            label="Adresse", value=f"{building.address}, {building.postal_code} {building.city}", editable=False
        ),
        TemplateField(label="Canton", value=building.canton, editable=False),
    ]

    asbestos_interventions = [
        i
        for i in interventions
        if i.status == "completed" and (i.intervention_type or "").lower() in ("asbestos_removal", "desamiantage")
    ]
    interv_fields = []
    for i in asbestos_interventions:
        interv_fields.append(TemplateField(label="Intervention", value=i.title, editable=False))
        interv_fields.append(
            TemplateField(
                label="Date de fin",
                value=str(i.date_end) if i.date_end else None,
                editable=i.date_end is None,
                field_type="date",
            )
        )
        interv_fields.append(TemplateField(label="Entreprise", value=i.contractor_name, editable=not i.contractor_name))
        if not i.contractor_name:
            warnings.append("Nom de l'entreprise manquant pour l'intervention")

    measurement_fields = [
        TemplateField(label="Laboratoire de mesure", value=None, editable=True),
        TemplateField(label="Date de mesure souhaitee", value=None, editable=True, field_type="date"),
        TemplateField(label="Zones a mesurer", value=None, editable=True),
        TemplateField(label="Seuil de liberation (fibres/m3)", value="1000", editable=False, field_type="number"),
    ]
    warnings.append("Laboratoire de mesure a completer")

    sections = [
        TemplateSection(name="building", title="Identification du chantier", fields=building_fields),
        TemplateSection(name="interventions", title="Interventions realisees", fields=interv_fields),
        TemplateSection(name="measurement", title="Mesure de liberation", fields=measurement_fields),
    ]

    return sections, warnings


def _generate_diagnostic_summary(data: dict) -> tuple[list[TemplateSection], list[str]]:
    """Generate diagnostic findings summary template."""
    building = data["building"]
    diagnostics = data["diagnostics"]
    samples = data["samples"]
    warnings: list[str] = []

    building_fields = [
        TemplateField(
            label="Adresse", value=f"{building.address}, {building.postal_code} {building.city}", editable=False
        ),
        TemplateField(label="Canton", value=building.canton, editable=False),
        TemplateField(
            label="Annee de construction",
            value=str(building.construction_year) if building.construction_year else None,
            editable=False,
        ),
    ]

    diag_fields = []
    for d in diagnostics:
        diag_fields.append(TemplateField(label="Diagnostic", value=f"{d.diagnostic_type} - {d.status}", editable=False))
        diag_fields.append(
            TemplateField(
                label="Date d'inspection",
                value=str(d.date_inspection) if d.date_inspection else None,
                editable=False,
                field_type="date",
            )
        )
        diag_fields.append(TemplateField(label="Conclusion", value=d.conclusion, editable=False))

    if not diagnostics:
        warnings.append("Aucun diagnostic enregistre")

    # Sample summary by pollutant
    pollutant_counts: dict[str, dict] = {}
    for s in samples:
        pt = (s.pollutant_type or "inconnu").lower()
        if pt not in pollutant_counts:
            pollutant_counts[pt] = {"total": 0, "positive": 0}
        pollutant_counts[pt]["total"] += 1
        if s.threshold_exceeded:
            pollutant_counts[pt]["positive"] += 1

    sample_fields = []
    for pt, counts in sorted(pollutant_counts.items()):
        sample_fields.append(
            TemplateField(
                label=pt.capitalize(),
                value=f"{counts['positive']}/{counts['total']} positifs",
                editable=False,
            )
        )

    if not samples:
        warnings.append("Aucun echantillon enregistre")

    sections = [
        TemplateSection(name="building", title="Batiment", fields=building_fields),
        TemplateSection(name="diagnostics", title="Diagnostics", fields=diag_fields),
        TemplateSection(name="samples", title="Resume des echantillons", fields=sample_fields),
    ]

    return sections, warnings


_GENERATORS: dict[str, callable] = {
    "building_summary": _generate_building_summary,
    "suva_notification": _generate_suva_notification,
    "cantonal_notification": _generate_cantonal_notification,
    "waste_elimination_plan": _generate_waste_elimination_plan,
    "work_authorization_request": _generate_work_authorization_request,
    "air_clearance_request": _generate_air_clearance_request,
    "diagnostic_summary": _generate_diagnostic_summary,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_available_templates(db: AsyncSession, building_id: UUID) -> list[TemplateInfo]:
    """Return available templates for a building based on its data."""
    data = await _fetch_building_with_relations(db, building_id)
    if data is None:
        return []

    templates: list[TemplateInfo] = []
    for ttype, tdef in _TEMPLATE_DEFS.items():
        is_available = _check_template_available(
            ttype,
            data["diagnostics"],
            data["samples"],
            data["interventions"],
        )
        templates.append(
            TemplateInfo(
                template_type=ttype,
                title=tdef["title"],
                description=tdef["description"],
                is_available=is_available,
                required_data=tdef["required_data"],
                legal_basis=tdef.get("legal_basis"),
            )
        )

    return templates


async def generate_template(db: AsyncSession, building_id: UUID, template_type: str) -> GeneratedTemplate:
    """Generate a pre-filled template for a building.

    Raises:
        ValueError: If building not found or template not available.
    """
    if template_type not in _TEMPLATE_DEFS:
        raise ValueError(f"Unknown template type: {template_type}")

    data = await _fetch_building_with_relations(db, building_id)
    if data is None:
        raise ValueError("Building not found")

    is_available = _check_template_available(
        template_type,
        data["diagnostics"],
        data["samples"],
        data["interventions"],
    )
    if not is_available:
        raise ValueError(f"Template '{template_type}' is not available for this building")

    generator = _GENERATORS[template_type]
    sections, warnings = generator(data)

    building = data["building"]
    tdef = _TEMPLATE_DEFS[template_type]

    return GeneratedTemplate(
        template_type=template_type,
        title=tdef["title"],
        sections=sections,
        metadata={
            "building_id": str(building_id),
            "building_address": f"{building.address}, {building.postal_code} {building.city}",
            "generated_at": datetime.now(UTC).isoformat(),
            "legal_basis": tdef.get("legal_basis"),
        },
        warnings=warnings,
        generated_at=datetime.now(UTC),
    )
