# W84-A Mobile Search Trigger Fix

## Mission

- business outcome: restore visible search affordance on mobile to keep navigation fast without keyboard shortcuts.
- user/problem context: mobile users currently lose direct access to search trigger (high-priority audit finding S-1).
- visible consumer window (`<=2 waves`): immediate; top-priority mobile fix from W83 audit.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour le fix Header/CommandPalette et les tests e2e associes.`

## Scope

- in scope:
  - add visible mobile search trigger in header
  - preserve existing command palette shortcut behavior
  - add targeted tests for mobile trigger open path
- out of scope:
  - broad header redesign
  - i18n hub merge work

## Target files

- primary file(s):
  - `frontend/src/components/Header.tsx` (modify)
- satellites (tests/schemas/routes):
  - `frontend/src/components/__tests__/Header.test.tsx` (modify)
  - `frontend/e2e/navigation.spec.ts` (modify)
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
  - maintain desktop behavior and existing shortcut (`Cmd/Ctrl+K`)
  - keep touch target size mobile-friendly (>=44px)
- repo conventions to preserve:
  - keep header controls readable at 375px

## Validation

- validation type:
  - `canonical_integration`: mobile header search trigger opens command palette
  - `targeted_unit_api`: header interaction tests
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- Header`
  - `cd frontend && npm run test:e2e -- navigation.spec.ts`
- required test level:
  - targeted unit + focused e2e
- acceptance evidence to report:
  - mobile screenshot/snippet showing visible search trigger
  - test output summary

## Exit criteria

- functional:
  - search trigger is visible and usable on mobile
- quality/reliability:
  - no regression on desktop header behavior
- docs/control-plane updates:
  - mark W84-A status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - reworking notification/language/user controls

## Deliverables

- code:
  - mobile search trigger fix in header flow
- tests:
  - updated header/e2e coverage
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

