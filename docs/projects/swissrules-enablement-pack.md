# SwissRules Enablement Pack

## Intent

This bootstrap pack gives SwissBuilding a typed regulatory spine without
forcing immediate router or ORM wiring while nearby wave work is still in
flight.

It is meant to help future implementation stay consistent with the product
decision:

- no second permit engine
- no second obligation entity
- no second document inbox
- no parallel action system outside Control Tower

## Added foundation

- `backend/app/schemas/swiss_rules.py`
  - typed models for:
    - `Jurisdiction`
    - `AuthorityRegistry`
    - `RuleSource`
    - `RuleSnapshot`
    - `NormativeForce`
    - `RuleTemplate`
    - `RequirementTemplate`
    - `ProcedureTemplate`
    - `ApplicabilityEvaluation`
    - `LegalChangeEvent`
    - `ImpactReview`
- `backend/app/services/swiss_rules_spine_service.py`
  - builds a bootstrap `SwissRulesEnablementPack`
  - encodes integration targets and anti-duplication guardrails
  - seeds official source URLs from the current SwissRules strategy brief
  - provides basic applicability evaluation for initial regulatory templates
  - provides snapshot hashing and change detection helpers
- `backend/app/schemas/swiss_rules_projection.py`
  - typed projection outputs for:
    - procedure candidates
    - obligation candidates
    - Control Tower action candidates
- `backend/app/services/swiss_rules_projection_service.py`
  - projects applicability evaluations into the existing product anchors
  - makes the bridge explicit from research to:
    - `PermitProcedure`
    - `Obligation`
    - `ControlTower`
- `backend/tests/test_swiss_rules_spine_service.py`
  - proves the pack shape, guardrails, source registry, change detection, and core applicability flows
- `backend/tests/test_swiss_rules_projection_service.py`
  - proves projection for permit, filing, waste, and manual-review scenarios
- `docs/projects/swissrules-regulatory-research-pack-2026-03-25.md`
  - dated internet research pack with official Swiss source anchors and product implications
- `docs/projects/swissrules-coverage-matrix-2026-03-25.md`
  - current domain-by-domain coverage status, priorities, and next moves
- `docs/projects/swissrules-watch-priority-backlog-2026-03-25.md`
  - watch cadence priorities and first expansion backlog
- `docs/projects/building-passport-best-practices-and-frictions-2026-03-25.md`
  - dated product best-practices and friction map for future waves

## Integration anchors

These are the subsystems future waves should extend rather than duplicate:

- `permit_tracking_service.py`
- `regulatory_filing_service.py`
- `obligation_service.py`
- `document_inbox_service.py`
- `authority_pack_service.py`
- `frontend/src/api/controlTower.ts`

Future execution layers remain explicit placeholders:

- `permit_procedure`
- `proof_delivery`

## Bootstrap scope

This is not a full legal corpus.

It is a typed scaffold that already captures:

- federal anchors:
  - territory / permit framing
  - waste / OLED
  - radon
  - asbestos / SUVA / CFST
- intercantonal or quasi-normative anchors:
  - EnDK / MoPEC
  - VKF / AEAI
  - Minergie
  - FACH
  - ASCA
- initial canton adapters:
  - Vaud / CAMAC
  - Geneva / OAC
  - Fribourg / SeCA

## Intended next step

When the current waves are merged, the next implementation should:

1. decide whether to map these schemas onto ORM tables directly or keep them as a service-layer registry first
2. wire `PermitProcedure` creation against `ProcedureTemplate`
3. wire `ControlTower` aggregation against `ApplicabilityEvaluation`
4. promote `RuleSnapshot` + `LegalChangeEvent` into the real regulatory watch pipeline

## Caution

This pack intentionally avoids hub-file wiring while concurrent work is active.
It is designed to be merged safely now and connected later by a supervisor or
follow-up wave.
