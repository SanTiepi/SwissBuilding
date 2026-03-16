# Expert Review, Disagreement, and Override Governance Program

## Mission

Give SwissBuildingOS a first-class way to capture expert disagreement, human overrides, review outcomes, and confidence adjustments without collapsing everything into a single "system truth".

## Why This Matters

As the product grows more intelligent:

- experts will disagree with the system
- experts will disagree with each other
- humans will override recommendations
- confidence and justification will need governance, not just state changes

If this is not modeled explicitly, institutional memory and trust both degrade.

## Core Outcomes

### 1. Human disagreement is a first-class object

Expected:

- disagreement with:
  - system output
  - another expert
  - source interpretation

### 2. Overrides preserve rationale

Expected:

- no silent override of trust/readiness/compliance states
- every override captures:
  - who
  - why
  - evidence basis
  - scope
  - expiry/review need if relevant

### 3. Review state is governable

Expected:

- expert review queue
- peer review or QA review states where useful
- ability to distinguish:
  - system suggestion
  - accepted truth
  - disputed truth
  - temporary override

## Recommended Workstreams

### Workstream A - Review and override objects

- define first-class records for:
  - review
  - disagreement
  - override
  - confidence adjustment

### Workstream B - UI surfacing

- show disputes and overrides where they matter:
  - readiness
  - trust
  - contradictions
  - passport
  - packs

### Workstream C - Governance and audit

- make disagreement/override history exportable and auditable
- connect to decision replay and operator memory

## Acceptance Criteria

- SwissBuilding can preserve disagreement instead of flattening it into a single opaque state
- overrides are explicit, justified, and reviewable
- expert governance strengthens trust instead of weakening it

## Metadata

- `macro_domain`: `11_identity_governance_and_legal_grade_trust`
- `ring`: `ring_3_to_4`
- `user_surface`: `pro / qa / internal / authority`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `human_governed_trust`
- `depends_on`: `decision replay + trust + contradictions + auditability`
