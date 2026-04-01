# Claude Restart Checklist

Date de controle: `25 mars 2026`

Use this when execution resumes after a noisy or blocked period.

## 1. Clear technical noise first

- use [auth-regression-sweep-pack-2026-03-25.md](./auth-regression-sweep-pack-2026-03-25.md) if the active blocker is the auth cluster
- do not run full suites by reflex

## 2. Read only the shortest control path

1. [claude-handoff-prompt-2026-03-25.md](./claude-handoff-prompt-2026-03-25.md)
2. [claude-now-priority-stack-2026-03-25.md](./claude-now-priority-stack-2026-03-25.md)
3. [claude-one-shot-finisher-pack-2026-03-25.md](./claude-one-shot-finisher-pack-2026-03-25.md)
4. [claude-master-execution-pack-2026-03-25.md](./claude-master-execution-pack-2026-03-25.md)
5. [claude-operating-pack-registry-2026-03-25.md](./claude-operating-pack-registry-2026-03-25.md)
6. [claude-next-wave-selector-2026-03-25.md](./claude-next-wave-selector-2026-03-25.md)

## 3. Find the right brief fast

Commands:

```bash
python backend/scripts/list_claude_briefs.py
python backend/scripts/list_claude_briefs.py --contains proof
python backend/scripts/list_claude_briefs.py --ids 1 2 3 4 5
python backend/scripts/print_claude_now_stack.py
```

## 4. Choose one wave only

Pick:

- one core wave
- or one moat wave
- or one adoption wave

Do not mix multiple strategic categories unless scopes are clearly disjoint.

## 5. Use the smallest validation loop

Start with:

- [claude-validation-matrix-2026-03-25.md](./claude-validation-matrix-2026-03-25.md)
- `python backend/scripts/run_local_test_loop.py changed`
- `npm run test:changed:strict`

## 6. Keep hub-file discipline

Do not directly edit:

- `backend/app/api/router.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `frontend/src/i18n/{en,fr,de,it}.ts`

Prepare supervisor merge notes instead.

## 7. Final rule

One problem.
One pack.
One brief.
One confidence loop.

Then ship.
