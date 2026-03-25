# Claude Wave Brief Kit

Date de controle: `25 mars 2026`

Use these as copy-paste execution briefs.
They are aligned with:

- [claude-master-execution-pack-2026-03-25.md](./claude-master-execution-pack-2026-03-25.md)
- [claude-wave-opportunity-map-2026-03-25.yaml](./claude-wave-opportunity-map-2026-03-25.yaml)
- [claude-validation-matrix-2026-03-25.md](./claude-validation-matrix-2026-03-25.md)

---

## Brief 1 - PermitProcedure Core

```yaml
outcome: Persistent procedural execution layer above permit_tracking with visible procedure state, steps, and authority requests.
files:
  modify:
    - backend/alembic/versions/
    - backend/tests/
  create:
    - backend/app/models/permit_procedure.py
    - backend/app/schemas/permit_procedure.py
    - backend/app/services/permit_procedure_service.py
    - backend/app/api/permit_procedures.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Reuse permit_tracking as calculated need layer; do not duplicate it.
  - Use Obligation as the only deadline entity.
  - Use WorkspaceMembership for assignment; no second access model.
  - Prepare hub-file wiring for supervisor merge instead of editing hub files directly.
exit: Models, service, API, targeted tests, and migration are ready; no partial exposure remains.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_permit_tracking.py tests/test_workspace.py -q
```

---

## Brief 2 - ControlTower v2

```yaml
outcome: One operating inbox aggregating blockers, overdue items, pending requests, and routed next actions across buildings.
files:
  modify:
    - backend/tests/
    - frontend/src/pages/ControlTower.tsx
    - frontend/src/api/controlTower.ts
    - frontend/src/components/__tests__/ControlTower.test.tsx
  create:
    - backend/app/services/action_aggregation_service.py
    - backend/app/api/control_tower.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
constraints:
  - Read-model only; do not create a second persistent action system.
  - Aggregate from existing canonical sources only.
  - Use local UI state for snooze/dismiss; no persistence yet.
  - Keep portfolio and building views in one aggregation model.
exit: Backend aggregation and frontend inbox are both live, tested, and clearly prioritized.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 3 - ProofDelivery

```yaml
outcome: Delivery trace for documents and packs with version, provenance, viewed state, and acknowledgement state.
files:
  modify:
    - backend/alembic/versions/
    - backend/tests/
    - frontend/src/components/__tests__/
  create:
    - backend/app/models/proof_delivery.py
    - backend/app/schemas/proof_delivery.py
    - backend/app/services/proof_delivery_service.py
    - backend/app/api/proof_delivery.py
    - frontend/src/api/proofDelivery.ts
    - frontend/src/components/building-detail/DeliveryHistory.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Build on top of existing document and pack concepts; no new storage system.
  - Treat delivery as evidence, not as email automation.
  - Prepare hub registration for supervisor merge only.
  - Keep status model simple: sent, viewed, acknowledged, failed or expired.
exit: Delivery records are queryable and rendered in UI with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 4 - Passport Exchange Hardening

```yaml
outcome: Audience-specific passport and transfer outputs that are clearer, reusable, and machine-readable enough for external exchange.
files:
  modify:
    - backend/app/services/passport_exchange_service.py
    - backend/tests/test_passport_exchange.py
    - frontend/src/api/passport.ts
    - frontend/src/pages/BuildingDetail.tsx
    - frontend/src/components/building-detail/DiagnosticsTab.tsx
  create:
    - frontend/src/components/building-detail/PassportPackSelector.tsx
    - frontend/src/components/__tests__/PassportPackSelector.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/schemas/__init__.py
constraints:
  - No new core model unless strictly necessary; prefer projection over existing passport and transfer package data.
  - Make included and excluded sections explicit by audience.
  - Optimize for authority, insurer, lender, buyer, and full export.
  - Keep exchange contract versioned and explainable.
exit: Audience-specific outputs are generated and previewable without introducing a second passport model.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python -m pytest tests/test_passport_exchange.py -q
  - cd frontend && npm run test:changed:strict
```

---

## Brief 5 - SwissRules Watch Foundations

```yaml
outcome: Operational foundation for regulatory freshness and later requalification, without building a giant rules engine in one wave.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/regulatory_source_watch.py
    - backend/app/models/regulatory_snapshot.py
    - backend/app/models/regulatory_change_event.py
    - backend/app/schemas/regulatory_watch.py
    - backend/app/services/regulatory_watch_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Extend the SwissRules spine; do not create a parallel rules universe.
  - Keep activation and review explicit; no silent auto-propagation of high-impact rule changes.
  - Prepare for later impact projection into obligations, procedures, and control tower.
  - Do not widen into legal encyclopedia behavior.
exit: Source watch, snapshot, and change-event foundations exist with targeted tests and no premature UI.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_regulatory_watch.py -q
```

---

## Brief 6 - Authority Flow Core

```yaml
outcome: First-class authority submission flow with submission state, complement requests, acknowledgement trace, and decision history.
files:
  modify:
    - backend/alembic/versions/
    - backend/tests/
    - frontend/src/components/__tests__/
  create:
    - backend/app/models/authority_submission.py
    - backend/app/models/authority_acknowledgement.py
    - backend/app/models/authority_decision.py
    - backend/app/schemas/authority_flow.py
    - backend/app/services/authority_flow_service.py
    - backend/app/api/authority_flow.py
    - frontend/src/api/authorityFlow.ts
    - frontend/src/components/building-detail/AuthoritySubmissionCard.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Extend PermitProcedure, Obligation, ControlTower, authority_pack, and ProofDelivery; do not create parallel systems.
  - Treat authority interaction as workflow state, not as a document export screen only.
  - Reuse existing pack and proof concepts whenever possible.
  - Prepare hub-file registration for supervisor merge only.
exit: Submission lifecycle, complement tracking, acknowledgement trace, and decision history are modeled and testable without partial hidden wiring.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 7 - Proof Trust Hardening

```yaml
outcome: Strengthen the proof layer from simple delivery tracking toward versioned receipts, replacement chains, and defensible evidence state.
files:
  modify:
    - backend/tests/
    - frontend/src/components/__tests__/
  create:
    - backend/app/models/proof_receipt.py
    - backend/app/schemas/proof_trust.py
    - backend/app/services/proof_trust_service.py
    - frontend/src/api/proofTrust.ts
    - frontend/src/components/building-detail/ProofTrustTimeline.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Build on top of ProofDelivery and existing document or pack versions.
  - Focus on traceability and reuse, not PKI or archive overengineering.
  - Keep the first slice explainable to owners, authorities, and partners.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Receipts, replacement chains, and trust-state rendering exist for changed proof flows with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 8 - Passport Exchange Network Foundations

```yaml
outcome: Versioned exchange contract, publication trace, and import receipt foundation for building passport and pack interoperability.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/exchange_contract_version.py
    - backend/app/models/passport_publication.py
    - backend/app/models/passport_import_receipt.py
    - backend/app/schemas/passport_exchange_network.py
    - backend/app/services/passport_exchange_network_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Extend existing passport, transfer, and publication package logic; do not create a second passport core.
  - Start with contract versioning, publication, and receipt traces only.
  - Keep cross-system capability negotiation out of the first slice.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Exchange contract and receipt foundations exist with targeted tests and no fake marketplace behavior.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_passport_exchange.py -q
```

---

## Brief 9 - Partner Trust Signals

```yaml
outcome: Internal-only partner trust signals grounded in proof delivery, rework, responsiveness, and workflow fit.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/partner_trust_profile.py
    - backend/app/models/partner_trust_signal.py
    - backend/app/schemas/partner_trust.py
    - backend/app/services/partner_trust_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Internal decision aid only; no public ranking or marketplace behavior.
  - Ground every signal in existing workflow evidence such as ProofDelivery, acknowledgement, and rework.
  - Keep low-confidence signals hidden or review-only.
  - Prepare hub-file registration for supervisor merge only.
exit: Trust signals and profiles exist as explainable internal primitives with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_partner_trust.py -q
```

---

## Brief 10 - Geometry Intelligence Foundations

```yaml
outcome: Geometry anchor, spatial proof link, and first useful plan overlay foundation without drifting into BIM authoring.
files:
  modify:
    - backend/tests/
    - frontend/src/components/__tests__/
  create:
    - backend/app/models/geometry_reference_frame.py
    - backend/app/models/geometry_anchor.py
    - backend/app/models/spatial_proof_link.py
    - backend/app/schemas/geometry_intelligence.py
    - backend/app/services/geometry_intelligence_service.py
    - frontend/src/api/geometryIntelligence.ts
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Reuse plans, zones, elements, evidence, and field observations; do not create a second building graph.
  - Focus on overlays and anchors, not BIM authoring or CAD features.
  - The first visible slice must improve proof or blocker readability on plans.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Geometry anchors and one useful spatial proof surface are modeled with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 11 - Territory and Public Systems Foundations

```yaml
outcome: Territory and utility dependency objects that can project external blockers and impacts into building workflows.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/public_system_dependency.py
    - backend/app/models/utility_interruption_impact.py
    - backend/app/models/territory_procedure_context.py
    - backend/app/schemas/territory_public_systems.py
    - backend/app/services/territory_public_systems_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Feed permit_tracking, PermitProcedure, SwissRules, ControlTower, and authority_pack; do not create parallel systems.
  - Keep the first slice blocker-oriented, not GIS-oriented.
  - Do not widen into generic map analytics.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Territory dependencies and impacts can be modeled and projected into blockers with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_territory_public_systems.py -q
```

---

## Brief 12 - Benchmarking Grounded in Proof Foundations

```yaml
outcome: Internal benchmarking snapshots and privacy-safe aggregates grounded in proof quality, blockers, obligations, and procedure state.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/benchmark_snapshot.py
    - backend/app/models/privacy_safe_aggregate.py
    - backend/app/schemas/benchmarking_grounded_in_proof.py
    - backend/app/services/benchmarking_grounded_in_proof_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Ground every benchmark in canonical workflow and proof anchors.
  - Keep the first slice internal-only and privacy-safe.
  - Do not build vanity dashboards or black-box scoring.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Internal benchmarking primitives exist with targeted tests and clear privacy boundaries.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_benchmarking_grounded_in_proof.py -q
```

---

## Brief 13 - Agent Operating Layer Foundations

```yaml
outcome: Agent run audit, recommendation audit, correction capture, and replay links that make automation inspectable and reusable.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/agent_run_audit.py
    - backend/app/models/agent_recommendation_audit.py
    - backend/app/models/knowledge_correction.py
    - backend/app/schemas/agent_operating_layer.py
    - backend/app/services/agent_operating_layer_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Agent outputs must be attributable to evidence and outcome.
  - Reuse timeline, ControlTower, SwissRules, and scenario factory anchors where possible.
  - Do not create free-form logs as the only source of truth.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Agent audit and correction primitives exist with targeted tests and clear replay hooks.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_agent_operating_layer.py -q
```

---

## Brief 14 - openBIM Convergence Foundations

```yaml
outcome: IFC mapping profile, requirement profile, and issue bridge foundations that make SwissBuilding standards-aware without BIM authoring drift.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/ifc_mapping_profile.py
    - backend/app/models/ids_requirement_profile.py
    - backend/app/models/digital_building_logbook_mapping.py
    - backend/app/schemas/openbim_convergence.py
    - backend/app/services/openbim_convergence_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Improve exchange, validation, or issue portability; do not add symbolic standards support only.
  - Reuse geometry intelligence, passport exchange, and proof layers.
  - Do not widen into IFC editing or BIM authoring.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Mapping and requirement foundations exist with targeted tests and future-proof export direction.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_openbim_convergence.py -q
```

---

## Brief 15 - Pilot Communes Foundations

```yaml
outcome: Commune adapter profile, local rule override, and procedure variant foundations for a small honest pilot-commune strategy.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/communal_adapter_profile.py
    - backend/app/models/communal_rule_override.py
    - backend/app/models/communal_procedure_variant.py
    - backend/app/schemas/pilot_communes.py
    - backend/app/services/pilot_communes_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Start with a few pilot communes only; do not fake broad communal automation.
  - Feed SwissRules, permit_tracking, PermitProcedure, and ControlTower.
  - Always preserve explicit manual-review fallback.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Pilot commune adapter foundations exist with targeted tests and clear fallback semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_pilot_communes.py -q
```
