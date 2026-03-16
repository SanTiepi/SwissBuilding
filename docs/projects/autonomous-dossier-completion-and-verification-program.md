# Autonomous Dossier Completion and Verification Program

## Mission

Build an agentic layer that can actively drive a dossier toward readiness by:
- finding missing items
- checking internal consistency
- requesting targeted inputs
- proposing canonical updates
- assembling the next best pack

This should remain bounded, reviewable, and evidence-first.

## Why This Matters

What became more practical after 2025 is not just generation.
It is reliable tool-using agents that can:
- inspect many sources
- compare states
- plan multi-step completion work
- explain why they are asking for something
- operate with structured outputs and human checkpoints

That makes it realistic to move from passive dossier tracking to active dossier completion.

## Strategic Outcomes

- SwissBuilding becomes agentic in a workflow-native way
- dossier completion becomes faster and less manual
- missing-proof chasing becomes a product capability, not just a user burden

## Product Scope

This program should produce:
- a bounded dossier-completion agent loop
- verification gates
- explicit proposed changes
- request / reminder / completion orchestration

It should not become:
- unchecked autonomous editing
- opaque agent behavior without review and audit

## Recommended Workstreams

### Workstream A - Completion planning engine

Candidate objects:
- `CompletionPlan`
- `CompletionStep`
- `MissingArtifactRequest`

### Workstream B - Verification and review gates

Candidate objects:
- `VerificationCheck`
- `ProposedUpdate`
- `ReviewDecision`

### Workstream C - Agent execution trace

Expected capabilities:
- what the agent checked
- what it inferred
- what it requested
- what it proposed
- why it stopped or escalated

Candidate objects:
- `AgentCompletionRun`
- `VerificationTrace`

## Acceptance Criteria

- SwissBuilding can actively drive a dossier toward readiness
- agent suggestions remain reviewable and auditable
- the completion loop increases product leverage without reducing trust

## Validation

Backend if touched:
- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend if touched:
- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run test:e2e`
- `npm run build`
