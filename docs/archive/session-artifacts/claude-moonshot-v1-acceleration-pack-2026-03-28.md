# Claude Moonshot V1 Acceleration Pack

Date: 28 mars 2026
Status: Active acceleration pack for the current moonshot
Use when: Claude is executing the current Moonshot V1 and needs directly reusable instruction content
Depends on:
- `docs/projects/v3-master-future-steps-plan-2026-03-28.md`
- `docs/projects/v3-master-plan-addendum-frontier-layers-2026-03-28.md`
- `docs/projects/v3-meta-layers-plan-2026-03-28.md`
- `docs/projects/claude-moonshot-evaluation-and-feedback-pack-2026-03-28.md`
- `AGENTS.md`
- `MEMORY.md`
- `ORCHESTRATOR.md`

---

## Purpose

This pack exists to help Claude move faster on Moonshot V1 without:

- reopening settled doctrine
- fragmenting the work into new conceptual branches
- over-coordinating
- or broadening endlessly instead of closing the nucleus

It is not a replacement for the moonshot plan.
It is a **speed layer**:

- assumptions Claude may safely make
- default heuristics when the path is ambiguous
- copy-paste instruction blocks the user can send directly
- closeout-oriented framing that preserves autonomy

---

## What Claude Should Assume by Default

Claude should assume all of the following without asking again unless a real blocker appears:

- the doctrine V3 is already decided
- the root families are already decided
- `BuildingCase` is the operating root
- `ritual_service` is the sole transition layer
- the shell stays:
  - `Today`
  - `Buildings`
  - `Cases`
  - `Finance`
  - `Portfolio`
- projections and redaction are preferred over actor-specific truth stores
- external writes remain controlled through import, validation, provenance, and rituals
- `Moonshot V1` is about **closing and deepening the canonical system**, not inventing a new doctrine

---

## Default Heuristics When Claude Needs to Choose Quickly

### 1. Close before broadening

If a choice exists between:

- finishing a partial canonical layer
- or opening a new high-potential layer

default to:

- finishing the partial canonical layer

unless the new layer directly removes a blocker for core closure.

### 2. Integrate before adding a primitive

If the user-facing gain can come from:

- an aggregate read model
- a projection
- a registry
- a ritual hook
- a bridge

do that before adding a new persistent primitive.

### 3. Prefer write-side severity, read-side generosity

Claude should be generous in:

- projections
- role views
- contextual workspaces
- exchange subsets

But severe in:

- roots
- transitions
- status grammars
- truth ownership

### 4. If uncertain, make the system more explainable

Default toward the implementation that improves:

- provenance
- freshness
- unknowns visibility
- caveats
- temporal validity
- explicit review or invalidation

### 5. Keep the product center of gravity in 3 places

If a new feature feels like it wants its own center, prefer attaching it to:

- `Building Home`
- `Case Room`
- `Today`

unless it is clearly finance- or portfolio-native.

---

## What Claude Should Optimize For

Claude should optimize for:

- fewer but more integrated waves
- coherent product jumps
- explicit closeout evidence
- measurable throughput
- doctrinal severity under pressure

Claude should not optimize for:

- maximum object count
- maximum route count
- maximum surface count
- speculative breadth with weak integration

---

## What Counts as Useful Progress

Useful progress on V1 means at least one of:

- a core block becomes closer to actual closure
- a frontier layer becomes real and consumable in canonical workspaces
- a meta-layer becomes operational and governs real flows
- a compatibility surface becomes more clearly subordinate
- a partial implementation becomes integrated enough to stop being misleading

Work that is not useful enough by default:

- renaming without stronger semantics
- adding isolated models without clear consumers
- duplicating state transitions in multiple services
- shipping a new page that behaves like a truth center outside the shell

---

## Directly Reusable User-to-Claude Instruction Blocks

These are meant to be pasted directly into Claude when helpful.

### Block A — V1 Continuation

```md
Continue Moonshot V1.

Assume the doctrine, root families, shell, `BuildingCase` operating root, and `ritual_service` transition doctrine are all already decided.

Do not reopen those debates.
Do not broaden just because a new idea is attractive.
Default to closing the most central partial canonical layer in front of you.

Optimize for:
- integrated closure
- measurable throughput
- doctrinal severity
- no parallel truth
- no new top-level centers

At the end, return:
- what block or layer moved materially closer to closure
- what remains partial
- what should be integrated before broadening
- validations run
- exact counters or throughput evidence updated
```

### Block B — Closeout-First Mode

```md
Work in closeout-first mode.

Treat Moonshot V1 as something to finish, not something to endlessly widen.

For every touched area, classify it implicitly or explicitly as:
- canonical
- subordinate
- compatibility-only
- deprecated

If you find a partial system, prefer:
- merge
- integrate
- make clearly subordinate
- or hide/defer

Do not add a new major center of gravity unless it is unavoidable to close the active block.
```

### Block C — Autonomy-Preserving Guardrails

```md
You have implementation autonomy.

Do not stop for routine confirmation.
Make reasonable choices yourself.

Only escalate if:
- a real blocker exists
- a destructive migration is required
- two valid paths have materially different long-term consequences

Otherwise:
- choose the path that preserves canonical severity
- keeps the repo more governable
- and reduces future retrofit debt
```

### Block D — Integration Before Expansion

```md
Before adding any new model, service, API, or page, ask internally:

1. Can this be expressed as a projection or aggregate over existing canonical roots?
2. Can this be expressed as a ritual, invalidation, or review path instead of new state?
3. Can this be attached to Building Home, Case Room, or Today instead of becoming its own center?
4. Does this remove active ambiguity or just add optional richness?

If the answer points to integration, integrate first.
```

### Block E — Return Format

```md
Return in this format:

1. Material progress
- what core block, frontier layer, or meta-layer actually advanced

2. Canonical impact
- what became more canonical, more subordinate, or more integrated

3. Remaining partials
- what is still not truly closed

4. Risks or drift
- anything that could create parallel truth, status sprawl, or isolated power centers

5. Validation
- exact commands run
- exact result

6. Recommended next wave
- integrate before broadening / continue same block / move to next block
```

---

## Fast Decision Rules for Common Situations

### If a compatibility bridge still exists

Default:

- keep it stable
- do not add new semantics there
- bridge from canonical outward

### If two objects overlap semantically

Default:

- identify the canonical owner
- reduce the other to subordinate, bridge, or deprecated status

### If a new workspace feels tempting

Default:

- embed it under an existing hub or contextual workspace

### If tests are expensive

Default:

- run the smallest high-signal loop first
- prove one golden path where the change is category-important

### If the wave is getting too broad

Default:

- cut outer-ring ambitions
- preserve the nucleus
- report the cut explicitly instead of silently carrying debt

---

## What to Feed Claude as Ready-to-Use Content

The user can help Claude most by giving one of these, not long free-form prompts:

### 1. A bounded objective

Example:

- "close the invalidation engine enough that it is canonical and reusable"
- "finish the projection registry and absorb the last obvious orphan read models"
- "make Trust Ops operational in Today and Case Room instead of merely modeled"

### 2. A doctrinal constraint bundle

Example:

- no new root
- no new top-level surface
- no semantics in compatibility bridges
- no transition outside `ritual_service`

### 3. A return contract

Example:

- show closure evidence
- list remaining partials
- identify what must be integrated before the next wave

This saves Claude much more time than giving more background theory.

---

## Suggested User Prompt Patterns

### Pattern 1 — Finish a Block

```md
Continue Moonshot V1 and close the most central remaining gap in Block X.

Assume doctrine is settled.
No new top-level center.
No new semantics in compatibility layers.
Prefer integration over new primitives.

Return with:
- what is actually closed
- what is still partial
- what should be cut or deferred
- validations run
```

### Pattern 2 — Integrate a Partial Cluster

```md
Take the current partial cluster around X and turn it into one coherent canonical slice.

Do not broaden scope.
Merge, subordinate, bridge, or deprecate where needed.
Prefer one stronger integrated result over several parallel improvements.

Return with:
- canonical owner
- subordinate surfaces
- compatibility surfaces
- drift risks removed
- validations run
```

### Pattern 3 — Push Hard Without Reopening Doctrine

```md
Push aggressively on Moonshot V1, but do not reopen settled doctrine.

Assume:
- root families are fixed
- shell is fixed
- BuildingCase is the operating root
- ritual_service owns transitions

Choose the highest-leverage path yourself and execute it end to end.
At the end, tell me what got materially closer to true closure.
```

---

## How to Help Claude Without Constraining Him Too Much

Good help:

- compact mission
- hard doctrinal constraints
- acceptance criteria
- permission to choose the implementation path

Bad help:

- restating the whole vision every time
- reopening V1 vs V2 debates mid-wave
- asking for tiny cosmetic updates while he is on a deep integration path
- making him justify every normal tradeoff

Rule of thumb:

- give Claude the destination and the walls
- let him pick the road

---

## Acceptance

This acceleration pack succeeds only if:

- Claude receives less repeated context
- Claude preserves more autonomy, not less
- V1 closes faster because the instructions are sharper
- the team gets more integrated progress and fewer loosely related expansions
