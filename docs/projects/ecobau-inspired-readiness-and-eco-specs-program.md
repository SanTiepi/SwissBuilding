# ecobau-Inspired Readiness and Eco Specs Program

## Mission

Strengthen the commercial wedge (`safe-to-start dossier`) with ecobau-inspired operator value:
- Polludoc-style pre-work diagnostic triggers
- eco tender/spec clause generation
- PFAS-ready pollutant extension
- material recommendation surfaces with explicit evidence requirements

This is a wedge-depth program, not a broad new-domain expansion.

## Why This Matters

Current SwissBuilding strengths are strong on readiness/proof/dossier orchestration.
What is still underexposed in UX and pack generation:
- deterministic diagnostic trigger guidance before works
- procurement-ready ecological language for mandates and tenders
- explicit PFAS handling in readiness flows
- material-level recommendation evidence framing

These are high-signal additions for manager-facing credibility and sales conversion.

## Strategic Outcomes

1. Better pre-work decision clarity:
- operators see when diagnostic escalation is mandatory or strongly advised.

2. Better procurement execution:
- intervention outputs include reusable eco/compliance clause blocks.

3. Better pollutant coverage:
- PFAS becomes explicit in readiness logic and UI blockers/conditions.

4. Better intervention quality:
- material recommendations become evidence-aware and traceable.

## Scope

### Workstream A - Diagnostic trigger assistant (Polludoc-style)

Outputs:
- deterministic trigger card in readiness/building detail
- building-era/intervention-scale trigger logic
- legal-basis references through rules-pack compatible metadata

### Workstream B - Eco tender/spec clause generator

Outputs:
- reusable clause templates by intervention type
- hazardous-material handling language blocks
- disposal and provenance requirements language blocks
- export-ready insertion into authority/contractor pack flow

### Workstream C - PFAS readiness extension

Outputs:
- PFAS pollutant profile support in readiness reasoner/checks
- blocker/condition semantics for PFAS where relevant
- clear claim-disciplined wording in UI

### Workstream D - Material recommendation evidence shelf

Outputs:
- intervention material options with internal eco status (`eco1/eco2`-style semantics)
- required-evidence hints per option
- circularity/health impact notes linked to evidence chain

## Suggested Delivery Sequence

1. Workstream A (fast wedge impact)
2. Workstream B (commercial/procurement leverage)
3. Workstream C (pollutant coverage depth)
4. Workstream D (material recommendation quality layer)

## Constraints

- keep legal-liability discipline:
  - no legal guarantee claims
  - keep readiness/provenance support framing
- prefer official source-compatible structures, not UI scraping
- preserve identifier hygiene (`egid` vs `egrid` vs `official_id`)
- during backend freeze windows, allow only minimal frontend-unblocker glue

## Acceptance Criteria

- safe-to-start flow exposes deterministic diagnostic trigger guidance
- at least one eco clause pack is generated from intervention context
- PFAS appears in readiness logic with explicit blocker/condition semantics
- material recommendation cards show evidence expectations, not only labels
- all new claims remain within completeness/provenance/readiness-support posture

## Validation

Backend if touched:
- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend if touched:
- `cd frontend`
- `npm run validate`
- `npm test`

Real integration when flow is externally claimed:
- `cd frontend`
- `npm run test:e2e:real:preflight`
- `npm run test:e2e:real`

## Notes

This program is intentionally aligned with ecobau-like execution quality patterns.
It should increase manager-facing trust and execution readiness without diluting SwissBuilding's core wedge.

