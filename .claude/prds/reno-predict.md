---
name: reno-predict
description: Module RénoPredict — estimation automatique des coûts de remédiation polluants (fourchette CHF, délai, complexité)
status: active
created: 2026-04-01T02:30:00Z
---

# PRD: RénoPredict

## Executive Summary

Un propriétaire qui découvre de l'amiante attend 4 semaines pour un devis. RénoPredict donne une fourchette de coût en 2 secondes basée sur: type de polluant, matériau, surface, état, canton, accessibilité. MVP avec table de référence (prix/m² marché suisse), ML quand les données Batiscan seront disponibles.

## Problem Statement

Après un diagnostic polluant positif, le propriétaire est dans le flou: combien ça va coûter? Quand? Quelle complexité? Il doit attendre 2-4 semaines pour un devis d'entreprise spécialisée. Pendant ce temps, il ne peut pas budgéter, ne peut pas décider, et parfois perd des fenêtres d'opportunité (subventions, fin de bail).

## User Stories

### US-1: Estimation rapide
**En tant que** gestionnaire immobilier, **je veux** obtenir une fourchette de coût immédiate après un diagnostic positif, **pour que** je puisse budgéter et prendre une décision sans attendre 4 semaines.
- AC: Input = polluant + matériau + surface + état + canton + accessibilité
- AC: Output = fourchette CHF (min/médian/max) + délai estimé + complexité
- AC: Temps de réponse < 2 secondes

### US-2: Breakdown détaillé
**En tant que** gestionnaire, **je veux** voir le détail de l'estimation (dépose, traitement, analyses, remise en état), **pour que** je puisse expliquer le budget à mon mandant.
- AC: Breakdown en 4-6 postes avec pourcentages
- AC: Explications en langage clair

### US-3: Comparaison multi-scénarios
**En tant que** gestionnaire, **je veux** comparer les coûts pour différentes options, **pour que** je choisisse l'approche optimale.
- AC: "Encapsulation vs dépose complète" avec coûts comparés
- AC: "Maintenant vs dans 2 ans" avec inflation estimée

### US-4: Lien avec diagnostics existants
**En tant que** gestionnaire, **je veux** que l'estimation se pré-remplisse depuis le diagnostic, **pour que** je n'aie pas à ressaisir.
- AC: Depuis un diagnostic avec samples, le formulaire est pré-rempli
- AC: Bouton "Estimer le coût" directement sur la page diagnostic

## Functional Requirements

### Backend
- F1: Table de référence `remediation_cost_reference` — prix/m² par combinaison (polluant × matériau × état × méthode)
- F2: Service `cost_predictor_service.py`:
  - Lookup dans la table de référence
  - Ajustement par canton (coefficient régional: VD=1.0, GE=1.15, ZH=1.10, VS=0.95)
  - Ajustement par accessibilité (facile=1.0, difficile=1.3, très difficile=1.6)
  - Calcul fourchette: min=0.7×médian, max=1.4×médian
  - Estimation délai (jours) et complexité (simple/moyenne/complexe)
- F3: Seed data `seed_cost_references.py` — table de référence initiale basée sur moyennes marché suisse:
  - Amiante flocage: 150-350 CHF/m² (dépose)
  - Amiante dalles vinyle: 50-120 CHF/m² (dépose)
  - Amiante joints: 80-200 CHF/m² (dépose)
  - PCB joints: 100-250 CHF/m² (dépose)
  - Plomb peinture: 60-150 CHF/m² (décapage)
  - HAP: 80-200 CHF/m² (dépose)
  - Radon: 5000-15000 CHF forfait (ventilation)
- F4: API endpoint: `POST /api/predict/cost` — input schema, output fourchette + breakdown
- F5: Breakdown postes: dépose (40-50%), traitement déchets (15-25%), analyses contrôle (5-10%), remise en état (20-30%), frais généraux (5-10%)

### Frontend
- F6: Bouton "Estimer le coût" sur DiagnosticView quand samples positifs
- F7: Modal/panel avec formulaire pré-rempli + résultat
- F8: Affichage fourchette (barre min/médian/max)
- F9: Breakdown en camembert ou barres
- F10: Export PDF de l'estimation

## Non-Functional Requirements
- Temps de réponse < 2 secondes
- Table de référence extensible (nouvelles entrées sans code change)
- Pas de nouvelle dépendance
- Résultats marqués "estimation indicative" (disclaimer légal)

## Success Criteria
- Estimation disponible en <2 secondes
- Fourchette dans ±30% du devis réel (à valider avec données Batiscan)
- 100% des combinaisons polluant×matériau courantes couvertes

## Constraints & Assumptions
- MVP = table de référence statique (pas de ML)
- Prix basés sur moyennes marché suisse 2024-2025
- Coefficient cantonal simplifié (4 cantons: VD, GE, ZH, VS)
- Disclaimer: "Estimation indicative, le devis final peut varier"
- ML training prévu quand Robin fournira les données historiques Batiscan

## Out of Scope
- ML model training (v2, quand données disponibles)
- Intégration avec entreprises de remédiation (v2)
- Prix temps réel (marché dynamique)
- Coûts indirects (perte de loyer pendant travaux, relogement)

## Dependencies
- diagnostic_service (lien avec diagnostics existants)
- sample model (type polluant, matériau, résultats)
- Gotenberg (export PDF estimation)
- compliance_engine (seuils réglementaires pour déterminer si intervention requise)
