# SwissBuilding Working Memory

## Purpose

This file stores durable project decisions and context that should survive across sessions.
It is not a changelog. Keep it concise and high-signal.

## Current Decisions

### Roadmap Tracking

- The active next-work backlog and Claude batch packs live in `docs/roadmap-next-batches.md`.
- The long-range strategic north star lives in `docs/vision-100x-master-brief.md`.
- The broadest frontier of known ideas, uncovered uses, product engines, internal tools, and moonshots lives in `docs/product-frontier-map.md`.
- `docs/product-frontier-map.md` is the canonical idea bank for product frontier thinking:
  - new ideas should be captured there or merged into existing entries
  - ideas are not considered discarded unless they are explicitly rejected or subsumed
  - once additions become mostly duplicates, the next step is triage and sequencing, not infinite repetition
- Use that file for prioritized future work; keep this memory file limited to durable decisions.
- The roadmap is structured around 3 mega-programs delivered through 5 rupture layers:
  - Evidence OS
  - Building Memory OS
  - Action OS
  - Portfolio OS
  - Agent OS
- The category ambition is bigger than a diagnostics platform:
  - Building Intelligence Network
  - long-term operating system of the built environment
  - most ambitious framing: Built Environment Meta-OS
- Mega-Program 1 is the active priority: build the living and actionable building dossier.
- Product signature:
  - Agent OS
  - invisible agents first
  - strong proof / explainability / auditability
- Commercial strategy follows a three-layer sequence:
  - Europe-shaped category model
  - Switzerland-first launch layer
  - canton rules packs as execution layer
- Internal ambition has no artificial ceiling:
  - think Europe-scale infrastructure for building truth, proof, readiness, and orchestration
  - include owner, finance, operations, territory, and public-system layers in long-range architecture
  - sequence the visible promise by proof, not by lack of ambition
- Product quality bar is international-class, not local-tool grade:
  - Europe-ready rules and data model
  - multilingual by design
  - enterprise-grade proof, auditability, and interoperability
  - reliability and trust expected to scale beyond the initial Swiss wedge
- Primary buyer for the first wedge:
  - multi-building property managers
- Initial execution wedge:
  - VD/GE-first
  - amiante-first
  - AvT -> ApT
  - safe-to-start dossier
- External gate lock (2026-03-09):
  - scenario external #1 = `safe-to-start dossier`
  - expected gate proof:
    - one seeded building moves from raw state to complete dossier
    - progression is visible in UI
    - progression is verifiable in real e2e
- Backend freeze policy (2026-03-09 decision):
  - freeze new backend expansion for `W68-W70`
  - allow only minimal frontend-unblocker backend glue during freeze
- External gate execution artifacts (2026-03-09 decision):
  - canonical pass/fail protocol:
    - `docs/safe-to-start-gate-runbook.md`
  - canonical external demo/commercial script:
    - `docs/market/safe-to-start-demo-onepager.md`
  - both documents are optimized for `Codex + ClaudeCode` autonomous execution
- ecobau inspiration mapping (2026-03-09):
  - actionable additions captured in:
    - `docs/market/ecobau-inspiration-additions.md`
    - `docs/projects/ecobau-inspired-readiness-and-eco-specs-program.md`
  - priority bias:
    - Polludoc-style trigger assistant
    - eco tender clause generation
    - PFAS readiness extension
    - licensed ecobalance adapter strategy
  - execution visibility:
    - brief is now in `ORCHESTRATOR.md > Next ready project briefs`
- post-W80 execution phase shift (2026-03-09):
  - frontend productization sweep reached saturation (`W72-W80`: 9 waves, 27 surfaces, ~750+ i18n keys, 0 rework, 0 blocked)
  - near-term execution mode is now hardening-first:
    - validation/audit tasks first (`Next 10` ranks `1-3`)
    - infrastructure polish next (`Next 10` ranks `4-10`)
    - backend expansion frozen by default in `W81+` unless hard blocker
  - no-stop wave briefs prepared for this phase:
    - `docs/waves/w81-*.md`
    - `docs/waves/w82-*.md`
    - `docs/waves/w83-*.md`
    - `docs/waves/w84-*.md`
    - `docs/waves/w85-*.md`
- lean autonomy mode (2026-03-10):
  - objective:
    - reduce ceremony/coordination overhead while keeping acceptance rigor
  - defaults:
    - compact briefs for stable-context waves (`docs/templates/wave-brief-compact-template.md`)
    - internal agent validate loop (`run -> fix -> rerun until clean`) before handoff
    - type-first + golden-path testing bias over render-only unit-test multiplication
    - for coherent polish clusters, allow one wider-scope autonomous task instead of forced micro-splitting
- Lead automation toolkit (2026-03-09 decision):
  - canonical usage doc:
    - `docs/lead-automation-toolkit.md`
  - gate automation:
    - `scripts/safe_to_start_gate_check.py`
    - `scripts/safe_to_start_proof_bundle.py`
  - briefing and wave guardrails:
    - `scripts/brief_lint.py`
    - `scripts/wave_readiness_gate.py`
    - `scripts/wave_overlap_guard.py`
    - `scripts/wave_telemetry.py`
  - wave-ready execution briefs:
    - `docs/waves/README.md`
    - `docs/waves/w76-*.md`, `docs/waves/w77-*.md`, `docs/waves/w78-*.md`
  - control-plane discipline:
    - keep `ORCHESTRATOR.md > Next 10 Actions` to exactly 10 ranked items
    - keep overflow queue in a separate section (`Next Queue (11+)`)
  - AGENTS-strategy sync enforcement:
    - `scripts/lead_control_plane_check.py --strict` now checks required invariant sections in:
      - `ORCHESTRATOR.md`
      - `docs/lead-master-plan.md`
      - `docs/lead-parallel-operating-model.md`
- Diagnosticians and labs are contributors first, not the primary initial buyer.
- ERP posture:
  - overlay first
  - no rip-and-replace claim
- Liability posture:
  - completeness / provenance / workflow traceability
  - no legal-compliance guarantee claim
- Claude prompts should stay compact and rely on shared repo docs for standing context.
- Large Claude prompts default to ORCHESTRATOR-driven supervision:
  - prompts stay compact
  - shared repo docs carry the standing context
  - `ORCHESTRATOR.md` carries the active execution frame
- `ORCHESTRATOR.md` should keep a live ranked view of the next 10 executable actions whenever meaningful work remains, so Claude can sequence waves without waiting for a new brief.
- `ORCHESTRATOR.md` should also maintain a rolling medium-range runway (roughly 60 days) so Claude can keep shipping through multiple waves without strategic interruption.
- architecture and object design should also stay compatible with a deliberately oversized 48-month horizon captured in the roadmap, vision brief, and frontier map
- Current execution posture is now explicitly:
  - better before broader
  - depth, integration, and productization over raw feature count
  - consolidate overlapping services before adding more primitives
  - prefer realistic datasets, full-chain validation, and real UX consumption over isolated backend capability growth
- Repo operating split:
  - Codex owns strategic ambition, product/category expansion, roadmap direction, market synthesis, prompt design, and acceptance review
  - Codex should also keep feeding future steps, low-regret anticipations, and upcoming program hints into repo docs/control-plane files while Claude executes
  - Codex is the execution pilot:
    - Claude executes scoped tasks delegated by Codex
    - Codex defines task order, non-negotiable constraints, validations, and exit criteria
    - work is accepted only after Codex review against these criteria
    - when Claude is already in a productive implementation wave, Codex should prefer outcome-level steering over step-by-step micromanagement
    - default delegation style should be:
      - mission and expected business outcome
      - non-negotiable constraints
      - validation and exit criteria
      - implementation path left to Claude
    - wave closeout should include a short debrief loop in `ORCHESTRATOR.md`:
      - `clear`
      - `fuzzy`
      - `missing`
    - rolling execution counters should be maintained in `ORCHESTRATOR.md`:
      - waves completed
      - rework count
      - blocked count
    - canonical execution brief format lives in:
      - `docs/templates/project-brief-template.md`
      - `docs/templates/wave-brief-compact-template.md`
    - multi-agent wave sizing, task granularity, and hub-file merge discipline live in:
      - `docs/agent-execution-patterns.md`
    - active-wave prioritization is consumer-first:
      - tasks should have a visible product consumer within `<=2` waves
      - ring_4/infrastructure tasks without near-term consumers should be deprioritized
    - near-term execution bias should stay:
      - `frontend productization : backend expansion ~= 2:1` unless a hard blocker requires backend-first
      - during polish/hardening clusters, wave sizing can shift to `1` wider-scope task when it lowers coordination overhead
    - execution-ground feedback should be captured in `ORCHESTRATOR.md`:
      - `Claude observations channel`
    - operating assumption is agent-only by default:
      - execution should be optimized for Codex + ClaudeCode without human-in-the-loop dependencies
    - continuity rule:
      - execution should auto-continue from `Next 10` -> `Next ready project briefs` -> `Future Horizon Feed` without waiting for a new prompt when work remains
  - Codex is expected to stay ahead of execution:
    - orchestrate what comes next
    - keep the next waves legible
    - push the frontier beyond the currently implemented surface
    - operate continuously across 4 parallel streams:
      - execution foresight
      - product frontier expansion
      - acceptance / QA parallelism
      - market / category / moat pressure
  - Claude Code owns execution-heavy delivery, agent supervision, and implementation waves
- `docs/lead-parallel-operating-model.md` is the repo reference for what Codex should keep doing while Claude is executing
- `docs/lead-master-plan.md` is the canonical structured planning layer for Codex's parallel lead work
- `docs/lead-ongoing-backlog.md` is the durable long-form backlog Codex should keep advancing while Claude executes implementation waves
- Initial market wedge:
  - pollutant diagnostics before renovation
  - chosen for legal pressure, data acquisition, and strong workflow pain
- Demo wow target:
  - living building dossier
  - portfolio steering
- The official scope map is intentionally broader than the visible wedge and should already account for:
  - building truth
  - works
  - operations
  - ownership
  - occupancy
  - finance
  - insurance
  - sale
  - procedure
  - portfolio
  - ecosystem exchange
- The roadmap should now be read in 12 macro-domains and 4 concentric rings:
  - macro-domains prevent under-modeling future layers
  - rings preserve execution discipline
- Differentiating product value should focus on:
  - proof
  - memory
  - orchestration
  - portfolio
  - controlled agency
- Moonshot target concepts:
  - Building Passport
  - Evidence Graph
  - Readiness Engine
  - Post-Works Truth
  - Portfolio Intelligence
  - European rules layers
- Long-range owner-facing expansion is intentional:
  - owner operating layer
  - renovation budgets and reserve planning
  - digital vault for building-critical records
  - insurance policy and claims operations
  - the product can evolve toward a true building super app if these layers stay grounded in building truth
- Preferred platform boosters by integration order:
  - now: `OCRmyPDF`, `Dramatiq + Redis`, `ClamAV`
  - next: `Gotenberg`, `Meilisearch`, `GlitchTip`
  - later if needed: `Docling`, `PaddleOCR`
- The broader 2026 open-source pull radar lives in `docs/projects/open-source-accelerators-2026-radar.md` and should be used when deciding whether to build or pull a capability.

### Vaud Ingestion

- Use official public sources, not map UI scraping.
- Do not mix:
  - Vaud public layer mappings
  - RegBL / MADD bulk mappings
- Keep `python -m app.seeds.seed_data` network-free.
- Use `python -m app.seeds.seed_demo ...` when a local demo dataset should be enriched with public Vaud buildings.

### Test Topology

- Keep mock Playwright and real Playwright suites separate.
- `npm run test:e2e` validates mocked UI flows quickly.
- `npm run test:e2e:real` validates the real frontend against Docker-backed backend + seeded dataset.
- The real suite authenticates once via storage state setup to avoid login rate-limit noise.
- Dataset strategy should be layered and scenario-based now, not deferred until the end:
  - demo dataset
  - ops/truth dataset
  - portfolio dataset
  - compliance dataset
  - multimodal dataset
  - edge-case dataset
- Treat seeds as product infrastructure, not only test fixtures.

### Building Identifiers

- `egid` != `egrid` != `official_id`
- Keep them separate in models, schemas, and imports.

## Known Public Vaud Layers

### `vd.adresse` (layer 241)

Primary use:

- address records
- `EGID`
- `EDID`
- locality / municipality

### `vd.batiment_rcb` (layer 39)

Primary use:

- public cantonal building registry attributes
- construction year
- building category / class
- heating / hot water metadata
- point geometry

### `vd.batiment` (layer 276)

Currently imported via `fetch_batiment_record()`:

- polygon footprint (rings geometry)
- cadastral building attributes (NO_COM_FED, GENRE_TXT, DESIGNATION_TXT, SURFACE, etc.)
- stored in `source_metadata_json.batiment`

## Current Gaps Still Outside Scope

- owner / land registry data
- EGRID from a trustworthy public cadastral join
- full-canton bulk import from MADD / RegBL
- non-Vaud ingestion

## Maintenance Rule

Update this file only when a decision changes future work, not for every implementation detail.
