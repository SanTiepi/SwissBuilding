# Safe-to-Start External Gate Runbook

## Purpose

Provide one canonical, agent-only pass/fail protocol for external scenario #1:
`safe-to-start dossier`.

This runbook is designed for `Codex + ClaudeCode` execution with no human-in-the-loop dependency.

## Gate Lock

- gate: `safe-to-start dossier`
- lock date: `2026-03-09`
- required proof:
  - one seeded building moves from raw dossier state to complete dossier state
  - the progression is visible in UI
  - the progression is verifiable in real e2e

## Non-Negotiable Constraints

- keep backend expansion freeze policy active (`W68-W70`), except minimal frontend-unblocker glue
- no legal-compliance-guarantee claims
- keep `egid`, `egrid`, and `official_id` distinct
- rely on official data flows and repo-native validation commands

## Canonical Scenario Buildings

The real e2e smoke suite now verifies 5 canonical scenario buildings from `seed_data.py`.
The dossier progression proof chain uses these specific buildings:

| Scenario | Address fragment | Dossier state | Key data |
|----------|-----------------|---------------|----------|
| `empty_dossier` | "Nouveau Import" | Raw — no diagnostics | Baseline: zero enrichment |
| `contradiction` | "Contradictions" | Partial — conflicting diagnostics | 2+ diagnostics (positive + negative) |
| `portfolio_cluster` | "Lot Portefeuille" | Partial — portfolio member | Cluster grouping |
| `post_works` | "Post-Travaux" | Advanced — completed intervention | Diagnostics + interventions |
| `nearly_ready` | "Presque Prêt" | Near-complete — validated diagnostics + artefacts | Diagnostics + artefacts + samples |

**Progression proof**: `empty_dossier` (0 diagnostics, 0 artefacts) vs `nearly_ready` (1+ diagnostics, 1+ artefacts).

## Pass Criteria

All checks below must be green.

| Check ID | Requirement | Evidence |
|----------|-------------|----------|
| G1 | Seeded scenario exists and passes threshold checks | `python -m app.seeds.seed_verify` exits `0` |
| G2 | Real environment targeting is correct before test run | `npm run test:e2e:real:preflight` exits `0` — must find all 5 scenario buildings |
| G3 | Real e2e suite passes against SwissBuilding backend | `npm run test:e2e:real` exits `0` — includes dossier progression tests |
| G4 | UI progression raw -> complete is visible on the same building chain | screenshot audit files + smoke progression tests |
| G5 | Safe-to-start positioning remains claim-disciplined | pack/readiness surfaces include non-guarantee posture |

Any failed check blocks gate acceptance.

## Canonical Execution Sequence

Run commands from repo root in this order.

1. Infrastructure up

Infrastructure runs on VPS via Docker Compose (not local Docker Desktop).
Ensure the VPS backend is reachable before proceeding.

```bash
# On VPS (via SSH):
cd infrastructure && docker compose up -d
# Or verify VPS is already running:
curl -s https://<vps-domain>/api/v1/health
```

2. Backend seed for realistic Vaud scenario

```powershell
cd ../backend
python -m app.seeds.seed_demo --commune Lausanne --limit 150
python -m app.seeds.seed_verify
```

3. Backend quality baseline

```powershell
ruff check app/ tests/
ruff format --check app/ tests/
```

4. Frontend quality baseline

```powershell
cd ../frontend
npm run validate
```

5. Real e2e preflight gate

```powershell
npm run test:e2e:real:preflight
```

Expected output includes:
- `All 5 canonical scenario buildings present`
- `All scenario data checks passed`
- `Real e2e preflight passed`

If preflight fails with "Missing canonical scenario buildings", re-run step 2 with `python -m app.seeds.seed_data` first.

6. Real e2e gate execution

```powershell
npm run test:e2e:real
```

Expected test groups:
- `Smoke tests — real backend` (9 tests): page load + content verification
- `Canonical dossier progression — seeded scenario` (7 tests): scenario building existence, data depth, and progression proof

7. UI evidence capture for desktop + mobile (recommended for gate dossier)

```powershell
npx playwright test -c playwright.real.config.ts screenshot-audit.spec.ts
```

## Mandatory Evidence Bundle

Keep these artifacts together for the gate decision:

- command transcript (or summarized command outputs) for steps 2-7
- preflight output proving backend target is SwissBuilding and all 5 scenario buildings found
- real e2e result summary (passed/failed tests by project)
- screenshot files from `frontend/test-results/real-audit-*.png`
- one explicit note identifying the canonical progression pair: `empty_dossier` vs `nearly_ready`
- one explicit note confirming claim discipline (`readiness support`, not `legal guarantee`)

## Rejection Triggers

Reject gate acceptance if any condition is true:

- preflight points to wrong backend or cannot authenticate
- preflight cannot find canonical scenario buildings
- seed verification fails thresholds
- real e2e is skipped, red, or run only on mocked suite
- progression proof is split across unrelated buildings (must use scenario buildings)
- summary claims legal compliance guarantee
- reported output is not reproducible with repo commands

## Recovery Fast-Path

If preflight fails, use this recovery order:

1. Ensure VPS infra is running: `ssh ubuntu@83.228.221.188 "cd /opt/swissbuilding/infrastructure && docker compose ps"`
2. Re-seed via SSH:
   - `python -m app.seeds.seed_data` (ensures scenario buildings exist)
   - `python -m app.seeds.seed_demo --commune Lausanne --limit 150`
3. Re-verify:
   - `python -m app.seeds.seed_verify`
4. If backend port differs from `:8000`, set:
   - `E2E_REAL_API_BASE`
   - `VITE_API_PROXY_TARGET`
5. Re-run preflight, then real e2e.

## Exit Decision Template

Use this exact structure for gate closeout:

- status: `PASS` or `FAIL`
- failed_checks: `[Gx, ...]` (empty on pass)
- seeded_building_progression: `empty_dossier (id) → nearly_ready (id)`
- ui_progression_proof: `<paths to screenshots>`
- real_e2e_summary: `<project counts — smoke + dossier progression>`
- residual_risks: `<explicit list or "none">`
