# W85-A Keyboard Navigation and Focus Audit

## Mission

- business outcome: verify and harden keyboard-only navigation on critical flows.
- user/problem context: after rapid UI expansion, focus order/trapping drift can silently break usability and accessibility.
- visible consumer window (`<=2 waves`): immediate; this is the next hardening item after W84.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour audit keyboard/focus, e2e navigation, et rapport de correction.`

## Scope

- in scope:
  - audit keyboard navigation and focus order on critical routes
  - add deterministic e2e checks for tab flow and escape/close behavior
  - produce ranked focus/accessibility fix backlog with file references
- out of scope:
  - full accessibility redesign program
  - backend/API changes

## Target files

- primary file(s):
  - `docs/keyboard-focus-audit.md` (new)
- satellites (tests/schemas/routes):
  - `frontend/e2e/navigation.spec.ts` (modify)
  - `frontend/e2e/pages.spec.ts` (modify)
- change mode:
  - `new`:
    - `docs/keyboard-focus-audit.md`
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
  - no domain payload or schema changes
- technical constraints:
  - checks must be reproducible (no manual-only claims)
  - include modal focus-trap and escape handling verification
- repo conventions to preserve:
  - keep audit output operational and ranked

## Validation

- validation type:
  - `canonical_integration`: keyboard/focus e2e checks green on targeted routes
  - `targeted_unit_api`: not required unless a focused unit test is added
- commands to run:
  - `cd frontend && npm run test:e2e -- navigation.spec.ts pages.spec.ts`
- required test level:
  - focused e2e keyboard/focus checks
- acceptance evidence to report:
  - audit report path
  - top issues with file references and severity

## Exit criteria

- functional:
  - keyboard/focus audit is complete and actionable
- quality/reliability:
  - critical keyboard flows have deterministic regression checks
- docs/control-plane updates:
  - mark W85-A status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - full remediation of all audit findings
  - i18n hub merge work

## Deliverables

- code:
  - focused e2e keyboard/focus checks
- tests:
  - navigation/pages keyboard coverage updates
- docs:
  - keyboard focus audit report

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

