# Claude Next Wave Selector

Date de controle: `25 mars 2026`

## Purpose

This is the shortest decision tree for choosing the next wave without
rethinking the entire strategy.

## Step 1 - Is the repo noisy or truly blocked?

Choose `technical cleanup` if:

- failures are homogeneous
- validation noise is dominating progress
- a cluster can be swept

Use:

- [auth-regression-sweep-pack-2026-03-25.md](./auth-regression-sweep-pack-2026-03-25.md)

Choose `feature wave` only if:

- the current regression cluster is closed
- the smallest confidence loop is green

## Step 2 - Which question matters most now?

### A. "What makes the product more real right now?"

Pick one:

- `Brief 1`
- `Brief 2`
- `Brief 3`
- `Brief 4`
- `Brief 5`
- `Brief 25`
- `Brief 26`
- `Brief 27`
- `Brief 28`
- `Brief 29`
- `Brief 30`
- `Brief 31`
- `Brief 32`
- `Brief 33`
- `Brief 34`
- `Brief 35`
- `Brief 36`
- `Brief 38`
- `Brief 39`
- `Brief 40`
- `Brief 41`
- `Brief 42`
- `Brief 43`
- `Brief 44`

### B. "What makes the moat stronger?"

Pick one:

- `Brief 6`
- `Brief 7`
- `Brief 8`
- `Brief 9`
- `Brief 12`

### C. "What makes the product easier to adopt?"

Pick one:

- `Brief 16`
- `Brief 17`
- `Brief 18`
- `Brief 19`
- `Brief 22`
- `Brief 37`
- `Brief 45`
- `Brief 46`
- `Brief 47`
- `Brief 48`
- `Brief 49`
- `Brief 52`
- `Brief 53`
- `Brief 54`
- `Brief 55`
- `Brief 56`
- `Brief 57`

### D. "What prepares the long game?"

Pick one:

- `Brief 13`
- `Brief 14`
- `Brief 15`
- `Brief 20`
- `Brief 23`
- `Brief 24`

## Step 3 - Filter by dependency truth

Do not pick a wave if its preconditions are not true.

Examples:

- do not pick `Authority Flow` before procedure and proof are credible
- do not pick `Partner Trust` before proof delivery and acknowledgement signals exist
- do not pick `Benchmarking` before canonical workflow truth exists
- do not pick `Embedded Channels` before bounded pack or viewer semantics are credible

Use:

- [claude-wave-opportunity-map-2026-03-25.yaml](./claude-wave-opportunity-map-2026-03-25.yaml)

## Step 4 - Filter by validation cost

Pick the wave whose validation loop is smallest among the valuable options.

Use:

- [claude-validation-matrix-2026-03-25.md](./claude-validation-matrix-2026-03-25.md)

Rule:

- if two waves have similar value, choose the one with the cheaper proof loop

## Step 5 - Pick only one shape

Choose:

- one core wave
- or one moat wave
- or one adoption wave

Do not mix all three in one go unless the write scopes are truly disjoint.

## Fast recommendations

### If Claude just got unstuck from validation noise

Best immediate picks:

- `Brief 1`
- `Brief 2`
- `Brief 3`
- `Brief 25`
- `Brief 26`
- `Brief 27`
- `Brief 28`
- `Brief 29`
- `Brief 30`
- `Brief 31`
- `Brief 32`
- `Brief 33`
- `Brief 34`
- `Brief 35`
- `Brief 36`

### If a demo or buyer conversation is near

Best immediate picks:

- `Brief 16`
- `Brief 18`
- `Brief 19`
- `Brief 37`
- `Brief 45`
- `Brief 46`
- `Brief 47`
- `Brief 48`
- `Brief 49`

### If the goal is future-proofing without visible feature sprawl

Best immediate picks:

- `Brief 5`
- `Brief 8`
- `Brief 13`

### If the goal is public-sector credibility

Best immediate picks:

- `Brief 20`
- `Brief 24`
- `Brief 15`
- `Brief 47`
- `Brief 51`

## Final rule

When in doubt:

1. choose the wave that strengthens canonical truth
2. prefer proof and procedure over breadth
3. prefer one finished slice over three half-wired slices
