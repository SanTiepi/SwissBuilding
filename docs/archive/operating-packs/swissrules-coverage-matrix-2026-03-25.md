# SwissRules Coverage Matrix

Date de controle: `25 mars 2026`

## Current pack summary

Le pack `SwissRules` actuellement bootstrappe dans le repo couvre:

- `12` juridictions
- `15` autorites
- `23` sources officielles ou quasi-normatives
- `12` rule templates
- `18` requirement templates
- `15` procedure templates
- `23` watch entries

Export machine-friendly:

- `cd backend && python scripts/export_swiss_rules_enablement_pack.py --summary`

## Coverage by domain

| Domain | Current status | Current outputs | Current anchor level | Next useful move |
|---|---|---|---|---|
| Permit and planning | `anchored` | `permit_tracking`, future `PermitProcedure`, `ControlTower` | federal + cantonal + communal placeholder | add commune-specific adapters and permit blockers |
| Pollutant declarations | `anchored` | `regulatory_filing`, `authority_pack`, `obligation` | federal + canton execution | harden canton-specific declaration variants |
| OLED / waste traceability | `anchored` | `regulatory_filing`, future `proof_delivery`, `ControlTower` | federal | connect manifest proof to delivery tracking |
| Radon | `anchored` | `obligation`, `authority_pack`, `ControlTower` | federal | add canton or commune risk overlays where available |
| Energy / MoPEC | `anchored_partial` | `permit_tracking`, `authority_pack`, `ControlTower` | intercantonal + cantonal placeholder | add canton-specific energy execution deltas |
| Fire safety | `anchored_partial` | `permit_tracking`, `authority_pack`, `ControlTower` | intercantonal standard | add canton or commune escalation rules for sensitive uses |
| RDPPF / identity | `anchored` | `permit_tracking`, `authority_pack`, `ControlTower` | federal dataset + cadastre | wire richer parcel and restriction explainability |
| Natural hazards | `anchored_partial` | `permit_tracking`, `authority_pack`, `ControlTower` | federal + local review placeholder | add canton hazard-map adapters and blockers |
| Groundwater protection | `anchored_partial` | `permit_tracking`, `authority_pack`, `ControlTower` | federal + local review placeholder | add water protection overlays and review reasons |
| Accessibility | `anchored_partial` | `permit_tracking`, `authority_pack`, `ControlTower` | federal + local review placeholder | add use-case thresholds and public-use detail |
| Heritage / outside-zone | `anchored_partial` | `permit_tracking`, future `PermitProcedure`, `ControlTower` | federal + local review placeholder | add canton and commune heritage adapters |
| Communal zoning specifics | `gap` | currently only `manual_review` | communal placeholder only | add commune adapter pattern and fixtures |
| Utility / network constraints | `gap` | none yet | utility placeholder only | add concession and network approval model |
| Subsidies / public funding | `gap` | none yet | not modeled | add funding source map and procedure templates |
| Special building classes | `gap` | none yet | not modeled | add school, hospital, industrial, agricultural, telecom variants |

## Priority order

### P0

- permit and planning
- pollutant declarations
- OLED / waste traceability
- communal zoning specifics

### P1

- natural hazards
- groundwater protection
- heritage / outside-zone
- energy / MoPEC

### P2

- fire safety
- accessibility
- utility / network constraints
- subsidies / public funding

### P3

- special building classes
- deep commune-by-commune coverage

## Product reading

This matrix should drive product behavior, not just research completeness.

For each domain, the target result is:

- what applies
- what is missing
- what blocks progress
- what proof is needed
- which authority owns the next move

## Anti-duplication note

Even when a domain is expanded, the existing anchors stay canonical:

- permit needs: `permit_tracking`
- deadlines: `Obligation`
- action aggregation: `ControlTower`
- authority-facing proof: `authority_pack`
- incoming docs: `DocumentInbox`

New coverage should feed those surfaces, not replace them.
