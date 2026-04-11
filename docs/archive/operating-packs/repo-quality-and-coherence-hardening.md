# Repo Quality and Coherence Hardening

## Mission

Raise the repo from "ambitious and shipping fast" to "international-class and internally coherent".

This is not a feature project.
It is a repo-hardening project focused on:

- documentation truthfulness
- naming coherence
- API surface discoverability
- reduction of structural drift between code, docs, and control-plane files

## Why This Matters

The product is expanding quickly.
At this pace, the next quality failure is unlikely to be "missing idea".
It is more likely to be:

- stale architecture docs
- duplicated or obsolete "future" objects that are already implemented
- naming leaks that confuse future contributors and agents
- too many project briefs without clear active/ready/archive discipline
- repo guidance drifting away from the actual code surface

If this is not cleaned up periodically, execution speed will stay high but coherence will degrade.

## Concrete Audit Findings Already Observed

### 1. Architecture docs are stale against the real codebase

Observed:
- `docs/architecture.md` still describes an older "current core schema"
- it only lists a small subset of the actually implemented models
- its `Reserved Future Product Domains` section still includes domains that are now already implemented

Reality signals:
- `backend/app/models/__init__.py` exports far more domains than the architecture doc currently describes
- `backend/app/api/router.py` registers a much broader API surface than the top-level docs imply

### 2. Reserved-vs-implemented object drift exists

Examples of objects that should no longer be treated as purely future in repo docs:
- `EvidenceLink`
- `ActionItem`
- `Campaign`
- `Assignment`
- `ExportJob`
- `SavedSimulation`
- `DataQualityIssue`
- `ChangeSignal`
- `ReadinessAssessment`
- `BuildingTrustScore`

The docs should be explicit about:
- what is already implemented
- what is productized
- what exists only as backend foundation
- what is still genuinely future

### 3. Naming drift is starting to leak into the codebase

Observed:
- `backend/app/models/building_trust_score_v2.py` exposes `BuildingTrustScore`

This kind of version suffix is understandable during iteration, but it should not become permanent repo vocabulary unless a real migration/versioning strategy requires it.

### 4. Project brief sprawl needs light governance

Observed:
- `docs/projects/` now contains many program briefs
- that is good for runway, but they need clearer lifecycle:
  - active
  - ready
  - parked
  - archived

Otherwise, the repo risks becoming rich but ambiguous.

### 5. Test stack is strong but still noisy

This overlaps with the testing modernization project, but it is also a coherence issue:
- frontend unit noise still exists
- real e2e environment ownership is still fragile

This project should not redo testing modernization, but it should ensure the docs and control plane describe the state accurately.

## Scope

### Workstream A — Architecture and schema truth sync

Update:
- `docs/architecture.md`

Expected:
- current schema section reflects the real implemented model surface at a useful level
- layered model remains readable
- implemented vs future is clearly separated

### Workstream B — Reserved future domains cleanup

Update:
- `docs/architecture.md`
- `docs/roadmap-next-batches.md`
- `README.md` only if needed

Expected:
- remove implemented objects from "future only" sections
- replace with cleaner wording:
  - implemented now
  - foundation present
  - future target

### Workstream C — Naming and taxonomy cleanup

Audit and decide on low-regret cleanup for:
- `building_trust_score_v2.py`
- any other `v2`, temporary, or misleading names that have become semi-permanent
- router/tag/resource naming consistency

Rule:
- do not rename just for vanity
- rename only when it clearly improves long-term coherence and is low-risk

Support tooling now available:
- `python scripts/router_inventory.py --write`
- `python scripts/router_inventory.py --strict`
- outputs:
  - `docs/router-inventory.md`
  - `docs/router-inventory.json`

### Workstream D — Project brief lifecycle governance

Add a light lifecycle discipline for `docs/projects/`:
- active
- ready
- parked
- archived

The goal is not process overhead.
The goal is fast scanning and less ambiguity for Claude and future agents.

### Workstream E — Repo source-of-truth mapping

Make the repo clearer about where truth lives:
- `README.md` = external/high-level product and setup
- `CLAUDE.md` = Claude bootstrap
- `AGENTS.md` = repo working rules
- `MEMORY.md` = durable decisions
- `ORCHESTRATOR.md` = active execution control plane
- `docs/roadmap-next-batches.md` = long-range execution structure
- `docs/product-frontier-map.md` = idea frontier
- `docs/projects/` = executable project briefs

This mapping already exists implicitly.
Make sure it is explicit enough and not self-contradictory.

## Acceptance Criteria

This project is complete when:

- architecture docs no longer understate the actual implemented system
- "reserved future domains" sections no longer list clearly implemented objects as if they were absent
- misleading file/version naming is either cleaned up or explicitly justified
- `docs/projects/` lifecycle is easier to scan
- repo docs form a coherent hierarchy of truth without obvious contradictions
- the repo feels easier to understand for a new high-context agent

## Validation

If docs only:
- ensure internal consistency across:
  - `README.md`
  - `CLAUDE.md`
  - `AGENTS.md`
  - `MEMORY.md`
  - `ORCHESTRATOR.md`
  - `docs/architecture.md`
  - `docs/roadmap-next-batches.md`
  - `docs/projects/*` metadata if added

If any code or naming changes:

Backend:
- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend if touched:
- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run build`

## Notes

This project should improve comprehension and execution speed, not create a documentation bureaucracy.

Prefer:
- fewer, clearer truths
- less stale "future" language
- cleaner naming
- faster scanning

Avoid:
- large cosmetic rewrites
- process theatre
- renaming stable public concepts without a clear payoff
