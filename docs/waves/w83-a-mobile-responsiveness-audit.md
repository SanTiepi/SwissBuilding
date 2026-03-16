# W83-A Mobile Responsiveness Audit

## Mission

- business outcome: produce a deterministic mobile-responsiveness audit so remaining UI polish is evidence-driven.
- user/problem context: broad frontend coverage exists, but mobile regressions are still costly when discovered late.
- visible consumer window (`<=2 waves`): immediate; this addresses rank #7 and feeds ranked follow-up fixes.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour audit e2e mobile, inventory des regressions, et rapport exploitable.`

## Scope

- in scope:
  - run and harden mobile-focused checks on key pages
  - capture concrete breakpoints/layout issues with reproducible references
  - produce ranked fix backlog (`critical/high/medium`) with file pointers
- out of scope:
  - implementing all mobile fixes across pages
  - backend/API contract changes

## Target files

- primary file(s):
  - `docs/mobile-responsiveness-audit.md` (new)
- satellites (tests/schemas/routes):
  - `frontend/e2e/pages.spec.ts` (modify)
  - `frontend/e2e/navigation.spec.ts` (modify)
- change mode:
  - `new`:
    - `docs/mobile-responsiveness-audit.md`
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
  - no schema/model changes
- technical constraints:
  - report must include reproducible viewport details and affected selectors/routes
  - avoid non-deterministic screenshot claims without test references
- repo conventions to preserve:
  - keep mock e2e vs real e2e boundaries explicit

## Validation

- validation type:
  - `canonical_integration`: mobile-focused mock e2e checks run green
  - `targeted_unit_api`: not applicable
- commands to run:
  - `cd frontend && npm run test:e2e -- pages.spec.ts navigation.spec.ts`
- required test level:
  - targeted mock e2e checks for mobile breakpoints
- acceptance evidence to report:
  - audit report path
  - list of ranked issues with page/file references

## Exit criteria

- functional:
  - mobile audit report exists and is actionable
- quality/reliability:
  - report findings are reproducible from tests/selectors
- docs/control-plane updates:
  - mark W83-A status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - full responsive redesign across all pages
  - i18n hub merge work

## Deliverables

- code:
  - focused test refinements for mobile checks
- tests:
  - targeted e2e mobile checks green
- docs:
  - mobile responsiveness audit report

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

