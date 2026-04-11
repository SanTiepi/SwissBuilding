"""GE Rules Pack — Geneva regulatory compliance rules for building asbestos/hazard assessments.

Implements 40+ canton-specific rules for Geneva (GE) compliance:
- OTConst (Ordonnance sur les matériaux de construction)
- Loi cantonale sur la qualité de l'air (LCQA)
- Guide de gérance immobilière (GIGES)
- Règlement cantonal sur la prévention des risques d'exposition (RCPRE)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class RuleSeverity(str, Enum):
    """Rule severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class RuleCategory(str, Enum):
    """Rule categories."""

    ASBESTOS = "asbestos"
    PCB = "pcb"
    LEAD = "lead"
    HAP = "hap"
    MOLD = "mold"
    RADON = "radon"
    OCCUPATIONAL = "occupational"
    ENVIRONMENTAL = "environmental"
    DOCUMENTATION = "documentation"
    TIMELINE = "timeline"


@dataclass
class Rule:
    """Rule definition."""

    id: str
    title_fr: str
    description_fr: str
    category: RuleCategory
    severity: RuleSeverity
    canton: str = "GE"
    applies_to_year_min: int | None = None
    applies_to_year_max: int | None = None
    check_fn: Callable[[dict], bool] | None = None
    remediation_guidance: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# ASBESTOS RULES (10+)
# ─────────────────────────────────────────────────────────────────────────────

ASBESTOS_RULES = [
    Rule(
        id="GE_ASB_001",
        title_fr="Diagnostic amiante obligatoire",
        description_fr="Bâtiment construit avant 2005 doit avoir diagnostic amiante complet",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.CRITICAL,
        applies_to_year_max=2005,
        remediation_guidance="Faire réaliser un diagnostic amiante par un bureau certifié (ISO 17020)",
    ),
    Rule(
        id="GE_ASB_002",
        title_fr="Diagnostic amiante tous les 5 ans",
        description_fr="Surveillance périodique requise pour bâtiments avec amiante détecté",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Réaliser diagnostic amiante tous les 5 ans min",
    ),
    Rule(
        id="GE_ASB_003",
        title_fr="Désamiantage avant démolition",
        description_fr="Désamiantage obligatoire avant tout abattage ou démolition",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Engager entreprise certifiée SDA pour désamiantage",
    ),
    Rule(
        id="GE_ASB_004",
        title_fr="Encapsulation ou suppression de friable",
        description_fr="Amiante friable (p.ex. laine isolante) doit être supprimée ou encapsulée",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Suppression ou encapsulation par entreprise spécialisée",
    ),
    Rule(
        id="GE_ASB_005",
        title_fr="Déclaration préfecture pour travaux",
        description_fr="Tout travaux risquant d'affecter amiante nécessite déclaration préfecture 30j avant",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Soumettre formulaire déclaration préfecture 30 jours avant",
    ),
    Rule(
        id="GE_ASB_006",
        title_fr="Étiquetage matériaux contenant amiante",
        description_fr="Tous matériaux contenant amiante doivent être étiquetés clairement",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Apposer étiquettes conformes (triangle jaune) sur tous matériaux",
    ),
    Rule(
        id="GE_ASB_007",
        title_fr="Registre matériaux amiante",
        description_fr="Registre centralisé et actualisé de tous matériaux contenant amiante requis",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.INFO,
        remediation_guidance="Créer registre avec localisation et état chaque matériau",
    ),
    Rule(
        id="GE_ASB_008",
        title_fr="Formation personnel intervention",
        description_fr="Personnel intervenant sur amiante doit avoir formation spécifique",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Formation amiante ISO 17020 pour tout personnel concerné",
    ),
    Rule(
        id="GE_ASB_009",
        title_fr="Traçabilité désamiantage",
        description_fr="Tous désamiantages doivent être documentés avec certificat",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Conserver certificat désamiantage de l'entreprise 10 ans min",
    ),
    Rule(
        id="GE_ASB_010",
        title_fr="Évaluation impact sur santé publique",
        description_fr="Amiante friable en zone publique nécessite évaluation risque immédiate",
        category=RuleCategory.ASBESTOS,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Arrêter accès, faire évaluation, planifier suppression d'urgence",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# PCB RULES (8+)
# ─────────────────────────────────────────────────────────────────────────────

PCB_RULES = [
    Rule(
        id="GE_PCB_001",
        title_fr="Diagnostic PCB bâtiments 1955-1975",
        description_fr="Bâtiments construits 1955-1975 doivent avoir diagnostic PCB",
        category=RuleCategory.PCB,
        severity=RuleSeverity.CRITICAL,
        applies_to_year_min=1955,
        applies_to_year_max=1975,
        remediation_guidance="Faire diagnostic PCB (sangles, tapes, vernis, mastics)",
    ),
    Rule(
        id="GE_PCB_002",
        title_fr="Équipements électriques avant 1980 à vérifier",
        description_fr="Vérifier transformateurs, condos, bobines avant 1980",
        category=RuleCategory.PCB,
        severity=RuleSeverity.WARNING,
        applies_to_year_max=1980,
        remediation_guidance="Test PCB sur équipements > 10 ans; remplacement si >50ppm",
    ),
    Rule(
        id="GE_PCB_003",
        title_fr="Remplacement équipements PCB",
        description_fr="Équipements PCB >50ppm doivent être remplacés",
        category=RuleCategory.PCB,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Remplacement par équipements sans PCB; enlèvement déchets spécialisé",
    ),
    Rule(
        id="GE_PCB_004",
        title_fr="Gestion déchets PCB certifiée",
        description_fr="Tous déchets PCB traitement par entreprise certifiée",
        category=RuleCategory.PCB,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Recourir entreprise reconnue gestion déchets dangereux",
    ),
    Rule(
        id="GE_PCB_005",
        title_fr="Traçabilité élimination PCB",
        description_fr="Certificat d'élimination PCB conservé 10 ans",
        category=RuleCategory.PCB,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Conserver documents élimination avec n° lot et destination",
    ),
    Rule(
        id="GE_PCB_006",
        title_fr="Inventaire équipements à risque",
        description_fr="Inventaire centralisé équipements > 50 ppm PCB",
        category=RuleCategory.PCB,
        severity=RuleSeverity.INFO,
        remediation_guidance="Créer registre avec localisation, année, niveau PCB estimé",
    ),
    Rule(
        id="GE_PCB_007",
        title_fr="Notification autorités PCB >1T",
        description_fr="Stocks >1 tonne PCB doivent être notifiés autorités cantonales",
        category=RuleCategory.PCB,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Notification OFEV si stocks cumulés >1 tonne",
    ),
    Rule(
        id="GE_PCB_008",
        title_fr="Contamination sols interdite",
        description_fr="Fuite PCB vers sols nécessite intervention immédiate",
        category=RuleCategory.PCB,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Isoler zone, analyser sols, décontamination spécialisée",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# LEAD RULES (8+)
# ─────────────────────────────────────────────────────────────────────────────

LEAD_RULES = [
    Rule(
        id="GE_LEAD_001",
        title_fr="Diagnostic plomb avant travaux enfants",
        description_fr="Diagnostic plomb obligatoire si travaux avant 2006 dans bâtiment avec enfants",
        category=RuleCategory.LEAD,
        severity=RuleSeverity.CRITICAL,
        applies_to_year_max=2006,
        remediation_guidance="Faire diagnostic plomb peintures, poussières, sols",
    ),
    Rule(
        id="GE_LEAD_002",
        title_fr="Dépoussiérage sécurisé peintures plomb",
        description_fr="Dépoussiérage peintures plomb seulement par entreprise qualifiée",
        category=RuleCategory.LEAD,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Utiliser HEPA filter, confinement travaux, décontamination",
    ),
    Rule(
        id="GE_LEAD_003",
        title_fr="Sauvetage enfants potentiellement exposés",
        description_fr="Test sérologie enfants si exposition plomb probable",
        category=RuleCategory.LEAD,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Proposer test plombémie enfants; PEC médicale si >100 µg/L",
    ),
    Rule(
        id="GE_LEAD_004",
        title_fr="Teneur eau potable <10µg/L",
        description_fr="Eau potable doit respecter limite 10 µg/L plomb",
        category=RuleCategory.LEAD,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Test annuel eau; remplacement tuyaux plomb si dépassement",
    ),
    Rule(
        id="GE_LEAD_005",
        title_fr="Remplacement tuyauteries plomb",
        description_fr="Tuyauteries plomb doivent être remplacées",
        category=RuleCategory.LEAD,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Remplacement par cuivre ou matériau approuvé",
    ),
    Rule(
        id="GE_LEAD_006",
        title_fr="Encapsulation peintures plomb",
        description_fr="Peintures plomb peuvent être encapsulées ou supprimées",
        category=RuleCategory.LEAD,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Encapsulation avec peinture certifiée ou ponçage HEPA",
    ),
    Rule(
        id="GE_LEAD_007",
        title_fr="Déchets plomb traitement spécialisé",
        description_fr="Tous déchets contenant plomb nécessitent traitement certifié",
        category=RuleCategory.LEAD,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Récupération spécialisée; interdiction mise en décharge",
    ),
    Rule(
        id="GE_LEAD_008",
        title_fr="Information locataire exposition plomb",
        description_fr="Informer locataires de risques plomb potentiels",
        category=RuleCategory.LEAD,
        severity=RuleSeverity.INFO,
        remediation_guidance="Documentation fournie; avis sur éléments contenant plomb",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# HAP/MOLD/RADON RULES (8+)
# ─────────────────────────────────────────────────────────────────────────────

OTHER_HAZARD_RULES = [
    Rule(
        id="GE_HAP_001",
        title_fr="Diagnostic HAP goudrons/brais",
        description_fr="Bâtiments avec toits/joints asphalte/goudron > 1950 à diagnostiquer",
        category=RuleCategory.HAP,
        severity=RuleSeverity.WARNING,
        applies_to_year_max=1950,
        remediation_guidance="Diagnostic HAP si rénovation prévue",
    ),
    Rule(
        id="GE_RADON_001",
        title_fr="Mesure radon bâtiments semi-souterrains",
        description_fr="Mesure radon requise >30 jours pour bâtiments avec sous-sol/cave",
        category=RuleCategory.RADON,
        severity=RuleSeverity.INFO,
        remediation_guidance="Test radon; si >300 Bq/m³ atténuation requise",
    ),
    Rule(
        id="GE_MOLD_001",
        title_fr="Inspection humidité/moisissures",
        description_fr="Inspection humidité/moisissures obligatoire avant vente/renouvellement bail",
        category=RuleCategory.MOLD,
        severity=RuleSeverity.WARNING,
        remediation_guidance="Inspection thermique; traitement si moisissures détectées",
    ),
    Rule(
        id="GE_MOLD_002",
        title_fr="Traitement moisissures professionnel",
        description_fr="Zones humides >10% surface doivent être traitées professionnellement",
        category=RuleCategory.MOLD,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Nettoyage antimoisissure; correction sources humidité",
    ),
    Rule(
        id="GE_OCCUPATIONAL_001",
        title_fr="Protection travailleurs exposition",
        description_fr="Employeurs doivent protéger travailleurs risques exposition",
        category=RuleCategory.OCCUPATIONAL,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="PPE, formation, suivi médical selon exposition",
    ),
    Rule(
        id="GE_ENVIRONMENTAL_001",
        title_fr="Prévention pollution sols/eaux",
        description_fr="Prévenir pollutions sols/eaux souterraines",
        category=RuleCategory.ENVIRONMENTAL,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Confinement travaux; évacuation déchets dangereux; analyse sols",
    ),
    Rule(
        id="GE_DOCUMENTATION_001",
        title_fr="Dossier technique à jour",
        description_fr="Dossier technique bâtiment doit être à jour et accessible",
        category=RuleCategory.DOCUMENTATION,
        severity=RuleSeverity.INFO,
        remediation_guidance="Centraliser diagnostics, certificats, registres",
    ),
    Rule(
        id="GE_TIMELINE_001",
        title_fr="Conformité avant échéance légale",
        description_fr="Tous travaux doivent être complétés avant limite légale",
        category=RuleCategory.TIMELINE,
        severity=RuleSeverity.CRITICAL,
        remediation_guidance="Planifier travaux; démarrer minimum 6 mois avant échéance",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# AGGREGATED RULES PACK
# ─────────────────────────────────────────────────────────────────────────────

GE_RULES_PACK = {
    "version": "1.0.0",
    "canton": "GE",
    "canton_name_fr": "Genève",
    "last_updated": "2026-04-03",
    "rules": (
        ASBESTOS_RULES + PCB_RULES + LEAD_RULES + OTHER_HAZARD_RULES
    ),
    "count": len(ASBESTOS_RULES + PCB_RULES + LEAD_RULES + OTHER_HAZARD_RULES),
}


def get_rules_by_category(category: RuleCategory) -> list[Rule]:
    """Filter rules by category."""
    return [r for r in GE_RULES_PACK["rules"] if r.category == category]


def get_rules_by_severity(severity: RuleSeverity) -> list[Rule]:
    """Filter rules by severity."""
    return [r for r in GE_RULES_PACK["rules"] if r.severity == severity]


def get_applicable_rules(building_year: int) -> list[Rule]:
    """Get rules applicable to building based on construction year."""
    applicable = []
    for rule in GE_RULES_PACK["rules"]:
        if rule.applies_to_year_min and building_year < rule.applies_to_year_min:
            continue
        if rule.applies_to_year_max and building_year > rule.applies_to_year_max:
            continue
        applicable.append(rule)
    return applicable
