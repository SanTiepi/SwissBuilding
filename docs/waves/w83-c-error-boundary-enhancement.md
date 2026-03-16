# W83-C Error Boundary Enhancement

## Mission

- business outcome: improve route-level recovery and error communication without masking failures.
- user/problem context: error boundaries exist but recovery actions and context clarity can be stronger.
- visible consumer window (`<=2 waves`): immediate; this addresses rank #9 in current Next 10.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour ErrorBoundary, route wrappers, et tests de recovery.`

## Scope

- in scope:
  - enhance global and page-level error boundary UX/recovery actions
  - improve route-level fallback consistency
  - strengthen targeted tests for crash/retry/reset behavior
- out of scope:
  - backend exception handling redesign
  - broad app shell redesign

## Target files

- primary file(s):
  - `frontend/src/components/ErrorBoundary.tsx` (modify)
- satellites (tests/schemas/routes):
  - `frontend/src/App.tsx` (modify)
  - `frontend/src/components/__tests__/ErrorBoundary.test.tsx` (modify)
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
  - no API contract changes
- technical constraints:
  - preserve existing route map semantics
  - errors must remain observable (no silent swallow)
- repo conventions to preserve:
  - keep boundary components composable and testable

## Validation

- validation type:
  - `canonical_integration`: route-level fallback and retry flows behave correctly
  - `targeted_unit_api`: error boundary test suite covers reset/retry branches
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- ErrorBoundary`
- required test level:
  - targeted frontend unit tests
- acceptance evidence to report:
  - before/after behavior summary for page crash and retry
  - test output summary

## Exit criteria

- functional:
  - users get clearer recovery paths on route/page failures
- quality/reliability:
  - error handling remains explicit, test-covered, and observable
- docs/control-plane updates:
  - mark W83-C status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - generic error-text rewrite across all pages
  - i18n hub merge work

## Deliverables

- code:
  - enhanced error boundary behavior and route integration
- tests:
  - strengthened ErrorBoundary tests
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

