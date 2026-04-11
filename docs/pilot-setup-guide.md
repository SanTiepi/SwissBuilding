# BatiConnect Pilot Setup Guide

## Quick Start

```bash
cd backend
python -m app.seeds.seed_pilot_ready
```

This single command seeds everything needed for a pilot demo:
base data, prospect portfolio, G1 scenario, form/procedure templates, source registry.

## Demo Credentials

| Role | Email | Password |
|---|---|---|
| Responsable technique | marc.favre@regiepilote.ch | pilot123 |
| Direction | nathalie.blanc@regiepilote.ch | pilot123 |
| Admin | admin@swissbuildingos.ch | admin123 |

Organization: **Regie Pilote SA** (property_management, Lausanne VD)

## Seeded Portfolio

| Batiment | Etat | Scenario |
|---|---|---|
| Rue de Bourg 12 | Partiellement pret | Diagnostic amiante expire, plan dechets manquant |
| Avenue d'Ouchy 45 | Pret | Tous diagnostics valides, docs complets |
| Chemin des Vignes 8 | Non evalue | Nouvelle acquisition, aucun diagnostic |
| Place St-Francois 3 | Soumis | Pack envoye, en attente autorite |
| Rue du Petit-Chene 21 | Complement demande | Autorite a retourne le dossier (PCB manquant) |
| Chemin des Alpes 28 | G1 scenario | 4 blockers: amiante expire, SUVA manquante, plan dechets manquant, sous-sol non couvert |

## Demo Flow (20 minutes)

1. Login as RT (marc.favre@regiepilote.ch) -> Today page shows actions
2. Open "Rue de Bourg 12" -> See readiness "Not ready, blockers"
3. Show dossier workflow panel -> Progress tracker shows step 1
4. Show missing pieces -> Actions list with priorities
5. Open "Avenue d'Ouchy 45" -> See readiness "Ready"
6. Generate authority pack -> Show conformance badge
7. Open scorecard -> Show baseline metrics
8. Show Today -> Weekly focus, upcoming deadlines

## Pilot Ritual (Weekly)

1. Open Today -> Review weekly_focus
2. Check overdue actions -> Fix highest priority
3. Check dossier progress -> Resolve blockers
4. Review scorecard -> Track improvement

## Org Isolation

The pilot org (Regie Pilote SA) is isolated from other seeded organizations:
- Today feed scoped by org_id
- Scorecard scoped by org_id
- Building-level endpoints (dossier, action queue, building scorecard) verify ownership
- Admin users bypass org checks for cross-org visibility
