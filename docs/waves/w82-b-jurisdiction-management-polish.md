# W82-B Jurisdiction Management Polish

## Mission

- business outcome: make jurisdiction/rules-pack administration reliable and usable for operators.
- user/problem context: admin jurisdictions flow exists but still lacks operational polish and confidence cues.
- visible consumer window (`<=2 waves`): immediate; rank #5 in current Next 10.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour la page AdminJurisdictions, API client, et tests.`

## Scope

- in scope:
  - polish jurisdictions list/filter/detail interactions
  - improve rules-pack visibility and admin actions clarity
  - add/extend targeted unit and e2e coverage for critical flows
- out of scope:
  - backend regulatory model redesign
  - broad admin-suite redesign

## Target files

- primary file(s):
  - `frontend/src/pages/AdminJurisdictions.tsx` (modify)
- satellites (tests/schemas/routes):
  - `frontend/src/api/jurisdictions.ts` (modify)
  - `frontend/src/components/__tests__/AdminJurisdictions.test.tsx` (new)
  - `frontend/e2e/admin-jurisdictions.spec.ts` (modify)
- change mode:
  - `new`:
    - `frontend/src/components/__tests__/AdminJurisdictions.test.tsx`
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
  - use existing jurisdictions/rules-pack backend contracts
- technical constraints:
  - keep admin actions explicit and recoverable (clear errors, no silent failure)
  - do not introduce new API coupling with unrelated admin pages
- repo conventions to preserve:
  - maintain admin page visual and interaction consistency

## Validation

- validation type:
  - `canonical_integration`: admin jurisdictions key flows pass in e2e mock path
  - `targeted_unit_api`: page-level unit tests for key interaction states
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- AdminJurisdictions`
  - `cd frontend && npm run test:e2e -- admin-jurisdictions.spec.ts`
- required test level:
  - targeted unit + focused e2e
- acceptance evidence to report:
  - e2e pass summary
  - unit test pass summary

## Exit criteria

- functional:
  - jurisdictions admin flow is faster to operate and less error-prone
- quality/reliability:
  - major user/admin states have explicit handling and test coverage
- docs/control-plane updates:
  - mark W82-B status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - backend rules engine work
  - cross-admin navigation refactor

## Deliverables

- code:
  - polished jurisdictions page + API client updates
- tests:
  - targeted unit/e2e coverage
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:
