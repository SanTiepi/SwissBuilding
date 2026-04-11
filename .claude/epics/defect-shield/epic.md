---
name: defect-shield
status: in-progress
created: 2026-04-01T02:32:00Z
updated: 2026-04-01T02:32:00Z
progress: 0%
prd: .claude/prds/defect-shield.md
github: (will be set on sync)
---

# Epic: DefectShield — Défauts construction, deadlines & notifications

## Overview

Module complet pour le calcul des délais de notification de défauts (art. 367 al. 1bis CO, 60 jours). Model + service + alertes + lettre PDF + API + frontend widget.

## Architecture Decisions

- Nouveau modèle `DefectTimeline` (pas de réutilisation d'un modèle existant — c'est un concept nouveau)
- Service standalone `defect_timeline_service.py` (calcul pur, pas de dépendance lourde)
- Alertes via le système de notification existant
- PDF via Gotenberg (déjà dans le stack)
- Frontend: widget dans OverviewTab de Building Home

## Task Breakdown

| # | Task | Parallel | Effort |
|---|------|----------|--------|
| 001 | Model + Schema + Migration | ✅ | S |
| 002 | Service calcul timeline | ❌ (needs 001) | M |
| 003 | Service alertes + notification integration | ❌ (needs 002) | M |
| 004 | API endpoints (4 routes) | ❌ (needs 002) | S |
| 005 | Lettre notification PDF (Gotenberg) | ✅ with 004 | M |
| 006 | Frontend widget + badge | ❌ (needs 004) | M |
| 007 | Tests exhaustifs (edge cases) | ✅ with all | M |

## Dependencies
- diagnostic_service, notification_service, Gotenberg
- Building model (building_id FK)

## Estimated Effort
- Total: ~20h
- Critical path: 001→002→004→006
