# W83-B PWA Offline Mode Polish

## Mission

- business outcome: improve offline behavior clarity and resilience for the PWA shell.
- user/problem context: PWA is configured, but offline state visibility and cache strategy are still minimal.
- visible consumer window (`<=2 waves`): immediate; this addresses rank #8 and supports external reliability claims.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour cache strategy PWA, indicator offline, et tests UI.`

## Scope

- in scope:
  - refine PWA cache strategy for app shell/static assets
  - add visible offline/online status indicator in app shell
  - add targeted tests for indicator behavior and registration path
- out of scope:
  - backend offline sync engine
  - broad network queue/replay feature set

## Target files

- primary file(s):
  - `frontend/vite.config.ts` (modify)
- satellites (tests/schemas/routes):
  - `frontend/src/main.tsx` (modify)
  - `frontend/src/components/PwaStatusIndicator.tsx` (new)
  - `frontend/src/components/__tests__/PwaStatusIndicator.test.tsx` (new)
- change mode:
  - `new`:
    - `frontend/src/components/PwaStatusIndicator.tsx`
    - `frontend/src/components/__tests__/PwaStatusIndicator.test.tsx`
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
  - do not alter domain payload contracts
- technical constraints:
  - keep PWA registration deterministic across dev/prod
  - indicator must degrade gracefully when browser APIs are unavailable
- repo conventions to preserve:
  - no hidden magic; keep offline behavior explicit in UI and tests

## Validation

- validation type:
  - `canonical_integration`: app boots with updated PWA config and status indicator
  - `targeted_unit_api`: indicator tests for online/offline transitions
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- PwaStatusIndicator`
  - `cd frontend && npm run build`
- required test level:
  - targeted unit + build integrity
- acceptance evidence to report:
  - indicator behavior summary
  - build output summary confirming PWA artifact generation

## Exit criteria

- functional:
  - offline status is visible and meaningful for users
- quality/reliability:
  - cache strategy and indicator behavior are tested and stable
- docs/control-plane updates:
  - mark W83-B status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - full offline CRUD synchronization
  - i18n hub merge work

## Deliverables

- code:
  - PWA config polish + status indicator component
- tests:
  - targeted indicator coverage
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

