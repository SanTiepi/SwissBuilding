# Agent Operating Layer Foundation Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [agent-governance-and-knowledge-workbench-program.md](./agent-governance-and-knowledge-workbench-program.md)

The goal is to make agentic behavior inspectable, correctable, and reusable
without turning SwissBuilding into an opaque automation box.

## Hard rule

Agent output must always be:

- attributable
- explainable
- reviewable
- reusable for learning

If an agent action cannot be traced back to evidence and outcome, it should not
be trusted as product infrastructure.

## Build posture

Build:

- audit objects
- review objects
- correction capture
- replay hooks

Do not build:

- autonomous agents with invisible side effects
- black-box recommendation memory
- free-form logs as the only source of truth

## Minimum objects

### AgentRunAudit

Represents one agent run or recommendation cycle.

Minimum shape:

- `id`
- `agent_type`
- `run_kind`
- `building_id`
- `started_at`
- `completed_at`
- `status`
- `confidence`
- `evidence_refs`
- `output_summary`

### AgentRecommendationAudit

Represents one recommendation or proposed action.

Minimum shape:

- `id`
- `run_id`
- `recommendation_type`
- `status`
- `accepted_by_user_id`
- `overridden_by_user_id`
- `reason_summary`

### KnowledgeCorrection

Represents a human correction to extraction, classification, or linkage.

Minimum shape:

- `id`
- `source_type`
- `source_id`
- `correction_type`
- `before_value`
- `after_value`
- `corrected_by_user_id`
- `corrected_at`

### ReplayScenarioLink

Represents the link from a corrected case to a replayable scenario.

Minimum shape:

- `id`
- `correction_id`
- `scenario_key`
- `replay_ready`

## Existing anchors to reuse

The layer should extend:

- timeline and activity
- `ControlTower`
- `SwissRules`
- seed and scenario factory
- future benchmarking and learning signals

It should not create:

- a second activity log
- a parallel admin universe detached from product truth

## First useful outputs

The first valuable surfaces are:

- who proposed what
- on which evidence
- with what confidence
- whether it was accepted or overridden
- which corrections should feed future replay or tests

## Sequence

### AGL1

Audit layer only:

- `AgentRunAudit`
- `AgentRecommendationAudit`

### AGL2

Correction and replay hooks:

- `KnowledgeCorrection`
- `ReplayScenarioLink`

### AGL3

Later:

- admin review surfaces
- feedback loops into learning and rules

## Acceptance

The layer is useful when automation becomes inspectable and corrections stop
being lost in ad hoc edits.
