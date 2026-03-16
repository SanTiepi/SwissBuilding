# W78-A Material Recommendation Evidence Shelf UI

## Mission

- business outcome: expose material recommendation shelf in intervention UX with evidence hints.
- user/problem context: operators need legible material choices linked to evidence requirements.
- visible consumer window (`<=2 waves`): direct consumption of W77-C endpoint.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour le composant UI, wiring API, et tests frontend.`

## Scope

- in scope:
  - add material recommendation shelf component
  - integrate into InterventionSimulator and/or BuildingInterventions
  - wire frontend API/types and add targeted tests
- out of scope:
  - i18n hub updates (supervisor merge pass)
  - backend logic changes

## Target files

- primary file(s):
  - `frontend/src/components/MaterialRecommendationShelf.tsx` (new)
- satellites (tests/schemas/routes):
  - `frontend/src/pages/InterventionSimulator.tsx` (modify)
  - `frontend/src/api/interventions.ts` (modify/add method)
  - `frontend/src/types/index.ts` (modify)
  - `frontend/src/components/__tests__/RiskSimulator.test.tsx` or dedicated shelf test (modify/add)
- change mode:
  - `new`:
    - `frontend/src/components/MaterialRecommendationShelf.tsx`
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
  - render evidence expectations explicitly for each recommendation
- technical constraints:
  - no blocking regression in intervention simulator flow
  - fallback UI when recommendation endpoint returns empty
- repo conventions to preserve:
  - existing visual language for cards/badges/status

## Validation

- validation type:
  - `canonical_integration`: shelf appears with backend recommendation payload
  - `targeted_unit_api`: shelf render/fallback tests
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- RiskSimulator`
- required test level:
  - targeted UI tests around recommendation shelf
- acceptance evidence to report:
  - screenshot/snippet of shelf cards with evidence hints

## Exit criteria

- functional:
  - intervention UI displays recommendation shelf with evidence expectations
- quality/reliability:
  - empty/error states handled explicitly
- docs/control-plane updates:
  - update W78-A status in `ORCHESTRATOR.md`

## Non-goals

- explicitly not part of this brief:
  - translation completion in all locales
  - pack export changes

## Deliverables

- code:
  - shelf component + page integration
- tests:
  - targeted frontend coverage
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

