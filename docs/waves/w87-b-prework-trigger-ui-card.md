# W87-B Prework Trigger UI Card

## Task

- outcome: render prework trigger guidance in BuildingDetail/Readiness surfaces.
- visible consumer window (`<=2 waves`): immediate user-facing consumption of W87-A.
- done definition (one line): users see clear trigger rationale with safe fallback behavior.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour composant UI, API types, et tests front.`

## Scope

- in scope:
  - add trigger card component
  - wire additive readiness contract to overview/readiness views
  - add targeted frontend tests
- out of scope:
  - i18n hub edits
  - backend logic changes

## Target files

- primary file(s):
  - `frontend/src/components/PreworkDiagnosticTriggerCard.tsx`
- satellites:
  - `frontend/src/components/building-detail/OverviewTab.tsx`
  - `frontend/src/pages/ReadinessWallet.tsx`
  - `frontend/src/api/readiness.ts`
  - `frontend/src/types/index.ts`
  - `frontend/src/components/__tests__/ReadinessWallet.test.tsx`
- change mode:
  - `new`:
    - `frontend/src/components/PreworkDiagnosticTriggerCard.tsx`
  - `modify`:
    - files above only
- do-not-touch:
  - `frontend/src/i18n/en.ts`
  - `frontend/src/i18n/fr.ts`
  - `frontend/src/i18n/de.ts`
  - `frontend/src/i18n/it.ts`

## Hard constraints

- explicit fallback when `prework_trigger` is absent
- preserve existing readiness cards and layout stability
- no reinterpretation of legal semantics

## Validate loop

- run -> fix -> rerun until clean:
  - yes
- commands:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- ReadinessWallet`
- acceptance evidence:
  - screenshot/snippet of trigger card on at least one seeded building

## Exit

- functional:
  - trigger card rendered with rationale and safe fallback
- validation:
  - commands green
- orchestrator updates:
  - set W87-B status + debrief lines

