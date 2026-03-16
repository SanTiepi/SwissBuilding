# W76-B Polludoc Trigger UI Card

## Mission

- business outcome: make diagnostic trigger guidance visible in the safe-to-start journey.
- user/problem context: operators need a clear "why escalate now" card in BuildingDetail/Readiness views.
- visible consumer window (`<=2 waves`): immediate user-visible consumer of W76-A backend contract.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour le composant UI, client API, et tests frontend.`

## Scope

- in scope:
  - add trigger card component
  - render in BuildingDetail overview and/or ReadinessWallet
  - wire frontend types/API for additive payload fields
- out of scope:
  - i18n hub updates (supervisor merge pass)
  - backend logic changes

## Target files

- primary file(s):
  - `frontend/src/components/PreworkDiagnosticTriggerCard.tsx` (new)
- satellites (tests/schemas/routes):
  - `frontend/src/components/building-detail/OverviewTab.tsx` (modify)
  - `frontend/src/pages/ReadinessWallet.tsx` (modify)
  - `frontend/src/api/readiness.ts` (modify)
  - `frontend/src/types/index.ts` (modify)
  - `frontend/src/components/__tests__/ReadinessWallet.test.tsx` (modify/add)
- change mode:
  - `new`:
    - `frontend/src/components/PreworkDiagnosticTriggerCard.tsx`
  - `modify`:
    - files above only
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
  - reflect backend trigger semantics without reinterpreting legal meaning
- technical constraints:
  - graceful fallback when `prework_trigger` is absent
  - no regressions on existing readiness cards
- repo conventions to preserve:
  - use existing AsyncState/Readiness visual patterns

## Validation

- validation type:
  - `canonical_integration`: BuildingDetail/Readiness renders trigger card from API payload
  - `targeted_unit_api`: component rendering and fallback behavior tests
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- ReadinessWallet`
- required test level:
  - targeted frontend tests for new component path
- acceptance evidence to report:
  - screenshot/snippet showing card in UI
  - test results summary

## Exit criteria

- functional:
  - trigger card visible with rationale and legal basis hints
- quality/reliability:
  - no runtime errors when payload is missing or partial
- docs/control-plane updates:
  - update W76-B status in `ORCHESTRATOR.md`

## Non-goals

- explicitly not part of this brief:
  - translation completeness across 4 languages
  - new navigation routes

## Deliverables

- code:
  - new card component + wiring in existing surfaces
- tests:
  - targeted rendering/fallback tests
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

