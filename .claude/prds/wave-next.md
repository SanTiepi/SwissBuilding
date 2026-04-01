---
name: wave-next
description: Consolidation repo + quality fixes + roadmap features — wave post Building Life OS
status: active
created: 2026-04-01T02:10:00Z
---

# PRD: SwissBuilding Wave Next

## Executive Summary

Post Building Life OS wave. 14 features livrées, branche building-life-os, repo stable mais pollué par 192 docs/projects/ dont ~55 sont du bruit de session. Priorité: consolider le repo, fixer la qualité, puis attaquer les features roadmap faisables en code pur.

## Problem Statement

1. **Repo pollué**: 192 fichiers dans docs/projects/ dont 22 claude-* obsolètes, 30 packs tactiques périmés, 61 programmes stratégiques non indexés dans le roadmap
2. **Code quality**: 324 `except Exception` silencieux, 3 erreurs ruff, NFT brainstorm éparpillé hors roadmap
3. **Roadmap disconnecté**: Le roadmap-48-months.md existe mais les 61 programmes stratégiques (docs/projects/*-program.md) ne sont pas cross-référencés
4. **Infra gaps**: CI/CD existe mais pas de staging, pas de backups automatisés, pas de monitoring GlitchTip

## User Stories

### US-1: Consolidation (Robin comme opérateur)
**En tant que** propriétaire du repo, **je veux** un repo propre avec un seul document de roadmap consolidé, **pour que** chaque session parte d'une source de vérité unique.
- AC: ≤50 fichiers dans docs/projects/ (vs 192 aujourd'hui)
- AC: Tout le contenu NFT, vision beyond, fractal brainstorm intégré dans roadmap-48-months.md
- AC: Les 61 programmes indexés dans le roadmap avec mapping phase/gate

### US-2: Code Quality (tout développeur)
**En tant que** développeur, **je veux** zéro lint errors et des exceptions loggées, **pour que** les bugs ne soient plus silencieux.
- AC: `ruff check` = 0 errors
- AC: Les 324 `except Exception: pass` remplacés par `except Exception: logger.warning(...)`
- AC: `npm run validate` = 0 errors

### US-3: Roadmap Features (gestionnaire immobilier)
**En tant que** gestionnaire, **je veux** que les 24 layers geo.admin soient actifs sur mes bâtiments, **pour que** chaque bâtiment ait un profil géospatial complet.
- AC: Enrichissement pipeline appelle les 24 fetchers existants
- AC: GeoContextPanel frontend affiche toutes les dimensions
- AC: Score risque géospatial composite calculé

### US-4: Infrastructure (équipe ops)
**En tant que** ops, **je veux** un staging fonctionnel et des backups automatisés, **pour que** on puisse deployer en confiance.
- AC: .env.example à jour
- AC: CI/CD GitHub Actions existant et vert
- AC: Docker health checks sur tous les services (DÉJÀ FAIT)

## Functional Requirements

### F1 — Consolidation Repo (PRIORITÉ 1)
- F1.1: Archiver les 22 fichiers claude-* dans docs/archive/session-artifacts/
- F1.2: Archiver les ~30 packs tactiques datés 2026-03-25 dans docs/archive/operating-packs/
- F1.3: Intégrer le contenu NFT brainstorm dans roadmap-48-months.md section dédiée
- F1.4: Créer un index des 61 programmes → mapping vers les gates/phases du roadmap
- F1.5: Supprimer les doublons et fichiers vides
- F1.6: Mettre à jour CLAUDE.md avec les compteurs corrects

### F2 — Code Quality (PRIORITÉ 2)
- F2.1: `ruff check --fix` pour les 3 erreurs d'import
- F2.2: Remplacer les `except Exception: pass` critiques par logging (buildings.py, diagnostics.py, documents.py en priorité)
- F2.3: Audit des frontend TODOs (2 trouvés: AddressPreview.tsx:454, Cases.tsx:188)

### F3 — Geo Enrichment Activation (PRIORITÉ 3)
- F3.1: Activer les fetchers geo.admin non branchés dans enrichment/orchestrator.py
- F3.2: Persister les résultats swissBUILDINGS3D (footprint, hauteur, volume) — actuellement parsés mais pas sauvegardés
- F3.3: Créer un score risque géospatial composite (score_computers.py)
- F3.4: Enrichir le GeoContextPanel frontend avec les nouvelles dimensions

### F4 — ClimateExposureProfile Activation (PRIORITÉ 3)
- F4.1: Peupler les champs vides du modèle ClimateExposureProfile depuis les fetchers existants
- F4.2: Créer le service OpportunityWindow detection (modèle existe, zéro logique)
- F4.3: Dashboard opportunities dans Building Home

### F5 — CLAUDE.md & AGENTS.md Update (PRIORITÉ 4)
- F5.1: Mettre à jour les compteurs (292 services, 162 modèles, 252+ routes, 73 pages)
- F5.2: Documenter la décision roadmap 48 mois
- F5.3: Documenter la décision Building Credential (VC-first, SBT-optional)

## Non-Functional Requirements

- Chaque changement doit avoir des tests
- Hub files (router.py, models/__init__, schemas/__init__) = supervisor merge only
- Branches éphémères + PR, jamais push direct sur building-life-os
- Les 7150+ tests backend doivent rester verts
- Les 996 tests frontend doivent rester verts

## Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| docs/projects/ file count | 192 | ≤60 |
| ruff check errors | 3 | 0 |
| Silent except Exception (critical paths) | ~20 | 0 |
| Geo layers active in enrichment | ~6 | 24 |
| ClimateExposureProfile fields populated | 0/10 | 10/10 |
| Roadmap-programme cross-reference | none | 61 programmes indexed |

## Constraints & Assumptions

- On travaille sur la branche building-life-os (pas main/master)
- Backend tourne sur VPS, pas localhost
- Les 24 fetchers geo.admin EXISTENT déjà dans le code — c'est du wiring, pas de la création
- Le modèle ClimateExposureProfile EXISTE — il suffit de le peupler
- Le modèle OpportunityWindow EXISTE — il suffit de créer la logique de détection

## Out of Scope

- Partenariats externes (notaires, banques, assureurs) — flaggé later dans roadmap
- Données payantes (Google Places, Comparis, etc.) — flaggé later
- Mobile native app — PWA suffisant
- Blockchain/SBT deployment — VC-first approach, blockchain only if demand proven
- Import de données réelles (cadastres GE/BE/ZH) — dépend de partenariats

## Dependencies

- Les fetchers geo.admin existants dans enrichment/geo_admin_fetchers.py
- Les modèles ClimateExposureProfile et OpportunityWindow dans models/climate_exposure.py
- Le pipeline enrichment/orchestrator.py
- Le score_computers.py pour les scores composites
