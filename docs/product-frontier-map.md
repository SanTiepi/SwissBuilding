# SwissBuilding - Product Frontier Map

This document captures the broadest product horizon currently envisioned for SwissBuilding.
It is intentionally expansive.

Use it to:
- keep track of uncovered uses
- identify the next engines to build
- distinguish near-term leverage from long-term moonshots
- preserve ideas without forcing them all into the current execution program

Read this together with:
- `docs/vision-100x-master-brief.md`
- `docs/roadmap-next-batches.md`

## Frontier Principle

SwissBuilding should not think in terms of isolated features only.
It should think in terms of:
- building truth
- building proof
- building readiness
- building memory
- building orchestration
- portfolio arbitration
- rules-layer expansion
- controlled agency

The horizon is intentionally open-ended.
The only real constraint is sequencing.

## 48-Month Frontier Rule

The frontier should be imagined further ahead than the current roadmap window.

Rule:
- keep enough strategic headroom for roughly 48 months of product evolution
- prefer storing an oversized but structured frontier over rediscovering critical ideas too late
- accept that many entries will remain hidden or backend-only for a long time
- use triage and sequencing to control exposure, not to shrink ambition

## Scope Expansion v2

SwissBuilding should now be read not only as an ambitious building product, but as a **Built Environment Meta-OS**.

The official scope map is intentionally oversized and should already account for 12 macro-domains:

1. `Pre-Work, Diagnostics, and Proof`
2. `Works Execution and Post-Works Truth`
3. `Building Memory and Physical Intelligence`
4. `Technical Systems and Operations`
5. `Owner, Household, and Everyday Building Ops`
6. `Resident, Occupancy, and Co-Ownership`
7. `Transaction, Insurance, and Finance`
8. `Permits, Authorities, and Public Funding`
9. `Portfolio, Strategy, and Capital Allocation`
10. `Network, Distribution, and Ecosystem`
11. `Identity, Governance, and Legal-Grade Trust`
12. `Infrastructure, Standards, and Intelligence Layer`

Interpretation rule:
- wedge-first execution still applies
- but the frontier should no longer under-describe the endgame
- if a new idea touches lifecycle, economics, operations, procedure, or network layers, it should still be captured even if not immediately roadmap-worthy

## Anticipatory Architecture Rule

The product should usually prefer:
- anticipating low-regret domain structures early
- hiding or delaying visible UX when needed
- avoiding future retrofit debt

This means:
- not every reserved object needs immediate UI exposure
- not every hidden capability needs a page right away
- but important future states, packs, engines, and artifacts should be modeled early when the cost of not doing so is likely to be high later

## Near-Term Low-Regret Pulls

These are the next frontier objects worth anticipating even before they receive first-class UI, because they reduce future retrofit debt and compound well with the current product shape:

- `SavedSimulation`
  - enables scenario persistence, later comparison, and portfolio arbitration
- `DataQualityIssue`
  - gives the product a native object for missing, stale, conflicting, or unverifiable building truth
- `ChangeSignal`
  - turns important dossier deltas into explicit operational events
- `ReadinessAssessment`
  - formalizes state transitions such as `safe_to_start` and `safe_to_tender`
- `BuildingTrustScore`
  - separates dossier reliability from risk severity
- `UnknownIssue`
  - makes missing knowledge a first-class tracked object rather than a side effect
- `PostWorksState`
  - preserves what was removed, what remains, and what must be requalified after intervention

Rule:
- these objects are strong candidates for backend-first implementation before broad UI exposure
- prefer adding them when they support active workstreams or remove obvious future retrofit pain
- do not create shallow pages for them until they are tied to real user value

## International-Class Complements

These are not just optional polish. They are the layers that separate a strong niche tool from a future reference product.

### 1. Interoperability Layer

Needs:
- stable export formats
- partner-facing APIs
- event / webhook model
- future SDK surface for ERP / document / portfolio ecosystems

Why it matters:
- the product must be able to sit above existing systems before it can become central to them

### 2. Reliability and Recovery Layer

Needs:
- job progress tracking
- resumable long-running exports and processing
- cleaner validation baselines
- stronger real-environment test confidence

Why it matters:
- international-class products are trusted because they behave predictably under load and failure

### 3. Trust and Audit Layer

Needs:
- dossier reliability scoring
- explicit confidence and uncertainty
- deeper audit trails
- durable before/after state comparisons

Why it matters:
- proof is not only about source links; it is also about confidence, accountability, and change history

### 4. Multilingual and Multi-Jurisdiction Layer

Needs:
- terminology discipline across languages
- jurisdiction-aware labels and packs
- Europe -> country -> canton/state -> authority rule layering

Why it matters:
- the product should feel born for cross-border expansion, not retrofitted later

### 5. Partner Ecosystem Layer

Needs:
- contributor portals that can later become partner channels
- export/import conventions
- structured handoff packs for contractors, owners, authorities, insurers, lenders

Why it matters:
- becoming a reference app means becoming a reference exchange point

## A. Uses Already Addressed vs Missing Uses

### A1. Already strongly targeted

- pre-renovation pollutant diagnostics
- diagnostics and samples management
- risk scoring and explainability foundations
- documents and reports
- simulation and remediation cost estimation
- portfolio steering foundations
- real and mocked validation flows

### A2. Partially covered and still incomplete

- building physical structure and navigability
- evidence chain visibility
- living dossier and dossier export
- action orchestration
- cross-actor collaboration
- post-diagnostic document workflows
- portfolio prioritization beyond raw risk

### A3. Key uses not yet fully covered

- transaction / due diligence readiness
- insurance and financing readiness
- tender / contractor readiness
- field capture and on-site updates
- post-works truth and residual risk memory
- unknowns visibility
- contradiction detection
- plan-native building navigation
- cross-building learning loops
- trust/reliability scoring
- building transfer between actors
- rules-pack expansion beyond the current Swiss wedge
- standard exportable building passport

## B. Core Product Engines to Build

These are the most important engines because they increase proof, memory, readiness, orchestration, or portfolio leverage.

### 1. Building Passport Engine

Purpose:
- make the building a persistent, versioned, transferable object

What it should enable:
- longitudinal building memory
- transfer across owners / managers / contractors
- portable dossier state
- identity anchored by durable identifiers

### 2. Evidence Graph Engine

Purpose:
- connect every score, recommendation, obligation, document, sample, and action to its sources

What it should enable:
- explainable risk
- legal traceability
- contradiction detection
- audit-ready outputs

### 3. Readiness Engine

Purpose:
- turn building state into explicit operational statuses

Target states:
- `safe_to_start`
- `safe_to_renovate`
- `safe_to_tender`
- `safe_to_sell`
- `safe_to_insure`
- `safe_to_finance`
- `safe_to_intervene`

### 4. Unknowns Engine

Purpose:
- show what is not known yet, not only what is known

Examples:
- uninspected zones
- missing plans
- unconfirmed materials
- undocumented interventions
- incomplete diagnostics

### 5. Contradiction Engine

Purpose:
- detect conflicting truth claims across the dossier

Examples:
- sample vs report mismatch
- public import vs manual entry mismatch
- intervention history vs current building state mismatch
- plan vs field observation mismatch

### 6. Post-Works Truth Engine

Purpose:
- preserve what changed after intervention

Examples:
- removed
- remaining
- encapsulated
- treated
- recheck needed
- unknown after intervention

### 7. Plan Annotation Engine

Purpose:
- turn plans into a living operational interface

Examples:
- attach zones
- attach elements/materials
- attach photos and observations
- attach samples and evidence
- display proof heatmaps on plans

### 8. Field Capture Companion

Purpose:
- make the product usable in the field

Examples:
- mobile-friendly capture
- voice notes
- photos
- on-plan annotations
- quick checklists
- direct sync to the dossier

### 9. Tender / Contractor Readiness Engine

Purpose:
- decide when a building is ready to be put out to tender or handed to an execution company

Examples:
- contractor-ready packs
- required documents checklist
- constraints and reservations
- pollutant / intervention warnings

### 10. Authority / Owner / Contractor Pack Engine

Purpose:
- generate different proof artifacts for different stakeholders from one truth layer

Examples:
- authority pack
- owner pack
- contractor pack
- insurer pack
- due diligence pack

### 11. Portfolio Opportunity Engine

Purpose:
- identify where the highest-value action is, not just where the highest risk is

Examples:
- quick wins
- grouped campaigns
- low-effort dossier completion opportunities
- high-cost-of-delay situations
- sequence optimization across many buildings

### 12. Rules Pack Studio

Purpose:
- industrialize rules and workflow expansion

Target layering:
- Europe model
- country layer
- canton / state / region layer
- authority layer
- domain-specific playbooks

## C. Additional High-Value Solutions

### 1. Transaction Readiness Layer

Use case:
- support sale, purchase, and due diligence

Needs:
- `safe_to_sell`
- trust score
- unresolved unknowns
- buyer/seller proof packs

### 2. Insurance and Finance Readiness Layer

Use case:
- support underwriting, financing, refinancing, and risk review

Needs:
- dossier reliability
- latent risk visibility
- exclusions / caveats
- insurer / bank oriented outputs

### 3. Building DNA / Material Genome

Use case:
- reason deeply about materials, eras, interventions, and likely hidden substance patterns

Needs:
- material families
- installation period reasoning
- likely pollutant families
- hidden-risk heuristics tied to typology

### 4. Building Trust Score / Dossier Reliability Engine

Use case:
- separate building risk from dossier reliability

Needs:
- percent proven
- percent inferred
- percent obsolete
- percent contradictory
- trend over time

### 5. Building Memory Timeline Diff

Use case:
- compare the building across two states in time

Examples:
- before works / after works
- before import / after import
- before diagnostic / after diagnostic

### 6. Building Memory Transfer

Use case:
- transfer structured building truth when stakeholders change

Examples:
- new property manager
- new owner
- new contractor
- new diagnostician

### 7. Neighbor / Typology Learning Engine

Use case:
- use nearby buildings and typological similarity as explainable signal layers

Examples:
- likely materials
- likely pollutants
- common dossier gaps
- likely interventions

### 8. Risk-to-CAPEX Translator

Use case:
- turn readiness gaps, interventions, and risk into budgeting and sequencing decisions

Examples:
- capex envelopes
- delay cost
- campaign economics
- urgency ladders

## D. Moonshots

These are the most radical concepts currently on the table.

### 1. Building Time Machine

- replay what was known at any date
- see what was proven, assumed, missing, or contradictory at that moment

### 2. Intervention Simulator

- simulate what a planned intervention would invalidate, require, trigger, or update

### 3. Proof Heatmap on Plans

- visualize strong proof, weak proof, unknowns, and contradictions directly on plans

### 4. Regulatory Diff Engine

- compare Europe / country / canton / authority rules
- compare old vs new obligations
- show which rule delta changed readiness

### 5. Building Readiness Wallet

- store multiple readiness states for different use cases

### 6. Autonomous Dossier Completion Agent

- identify missing items
- request them from the right contributors
- relaunch
- rebuild the pack
- update completeness

### 7. Cross-Building Pattern Engine

- learn from recurring dossier, material, and intervention patterns across buildings

### 8. Agent Audit Console

- track which agent proposed what
- on what proof
- with what confidence
- validated by whom

### 9. Building Passport Export Standard

- create a portable, versioned, transferable dossier format
- potentially become a market interface standard

### 10. European Rules Layer as Product

- build not just local rules, but a reusable rules system that can scale geographically

## D2. Killer Demo Surfaces

These are the moonshots most worth pulling downward into implementation because they create immediate product wow while reinforcing the core architecture.

1. **Building Time Machine**
   - replay what was known, proven, missing, or contradictory at a given time
2. **Proof Heatmap on Plans**
   - show strong proof, weak proof, unknowns, and contradictions directly on plans
3. **Intervention Simulator**
   - predict what a planned intervention invalidates, triggers, or requires
4. **Readiness Wallet**
   - make multiple readiness states visible as one coherent decision surface
5. **Autonomous Dossier Completion Agent**
   - detect missing proof and orchestrate the shortest path to completion

Rule:
- these are the best “impressive but still believable” features to pull into the product once the core trust/readiness/compliance layers are stable

## E. Internal Tools We Should Build

These tools may never be the main customer-facing product, but they can radically accelerate quality, learning, and moat.

### 1. Knowledge Capture Workbench

- correct OCR extractions
- normalize terminology
- curate evidence relationships
- train structured extraction workflows

### 2. Rules Pack Studio

- edit and validate rules packs internally
- version them cleanly
- compare jurisdictions and playbooks

### 3. Agent Audit Console

- govern agentic automation
- inspect outcomes and confidence
- support safe deployment of invisible agents

### 4. Dataset Curation Bench

- build better demo and learning datasets
- organize edge cases, contradictions, and post-works states

### 5. Building Passport Export Toolkit

- export, validate, diff, and import building passport artifacts

## F. Platform / Tooling Boosters

These tools amplify product capability and should remain tied to explicit product outcomes.

### Immediate

- `OCRmyPDF`
- `Dramatiq + Redis`
- `ClamAV`

### Near-term

- `Gotenberg`
- `Meilisearch`
- `GlitchTip`

### Conditional

- `Docling`
- `PaddleOCR`

## G. Prioritization Framework

When choosing what to build next, prefer what increases one or more of:
- proof
- memory
- readiness
- orchestration
- portfolio arbitration
- transferability
- defensibility

## H. Recommended Order of Strategic Depth

### Must build

- Building Passport Engine
- Evidence Graph Engine
- Readiness Engine
- Unknowns Engine
- Contradiction Engine
- Post-Works Truth Engine

### Strong moat builders

- Plan Annotation Engine
- Tender / Contractor Readiness Engine
- Authority / Owner / Contractor Pack Engine
- Portfolio Opportunity Engine
- Rules Pack Studio
- Building Trust Score

### Moonshot builders

- Building Time Machine
- Building Passport Export Standard
- Cross-Building Pattern Engine
- European Rules Layer as Product
- Autonomous Dossier Completion Agent

### Internal force multipliers

- Knowledge Capture Workbench
- Agent Audit Console
- Dataset Curation Bench

## I. Design Rule

Do not treat these as random ideas to dump into the product.

They should compound into one system:
- the building is known
- the building is proven
- the building is ready or not ready
- the building can be transferred
- the building can be acted on
- the building can be arbitrated in a portfolio
- the system gets smarter without becoming opaque

## J. Extended Idea Reservoir

This section is intentionally broad.
It captures additional solution spaces that may later be merged into engines, products, internal tools, or packs.

### J1. Building Fabric and Physical Truth

1. **Cavity Registry**
   - track what may exist behind walls, ceilings, shafts, and floors even when not yet opened
2. **Hidden Layer Hypothesis Map**
   - explicit hypotheses for unseen construction layers and likely materials
3. **Building Systems Atlas**
   - map HVAC, ducts, pipes, electrical, technical rooms, and service risers as living systems
4. **Material Aging Predictor**
   - estimate likely degradation, brittleness, or contamination risk based on age and context
5. **Zone / Room Lifecycle History**
   - preserve how rooms and zones changed over time
6. **Component Genealogy**
   - track which element replaced or superseded which prior element
7. **Thermal + Pollutant Overlay**
   - combine energy/thermal context with pollutant and material risk
8. **Accessibility Constraint Layer**
   - capture access difficulty, destructive access needs, safety limits, and inspection friction
9. **Fire and Safety Overlay**
   - map fire compartments, escapes, and safety-critical intersections with pollutant/remediation work
10. **Hazard Path Mapping**
    - model how risk propagates across connected zones or systems

### J2. Evidence, Proof, and Truth Maintenance

11. **Evidence Decay Engine**
    - downgrade confidence as evidence becomes stale or conditions change
12. **Burden-of-Proof Estimator**
    - estimate how much proof is still needed before a decision can be defended
13. **Legal Applicability Map**
    - show exactly which rule set applies to which building, zone, time, and intervention
14. **Citation Snapshot Engine**
    - store the exact rule text/version used when a recommendation was made
15. **Evidence Confidence Ladder**
    - classify proof strength from declared -> inferred -> observed -> sampled -> confirmed
16. **Consensus Engine**
    - detect when multiple sources agree strongly and where they diverge
17. **Counter-Evidence Workflow**
    - track evidence that weakens or contradicts an existing belief
18. **Proof Gap Forecaster**
    - predict which missing pieces are most likely to block the next phase
19. **Versioned Legal Pack**
    - freeze the legal/referential context attached to a dossier or decision
20. **Evidence Reuse Engine**
    - safely reuse proof across future interventions, tenders, or portfolio decisions

### J3. Readiness States and Decision Surfaces

21. **Permit Readiness**
    - determine whether the dossier is ready for permit-related workflows
22. **Remediation Readiness**
    - determine whether pollutant treatment can start safely
23. **Tender Readiness**
    - determine whether the building is ready to be sent to contractors
24. **Occupancy Safety Readiness**
    - determine whether current occupants face unresolved safety/documentation gaps
25. **Demolition Readiness**
    - determine whether a demolition or strip-out phase is properly documented and safe
26. **Partial-Zone Readiness**
    - determine readiness by zone, not only by whole building
27. **Financing Readiness**
    - determine whether the dossier is strong enough for financing review
28. **Insurance Readiness**
    - determine whether evidence and residual risks are clear enough for underwriting
29. **Resale Readiness**
    - determine whether the asset is prepared for due diligence and transfer
30. **Chain-of-Custody Readiness**
    - ensure work, waste, and evidence can be tracked end-to-end

### J4. Field, Inspection, and Execution

31. **Geo-Tagged Field Capture**
    - capture field observations with plan/zone context and geolocation where relevant
32. **Inspection Route Planner**
    - propose efficient on-site paths for inspections and sample collection
33. **Sampling Planner**
    - recommend where and how many samples to take based on building uncertainty
34. **Safety Briefing Generator**
    - generate a zone/intervention-specific briefing before field work
35. **Zone / Material QR Labels**
    - label physical zones/elements/materials and bind them to the digital twin
36. **Offline Field Mode**
    - capture data without connectivity and sync back later
37. **Contractor Acknowledgment Workflow**
    - confirm that external parties saw and acknowledged risks/reservations
38. **Waste Chain Tracking**
    - track removal, waste categories, transport, and disposal proof
39. **Photo Re-Detection Engine**
    - align new field photos with known plans/zones/elements over time
40. **Before/After Evidence Composer**
    - generate structured before-vs-after field proof packs

### J5. Portfolio, Campaigns, and Strategy

41. **Campaign Recommendation Engine**
    - suggest which campaign to run next across a portfolio
42. **Portfolio Blind-Spot Heatmap**
    - show where the portfolio is least known or least defensible
43. **Delay Cost Escalator**
    - estimate how much cost or risk grows when action is postponed
44. **Bundling Engine**
    - identify where interventions or diagnostics should be grouped
45. **Contractor Capacity Matching**
    - match campaign scope to available external execution capacity
46. **Portfolio Readiness Ladder**
    - classify assets from not-ready to intervention-ready to proof-ready
47. **Cross-Portfolio Benchmarking**
    - compare building types, dossier maturity, and risk posture across portfolios
48. **Scenario Stress Testing**
    - test capex/risk impacts under regulation, timing, or evidence shocks
49. **Geographic Campaign Clustering**
    - cluster work by geography, typology, or regulatory context
50. **Evidence Debt Dashboard**
    - show the portfolio-wide backlog of missing proof and unresolved unknowns

### J6. Ecosystem and Commercial Packs

51. **Lender Pack**
    - package building truth for lenders and refinancing discussions
52. **Insurer Pack**
    - package residual risk, exclusions, and proof for insurers
53. **Municipality Pack**
    - package the subset of information a municipality or authority actually needs
54. **Buyer / Seller Negotiation Pack**
    - package what is known, unknown, and reserved during transaction discussions
55. **Building Handover Package**
    - package a building dossier for change of manager/owner/operator
56. **ESG-to-Proof Bridge**
    - connect high-level ESG/renovation targets to building-level evidence
57. **Supplier Evidence Portal**
    - allow contractors/labs/suppliers to upload bounded evidence into the chain
58. **Broker / Transaction Workspace**
    - support building-level transaction workflows with dossier and proof visibility
59. **Asset Committee Pack**
    - generate investor/board-ready decision packs
60. **Litigation / Claims Pack**
    - generate defensible evidence packages for disputes or claims

### J7. Standards, Data, and Network Effects

61. **Building Passport Schema**
    - define the structured format of the building passport itself
62. **Evidence Exchange Standard**
    - define how proof and provenance can move between systems
63. **Rules Pack Registry**
    - version and catalogue the rules layers and playbooks in use
64. **Cross-Jurisdiction Mapping Engine**
    - map equivalent concepts across countries, cantons, and authorities
65. **Semantic Building Ontology**
    - define the vocabulary that underpins materials, zones, elements, and evidence
66. **Source Reliability Ranking**
    - score public, private, declared, and inferred sources over time
67. **Privacy-Preserving Benchmarking**
    - extract learning effects without exposing sensitive building specifics
68. **Portfolio Learning Graph**
    - connect recurring building, intervention, and proof patterns at scale
69. **Building Fingerprint Model**
    - describe the characteristic signature of a building and its likely hidden issues
70. **Public-Data Delta Monitor**
    - detect when source registries or public layers have changed in a meaningful way

### J8. Agents and Internal Force Multipliers

71. **Dossier QA Agent**
    - scan the dossier for missing proof, stale references, and obvious inconsistencies
72. **Contradiction Investigation Agent**
    - propose the shortest path to resolve a contradiction
73. **Jurisdiction Pack Authoring Assistant**
    - accelerate the creation of new country/canton/authority rules packs
74. **Plan-to-Zone Bootstrap Agent**
    - propose initial zones and structures from uploaded plans
75. **Sample-to-Material Linker**
    - suggest the most likely material/evidence relations after analysis results arrive
76. **Export Pack Composer**
    - assemble the right pack for authority, owner, insurer, or contractor context
77. **Requalification Trigger Agent**
    - detect when the building should be re-opened or re-reviewed
78. **Account Expansion Insight Agent**
    - detect where one successful building can unlock account-wide rollout
79. **Data Quality Triage Console**
    - prioritize which conflicts or missing data items deserve human attention first
80. **Synthetic Scenario Generator**
    - generate realistic training/demo scenarios for new product layers

### J9. Commercial and Financial Expansion

81. **Transaction Readiness Workspace**
    - support due diligence and seller/buyer handoffs
82. **Insurance Underwriting Readiness**
    - turn dossier truth into underwriting-friendly surfaces
83. **Lender Review Layer**
    - package trust, readiness, and residual risk for financing review
84. **Refinancing Trigger Engine**
    - identify when improved trust/readiness changes financing posture
85. **Portfolio Exit Readiness**
    - identify which buildings are most ready for disposal or transfer

### J10. Europe-Scale Rules and Governance

86. **Rules Pack Studio**
    - author, validate, diff, and publish rules packs at scale
87. **Authority Rules Registry**
    - catalogue authority-specific pack logic and required artefacts
88. **Regulatory Applicability Explorer**
    - explain exactly why a rule set applies to a building or intervention
89. **Cross-Border Expansion Kit**
    - structure country-level entry from the Europe baseline
90. **Rules Quality Bench**
    - detect broken, missing, conflicting, or stale rules packs

### J11. Agentic Governance and Knowledge Ops

91. **Agent Run Ledger**
    - durable record of agent proposals, evidence, confidence, and human validation
92. **Knowledge Correction Workbench**
    - human correction of extraction, classification, and linking outputs
93. **Scenario Curation Studio**
    - curate reusable hard cases for demos, testing, and learning
94. **Ontology Evolution Console**
    - manage vocabulary changes across materials, risks, and building structure
95. **Recommendation QA Harness**
    - evaluate agent and rules outputs against expected outcomes

### J12. Market Infrastructure and Exchange

96. **Building Passport Exchange Standard**
    - portable machine-readable building truth package
97. **Evidence Exchange Contract**
    - normalized proof transfer between systems and actors
98. **Contributor Gateway**
    - bounded ecosystem entry point for labs, diagnosticians, contractors
99. **Partner Event Layer**
    - webhook/event model for ecosystem interoperability
100. **Public Data Delta Monitor**
    - reopen dossiers when external truth changes

### J13. Institutional Portfolio Intelligence

101. **Portfolio Command Center**
     - execution-first portfolio cockpit
102. **Opportunity Cluster Engine**
     - surface the most leverageable building groups
103. **Risk-to-CAPEX Translator**
     - convert residual truth into budget action
104. **Executive Readiness Board**
     - board-level view across sell / insure / finance / start / tender states
105. **Institutional Benchmark Layer**
     - compare portfolio health and trust across large asset bases

### J14. Reliability, Recovery, and Operator Trust

106. **System Health Snapshot**
     - summarize dependency and subsystem health in product terms
107. **Derived State Freshness**
     - show whether trust/readiness/search-derived states are current or stale
108. **Retryable Export Flow**
     - rerun failed dossier and pack generation safely
109. **Index Sync Status**
     - expose whether search indexes are lagging or stale
110. **Support Bundle Export**
     - package technical diagnostics for troubleshooting without deep log-diving

### J15. Demo, Sales, and Category Acceleration

111. **Demo Scenario Selector**
     - choose seeded narratives by persona or outcome
112. **Executive Narrative Surfaces**
     - explain value in buyer language without leaving the product
113. **Operator Demo Panel**
     - quickly reset, switch, and validate demo states
114. **Persona Pack Presets**
     - generate owner / authority / contractor / executive variants fast
115. **Commercial Wow Runbooks**
     - reusable scenario scripts tied to product truth, not fake demo hacks

### J16. Privacy, Security, and Data Governance

116. **Audience Scope Model**
     - define which truth subsets belong to which audience class
117. **Sensitive Evidence Classification**
     - mark which artefacts are internal-only, shareable, or redaction-worthy
118. **Redaction Profile Engine**
     - generate bounded outputs by audience without ad hoc manual trimming
119. **Evidence Access Ledger**
     - track who accessed high-sensitivity evidence and pack artifacts
120. **Retention and Stewardship Layer**
     - make archival, retention, and ownership of sensitive dossier data explicit

### J17. Distribution and Embedded Channels

121. **Embedded Passport Card**
     - bounded building summary for insertion into adjacent systems
122. **Readiness / Trust Widget**
     - lightweight embedded state surface for operator and executive contexts
123. **External Viewer**
     - controlled external-facing building/pack view for bounded audiences
124. **Partner Summary Endpoint**
     - stable machine-facing summary for integrations and ecosystem pull
125. **Account Expansion Trigger**
     - detect and operationalize the moments where one successful project should spread across the account

### J18. Occupant Safety and Communication

126. **Occupancy Safety Readiness**
     - determine whether unresolved building truth creates occupant-facing safety uncertainty
127. **Zone Restriction Surface**
     - communicate where access or caution rules apply at zone level
128. **Occupant Notice Engine**
     - generate bounded notices linked to intervention and proof state
129. **Notice Delivery / Acknowledgement Tracking**
     - know whether bounded safety communication actually reached its audience
130. **Occupant Pack**
     - share only the evidence-backed subset that a resident or non-expert actor needs

### J19. openBIM and Digital Logbook Convergence

131. **IFC Mapping Profile**
     - map core building passport objects toward IFC/openBIM concepts where useful
132. **BCF Issue Bridge**
     - express contradictions, open issues, and coordination items in an interoperable issue model
133. **IDS Requirement Profile**
     - define machine-readable information requirements and checking logic
134. **Digital Building Logbook Mapping**
     - map SwissBuilding memory and passport concepts toward DBL-style artifacts
135. **Renovation Passport Export**
     - generate machine-readable renovation/passport-oriented outputs

### J20. Semantic Building Operations

136. **Building System Ontology**
     - model HVAC, ventilation, fire, water, and electrical systems distinctly from materials and structure
137. **Technical Equipment Layer**
     - make technical equipment inspectable and connectable to plans/zones/interventions
138. **Semantic Mapping Profile**
     - prepare alignment with Brick / Haystack style semantics
139. **System Readiness**
     - evaluate readiness and residual truth at the system/equipment layer
140. **Operations Pack**
     - package bounded system-level truth for maintenance and technical operations use cases

### J21. Legal-Grade Proof and Custody

141. **Proof Version**
     - canonical version semantics for dossiers and packs
142. **Custody Event**
     - track handling, approval, transmission, and archival of proof artifacts
143. **Delivery Receipt**
     - prove pack or artefact delivery in a defensible way
144. **Archived Snapshot**
     - preserve legally meaningful evidence exports as explicit snapshots
145. **Signature Placeholder Layer**
     - prepare future e-signature and acknowledgement integrations

### J22. Enterprise Identity and Tenant Governance

146. **Tenant Boundary**
     - make multi-tenant and org boundaries explicit where needed
147. **Delegated Access Grant**
     - bounded access delegation for scoped actors and projects
148. **Temporary Role Grant**
     - limited-time access patterns for due diligence, support, or contractors
149. **Impersonation Audit**
     - governed support/admin access traceability
150. **Identity Provider Config**
     - future SSO/SAML/OIDC integration path

### J23. BIM, 3D, and Geometry-Native Intelligence

151. **Geometry Anchor**
     - durable anchors linking plans, zones, issues, and model geometry
152. **Spatial Issue**
     - geometry-bound contradiction, unknown, or intervention issue
153. **Model Snapshot**
     - preserve a specific geometry/model state over time
154. **Plan Reality Diff**
     - compare expected geometry or plan truth with observed state
155. **IFC Geometry Reference**
     - selective IFC-aware geometry linkage

### J24. Execution Quality and Hazardous Works Operations

156. **Execution Checkpoint**
     - structured control points during hazardous works
157. **Method Statement**
     - bounded method/workflow record for risky interventions
158. **Work Quality Record**
     - execution-side quality evidence and validation
159. **Acceptance Step**
     - partial/final acceptance semantics with reopen conditions
160. **Disposal Chain Record**
     - stronger linkage between works, waste, and disposal truth

### J25. Partner Network and Contributor Reputation

161. **Contributor Quality Signal**
     - measure contribution quality and responsiveness
162. **Partner Trust Profile**
     - internal trust layer for contributors and partners
163. **Delivery Reliability Score**
     - track repeated delivery quality and completeness
164. **Routing Suggestion**
     - recommend partner routing based on fit and reliability
165. **Network Pull Indicator**
     - detect where ecosystem usage strengthens product spread

### J26. Benchmarking, Learning, and Market Intelligence

166. **Benchmark Snapshot**
     - compare maturity and readiness across assets or portfolios
167. **Learning Signal**
     - structured reusable signal from repeated outcomes and patterns
168. **Portfolio Pattern**
     - recurring combination of truth, gap, and intervention shape
169. **Privacy-Safe Aggregate**
     - benchmark without exposing sensitive dossier identity
170. **Recommendation Learning Input**
     - connect validated aggregate learning back into product engines

## L. Canonical System Gaps Now Tracked as Programs

The following clusters are no longer just idea families.
They now have dedicated executable briefs under `docs/projects/` and should be treated as the next system-level expansion family:

- `J21 Legal-Grade Proof and Custody`
  - `docs/projects/legal-grade-proof-and-chain-of-custody-program.md`
- `J22 Enterprise Identity and Tenant Governance`
  - `docs/projects/enterprise-identity-and-tenant-governance-program.md`
- `J23 BIM, 3D, and Geometry-Native Intelligence`
  - `docs/projects/bim-3d-and-geometry-native-intelligence-program.md`
- `J24 Execution Quality and Hazardous Works Operations`
  - `docs/projects/execution-quality-and-hazardous-works-operations-program.md`
- `J25 Partner Network and Contributor Reputation`
  - `docs/projects/partner-network-and-contributor-reputation-program.md`
- `J26 Benchmarking, Learning, and Market Intelligence`
  - `docs/projects/benchmarking-learning-and-market-intelligence-program.md`

Rule:
- treat these as canonical system gaps, not optional theme notes
- once the active trust/readiness/post-works and portfolio productization waves are stable, this family becomes the next natural international-class expansion surface

### J27. Owner Operating Layer

171. **Expense Record**
     - recurring and event-based owner/building expenses linked to truth
172. **Renovation Budget**
     - first-class building budget envelopes, reserve, and variance
173. **Vault Document**
     - durable, trusted owner-side record storage beyond workflow attachments
174. **Insurance Policy Memory**
     - policy, coverage, exclusions, and renewal awareness tied to the building
175. **Claim Pack**
     - insurer-facing reusable proof package for incidents and claims

Rule:
- this cluster should support the future "super app" direction without collapsing into generic personal finance or generic cloud storage
- it is a future owner-operating layer that compounds building truth rather than replacing it

### J28. Permit, Funding, and Procedure Layer

176. **Permit Procedure**
     - procedural readiness and authority-step tracking
177. **Authority Submission**
     - explicit procedural artifact and decision record
178. **Funding Eligibility Check**
     - subsidy/grant readiness tied to proof
179. **Funding Pack**
     - reusable package for subsidy/public funding workflows
180. **Procedural Blocker**
     - explicit blocker between technical readiness and legal/procedural execution

### J29. Co-Ownership and Resident Governance

181. **Ownership Group**
     - multi-owner structure for a building
182. **Governance Decision**
     - board/co-owner decision record linked to works and packs
183. **Vote Record**
     - collective approval trail
184. **Resident Notice**
     - bounded resident communication artifact
185. **Restriction Window**
     - time-bounded restriction or impact window for residents

### J30. Energy, Carbon, and Live Performance

186. **Performance Snapshot**
     - observed energy/carbon state at a point in time
187. **Performance Gap**
     - target vs observed delta
188. **Drift Signal**
     - ongoing deterioration or deviation detection
189. **Meter Ingest Profile**
     - structured path for recurring performance data
190. **Performance Feed**
     - live or periodic operating performance surface

### J31. Warranty, Defects, and Service Obligations

191. **Warranty Record**
     - post-works warranty memory linked to interventions and systems
192. **Defect Record**
     - ongoing issue after delivery or operation
193. **Service Obligation**
     - recurring service / compliance duty tied to the building
194. **Warranty Expiry Signal**
     - action-driving expiry awareness
195. **Renewal Signal**
     - recurring duty or service renewal trigger

### J32. Constraint and Unlock Intelligence

196. **Constraint Node**
     - explicit blocker or dependency in the building graph
197. **Dependency Edge**
     - formal relation between what blocks and what is blocked
198. **Unlock Action Hint**
     - smallest move likely to unlock the most value or readiness
199. **Critical Dependency Path**
     - highest-impact blocker chain
200. **Blocking Condition**
     - explicit constraint between proof, procedure, budget, or execution

### J33. Decision Replay and Operator Memory

201. **Decision Record**
     - why a choice was made at a given moment
202. **Decision Assumption**
     - what was accepted as true or uncertain
203. **Override Reason**
     - why human judgement overrode the system
204. **Decision Replay Surface**
     - time-based reconstruction of what was known and decided
205. **Judgement Split**
     - explicit human-versus-system reasoning divergence

### J34. Weak-Signal Watchtower

206. **Weak Signal**
     - low-grade precursor to future blocker or drift
207. **Signal Pattern**
     - recurring combination of small signals
208. **Signal Severity Trend**
     - how small signals intensify over time
209. **Watchtower Warning**
     - escalated early warning before red-state failure
210. **Pre-Blocker Alert**
     - operator-facing alert before readiness actually collapses

### J35. Multimodal Building Understanding

211. **Multimodal Source Fragment**
     - grounded fragment from PDF, plan, image, voice, or table
212. **Grounded Answer**
     - evidence-backed natural-language answer with citations
213. **Cross-Modal Link**
     - alignment between report, plan, image, and observation
214. **Answer Citation**
     - explicit source support for a response
215. **Extracted Claim**
     - structured claim derived from multimodal evidence

### J36. Autonomous Dossier Completion

216. **Completion Plan**
     - agent-generated sequence to close dossier gaps
217. **Missing Artifact Request**
     - targeted request for the exact missing item
218. **Proposed Update**
     - reviewable, agent-suggested dossier update
219. **Verification Trace**
     - evidence-first log of what the agent checked and why
220. **Agent Completion Run**
     - bounded execution record for a completion cycle

### J37. Cross-Modal Change Detection and Reconstruction

221. **Change Hypothesis**
     - likely building change inferred from mixed evidence
222. **Reconstruction Hypothesis**
     - inferred state reconstruction with uncertainty
223. **Cross-Modal Diff**
     - structured delta across plans, reports, photos, and interventions
224. **Change Evidence Set**
     - source bundle supporting a change conclusion
225. **Requalification Trigger**
     - explicit trigger to reopen or re-evaluate a building state

### J38. Open-Source Acceleration Layer

226. **Docling Pull Path**
     - multimodal document understanding acceleration path
227. **IfcOpenShell Pull Path**
     - IFC/geometry acceleration path
228. **Brick / Haystack Pull Path**
     - open semantics for systems and live operations
229. **Temporal Pull Path**
     - durable execution acceleration path
230. **OpenTelemetry / SigNoz / Keycloak / PMTiles Pull Path**
     - mature open-source building blocks for observability, identity, and spatial distribution
231. **Argilla / Label Studio / CVAT Pull Path**
     - human correction, dataset curation, and plan/photo annotation acceleration path
232. **OpenFGA / OPA Pull Path**
     - relationship-aware sharing and policy-as-code acceleration path
233. **DuckDB / Ibis Pull Path**
     - embedded analytics and benchmark computation acceleration path
234. **OpenLineage Pull Path**
     - lineage and pipeline traceability acceleration path
235. **Apache Tika Pull Path**
     - broad metadata extraction and vault normalization acceleration path
236. **Valkey Pull Path**
     - Redis-compatible infra acceleration path if queue/cache posture shifts

### J39. System Refinement and Hardening

237. **Search Relevance Tuning**
     - make retrieval quality and navigation feel deliberate, not merely indexed
238. **Pack Infrastructure Hardening**
     - make export and pack generation resilient, resumable, and inspectable
239. **Real E2E Ownership**
     - make real-environment validation clearly targeted and preflight-safe
240. **Workflow Replay and Recovery**
     - make long-running processes auditable, replayable, and recoverable
241. **Seed Determinism Layer**
     - make scenario-rich seeds predictable, reviewable, and verifiable
242. **Migration and Backfill Safety**
     - keep fast model growth compatible with safe evolution
243. **Archive and Retention Policy**
     - turn document/file retention into an explicit product concern
244. **UI Language and Token Discipline**
     - keep copy, dark mode, and shared UI semantics coherent at scale
245. **Integration Boundary Map**
     - make ownership of OCR, search, export, map, and policy subsystems explicit
246. **Frontend Async State Standardization**
     - make loading, error, empty, and data states consistent across cards, feeds, tabs, and intelligence panels
247. **Modernization Review Cycle**
     - institutionalize periodic upgrade/review passes once the product surface gets large

### J40. Tenancy and Occupancy Economics

248. **Lease Record**
     - persistent lease truth linked to units, works, and restrictions
249. **Vacancy / Impact Tracking**
     - know which units are empty, occupied, or disrupted by works
250. **Rent Impact Window**
     - capture when works, restrictions, or risks affect rent economics
251. **Tenant Claim Record**
     - connect complaints, claims, and disruption memory back to the dossier
252. **Rent Reduction Support Pack**
     - bounded support artefact for documented disruption situations

### J41. Utilities and Recurring Service Contracts

253. **Utility Account**
     - durable memory of utility providers and accounts
254. **Meter Contract**
     - metering responsibility and continuity memory
- **Service Vendor Contract**
     - recurring service and maintenance provider truth
255. **Recurring Invoice Memory**
     - operating cost continuity over time
256. **Maintenance SLA Renewal Signal**
     - service renewals and missed obligations as first-class signals

### J42. Incident, Emergency, and Continuity

257. **Incident Record**
     - structured operational incident memory
258. **Building Shutdown State**
     - explicit temporary shutdown or restricted operation state
259. **Emergency Readiness**
     - whether the building can be safely operated under abnormal conditions
260. **Crisis Communication Pack**
     - bounded emergency-facing communication artefact
261. **Incident-to-Claim Bridge**
     - start insurer and proof flows directly from incident truth

### J43. Procurement, Vendor, and SLA Control

262. **Vendor Contract**
     - first-class procurement and service contract object
263. **Framework Agreement**
     - recurring relationship memory with contractors or service vendors
264. **Vendor Prequalification**
     - know who is suitable for which work type
265. **Tender Package**
     - contractor-facing pack with constraints, readiness, and requirements
266. **Service-Level Monitoring**
     - whether recurring obligations are actually delivered as contracted

### J44. Circularity and Material Afterlife

267. **Removed Material Passport**
     - structured afterlife record for removed materials
268. **Disposal Chain Expansion**
     - stronger linkage from material removal to final disposal proof
269. **Reuse / Salvage Candidate**
     - track components or materials that may have second life
270. **Circularity Score**
     - explicit circularity and reuse potential signal
271. **Waste Trace Pack**
     - artefact for downstream regulated waste and material handling

### J45. Tax, Incentive, and Fiscal Readiness

272. **Fiscal Readiness**
     - whether a dossier can support fiscal or incentive workflows
273. **Tax Document Pack**
     - owner or portfolio artefact for fiscal handling
274. **Grant Timeline**
     - timing memory for subsidy and public incentive windows
275. **Incentive Loss Risk**
     - signal that a project may miss a funding opportunity
276. **Rebate Eligibility Memory**
     - durable record of what incentives were possible, claimed, or lost

### J46. Climate Resilience and Environmental Context

277. **Flood / Heat / Noise Context**
     - territorial context beyond pollutants
278. **Resilience Readiness**
     - whether a building is prepared for resilience-related expectations or works
279. **Climate Retrofit Dependency**
     - what additional interventions are required for adaptation
280. **Environmental Risk Context**
     - cross-link building truth with broader territorial environmental pressure
281. **Territory-Aware Priority Signal**
     - use context to influence portfolio and procedure logic

### J47. Training, Certification, and Operating Enablement

282. **Operator Readiness**
     - whether an actor is prepared to execute or review a workflow correctly
283. **Contractor Competency Memory**
     - durable signal of capability and fitness for certain work
284. **Mandatory Training Pack**
     - bounded training or onboarding artefact for risky workflows
285. **SOP Playbook Library**
     - reusable operating recipes tied to rules, packs, and evidence
286. **QA Reviewer Certification Layer**
     - confidence that critical reviews were performed by suitably prepared actors

### J48. Territory, Utilities, and Public Systems

287. **Public-System Dependency Map**
     - explicit dependencies on utilities, authorities, and public systems
288. **Territory Procedure Layer**
     - procedural context beyond the building itself
289. **Utility Interruption Impact**
     - model impacts of network outages or service disruption on building readiness
290. **District / Block Coordination Surface**
     - capture where multiple assets share context, risk, or execution constraints
291. **Public-Owner Operating Model**
     - support state, municipality, and institutional governance patterns

### J49. Built Environment Infrastructure and Market Standardization

292. **Market Reference Schema**
     - candidate canonical data contract for building truth and evidence exchange
293. **Inter-System Trust Handshake**
     - bounded exchange of trust, readiness, and proof between systems
294. **Network State Snapshot**
     - see portfolio, contributor, and territory intelligence as one operating graph
295. **External Reliance Signal**
     - measure when other tools or actors start depending on SwissBuilding truth
296. **Meta-OS Governance Layer**
     - govern how the product evolves from software into market infrastructure

### J50. Dataset and Scenario Infrastructure

297. **Canonical Demo Dataset**
     - stable, high-wow, authority-ready demo buildings and flows
298. **Ops Truth Dataset**
     - realistic incomplete, contradictory, and operator-grade building cases
299. **Portfolio Dataset**
     - enough breadth for campaigns, signals, CAPEX, and benchmark surfaces
300. **Compliance Dataset**
     - AvT/ApT, authority artefacts, disposal chain, post-remediation truth
301. **Multimodal Dataset**
     - PDFs, plans, images, photos, technical drawings, and cross-modal contradictions
302. **Edge-Case Dataset**
     - broken imports, stale proofs, orphan references, partial dossiers, odd but valid states
303. **Scenario Manifest**
     - explicit ownership of which seed scripts power which scenario families
304. **Seed Determinism Contract**
     - repeatable, reviewable, non-random canonical scenarios
305. **Real E2E Dataset Preflight**
     - fail fast when the wrong seeded world is present
306. **Dataset Evolution Policy**
     - every new major product surface eventually gets a clean scenario and a messy one

### J51. Read Models, Query Topology, and Aggregate APIs

307. **Building Summary Aggregate**
     - one coherent screen-level read for building overview surfaces
308. **Portfolio Summary Projection**
     - aggregate portfolio truth without page-level query sprawl
309. **Pack and Export Status Aggregate**
     - a single source of truth for generation progress, retries, and stale state
310. **Query Topology Contract**
     - explicit policy for shell reads, detail reads, and drill-down reads
311. **Read Projection Registry**
     - documented map of which major surfaces are live-computed vs projection-backed

### J52. API Contract Integrity and Generated Clients

312. **Schema Drift Radar**
     - detect where backend and frontend contracts diverge or duplicate too much
313. **Enum Sync Layer**
     - one reliable path for high-change enum/value surfaces
314. **OpenAPI Client Pull Path**
     - generated or semi-generated client strategy for volatile domains
315. **Exchange Contract Profile**
     - bounded, durable shapes for partner and passport/exchange APIs
316. **Contract Guardrail Check**
     - lightweight validation that makes API drift visible before it becomes product debt

### J53. Async Jobs, Projections, and Background Orchestration

317. **Job Lifecycle Model**
     - common model for queued/running/completed/failed/retried work
318. **Projection Candidate Registry**
     - identify which high-value surfaces should be projection-backed
319. **Replay and Backfill Path**
     - re-run projections and derived truth safely after model/rules changes
320. **Operator Recovery Surface**
     - explicit retry/recovery for stuck exports, packs, and derived jobs
321. **Agent-Ready Background Spine**
     - bounded orchestration layer for completion, indexing, packs, and signal generation

### J54. Sensor Fusion and Live Building State

322. **Live Building State**
     - normalized current operating state from meters, telemetry, probes, or sensors
323. **System Live State**
     - per-system health and drift for HVAC, water, safety, envelope, or utilities
324. **Anomaly Signal**
     - first-class anomalies that can trigger incident, maintenance, contradiction, or readiness review
325. **Telemetry Ingest Contract**
     - bounded ingestion profile so SwissBuilding can absorb live signals without turning into a generic BMS
326. **Live Readiness Impact**
     - explicit way for live signals to degrade trust, readiness, or dossier confidence

### J55. Counterfactual Stress and Shock Planning

327. **Stress Scenario**
     - explicit scenario for regulation, finance, insurer, contractor, climate, or proof shocks
328. **Counterfactual Run**
     - stored execution of a what-if scenario at building or portfolio scope
329. **Shock Impact Graph**
     - shows which packs, states, actions, or costs break first under stress
330. **Resilience Ranking**
     - compare buildings or portfolios by robustness under shock, not only current readiness
331. **What-Changed-If Surface**
     - human-readable explanation of what becomes blocked, stale, or urgent under a given scenario

### J56. Expert Disagreement and Override Governance

332. **Expert Disagreement Record**
     - capture where an expert disputes system output or another expert conclusion
333. **Override Rationale Ledger**
     - preserve who overrode what, why, on what basis, and for how long
334. **Confidence Adjustment Trail**
     - explicit confidence changes with human justification instead of hidden state mutation
335. **Review Queue and Resolution Flow**
     - route disputed truth to QA, peer review, or authority-facing review
336. **Temporary Override Expiry**
     - force re-review of overrides that should not silently become permanent truth

### J57. Offline Field Sync and Resilient Capture

337. **Offline Observation Draft**
     - capture field findings without guaranteed connectivity
338. **Sync Queue State**
     - visible queued / syncing / conflicted / failed / synced status for field truth
339. **Conflict-Aware Merge**
     - preserve changes when server truth moved while field capture was offline
340. **Resilient Photo and Annotation Capture**
     - bounded offline support for the highest-value field evidence
341. **Field Sync Recovery Surface**
     - operator tooling to retry, inspect, and resolve failed syncs

### J58. Full-Chain Integration and Demo Truth

342. **Canonical End-to-End Journey**
     - prove import -> enrich -> diagnose -> remediate -> clear -> dossier on seeded data
343. **Authority Journey Harness**
     - validate a full authority-ready scenario instead of only isolated calculators
344. **Demo Truth Contract**
     - demos must be reproducible and derived from realistic seeded scenarios
345. **Cross-Domain State Assertion**
     - trust, readiness, actions, evidence, and post-works must agree in one flow
346. **Integration Regression Sentinel**
     - catch full-chain drift before another backend primitive gets added

### J59. Remediation Module (validated 2026-03-25, updated v2)

Status: `core_now`

Internal BatiConnect module for regulated competition on pollutant remediation works. Batiscan-verified companies receive RFQs from property managers. No platform recommendation, no payment-influenced ranking. Not a separate product.

**6 Delivery Lots**

347. **Company Verification and Onboarding (REM-1)**
     - verify remediation companies (certifications, SUVA recognition, trade categories, service regions) before they can receive RFQs
348. **Neutral RFQ Lifecycle (REM-2)**
     - property managers create ClientRequests scoped to building + pollutant type + work category; verified companies receive RequestInvitations and submit Quotes; no platform ranking or recommendation
349. **Award, Completion, and Verified Review (REM-3)**
     - formal award with hash-signed AwardConfirmation; post-works CompletionConfirmation with dual sign-off (client + company); verified Review only after confirmed completion
350. **Company Subscription Management (REM-4)**
     - subscription tiers and billing lifecycle; subscription tier does NOT influence visibility or ranking in RFQ results
351. **Module Workspace Surface (REM-5)**
     - company profiles, RFQ submission forms, and remediation navigation integrated into BatiConnect Workspace surface
352. **Post-Works Truth (REM-6)**
     - closed-loop: diagnostic -> dossier -> RFQ -> works -> confirmation -> passport update; every completed remediation feeds back into the building passport and digital twin

**AI Layer**

353. **AI Extraction and Structuring**
     - extract structured data from uploaded diagnostics, quotes, and completion reports
354. **AI Contradiction Detection**
     - flag inconsistencies between diagnostic findings and remediation scope
355. **AI Passport Narrative**
     - generate human-readable building state summaries from structured evidence
356. **AI Readiness Advisor**
     - evaluate whether a building is ready for remediation (regulatory, evidence, procedural)
357. **AI Portfolio Intelligence**
     - aggregate remediation patterns across buildings for timing and budget decisions
358. **AI Quote Comparison**
     - surface objective differences across received quotes (cost, scope, timeline) without ranking
359. **AI Progressive Learning**
     - extraction and validation models improve with each completed remediation cycle; compounding data advantage over time

**Data Flywheel (structural)**

The remediation module creates a compounding data advantage:
- every completed cycle improves extraction accuracy, contradiction detection, and cost benchmarks
- building passports become richer with each intervention, increasing platform value for subsequent workflows
- the flywheel is the primary long-term moat: the more the platform is used, the better it becomes

**Dependencies**

- existing auth and RBAC (Organization backbone)
- Document Intake (diagnostic publications as RFQ context)
- audit trail infrastructure
- diagnostic publications (BatiConnect evidence layer)

**Unlocks**

- company subscriptions (new revenue stream)
- verified network effects (more companies attract more clients and vice versa)
- remediation evidence chain (post-works truth feeds back into building dossier)
- closed-loop diagnostic-to-remediation flow
- replicable pattern for other professional verticals

**Replicable Pattern**

The remediation module establishes a vertical pattern replicable to:
- architectes reno (architectural renovation mandates)
- bureaux d'etudes environnementaux (environmental assessment workflows)
- controleurs qualite (inspection, non-conformity, corrective action loops)

Each vertical reuses the same trust model, closed-loop evidence chain, and progressive AI layer.

**6 Invariants**

1. No recommendation: platform never ranks or recommends companies to clients
2. Payment != ranking: subscription tier does not influence visibility in RFQ results
3. Verified contracts only: awards and reviews require completed verification chain
4. No shared database between BatiConnect and external systems
5. BatiConnect is an evidence/readiness layer, not a diagnostic tool itself
6. AI assists with data quality and decision clarity, never with company selection

## K. Saturation and Triage Workflow

This file is meant to grow until new additions become mostly variants or duplicates.

When that happens:
- merge variants into the strongest canonical concept
- keep synonyms or related phrasings inside the canonical entry if useful
- do not silently delete ideas unless they are clearly weaker duplicates

Recommended idea states:
- `frontier`
- `candidate`
- `merged`
- `subsumed`
- `parked`
- `rejected`

Operational rule:
- if a new idea is only a narrower expression of an existing engine, merge it there
- if it introduces a genuinely new use case, engine, or moat, keep it as its own entry
- once a family becomes saturated with duplicates, move the effort to prioritization and sequencing rather than continued enumeration
