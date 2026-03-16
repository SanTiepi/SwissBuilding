# Continuous Review and Modernization Program

## Mission

When the major feature queue thins out, run a broad but disciplined modernization pass across SwissBuildingOS so the repo keeps improving instead of freezing around old assumptions.

This is not a random cleanup phase.
It is a structured final-pass program for:
- toolchain upgrades
- test-system hardening
- extension and integration modernization
- docs/code alignment
- low-regret refactors
- repo hygiene and performance improvements

## Why This Matters

By the time the product surface becomes large, the next source of drag is rarely one missing feature.
It is usually:
- stale tooling
- half-modernized test helpers
- weak defaults in extensions/integrations
- old assumptions in docs and scripts
- low-grade friction spread across many files

This program exists so SwissBuilding keeps compounding in quality after the main roadmap waves land.

## Strategic Outcomes

- reduce hidden friction for future waves
- keep the repo international-class as it scales
- modernize infrastructure and testing before drift accumulates
- upgrade external tools only where the gain is real
- leave the repo cleaner, more stable, and easier to extend

## Scope

### 1. Tooling modernization

Review and improve, where justified:
- frontend build/test tooling
- backend tooling
- Docker services and compose ergonomics
- repo validation scripts
- CI-facing command consistency
- local developer and agent ergonomics

Typical targets:
- build speed
- flaky tests
- stale extensions or helper patterns
- inconsistent validation commands
- outdated scripts or duplicated utilities

### 2. Extension and integration review

Review existing or planned external integrations:
- OCR / parsing stack
- Gotenberg
- Meilisearch
- observability stack
- identity/policy stack
- map stack
- queue/workflow stack

For each:
- confirm current fit
- identify low-regret upgrades
- remove dead or duplicated glue
- tighten boundaries and ownership

### 3. Test topology hardening

Review:
- backend test structure
- frontend unit tests
- mock e2e
- real e2e
- seed/verify flows
- snapshot and visual-regression stability

Improve:
- flake reduction
- fixture consistency
- helper reuse
- environment targeting
- warning noise
- validation cost vs confidence

### 4. Docs and control-plane coherence

Review and improve:
- `CLAUDE.md`
- `AGENTS.md`
- `CODEX.md`
- `MEMORY.md`
- `ORCHESTRATOR.md`
- `docs/projects/README.md`
- architecture and roadmap docs

Goals:
- no stale counters or false claims
- no duplicated truth
- control plane stays usable
- project briefs stay scannable

### 5. Low-regret refactors

Only when clearly useful:
- naming cleanup
- extract shared constants
- remove dead paths
- unify patterns
- improve boundaries between services and models

Rule:
- no vanity refactor
- no large rewrite without evidence

## Suggested Improvement Targets

These are the first systems worth reviewing once the queue reaches this program:

### 1. Search relevance and retrieval ergonomics
- grouped result quality
- evidence-first ranking
- typo tolerance vs precision
- dossier navigation shortcuts

### 2. Export and pack infrastructure
- progress visibility
- retry / resume behavior
- file-path truth
- template modularity
- storage and retrieval consistency

### 3. Real e2e ownership and environment targeting
- backend target ownership
- preflight checks
- seed prerequisites
- storage-state robustness
- env drift detection

### 4. Visual regression and snapshot discipline
- flaky snapshots
- noisy baselines
- stable screenshot naming
- reviewable baseline update flow

### 5. Background workflow recovery
- replayability
- dead-letter handling
- idempotent reruns
- job visibility and operator recovery

### 6. Seed determinism and scenario richness
- deterministic seeds where needed
- scenario coverage for newest models
- seed/runtime mismatch checks
- richer verify output

### 7. Data migration and backfill safety
- low-regret migration patterns
- backfill scripts
- rollback assumptions
- upgrade safety for rapidly growing models

### 8. Document and archive trust boundaries
- file retention assumptions
- content hashing / provenance
- export consistency
- vault/document overlap cleanup

### 9. Shared UI/system language
- i18n drift
- repeated labels
- design token consistency
- dark-mode parity

### 10. Integration boundaries
- OCR/parsing service boundaries
- dossier/export ownership
- search indexing ownership
- map stack boundaries
- identity/policy boundaries

## Workstreams

### A. Toolchain and validation audit
- map all validation commands
- identify duplicate or stale scripts
- tighten repo-first validation flow

### B. Testing and environment reliability
- reduce test noise
- reduce flake
- improve real e2e targeting
- review seed verification and preflight checks

### C. Integration modernization
- review each major external tool/integration
- propose keep / upgrade / replace / deprecate

### D. Repo coherence pass
- sync docs with code reality
- clean "future vs implemented"
- improve project brief lifecycle hygiene

### E. Performance and scale friction pass
- identify avoidable build/test slowness
- identify heavy surfaces and low-regret optimizations

### F. System review shortlist
- work through the suggested improvement targets above
- promote only the changes with clear leverage
- park or reject low-value cleanup

## Candidate Outputs

- tightened scripts/tasks
- upgraded validation docs
- improved fixtures/helpers
- simplified integration boundaries
- reduced warning/flaky surface
- updated project indexes
- modernization notes embedded in the right source-of-truth files

## Acceptance Criteria

This program is successful if:
- the repo is easier to validate than before
- the biggest remaining testing/tooling pain points are reduced
- integrations are cleaner and more intentionally chosen
- docs and control-plane files are truer and easier to navigate
- no major new debt is introduced by the cleanup

## Rules

- prefer many small high-leverage improvements over one giant rewrite
- use evidence before changing a tool or integration
- keep the moat in product logic, not in accidental tool complexity
- if a modernization is not clearly valuable, do not do it
