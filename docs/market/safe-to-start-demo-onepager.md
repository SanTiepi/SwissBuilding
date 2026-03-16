# Safe-to-Start Demo One-Pager

## Positioning

SwissBuilding is sold as an overlay above ERP/document systems for multi-building property managers.

Commercial wedge:
- `VD/GE-first`
- `amiante-first`
- `AvT -> ApT`
- `safe-to-start dossier`

## Primary Buyer

- portfolio or operations lead at a multi-building property manager
- secondary stakeholders in the same sale:
  - compliance/responsible authority interface
  - project manager coordinating diagnosticians and contractors
  - asset owner representative

## Core Promise (What We Claim)

- move one building dossier from incomplete to operationally ready
- make missing evidence explicit and trackable
- generate authority/owner/contractor-ready outputs with provenance
- reduce documentary rework and stop-work risk

## Claim Boundaries (What We Do Not Claim)

- no automatic legal-compliance guarantee
- no ERP replacement claim
- no "AI black box" decision claims without evidence trace

## 10-Minute External Demo Script

Target outcome:
- prove one seeded building moving from raw to complete with visible UI + real e2e backing.

1. `00:00-01:00` - Context and baseline
- open `/dashboard`
- state current wedge in one line: regulated pre-work readiness, not generic property software

2. `01:00-03:00` - Building baseline (raw/incomplete)
- open `/buildings`, select seeded target building
- open `/buildings/:id`
- show incompleteness, blockers, or unknowns on the baseline state

3. `03:00-05:00` - Readiness and proof chain
- open `/buildings/:id/readiness`
- show safe-to-start status, checks, blockers, and legal-basis context
- return to detail and show trust/provenance indicators

4. `05:00-07:00` - Dossier and authority packaging
- show dossier generation/download flow from building detail surfaces
- open `/authority-packs`
- show package status, completeness, and readiness context

5. `07:00-09:00` - Operator value
- show next actions/missing evidence orchestration
- show how this reduces iterative back-and-forth across actors

6. `09:00-10:00` - Close
- restate measurable outcomes and boundaries:
  - readiness support, provenance, workflow traceability
  - not legal guarantee

## Proof Metrics for External Conversations

Use measurable language tied to seeded and validated scenarios:

| Metric Family | Target |
|---------------|--------|
| Dossier completeness | `>=95%` on canonical seeded scenario |
| Documentary rework | `>=50%` reduction vs prior process baseline |
| Authority-ready pack latency | `<=2h` from validated inputs |
| Provenance integrity | `100%` of critical evidence traceable to source |

## Standard Objections and Responses

- "We already have an ERP."
  - response: SwissBuilding overlays ERP and focuses on regulated evidence/readiness logic ERP does not structure.
- "Is this legal certification?"
  - response: no, it is a readiness/proof orchestration layer with explicit provenance and gaps.
- "Can this scale beyond one building?"
  - response: yes, same chain is designed to roll up to portfolio surfaces and campaign orchestration.

## Operational Use in Agent-Only Loop

Codex responsibilities:
- keep this one-pager aligned with current gate proof and claim boundaries
- update narrative when gate definition changes

Claude responsibilities:
- keep demo surfaces and flows executable against seeded real scenario
- keep commands/tests used for demo proof green

