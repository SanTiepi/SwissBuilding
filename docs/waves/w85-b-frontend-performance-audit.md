# W85-B Frontend Performance Audit and Quick Wins

## Mission

- business outcome: keep post-sweep frontend performance under control with measurable quick wins.
- user/problem context: feature velocity increased bundle and runtime complexity; drift must be measured and contained.
- visible consumer window (`<=2 waves`): immediate; this is a top hardening objective after W84.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour audit build output, lazy-loading quick wins, et rapport de performance.`

## Scope

- in scope:
  - run bundle/perf audit on current frontend build outputs
  - apply low-risk quick wins (lazy split/import-level containment) if clearly justified
  - produce concise performance report with before/after metrics
- out of scope:
  - major architectural frontend rewrite
  - backend performance work

## Target files

- primary file(s):
  - `docs/frontend-performance-audit.md` (new)
- satellites (tests/schemas/routes):
  - `frontend/vite.config.ts` (modify only if quick win required)
  - `frontend/src/App.tsx` (modify only if lazy-load containment required)
- change mode:
  - `new`:
    - `docs/frontend-performance-audit.md`
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
  - no domain behavior changes
- technical constraints:
  - no "optimization" that increases runtime fragility
  - report must include concrete metrics and identified hot chunks
- repo conventions to preserve:
  - prefer low-risk, measurable quick wins over broad speculative refactors

## Validation

- validation type:
  - `canonical_integration`: build remains green with measured output
  - `targeted_unit_api`: not required unless code paths are changed
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm run build`
- required test level:
  - build + static validation
- acceptance evidence to report:
  - performance report path
  - before/after chunk metrics for changed areas

## Exit criteria

- functional:
  - performance audit report exists with prioritized actions
- quality/reliability:
  - any implemented quick wins are validated and low-risk
- docs/control-plane updates:
  - mark W85-B status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - full performance rewrite
  - i18n hub merge work

## Deliverables

- code:
  - optional low-risk quick-win changes
- tests:
  - validate/build evidence
- docs:
  - frontend performance audit report

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

