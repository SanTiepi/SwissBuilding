"""Demo Path service — guided demo orchestrator for market conviction.

Generates scenario-based walkthroughs tailored to different persona roles,
referencing real seed buildings and actual API endpoints.
"""

from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.demo_path import DemoScenarioResult, DemoStep

logger = logging.getLogger(__name__)

ScenarioType = Literal["property_manager", "authority", "insurer", "diagnostician"]

# ---------------------------------------------------------------------------
# Scenario definitions — static, no DB dependency for the scenario structure.
# Steps reference seed building addresses so the demo can point to real data.
# ---------------------------------------------------------------------------

_SCENARIOS: dict[ScenarioType, dict] = {
    "property_manager": {
        "title": "Gerance multi-immeubles",
        "description": "Parcours type pour un gestionnaire de portefeuille immobilier: vue completude, blocages, actions prioritaires.",
        "icon": "building",
        "steps": [
            DemoStep(
                order=1,
                title="Vue portefeuille",
                description="Visualisez l'etat de sante global de votre parc immobilier en un coup d'oeil.",
                api_endpoint="/api/portfolio/summary",
                expected_insight="Score de completude moyen du portefeuille et nombre de batiments en alerte.",
                page_path="/portfolio",
                cta_label="Ouvrir le portfolio",
            ),
            DemoStep(
                order=2,
                title="Triage prioritaire",
                description="Identifiez les batiments qui necessitent une action immediate grace au triage automatique.",
                api_endpoint="/api/portfolio-triage/triage",
                expected_insight="Classement des batiments par urgence: blocages reglementaires, preuves manquantes.",
                page_path="/portfolio-triage",
                cta_label="Voir le triage",
            ),
            DemoStep(
                order=3,
                title="Fiche batiment enrichie",
                description="Explorez le dossier complet d'un batiment: identite, diagnostics, preuves, confiance.",
                api_endpoint="/api/buildings/{id}",
                expected_insight="Grade passeport, couverture polluants, score de confiance du batiment.",
                page_path="/buildings",
                cta_label="Explorer un batiment",
            ),
            DemoStep(
                order=4,
                title="Carte instantanee (5 questions)",
                description="Repondez aux 5 questions cles: que sait-on, quels risques, quoi bloque, quoi faire, quoi reutiliser.",
                api_endpoint="/api/buildings/{id}/instant-card",
                expected_insight="Structure decision-grade en 5 sections avec preuves et actions concretes.",
                page_path="/buildings",
                cta_label="Voir la carte instantanee",
            ),
            DemoStep(
                order=5,
                title="Passeport batiment",
                description="Consultez le passeport unifie: grade A-F, couverture preuves, contradictions, zones aveugles.",
                api_endpoint="/api/buildings/{id}/passport",
                expected_insight="Grade passeport avec detail par categorie et tendance d'evolution.",
                page_path="/buildings",
                cta_label="Consulter le passeport",
            ),
            DemoStep(
                order=6,
                title="Actions et campagnes",
                description="Gerez les actions correctives et lancez des campagnes de mise a jour documentaire.",
                api_endpoint="/api/actions",
                expected_insight="Liste d'actions priorisees avec statut et lien aux preuves.",
                page_path="/actions",
                cta_label="Gerer les actions",
            ),
            DemoStep(
                order=7,
                title="Export dossier",
                description="Generez un dossier complet pour un audit ou une transaction en quelques clics.",
                api_endpoint="/api/exports",
                expected_insight="Pack export avec toutes les preuves, diagnostics et rapports inclus.",
                page_path="/exports",
                cta_label="Exporter un dossier",
            ),
        ],
    },
    "authority": {
        "title": "Autorite cantonale / communale",
        "description": "Parcours type pour une autorite: verification conformite, suivi procedures, packs reglementaires.",
        "icon": "shield",
        "steps": [
            DemoStep(
                order=1,
                title="Tableau de bord conformite",
                description="Vue consolidee des batiments sous votre juridiction et leur etat de conformite.",
                api_endpoint="/api/portfolio/summary",
                expected_insight="Nombre de batiments conformes vs non-conformes dans la juridiction.",
                page_path="/control-tower",
                cta_label="Ouvrir le tableau de bord",
            ),
            DemoStep(
                order=2,
                title="Packs autorite",
                description="Consultez les packs de preuves prepares pour soumission aux autorites.",
                api_endpoint="/api/authority-packs",
                expected_insight="Packs prets a soumettre avec statut de completude et hash de verification.",
                page_path="/authority-packs",
                cta_label="Voir les packs",
            ),
            DemoStep(
                order=3,
                title="Suivi des procedures",
                description="Suivez l'avancement des procedures de permis et d'autorisation.",
                api_endpoint="/api/buildings/{id}/permit-procedures",
                expected_insight="Etapes de procedure avec delais, responsables et documents requis.",
                page_path="/admin/procedures",
                cta_label="Suivre les procedures",
            ),
            DemoStep(
                order=4,
                title="Carte de risques polluants",
                description="Visualisez la cartographie des risques polluants sur votre territoire.",
                api_endpoint="/api/pollutant-map",
                expected_insight="Repartition geographique des risques amiante, PCB, plomb, HAP, radon, PFAS.",
                page_path="/map",
                cta_label="Explorer la carte",
            ),
            DemoStep(
                order=5,
                title="Verification de preuve",
                description="Verifiez la chaine de preuve et la provenance des donnees d'un batiment.",
                api_endpoint="/api/buildings/{id}/evidence-chain",
                expected_insight="Chaine de provenance complete avec horodatage et hash d'integrite.",
                page_path="/buildings",
                cta_label="Verifier les preuves",
            ),
        ],
    },
    "insurer": {
        "title": "Assureur immobilier",
        "description": "Parcours type pour un assureur: evaluation risques, impact assurance, readiness transactionnel.",
        "icon": "shield-check",
        "steps": [
            DemoStep(
                order=1,
                title="Apercu adresse instantane",
                description="Entrez une adresse et obtenez un profil de risque complet en 10 secondes.",
                api_endpoint="/api/address-preview",
                expected_insight="Score environnemental, risques polluants predits, grade intelligence batiment.",
                page_path="/address-preview",
                cta_label="Tester une adresse",
            ),
            DemoStep(
                order=2,
                title="Evaluation risque assurance",
                description="Consultez l'evaluation automatique du risque pour le calcul de prime.",
                api_endpoint="/api/buildings/{id}/insurance-risk",
                expected_insight="Tier de risque, multiplicateur de prime, resume des facteurs.",
                page_path="/buildings",
                cta_label="Evaluer le risque",
            ),
            DemoStep(
                order=3,
                title="Readiness transactionnel",
                description="Verifiez si un batiment est pret pour une transaction (vente, assurance, financement, bail).",
                api_endpoint="/api/buildings/{id}/transaction-readiness",
                expected_insight="Score readiness par type de transaction avec blocages identifies.",
                page_path="/buildings",
                cta_label="Verifier la readiness",
            ),
            DemoStep(
                order=4,
                title="Due diligence automatisee",
                description="Lancez une due diligence complete sur un actif immobilier.",
                api_endpoint="/api/buildings/{id}/due-diligence",
                expected_insight="Rapport due diligence avec scores, risques et recommandations.",
                page_path="/buildings",
                cta_label="Lancer la due diligence",
            ),
            DemoStep(
                order=5,
                title="Comparaison multi-batiments",
                description="Comparez plusieurs batiments sur tous les axes: passeport, confiance, completude.",
                api_endpoint="/api/buildings/compare",
                expected_insight="Tableau comparatif avec grades, scores et ecarts par axe.",
                page_path="/comparison",
                cta_label="Comparer des batiments",
            ),
        ],
    },
    "diagnostician": {
        "title": "Diagnostiqueur polluants",
        "description": "Parcours type pour un diagnostiqueur: missions, rapports, preuves, retour terrain.",
        "icon": "microscope",
        "steps": [
            DemoStep(
                order=1,
                title="Mes batiments assignes",
                description="Retrouvez tous les batiments pour lesquels vous avez un mandat de diagnostic.",
                api_endpoint="/api/buildings",
                expected_insight="Liste filtree des batiments avec etat du diagnostic et actions en attente.",
                page_path="/buildings",
                cta_label="Voir mes batiments",
            ),
            DemoStep(
                order=2,
                title="Explorateur de batiment",
                description="Naviguez dans la structure du batiment: zones, elements, materiaux, echantillons.",
                api_endpoint="/api/buildings/{id}/zones",
                expected_insight="Arborescence complete zone/element/materiau avec statut diagnostic.",
                page_path="/buildings",
                cta_label="Explorer la structure",
            ),
            DemoStep(
                order=3,
                title="Integration diagnostic",
                description="Importez les resultats de diagnostic et liez-les aux preuves documentaires.",
                api_endpoint="/api/buildings/{id}/diagnostics",
                expected_insight="Diagnostic integre avec echantillons, seuils et conclusions.",
                page_path="/buildings",
                cta_label="Integrer un diagnostic",
            ),
            DemoStep(
                order=4,
                title="Observations terrain",
                description="Enregistrez vos observations de terrain avec photos et geolocalisation.",
                api_endpoint="/api/buildings/{id}/field-observations",
                expected_insight="Observations liees aux zones avec preuves visuelles.",
                page_path="/buildings",
                cta_label="Saisir des observations",
            ),
            DemoStep(
                order=5,
                title="Publication du rapport",
                description="Publiez le rapport de diagnostic et declenchez les workflows de validation.",
                api_endpoint="/api/buildings/{id}/diagnostic-publications",
                expected_insight="Rapport publie avec statut de revue et horodatage de publication.",
                page_path="/buildings",
                cta_label="Publier le rapport",
            ),
            DemoStep(
                order=6,
                title="Simulateur d'intervention",
                description="Simulez l'impact d'interventions planifiees sur le grade et le risque.",
                api_endpoint="/api/buildings/{id}/simulate-intervention",
                expected_insight="Projection du grade apres intervention avec delta de risque.",
                page_path="/buildings",
                cta_label="Simuler une intervention",
            ),
        ],
    },
}

AVAILABLE_SCENARIOS: list[ScenarioType] = list(_SCENARIOS.keys())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def list_demo_scenarios(
    db: AsyncSession,
) -> list[DemoScenarioResult]:
    """Return lightweight list of available demo scenarios."""
    results: list[DemoScenarioResult] = []
    for code, data in _SCENARIOS.items():
        results.append(
            DemoScenarioResult(
                scenario_type=code,
                title=data["title"],
                description=data["description"],
                icon=data["icon"],
                step_count=len(data["steps"]),
                steps=data["steps"],
            )
        )
    return results


async def get_demo_scenario(
    db: AsyncSession,
    scenario_type: str,
) -> DemoScenarioResult | None:
    """Return a specific demo scenario with all its steps."""
    data = _SCENARIOS.get(scenario_type)  # type: ignore[arg-type]
    if data is None:
        return None
    return DemoScenarioResult(
        scenario_type=scenario_type,
        title=data["title"],
        description=data["description"],
        icon=data["icon"],
        step_count=len(data["steps"]),
        steps=data["steps"],
    )
