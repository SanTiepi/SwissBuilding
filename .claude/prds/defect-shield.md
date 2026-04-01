---
name: defect-shield
description: Module DefectShield — calcul automatique des délais de notification de défauts (art. 367 al. 1bis CO, 60 jours depuis 01.01.2026)
status: active
created: 2026-04-01T02:30:00Z
---

# PRD: DefectShield

## Executive Summary

Depuis le 1er janvier 2026, l'art. 367 al. 1bis CO donne 60 jours (au lieu de 7-10) aux propriétaires pour notifier les défauts de construction. Nouveau droit de rectification gratuite pour biens neufs (<2 ans). La plupart des régies ne connaissent pas ce changement. BatiConnect calcule automatiquement les deadlines, génère des alertes et produit des lettres de notification conformes — en 1 clic vs CHF 300+/h chez un avocat.

## Problem Statement

Les propriétaires et régies perdent leurs droits par méconnaissance des délais légaux. Un défaut non notifié dans les 60 jours = perte du droit de garantie. Le coût d'un avocat pour calculer les délais et rédiger une notification est de CHF 300-500+/h. Aucun outil ne fait ce calcul automatiquement dans le contexte du bâtiment.

## User Stories

### US-1: Calcul timeline défaut
**En tant que** gestionnaire immobilier, **je veux** entrer la date de découverte d'un défaut et obtenir automatiquement la deadline de notification, **pour que** je ne perde jamais un droit de garantie.
- AC: Input = date découverte + type défaut + date achat → Output = deadline 60j, garantie neuf applicable?, prescription
- AC: Calcul correct pour art. 367 al. 1bis CO (60 jours calendaires)
- AC: Détection automatique bien neuf <2 ans (droit rectification gratuite)

### US-2: Alertes proactives
**En tant que** gestionnaire, **je veux** recevoir des alertes avant l'expiration des délais, **pour que** je puisse agir à temps.
- AC: Alertes à 45j, 30j, 15j, 7j avant expiration
- AC: Badge rouge dans le dashboard bâtiment quand deadline approche
- AC: Notification intégrée au système existant (NotificationBell)

### US-3: Lettre de notification
**En tant que** gestionnaire, **je veux** générer une lettre de notification conforme en 1 clic, **pour que** la notification soit juridiquement valide sans avocat.
- AC: Template PDF avec: destinataire, description défaut, base légale, délai, demande
- AC: Personnalisable (texte libre additionnel)
- AC: Téléchargeable en PDF

### US-4: Intégration diagnostics existants
**En tant que** gestionnaire, **je veux** que DefectShield se branche sur les diagnostics déjà dans le système, **pour que** je n'aie pas à ressaisir les informations.
- AC: Un diagnostic existant peut générer un timeline de défaut
- AC: Les polluants détectés = défauts potentiels avec timeline auto

## Functional Requirements

### Backend
- F1: Modèle `DefectTimeline` — building_id, defect_type, discovery_date, purchase_date, notification_deadline, guarantee_type (standard/new_build), prescription_date, status (active/notified/expired/resolved)
- F2: Service `defect_timeline_service.py` — calcul deadlines (60j CO, 2 ans neuf, prescriptions cantonales)
- F3: Service `defect_alert_service.py` — génération alertes proactives (45/30/15/7j)
- F4: Service `defect_notification_generator.py` — génération lettre PDF (Gotenberg)
- F5: API endpoints:
  - `POST /api/defects/timeline` — créer un timeline
  - `GET /api/defects/timeline/{building_id}` — lister les timelines d'un bâtiment
  - `GET /api/defects/alerts` — alertes actives (cross-building)
  - `POST /api/defects/notification/{timeline_id}` — générer lettre PDF
- F6: Integration avec diagnostic_service — lien défaut ↔ diagnostic

### Frontend
- F7: Widget "Échéances défauts" dans Building Home (OverviewTab ou nouveau tab)
- F8: Badge rouge/orange sur bâtiment quand deadline <30j
- F9: Formulaire création défaut (date, type, description)
- F10: Bouton "Générer notification" → PDF téléchargeable
- F11: Timeline visuelle des défauts avec statuts

## Non-Functional Requirements
- Calculs conformes au droit suisse (CO art. 367, 368, 371)
- Tests edge cases: jour 59, limite 2 ans exacte, défauts multiples, jours fériés
- Pas de nouvelle dépendance backend
- Gotenberg déjà disponible pour PDF

## Success Criteria
- Calcul deadline correct à 100% (tests exhaustifs)
- Lettre PDF générée en <3 secondes
- 0 défauts non notifiés grâce aux alertes

## Constraints & Assumptions
- Droit fédéral (CO) s'applique partout en Suisse
- Prescriptions cantonales peuvent varier (VS, GE ont des spécificités)
- Pour le MVP: droit fédéral uniquement, cantonaux en v2
- Gotenberg est déjà dans le Docker Compose

## Out of Scope
- Suivi judiciaire (procédure, tribunal)
- Conseil juridique (on calcule des délais, on ne donne pas d'avis de droit)
- Prescriptions cantonales spécifiques (v2)
- Intégration avec études d'avocats

## Dependencies
- diagnostic_service (lien défaut ↔ diagnostic)
- notification_service (alertes)
- Gotenberg (PDF generation)
- Building model (building_id)
