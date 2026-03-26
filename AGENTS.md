# SwissBuilding Agent Operating Rules

> Consumed by AI agents (Claude Code, Codex, subagents). Optimized for machine parsing.
> Any AI operating in this repo MAY update this file when it identifies improvements — no approval needed for clarifications, deduplication, or structural optimization. Substantive rule changes require explicit user confirmation.

## Self-Improvement Protocol

Agents SHOULD update repo control files (`AGENTS.md`, `CLAUDE.md`, `MEMORY.md`) when they notice:
- outdated counts, paths, or references
- duplicated information across files
- rules that are never triggered or always overridden
- structural improvements that reduce parse overhead

Do NOT update `ORCHESTRATOR.md` outside of active wave execution.

## Identity Constraints (HARD ERROR if violated)

```
egid:        integer — federal building identifier (RegBL)
egrid:       string  — land parcel identifier (property registry)
official_id: string  — legacy/external reference
```

NEVER interchangeable.

## Execution Model

```yaml
default_mode: autonomous
operators: [codex→strategy, claude_code→execution, user→final_authority]
human_involvement: blockers_and_acceptance_only
```

### Agent Spawning
- max 3 parallel agents per wave, disjoint file scopes
- agent runs validate + fix internally before returning
- brief format: outcome + files + constraints + exit (skip repo context — agent reads docs)
- default to fewer, larger autonomous lots over repeated micro-batches
- split work only when disjoint scopes create real speedup or reduce merge/blocker risk
- for coherent frontend polish/hardening clusters, prefer 1 wider-scope autonomous task over forced micro-splitting
- do not interrupt the user with mid-wave clarification requests unless there is a real blocker or an irreversible/risky decision

### Wave Pattern
```
read_briefs → launch_≤3_agents → collect → unified_validate+test → update_ORCHESTRATOR → next_wave
```

Checkpoint rule:
- one checkpoint at wave completion (not per micro-task) unless blocker
- user confirmation is not required between normal waves; continue autonomously while repo-visible work remains

### Validation Commands

Frontend (`cd frontend`):
```
npm run validate          # tsc + eslint + prettier (fast gate)
npm test                  # vitest unit (299 tests)
npm run test:e2e          # playwright mock (no backend)
npm run test:e2e:real     # playwright real (needs backend:8000)
npm run build             # prod build + PWA
npm run lint:fix && npm run format:fix  # auto-fix
```

Backend (`cd backend`):
```
ruff check app/ tests/              # lint (must be 0 errors)
ruff format --check app/ tests/     # format (must be 0 errors)
python -m pytest tests/ -q          # 4563 tests
ruff check --fix app/ tests/ && ruff format app/ tests/  # auto-fix
```

### Testing Doctrine
- strict types > unit tests > e2e (bug prevention ROI order)
- 1 golden-path e2e per feature > N assertion-per-label unit tests
- branded types / discriminated unions catch more than runtime checks
- test count is cost AND signal — optimize for signal density
- canonical seeded scenarios > synthetic mocks for proving chains
- when adding tests: prefer 1 integration test that exercises the full flow over 10 unit tests that check individual labels

## Hub-File Discipline

Never edited by agents during waves (supervisor merge only):
```
frontend/src/i18n/{en,fr,de,it}.ts
backend/app/api/router.py
backend/app/models/__init__.py
backend/app/schemas/__init__.py
```

i18n workaround: `t(key) || 'inline fallback'`

## Architecture Invariants

- no backend expansion unless explicitly gated
- no partially wired features — hide incomplete work
- imports: idempotent + explicit upserts
- shared constants: `backend/app/constants.py` (not string literals)
- all new frontend: dark mode (`dark:` classes) + `cn()` for conditionals
- loading/error/empty: use `AsyncStateWrapper` or explicit states
- official public data sources over UI scraping

## Ecosystem Invariants (HARD RULES)

BatiConnect carries building intelligence + remediation module (internal) + transversal AI layer.
Remediation is an internal module of BatiConnect, NOT a separate product surface.

Six invariants that must be respected everywhere:
1. Batiscan V4 is frozen -- no features added, consumes via immutable bridge only
2. Site public (batiscan.ch) carries no transactional workflow -- acquisition only
3. BatiConnect does NOT do diagnostics -- consumes Batiscan publications read-only
4. Remediation module does NOT recommend -- client chooses, Batiscan verifies
5. No shared database between V4 and BatiConnect -- immutable bridge (DiagnosticPublicationPackage)
6. Payment never influences ranking -- subscription = visibility, not priority

AI layer rules:
- `ai_generated` flag on all AI-produced outputs (extractions, classifications, suggestions)
- user corrections feed `ai_feedback` table (data flywheel)
- no personal data sent to external LLM -- anonymize or use local models
- progressive learning: Phase 1 (LLM does work) -> Phase 2 (deterministic rules) -> Phase 3 (LLM supervises)

Additional rules:
- auth/docs/audit infrastructure is shared across all modules
- remediation RFQ requires diagnostic proof -- no RFQ without validated report

## Role Split

```
Codex:      strategy, roadmap, vision, acceptance, wave briefs, frontier expansion
Claude:     execution, agents, validation, ORCHESTRATOR, code/tests/seeds
User:       final authority, blocker resolution, acceptance
```

Codex feeds future waves into repo while Claude executes current ones.

## Brief Format (optimal for AI agents)

```yaml
outcome: <1 sentence>
files: { modify: [...], create: [...], do_not_touch: [...] }
constraints: [3-5 hard rules max]
exit: <what "done" means>
validate: <command(s)>
```

Everything else: read from repo docs. Don't restate.
Template references:
- full: `docs/templates/project-brief-template.md`
- compact: `docs/templates/wave-brief-compact-template.md`

## Wave Debrief (in ORCHESTRATOR.md)

```
clear:   <what accelerated>
fuzzy:   <what was ambiguous>
missing: <what had to be inferred>
```

Plus counters: `waves_completed`, `rework_count`, `blocked_count`.

## Definition of Done

1. validate passes (0 errors)
2. relevant tests pass
3. no new warnings introduced
4. ORCHESTRATOR updated (if wave work)
5. no partially wired features exposed

## Memory Sync

| File | Contains | Update trigger |
|------|----------|---------------|
| `CLAUDE.md` | bootstrap + validation refs | commands/counts change |
| `AGENTS.md` | operating rules (this) | rules/patterns improve |
| `MEMORY.md` | project state + architecture | structure changes |
| `ORCHESTRATOR.md` | execution board | wave execution only |

One source of truth per topic. Zero duplication.

## Depth Before Breadth

Current optimization priority:
```
productization > new primitives
consolidation > expansion
realistic data > synthetic mocks
full-chain validation > isolated units
```

New service must unlock an active gate or remove structural debt.

## Ingestion Rules (backend)

- idempotent imports + explicit upserts
- store normalized fields + source provenance separately
- dataset identifiers in `constants.py`
- risk scoring: reuse existing services, don't duplicate
- validate on real source data before claiming success
- no importer change without matching tests
