# Batiscan and SwissBuilding Cross-Product Operator Stories

Date de controle: `25 mars 2026`

## Purpose

The two-product strategy becomes real only when operators can move naturally
between them.

This pack defines the key stories that make the separation credible and useful.

## Rule

The products stay distinct, but the operator should feel continuity, not
fracture.

## Story 1 - SwissBuilding triggers a diagnostic mission

Starting point:

- building in SwissBuilding
- blocker or need appears

Operator need:

- order the diagnostic without losing building context

Flow:

- manager creates `DiagnosticMissionOrder`
- key building identity and context are sent to `Batiscan`
- SwissBuilding keeps the order and expected return path visible

Win:

- no copy-paste project recreation

## Story 2 - Batiscan publishes a validated report back

Starting point:

- mission is complete in `Batiscan`

Operator need:

- make the report useful in SwissBuilding immediately

Flow:

- `Batiscan` publishes the validated package
- SwissBuilding matches it to the canonical building
- the publication becomes visible in diagnostics, packs, and timeline

Win:

- report becomes reusable building truth, not just another file

## Story 3 - The publication changes what is blocked

Starting point:

- diagnostic publication is attached

Operator need:

- understand what operationally changed

Flow:

- publication updates blockers, obligations, or proof readiness
- ControlTower shows the consequence
- next action becomes visible

Win:

- document arrival changes workflow truth automatically

## Story 4 - Authority dossier reuses Batiscan proof

Starting point:

- validated diagnostic exists
- authority procedure starts later

Operator need:

- reuse that proof safely

Flow:

- authority pack references the publication
- caveats and version remain visible
- delivery trace shows what was sent

Win:

- one diagnostic generates repeated value

## Story 5 - Portfolio manager sees cross-product value

Starting point:

- multiple buildings
- multiple diagnostic and authority states

Operator need:

- understand portfolio risk and action from one place

Flow:

- SwissBuilding aggregates unmatched publications, procedures, obligations, and
  proof gaps
- Batiscan remains the execution system for diagnostic work itself

Win:

- clear separation of systems with one management surface

## Story 6 - Future external diagnostician uses Batiscan

Starting point:

- external diagnostician uses `Batiscan`

Operator need:

- publish into SwissBuilding without becoming the same product

Flow:

- the diagnostician works in Batiscan
- publication contract remains stable
- SwissBuilding consumes validated outputs only

Win:

- future ecosystem growth without collapsing the product boundary

## Acceptance

This pack is succeeding when the product story is clear:

- `Batiscan` runs diagnostic work
- `SwissBuilding` turns validated outputs into durable building operations value
