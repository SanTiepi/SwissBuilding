# W82-A Dashboard Enhancement (KPI + Activity + Quick Actions)

## Mission

- business outcome: make dashboard immediately operational for daily steering (not only static summary cards).
- user/problem context: current dashboard coverage is useful but still shallow for quick triage and action launch.
- visible consumer window (`<=2 waves`): immediate; rank #4 in current Next 10.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour l'enrichissement Dashboard, API wiring, et tests frontend.`

## Scope

- in scope:
  - enrich dashboard KPIs and recent activity module
  - add quick actions entry points to high-value flows
  - strengthen dashboard tests for new widgets/states
- out of scope:
  - new backend domain primitives
  - cross-page redesign

## Target files

- primary file(s):
  - `frontend/src/pages/Dashboard.tsx` (modify)
- satellites (tests/schemas/routes):
  - `frontend/src/components/DashboardCharts.tsx` (modify)
  - `frontend/src/api/buildingDashboard.ts` (modify)
  - `frontend/src/components/__tests__/DashboardWidgets.test.tsx` (new)
- change mode:
  - `new`:
    - `frontend/src/components/__tests__/DashboardWidgets.test.tsx`
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
  - use existing dashboard/read-model contracts; no invented fields
- technical constraints:
  - explicit loading/empty/error handling for each new widget
  - keep dashboard performant (no redundant per-card query storms)
- repo conventions to preserve:
  - preserve current component composition and AsyncStateWrapper usage patterns

## Validation

- validation type:
  - `canonical_integration`: dashboard renders new KPI/activity/actions states correctly
  - `targeted_unit_api`: dashboard widget tests
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- DashboardWidgets`
- required test level:
  - targeted frontend unit tests for new dashboard modules
- acceptance evidence to report:
  - screenshot/snippet of enhanced dashboard states
  - test output summary

## Exit criteria

- functional:
  - dashboard exposes richer KPI/activity/quick-action value
- quality/reliability:
  - error/empty/loading states are explicit and tested
- docs/control-plane updates:
  - mark W82-A status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - adding backend models or services
  - i18n hub merge work

## Deliverables

- code:
  - enhanced dashboard page + supporting API/component wiring
- tests:
  - targeted dashboard widget coverage
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:
