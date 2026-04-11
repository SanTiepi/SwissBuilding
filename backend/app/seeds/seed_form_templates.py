"""
BatiConnect - Seed form templates

Seeds the most common Swiss regulatory form templates with fields_schema
and required_attachments. Idempotent (upserts by form_type + canton).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_instance import FormTemplate

FORM_TEMPLATES: list[dict] = [
    {
        "name": "Notification SUVA",
        "description": "Notification obligatoire a la SUVA en cas de travaux avec exposition a l'amiante.",
        "form_type": "suva_notification",
        "canton": None,
        "version": "1.0",
        "source_url": "https://www.suva.ch/fr/materiel/fiche-thematique/amiante-notification",
        "fields_schema": [
            {
                "name": "building_address",
                "label": "Adresse du batiment",
                "type": "text",
                "required": True,
                "source_mapping": "building.address",
            },
            {
                "name": "building_city",
                "label": "Localite",
                "type": "text",
                "required": True,
                "source_mapping": "building.city",
            },
            {
                "name": "building_postal_code",
                "label": "NPA",
                "type": "text",
                "required": True,
                "source_mapping": "building.postal_code",
            },
            {
                "name": "building_egid",
                "label": "EGID",
                "type": "text",
                "required": False,
                "source_mapping": "building.egid",
            },
            {
                "name": "owner",
                "label": "Proprietaire / maitre d'ouvrage",
                "type": "text",
                "required": True,
                "source_mapping": "building.owner",
            },
            {
                "name": "work_type",
                "label": "Type de travaux",
                "type": "select",
                "required": True,
                "source_mapping": "intervention.type",
                "options": ["renovation", "demolition", "transformation", "entretien"],
            },
            {
                "name": "pollutant_type",
                "label": "Type de polluant",
                "type": "text",
                "required": True,
                "source_mapping": "diagnostic.pollutant_types",
            },
            {
                "name": "quantities",
                "label": "Quantites estimees (m2/ml)",
                "type": "text",
                "required": True,
                "source_mapping": "manual",
            },
            {
                "name": "contractor",
                "label": "Entreprise de desamiantage",
                "type": "text",
                "required": True,
                "source_mapping": "intervention.contractor",
            },
            {
                "name": "start_date",
                "label": "Date de debut des travaux",
                "type": "date",
                "required": True,
                "source_mapping": "intervention.start_date",
            },
            {
                "name": "end_date",
                "label": "Date de fin prevue",
                "type": "date",
                "required": False,
                "source_mapping": "intervention.end_date",
            },
            {
                "name": "work_category",
                "label": "Categorie de travaux CFST",
                "type": "select",
                "required": True,
                "source_mapping": "manual",
                "options": ["minor", "medium", "major"],
            },
        ],
        "required_attachments": ["diagnostic_report", "work_plan"],
    },
    {
        "name": "Declaration polluants VD",
        "description": "Declaration cantonale des polluants pour le canton de Vaud (DGE-DIRNA).",
        "form_type": "cantonal_declaration",
        "canton": "VD",
        "version": "1.0",
        "source_url": None,
        "fields_schema": [
            {
                "name": "building_address",
                "label": "Adresse du batiment",
                "type": "text",
                "required": True,
                "source_mapping": "building.address",
            },
            {
                "name": "building_city",
                "label": "Localite",
                "type": "text",
                "required": True,
                "source_mapping": "building.city",
            },
            {
                "name": "building_postal_code",
                "label": "NPA",
                "type": "text",
                "required": True,
                "source_mapping": "building.postal_code",
            },
            {
                "name": "building_egid",
                "label": "EGID",
                "type": "text",
                "required": False,
                "source_mapping": "building.egid",
            },
            {
                "name": "building_egrid",
                "label": "EGRID",
                "type": "text",
                "required": False,
                "source_mapping": "building.egrid",
            },
            {
                "name": "owner",
                "label": "Proprietaire",
                "type": "text",
                "required": True,
                "source_mapping": "building.owner",
            },
            {
                "name": "construction_year",
                "label": "Annee de construction",
                "type": "text",
                "required": False,
                "source_mapping": "building.construction_year",
            },
            {
                "name": "pollutant_inventory",
                "label": "Inventaire des polluants detectes",
                "type": "textarea",
                "required": True,
                "source_mapping": "diagnostic.pollutant_inventory",
            },
            {
                "name": "diagnostic_references",
                "label": "References des diagnostics",
                "type": "text",
                "required": True,
                "source_mapping": "diagnostic.references",
            },
            {
                "name": "planned_works",
                "label": "Travaux prevus",
                "type": "textarea",
                "required": False,
                "source_mapping": "intervention.scope",
            },
        ],
        "required_attachments": ["diagnostic_report"],
    },
    {
        "name": "Plan de gestion des dechets",
        "description": "Plan de gestion des dechets de chantier selon l'OLED (federal).",
        "form_type": "waste_plan",
        "canton": None,
        "version": "1.0",
        "source_url": None,
        "fields_schema": [
            {
                "name": "building_address",
                "label": "Adresse du batiment",
                "type": "text",
                "required": True,
                "source_mapping": "building.address",
            },
            {
                "name": "building_city",
                "label": "Localite",
                "type": "text",
                "required": True,
                "source_mapping": "building.city",
            },
            {
                "name": "building_postal_code",
                "label": "NPA",
                "type": "text",
                "required": True,
                "source_mapping": "building.postal_code",
            },
            {
                "name": "waste_types",
                "label": "Types de dechets",
                "type": "textarea",
                "required": True,
                "source_mapping": "waste.types",
            },
            {
                "name": "waste_quantities",
                "label": "Quantites estimees (tonnes)",
                "type": "text",
                "required": True,
                "source_mapping": "waste.quantities",
            },
            {
                "name": "disposal_routes",
                "label": "Filieres d'elimination",
                "type": "textarea",
                "required": True,
                "source_mapping": "waste.disposal_routes",
            },
            {
                "name": "contractor",
                "label": "Entreprise responsable",
                "type": "text",
                "required": True,
                "source_mapping": "intervention.contractor",
            },
        ],
        "required_attachments": ["diagnostic_report", "waste_elimination_plan"],
    },
    {
        "name": "Demande de permis de construire (simplifiee)",
        "description": "Formulaire simplifie de demande de permis de construire.",
        "form_type": "work_permit",
        "canton": None,
        "version": "1.0",
        "source_url": None,
        "fields_schema": [
            {
                "name": "building_address",
                "label": "Adresse du batiment",
                "type": "text",
                "required": True,
                "source_mapping": "building.address",
            },
            {
                "name": "building_city",
                "label": "Localite",
                "type": "text",
                "required": True,
                "source_mapping": "building.city",
            },
            {
                "name": "building_postal_code",
                "label": "NPA",
                "type": "text",
                "required": True,
                "source_mapping": "building.postal_code",
            },
            {
                "name": "building_egid",
                "label": "EGID",
                "type": "text",
                "required": False,
                "source_mapping": "building.egid",
            },
            {
                "name": "building_egrid",
                "label": "EGRID",
                "type": "text",
                "required": False,
                "source_mapping": "building.egrid",
            },
            {
                "name": "owner",
                "label": "Proprietaire / maitre d'ouvrage",
                "type": "text",
                "required": True,
                "source_mapping": "building.owner",
            },
            {
                "name": "architect",
                "label": "Architecte mandataire",
                "type": "text",
                "required": True,
                "source_mapping": "manual",
            },
            {
                "name": "work_description",
                "label": "Description des travaux",
                "type": "textarea",
                "required": True,
                "source_mapping": "intervention.scope",
            },
            {
                "name": "budget_estimate",
                "label": "Estimation du cout (CHF)",
                "type": "text",
                "required": True,
                "source_mapping": "manual",
            },
            {
                "name": "has_pollutants",
                "label": "Polluants detectes (oui/non)",
                "type": "text",
                "required": True,
                "source_mapping": "diagnostic.has_positive_asbestos",
            },
            {
                "name": "surface_area",
                "label": "Surface de plancher (m2)",
                "type": "text",
                "required": False,
                "source_mapping": "building.surface_area_m2",
            },
        ],
        "required_attachments": ["diagnostic_report", "architectural_plan"],
    },
]


async def seed_form_templates(db: AsyncSession) -> int:
    """Seed form templates. Idempotent: skips existing by form_type + canton."""
    created = 0
    for tpl_data in FORM_TEMPLATES:
        canton = tpl_data["canton"]
        form_type = tpl_data["form_type"]

        # Check existence
        query = select(FormTemplate).where(FormTemplate.form_type == form_type)
        if canton:
            query = query.where(FormTemplate.canton == canton)
        else:
            query = query.where(FormTemplate.canton.is_(None))

        result = await db.execute(query)
        if result.scalar_one_or_none() is not None:
            continue

        template = FormTemplate(
            name=tpl_data["name"],
            description=tpl_data["description"],
            form_type=form_type,
            canton=canton,
            version=tpl_data["version"],
            source_url=tpl_data.get("source_url"),
            fields_schema=tpl_data["fields_schema"],
            required_attachments=tpl_data["required_attachments"],
            active=True,
        )
        db.add(template)
        created += 1

    if created:
        await db.flush()
    return created
