# Authority Adapter Priority Map

Date de controle: `25 mars 2026`

## Purpose

Authority integration should not start as "all authorities, all channels".

It should start with a clear adapter map:

- where to watch
- where to model procedures
- where to prepare channel adapters
- where manual review remains the right default

## Priority map

### Tier A - procedural anchor jurisdictions

These should anchor the first real authority-aware flows.

#### Vaud / CAMAC

- role: primary cantonal permit anchor
- current source: `vd_camac`
- adapter posture:
  - source watch now
  - procedure template now
  - submission adapter later
- why: high procedural value, explicit portal and permit framing

#### Geneve / autorisation de construire

- role: second cantonal permit anchor
- current source: `ge_building_auth`
- adapter posture:
  - source watch now
  - procedure template now
  - submission adapter later
- why: strong permit path and protected/sensitive case relevance

#### Fribourg / SeCA

- role: third permit anchor
- current source: `fr_seca`
- adapter posture:
  - source watch now
  - procedure template now
  - submission adapter later
- why: useful triangulation beyond `VD/GE`

### Tier B - federal and execution bodies

These are essential for rule depth and filings, even when they are not
full "authority submission" channels in the same way.

#### SUVA

- role: execution and notification body
- current source: `suva_asbestos`
- adapter posture:
  - filing requirement now
  - workflow adapter later

#### BAFU / BAG / ARE / BAK / EBGB

- role: rule and guidance anchors
- adapter posture:
  - watch now
  - explainability now
  - direct submission adapter mostly not first priority

### Tier C - communal authorities

These should stay mostly `manual_review` until a pilot commune strategy exists.

- role: commune-specific permits, zoning, aesthetics, local constraints
- adapter posture:
  - communal placeholder now
  - pilot commune adapters later
  - no fake national communal automation

Pilot shortlist reference:

- [pilot-commune-candidates-2026-03-25.md](./pilot-commune-candidates-2026-03-25.md)

### Tier D - utilities and concession bodies

These are important but should come after procedure and authority basics.

- role: network and concession constraints
- adapter posture:
  - source map later
  - adapter after core authority flow exists

## Adapter types

### Watch adapter

Purpose:

- monitor source or portal change

Good for:

- most official pages

### Procedure adapter

Purpose:

- map local process into steps, blockers, requests, and required proof

Good for:

- `VD`, `GE`, `FR`, pilot communes

### Submission adapter

Purpose:

- prepare real channel-specific sending or export constraints

Good for:

- later phase only, after local procedure semantics are stable

### Manual-review adapter

Purpose:

- explicitly say the case is local, ambiguous, or not machine-ready

Good for:

- communal specifics
- protected buildings
- mixed or special-use cases

## Product rule

No authority adapter should be built if it does not improve at least one of:

- procedural clarity
- required proof clarity
- blocker visibility
- routing to the right authority

If it only adds metadata without changing workflow quality, it is not yet worth
the build cost.
