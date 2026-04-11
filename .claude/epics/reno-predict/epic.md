---
name: reno-predict
status: in-progress
created: 2026-04-01T02:32:00Z
updated: 2026-04-01T02:32:00Z
progress: 0%
prd: .claude/prds/reno-predict.md
github: (will be set on sync)
---

# Epic: RénoPredict — Estimation coûts remédiation polluants

## Overview

Module estimation automatique des coûts de remédiation. Table de référence (prix/m²) + coefficients cantonaux/accessibilité + fourchette min/médian/max + breakdown postes. MVP sans ML.

## Architecture Decisions

- Table de référence en base (seed data, extensible sans code change)
- Service standalone `cost_predictor_service.py` (lookup + calcul)
- Réutilise les types polluants et matériaux existants dans constants.py
- Frontend: bouton sur DiagnosticView, modal résultat
- Pas de nouveau modèle lourd — une seule table `RemediationCostReference`

## Task Breakdown

| # | Task | Parallel | Effort |
|---|------|----------|--------|
| 001 | Model RemediationCostReference + seed data | ✅ | M |
| 002 | Service cost_predictor | ❌ (needs 001) | M |
| 003 | API endpoint POST /predict/cost | ❌ (needs 002) | S |
| 004 | Frontend bouton + modal estimation | ❌ (needs 003) | M |
| 005 | Export PDF estimation | ✅ with 004 | S |
| 006 | Tests (edge cases + fourchettes) | ✅ with all | M |

## Dependencies
- diagnostic_service (lien samples), compliance_engine (seuils)
- constants.py (types polluants, matériaux)
- Gotenberg (PDF)

## Estimated Effort
- Total: ~16h
- Critical path: 001→002→003→004
