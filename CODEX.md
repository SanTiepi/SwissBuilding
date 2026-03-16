# SwissBuilding — Codex Quick Reference

Quick entry point for Codex.
Source of truth remains `AGENTS.md` for rules and `MEMORY.md` for project state.

Default role in this repo:
- Codex = strategic / creative lead
- Claude Code = execution / orchestration engine

Bias your effort toward:
- moonshot product ideas and differentiating layers
- market/category analysis
- roadmap direction and sequencing
- prompt design for Claude
- independent acceptance review and anti-drift control

Only absorb implementation work directly when:
- it is faster than delegating
- it avoids overlap
- or it materially sharpens the repo before Claude's next wave

For Claude prompts in general:
- keep the prompt lean
- rely on repo docs for shared context
- include only task-specific constraints and required validations

## Best Results Pattern

Codex performs best here when the request is shaped like one of these:

- `push the vision`
- `find the gaps`
- `challenge the plan`
- `turn this into a stronger roadmap`
- `prepare the next Claude mega-program`
- `review what Claude delivered and accept/reject it`
- `keep going until saturation, then switch to triage`

Practical rules:
- prefer outcome-first instructions over micro-management
- let Codex infer from repo context instead of re-briefing everything
- use Codex for:
  - strategy
  - category design
  - moat building
  - prompts
  - acceptance review
  - idea saturation and triage
- use Claude for:
  - large implementation waves
  - agent-heavy delivery
  - code/test/seed execution

For large Claude prompts:
- tell Claude to read `CLAUDE.md`, `CODEX.md`, and `ORCHESTRATOR.md`
- keep the prompt lean and task-specific
- ask Claude to use `ORCHESTRATOR.md` as the durable control plane
- do not duplicate long repo context unless the task introduces new decisions

## Validate before declaring done

Frontend (from `frontend/`):
```bash
npm run validate
npm run test:surface:list
npm run test:surface -- readiness
npm test
npm run test:e2e
npm run build
```

Run the real suite only when the scope justifies it and the backend is up:
```bash
cd frontend && npm run test:e2e:real:preflight
cd frontend && npm run test:e2e:real
```

Real-e2e preflight/env overrides when needed:
```bash
set E2E_REAL_ADMIN_EMAIL=...
set E2E_REAL_ADMIN_PASSWORD=...
set E2E_REAL_API_BASE=http://localhost:8000
```

Backend (from `backend/`):
```bash
python scripts/run_confidence_suite.py --list
ruff check app/ tests/
ruff format --check app/ tests/
python -m pytest tests/ -q
```

Repo-level related checks:
```bash
python scripts/run_related_checks.py --list
python scripts/run_related_checks.py frontend/src/pages/ReadinessWallet.tsx
python scripts/run_related_checks.py --run frontend/src/pages/ReadinessWallet.tsx
```

Both `ruff check` and `ruff format --check` are baseline-clean. New code must keep them green.

## Auto-fix

```bash
cd frontend && npm run lint:fix && npm run format:fix
cd backend && ruff check --fix app/ tests/ && ruff format app/ tests/
```

## Key constraints

- `egid` != `egrid` != `official_id`
- Shared dataset/constants go in `backend/app/constants.py`
- `t()` does not support `defaultValue`; use `t(key) || fallback`
- Frontend alias: `@/` = `src/`
- Keep mock e2e and real e2e clearly separated
