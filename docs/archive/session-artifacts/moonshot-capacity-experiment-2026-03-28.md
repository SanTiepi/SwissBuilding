# SwissBuilding — Moonshot Capacity Experiment

Date: 28 mars 2026
Status: Active execution program
Measurement: throughput experiment — how far can we push before velocity breaks

---

## Execution Model

- Continuous waves, not isolated prompts
- Max 3 parallel agents per wave, disjoint scopes
- Never reopen settled decisions (roots, hubs, rituals, BuildingCase, read-first API)
- Each wave end: validation, checkpoint, ORCHESTRATOR update, throughput measurement
- Cut rule: cut by outer rings, never by the core

---

## 13 Blocs

| Bloc | Name | Status |
|---|---|---|
| 0 | Harness | **Done** (doctrine, ADRs, memory, measurement) |
| 1 | Spine absolue | **CLOSED** — 253 tests green, all layers wired, BuildingCase operating root, rituals transversal, SafeToX←unknowns, invalidation engine, Truth API v1, source registry |
| 2 | Total Source OS | **~75%** — geo.admin 10 overlays, identity chain EGID→EGRID→RDPPF, source registry 27 sources, health events, swissBUILDINGS3D. Remaining: cantonal portals |
| 3 | Procedure OS total | **~90%** — grammar, 8 templates, 22 work families, freshness watch, auto-BuildingCase. Remaining: cantonal deepening |
| 4 | Document Intelligence OS | **~90%** — 4 extractors (diagnostic/quote/authority/contract), consequence engine, unknowns ledger, review queue |
| 5 | Building Genealogy OS | **~70%** — 3 models, timeline, declared vs observed. Remaining: historical imagery |
| 6 | Climate/Exposure/Opportunity OS | **~75%** — exposure profile, opportunity windows, best timing. Remaining: MeteoSwiss long-term |
| 7 | Exchange/Transfer/Conformance | **~75%** — PassportEnvelope, rituals, diff/export/manifest/reimport, conformance checks (5 profiles, 8 check types) |
| 8 | Finance/Insurance/Transaction/Caveat | **~65%** — financial redaction, SafeToX, commitments+caveats, incidents, decision replay |
| 9 | Operations/Owner/Utility Twin | **~55%** — BuildingLife, action queue, owner ops, recurring services, warranties |
| 10 | Incident/Damage Memory | **~70%** — IncidentEpisode, DamageObservation, recurring chain, insurer summary, change grammar wired |
| 11 | Counterfactual/Scenario/Portfolio | **~60%** — 12 scenario types, evaluate, compare, auto-generate standard |
| 12 | Network/Autonomous Market OS | **~35%** — partner trust V3-wired (case, rituals, RFQ, contractor ack), trust signals in flows |

## Cut Order (if needed)

Cut from bottom: 12 → 11 → 10 → 9 → 8. Never cut before spine + source + procedure + doc intelligence + genealogy/exchange core are secured.

## Success Signal

- Blocs 1-4 closed = exceptional core
- Blocs 1-8 closed = very hard to catch
- Blocs 1-12 closed = category leap
