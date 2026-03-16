# Agent Execution Patterns

This file defines the practical execution pattern for multi-agent waves.
Goal: maximize throughput while keeping merge and validation risk low.

## Wave Size

- default mode depends on work type:
  - `build mode`: up to `3` disjoint tasks in parallel
  - `hardening/polish mode`: prefer `1` wider-scope autonomous task to reduce coordination overhead
- do not exceed `3` parallel implementation tasks in the same wave

Why:
- above `3`, merge conflicts on shared files increase and remove speed gains
- for polish clusters, forced micro-splitting creates unnecessary briefing + merge overhead

## Scope Disjointness

Before launching agents, ensure tasks are non-overlapping.

High-conflict hub files (supervisor-owned by default):
- `backend/app/api/router.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `backend/app/seeds/seed_data.py`
- `frontend/src/i18n/en.ts`
- `frontend/src/i18n/fr.ts`
- `frontend/src/i18n/de.ts`
- `frontend/src/i18n/it.ts`

Rule:
- agents should avoid hub files unless explicitly assigned
- hub-file integration is handled by the supervisor during merge/finalization
- briefs should explicitly state when agents must not register routes/imports in hub files

## Task Granularity

Preferred shape:
- default:
  - `1` task = `1` bounded deliverable (one primary file plus satellites)
- allowed exception (lean hardening mode):
  - `1` task = one coherent polish cluster (for example 3 closely related pages/components)
  - use this when splitting would mostly add coordination overhead

Good:
- create one service + one schema + one route + targeted tests
- one coherent UI hardening cluster with explicit exit checklist

Too broad:
- multiple domain facades plus multiple routes plus broad migration/refactor in one task

Too small:
- one-line-only tasks that can be completed directly without agent spawn

## Prioritization Gate (Consumer First)

Before promoting a task into an active wave, ask:
- does this work have a visible product consumer within the next `2` waves?

Rule:
- if a task (especially `ring_4`) has no near-term visible consumer, deprioritize it
- prioritize productization of already landed backend capabilities over adding new standalone primitives

## Frontend/Backend Balance

Near-term default for active waves:
- target a `2:1` ratio of frontend productization tasks to backend expansion tasks

Exception:
- allow backend-heavy waves only for hard blockers or maturity-gate-critical gaps

## Validation Flow

- each agent must run an internal validate-fix loop before reporting done:
  - run validation commands from brief
  - fix failures introduced by its scope
  - rerun until clean
- supervisor still performs acceptance validation after merge
- do not postpone all validation to one large final batch

Why:
- catches integration breakage early
- removes avoidable handoff churn (`code -> validate -> fix -> return`)

## Validation Typing

Validation in briefs should be typed, not only counted.

Preferred:
- type/compiler checks first (strict typing as first filter)
- one canonical integration or e2e golden path per feature slice
- targeted unit/API tests for non-trivial branch logic only

Avoid:
- inflating test count with low-signal render assertions that duplicate golden-path coverage

## Type-First Reliability

For frontend and API-facing domain boundaries:

- prefer strong typing over display-level unit-test multiplication
- where useful, use branded/discriminated types for critical identifiers and domain states
- for this repo, preserve explicit distinction:
  - `egid`
  - `egrid`
  - `official_id`

## Agent Usage Rules

- use direct search/read commands for simple lookups (`rg`, file reads)
- reserve agents for open-ended exploration or bounded implementation work
- apply lightweight fixes (format/import/small wiring) directly after merge without spawning a new agent

## Brief Requirements

Each task brief should explicitly include:
- target file paths
- change mode per file (`new` vs `modify`)
- deliverable boundary (or explicit polish-cluster checklist in lean mode)
- validation command(s)
- do-not-touch files (especially hub files when reserved to supervisor)
- explicit internal validate-loop requirement (`run -> fix -> rerun until clean`)

## Lean Brief Mode

When velocity matters more than ceremony:

- use compact briefs (minimal sections, high-signal deltas only)
- keep only hard constraints that matter for acceptance
- avoid restating standing repo rules already captured in `AGENTS.md` / `ORCHESTRATOR.md`

## Autonomous Loop (Codex + ClaudeCode)

Operating assumption:
- no human-in-the-loop dependency for execution continuity

Control behavior:
- Codex keeps strategy, sequencing pressure, and acceptance gates explicit
- Claude keeps implementation waves moving from repo control-plane artifacts
- when active work remains, execution continues without waiting for ad-hoc re-briefs

Canonical references:
- external gate protocol:
  - `docs/safe-to-start-gate-runbook.md`
- external demo/commercial script:
  - `docs/market/safe-to-start-demo-onepager.md`

## Task Snippet (recommended)

```md
## Task: <short name>
- Scope: <primary file path> (new|modify)
- Dependencies: <models/services used>
- Deliverable: <service + schema + route + tests>
- Validation: <exact commands>
- Do not touch: <hub files reserved for supervisor>
```
