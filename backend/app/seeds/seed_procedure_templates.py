"""Seed 8 real Swiss procedure templates for the Procedure OS.

Idempotent: upserts by name. Run via seed_data or standalone.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.procedure import ProcedureTemplate

logger = logging.getLogger(__name__)

TEMPLATES: list[dict] = [
    # 1. SUVA notification (federal) — asbestos/PCB works
    {
        "name": "Annonce SUVA — travaux sur substances dangereuses",
        "description": (
            "Notification obligatoire a la SUVA avant tout travail impliquant de l'amiante, "
            "des PCB ou d'autres substances dangereuses selon OTConst Art. 60a et directive CFST 6503."
        ),
        "procedure_type": "notification",
        "scope": "federal",
        "canton": None,
        "steps": [
            {
                "name": "identification_polluants",
                "order": 1,
                "required": True,
                "description": "Identifier les polluants presents (diagnostic prealable)",
            },
            {
                "name": "classification_travaux",
                "order": 2,
                "required": True,
                "description": "Classifier les travaux selon CFST 6503 (mineur/moyen/majeur)",
            },
            {
                "name": "preparation_annonce",
                "order": 3,
                "required": True,
                "description": "Remplir le formulaire d'annonce SUVA",
            },
            {
                "name": "envoi_annonce",
                "order": 4,
                "required": True,
                "description": "Envoyer l'annonce a la SUVA (min. 14 jours avant travaux)",
            },
            {
                "name": "confirmation_reception",
                "order": 5,
                "required": False,
                "description": "Attendre la confirmation de reception SUVA",
            },
        ],
        "required_artifacts": [
            {"type": "diagnostic_report", "description": "Rapport de diagnostic polluants", "mandatory": True},
            {"type": "work_plan", "description": "Plan des travaux avec mesures de protection", "mandatory": True},
            {"type": "suva_form", "description": "Formulaire d'annonce SUVA", "mandatory": True},
            {"type": "site_plan", "description": "Plan de situation", "mandatory": False},
        ],
        "authority_name": "SUVA (Caisse nationale suisse d'assurance en cas d'accidents)",
        "authority_route": "portal",
        "filing_channel": "Portail en ligne SUVA ou envoi postal",
        "form_template_ids": [],
        "applicable_work_families": ["asbestos_removal", "pcb_removal", "lead_removal", "pollutant_remediation"],
        "typical_duration_days": 21,
        "advance_notice_days": 14,
        "legal_basis": "OTConst Art. 60a, Directive CFST 6503",
        "source_url": "https://www.suva.ch",
        "version": "1.0",
    },
    # 2. Cantonal pollutant declaration VD
    {
        "name": "Declaration cantonale polluants — Vaud (DGE-DIREV)",
        "description": (
            "Declaration obligatoire au canton de Vaud (DGE-DIREV) pour tout "
            "batiment construit avant 1991 faisant l'objet de travaux de transformation ou demolition."
        ),
        "procedure_type": "declaration",
        "scope": "cantonal",
        "canton": "VD",
        "steps": [
            {
                "name": "diagnostic_prealable",
                "order": 1,
                "required": True,
                "description": "Realiser le diagnostic polluants (obligatoire avant 1991)",
            },
            {
                "name": "remplissage_formulaire",
                "order": 2,
                "required": True,
                "description": "Remplir le formulaire de declaration cantonale VD",
            },
            {
                "name": "joindre_diagnostic",
                "order": 3,
                "required": True,
                "description": "Joindre le rapport de diagnostic au dossier",
            },
            {
                "name": "depot_dge",
                "order": 4,
                "required": True,
                "description": "Deposer la declaration aupres de la DGE-DIREV",
            },
            {
                "name": "validation_cantonale",
                "order": 5,
                "required": True,
                "description": "Attendre la validation cantonale",
            },
        ],
        "required_artifacts": [
            {"type": "diagnostic_report", "description": "Rapport de diagnostic polluants complet", "mandatory": True},
            {"type": "cantonal_form", "description": "Formulaire de declaration cantonale VD", "mandatory": True},
            {"type": "building_plans", "description": "Plans du batiment", "mandatory": False},
            {"type": "site_photos", "description": "Photos du site", "mandatory": False},
        ],
        "authority_name": "DGE-DIREV (Direction generale de l'environnement — Division environnement)",
        "authority_route": "portal",
        "filing_channel": "Guichet Unique DGE en ligne",
        "form_template_ids": [],
        "applicable_work_families": [
            "asbestos_removal",
            "pcb_removal",
            "lead_removal",
            "hap_removal",
            "demolition",
            "renovation",
            "transformation",
        ],
        "typical_duration_days": 30,
        "advance_notice_days": 21,
        "legal_basis": "Loi cantonale VD sur la protection de l'environnement, Directive cantonale polluants",
        "source_url": "https://www.vd.ch/themes/environnement/sol/polluants-de-la-construction",
        "version": "1.0",
    },
    # 3. Cantonal pollutant declaration GE
    {
        "name": "Declaration cantonale polluants — Geneve (GESDEC)",
        "description": (
            "Declaration obligatoire a Geneve (GESDEC) pour tout batiment construit avant 1991 "
            "faisant l'objet de travaux de transformation, renovation ou demolition."
        ),
        "procedure_type": "declaration",
        "scope": "cantonal",
        "canton": "GE",
        "steps": [
            {
                "name": "diagnostic_prealable",
                "order": 1,
                "required": True,
                "description": "Realiser le diagnostic polluants (obligatoire avant 1991)",
            },
            {
                "name": "remplissage_formulaire_ge",
                "order": 2,
                "required": True,
                "description": "Remplir le formulaire GESDEC",
            },
            {
                "name": "depot_gesdec",
                "order": 3,
                "required": True,
                "description": "Deposer la declaration aupres du GESDEC",
            },
            {
                "name": "notification_entreprise",
                "order": 4,
                "required": True,
                "description": "Notifier l'entreprise de desamiantage",
            },
            {
                "name": "validation_cantonale",
                "order": 5,
                "required": True,
                "description": "Attendre la validation GESDEC",
            },
        ],
        "required_artifacts": [
            {"type": "diagnostic_report", "description": "Rapport de diagnostic polluants", "mandatory": True},
            {"type": "cantonal_form", "description": "Formulaire de declaration GESDEC", "mandatory": True},
            {
                "type": "contractor_certification",
                "description": "Certification de l'entreprise de desamiantage",
                "mandatory": True,
            },
            {"type": "waste_plan", "description": "Plan d'elimination des dechets", "mandatory": False},
        ],
        "authority_name": "GESDEC (Service de geologie, sols et dechets)",
        "authority_route": "portal",
        "filing_channel": "Portail AD-ENVIRONNEMENT (Geneve)",
        "form_template_ids": [],
        "applicable_work_families": [
            "asbestos_removal",
            "pcb_removal",
            "lead_removal",
            "hap_removal",
            "demolition",
            "renovation",
            "transformation",
        ],
        "typical_duration_days": 30,
        "advance_notice_days": 21,
        "legal_basis": "Reglement cantonal GE sur la gestion des dechets, Directive cantonale polluants",
        "source_url": "https://www.ge.ch/gestion-dechets-chantier",
        "version": "1.0",
    },
    # 4. Waste disposal plan (federal)
    {
        "name": "Plan d'elimination des dechets de chantier",
        "description": (
            "Plan d'elimination obligatoire selon OLED pour les chantiers generant plus de "
            "200 m3 de dechets ou contenant des dechets speciaux (amiante, PCB, plomb, HAP)."
        ),
        "procedure_type": "declaration",
        "scope": "federal",
        "canton": None,
        "steps": [
            {
                "name": "inventaire_dechets",
                "order": 1,
                "required": True,
                "description": "Inventorier les types et volumes de dechets attendus",
            },
            {
                "name": "classification_dechets",
                "order": 2,
                "required": True,
                "description": "Classifier selon OLED (type B, type E, special)",
            },
            {
                "name": "identification_filieres",
                "order": 3,
                "required": True,
                "description": "Identifier les filieres d'elimination agreees",
            },
            {"name": "redaction_plan", "order": 4, "required": True, "description": "Rediger le plan d'elimination"},
            {
                "name": "validation_plan",
                "order": 5,
                "required": True,
                "description": "Faire valider le plan par l'autorite competente",
            },
        ],
        "required_artifacts": [
            {"type": "waste_inventory", "description": "Inventaire des dechets", "mandatory": True},
            {"type": "waste_plan", "description": "Plan d'elimination", "mandatory": True},
            {"type": "disposal_contracts", "description": "Contrats avec filieres d'elimination", "mandatory": True},
            {"type": "diagnostic_report", "description": "Rapport de diagnostic (si polluants)", "mandatory": False},
        ],
        "authority_name": "Service cantonal de l'environnement (selon canton)",
        "authority_route": "physical",
        "filing_channel": "Depot du plan d'elimination au service cantonal",
        "form_template_ids": [],
        "applicable_work_families": [
            "demolition",
            "renovation",
            "asbestos_removal",
            "pcb_removal",
            "pollutant_remediation",
        ],
        "typical_duration_days": 14,
        "advance_notice_days": 14,
        "legal_basis": "OLED (Ordonnance sur la limitation et l'elimination des dechets)",
        "source_url": "https://www.fedlex.admin.ch/eli/cc/2015/891/fr",
        "version": "1.0",
    },
    # 5. Building permit (cantonal VD simplified)
    {
        "name": "Permis de construire simplifie — Vaud",
        "description": (
            "Procedure simplifiee de permis de construire dans le canton de Vaud "
            "pour les travaux de transformation interieure ou de renovation legere "
            "ne modifiant pas l'aspect exterieur du batiment."
        ),
        "procedure_type": "permit",
        "scope": "cantonal",
        "canton": "VD",
        "steps": [
            {
                "name": "dossier_preparation",
                "order": 1,
                "required": True,
                "description": "Preparer le dossier de demande de permis",
            },
            {
                "name": "plans_conformite",
                "order": 2,
                "required": True,
                "description": "Verifier la conformite des plans (architecte)",
            },
            {"name": "depot_commune", "order": 3, "required": True, "description": "Deposer le dossier a la commune"},
            {
                "name": "instruction_municipale",
                "order": 4,
                "required": True,
                "description": "Instruction par la municipalite",
            },
            {
                "name": "decision",
                "order": 5,
                "required": True,
                "description": "Decision d'octroi ou de refus du permis",
            },
        ],
        "required_artifacts": [
            {"type": "building_plans", "description": "Plans du batiment (existant + projet)", "mandatory": True},
            {
                "type": "architectural_description",
                "description": "Description architecturale du projet",
                "mandatory": True,
            },
            {"type": "site_plan", "description": "Plan de situation 1:500", "mandatory": True},
            {
                "type": "energy_certificate",
                "description": "Justificatif energetique (si applicable)",
                "mandatory": False,
            },
            {
                "type": "pollutant_clearance",
                "description": "Attestation absence polluants ou declaration",
                "mandatory": False,
            },
        ],
        "authority_name": "Municipalite de la commune",
        "authority_route": "physical",
        "filing_channel": "Depot en main propre ou envoi recommande a la commune",
        "form_template_ids": [],
        "applicable_work_families": ["renovation", "transformation", "interior_works"],
        "typical_duration_days": 60,
        "advance_notice_days": 0,
        "legal_basis": "LATC (Loi sur l'amenagement du territoire et les constructions — Vaud)",
        "source_url": "https://www.vd.ch/themes/territoire-et-construction/constructions",
        "version": "1.0",
    },
    # 6. Demolition permit (cantonal VD)
    {
        "name": "Permis de demolir — Vaud",
        "description": (
            "Autorisation de demolir dans le canton de Vaud. Necessaire pour toute "
            "demolition complete ou partielle d'un batiment. Inclut diagnostic polluants "
            "obligatoire pour les batiments construits avant 1991."
        ),
        "procedure_type": "permit",
        "scope": "cantonal",
        "canton": "VD",
        "steps": [
            {
                "name": "diagnostic_polluants",
                "order": 1,
                "required": True,
                "description": "Realiser le diagnostic polluants (obligatoire avant 1991)",
            },
            {
                "name": "plan_elimination",
                "order": 2,
                "required": True,
                "description": "Etablir le plan d'elimination des dechets",
            },
            {
                "name": "dossier_demolition",
                "order": 3,
                "required": True,
                "description": "Preparer le dossier de demande de demolition",
            },
            {
                "name": "enquete_publique",
                "order": 4,
                "required": True,
                "description": "Mise a l'enquete publique (30 jours)",
            },
            {
                "name": "notification_suva",
                "order": 5,
                "required": True,
                "description": "Notifier la SUVA si polluants presents",
            },
            {"name": "decision_municipale", "order": 6, "required": True, "description": "Decision de la municipalite"},
        ],
        "required_artifacts": [
            {"type": "diagnostic_report", "description": "Rapport de diagnostic polluants complet", "mandatory": True},
            {"type": "waste_plan", "description": "Plan d'elimination des dechets", "mandatory": True},
            {"type": "building_plans", "description": "Plans du batiment a demolir", "mandatory": True},
            {"type": "site_plan", "description": "Plan de situation", "mandatory": True},
            {
                "type": "heritage_clearance",
                "description": "Avis du service des monuments (si classe)",
                "mandatory": False,
            },
            {"type": "suva_notification", "description": "Copie de l'annonce SUVA", "mandatory": False},
        ],
        "authority_name": "Municipalite de la commune + DGE-DIREV",
        "authority_route": "physical",
        "filing_channel": "Depot a la commune + copie DGE",
        "form_template_ids": [],
        "applicable_work_families": ["demolition"],
        "typical_duration_days": 90,
        "advance_notice_days": 0,
        "legal_basis": "LATC Art. 103 ss, Directive cantonale polluants VD",
        "source_url": "https://www.vd.ch/themes/territoire-et-construction/constructions",
        "version": "1.0",
    },
    # 7. Energy renovation declaration
    {
        "name": "Declaration de renovation energetique (Programme Batiments)",
        "description": (
            "Declaration pour beneficier des subventions du Programme Batiments "
            "(programme federal + complements cantonaux) pour les travaux d'amelioration "
            "energetique: isolation, chauffage, fenetres, ventilation."
        ),
        "procedure_type": "funding",
        "scope": "federal",
        "canton": None,
        "steps": [
            {
                "name": "audit_energetique",
                "order": 1,
                "required": True,
                "description": "Realiser un audit energetique ou CECB",
            },
            {
                "name": "devis_travaux",
                "order": 2,
                "required": True,
                "description": "Obtenir les devis des travaux prevus",
            },
            {
                "name": "demande_subvention",
                "order": 3,
                "required": True,
                "description": "Deposer la demande de subvention (AVANT debut des travaux)",
            },
            {"name": "accord_prealable", "order": 4, "required": True, "description": "Attendre l'accord prealable"},
            {"name": "realisation_travaux", "order": 5, "required": True, "description": "Realiser les travaux"},
            {
                "name": "justificatifs_finaux",
                "order": 6,
                "required": True,
                "description": "Envoyer les justificatifs de fin de travaux",
            },
            {
                "name": "versement",
                "order": 7,
                "required": False,
                "description": "Reception du versement de la subvention",
            },
        ],
        "required_artifacts": [
            {"type": "energy_audit", "description": "Audit energetique ou certificat CECB", "mandatory": True},
            {"type": "cost_estimate", "description": "Devis detaille des travaux", "mandatory": True},
            {"type": "subsidy_form", "description": "Formulaire de demande de subvention", "mandatory": True},
            {"type": "completion_photos", "description": "Photos avant/apres travaux", "mandatory": True},
            {"type": "invoices", "description": "Factures des travaux realises", "mandatory": True},
        ],
        "authority_name": "Service cantonal de l'energie (selon canton)",
        "authority_route": "portal",
        "filing_channel": "Portail en ligne du Programme Batiments",
        "form_template_ids": [],
        "applicable_work_families": [
            "energy_renovation",
            "insulation",
            "heating_replacement",
            "window_replacement",
            "ventilation",
        ],
        "typical_duration_days": 120,
        "advance_notice_days": 30,
        "legal_basis": "Loi sur le CO2, Programme Batiments (Confederation + cantons)",
        "source_url": "https://www.leprogrammebatiments.ch",
        "version": "1.0",
    },
    # 8. Heritage review request
    {
        "name": "Demande de preavis des monuments historiques",
        "description": (
            "Demande de preavis obligatoire aupres du service des monuments historiques "
            "pour tout travail sur un batiment classe ou inventorie. Le preavis conditionne "
            "l'obtention du permis de construire."
        ),
        "procedure_type": "authorization",
        "scope": "cantonal",
        "canton": "VD",
        "steps": [
            {
                "name": "identification_classement",
                "order": 1,
                "required": True,
                "description": "Verifier le classement du batiment (RF, inventaire)",
            },
            {
                "name": "description_projet",
                "order": 2,
                "required": True,
                "description": "Decrire le projet de travaux en detail",
            },
            {
                "name": "dossier_preavis",
                "order": 3,
                "required": True,
                "description": "Constituer le dossier pour le service des monuments",
            },
            {"name": "depot_demande", "order": 4, "required": True, "description": "Deposer la demande de preavis"},
            {
                "name": "visite_site",
                "order": 5,
                "required": False,
                "description": "Visite du site par le conservateur (si necessaire)",
            },
            {
                "name": "preavis",
                "order": 6,
                "required": True,
                "description": "Reception du preavis (favorable/defavorable/conditionnel)",
            },
        ],
        "required_artifacts": [
            {"type": "building_plans", "description": "Plans du batiment (existant + projet)", "mandatory": True},
            {"type": "heritage_file", "description": "Fiche de classement ou inventaire", "mandatory": True},
            {"type": "project_description", "description": "Description detaillee du projet", "mandatory": True},
            {
                "type": "site_photos",
                "description": "Photographies du batiment et des elements concernes",
                "mandatory": True,
            },
            {
                "type": "material_samples",
                "description": "Echantillons de materiaux (si restauration)",
                "mandatory": False,
            },
        ],
        "authority_name": "Section monuments et sites (VD)",
        "authority_route": "physical",
        "filing_channel": "Envoi postal ou depot au service des monuments et sites",
        "form_template_ids": [],
        "applicable_work_families": ["renovation", "transformation", "restoration", "demolition"],
        "typical_duration_days": 45,
        "advance_notice_days": 0,
        "legal_basis": "LPNMS (Loi sur la protection de la nature, des monuments et des sites — VD)",
        "source_url": "https://www.vd.ch/themes/culture/patrimoine-bati-et-sites",
        "version": "1.0",
    },
]


async def seed_procedure_templates(db: AsyncSession) -> int:
    """Seed procedure templates. Idempotent: upserts by name.

    Returns number of templates created or updated.
    """
    count = 0
    for data in TEMPLATES:
        result = await db.execute(select(ProcedureTemplate).where(ProcedureTemplate.name == data["name"]))
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            for key, value in data.items():
                setattr(existing, key, value)
            logger.info("Updated procedure template: %s", data["name"])
        else:
            tpl = ProcedureTemplate(**data)
            db.add(tpl)
            logger.info("Created procedure template: %s", data["name"])

        count += 1

    await db.flush()
    logger.info("Seeded %d procedure templates", count)
    return count
