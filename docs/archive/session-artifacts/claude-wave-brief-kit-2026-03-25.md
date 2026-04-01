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
  - Use the shortlist in docs/projects/pilot-commune-candidates-2026-03-25.md.
  - Use docs/projects/communal-adapter-projection-map-2026-03-25.md to map local deltas into existing product anchors.
  - Feed SwissRules, permit_tracking, PermitProcedure, and ControlTower.
  - Always preserve explicit manual-review fallback.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Pilot commune adapter foundations exist with targeted tests and clear fallback semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_pilot_communes.py -q
```

---

## Brief 16 - Killer Demo Foundations

```yaml
outcome: Canonical demo scenarios, operator runbooks, and known-good seeded states that make demos repeatable and buyer-legible.
files:
  modify:
    - backend/tests/
    - frontend/e2e-real/
  create:
    - backend/app/models/demo_scenario.py
    - backend/app/schemas/demo_enablement.py
    - backend/app/services/demo_enablement_service.py
    - frontend/src/components/demo/OperatorDemoPanel.tsx
    - frontend/src/components/demo/DemoScenarioSwitcher.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Reuse real seeds and product truth; no fake demo-only flows.
  - Keep scenarios persona-legible and repeatable.
  - Focus on property-manager and authority-ready stories first.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Canonical scenarios and operator helpers exist with targeted tests and stable demo reset semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 17 - Enterprise Rollout Foundations

```yaml
outcome: Boundary, delegated access, and privileged audit foundations that reduce enterprise rollout friction without becoming IAM middleware.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/tenant_boundary.py
    - backend/app/models/delegated_access_grant.py
    - backend/app/models/privileged_access_event.py
    - backend/app/schemas/enterprise_rollout.py
    - backend/app/services/enterprise_rollout_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Reduce rollout friction around access, visibility, revocation, and support auditability.
  - Reuse WorkspaceMembership and existing sharing semantics where possible.
  - Do not widen into full SSO or IAM replacement.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Enterprise rollout primitives exist with targeted tests and clear governance semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_enterprise_rollout.py -q
```

---

## Brief 18 - Buyer Packaging Presets

```yaml
outcome: Buyer-facing pack presets and package-aligned surfaces for wedge, operational, and portfolio narratives.
files:
  modify:
    - backend/tests/
    - frontend/src/components/building-detail/
  create:
    - backend/app/schemas/buyer_packaging.py
    - backend/app/services/buyer_packaging_service.py
    - frontend/src/components/building-detail/BuyerPackPresetSelector.tsx
    - frontend/src/components/__tests__/BuyerPackPresetSelector.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Reuse existing pack and exchange concepts; do not create a second packaging engine.
  - Align presets to wedge, operational, and portfolio value stories.
  - Keep the first slice buyer-legible, not pricing-engine heavy.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Buyer packaging presets exist with targeted tests and no divergence from the main pack model.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 19 - Embedded Channels Foundations

```yaml
outcome: Bounded embed tokens, external viewer semantics, and stable summary artifacts that lower switching cost and support account spread.
files:
  modify:
    - backend/tests/
    - frontend/src/components/__tests__/
  create:
    - backend/app/models/bounded_embed_token.py
    - backend/app/models/external_viewer_profile.py
    - backend/app/models/account_expansion_trigger.py
    - backend/app/schemas/embedded_channels.py
    - backend/app/services/embedded_channels_service.py
    - frontend/src/components/embed/EmbeddedPassportCard.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Reduce switching cost or increase account spread; do not mirror the whole app externally.
  - Reuse pack, passport, and proof surfaces where possible.
  - Keep the first slice bounded and audience-safe.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Embedded channel primitives exist with targeted tests and clear boundary semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 20 - Public Owner and Municipality Foundations

```yaml
outcome: Public-owner operating mode, municipality-ready review pack, and governance signal foundations for public-sector building workflows.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/public_owner_operating_mode.py
    - backend/app/models/municipality_review_pack.py
    - backend/app/models/public_asset_governance_signal.py
    - backend/app/schemas/public_owner_municipality.py
    - backend/app/services/public_owner_municipality_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Reinforce the canonical building workspace; do not drift into generic public-sector ERP behavior.
  - Reuse PermitProcedure, Authority Flow, packs, proof delivery, and territory context.
  - Keep the first slice review-pack and governance oriented.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Public-owner primitives exist with targeted tests and a clear municipality review story.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_public_owner_municipality.py -q
```

---

## Brief 21 - Insurer and Fiduciary Surfaces Foundations

```yaml
outcome: Bounded insurer and fiduciary pack presets with redaction and trust-oriented delivery semantics.
files:
  modify:
    - backend/tests/
    - frontend/src/components/building-detail/
  create:
    - backend/app/models/external_audience_redaction_profile.py
    - backend/app/schemas/insurer_fiduciary_surfaces.py
    - backend/app/services/insurer_fiduciary_surfaces_service.py
    - frontend/src/components/building-detail/ExternalAudiencePackPresets.tsx
    - frontend/src/components/__tests__/ExternalAudiencePackPresets.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Keep surfaces bounded, pack-centric, and evidence-driven.
  - Reuse existing pack architecture, ProofDelivery, and buyer packaging presets.
  - Do not widen into insurer or fiduciary core workflow platforms.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Insurer and fiduciary surface primitives exist with targeted tests and audience-safe semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 22 - Distribution Sales Loops Foundations

```yaml
outcome: Distribution-loop signals and expansion opportunities grounded in real workflow success, not synthetic growth mechanics.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/distribution_loop_signal.py
    - backend/app/models/expansion_opportunity.py
    - backend/app/schemas/distribution_sales_loops.py
    - backend/app/services/distribution_sales_loops_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Only emit spread signals when real product value has been observed.
  - Reuse embedded channels, ProofDelivery, partner trust, and buyer packaging anchors.
  - Do not drift into CRM replacement behavior.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Distribution-loop primitives exist with targeted tests and explainable account-spread logic.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_distribution_sales_loops.py -q
```

---

## Brief 23 - Transaction and Lender Surfaces Foundations

```yaml
outcome: Transaction-facing and lender-facing pack presets with explicit caveats, trust links, and bounded readiness semantics.
files:
  modify:
    - backend/tests/
    - frontend/src/components/building-detail/
  create:
    - backend/app/models/decision_caveat_profile.py
    - backend/app/schemas/transaction_lender_surfaces.py
    - backend/app/services/transaction_lender_surfaces_service.py
    - frontend/src/components/building-detail/TransactionLenderPackPresets.tsx
    - frontend/src/components/__tests__/TransactionLenderPackPresets.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Keep surfaces pack-centric, trust-centric, and bounded.
  - Reuse readiness wallet, pack architecture, ProofDelivery, and buyer packaging.
  - Do not widen into deal-room or lending workflow platforms.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Transaction and lender surface primitives exist with targeted tests and explicit caveat handling.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 24 - Public Procurement and Committee Foundations

```yaml
outcome: Committee-ready packs, procurement-facing clause bundles, and review-decision traces for public-owner circulation flows.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/models/committee_decision_pack.py
    - backend/app/models/procurement_clause_bundle.py
    - backend/app/models/review_decision_trace.py
    - backend/app/schemas/public_procurement_committee.py
    - backend/app/services/public_procurement_committee_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Reinforce dossier clarity, review traceability, and reusable decision artifacts.
  - Reuse public-owner operating mode, municipality review packs, ecobau/procurement clause logic, and proof delivery.
  - Do not widen into full tender-management or procurement ERP behavior.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Public procurement and committee primitives exist with targeted tests and clear circulation semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_public_procurement_committee.py -q
```

---

## Brief 25 - Must-Win Workflow Instrumentation

```yaml
outcome: Product-native workflow state and visibility for the few flows SwissBuilding must beat decisively.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
    - frontend/src/pages/
  create:
    - backend/app/schemas/must_win_workflows.py
    - backend/app/services/must_win_workflow_service.py
    - frontend/src/components/building-detail/MustWinWorkflowSummary.tsx
    - frontend/src/components/__tests__/MustWinWorkflowSummary.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/must-win-workflow-map-2026-03-25.md as the source of truth.
  - Project from existing canonical workflow truth; do not create a second workflow engine.
  - Highlight clarity, blockers, and next action rather than generic analytics.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: The must-win workflows are visible as explicit product states or summaries with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 26 - Proof Reuse Scenario Seeds

```yaml
outcome: Canonical seeded scenarios and projections that prove evidence reuse across audiences instead of one-off output generation.
files:
  modify:
    - backend/tests/
    - frontend/e2e-real/
  create:
    - backend/app/schemas/proof_reuse_scenarios.py
    - backend/app/services/proof_reuse_scenario_service.py
    - frontend/src/components/building-detail/ProofReuseMoments.tsx
    - frontend/src/components/__tests__/ProofReuseMoments.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/proof-reuse-scenario-library-2026-03-25.md as the source of truth.
  - Reuse DiagnosticPublication, packs, procedures, and ProofDelivery; do not create a second evidence system.
  - Keep freshness, caveats, and provenance visible whenever proof is reused.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: At least a few canonical proof-reuse scenarios are visible, seeded, and testable with targeted validation green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 27 - Confidence Ladder and Review Queue Foundations

```yaml
outcome: Shared confidence semantics and visible review queue foundations across rules, procedures, proof reuse, and agent outputs.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
    - frontend/src/pages/
  create:
    - backend/app/schemas/confidence_review.py
    - backend/app/services/confidence_review_service.py
    - frontend/src/components/review/ConfidenceBadge.tsx
    - frontend/src/components/review/ReviewQueuePanel.tsx
    - frontend/src/components/__tests__/ReviewQueuePanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/confidence-ladder-and-manual-review-pack-2026-03-25.md as the source of truth.
  - Reuse ControlTower, SwissRules, pilot communes, and agent audit anchors; do not create a second action system.
  - Keep visible uncertainty explicit; do not auto-hide review-required states in logs.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Shared confidence levels, visible review semantics, and a bounded review queue foundation exist with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 28 - Habit Loop Surface Foundations

```yaml
outcome: Visible daily, weekly, and event-driven operating rituals embedded into the product so key personas build recurring habits.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
    - frontend/src/pages/
  create:
    - backend/app/schemas/habit_loops.py
    - backend/app/services/habit_loop_service.py
    - frontend/src/components/dashboard/OperatingRitualsPanel.tsx
    - frontend/src/components/__tests__/OperatingRitualsPanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/habit-loop-and-operating-rituals-2026-03-25.md as the source of truth.
  - Reinforce existing canonical surfaces; do not create a second dashboard universe.
  - Every ritual must point to a next action, not just a metric or status.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Recurring operating rituals are visible for at least core personas with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 29 - Canonical Timeline Event Contract

```yaml
outcome: Shared event taxonomy and timeline contract that unifies procedure, proof, diagnostics, obligations, and review visibility.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
  create:
    - backend/app/schemas/timeline_event_contract.py
    - backend/app/services/timeline_event_projection_service.py
    - frontend/src/components/timeline/TimelineEventFamilyBadge.tsx
    - frontend/src/components/__tests__/TimelineEventFamilyBadge.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/canonical-event-taxonomy-and-timeline-contract-2026-03-25.md as the source of truth.
  - Extend existing timeline semantics; do not create a second activity stream.
  - Keep event families human-readable and workflow-relevant.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: A shared event contract exists and can project key families into the canonical timeline with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 30 - North-Star Metrics and Instrumentation Foundations

```yaml
outcome: Product-facing instrumentation model tied to canonical workflows, proof reuse, procedural clarity, and recurring building value.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/product_metrics.py
    - backend/app/services/product_metrics_service.py
    - backend/app/services/product_metric_projection_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/north-star-metric-tree-and-product-instrumentation-2026-03-25.md as the source of truth.
  - Instrument workflow outcomes, not vanity clicks.
  - Tie metrics back to canonical building objects and event sources.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: A usable metric tree and projection foundation exist for product instrumentation with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_product_metrics.py -q
```

---

## Brief 31 - Switching Cost Removal Foundations

```yaml
outcome: Product primitives that reduce migration pain, preserve source provenance, and support partial adoption without big-bang replacement.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/switching_cost_migration.py
    - backend/app/services/switching_cost_migration_service.py
    - backend/app/services/import_provenance_projection_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/switching-cost-removal-and-migration-pack-2026-03-25.md as the source of truth.
  - Reduce coexistence and migration friction; do not build a generic migration console.
  - Preserve source system and import provenance explicitly.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Migration-friction reduction primitives exist with targeted tests and no generic ETL sprawl.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_switching_cost_migration.py -q
```

---

## Brief 32 - Freshness and Staleness Foundations

```yaml
outcome: Shared freshness semantics for proof, packs, rules, and summaries so users can distinguish current, aging, stale, superseded, and review-dependent states.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
  create:
    - backend/app/schemas/freshness_contract.py
    - backend/app/services/freshness_projection_service.py
    - frontend/src/components/common/FreshnessBadge.tsx
    - frontend/src/components/__tests__/FreshnessBadge.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/data-freshness-and-staleness-contract-2026-03-25.md as the source of truth.
  - Extend existing proof, rules, and pack semantics; do not create a second validity system.
  - Make stale and superseded states visibly different.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Shared freshness semantics and bounded UI rendering exist with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 33 - Canonical Identity Resolution Foundations

```yaml
outcome: Shared identity-resolution primitives for building, parcel, and legacy identifiers with explicit confidence and review semantics.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/identity_resolution.py
    - backend/app/services/identity_resolution_service.py
    - backend/app/services/identity_match_explanation_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/canonical-identity-resolution-pack-2026-03-25.md as the source of truth.
  - Preserve the hard distinction between egid, egrid, and official_id.
  - Never auto-merge materially ambiguous identities silently.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Identity-resolution primitives exist with targeted tests and explicit match explanations.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_identity_resolution.py -q
```

---

## Brief 34 - UX Surface Grammar Foundations

```yaml
outcome: Shared surface grammar for blockers, deadlines, confidence, freshness, proof, and next action across key product views.
files:
  modify:
    - frontend/src/components/
    - frontend/src/pages/
    - frontend/src/components/__tests__/
  create:
    - frontend/src/components/common/SurfacePriorityStack.tsx
    - frontend/src/components/common/NextActionStrip.tsx
    - frontend/src/components/__tests__/SurfacePriorityStack.test.tsx
  do_not_touch:
    - frontend/src/i18n/en.ts
    - frontend/src/i18n/fr.ts
    - frontend/src/i18n/de.ts
    - frontend/src/i18n/it.ts
constraints:
  - Use docs/projects/ux-information-hierarchy-and-surface-grammar-2026-03-25.md as the source of truth.
  - Reuse existing canonical surfaces; do not build a second design system.
  - Every enhanced surface must make next action easier to see.
  - Use inline fallbacks instead of editing hub i18n files.
exit: A shared visual grammar exists on a few key surfaces with targeted tests green.
validate:
  - cd frontend && npm run validate
  - cd frontend && npm run test:changed:strict
```

---

## Brief 35 - Explainability and Decision Trace Foundations

```yaml
outcome: Shared explainability primitives that let consequential outputs show source, reasoning path, confidence, and resulting action.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
  create:
    - backend/app/schemas/decision_trace.py
    - backend/app/services/decision_trace_service.py
    - frontend/src/components/common/DecisionTracePanel.tsx
    - frontend/src/components/__tests__/DecisionTracePanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/explainability-and-decision-trace-pack-2026-03-25.md as the source of truth.
  - Reuse canonical sources and projections; do not invent opaque black-box reasoning.
  - Keep the first slice one-click-away explainability, not a forensic console.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Decision traces exist for consequential outputs with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 36 - Progressive Exposure Foundations

```yaml
outcome: Bounded exposure semantics and internal or pilot gating patterns that prevent half-wired capability from leaking into the main workspace.
files:
  modify:
    - backend/tests/
    - frontend/src/pages/
  create:
    - backend/app/schemas/progressive_exposure.py
    - backend/app/services/progressive_exposure_service.py
    - frontend/src/components/common/PilotScopeNotice.tsx
    - frontend/src/components/__tests__/PilotScopeNotice.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/release-safety-and-progressive-exposure-pack-2026-03-25.md as the source of truth.
  - Reinforce the existing no-partially-wired-feature rule; do not create feature-flag sprawl.
  - Prefer internal-only or bounded pilot semantics over vague partial rollout.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Progressive exposure primitives exist with targeted tests and clear bounded rollout semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 37 - Buyer Counterproof Surfaces

```yaml
outcome: Product-facing counterproof surfaces that answer the strongest buyer objections with workflow evidence instead of marketing claims.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
    - frontend/src/pages/
  create:
    - backend/app/schemas/buyer_counterproof.py
    - backend/app/services/buyer_counterproof_service.py
    - frontend/src/components/demo/BuyerCounterproofPanel.tsx
    - frontend/src/components/__tests__/BuyerCounterproofPanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/market/buyer-objection-map-and-counterproof-pack-2026-03-25.md as the source of truth.
  - Answer objections with real workflow proof, not marketing copy alone.
  - Reuse existing packs, ControlTower, proof reuse, and procedure surfaces.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: A few high-value buyer objections can be answered by visible product counterproof with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 38 - Strategic Debt Hardening Queue

```yaml
outcome: A bounded hardening queue model that prioritizes debt by impact on truth, speed, trust, and adoption rather than by random annoyance.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/strategic_debt.py
    - backend/app/services/strategic_debt_service.py
    - backend/app/services/hardening_priority_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/implementation-debt-kill-list-and-hardening-ladder-2026-03-25.md as the source of truth.
  - Keep the first slice prioritization-oriented; do not build a generic issue tracker.
  - Focus on truth, validation speed, and trust debt first.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Strategic debt can be modeled and ranked with targeted tests and no generic ticket-system drift.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_strategic_debt.py -q
```

---

## Brief 39 - Batiscan Cross-Product Operator Story Surfaces

```yaml
outcome: Visible cross-product continuity surfaces that make the Batiscan to SwissBuilding loop obvious to operators without collapsing the product boundary.
files:
  modify:
    - backend/tests/
    - frontend/src/components/building-detail/
  create:
    - backend/app/schemas/cross_product_operator_stories.py
    - backend/app/services/cross_product_operator_story_service.py
    - frontend/src/components/building-detail/CrossProductContinuityCard.tsx
    - frontend/src/components/__tests__/CrossProductContinuityCard.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/batiscan-swissbuilding-cross-product-operator-stories-2026-03-25.md as the source of truth.
  - Reinforce the two-product model; do not blur execution boundaries.
  - Reuse mission orders, diagnostic publications, packs, and ControlTower.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Cross-product continuity is visible and understandable to operators with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 40 - Failure and Recovery Surface Foundations

```yaml
outcome: Visible failure and recovery semantics for the most trust-sensitive breakdowns in identity, proof, procedure, and cross-product publication.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
  create:
    - backend/app/schemas/failure_recovery.py
    - backend/app/services/failure_recovery_service.py
    - frontend/src/components/common/RecoveryStatePanel.tsx
    - frontend/src/components/__tests__/RecoveryStatePanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/failure-mode-and-recovery-scenario-library-2026-03-25.md as the source of truth.
  - Focus on user-understandable recovery paths, not backend-only error catalogs.
  - Reuse confidence, freshness, identity, and proof anchors.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Key trust-sensitive failure modes have visible recovery semantics with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 41 - Source-of-Truth Boundary Guards

```yaml
outcome: Shared boundary guards and projection semantics that prevent truth duplication across building, rules, procedure, proof, and diagnostic execution domains.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/source_of_truth_boundaries.py
    - backend/app/services/source_of_truth_boundary_service.py
    - backend/app/services/projection_guard_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/source-of-truth-boundary-matrix-2026-03-25.md as the source of truth.
  - Prefer projection and guardrails over duplicated persistence.
  - Preserve the two-product boundary between Batiscan and SwissBuilding.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Boundary rules are modeled explicitly with targeted tests and projection safety semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_source_of_truth_boundaries.py -q
```

---

## Brief 42 - Persona Home Surface Foundations

```yaml
outcome: Persona-specific home-entry semantics that route users into the right primary and weekly review surfaces without fragmenting canonical truth.
files:
  modify:
    - frontend/src/pages/
    - frontend/src/components/
    - frontend/src/components/__tests__/
  create:
    - backend/app/schemas/persona_entry_points.py
    - backend/app/services/persona_entry_point_service.py
    - frontend/src/components/dashboard/PersonaHomeRouter.tsx
    - frontend/src/components/__tests__/PersonaHomeRouter.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/persona-entry-points-and-home-surface-map-2026-03-25.md as the source of truth.
  - Route personas into canonical surfaces; do not create separate product silos.
  - Keep the first slice simple and wedge-focused.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Persona-specific home-entry logic exists with targeted tests and no dashboard fragmentation.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 43 - Trust Claim Evidence Surfaces

```yaml
outcome: Explicit product surfaces that tie key trust claims to visible evidence paths across building understanding, procedure, proof reuse, and packs.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
  create:
    - backend/app/schemas/trust_claims.py
    - backend/app/services/trust_claim_service.py
    - frontend/src/components/common/TrustClaimPanel.tsx
    - frontend/src/components/__tests__/TrustClaimPanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/trust-claims-and-evidence-matrix-2026-03-25.md as the source of truth.
  - Reuse existing evidence, procedure, freshness, and confidence semantics.
  - Keep claims grounded in visible proof, not marketing abstraction.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: A few key trust claims can be rendered with concrete evidence support and targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 44 - Human Handoff and Escalation Foundations

```yaml
outcome: Clean escalation and reviewer-handoff primitives that preserve context for ambiguous, blocked, or high-stakes cases.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
  create:
    - backend/app/schemas/human_handoff.py
    - backend/app/services/human_handoff_service.py
    - frontend/src/components/review/HandoffContextPanel.tsx
    - frontend/src/components/__tests__/HandoffContextPanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/operator-escalation-and-human-handoff-pack-2026-03-25.md as the source of truth.
  - Reuse confidence, identity, procedure, and cross-product mismatch anchors.
  - Escalation must preserve context, not just create a vague review task.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: High-stakes escalation cases can be handed off with preserved context and targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 45 - Wow Moment Instrumentation Foundations

```yaml
outcome: Product-visible wow moments tied to real workflow value so differentiation is memorable and measurable, not demo-only theater.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
    - frontend/e2e-real/
  create:
    - backend/app/schemas/wow_moments.py
    - backend/app/services/wow_moment_service.py
    - frontend/src/components/demo/WowMomentCallout.tsx
    - frontend/src/components/__tests__/WowMomentCallout.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/wow-moments-and-category-differentiation-map-2026-03-25.md as the source of truth.
  - Every wow moment must map to lasting product value and existing canonical truth.
  - Avoid demo-only or synthetic spectacle.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: A few category-defining wow moments are explicit and testable with targeted validation green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 46 - Procurement Evidence Ladder Surfaces

```yaml
outcome: Buyer-facing trust-evidence surfaces that match procurement skepticism with visible product proof at increasing trust thresholds.
files:
  modify:
    - backend/tests/
    - frontend/src/components/demo/
  create:
    - backend/app/schemas/procurement_evidence.py
    - backend/app/services/procurement_evidence_service.py
    - frontend/src/components/demo/ProcurementEvidenceLadder.tsx
    - frontend/src/components/__tests__/ProcurementEvidenceLadder.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/procurement-evidence-ladder-2026-03-25.md as the source of truth.
  - Reuse trust claims, decision traces, freshness, and procedure signals.
  - Keep proof buyer-legible, not governance-jargon heavy.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Procurement-oriented evidence tiers are visible with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 47 - Public Authority Trust Signal Surfaces

```yaml
outcome: Authority-facing trust signals that make route clarity, proof completeness, response traceability, and version discipline explicit.
files:
  modify:
    - backend/tests/
    - frontend/src/components/building-detail/
  create:
    - backend/app/schemas/public_authority_trust.py
    - backend/app/services/public_authority_trust_service.py
    - frontend/src/components/building-detail/AuthorityTrustSignals.tsx
    - frontend/src/components/__tests__/AuthorityTrustSignals.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/public-authority-trust-signal-pack-2026-03-25.md as the source of truth.
  - Reuse authority flow, confidence, freshness, and proof delivery semantics.
  - Keep signals operational, not ornamental.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: A bounded set of authority trust signals is visible with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 48 - Deal-Breaker and Go/No-Go Fit Logic

```yaml
outcome: Product and GTM-facing fit logic that makes deal-breakers, bounded pilot triggers, and go/no-go semantics explicit.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/deal_breakers.py
    - backend/app/services/deal_breaker_service.py
    - backend/app/services/fit_signal_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/market/deal-breaker-matrix-and-go-no-go-pack-2026-03-25.md as the source of truth.
  - Keep this slice decision-support oriented; do not build a CRM scoring engine.
  - Tie fit signals back to workflow reality and canonical building truth.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Deal-breaker and bounded-pilot logic exists with targeted tests and no CRM drift.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_deal_breakers.py -q
```

---

## Brief 49 - Post-Sale Adoption Loop Surfaces

```yaml
outcome: Product-visible post-sale adoption loops that make recurring use, actor spread, and proof reuse growth explicit after the first deployment.
files:
  modify:
    - backend/tests/
    - frontend/src/components/dashboard/
  create:
    - backend/app/schemas/post_sale_adoption.py
    - backend/app/services/post_sale_adoption_service.py
    - frontend/src/components/dashboard/PostSaleAdoptionLoopsPanel.tsx
    - frontend/src/components/__tests__/PostSaleAdoptionLoopsPanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/post-sale-adoption-loop-pack-2026-03-25.md as the source of truth.
  - Reuse habit loops, proof reuse, embedded channels, and expansion signals.
  - Keep this slice behavior-oriented, not vanity-analytics oriented.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Post-sale adoption loops are visible with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 50 - Ecosystem Partner API Contract Foundations

```yaml
outcome: Bounded, versioned, idempotent partner contracts for publication, import, and viewer use cases without exposing the whole internal model.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/partner_api_contracts.py
    - backend/app/services/partner_api_contract_service.py
    - backend/app/services/contract_versioning_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/ecosystem-partner-api-contract-pack-2026-03-25.md as the source of truth.
  - Keep contracts bounded and audience-safe; do not leak internal graph complexity.
  - Reuse exchange, publication, and embed primitives.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Core partner contract primitives exist with targeted tests and clear versioning semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_partner_api_contracts.py -q
```

---

## Brief 51 - Authority Submission Room Foundations

```yaml
outcome: A bounded procedural room around one authority path, with current proof set, active step, request history, and next move visible in one place.
files:
  modify:
    - backend/tests/
    - frontend/src/components/building-detail/
  create:
    - backend/app/schemas/authority_submission_room.py
    - backend/app/services/authority_submission_room_service.py
    - frontend/src/components/building-detail/AuthoritySubmissionRoom.tsx
    - frontend/src/components/__tests__/AuthoritySubmissionRoom.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/authority-submission-room-pack-2026-03-25.md as the source of truth.
  - Reinforce authority flow, proof delivery, and procedure semantics; do not create a second document room.
  - Keep the first slice bounded to one active path.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: A bounded submission-room surface exists with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 52 - ROI Proof Calculator Foundations

```yaml
outcome: ROI primitives grounded in workflow events such as avoided rebuilds, earlier blocker discovery, cleaner procedure loops, and proof reuse.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/roi_proof.py
    - backend/app/services/roi_proof_service.py
    - backend/app/services/roi_event_projection_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/roi-proof-calculator-grounded-in-workflow-events-2026-03-25.md as the source of truth.
  - Ground ROI in real workflow evidence, not vanity analytics.
  - Keep the first slice calculation-oriented, not pricing-model heavy.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: ROI-proof primitives exist with targeted tests and event-grounded semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_roi_proof.py -q
```

---

## Brief 53 - Pilot Design Cookbook Surfaces

```yaml
outcome: Product and operator-facing pilot templates that make narrow, measurable, workflow-centered pilots easier to set up and evaluate.
files:
  modify:
    - backend/tests/
    - frontend/src/components/demo/
  create:
    - backend/app/schemas/pilot_design.py
    - backend/app/services/pilot_design_service.py
    - frontend/src/components/demo/PilotDesignTemplatePanel.tsx
    - frontend/src/components/__tests__/PilotDesignTemplatePanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/pilot-design-cookbook-2026-03-25.md as the source of truth.
  - Keep pilots narrow, measurable, and workflow-led.
  - Reuse must-win workflows, adoption loops, and buyer proof anchors.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Pilot design templates exist with targeted tests and no generic project-management drift.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 54 - Pilot Scorecard and Exit Logic

```yaml
outcome: Explicit pilot scorecards and exit states so pilots end in promote, extend narrowly, or stop with evidence.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/pilot_scorecards.py
    - backend/app/services/pilot_scorecard_service.py
    - backend/app/services/pilot_exit_logic_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/pilot-scorecard-and-exit-criteria-pack-2026-03-25.md as the source of truth.
  - Keep scorecards workflow-centered, not vanity-report oriented.
  - Reuse pilot design, adoption loops, and ROI proof anchors.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Pilot scorecards and exit logic exist with targeted tests and no fuzzy-success drift.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_pilot_scorecards.py -q
```

---

## Brief 55 - Case Study Proof Story Templates

```yaml
outcome: Structured proof-story templates that turn successful workflows into reusable buyer-legible case studies grounded in product truth.
files:
  modify:
    - backend/tests/
    - frontend/src/components/demo/
  create:
    - backend/app/schemas/case_study_templates.py
    - backend/app/services/case_study_template_service.py
    - frontend/src/components/demo/ProofStoryTemplateCard.tsx
    - frontend/src/components/__tests__/ProofStoryTemplateCard.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/case-study-template-and-proof-story-pack-2026-03-25.md as the source of truth.
  - Keep stories workflow-centered and evidence-centered, not brochure-style.
  - Reuse wow moments, ROI proof, and buyer counterproof anchors.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Structured proof-story templates exist with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 56 - Partner Certification Quality Signals

```yaml
outcome: Evidence-backed partner quality and certification primitives grounded in workflow discipline, trust signals, and rework reduction.
files:
  modify:
    - backend/tests/
  create:
    - backend/app/schemas/partner_certification.py
    - backend/app/services/partner_certification_service.py
    - backend/app/services/partner_quality_loop_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/partner-certification-and-quality-loop-pack-2026-03-25.md as the source of truth.
  - Ground quality in product-truth and workflow evidence, not badges alone.
  - Reuse partner trust, proof delivery, and handoff quality anchors.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Partner quality and certification primitives exist with targeted tests and evidence-backed semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_partner_certification.py -q
```

---

## Brief 57 - Customer Success Operating Loop Surfaces

```yaml
outcome: Product-visible customer-success milestones that tie deployment health to workflow wins, proof reuse, actor spread, and external trust.
files:
  modify:
    - backend/tests/
    - frontend/src/components/dashboard/
  create:
    - backend/app/schemas/customer_success_loops.py
    - backend/app/services/customer_success_loop_service.py
    - frontend/src/components/dashboard/CustomerSuccessLoopPanel.tsx
    - frontend/src/components/__tests__/CustomerSuccessLoopPanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/customer-success-operating-loop-pack-2026-03-25.md as the source of truth.
  - Anchor success milestones in workflow events, not generic account health.
  - Reuse post-sale adoption loops, ROI proof, and wow moments.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Customer-success loops are visible with targeted tests green.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 58 - Environment Parity and Demo Fidelity Foundations

```yaml
outcome: Shared parity primitives that reduce drift between local, demo, and real-integration workflow behavior.
files:
  modify:
    - backend/tests/
    - frontend/e2e-real/
  create:
    - backend/app/schemas/environment_parity.py
    - backend/app/services/environment_parity_service.py
    - backend/app/services/demo_fidelity_service.py
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/environment-parity-and-demo-fidelity-pack-2026-03-25.md as the source of truth.
  - Reduce demo and local drift; do not build a generic environment manager.
  - Reuse seeds, preflight, and real-e2e anchors.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Parity and demo-fidelity primitives exist with targeted tests and clearer environment semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd backend && python -m pytest tests/test_environment_parity.py -q
```

---

## Brief 59 - Record Retention and Evidence Lifecycle Foundations

```yaml
outcome: Shared lifecycle semantics for active, aging, archived, superseded, and trace-held records across proof, packs, and procedural artifacts.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
  create:
    - backend/app/schemas/record_lifecycle.py
    - backend/app/services/record_lifecycle_service.py
    - frontend/src/components/common/RecordLifecycleBadge.tsx
    - frontend/src/components/__tests__/RecordLifecycleBadge.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/record-retention-and-evidence-lifecycle-pack-2026-03-25.md as the source of truth.
  - Extend proof and freshness semantics; do not create a second archive universe.
  - Keep lifecycle visible enough to support trust and audit.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Record lifecycle primitives exist with targeted tests and visible lifecycle semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 60 - Jurisdiction Language and Terminology Foundations

```yaml
outcome: Shared terminology mapping for jurisdiction-aware user-facing language without flattening important Swiss procedural distinctions.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
  create:
    - backend/app/schemas/jurisdiction_terminology.py
    - backend/app/services/jurisdiction_terminology_service.py
    - frontend/src/components/common/JurisdictionTermHint.tsx
    - frontend/src/components/__tests__/JurisdictionTermHint.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
    - frontend/src/i18n/en.ts
    - frontend/src/i18n/fr.ts
    - frontend/src/i18n/de.ts
    - frontend/src/i18n/it.ts
constraints:
  - Use docs/projects/jurisdiction-language-and-terminology-pack-2026-03-25.md as the source of truth.
  - Map terms instead of flattening them.
  - Preserve jurisdiction-specific distinctions while staying user-legible.
  - Use inline fallbacks instead of editing hub i18n files.
exit: Terminology mapping primitives exist with targeted tests and bounded UI rendering.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```

---

## Brief 61 - Support Debug and Incident Handoff Foundations

```yaml
outcome: Clean support-to-engineering handoff primitives that preserve product context, workflow state, recent events, and environment clues.
files:
  modify:
    - backend/tests/
    - frontend/src/components/
  create:
    - backend/app/schemas/support_handoff.py
    - backend/app/services/support_handoff_service.py
    - frontend/src/components/common/SupportHandoffPanel.tsx
    - frontend/src/components/__tests__/SupportHandoffPanel.test.tsx
  do_not_touch:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/schemas/__init__.py
constraints:
  - Use docs/projects/support-debug-and-incident-handoff-pack-2026-03-25.md as the source of truth.
  - Preserve product context, not just technical error text.
  - Reuse failure-recovery, event taxonomy, and escalation anchors.
  - Prepare supervisor merge notes instead of editing hub files directly.
exit: Support-handoff primitives exist with targeted tests and clear incident-context semantics.
validate:
  - cd backend && ruff check app/ tests/
  - cd backend && python scripts/run_local_test_loop.py changed
  - cd frontend && npm run test:changed:strict
```
