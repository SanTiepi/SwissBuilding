# W77-B PFAS Readiness Wallet UI

## Mission

- business outcome: make PFAS readiness status visible and actionable in wallet/detail surfaces.
- user/problem context: operators need explicit PFAS blockers/conditions, not hidden backend states.
- visible consumer window (`<=2 waves`): immediate consumer of W77-A backend extension.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour les composants/pages frontend et tests ciblés.`

## Scope

- in scope:
  - render PFAS readiness checks in wallet/detail UI
  - ensure blocker/condition presentation is legible and consistent
  - wire frontend types/API additions
- out of scope:
  - i18n hub updates (supervisor merge pass)
  - backend logic changes

## Target files

- primary file(s):
  - `frontend/src/pages/ReadinessWallet.tsx` (modify)
- satellites (tests/schemas/routes):
  - `frontend/src/components/ReadinessSummary.tsx` (modify)
  - `frontend/src/api/readiness.ts` (modify)
  - `frontend/src/types/index.ts` (modify)
  - `frontend/src/components/__tests__/ReadinessWallet.test.tsx` (modify/add)
- change mode:
  - `new`:
    - none required
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
  - reflect backend PFAS checks exactly; no frontend reinterpretation
- technical constraints:
  - robust fallback when PFAS fields are absent
  - preserve existing wallet interactions/performance
- repo conventions to preserve:
  - existing card/badge semantics and readability patterns

## Validation

- validation type:
  - `canonical_integration`: wallet displays PFAS readiness status from API payload
  - `targeted_unit_api`: rendering and fallback tests
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- ReadinessWallet`
- required test level:
  - targeted readiness wallet tests
- acceptance evidence to report:
  - UI screenshot/snippet with PFAS block/condition

## Exit criteria

- functional:
  - PFAS appears in readiness wallet/detail with clear status and blockers/conditions
- quality/reliability:
  - no regressions on existing readiness rendering
- docs/control-plane updates:
  - update W77-B status in `ORCHESTRATOR.md`

## Non-goals

- explicitly not part of this brief:
  - translation completion in 4 languages
  - backend PFAS rule changes

## Deliverables

- code:
  - wallet/detail PFAS UI support
- tests:
  - targeted readiness wallet assertions
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

