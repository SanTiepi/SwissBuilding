# SwissBuilding Claude Bootstrap

Read [AGENTS.md](./AGENTS.md) for operating rules.
Read [MEMORY.md](./MEMORY.md) for project state.
Read [ORCHESTRATOR.md](./ORCHESTRATOR.md) for active execution board (large/multi-wave missions).

> AI agents MAY update this file to fix outdated counts, commands, or references.

## Ecosystem

BatiConnect is a **standalone brand** (Batiscan Sarl is founder/operator).
This repo carries **two product surfaces**:
1. **Building intelligence** — dossier, evidence, completeness, trust, readiness, portfolio
2. **Remediation marketplace** — mise en concurrence encadree for pollutant remediation works

Both share infra (auth, docs, audit) but have separate models and routes.
See `memory/project_ecosystem_vision.md` for the full 4-brick map.

## Hard Rules

- `egid` != `egrid` != `official_id` (see AGENTS.md for types)
- no partially wired features — hide or simplify incomplete work
- no backend expansion unless explicitly gated
- hub files (i18n, router.py, models/__init__, schemas/__init__) = supervisor merge only
- shared constants in `backend/app/constants.py`
- imports: idempotent + explicit upserts
- before claiming done: check AGENTS.md Definition of Done

## Mission Protocol

For large missions:
- prompt = mission framing only (don't restate repo context)
- `ORCHESTRATOR.md` = durable execution board (maintain Next 10, wave status, debriefs)
- `Lead Feed` section = Codex→Claude channel
- repo docs = standing context (don't expect prompt to contain everything)

## Validation Commands

### Frontend (`cd frontend`)

| Command | Purpose |
|---------|---------|
| `npm run validate` | tsc + eslint + prettier (fast gate) |
| `npm test` | vitest unit (299 tests) |
| `npm run test:e2e` | playwright mock (no backend) |
| `npm run test:e2e:real` | playwright real (needs backend:8000, runs preflight auto) |
| `npm run build` | prod build + PWA artifacts |
| `npm run lint:fix && npm run format:fix` | auto-fix |

### Backend (`cd backend`)

| Command | Purpose |
|---------|---------|
| `ruff check app/ tests/` | lint (must be 0 errors) |
| `ruff format --check app/ tests/` | format (must be 0 errors) |
| `python -m pytest tests/ -q` | 4563 tests |
| `python -m app.seeds.seed_verify` | verify seed dataset |
| `ruff check --fix app/ tests/ && ruff format app/ tests/` | auto-fix |

### Strategy

- after frontend edits: `npm run validate`
- after backend edits: `ruff check app/ tests/`
- before done: run relevant tests
- full validation (build + all tests): only when scope justifies it
- testing doctrine: signal density > test count (see AGENTS.md)
