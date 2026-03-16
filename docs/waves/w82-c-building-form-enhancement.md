# W82-C Building Creation/Edit Form Enhancement

## Mission

- business outcome: improve building create/edit quality so data entry is complete, fast, and less error-prone.
- user/problem context: building form flow exists but field coverage and UX clarity are still uneven.
- visible consumer window (`<=2 waves`): immediate; rank #6 in current Next 10.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour le formulaire BuildingsList, validations, et tests.`

## Scope

- in scope:
  - improve building create/edit form coverage and validation messaging
  - refine advanced fields UX and guardrails
  - add targeted tests for form validation and submission states
- out of scope:
  - backend schema migration
  - unrelated list/card redesign

## Target files

- primary file(s):
  - `frontend/src/pages/BuildingsList.tsx` (modify)
- satellites (tests/schemas/routes):
  - `frontend/src/api/buildings.ts` (modify only if required by existing contract)
  - `frontend/src/components/__tests__/BuildingsListForm.test.tsx` (new)
  - `frontend/e2e/buildings.spec.ts` (modify)
- change mode:
  - `new`:
    - `frontend/src/components/__tests__/BuildingsListForm.test.tsx`
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
  - preserve `egid` vs `egrid` distinctions in form labels/validation and payload fields
  - do not invent fields not present in backend contract
- technical constraints:
  - explicit error and success states for submission path
  - no regression on existing building list filtering/search behavior
- repo conventions to preserve:
  - keep form schema validation centralized and readable

## Validation

- validation type:
  - `canonical_integration`: create/edit flows pass in buildings e2e spec
  - `targeted_unit_api`: form validation and submission unit tests
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- BuildingsListForm`
  - `cd frontend && npm run test:e2e -- buildings.spec.ts`
- required test level:
  - targeted unit + focused e2e
- acceptance evidence to report:
  - form validation cases covered
  - create/edit flow pass summary

## Exit criteria

- functional:
  - building create/edit form has clearer validation and fuller field support
- quality/reliability:
  - key form regressions are covered in tests
- docs/control-plane updates:
  - mark W82-C status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - backend domain expansion
  - i18n hub merge work

## Deliverables

- code:
  - enhanced form behavior and validation
- tests:
  - targeted form unit tests + e2e coverage update
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:
