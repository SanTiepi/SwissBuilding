# W84-B Building Comparison Mobile Fallback

## Mission

- business outcome: make building comparison genuinely usable on mobile for 3+ buildings.
- user/problem context: current table-based layout becomes impractical on 375px (high-priority audit finding BC-1).
- visible consumer window (`<=2 waves`): immediate; top-priority mobile fix from W83 audit.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour fallback mobile sur BuildingComparison et tests associes.`

## Scope

- in scope:
  - add a mobile-friendly fallback layout (cards/stacked rows) for comparison view
  - keep desktop/table comparison untouched
  - add targeted unit/e2e coverage for mobile comparison path
- out of scope:
  - backend comparison contract changes
  - redesign of non-mobile comparison surfaces

## Target files

- primary file(s):
  - `frontend/src/pages/BuildingComparison.tsx` (modify)
- satellites (tests/schemas/routes):
  - `frontend/src/components/__tests__/BuildingComparisonPage.test.tsx` (modify)
  - `frontend/e2e/pages.spec.ts` (modify)
- change mode:
  - `new`:
    - none required
  - `modify`:
    - files listed above only
- hub-file ownership:
  - `supervisor_merge`:
    - `frontend/src/i18n/en.ts`
    - `frontend/src/i18n/fr.ts`
    - `frontend/src/i18n/de.ts`
    - `frontend/src/i18n/it.ts`
  - `agent_allowed`:
    - files listed in scope
- do-not-touch (hub files reserved to supervisor merge):
  - `frontend/src/i18n/en.ts`
  - `frontend/src/i18n/fr.ts`
  - `frontend/src/i18n/de.ts`
  - `frontend/src/i18n/it.ts`

## Non-negotiable constraints

- data/model constraints:
  - use existing comparison payload; no invented fields
- technical constraints:
  - mobile fallback must support at least 3 buildings without horizontal usability collapse
  - desktop table mode must remain intact
- repo conventions to preserve:
  - keep comparison semantics consistent between desktop and mobile views

## Validation

- validation type:
  - `canonical_integration`: mobile comparison flow is usable and readable
  - `targeted_unit_api`: comparison page layout logic covered
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- BuildingComparisonPage`
  - `cd frontend && npm run test:e2e -- pages.spec.ts`
- required test level:
  - targeted unit + focused e2e
- acceptance evidence to report:
  - mobile screenshot/snippet of fallback layout
  - test output summary

## Exit criteria

- functional:
  - comparison is operable on 375px with 3+ buildings
- quality/reliability:
  - desktop comparison behavior preserved
- docs/control-plane updates:
  - mark W84-B status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - adding new comparison dimensions
  - i18n hub merge work

## Deliverables

- code:
  - mobile fallback layout for comparison page
- tests:
  - updated comparison unit/e2e coverage
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

