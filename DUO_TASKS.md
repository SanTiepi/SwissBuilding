# DUO_TASKS — Autonomous Improvement Backlog

## Active
- (backlog empty — awaiting new tasks)

## Pending (Priority Order)
- (none)

## Completed
- `SB-11` Alert system for stale evidence: SKIP — already implemented (freshness_watch_service, change_signal_generator, notification_digest_service) (2026-03-29)
- `SB-10` Building dossier export: SKIP — already implemented (dossier_service + Gotenberg PDF + API route) (2026-03-29)
- `SB-09` Risk scoring engine: SKIP — already fully implemented with tests and 8 API routes (2026-03-29)
- `SB-08` Test gap hunt: 63 new tests for 2 zero-coverage extraction services + fixed regex bug in extract_scope (2026-03-29)
- `SB-07` Schema coverage: only 1 endpoint lacked validation (building_dashboard batch), fixed (2026-03-29)
- `SB-06` Error response audit: fixed 7 exception detail leaks in 500/502 responses (security) (2026-03-29)
- `SB-04` Remove 4 dead services: temporal_utils, value_notification_hooks, authority_extraction_service, contract_extraction_service — 2866 lines + 1735 test lines removed (2026-03-29)
- `SB-03` Blast radius: all 4 dead services safe to delete (0 runtime consumers) (2026-03-29)
- `SB-02` Classify 24 orphan services — 16 active (inventory error), 4 dead code, 2 broken import, 2 planned (2026-03-29)
- `SB-01` Inventory + consumer graph — 258 services, 24 orphans identified, hub services mapped (2026-03-29)

## Bugs Found
- `BUG-01` `_classify_generic_result` in diagnostic_extraction_service: positive keyword "détecté" matches as substring inside "non détecté", causing false positives. Negative keywords should be checked BEFORE positive ones.

## Rules
- One task at a time
- Run targeted tests after each change (not full suite unless justified)
- Run `pre_commit_check.py --fast` as gate
- Commit on branch `duo/improvements` only
- If tests break unexpectedly → stop, report, don't push forward
