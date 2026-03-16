# Lead Automation Toolkit

Purpose:
- keep Codex lead operations fast, reproducible, and non-blocking for Claude waves
- automate gate validation, proof packaging, brief quality checks, and wave guardrails

## 1) Safe-to-start gate bot

Script:
- `python scripts/safe_to_start_gate_check.py --run --run-screenshot-audit`
- plan mode non-bloquant:
  - `python scripts/safe_to_start_gate_check.py --allow-incomplete-exit0`

Outputs:
- gate verdict JSON:
  - `tmp/safe_to_start_gate_result.json`
- command logs:
  - `tmp/safe_to_start_gate_logs/*.log`

Notes:
- run without `--run` for a dry planning report
- add `--allow-missing-screenshots` only when doing non-final checks

## 2) Proof bundle generator

Script:
- `python scripts/safe_to_start_proof_bundle.py --strict-pass`

Outputs:
- timestamped bundle under:
  - `artifacts/gates/safe-to-start/<timestamp>/`
- includes:
  - gate result JSON
  - referenced logs/evidence
  - available screenshot artifacts
  - `SUMMARY.md`
  - `manifest.json`

## 3) Brief linter (Claude task quality)

Script:
- `python scripts/brief_lint.py <brief1.md> <brief2.md>`
- or:
  - `python scripts/brief_lint.py --glob "docs/projects/*.md"`
- strict diff-friendly mode for wave briefs:
  - `python scripts/brief_lint.py --strict-diff --glob "docs/waves/w*.md"`
- templates supported:
  - full template: `docs/templates/project-brief-template.md`
  - compact template: `docs/templates/wave-brief-compact-template.md`

Checks:
- mandatory sections from canonical template
- explicit agent-usage line
- target file specificity
- validation command presence

## 4) Wave overlap guard

Script:
- `python scripts/wave_overlap_guard.py <briefA.md> <briefB.md> <briefC.md>`

Checks:
- overlapping target paths across briefs
- hub-file contention (`router.py`, `__init__.py`, i18n hubs, seed hub)

Overrides:
- allow one shared path:
  - `--allow-shared backend/app/services/shared.py`
- allow one hub touch for this run:
  - `--allow-hub frontend/src/i18n/fr.ts`

## 5) Wave readiness binary gate

Script:
- `python scripts/wave_readiness_gate.py --wave-id W76 --expect-three --brief docs/waves/w76-a-polludoc-trigger-backend.md --brief docs/waves/w76-b-polludoc-trigger-ui.md --brief docs/waves/w76-c-eco-clause-template-backend.md`

Outputs:
- `tmp/wave_gates/w76.json`
- lint and overlap reports in the same folder

Verdict:
- `PASS` when brief lint + overlap guard are both green
- `FAIL` otherwise

## 6) Wave telemetry updater

Script:
- preview:
  - `python scripts/wave_telemetry.py --wave-id W72 --clear "..." --fuzzy "..." --missing "..."`
- apply:
  - `python scripts/wave_telemetry.py --wave-id W72 --clear "..." --fuzzy "..." --missing "..." --apply`

Actions:
- increments `waves_completed`
- optionally increments `rework_count` / `blocked_count`
- updates `last_updated`
- appends wave debrief in `## Decision Log`

## 7) Lead control-plane hygiene check

Script:
- `python scripts/lead_control_plane_check.py --strict`

Checks:
- required lead/control-plane files exist
- required strategy headings are present (`AGENTS` sync invariants in lead docs + orchestrator)
- `Next 10 Actions` count stays exactly `10` in strict mode

## Agent-only operations note

These tools are intended for autonomous `Codex + ClaudeCode` execution.
Prefer running them from isolated lead flows to avoid merge contention with active Claude implementation waves.
