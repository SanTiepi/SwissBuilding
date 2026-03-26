"""Bootstrap helpers for the SwissRules regulatory spine.

This module is intentionally self-contained so it can help future waves
without forcing immediate router or ORM wiring while nearby hub files are
in motion.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256

from app.schemas.swiss_rules import (
    AntiDuplicationGuardrail,
    ApplicabilityEvaluation,
    ApplicabilityStatus,
    AuthorityRegistry,
    BuildingContext,
    ChangeSeverity,
    ChangeType,
    ImpactReview,
    IntegrationTarget,
    Jurisdiction,
    JurisdictionLevel,
    LegalChangeEvent,
    NormativeForce,
    ProcedureStepTemplate,
    ProcedureTemplate,
    ProjectContext,
    RequirementTemplate,
    ReviewStatus,
    RuleSnapshot,
    RuleSource,
    RuleTemplate,
    SourceKind,
    SwissRulesEnablementPack,
    WatchCadence,
    WatchPlan,
)


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def build_integration_targets() -> list[IntegrationTarget]:
    return [
        IntegrationTarget(
            code="permit_tracking",
            subsystem="permit_tracking",
            anchored_path="backend/app/services/permit_tracking_service.py",
            integration_mode="reuse_existing_read_model",
            notes="Computed permit needs remain the canonical read model for required permits.",
        ),
        IntegrationTarget(
            code="regulatory_filing",
            subsystem="regulatory_filing",
            anchored_path="backend/app/services/regulatory_filing_service.py",
            integration_mode="reuse_existing_output_service",
            notes="SUVA, cantonal declarations, and OLED filings stay anchored here.",
        ),
        IntegrationTarget(
            code="obligation",
            subsystem="obligation",
            anchored_path="backend/app/services/obligation_service.py",
            integration_mode="reuse_existing_deadline_entity",
            notes="All regulatory or procedural deadlines flow through the existing Obligation model.",
        ),
        IntegrationTarget(
            code="document_inbox",
            subsystem="document_inbox",
            anchored_path="backend/app/services/document_inbox_service.py",
            integration_mode="reuse_existing_inbox",
            notes="Incoming documents must be qualified through the existing inbox rather than a parallel queue.",
        ),
        IntegrationTarget(
            code="authority_pack",
            subsystem="authority_pack",
            anchored_path="backend/app/services/authority_pack_service.py",
            integration_mode="reuse_existing_pack_output",
            notes="Authority-facing proof should enrich authority packs rather than create a second dossier channel.",
        ),
        IntegrationTarget(
            code="control_tower",
            subsystem="control_tower",
            anchored_path="frontend/src/api/controlTower.ts",
            integration_mode="extend_existing_aggregator",
            notes="New regulatory signals should feed the current operating inbox instead of spawning a parallel action system.",
        ),
        IntegrationTarget(
            code="permit_procedure",
            subsystem="permit_procedure",
            anchored_path="future:backend/app/services/permit_procedure_service.py",
            integration_mode="future_execution_layer",
            notes="Future PermitProcedure execution should consume ProcedureTemplate rather than duplicate permit logic.",
        ),
        IntegrationTarget(
            code="proof_delivery",
            subsystem="proof_delivery",
            anchored_path="future:backend/app/models/proof_delivery.py",
            integration_mode="future_proof_distribution_layer",
            notes="Distribution and acknowledgement tracking should attach to existing packs and documents.",
        ),
    ]


def build_guardrails() -> list[AntiDuplicationGuardrail]:
    return [
        AntiDuplicationGuardrail(
            code="no_parallel_permit_logic",
            title="Keep permit computation anchored to permit_tracking",
            rule="Do not create a second rules engine that independently answers which permits are required.",
            reuse_target="permit_tracking",
            prohibited_patterns=[
                "parallel /permits/* logic",
                "second permit-read model",
                "duplicate permit status engine",
            ],
        ),
        AntiDuplicationGuardrail(
            code="no_second_obligation_entity",
            title="One deadline entity only",
            rule="All regulatory and procedural due dates must land in the existing Obligation entity.",
            reuse_target="obligation",
            prohibited_patterns=["new deadline model", "second obligation table", "procedure-specific due date entity"],
        ),
        AntiDuplicationGuardrail(
            code="no_second_document_inbox",
            title="One incoming document queue",
            rule="Do not create a regulatory-only inbox for documents that can flow through DocumentInbox.",
            reuse_target="document_inbox",
            prohibited_patterns=["regulatory inbox", "authority inbox clone", "second incoming document queue"],
        ),
        AntiDuplicationGuardrail(
            code="no_free_json_document_links",
            title="Prefer object links over free-form JSON",
            rule="Procedures and requirements should link to existing Document, ComplianceArtefact, and EvidencePack entities when possible.",
            reuse_target="authority_pack",
            prohibited_patterns=[
                "documents_json ids only",
                "opaque proof blobs",
                "free-form attachment JSON as source of truth",
            ],
        ),
        AntiDuplicationGuardrail(
            code="no_parallel_action_system",
            title="Extend Control Tower instead of replacing it",
            rule="New regulatory blockers should aggregate into Control Tower and not create a separate action feed.",
            reuse_target="control_tower",
            prohibited_patterns=[
                "standalone regulatory inbox",
                "second next-best-action pipeline",
                "unintegrated blocker list",
            ],
        ),
    ]


def build_jurisdictions() -> list[Jurisdiction]:
    return [
        Jurisdiction(code="ch", name="Confederation suisse", level=JurisdictionLevel.FEDERAL),
        Jurisdiction(
            code="ch-endk",
            name="Conference des directeurs cantonaux de l'energie",
            level=JurisdictionLevel.INTERCANTONAL,
            parent_code="ch",
            notes="Intercantonal energy harmonisation.",
        ),
        Jurisdiction(code="ch-vd", name="Canton de Vaud", level=JurisdictionLevel.CANTONAL, parent_code="ch"),
        Jurisdiction(code="ch-ge", name="Canton de Geneve", level=JurisdictionLevel.CANTONAL, parent_code="ch"),
        Jurisdiction(code="ch-fr", name="Canton de Fribourg", level=JurisdictionLevel.CANTONAL, parent_code="ch"),
        Jurisdiction(
            code="ch-communal",
            name="Communes suisses",
            level=JurisdictionLevel.COMMUNAL,
            parent_code="ch",
            notes="Generic placeholder for commune-specific zoning and construction rules.",
        ),
        Jurisdiction(
            code="ch-utility",
            name="Utilities and infrastructure operators",
            level=JurisdictionLevel.UTILITY,
            parent_code="ch",
            notes="Network and concession constraints sit here when they affect procedures.",
        ),
        Jurisdiction(
            code="std-vkf",
            name="Association des etablissements cantonaux d'assurance incendie",
            level=JurisdictionLevel.PRIVATE_STANDARD,
            parent_code="ch",
        ),
        Jurisdiction(
            code="std-sia",
            name="Societe suisse des ingenieurs et des architectes",
            level=JurisdictionLevel.PRIVATE_STANDARD,
            parent_code="ch",
        ),
        Jurisdiction(code="std-minergie", name="Minergie", level=JurisdictionLevel.PRIVATE_STANDARD, parent_code="ch"),
        Jurisdiction(code="std-fach", name="FACH", level=JurisdictionLevel.PRIVATE_STANDARD, parent_code="ch"),
        Jurisdiction(code="std-asca", name="ASCA/VABS", level=JurisdictionLevel.PRIVATE_STANDARD, parent_code="ch"),
    ]


def build_authority_registry() -> list[AuthorityRegistry]:
    return [
        AuthorityRegistry(
            code="are_ch",
            name="Office federal du developpement territorial",
            jurisdiction_code="ch",
            authority_type="federal_office",
            portal_url="https://www.are.admin.ch/",
            filing_modes=["guidance"],
        ),
        AuthorityRegistry(
            code="bafu_ch",
            name="Office federal de l'environnement",
            jurisdiction_code="ch",
            authority_type="federal_office",
            portal_url="https://www.bafu.admin.ch/",
            filing_modes=["guidance", "reference"],
        ),
        AuthorityRegistry(
            code="bag_ch",
            name="Office federal de la sante publique",
            jurisdiction_code="ch",
            authority_type="federal_office",
            portal_url="https://www.bag.admin.ch/",
            filing_modes=["guidance", "reference"],
        ),
        AuthorityRegistry(
            code="suva_ch",
            name="SUVA",
            jurisdiction_code="ch",
            authority_type="execution_body",
            portal_url="https://www.suva.ch/",
            filing_modes=["notification", "guidance"],
        ),
        AuthorityRegistry(
            code="ekas_ch",
            name="CFST / EKAS",
            jurisdiction_code="ch",
            authority_type="execution_body",
            portal_url="https://www.ekas.admin.ch/",
            filing_modes=["directive"],
        ),
        AuthorityRegistry(
            code="endk_ch",
            name="EnDK",
            jurisdiction_code="ch-endk",
            authority_type="intercantonal_body",
            portal_url="https://www.endk.ch/fr/politique-energetique/mopec",
            filing_modes=["standard"],
        ),
        AuthorityRegistry(
            code="bfs_regbl",
            name="OFS - RegBL",
            jurisdiction_code="ch",
            authority_type="federal_register",
            portal_url="https://www.delimo.bfs.admin.ch/fr/index.html",
            filing_modes=["reference", "dataset"],
        ),
        AuthorityRegistry(
            code="swisstopo_cadastre",
            name="swisstopo / cadastre RDPPF",
            jurisdiction_code="ch",
            authority_type="federal_cadastre",
            portal_url="https://www.cadastre.ch/fr/cadastre-rdppf",
            filing_modes=["reference", "dataset"],
        ),
        AuthorityRegistry(
            code="bak_ch",
            name="Office federal de la culture",
            jurisdiction_code="ch",
            authority_type="federal_office",
            portal_url="https://www.bak.admin.ch/bak/fr/home/baukultur/isos-und-ortsbildschutz.html",
            filing_modes=["guidance", "reference"],
        ),
        AuthorityRegistry(
            code="ebgb_ch",
            name="Bureau federal de l'egalite pour les personnes handicapees",
            jurisdiction_code="ch",
            authority_type="federal_office",
            portal_url="https://www.ebgb.admin.ch/fr/loi-sur-legalite-pour-les-personnes-handicapees-lhand",
            filing_modes=["guidance", "reference"],
        ),
        AuthorityRegistry(
            code="vd_camac",
            name="CAMAC Vaud",
            jurisdiction_code="ch-vd",
            authority_type="cantonal_portal",
            portal_url="https://www.vd.ch/territoire-et-construction/permis-de-construire",
            filing_modes=["portal_submission"],
        ),
        AuthorityRegistry(
            code="ge_oac",
            name="Autorisations de construire Geneve",
            jurisdiction_code="ch-ge",
            authority_type="cantonal_portal",
            portal_url="https://www.ge.ch/demander-autorisation-construire",
            filing_modes=["portal_submission"],
        ),
        AuthorityRegistry(
            code="fr_seca",
            name="Service des constructions et de l'amenagement Fribourg",
            jurisdiction_code="ch-fr",
            authority_type="cantonal_portal",
            portal_url="https://www.fr.ch/territoire-amenagement-et-constructions/territoire/seca-presentation-du-service",
            filing_modes=["portal_submission"],
        ),
        AuthorityRegistry(
            code="communal_building_authority",
            name="Autorite communale de construction",
            jurisdiction_code="ch-communal",
            authority_type="communal_authority",
            portal_url="https://www.ch.ch/",
            filing_modes=["manual_review"],
            notes="Placeholder authority for commune-specific adapters.",
        ),
        AuthorityRegistry(
            code="vkf_aeai",
            name="VKF / AEAI",
            jurisdiction_code="std-vkf",
            authority_type="intercantonal_standard_body",
            portal_url="https://www.vkf.ch/",
            filing_modes=["standard"],
        ),
    ]


def build_rule_sources() -> list[RuleSource]:
    return [
        RuleSource(
            source_id="are_hors_zone",
            title="ARE - Construire hors de la zone a batir",
            url="https://www.are.admin.ch/fr/horszone",
            jurisdiction_code="ch",
            publisher="ARE",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.GUIDELINE,
            cadence=WatchCadence.WEEKLY,
            tags=["territory", "outside_zone", "procedure"],
        ),
        RuleSource(
            source_id="are_lat_oat",
            title="ARE - LAT/OAT",
            url="https://www.are.admin.ch/fr/newnsb/j4neypyAUUfxheQESMmda",
            jurisdiction_code="ch",
            publisher="ARE",
            normative_force=NormativeForce.BINDING_LAW,
            source_kind=SourceKind.LEGAL_TEXT,
            cadence=WatchCadence.WEEKLY,
            tags=["territory", "planning"],
        ),
        RuleSource(
            source_id="bafu_oled",
            title="BAFU - OLED",
            url="https://www.bafu.admin.ch/fr/oled",
            jurisdiction_code="ch",
            publisher="BAFU",
            normative_force=NormativeForce.BINDING_REGULATION,
            source_kind=SourceKind.LEGAL_TEXT,
            cadence=WatchCadence.WEEKLY,
            tags=["waste", "environment"],
        ),
        RuleSource(
            source_id="bafu_waste_law",
            title="BAFU - Lois et ordonnances dechets",
            url="https://www.bafu.admin.ch/bafu/fr/home/themes/dechets/droit/lois-ordonnances.html",
            jurisdiction_code="ch",
            publisher="BAFU",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.GUIDELINE,
            cadence=WatchCadence.WEEKLY,
            tags=["waste", "law"],
        ),
        RuleSource(
            source_id="bafu_pcb_joints",
            title="BAFU - Masses d'etancheite contenant des PCB",
            url="https://www.bafu.admin.ch/fr/masses-detancheite-des-joints",
            jurisdiction_code="ch",
            publisher="BAFU",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.GUIDELINE,
            cadence=WatchCadence.MONTHLY,
            tags=["pcb", "pollutants"],
        ),
        RuleSource(
            source_id="bag_radon",
            title="BAG - Protection contre le radon",
            url="https://www.bag.admin.ch/fr/protection-contre-le-radon",
            jurisdiction_code="ch",
            publisher="BAG",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.GUIDELINE,
            cadence=WatchCadence.MONTHLY,
            tags=["radon", "health"],
        ),
        RuleSource(
            source_id="bag_radon_legal",
            title="BAG - Dispositions legales concernant le radon",
            url="https://www.bag.admin.ch/fr/dispositions-legales-concernant-le-radon",
            jurisdiction_code="ch",
            publisher="BAG",
            normative_force=NormativeForce.BINDING_REGULATION,
            source_kind=SourceKind.LEGAL_TEXT,
            cadence=WatchCadence.WEEKLY,
            tags=["radon", "legal"],
        ),
        RuleSource(
            source_id="suva_asbestos",
            title="SUVA - Amiante",
            url="https://www.suva.ch/fr-ch/prevention/matieres-substances/amiante",
            jurisdiction_code="ch",
            publisher="SUVA",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.GUIDELINE,
            cadence=WatchCadence.WEEKLY,
            tags=["asbestos", "worksite_safety"],
        ),
        RuleSource(
            source_id="ekas_cfst_6503",
            title="CFST 6503 - Directive amiante",
            url="https://www.ekas.admin.ch/fr/directive-cfst-6503-directive-amiante-mise-a-jour",
            jurisdiction_code="ch",
            publisher="CFST/EKAS",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.DIRECTIVE,
            cadence=WatchCadence.WEEKLY,
            tags=["asbestos", "worksite_safety"],
        ),
        RuleSource(
            source_id="endk_mopec",
            title="EnDK - MoPEC",
            url="https://www.endk.ch/fr/politique-energetique/mopec",
            jurisdiction_code="ch-endk",
            publisher="EnDK",
            normative_force=NormativeForce.INTERCANTONAL_STANDARD,
            source_kind=SourceKind.STANDARD,
            cadence=WatchCadence.MONTHLY,
            tags=["energy", "intercantonal"],
        ),
        RuleSource(
            source_id="vkf_fire",
            title="VKF / AEAI",
            url="https://www.vkf.ch/",
            jurisdiction_code="std-vkf",
            publisher="VKF/AEAI",
            normative_force=NormativeForce.INTERCANTONAL_STANDARD,
            source_kind=SourceKind.STANDARD,
            cadence=WatchCadence.MONTHLY,
            tags=["fire", "safety"],
        ),
        RuleSource(
            source_id="bfs_regbl",
            title="OFS - Registre federal des batiments et des logements",
            url="https://www.delimo.bfs.admin.ch/fr/index.html",
            jurisdiction_code="ch",
            publisher="OFS",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.DATASET,
            cadence=WatchCadence.MONTHLY,
            tags=["identity", "egid", "register"],
        ),
        RuleSource(
            source_id="cadastre_rdppf",
            title="Cadastre RDPPF",
            url="https://www.cadastre.ch/fr/cadastre-rdppf",
            jurisdiction_code="ch",
            publisher="cadastre.ch / swisstopo",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.DATASET,
            cadence=WatchCadence.MONTHLY,
            tags=["cadastre", "rdppf", "planning"],
        ),
        RuleSource(
            source_id="bafu_natural_hazards",
            title="BAFU - Faire face aux dangers naturels",
            url="https://www.bafu.admin.ch/bafu/fr/home/themes/dangers-naturels/umgang-mit-naturgefahren.html",
            jurisdiction_code="ch",
            publisher="BAFU",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.GUIDELINE,
            cadence=WatchCadence.MONTHLY,
            tags=["natural_hazards", "planning", "safety"],
        ),
        RuleSource(
            source_id="bafu_groundwater_protection",
            title="BAFU - Zones de protection des eaux souterraines",
            url="https://www.bafu.admin.ch/dam/fr/sd-web/MagXxADIZu1m/grundwasserschutzzonenbeilockergesteinen%2520%283%29.pdf",
            jurisdiction_code="ch",
            publisher="BAFU",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.GUIDELINE,
            cadence=WatchCadence.MONTHLY,
            tags=["water", "groundwater", "planning"],
        ),
        RuleSource(
            source_id="bak_isos",
            title="BAK - ISOS et protection des sites",
            url="https://www.bak.admin.ch/bak/fr/home/baukultur/isos-und-ortsbildschutz.html",
            jurisdiction_code="ch",
            publisher="BAK",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.GUIDELINE,
            cadence=WatchCadence.MONTHLY,
            tags=["heritage", "isos", "planning"],
        ),
        RuleSource(
            source_id="ebgb_lhand",
            title="LHand - accessibilite des batiments",
            url="https://www.ebgb.admin.ch/fr/loi-sur-legalite-pour-les-personnes-handicapees-lhand",
            jurisdiction_code="ch",
            publisher="BFEH/EBGB",
            normative_force=NormativeForce.BINDING_LAW,
            source_kind=SourceKind.GUIDELINE,
            cadence=WatchCadence.MONTHLY,
            tags=["accessibility", "public_use", "permit"],
        ),
        RuleSource(
            source_id="minergie_label",
            title="Minergie",
            url="https://www.minergie.ch/",
            jurisdiction_code="std-minergie",
            publisher="Minergie",
            normative_force=NormativeForce.LABEL,
            source_kind=SourceKind.LABEL,
            cadence=WatchCadence.QUARTERLY,
            tags=["energy", "label"],
        ),
        RuleSource(
            source_id="vd_camac",
            title="Vaud - Permis de construire / CAMAC",
            url="https://www.vd.ch/territoire-et-construction/permis-de-construire",
            jurisdiction_code="ch-vd",
            publisher="Etat de Vaud",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.PORTAL,
            cadence=WatchCadence.DAILY,
            tags=["permit", "portal", "vaud"],
        ),
        RuleSource(
            source_id="ge_building_auth",
            title="Geneve - Demander une autorisation de construire",
            url="https://www.ge.ch/demander-autorisation-construire",
            jurisdiction_code="ch-ge",
            publisher="Etat de Geneve",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.PORTAL,
            cadence=WatchCadence.DAILY,
            tags=["permit", "portal", "geneva"],
        ),
        RuleSource(
            source_id="fr_seca",
            title="Fribourg - SeCA",
            url="https://www.fr.ch/territoire-amenagement-et-constructions/territoire/seca-presentation-du-service",
            jurisdiction_code="ch-fr",
            publisher="Etat de Fribourg",
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            source_kind=SourceKind.PORTAL,
            cadence=WatchCadence.DAILY,
            tags=["permit", "portal", "fribourg"],
        ),
        RuleSource(
            source_id="fach_guidance",
            title="FACH",
            url="https://www.fach.ch/",
            jurisdiction_code="std-fach",
            publisher="FACH",
            normative_force=NormativeForce.PRIVATE_STANDARD,
            source_kind=SourceKind.STANDARD,
            cadence=WatchCadence.QUARTERLY,
            tags=["pollutants", "diagnostic"],
        ),
        RuleSource(
            source_id="asca_guidance",
            title="ASCA / VABS",
            url="https://www.asca-vabs.ch/",
            jurisdiction_code="std-asca",
            publisher="ASCA / VABS",
            normative_force=NormativeForce.PRIVATE_STANDARD,
            source_kind=SourceKind.STANDARD,
            cadence=WatchCadence.QUARTERLY,
            tags=["asbestos", "diagnostic"],
        ),
    ]


def build_rule_templates() -> list[RuleTemplate]:
    return [
        RuleTemplate(
            code="permit_gatekeeping",
            title="Permit gatekeeping",
            summary="Construction, transformation, demolition, or sensitive interventions should flow through canton and commune permit rules.",
            jurisdiction_levels=[JurisdictionLevel.CANTONAL, JurisdictionLevel.COMMUNAL],
            source_ids=["are_lat_oat", "are_hors_zone", "vd_camac", "ge_building_auth", "fr_seca"],
            normative_force=NormativeForce.BINDING_LAW,
            domain_tags=["permit", "planning", "procedure"],
            required_project_kinds=["new_build", "renovation", "transformation", "demolition", "remediation"],
            manual_review_flags=["outside_building_zone", "protected_building", "communal_override"],
            output_requirement_codes=["permit_dossier"],
            default_procedure_codes=["cantonal_permit_review"],
            default_authority_codes=["communal_building_authority"],
            integration_targets=["permit_tracking", "permit_procedure", "control_tower"],
        ),
        RuleTemplate(
            code="suva_asbestos_notification",
            title="SUVA asbestos notification",
            summary="Asbestos-related work should surface safety, notification, and worker protection requirements.",
            jurisdiction_levels=[JurisdictionLevel.FEDERAL],
            source_ids=["suva_asbestos", "ekas_cfst_6503"],
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            domain_tags=["asbestos", "worksite_safety", "notification"],
            required_project_kinds=["renovation", "transformation", "demolition", "remediation"],
            required_pollutants=["asbestos"],
            output_requirement_codes=["asbestos_diagnostic", "worker_protection_plan", "suva_notification_requirement"],
            default_procedure_codes=["suva_asbestos_notification"],
            default_authority_codes=["suva_ch"],
            integration_targets=["regulatory_filing", "obligation", "authority_pack", "control_tower"],
        ),
        RuleTemplate(
            code="cantonal_pollutant_declaration",
            title="Cantonal pollutant declaration",
            summary="Pollutant findings should trigger a canton-aware declaration workflow with linked proof.",
            jurisdiction_levels=[JurisdictionLevel.CANTONAL],
            source_ids=["vd_camac", "ge_building_auth", "fr_seca", "bafu_pcb_joints"],
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            domain_tags=["pollutants", "declaration", "procedure"],
            required_project_kinds=["renovation", "transformation", "demolition", "remediation"],
            required_pollutants=["asbestos", "pcb", "lead", "hap", "pfas"],
            output_requirement_codes=["cantonal_declaration_requirement", "diagnostic_report"],
            default_procedure_codes=["cantonal_pollutant_declaration"],
            default_authority_codes=["vd_camac", "ge_oac", "fr_seca"],
            integration_targets=["regulatory_filing", "obligation", "authority_pack", "control_tower"],
        ),
        RuleTemplate(
            code="oled_waste_manifest",
            title="OLED waste manifest",
            summary="Controlled or special waste should generate trackable waste manifest and disposal proof requirements.",
            jurisdiction_levels=[JurisdictionLevel.FEDERAL],
            source_ids=["bafu_oled", "bafu_waste_law"],
            normative_force=NormativeForce.BINDING_REGULATION,
            domain_tags=["waste", "oled", "disposal"],
            required_project_kinds=["renovation", "transformation", "demolition", "remediation"],
            required_waste_categories=["type_e", "special"],
            output_requirement_codes=["waste_manifest_requirement", "waste_disposal_chain"],
            default_procedure_codes=["oled_waste_manifest"],
            default_authority_codes=["bafu_ch"],
            integration_targets=["regulatory_filing", "authority_pack", "proof_delivery", "control_tower"],
        ),
        RuleTemplate(
            code="radon_assessment",
            title="Radon assessment",
            summary="Radon-sensitive contexts should trigger measurement or mitigation review before declaring the dossier ready.",
            jurisdiction_levels=[JurisdictionLevel.FEDERAL],
            source_ids=["bag_radon", "bag_radon_legal"],
            normative_force=NormativeForce.BINDING_REGULATION,
            domain_tags=["radon", "health"],
            required_project_kinds=["new_build", "renovation", "transformation"],
            required_building_flags=["radon_risk"],
            output_requirement_codes=["radon_measurement_requirement"],
            default_procedure_codes=["radon_review"],
            default_authority_codes=["bag_ch"],
            integration_targets=["obligation", "authority_pack", "control_tower"],
        ),
        RuleTemplate(
            code="energy_code_review",
            title="Energy code review",
            summary="Permit-facing energy justification should align with the relevant canton and inter-cantonal model.",
            jurisdiction_levels=[JurisdictionLevel.INTERCANTONAL, JurisdictionLevel.CANTONAL],
            source_ids=["endk_mopec", "vd_camac", "ge_building_auth", "fr_seca", "minergie_label"],
            normative_force=NormativeForce.INTERCANTONAL_STANDARD,
            domain_tags=["energy", "permit"],
            required_project_kinds=["new_build", "renovation", "transformation"],
            output_requirement_codes=["energy_justification_requirement"],
            default_procedure_codes=["energy_review"],
            default_authority_codes=["endk_ch", "vd_camac", "ge_oac", "fr_seca"],
            integration_targets=["permit_tracking", "authority_pack", "control_tower"],
        ),
        RuleTemplate(
            code="fire_safety_review",
            title="Fire safety review",
            summary="Sensitive occupancies and public-facing projects should surface fire concept requirements early.",
            jurisdiction_levels=[
                JurisdictionLevel.INTERCANTONAL,
                JurisdictionLevel.CANTONAL,
                JurisdictionLevel.COMMUNAL,
            ],
            source_ids=["vkf_fire", "vd_camac", "ge_building_auth", "fr_seca"],
            normative_force=NormativeForce.INTERCANTONAL_STANDARD,
            domain_tags=["fire", "safety", "permit"],
            required_project_kinds=["new_build", "renovation", "transformation"],
            manual_review_flags=["public_facing", "special_fire_case"],
            output_requirement_codes=["fire_safety_concept_requirement"],
            default_procedure_codes=["fire_review"],
            default_authority_codes=["vkf_aeai", "communal_building_authority"],
            integration_targets=["permit_tracking", "authority_pack", "control_tower"],
        ),
        RuleTemplate(
            code="rdppf_property_restrictions_review",
            title="RDPPF and public-law restrictions review",
            summary="Permit-facing dossiers should include public-law property restrictions and canonical building identity data.",
            jurisdiction_levels=[JurisdictionLevel.FEDERAL, JurisdictionLevel.CANTONAL, JurisdictionLevel.COMMUNAL],
            source_ids=["cadastre_rdppf", "bfs_regbl", "vd_camac", "ge_building_auth", "fr_seca"],
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            domain_tags=["cadastre", "rdppf", "permit", "planning"],
            required_project_kinds=["new_build", "renovation", "transformation", "demolition", "remediation"],
            output_requirement_codes=["rdppf_extract_requirement", "official_identity_requirement"],
            default_procedure_codes=["rdppf_review"],
            default_authority_codes=["swisstopo_cadastre"],
            integration_targets=["permit_tracking", "authority_pack", "control_tower"],
        ),
        RuleTemplate(
            code="natural_hazard_review",
            title="Natural hazard review",
            summary="Projects in natural hazard contexts should surface assessment and routing requirements before submission.",
            jurisdiction_levels=[JurisdictionLevel.FEDERAL, JurisdictionLevel.CANTONAL, JurisdictionLevel.COMMUNAL],
            source_ids=["bafu_natural_hazards", "cadastre_rdppf", "vd_camac", "ge_building_auth", "fr_seca"],
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            domain_tags=["natural_hazards", "permit", "safety"],
            required_project_kinds=["new_build", "renovation", "transformation", "demolition"],
            manual_review_flags=["natural_hazard_area"],
            output_requirement_codes=["natural_hazard_assessment_requirement"],
            default_procedure_codes=["natural_hazard_review"],
            default_authority_codes=["bafu_ch", "communal_building_authority"],
            integration_targets=["permit_tracking", "authority_pack", "control_tower"],
        ),
        RuleTemplate(
            code="groundwater_protection_review",
            title="Groundwater protection review",
            summary="Projects in water protection areas should surface hydrogeologic and filing constraints early.",
            jurisdiction_levels=[JurisdictionLevel.FEDERAL, JurisdictionLevel.CANTONAL, JurisdictionLevel.COMMUNAL],
            source_ids=["bafu_groundwater_protection", "cadastre_rdppf", "vd_camac", "ge_building_auth", "fr_seca"],
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            domain_tags=["water", "groundwater", "permit"],
            required_project_kinds=["new_build", "renovation", "transformation", "remediation"],
            manual_review_flags=["groundwater_protection"],
            output_requirement_codes=["groundwater_protection_requirement"],
            default_procedure_codes=["groundwater_review"],
            default_authority_codes=["bafu_ch", "communal_building_authority"],
            integration_targets=["permit_tracking", "authority_pack", "control_tower"],
        ),
        RuleTemplate(
            code="accessibility_review",
            title="Accessibility review",
            summary="Public-facing or high-impact projects should surface accessibility compliance early in the dossier.",
            jurisdiction_levels=[JurisdictionLevel.FEDERAL, JurisdictionLevel.CANTONAL, JurisdictionLevel.COMMUNAL],
            source_ids=["ebgb_lhand", "vd_camac", "ge_building_auth", "fr_seca"],
            normative_force=NormativeForce.BINDING_LAW,
            domain_tags=["accessibility", "permit", "public_use"],
            required_project_kinds=["new_build", "renovation", "transformation"],
            manual_review_flags=["accessibility_scope"],
            output_requirement_codes=["accessibility_compliance_requirement"],
            default_procedure_codes=["accessibility_review"],
            default_authority_codes=["ebgb_ch", "communal_building_authority"],
            integration_targets=["permit_tracking", "authority_pack", "control_tower"],
        ),
        RuleTemplate(
            code="heritage_and_outside_zone_review",
            title="Heritage or outside-zone review",
            summary="Protected buildings and outside-building-zone projects must be escalated for manual jurisdiction review.",
            jurisdiction_levels=[JurisdictionLevel.FEDERAL, JurisdictionLevel.CANTONAL, JurisdictionLevel.COMMUNAL],
            source_ids=["are_hors_zone", "bak_isos", "vd_camac", "ge_building_auth", "fr_seca"],
            normative_force=NormativeForce.OFFICIAL_EXECUTION_GUIDELINE,
            domain_tags=["heritage", "outside_zone", "manual_review"],
            required_project_kinds=["new_build", "renovation", "transformation", "demolition"],
            manual_review_flags=["outside_building_zone", "protected_building"],
            output_requirement_codes=["manual_jurisdiction_review_requirement", "heritage_assessment_requirement"],
            default_procedure_codes=["manual_jurisdiction_review"],
            default_authority_codes=["bak_ch", "communal_building_authority"],
            integration_targets=["permit_tracking", "permit_procedure", "control_tower"],
        ),
    ]


def build_requirement_templates() -> list[RequirementTemplate]:
    return [
        RequirementTemplate(
            code="permit_dossier",
            title="Permit dossier",
            summary="Structured permit-ready dossier for canton or commune.",
            source_rule_codes=["permit_gatekeeping"],
            evidence_type="evidence_pack",
            responsible_role="property_manager",
            due_hint="before_submission",
            legal_basis_source_ids=["are_lat_oat", "vd_camac", "ge_building_auth", "fr_seca"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="asbestos_diagnostic",
            title="Asbestos diagnostic",
            summary="Validated asbestos diagnostic or publication linked to the building workspace.",
            source_rule_codes=["suva_asbestos_notification"],
            evidence_type="diagnostic_publication",
            responsible_role="diagnostician",
            legal_basis_source_ids=["suva_asbestos", "ekas_cfst_6503"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="worker_protection_plan",
            title="Worker protection plan",
            summary="Worker protection and confinement plan for asbestos-related works.",
            source_rule_codes=["suva_asbestos_notification"],
            evidence_type="compliance_artefact",
            responsible_role="contractor",
            legal_basis_source_ids=["ekas_cfst_6503"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="suva_notification_requirement",
            title="SUVA notification",
            summary="Notification package and timing evidence before asbestos works start.",
            source_rule_codes=["suva_asbestos_notification"],
            evidence_type="regulatory_filing",
            responsible_role="property_manager",
            due_hint="before_work_start",
            legal_basis_source_ids=["suva_asbestos", "ekas_cfst_6503"],
            integration_target="regulatory_filing",
        ),
        RequirementTemplate(
            code="cantonal_declaration_requirement",
            title="Cantonal pollutant declaration",
            summary="Canton-aware declaration output for pollutant findings.",
            source_rule_codes=["cantonal_pollutant_declaration"],
            evidence_type="regulatory_filing",
            responsible_role="property_manager",
            due_hint="before_work_start",
            legal_basis_source_ids=["vd_camac", "ge_building_auth", "fr_seca"],
            integration_target="regulatory_filing",
        ),
        RequirementTemplate(
            code="diagnostic_report",
            title="Diagnostic report",
            summary="Published or linked pollutant report used as procedural proof.",
            source_rule_codes=["cantonal_pollutant_declaration"],
            evidence_type="diagnostic_publication",
            responsible_role="diagnostician",
            legal_basis_source_ids=["bafu_pcb_joints", "fach_guidance"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="waste_manifest_requirement",
            title="Waste manifest",
            summary="OLED waste tracking output for controlled or special waste.",
            source_rule_codes=["oled_waste_manifest"],
            evidence_type="regulatory_filing",
            responsible_role="contractor",
            due_hint="before_disposal",
            legal_basis_source_ids=["bafu_oled", "bafu_waste_law"],
            integration_target="regulatory_filing",
        ),
        RequirementTemplate(
            code="waste_disposal_chain",
            title="Waste disposal chain",
            summary="Transport and disposal evidence linked to the dossier.",
            source_rule_codes=["oled_waste_manifest"],
            evidence_type="proof_delivery",
            responsible_role="contractor",
            legal_basis_source_ids=["bafu_oled", "bafu_waste_law"],
            integration_target="proof_delivery",
        ),
        RequirementTemplate(
            code="radon_measurement_requirement",
            title="Radon measurement or mitigation evidence",
            summary="Measurement, mitigation, or manual review evidence for radon-sensitive cases.",
            source_rule_codes=["radon_assessment"],
            evidence_type="compliance_artefact",
            responsible_role="property_manager",
            legal_basis_source_ids=["bag_radon", "bag_radon_legal"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="energy_justification_requirement",
            title="Energy justification",
            summary="Energy or envelope justification aligned to canton requirements.",
            source_rule_codes=["energy_code_review"],
            evidence_type="document",
            responsible_role="architect",
            legal_basis_source_ids=["endk_mopec", "minergie_label"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="fire_safety_concept_requirement",
            title="Fire safety concept",
            summary="Fire concept or equivalent safety evidence for sensitive occupancies.",
            source_rule_codes=["fire_safety_review"],
            evidence_type="document",
            responsible_role="architect",
            legal_basis_source_ids=["vkf_fire"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="rdppf_extract_requirement",
            title="RDPPF extract",
            summary="Public-law property restrictions and zoning extract linked to the permit dossier.",
            source_rule_codes=["rdppf_property_restrictions_review"],
            evidence_type="document",
            responsible_role="property_manager",
            due_hint="before_submission",
            legal_basis_source_ids=["cadastre_rdppf"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="official_identity_requirement",
            title="Official building identity",
            summary="Verified EGID and parcel identity aligned with official registers.",
            source_rule_codes=["rdppf_property_restrictions_review"],
            evidence_type="document",
            responsible_role="property_manager",
            legal_basis_source_ids=["bfs_regbl", "cadastre_rdppf"],
            integration_target="permit_tracking",
        ),
        RequirementTemplate(
            code="natural_hazard_assessment_requirement",
            title="Natural hazard assessment",
            summary="Hazard-area assessment or routing evidence for exposed sites.",
            source_rule_codes=["natural_hazard_review"],
            evidence_type="document",
            responsible_role="architect",
            legal_basis_source_ids=["bafu_natural_hazards", "cadastre_rdppf"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="groundwater_protection_requirement",
            title="Groundwater protection review",
            summary="Hydrogeologic and water-protection compliance evidence for protected areas.",
            source_rule_codes=["groundwater_protection_review"],
            evidence_type="expert_review",
            responsible_role="architect",
            legal_basis_source_ids=["bafu_groundwater_protection", "cadastre_rdppf"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="accessibility_compliance_requirement",
            title="Accessibility compliance",
            summary="Accessibility compliance evidence for public or high-impact uses.",
            source_rule_codes=["accessibility_review"],
            evidence_type="document",
            responsible_role="architect",
            legal_basis_source_ids=["ebgb_lhand"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="heritage_assessment_requirement",
            title="Heritage assessment",
            summary="Protected-building or ISOS compatibility assessment linked to the dossier.",
            source_rule_codes=["heritage_and_outside_zone_review"],
            evidence_type="expert_review",
            responsible_role="architect",
            legal_basis_source_ids=["bak_isos", "are_hors_zone"],
            integration_target="authority_pack",
        ),
        RequirementTemplate(
            code="manual_jurisdiction_review_requirement",
            title="Manual jurisdiction review",
            summary="Manual authority qualification for outside-zone or protected-building cases.",
            source_rule_codes=["heritage_and_outside_zone_review"],
            evidence_type="expert_review",
            responsible_role="property_manager",
            legal_basis_source_ids=["are_hors_zone", "bak_isos", "vd_camac", "ge_building_auth", "fr_seca"],
            integration_target="control_tower",
        ),
    ]


def build_procedure_templates() -> list[ProcedureTemplate]:
    submission_steps = [
        ProcedureStepTemplate(
            step_key="submission", title="Submission", summary="Assemble and submit the dossier.", blocking=True
        ),
        ProcedureStepTemplate(
            step_key="review", title="Review", summary="Authority reviews the dossier.", blocking=True
        ),
        ProcedureStepTemplate(
            step_key="complement_loop",
            title="Complement loop",
            summary="Handle authority requests and resubmit missing evidence.",
            blocking=True,
        ),
        ProcedureStepTemplate(
            step_key="decision", title="Decision", summary="Capture approval, rejection, or withdrawal.", blocking=True
        ),
        ProcedureStepTemplate(
            step_key="acknowledgement",
            title="Acknowledgement",
            summary="Archive acknowledgement and distribute proof.",
            blocking=False,
        ),
    ]
    return [
        ProcedureTemplate(
            code="vd_camac_permit",
            title="CAMAC permit workflow",
            summary="Vaud construction permit workflow anchored on CAMAC.",
            jurisdiction_code="ch-vd",
            authority_code="vd_camac",
            procedure_type="construction_permit",
            source_rule_codes=["permit_gatekeeping"],
            steps=submission_steps,
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="ge_building_authorization",
            title="Geneva building authorization",
            summary="Geneva construction authorization workflow.",
            jurisdiction_code="ch-ge",
            authority_code="ge_oac",
            procedure_type="construction_permit",
            source_rule_codes=["permit_gatekeeping"],
            steps=submission_steps,
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="fr_seca_permit",
            title="Fribourg SeCA permit workflow",
            summary="Fribourg permit workflow anchored on SeCA procedures.",
            jurisdiction_code="ch-fr",
            authority_code="fr_seca",
            procedure_type="construction_permit",
            source_rule_codes=["permit_gatekeeping"],
            steps=submission_steps,
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="cantonal_permit_review",
            title="Generic cantonal permit review",
            summary="Fallback permit procedure for cantons without a dedicated adapter yet.",
            jurisdiction_code="ch",
            authority_code="communal_building_authority",
            procedure_type="construction_permit",
            source_rule_codes=["permit_gatekeeping"],
            steps=submission_steps,
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="cantonal_pollutant_declaration",
            title="Cantonal pollutant declaration",
            summary="Declaration workflow for pollutant findings.",
            jurisdiction_code="ch",
            authority_code="communal_building_authority",
            procedure_type="pollutant_declaration",
            source_rule_codes=["cantonal_pollutant_declaration"],
            steps=submission_steps,
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="suva_asbestos_notification",
            title="SUVA asbestos notification",
            summary="Notify SUVA and track acknowledgement before work starts.",
            jurisdiction_code="ch",
            authority_code="suva_ch",
            procedure_type="suva_notification",
            source_rule_codes=["suva_asbestos_notification"],
            steps=[
                ProcedureStepTemplate(
                    step_key="prepare",
                    title="Prepare",
                    summary="Prepare asbestos diagnostic and worker protection plan.",
                    blocking=True,
                ),
                ProcedureStepTemplate(
                    step_key="notify",
                    title="Notify",
                    summary="Submit the SUVA notification before works start.",
                    blocking=True,
                ),
                ProcedureStepTemplate(
                    step_key="acknowledge",
                    title="Acknowledge",
                    summary="Track acknowledgement and start readiness.",
                    blocking=True,
                ),
            ],
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="oled_waste_manifest",
            title="OLED waste manifest",
            summary="Generate manifest and track disposal chain evidence.",
            jurisdiction_code="ch",
            authority_code="bafu_ch",
            procedure_type="waste_manifest",
            source_rule_codes=["oled_waste_manifest"],
            steps=[
                ProcedureStepTemplate(
                    step_key="prepare",
                    title="Prepare",
                    summary="Classify waste and assemble the disposal chain.",
                    blocking=True,
                ),
                ProcedureStepTemplate(
                    step_key="issue", title="Issue manifest", summary="Generate the OLED manifest.", blocking=True
                ),
                ProcedureStepTemplate(
                    step_key="archive",
                    title="Archive disposal proof",
                    summary="Track transport and disposal acknowledgements.",
                    blocking=False,
                ),
            ],
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="radon_review",
            title="Radon review",
            summary="Measure, review, or mitigate radon-sensitive cases.",
            jurisdiction_code="ch",
            authority_code="bag_ch",
            procedure_type="radon_review",
            source_rule_codes=["radon_assessment"],
            steps=[
                ProcedureStepTemplate(
                    step_key="measure", title="Measure", summary="Measure or review radon risk evidence.", blocking=True
                ),
                ProcedureStepTemplate(
                    step_key="decide",
                    title="Decide mitigation",
                    summary="Capture review outcome and mitigation needs.",
                    blocking=True,
                ),
            ],
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="energy_review",
            title="Energy review",
            summary="Attach energy justification to the permit-ready dossier.",
            jurisdiction_code="ch-endk",
            authority_code="endk_ch",
            procedure_type="energy_review",
            source_rule_codes=["energy_code_review"],
            steps=[
                ProcedureStepTemplate(
                    step_key="justify", title="Justify", summary="Prepare the energy justification.", blocking=True
                ),
                ProcedureStepTemplate(
                    step_key="validate",
                    title="Validate",
                    summary="Validate alignment with the cantonal path.",
                    blocking=False,
                ),
            ],
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="fire_review",
            title="Fire safety review",
            summary="Collect fire safety evidence and route sensitive cases.",
            jurisdiction_code="std-vkf",
            authority_code="vkf_aeai",
            procedure_type="fire_review",
            source_rule_codes=["fire_safety_review"],
            steps=[
                ProcedureStepTemplate(
                    step_key="concept", title="Fire concept", summary="Prepare the fire safety concept.", blocking=True
                ),
                ProcedureStepTemplate(
                    step_key="route",
                    title="Route review",
                    summary="Route to the relevant authority or reviewer.",
                    blocking=True,
                ),
            ],
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="rdppf_review",
            title="RDPPF review",
            summary="Verify public-law restrictions and official building identity before filing.",
            jurisdiction_code="ch",
            authority_code="swisstopo_cadastre",
            procedure_type="rdppf_review",
            source_rule_codes=["rdppf_property_restrictions_review"],
            steps=[
                ProcedureStepTemplate(
                    step_key="extract",
                    title="Extract",
                    summary="Collect RDPPF and official identity data.",
                    blocking=True,
                ),
                ProcedureStepTemplate(
                    step_key="qualify",
                    title="Qualify",
                    summary="Qualify public-law restrictions that affect the project.",
                    blocking=True,
                ),
            ],
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="natural_hazard_review",
            title="Natural hazard review",
            summary="Route projects affected by hazard maps through a dedicated review path.",
            jurisdiction_code="ch",
            authority_code="communal_building_authority",
            procedure_type="natural_hazard_review",
            source_rule_codes=["natural_hazard_review"],
            steps=[
                ProcedureStepTemplate(
                    step_key="screen", title="Screen", summary="Screen project against hazard context.", blocking=True
                ),
                ProcedureStepTemplate(
                    step_key="assess",
                    title="Assess",
                    summary="Collect hazard assessment or mitigation evidence.",
                    blocking=True,
                ),
            ],
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="groundwater_review",
            title="Groundwater protection review",
            summary="Route projects in groundwater protection areas through a dedicated review path.",
            jurisdiction_code="ch",
            authority_code="communal_building_authority",
            procedure_type="groundwater_review",
            source_rule_codes=["groundwater_protection_review"],
            steps=[
                ProcedureStepTemplate(
                    step_key="screen",
                    title="Screen",
                    summary="Screen project against water-protection areas.",
                    blocking=True,
                ),
                ProcedureStepTemplate(
                    step_key="assess",
                    title="Assess",
                    summary="Collect hydrogeologic or authority review evidence.",
                    blocking=True,
                ),
            ],
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="accessibility_review",
            title="Accessibility review",
            summary="Review accessibility compliance for public or high-impact uses.",
            jurisdiction_code="ch",
            authority_code="ebgb_ch",
            procedure_type="accessibility_review",
            source_rule_codes=["accessibility_review"],
            steps=[
                ProcedureStepTemplate(
                    step_key="scope",
                    title="Scope",
                    summary="Decide whether the project falls into accessibility review scope.",
                    blocking=True,
                ),
                ProcedureStepTemplate(
                    step_key="justify",
                    title="Justify",
                    summary="Collect accessibility compliance evidence.",
                    blocking=True,
                ),
            ],
            integration_target="permit_procedure",
        ),
        ProcedureTemplate(
            code="manual_jurisdiction_review",
            title="Manual jurisdiction review",
            summary="Manual escalation path for protected buildings and outside-zone cases.",
            jurisdiction_code="ch-communal",
            authority_code="communal_building_authority",
            procedure_type="manual_review",
            source_rule_codes=["heritage_and_outside_zone_review"],
            steps=[
                ProcedureStepTemplate(
                    step_key="qualify",
                    title="Qualify",
                    summary="Qualify the jurisdiction-specific constraints.",
                    blocking=True,
                ),
                ProcedureStepTemplate(
                    step_key="route",
                    title="Route",
                    summary="Route to the competent canton or commune authority.",
                    blocking=True,
                ),
            ],
            integration_target="permit_procedure",
        ),
    ]


def build_watch_plan(sources: list[RuleSource]) -> list[WatchPlan]:
    plan: list[WatchPlan] = []
    rationale_by_cadence = {
        WatchCadence.DAILY: "Portal and filing pages drift frequently and affect procedure execution.",
        WatchCadence.WEEKLY: "Core legal and execution guidance sources should be checked every week.",
        WatchCadence.MONTHLY: "Lower-volatility standards still need freshness and impact review.",
        WatchCadence.QUARTERLY: "Labels and private standards change less often but still affect dossier expectations.",
        WatchCadence.EVENT_DRIVEN: "Event-driven review should supplement the scheduled watch when official notices land.",
    }
    for source in sources:
        parser_kind = "html_portal" if source.source_kind == SourceKind.PORTAL else "structured_text"
        plan.append(
            WatchPlan(
                source_id=source.source_id,
                cadence=source.cadence,
                parser_kind=parser_kind,
                manual_review_required=True,
                rationale=rationale_by_cadence[source.cadence],
            )
        )
    return plan


def build_core_swiss_rules_enablement_pack() -> SwissRulesEnablementPack:
    jurisdictions = build_jurisdictions()
    authorities = build_authority_registry()
    sources = build_rule_sources()
    return SwissRulesEnablementPack(
        version="0.1.0-bootstrap",
        jurisdictions=jurisdictions,
        authorities=authorities,
        sources=sources,
        rule_templates=build_rule_templates(),
        requirement_templates=build_requirement_templates(),
        procedure_templates=build_procedure_templates(),
        integration_targets=build_integration_targets(),
        guardrails=build_guardrails(),
        watch_plan=build_watch_plan(sources),
    )


def snapshot_rule_source(source: RuleSource, content: str, *, captured_at: datetime | None = None) -> RuleSnapshot:
    digest = sha256(content.encode("utf-8")).hexdigest()
    excerpt = content.strip().replace("\n", " ")[:240] or None
    return RuleSnapshot(
        source_id=source.source_id,
        fetched_at=captured_at or datetime.now(UTC),
        content_hash=digest,
        excerpt=excerpt,
    )


def detect_legal_change(
    previous: RuleSnapshot,
    current: RuleSnapshot,
    *,
    impacted_rule_codes: list[str] | None = None,
) -> LegalChangeEvent | None:
    if previous.source_id != current.source_id:
        raise ValueError("Snapshots must belong to the same source")
    if previous.content_hash == current.content_hash:
        return None

    change_type = ChangeType.AMENDED_RULE
    return LegalChangeEvent(
        source_id=current.source_id,
        change_type=change_type,
        severity=ChangeSeverity.MEDIUM,
        previous_hash=previous.content_hash,
        current_hash=current.content_hash,
        impacted_rule_codes=impacted_rule_codes or [],
        notes="Source content changed and requires impact review before activation.",
    )


def create_impact_review(change_event: LegalChangeEvent, *, decision_summary: str | None = None) -> ImpactReview:
    impacted_subsystems: list[str] = []
    for code in change_event.impacted_rule_codes:
        if "permit" in code:
            impacted_subsystems.append("permit_tracking")
        if "notification" in code or "declaration" in code or "waste" in code:
            impacted_subsystems.append("regulatory_filing")
        if "review" in code:
            impacted_subsystems.append("control_tower")
    return ImpactReview(
        change_event_id=change_event.event_id,
        status=ReviewStatus.PENDING,
        decision_summary=decision_summary,
        republish_required=True,
        impacted_subsystems=_unique_preserve_order(impacted_subsystems),
    )


def _has_manual_review_flag(flag: str, building_context: BuildingContext, project_context: ProjectContext) -> bool:
    if flag == "outside_building_zone":
        return building_context.outside_building_zone
    if flag == "protected_building":
        return building_context.protected_building
    if flag == "natural_hazard_area":
        hazard_tags = {"natural_hazard_area", "flood_risk", "landslide_risk", "runoff_risk", "seismic_risk"}
        return bool(hazard_tags.intersection(building_context.special_case_tags))
    if flag == "groundwater_protection":
        water_tags = {"groundwater_protection", "water_catchment", "s1_zone", "s2_zone", "s3_zone", "zu_zone"}
        return bool(water_tags.intersection(building_context.special_case_tags))
    if flag == "accessibility_scope":
        return (
            project_context.public_facing
            or building_context.usage in {"public", "mixed_public", "school", "hospital", "administrative"}
            or "multi_family_large" in building_context.special_case_tags
        )
    if flag == "public_facing":
        return project_context.public_facing
    if flag == "communal_override":
        return "communal_override" in building_context.special_case_tags
    if flag == "special_fire_case":
        fire_tags = {"school", "hospital", "assembly_use", "industrial"}
        return bool(fire_tags.intersection(project_context.special_case_tags))
    return flag in building_context.special_case_tags or flag in project_context.special_case_tags


def _meets_required_building_flag(flag: str, building_context: BuildingContext) -> bool:
    return bool(getattr(building_context, flag, False))


def _resolve_procedure_codes(rule: RuleTemplate, building_context: BuildingContext) -> list[str]:
    if rule.code == "permit_gatekeeping":
        canton = building_context.canton.upper()
        if canton == "VD":
            return ["vd_camac_permit"]
        if canton == "GE":
            return ["ge_building_authorization"]
        if canton == "FR":
            return ["fr_seca_permit"]
        return ["cantonal_permit_review"]
    return list(rule.default_procedure_codes)


def _resolve_authority_codes(rule: RuleTemplate, building_context: BuildingContext) -> list[str]:
    if rule.code == "permit_gatekeeping":
        canton = building_context.canton.upper()
        if canton == "VD":
            return ["vd_camac"]
        if canton == "GE":
            return ["ge_oac"]
        if canton == "FR":
            return ["fr_seca"]
    if rule.code == "cantonal_pollutant_declaration":
        canton = building_context.canton.upper()
        if canton == "VD":
            return ["vd_camac"]
        if canton == "GE":
            return ["ge_oac"]
        if canton == "FR":
            return ["fr_seca"]
    return list(rule.default_authority_codes)


def evaluate_rule_applicability(
    rule: RuleTemplate,
    building_context: BuildingContext,
    project_context: ProjectContext,
) -> ApplicabilityEvaluation:
    reasons: list[str] = []
    matched_conditions: list[str] = []
    manual_review_reasons: list[str] = []

    if rule.required_project_kinds and project_context.project_kind not in rule.required_project_kinds:
        return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)

    if rule.required_pollutants:
        matched_pollutants = sorted(set(rule.required_pollutants).intersection(project_context.pollutants_detected))
        if not matched_pollutants:
            return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)
        matched_conditions.extend([f"pollutant:{pollutant}" for pollutant in matched_pollutants])
        reasons.append(f"Detected pollutants trigger {rule.title.lower()}.")

    if rule.required_waste_categories:
        matched_waste = sorted(set(rule.required_waste_categories).intersection(project_context.waste_categories))
        if not matched_waste:
            return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)
        matched_conditions.extend([f"waste:{category}" for category in matched_waste])
        reasons.append("Waste classification requires a regulated disposal path.")

    for flag in rule.required_building_flags:
        if not _meets_required_building_flag(flag, building_context):
            return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)
        matched_conditions.append(f"building:{flag}")

    if rule.code == "permit_gatekeeping":
        if not (
            project_context.requires_permit
            or project_context.touches_structure
            or project_context.involves_demolition
            or building_context.outside_building_zone
            or building_context.protected_building
        ):
            return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)
        matched_conditions.extend(
            cond
            for cond, enabled in [
                ("project:requires_permit", project_context.requires_permit),
                ("project:touches_structure", project_context.touches_structure),
                ("project:involves_demolition", project_context.involves_demolition),
                ("building:outside_building_zone", building_context.outside_building_zone),
                ("building:protected_building", building_context.protected_building),
            ]
            if enabled
        )
        reasons.append("Project characteristics indicate permit gatekeeping is needed.")

    if rule.code == "energy_code_review" and not (project_context.touches_structure or project_context.requires_permit):
        return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)

    if rule.code == "fire_safety_review" and not (
        project_context.public_facing
        or set(project_context.special_case_tags).intersection({"school", "hospital", "assembly_use", "industrial"})
    ):
        return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)

    if rule.code == "rdppf_property_restrictions_review" and not (
        project_context.requires_permit or project_context.touches_structure or project_context.involves_demolition
    ):
        return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)

    if rule.code == "natural_hazard_review" and not _has_manual_review_flag(
        "natural_hazard_area", building_context, project_context
    ):
        return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)

    if rule.code == "groundwater_protection_review" and not _has_manual_review_flag(
        "groundwater_protection", building_context, project_context
    ):
        return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)

    if rule.code == "accessibility_review" and not _has_manual_review_flag(
        "accessibility_scope", building_context, project_context
    ):
        return ApplicabilityEvaluation(rule_code=rule.code, status=ApplicabilityStatus.NOT_APPLICABLE)

    for flag in rule.manual_review_flags:
        if _has_manual_review_flag(flag, building_context, project_context):
            manual_review_reasons.append(flag)

    status = ApplicabilityStatus.MANUAL_REVIEW if manual_review_reasons else ApplicabilityStatus.APPLICABLE
    if not reasons:
        reasons.append(f"{rule.title} applies to the current building and project context.")

    return ApplicabilityEvaluation(
        rule_code=rule.code,
        status=status,
        reasons=reasons,
        matched_conditions=_unique_preserve_order(matched_conditions),
        required_requirement_codes=list(rule.output_requirement_codes),
        required_procedure_codes=_resolve_procedure_codes(rule, building_context),
        authority_codes=_resolve_authority_codes(rule, building_context),
        integration_targets=list(rule.integration_targets),
        manual_review_reasons=manual_review_reasons,
    )


def evaluate_enablement_pack(
    pack: SwissRulesEnablementPack,
    building_context: BuildingContext,
    project_context: ProjectContext,
) -> list[ApplicabilityEvaluation]:
    evaluations = [evaluate_rule_applicability(rule, building_context, project_context) for rule in pack.rule_templates]
    return [evaluation for evaluation in evaluations if evaluation.status != ApplicabilityStatus.NOT_APPLICABLE]
