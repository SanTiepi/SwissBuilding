# Duo Mode — Autonomous Improvement System

## What This Is
An autonomous dual-AI system that improves this repo continuously:
- **Codex** (OpenAI, via CLI) = lead architect, planner, reviewer — has full repo access
- **Claude** (Anthropic, in IDE) = builder, executor — has full repo access
- **Both agents are symmetric** — either can read, write, test, review

## How To Start

### Option A: From Claude Code (recommended)
Open this repo in VS Code with Claude Code, then:
```
Read DUO_MODE.md, CLAUDE.md, AGENTS.md, MEMORY.md.
Read docs/duo_inventory.md for the current repo analysis.
Continue the DUO_TASKS.md backlog — pick the top pending task and execute it.
Use Codex CLI for planning: codex exec --full-auto "your prompt"
```

### Option B: From Codex CLI
```bash
cd "c:/PROJET IA/SwissBuilding"
codex exec --full-auto -s workspace-write "Read DUO_MODE.md and DUO_TASKS.md. Pick the top pending task and execute it. Run tests after each change."
```

## Branch Policy
- Work on branch `duo/improvements` (already created)
- Never push to master/main directly
- Each task = one logical commit
- Robin reviews and merges when ready

## Protocol

### Planning (Codex)
```
codex exec --full-auto "PLAN: <task description>. Read the relevant files first. Return: FILES, DO, TEST, DONT, CLASS."
```

### Execution (Claude or Codex)
- Make the change
- Run affected tests: `cd backend && python -m pytest tests/ -x -q`
- Run lint: `cd backend && ruff check app/`
- Report: DONE / CHANGED / TESTS / RISK

### Review (Codex)
```
codex exec --full-auto "REVIEW: <what was done>. Read the changed files and verify correctness. VERDICT: approve/challenge/reject."
```

## Current Backlog
See `DUO_TASKS.md` for the prioritized task list.

## Inventory
See `docs/duo_inventory.md` for the full repo analysis:
- 258 services, 109K lines
- 24 orphan services (~11K dead lines)
- Consumer graph with hub services identified

## Hard Rules (from AGENTS.md)
- No partially wired features
- Hub files (router, models/__init__, schemas/__init__) = supervisor merge only
- Run tests before claiming done
- Shared constants in constants.py
