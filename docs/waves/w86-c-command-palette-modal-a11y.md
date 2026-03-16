# W86-C Command Palette Modal A11y

## Task

- outcome: make CommandPalette modal semantics and focus behavior fully keyboard-accessible.
- visible consumer window (`<=2 waves`): immediate, fixes W85-A findings `CP1/CP2/CP3`.
- done definition (one line): no Tab trap, proper modal semantics, focus restored after close.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour CommandPalette focus logic et tests ciblés.`

## Scope

- in scope:
  - remove/adjust Tab interception behavior that blocks keyboard navigation
  - add missing modal semantics (`aria-modal`, related dialog hygiene)
  - restore focus to prior trigger element on close
  - update unit/e2e checks
- out of scope:
  - redesign of search ranking or result grouping

## Target files

- primary file(s):
  - `frontend/src/components/CommandPalette.tsx`
- satellites:
  - `frontend/src/components/Layout.tsx`
  - `frontend/src/components/__tests__/CommandPalette.test.tsx`
  - `frontend/e2e/navigation.spec.ts`
- change mode:
  - `new`:
    - none required
  - `modify`:
    - files above only
- do-not-touch:
  - `frontend/src/i18n/en.ts`
  - `frontend/src/i18n/fr.ts`
  - `frontend/src/i18n/de.ts`
  - `frontend/src/i18n/it.ts`

## Hard constraints

- keep existing Arrow/Enter result navigation behavior
- preserve command palette open shortcuts (`Cmd/Ctrl+K`)
- avoid introducing custom brittle focus hacks

## Validate loop

- run -> fix -> rerun until clean:
  - yes
- commands:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- CommandPalette`
  - `cd frontend && npm run test:e2e -- navigation.spec.ts`
- acceptance evidence:
  - test output + short note confirming close-button/filter keyboard reachability and focus restoration

## Exit

- functional:
  - palette keyboard flow is complete and modal semantics are correct
- validation:
  - commands green
- orchestrator updates:
  - set W86-C status + debrief lines

