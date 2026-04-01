# BatiConnect — Roadmap 48 Mois (2026-2030)

> Version: 2026-04-01
> Auteur: Robin Fragniere + Claude
> Statut: Draft strategique — a valider par increment

Ce document est le plan de route complet de BatiConnect sur 48 mois.
Il s'articule autour de **4 gates de maturite** (pas des phases calendaires — on avance par preuve, pas par date).
Chaque gate debloque la suivante. Pas de saut.

---

## Architecture du plan

```
Gate 1: Wedge Dominance          [M0-M12]   ← ON EST ICI
Gate 2: Building Operating System [M6-M18]
Gate 3: Portfolio & Capital       [M12-M30]
Gate 4: Infrastructure & Standard [M24-M48]

Cross-cutting (permanent):
  - AI Layer (Phase 1→2→3)
  - Platform & DevOps
  - Mobile & Field
  - Ecosystem & Partners
  - International (CH→DACH→EU)
```

Les gates se chevauchent intentionnellement — Gate 2 commence avant que Gate 1 soit 100% fermee.

---

## GATE 1 — WEDGE DOMINANCE (M0-M12)

**Mission:** Prouver que BatiConnect est indispensable pour le dossier pre-travaux polluants en VD/GE.

**Critere de passage:** 3 clients pilotes actifs, completude ≥95%, rework ≤50%, pack autorite <2h, provenance 100%.

### Q1 (M0-M3) — Pilot-Ready [CURRENT]

| # | Deliverable | Status | Detail |
|---|-------------|--------|--------|
| 1.1 | Safe-to-start dossier complet | DONE | G1+G2+M1, 4 wedges fermes |
| 1.2 | Building Life OS wired | DONE | 10 layers + 4 GED + calendar |
| 1.3 | E2E real avec seed complete | TODO | 4 wedges, real backend, all packs |
| 1.4 | Pilot scorecard operationnel | DONE | G2 ready_count wire |
| 1.5 | Fix infra VPS | DONE | localhost→VPS partout |
| 1.6 | Onboarding wizard fonctionnel | PARTIAL | Wizard existe, flow a hardener |
| 1.7 | Demo path pour prospect | PARTIAL | demo_path_service existe |
| 1.8 | Authority pack PDF generation | DONE | Gotenberg wire |
| 1.9 | Shared link avec hash SHA-256 | DONE | contractor_acknowledgment |
| 1.10 | Real e2e preflight stabilise | TODO | preflight.mjs dirty |

### Q2 (M3-M6) — First Pilots

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 2.1 | **Pilot #1 onboarde** (gerance VD) | P0 | Premier client reel avec buildings reels |
| 2.2 | Import diagnostics reels (PDF→extraction) | P0 | ai_extraction + document_classifier en prod |
| 2.3 | OCR pipeline hardened | P0 | OCRmyPDF + ClamAV fiable a 99%+ |
| 2.4 | Completeness engine calibre sur cas reels | P0 | 16 checks valides sur dossiers reels |
| 2.5 | Feedback loop v1 | P1 | User corrections → ai_feedback table |
| 2.6 | Authority pack valide par autorite reelle | P1 | Pack soumis et accepte par autorite VD |
| 2.7 | Quote extraction en prod | P1 | Devis reels parses automatiquement |
| 2.8 | Meilisearch indexing complet | P1 | 3 index (buildings, diagnostics, documents) |
| 2.9 | GlitchTip error tracking | P2 | Monitoring erreurs prod |
| 2.10 | Notification digest v1 | P2 | Email recap hebdo |
| 2.11 | Multi-org dashboard | P2 | Vue cross-orgs pour Robin/support |
| 2.12 | **Pilot #2 onboarde** (gerance GE) | P1 | Deuxieme canton valide |

### Q3 (M6-M9) — Wedge Proof

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 3.1 | **Pilot #3 active** | P0 | 3eme client, validation du pattern |
| 3.2 | Completude ≥95% mesuree sur 20+ buildings | P0 | Metrique reelle, pas seed |
| 3.3 | Rework reduction mesuree ≤50% | P0 | Avant/apres mesure |
| 3.4 | Pack autorite <2h mesure | P0 | Time-to-pack chronometre |
| 3.5 | Rules pack VD v2 (GAD, AvT/ApT complet) | P1 | Couverture reglementaire profonde |
| 3.6 | Rules pack GE v1 | P1 | Adaptation Geneva |
| 3.7 | Post-works truth v1 en prod | P1 | Avant/apres travaux trace |
| 3.8 | Building passport v1 (A-F grade) en prod | P1 | Passport visible sur chaque building |
| 3.9 | Trust score visible en prod | P1 | Indicateur confiance dossier |
| 3.10 | Unknown issues visible en prod | P1 | Lacunes explicites |
| 3.11 | Contradiction detection visible | P2 | Incoherences signalees |
| 3.12 | Field observation v1 (mobile-friendly) | P2 | Saisie terrain basique |
| 3.13 | Pattern learning v1 actif | P2 | Cross-building learning demarre |
| 3.14 | Customer success dashboard | P2 | Suivi adoption/satisfaction |

### Q4 (M9-M12) — Wedge Lock

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 4.1 | **5-10 clients actifs** | P0 | Traction commerciale prouvee |
| 4.2 | Pricing valide | P0 | Modele SaaS per-building ou per-org |
| 4.3 | Remediation module v1 live | P1 | Mise en concurrence encadree, premiere utilisation |
| 4.4 | RFQ marketplace v1 (contractors) | P1 | Demande de devis structuree |
| 4.5 | Contractor acknowledgment en prod | P1 | Workflow acquittement |
| 4.6 | Subsidy tracking v1 | P1 | Subventions Programme Batiments |
| 4.7 | Eco clauses integrees | DONE | Templates eco-clauses |
| 4.8 | Safe-to-sell readiness v1 | P2 | Transaction readiness basique |
| 4.9 | Safe-to-insure readiness v1 | P2 | Insurance readiness basique |
| 4.10 | Regulatory watch v1 | P2 | Veille reglementaire automatisee |
| 4.11 | Benchmark inter-buildings | P2 | Comparaison entre immeubles |
| 4.12 | AI Phase 1→2 transition starts | P2 | Premieres regles codifiees |

**Gate 1 PASS criteria:**
- [ ] 5+ clients actifs avec buildings reels
- [ ] Completude ≥95% mesuree
- [ ] Rework ≤50% mesure
- [ ] Pack autorite <2h mesure
- [ ] Provenance 100%
- [ ] Revenue recurrent demarre

---

## PROGRAMME INDEX — 61 Strategic Programmes

Cross-reference of all strategic programme files (`docs/projects/*-program.md`) mapped to roadmap gates.

### Gate 1 — Wedge Dominance (M0-M12)

| Programme File | Gate | Roadmap Programme | Domain |
|---------------|------|-------------------|--------|
| trust-readiness-postworks-program.md | G1 | A, I | Evidence, readiness & post-works truth |
| ecobau-inspired-readiness-and-eco-specs-program.md | G1 | A, N | Safe-to-start wedge & eco specs |
| killer-demo-and-wow-surfaces-program.md | G1 | K | Demo surfaces & wow factor |
| demo-and-sales-enablement-program.md | G1 | K | Sales enablement & demo flow |
| full-chain-integration-and-demo-truth-program.md | G1 | K, L | End-to-end integration & demo truth |
| dataset-scenario-factory-and-seed-strategy-program.md | G1 | L | Seed data & demo scenarios |
| spatial-truth-and-field-operations-program.md | G1 | G, A | Spatial proof & field operations |
| occupant-safety-and-communication-program.md | G1 | D, N | Occupant safety & communication |
| autonomous-dossier-completion-and-verification-program.md | G1 | I, M | Agentic dossier completion |
| execution-quality-and-hazardous-works-operations-program.md | G1 | N | Hazardous works quality control |
| legal-grade-proof-and-chain-of-custody-program.md | G1 | I, AD | Legal-grade proof & chain of custody |
| weak-signal-watchtower-program.md | G1 | I, N | Weak signal detection & drift prevention |

### Gate 2 — Building Operating System (M6-M18)

| Programme File | Gate | Roadmap Programme | Domain |
|---------------|------|-------------------|--------|
| contradiction-passport-and-transfer-program.md | G2 | I, AD | Contradiction detection, passport & transfer |
| building-passport-standard-and-exchange-program.md | G2 | AD | Passport standard & exchange format |
| decision-replay-and-operator-memory-program.md | G2 | I, AC | Decision replay & building memory |
| expert-review-disagreement-and-override-governance-program.md | G2 | I | Expert review & override governance |
| constraint-graph-and-dependency-intelligence-program.md | G2 | I | Constraint graph & dependency reasoning |
| cross-modal-change-detection-and-reconstruction-program.md | G2 | I, X | Cross-modal change detection |
| multimodal-building-understanding-and-grounded-query-program.md | G2 | I, L | Multimodal extraction & grounded query |
| energy-carbon-and-live-performance-program.md | G2 | B, E | Energy, carbon & live performance |
| lease-tenancy-and-occupancy-economics-program.md | G2 | — | Lease, tenancy & occupancy economics |
| warranty-defects-and-service-obligations-program.md | G2 | D | Warranty, defects & service obligations |
| incident-emergency-and-continuity-program.md | G2 | D | Incident, emergency & continuity |
| utilities-and-recurring-services-program.md | G2 | — | Utilities & recurring services |
| permit-procedure-and-public-funding-program.md | G2 | F, H | Permits, procedures & public funding |
| tax-incentive-and-fiscal-readiness-program.md | G2 | F | Tax, incentives & fiscal readiness |
| coownership-governance-and-resident-operations-program.md | G2 | — | Co-ownership & resident operations |
| semantic-building-operations-and-systems-program.md | G2 | C, J | Building systems & equipment semantics |
| climate-resilience-and-environmental-context-program.md | G2 | B, S | Climate resilience & environmental context |
| sensor-fusion-and-live-building-state-program.md | G2 | J | Sensor fusion & live building state |
| agent-governance-and-knowledge-workbench-program.md | G2 | I | Agent governance & knowledge workbench |
| bim-3d-and-geometry-native-intelligence-program.md | G2 | G, X | BIM, 3D & geometry-native intelligence |
| circularity-and-material-afterlife-program.md | G2 | C | Circularity & material afterlife |
| offline-field-sync-and-resilient-capture-program.md | G2 | G | Offline field sync & resilient capture |

### Gate 3 — Portfolio & Capital (M12-M30)

| Programme File | Gate | Roadmap Programme | Domain |
|---------------|------|-------------------|--------|
| portfolio-execution-and-packs-program.md | G3 | I, M | Portfolio execution & authority packs |
| portfolio-intelligence-command-center-program.md | G3 | I | Portfolio intelligence command center |
| transaction-insurance-finance-readiness-program.md | G3 | AA, F, R | Transaction, insurance & finance readiness |
| benchmarking-learning-and-market-intelligence-program.md | G3 | I, R | Benchmarking & market intelligence |
| counterfactual-stress-testing-and-shock-planning-program.md | G3 | I | Stress testing & scenario planning |
| training-certification-and-operating-enablement-program.md | G3 | — | Training, certification & enablement |
| procurement-vendor-and-sla-program.md | G3 | — | Procurement, vendor & SLA management |
| partner-network-and-contributor-reputation-program.md | G3 | — | Partner network & contributor reputation |

### Gate 4 — Infrastructure & Standard (M24-M48)

| Programme File | Gate | Roadmap Programme | Domain |
|---------------|------|-------------------|--------|
| rules-pack-studio-and-europe-expansion-program.md | G4 | N | Rules pack studio & Europe expansion |
| ecosystem-network-and-market-infrastructure-program.md | G4 | — | Ecosystem network & market infrastructure |
| openbim-digital-logbook-and-passport-convergence-program.md | G4 | AD | openBIM & digital logbook convergence |
| distribution-and-embedded-channels-program.md | G4 | — | Distribution & embedded channels |
| enterprise-identity-and-tenant-governance-program.md | G4 | — | Enterprise identity & tenant governance |
| territory-public-systems-and-utility-coordination-program.md | G4 | — | Territory & public systems coordination |
| market-reference-schema-and-meta-os-governance-program.md | G4 | AD | Market reference schema & meta-OS governance |
| privacy-security-and-data-governance-program.md | G4 | — | Privacy, security & data governance |

### Cross-Cutting (M0-M48)

| Programme File | Gate | Roadmap Programme | Domain |
|---------------|------|-------------------|--------|
| reliability-observability-and-recovery-program.md | Cross | Platform & DevOps | Reliability, observability & recovery |
| continuous-review-and-modernization-program.md | Cross | Platform & DevOps | Continuous review & modernization |
| frontend-async-state-standardization-program.md | Cross | Platform & DevOps | Frontend async state standardization |
| frontend-performance-and-bundle-hardening-program.md | Cross | Platform & DevOps | Frontend performance & bundle hardening |
| domain-facades-and-service-consolidation-program.md | Cross | Platform & DevOps | Domain facades & service consolidation |
| service-consumer-mapping-and-dead-code-pruning-program.md | Cross | Platform & DevOps | Service mapping & dead-code pruning |
| test-right-sizing-and-integration-confidence-program.md | Cross | Platform & DevOps | Test right-sizing & integration confidence |
| read-models-query-topology-and-aggregate-apis-program.md | Cross | Platform & DevOps | Read models & aggregate APIs |
| api-contracts-and-generated-clients-program.md | Cross | Platform & DevOps | API contracts & generated clients |
| async-jobs-projections-and-background-orchestration-program.md | Cross | Platform & DevOps | Async jobs & background orchestration |
| baticonnect-product-blueprint-program.md | Cross | — | Product blueprint & canonical architecture |

**Total: 61 programmes | G1: 12 | G2: 22 | G3: 8 | G4: 8 | Cross-cutting: 11**

---

## PROGRAMMES ACCELERES M0-M12 — CAPACITE DEV MASSIVE

> Ces programmes s'executent en parallele des Q1-Q4 Gate 1.
> Chaque programme est independant et peut etre assigne a un agent ou une equipe.
> L'objectif: quand le premier client arrive, la profondeur du produit est deja impressionnante.

---

### PROGRAMME A — ENRICHISSEMENT GEOSPATIAL COMPLET (M0-M6)

**Constat:** 24 fetchers geo.admin existent dans `enrichment/geo_admin_fetchers.py`, seulement ~6 sont actifs dans le pipeline. Les donnees sont la, il suffit de les brancher.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| A.1 | **Activer les 24 layers geo.admin** | geo.admin REST API | S | ★★★★★ | Brancher tous les fetchers existants dans l'orchestrator d'enrichissement |
| A.2 | **swissBUILDINGS3D complet** | ch.swisstopo.swissbuildings3d | M | ★★★★ | Persister footprint WKT, hauteur, type de toit, volume, nb etages (deja parse, pas persiste) |
| A.3 | **Carte bruit (sonBASE)** | ch.bafu.laerm-strassenlaerm | S | ★★★ | Exposition bruit routier/ferroviaire/aerien → impact sante/confort locataires |
| A.4 | **Potentiel solaire toitures** | ch.bfe.solarenergie-eignung-daecher | S | ★★★★ | kWh/an potentiel par batiment → opportunite renovation energetique |
| A.5 | **Sites contamines (OPCS)** | ch.bafu.altlasten-kataster | S | ★★★★★ | Cadastre sites pollues → risque environnemental direct |
| A.6 | **Zones protection eaux souterraines** | ch.bafu.grundwasserschutzzonen | S | ★★★ | Contraintes evacuation dechets polluants |
| A.7 | **Zones danger inondation** | ch.bafu.gefahrenkarte-hochwasser | S | ★★★★ | Risque inondation → assurance, readiness |
| A.8 | **Zone sismique** | ch.bafu.erdbeben-baugrundklassen | S | ★★★ | Classe sismique → contraintes structurelles |
| A.9 | **Inventaire ISOS (patrimoine)** | ch.bak.bundesinventar-schuetzenswerte-ortsbilder | S | ★★★★ | Protection patrimoine → contraintes renovation lourdes |
| A.10 | **Monuments proteges** | ch.bak.bundesinventar-schuetzenswerte-denkmaeler | S | ★★★ | Classement monument → interdiction demolition/modification |
| A.11 | **Zones agricoles** | ch.blw.landwirtschaftliche-zonengrenzen | S | ★★ | Contraintes zone agricole |
| A.12 | **Reserves forestieres** | ch.bafu.waldreservate | S | ★★ | Contraintes forestieres |
| A.13 | **Reseaux thermiques** | ch.bfe.fernwaermenetze | S | ★★★ | Raccordement possible → opportunite energetique |
| A.14 | **Danger avalanches/glissements** | ch.bafu.gefahrenkarte-massenbewegungen | S | ★★★ | Risques naturels gravitaires |
| A.15 | **GeoContextPanel enrichi** | Frontend | M | ★★★★★ | Afficher les 24 layers dans le panel avec indicateurs visuels |
| A.16 | **Geo Risk Score composite** | Nouveau service | M | ★★★★★ | Score risque geospatial composite (bruit + inondation + sismique + contamination + patrimoine) |
| A.17 | **Carte interactive multi-layers** | Mapbox GL | L | ★★★★★ | Carte avec toggle par layer, clusters, heatmap par risque |
| A.18 | **Enrichissement auto a la creation** | Pipeline | S | ★★★★ | Chaque building cree declenche enrichissement 24 layers automatiquement |
| A.19 | **Refresh periodique geo-data** | Cron job | S | ★★★ | Re-fetch mensuel pour detecter changements (nouvelle zone danger, etc.) |
| A.20 | **Alerte changement geospatial** | Change signal | M | ★★★★ | "Votre batiment est maintenant en zone inondation" → alerte proactive |

**Resultat:** Chaque batiment a un profil geospatial complet avec 24 dimensions, score de risque composite, et alertes proactives.

---

### PROGRAMME B — PROFIL CLIMATIQUE & ENVIRONNEMENTAL (M0-M6)

**Constat:** Le modele `ClimateExposureProfile` existe avec 10 champs, tous vides. Le modele `OpportunityWindow` existe avec 10 types, aucun service de detection.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| B.1 | **Peupler ClimateExposureProfile** | MeteoSwiss + geo.admin | M | ★★★★ | heating_degree_days, freeze_thaw_cycles, moisture/thermal/uv_stress |
| B.2 | **Profil exposition radon reel** | ch.bag.radonkarte (deja fetcher) | S | ★★★★★ | Remplacer heuristique canton par donnee reelle geo.admin |
| B.3 | **Stress materiau predictif** | Climate + age + type construction | M | ★★★★★ | "Ce batiment de 1965 en zone gel frequent a un risque accelere de degradation amiante" |
| B.4 | **Fenetres d'opportunite** | OpportunityWindow model | L | ★★★★★ | Detection auto: fenetre meteo (ete=desamiantage), fenetre subvention (deadline), fenetre bail (fin bail=travaux), fenetre permis (permis expire bientot) |
| B.5 | **Dashboard opportunities** | Frontend | M | ★★★★ | "3 fenetres d'opportunite ouvertes pour ce batiment" dans Building Home |
| B.6 | **Alerte fenetre fermante** | Notification | S | ★★★★ | "La subvention Programme Batiments ferme dans 45 jours" |
| B.7 | **Saisonnalite travaux** | Meteo historique | M | ★★★ | "Meilleure periode pour travaux exterieurs: mai-septembre" basee sur meteo locale |
| B.8 | **Impact climatique sur delais** | Compliance calendar | S | ★★★ | Ajuster les delais reglementaires selon saison/meteo |
| B.9 | **Score durabilite batiment** | Composite | M | ★★★★ | Score A-F durabilite (energie + polluants + climat + materiaux) |
| B.10 | **Projection changement climatique** | Scenarios CH2018 | L | ★★★ | "En 2040, ce batiment sera en zone canicule frequente" |

**Resultat:** Chaque batiment a un profil climatique vivant, des fenetres d'opportunite detectees automatiquement, et des alertes proactives.

---

### PROGRAMME C — INTELLIGENCE MATERIAU & INVENTAIRE (M3-M9)

**Constat:** Les modeles `Material`, `InventoryItem` (14 types), `FieldObservation` existent avec des schemas riches mais aucun service d'agregation ni d'intelligence.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| C.1 | **Inventaire equipements complet** | InventoryItem model | M | ★★★★ | CRUD complet pour 14 types: HVAC, chaudiere, ascenseur, panneaux solaires, etc. |
| C.2 | **Timeline remplacement equipements** | warranty_end_date + condition | M | ★★★★★ | "La chaudiere a 18 ans, garantie expiree, remplacement dans 2 ans" |
| C.3 | **Cout remplacement agrege** | replacement_cost × items | S | ★★★★ | Budget previsionnel remplacement equipements sur 5-10 ans |
| C.4 | **Passeport materiau** | Material model enrichi | M | ★★★★ | Chaque materiau: type, age, polluant, degradation, source, confiance |
| C.5 | **Matrice materiaux × polluants** | Croisement materiaux/diagnostics | M | ★★★★★ | "Dalles vinyle 1972 → probabilite amiante 85%" — prediction par type+age |
| C.6 | **Reconnaissance materiau photo** | LLM vision (Claude) | L | ★★★★★ | Upload photo → identification materiau + estimation age + alerte polluant |
| C.7 | **Degradation materiau predictive** | Age + climat + usage | M | ★★★★ | "Ce joint d'etancheite PCB de 1978 est en phase de desagregation" |
| C.8 | **Field observation collective** | FieldObservation aggregation | M | ★★★★ | Observations terrain agregees par confiance, verification, zone |
| C.9 | **Material DNA / Genome** | Cross-building material patterns | L | ★★★★ | "Les batiments 1960-1975 en beton dans cette zone ont 73% de probabilite amiante dans les colles" |
| C.10 | **Contradiction materiau/diagnostic** | Cross-reference | M | ★★★★★ | "L'observation terrain dit amiante, le diagnostic dit negatif — contradiction flaggee" |
| C.11 | **Catalogue materiaux suisses** | Donnees historiques construction | L | ★★★ | Base de reference materiaux par epoque de construction suisse |
| C.12 | **Scan etiquette/plaque equipement** | OCR mobile | M | ★★★ | Scanner plaque chaudiere → extraction modele/annee/fabricant auto |

**Resultat:** Chaque batiment a un inventaire vivant d'equipements et materiaux, avec predictions de remplacement, alertes polluants, et intelligence croisee.

---

### PROGRAMME D — INCIDENTS, DOMMAGES & MEMOIRE SINISTRES (M3-M9)

**Constat:** `IncidentEpisode` (12 types), `DamageObservation` (10 types de dommage, progression tracking) — modeles riches, zero intelligence.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| D.1 | **Workflow incident complet** | IncidentEpisode CRUD | M | ★★★★ | Signalement → evaluation → action → resolution → fermeture |
| D.2 | **Detection patterns recurrents** | Analyse incidents | M | ★★★★★ | "3eme fuite au 2eme etage en 18 mois — probleme structurel probable" |
| D.3 | **Score building sinistralite** | Historique incidents | S | ★★★★ | Score 0-100 sinistralite → impact assurance |
| D.4 | **Trending dommages visuels** | DamageObservation progression | M | ★★★★ | Fissure "stable" → "lente" → "rapide" avec timeline visuelle |
| D.5 | **Correlation incident/intervention** | Cross-reference | M | ★★★★★ | "Apres travaux toiture 2024, plus aucune infiltration — intervention efficace prouvee" |
| D.6 | **Photo avant/apres dommage** | Upload + comparaison | M | ★★★★ | Comparaison visuelle evolution dommage |
| D.7 | **Alerte incident previsible** | Pattern + climat + age | M | ★★★★★ | "Risque fuite toiture eleve — batiment 1970, toiture non renovee, forte pluie prevue" |
| D.8 | **Export sinistralite assureur** | Pack export | S | ★★★★ | Historique incidents structure pour assureur |
| D.9 | **Impact occupants** | Incident → unites touchees | S | ★★★ | "Incident a impacte 4 unites, 12 occupants" |
| D.10 | **Lien incident → obligation** | Cross-reference | S | ★★★★ | Incident genere automatiquement une obligation (reparation, controle, etc.) |

**Resultat:** Memoire complete des sinistres, detection de patterns, predictions, et pack export assureur.

---

### PROGRAMME E — ENERGIE, CERTIFICATION & PERFORMANCE (M3-M9)

**Constat:** `EnergyPerformanceService` estime a partir de l'annee de construction seulement. `BuildingCertificationService` a des checks hardcodes sans lookup registre. CECB/GEAK/Minergie non integres.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| E.1 | **Import CECB/GEAK reel** | Registres cantonaux CECB | L | ★★★★★ | Lookup certificat energetique reel par EGID |
| E.2 | **Label Minergie/SNBS lookup** | minergie.ch API | M | ★★★ | Verification label reel |
| E.3 | **Performance energetique reelle** | CECB + consommation | M | ★★★★ | Classe A-G basee sur donnees reelles, pas estimation |
| E.4 | **Trajectoire energetique** | Historique + projection | M | ★★★★ | "Ce batiment consomme 180 kWh/m2 → cible 2030: 90 kWh/m2 → ecart: 50%" |
| E.5 | **Potentiel solaire personalise** | geo.admin solar + toiture 3D | M | ★★★★ | "Toiture 45m2, orientation sud, potentiel: 8'200 kWh/an, ROI: 7 ans" |
| E.6 | **Simulation renovation energetique** | Cout + gain + subvention | L | ★★★★★ | "Isolation facade: -35% consommation, cout 120k, subvention 40k, ROI 12 ans" |
| E.7 | **Score carbone batiment** | Materiaux + energie + transport | M | ★★★★ | Empreinte carbone estimee du batiment |
| E.8 | **Etiquette energie dans passport** | Integration passport | S | ★★★★ | Classe energetique visible dans le passport batiment |
| E.9 | **Alerte obligation energetique** | OFEN / regles cantonales | M | ★★★★★ | "Obligation remplacement chaudiere mazout avant 2030 (loi GE)" |
| E.10 | **Comparaison energetique parc** | Benchmark portfolio | M | ★★★ | "Ce batiment consomme 40% de plus que la moyenne du parc" |

**Resultat:** Chaque batiment a un profil energetique reel, une trajectoire, des simulations de renovation, et des alertes obligations.

---

### PROGRAMME F — FISCALITE, SUBVENTIONS & FINANCEMENT (M3-M9)

**Constat:** `TaxContext` (modele), `FinancialEntry` (21 categories), `subsidy_source_service` (hardcode) — infrastructure la mais pas valorisee.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| F.1 | **Contexte fiscal par batiment** | TaxContext API complete | M | ★★★★ | Valeur officielle, valeur fiscale, impot foncier, deductions |
| F.2 | **Deductions fiscales renovation** | Regles cantonales | M | ★★★★★ | "Travaux desamiantage: deductible a 100% (VD), plafond 50k" |
| F.3 | **Simulateur fiscal renovation** | Cout travaux → economie impot | M | ★★★★★ | "Renovation 200k → deduction fiscale 60k → cout net 140k" |
| F.4 | **Subventions dynamiques** | APIs cantonales | L | ★★★★★ | Remplacer hardcode par lookup temps reel Programme Batiments + cantonaux |
| F.5 | **Eligibilite subvention auto** | Croisement batiment/programme | M | ★★★★★ | "Ce batiment est eligible a 3 programmes: isolation (max 40k), chauffage (max 20k), vitrage (max 8k)" |
| F.6 | **Calendrier subventions** | Deadlines programmes | S | ★★★★ | "Date limite Programme Batiments VD: 31.12.2026" dans Building Life calendar |
| F.7 | **Cash flow previsionnel** | FinancialEntry aggregation | M | ★★★★ | Projection tresorerie 12/24/60 mois par batiment |
| F.8 | **ROI renovation complet** | Cout - subvention - deduction + economie energie | M | ★★★★★ | "Renovation complete: cout brut 350k, subventions 80k, deductions 90k, economie energie 8k/an → ROI net 10 ans" |
| F.9 | **Export comptable** | Format standard | M | ★★★ | Export charges/travaux au format comptable (Abacus, etc.) |
| F.10 | **Scoring bancaire batiment** | Composite readiness | M | ★★★★ | Score pret hypothecaire basé sur etat, risques, energie, documentation |

**Resultat:** Chaque batiment a un profil financier complet avec simulations fiscales, eligibilite subventions, et ROI renovation.

---

### PROGRAMME G — PLANS TECHNIQUES & VISUALISATION SPATIALE (M3-M9)

**Constat:** `TechnicalPlan` (8 types), `PlanAnnotation` (6 types avec x,y,couleur), `plan_heatmap_service` — infrastructure prete, pas de viewer interactif.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| G.1 | **Viewer plans interactif** | Frontend (OpenLayers/Leaflet) | L | ★★★★★ | Zoom, pan, annotations clickables sur plans techniques |
| G.2 | **Overlay zones polluants sur plan** | Diagnostics + zones | M | ★★★★★ | "Zone rouge = amiante confirmee, zone orange = suspectee, zone verte = testee negative" |
| G.3 | **Overlay prelevements sur plan** | Samples + x,y | M | ★★★★ | Points de prelevement geolocalises sur le plan avec resultats |
| G.4 | **Heatmap confiance sur plan** | Trust scores par zone | M | ★★★★★ | "Zones bien documentees en bleu, zones avec lacunes en rouge" — killer demo |
| G.5 | **Annotations collaboratives** | Multi-user annotations | M | ★★★ | Diagnosticien, gestionnaire, entreprise annotent le meme plan |
| G.6 | **Extraction auto zones depuis plan** | LLM vision | L | ★★★★ | Upload plan PDF → detection auto des pieces/zones → creation zones |
| G.7 | **Photo terrain → position sur plan** | Geotagging + mapping | L | ★★★★ | Photo terrain placee automatiquement sur le plan |
| G.8 | **Vue 3D batiment** | swissBUILDINGS3D + Deck.gl | XL | ★★★★★ | Vue 3D du batiment avec overlays (polluants, interventions, etc.) |
| G.9 | **Comparaison plans avant/apres** | Diff visuel | M | ★★★ | Superposition plans avant et apres travaux |
| G.10 | **Export plan annote PDF** | Gotenberg | S | ★★★★ | Plan avec toutes annotations → PDF pour autorite |

**Resultat:** Plans techniques interactifs avec overlays polluants, confiance, prelevements — surface de demo killer.

---

### PROGRAMME H — REGISTRES PUBLICS & DONNEES LEGALES (M3-M9)

**Constat:** Registre foncier, permis de construire, protection du patrimoine — donnees legales critiques non integrees.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| H.1 | **EGRID → Registre foncier** | ch.swisstopo.cadastre / RDPPF | L | ★★★★★ | Restrictions de droit public: servitudes, charges, droits de preemption |
| H.2 | **Cadastre RDPPF complet** | Geoservices cantonaux | L | ★★★★★ | Restrictions: zones constructibles, alignements, distances, affectation |
| H.3 | **Historique permis de construire** | Portails cantonaux | L | ★★★★ | Tous les permis emis pour le batiment → timeline juridique |
| H.4 | **Zone d'affectation** | Plans GA cantonaux | M | ★★★★ | Zone habitation, mixte, industrielle → contraintes specifiques |
| H.5 | **Proprietaire actuel** | Registre foncier | M | ★★★ | Proprietaire officiel (si accessible) |
| H.6 | **Hypotheques et gages** | Registre foncier | M | ★★★ | Situation hypothecaire (si accessible) |
| H.7 | **Classement ISOS detail** | Inventaire federal | M | ★★★★ | Categorie, objectifs de sauvegarde, perimetres |
| H.8 | **Recensement architectural** | Cantonal heritage | M | ★★★★ | Note architecturale, valeur patrimoniale |
| H.9 | **Plans d'amenagement locaux** | Communes | L | ★★★ | Reglement communal applicable |
| H.10 | **Registre des batiments (RegBL) enrichi** | GWR/BFS complet | M | ★★★★★ | Tous les champs RegBL: chauffage, renovation, nb logements, surface, epoque |

**Resultat:** Contexte juridique et administratif complet par batiment — critique pour transaction readiness et due diligence.

---

### PROGRAMME I — INTELLIGENCE CROISEE & PREDICTIONS (M6-M12)

**Constat:** 292 services, 162 modeles — enorme potentiel de croisement non exploite.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| I.1 | **Correlation age × polluant × type** | Cross-analysis | M | ★★★★★ | "Batiments 1960-1975, beton, Lausanne: 78% amiante dans colles de carrelage" |
| I.2 | **Prediction risque par similarite** | Cross-building patterns | L | ★★★★★ | "Batiment similaire a 47 batiments diagnostiques → risque predit: high amiante, medium PCB" |
| I.3 | **Score confiance croise** | Multi-source trust | M | ★★★★ | Trust score = f(diagnostic, terrain, registre, voisinage, anciennete donnee) |
| I.4 | **Detection lacunes par comparaison** | Cross-building gaps | M | ★★★★★ | "95% des batiments similaires ont un diagnostic radon — le votre non" |
| I.5 | **Enrichissement par voisinage** | Nearby buildings | M | ★★★★ | "Le batiment voisin a de l'amiante dans les joints → votre batiment contemporain aussi probablement" |
| I.6 | **Heatmap risque par quartier** | Aggregation spatiale | M | ★★★★★ | Carte: "Ce quartier a 85% de probabilite amiante" — donnee aggregate anonymisee |
| I.7 | **Alertes anomalies reglementaires** | Compliance + patterns | M | ★★★★★ | "Ce batiment de 1972 n'a aucun diagnostic amiante — anomalie reglementaire probable" |
| I.8 | **Prediction cout remediation** | Historique + surface + type | M | ★★★★ | "Desamiantage predit: 45-65k CHF (basé sur 23 cas similaires)" |
| I.9 | **Score urgence intellignet** | Multi-facteur | M | ★★★★★ | Urgence = f(risque sante, reglementaire, fenetre opportunite, budget, bail) |
| I.10 | **Recommandation proactive** | Nudge engine enrichi | M | ★★★★ | "Recommandation: commander diagnostic radon maintenant (fenetre meteo ideale + subvention ouverte)" |
| I.11 | **Benchmark automatique** | Cross-building scoring | M | ★★★★ | "Votre batiment: B+ (top 30% du parc VD pour la meme epoque)" |
| I.12 | **Weak signals detection** | Change signals + patterns | M | ★★★★ | "Hausse incidents fuites dans batiments similaires → signal faible alerte" |
| I.13 | **Building digital twin score** | Completude modele numerique | S | ★★★ | "Ce batiment a un jumeau numerique complet a 72%" |
| I.14 | **Timeline predictive** | ML projection | L | ★★★★ | "Dans 2 ans: obligation remplacement chaudiere, fin bail 3eme, subvention disponible → fenetre ideale renovation globale" |
| I.15 | **Portfolio heat score** | Aggregation multi-batiment | M | ★★★★★ | Score composite portefeuille: "8 batiments en zone rouge, action requise" |

**Resultat:** Le systeme devient predictif et proactif — il ne se contente pas de documenter, il anticipe et recommande.

---

### PROGRAMME J — SENSEURS & IoT (M6-M12)

**Constat:** `SensorIntegrationService` existe avec 5 types de capteurs, seuils definis, mais donnees synthetiques uniquement.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| J.1 | **Integration capteur radon reel** | API capteurs radon (Airthings, etc.) | M | ★★★★★ | Donnees radon temps reel → alerte si >300 Bq/m3 |
| J.2 | **Integration qualite air interieur** | API capteurs IAQ | M | ★★★★ | CO2, COV, particules, humidite → score qualite air |
| J.3 | **Dashboard capteurs temps reel** | Frontend websocket | L | ★★★★ | Graphiques temps reel des mesures |
| J.4 | **Alerte seuil depassement** | Notification service | S | ★★★★★ | "Alerte: radon >300 Bq/m3 depuis 48h au sous-sol" |
| J.5 | **Historique mesures** | Time series storage | M | ★★★ | Historique mesures avec trends et saisonnalite |
| J.6 | **Correlation capteur/intervention** | Cross-reference | M | ★★★★ | "Apres ventilation installee: radon passe de 450 a 120 Bq/m3 — preuve d'efficacite" |
| J.7 | **Integration compteur energie** | Smart meter APIs | L | ★★★★ | Consommation reelle vs theorique |
| J.8 | **Capteur humidite/temperature** | API capteurs | M | ★★★ | Detection precoce moisissure/condensation |
| J.9 | **QR code capteur → batiment** | Scan + link | S | ★★★ | Scanner QR du capteur → associe au batiment/zone |
| J.10 | **Preuve de mesure certifiee** | Hash + timestamp | M | ★★★★★ | Mesure capteur = preuve opposable (hash, timestamp, calibration) |

**Resultat:** Le batiment devient "connecte" — donnees temps reel, preuves de mesure, alertes proactives.

---

### PROGRAMME K — VISUALISATIONS & DEMO SURFACES (M3-M12)

**Constat:** Les donnees sont la, mais les visualisations ne sont pas a la hauteur de la profondeur du produit.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| K.1 | **Timeline immersive batiment** | Tous evenements | L | ★★★★★ | Timeline scrollable avec photos, documents, interventions, incidents, mesures — "la vie du batiment" |
| K.2 | **Vue satellite/Street View** | Google/Mapbox imagery | M | ★★★★ | Photo satellite + Street View du batiment dans Building Home |
| K.3 | **Carte risque quartier interactive** | Aggregation + Mapbox | L | ★★★★★ | Heatmap interactive: polluants, age, sinistralite par quartier |
| K.4 | **Comparaison batiments cote a cote** | Building comparison enrichi | M | ★★★★ | 2-4 batiments compares sur 20+ dimensions avec graphiques radar |
| K.5 | **Dashboard "Building Intelligence"** | Nouveau panel | L | ★★★★★ | Tab Intelligence: predictions, recommandations, signaux faibles, opportunites |
| K.6 | **Graphe evidence interactif** | D3.js / Cytoscape | L | ★★★★★ | Graphe navigable: chaque score → ses preuves → ses sources |
| K.7 | **Rapport PDF automatique luxe** | Gotenberg + templates | L | ★★★★★ | Rapport complet 20 pages: passport, risques, energie, recommandations, timeline |
| K.8 | **Export passeport batiment** | PDF + JSON | M | ★★★★ | Passeport exportable: tout l'etat du batiment en un fichier |
| K.9 | **Infographie polluants** | SVG/Canvas | M | ★★★★ | Schema batiment avec overlay polluants par zone — comme une coupe architecturale |
| K.10 | **Screen sharing mode** | Frontend mode | S | ★★★ | Mode presentation: masque infos sensibles, agrandit les visuels |
| K.11 | **Before/after intervention slider** | Image comparison | M | ★★★★ | Slider avant/apres sur photos d'intervention |
| K.12 | **Animated building health** | Animation score | M | ★★★★ | Animation du score sante qui evolue avec les interventions — "le batiment guerit" |
| K.13 | **Portfolio map 3D** | Deck.gl / Mapbox 3D | XL | ★★★★★ | Vue 3D du portfolio avec batiments colores par risque/readiness |
| K.14 | **Readiness radar chart** | Recharts | S | ★★★★ | Spider chart: 7 axes safe_to_X pour chaque batiment |
| K.15 | **Mobile building card** | Responsive | M | ★★★★ | Fiche batiment optimisee mobile avec photo, score, alertes — "carte de visite du batiment" |

**Resultat:** Le produit est visuellement impressionnant et demo-ready — chaque ecran raconte une histoire.

---

### PROGRAMME L — CONNECTEURS & IMPORTS DE DONNEES (M0-M12)

**Constat:** Un seul importer actif (Vaud public). Le potentiel d'ingestion est enorme.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| L.1 | **Import RegBL/GWR complet** | BFS API | L | ★★★★★ | Tous les champs RegBL: chauffage, renovation, nb logements, surface, epoque, pour toute la Suisse |
| L.2 | **Import cadastre GE** | SITG Geneve | L | ★★★★ | Donnees genevoises: parcelles, batiments, adresses |
| L.3 | **Import cadastre BE** | Geoportal BE | L | ★★★ | Premier canton germanophone |
| L.4 | **Import MADD (adresses)** | BFS MADD | M | ★★★★ | Registre federal des adresses — reference pour geocodage |
| L.5 | **Import diagnostic PDF auto** | ai_extraction pipeline | L | ★★★★★ | Drop PDF diagnostic → extraction complete automatique |
| L.6 | **Import devis/facture PDF** | quote_extraction pipeline | M | ★★★★ | Drop devis PDF → extraction montants, postes, entreprise |
| L.7 | **Import email inbox** | IMAP/API | L | ★★★ | Boite email → detection auto documents pertinents → import |
| L.8 | **Import SharePoint/OneDrive** | Microsoft Graph API | L | ★★★ | Connecteur dossiers partages Microsoft |
| L.9 | **Import photos terrain batch** | Upload multiple + EXIF | M | ★★★★ | Upload 50 photos → extraction GPS, date, orientation → placement auto |
| L.10 | **Import plan PDF avec OCR** | OCR + LLM vision | L | ★★★★ | Plan PDF → detection pieces, surfaces, annotations |
| L.11 | **Connecteur Rimo (ERP)** | API Rimo | XL | ★★★★★ | Sync bidirectionnel avec ERP immobilier #1 Suisse |
| L.12 | **Import CSV/Excel generique** | Upload + mapping | M | ★★★★ | Import tableaux Excel de buildings, diagnostics, contacts |
| L.13 | **Import opendata.swiss** | CKAN API | M | ★★★ | Datasets ouverts: statistiques batiments, energie, etc. |
| L.14 | **Import swissBUILDINGS3D** | Swisstopo API | L | ★★★★ | Modele 3D batiments pour tout le territoire |
| L.15 | **Webhooks entrants** | API webhook | M | ★★★ | Recevoir donnees push de partenaires |

**Resultat:** Le systeme ingere des donnees de partout — registres, documents, ERP, emails, photos — et les consolide automatiquement.

---

### PROGRAMME M — GENERATION AUTOMATIQUE & RAPPORTS (M6-M12)

**Constat:** Le systeme a des tonnes de donnees mais la generation de documents exploitables est limitee.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| M.1 | **Rapport autorite auto complet** | Gotenberg + toutes donnees | L | ★★★★★ | Rapport 20+ pages genere en 1 clic: diagnostic, risques, recommandations, preuves |
| M.2 | **Rapport proprietaire vulgarise** | LLM + donnees | M | ★★★★★ | Version "humaine" du rapport: pas de jargon, recommandations claires, couts |
| M.3 | **Rapport assureur standardise** | Pack export | M | ★★★★ | Sinistralite + risques + mesures + interventions au format assureur |
| M.4 | **Rapport bancaire (pret hypo)** | Pack export | M | ★★★★ | Etat batiment + risques + valeur + energie au format bancaire |
| M.5 | **Lettre type locataire** | Templates + LLM | M | ★★★★ | "Chers locataires, des travaux de desamiantage auront lieu..." — genere auto |
| M.6 | **Bon de commande diagnostic** | DiagnosticMissionOrder | M | ★★★★ | Bon de commande auto avec perimetre, conditions, prix — pret a envoyer |
| M.7 | **Cahier des charges travaux** | Intervention → spec | L | ★★★★★ | Cahier des charges travaux genere: perimetre, conditions, exigences securite, elimination dechets |
| M.8 | **PV reception travaux** | Post-works template | M | ★★★★ | PV genere: verification points, mesures, conformite, signatures |
| M.9 | **Newsletter batiment mensuelle** | Auto-generation | M | ★★★ | Recap mensuel auto: ce qui a change, ce qui arrive, recommandations |
| M.10 | **Export donnees autorite numerique** | Format structure | M | ★★★★ | Export au format eCH/INTERLIS pour soumission autorite numerique |

**Resultat:** Chaque acteur recoit un document adapte a ses besoins, genere automatiquement — reduction massive du travail administratif.

---

### PROGRAMME N — CONFORMITE PROACTIVE & VEILLE (M6-M12)

**Constat:** `swiss_rules_spine_service` (71k LOC!), `regulatory_watch_service`, `compliance_engine` — infrastructure massive, pas assez proactive.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| N.1 | **Scan conformite automatique** | Toutes regles × batiment | M | ★★★★★ | Scan complet: "Ce batiment a 3 non-conformites, 2 risques reglementaires, 1 obligation a venir" |
| N.2 | **Delais reglementaires calcules** | Rules spine + calendar | M | ★★★★★ | "Delai pour analyse amiante avant travaux: 30 jours (OTConst Art. 82)" |
| N.3 | **Veille reglementaire auto** | RSS + scraping officiel | L | ★★★★ | "Nouvelle modification ORRChim entree en vigueur le 1er avril — impact sur 12 batiments" |
| N.4 | **Diff regles entre cantons** | Cross-canton comparison | M | ★★★★★ | "VD exige diagnostic avant 10m2, GE avant tout travaux — votre batiment est a cheval" |
| N.5 | **Checklist reglementaire dynamique** | Per-building generated | M | ★★★★ | Checklist personnalisee par batiment: "12 points a verifier avant travaux" |
| N.6 | **Alerte nouvelle obligation** | Regulatory watch + match | M | ★★★★★ | "Nouvelle loi GE: obligation audit energetique pour batiments >1000m2 avant 2028 — 3 batiments concernes" |
| N.7 | **Calendrier obligations complet** | Building Life calendar enrichi | M | ★★★★ | Toutes les echeances reglementaires dans le calendrier: diagnostics, controles, renouvellements |
| N.8 | **Score conformite global** | Composite | S | ★★★★ | Score 0-100 conformite par batiment |
| N.9 | **Rapport non-conformite** | Export PDF | M | ★★★★ | Liste structuree des non-conformites avec references legales et recommandations |
| N.10 | **Simulation impact nouvelle regle** | What-if reglementaire | L | ★★★★★ | "Si la limite radon passe a 200 Bq/m3, 15 batiments sont impactes" |

**Resultat:** Le systeme connait les regles mieux que le gestionnaire et alerte proactivement sur chaque risque reglementaire.

---

### PROGRAMME O — CONTEXTE URBAIN & VIE DE QUARTIER (M0-M9)

**Constat:** OSM ramene deja ecoles, hopitaux, restos, parcs (500m). Mais on n'exploite pas: reviews, qualite, densite commerciale, vie nocturne, securite, dynamique du quartier. Le batiment n'existe pas dans le vide — il vit dans un quartier.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| O.1 | **Google Places enrichissement** | Google Places API | M | ★★★★★ | Commerces, restos, services dans 500m avec ratings, photos, horaires, popularite |
| O.2 | **Score vie de quartier** | Composite | M | ★★★★★ | Score 0-10: commerces + restos + services + culture + loisirs = "quartier vivant" |
| O.3 | **Reviews & reputation zone** | Google Reviews aggregate | M | ★★★★ | Rating moyen des commerces du quartier, sentiment analysis, tendances |
| O.4 | **Densite commerciale** | OSM + Google Places | S | ★★★★ | Nombre de commerces/km2, types dominants, diversite |
| O.5 | **Walkability score** | OSM + trottoirs + pentes | M | ★★★★★ | Score marchabilite: trottoirs, passages pietons, pentes, obstacles |
| O.6 | **Bikeability score** | OSM cyclable + Veloland | M | ★★★★ | Pistes cyclables, stations Publibike, topographie |
| O.7 | **Marche hebdomadaire / evenements** | Donnees communales | S | ★★★ | Marches, brocantes, evenements reguliers dans le quartier |
| O.8 | **Indice vie nocturne** | Google Places + horaires | S | ★★★ | Bars, clubs, restos ouverts tard — nuisance potentielle OU avantage |
| O.9 | **Distance commodites cles** | OSM routing | M | ★★★★ | Temps a pied vers: supermarche, ecole, medecin, poste, pharmacie, parc, arret TP |
| O.10 | **Carte isochrone** | Mapbox Isochrone API | M | ★★★★★ | "Tout ce qui est accessible en 5/10/15 min a pied" — visuel killer |
| O.11 | **Evolution quartier** | Historique Google/OSM | L | ★★★★ | Nouveaux commerces, fermetures, tendance gentrification |
| O.12 | **Securite percue** | Statistiques cantonales criminalite | M | ★★★★ | Taux criminalite par commune/quartier — Swiss crime statistics |
| O.13 | **Eclairage public** | OSM street_lamp | S | ★★ | Densite eclairage → securite percue |
| O.14 | **Espaces coworking** | Google Places | S | ★★★ | Distance au coworking le plus proche → attractivite teletravail |
| O.15 | **Points de vente alimentaire** | OSM + Google | S | ★★★ | Boulangeries, boucheries, epiceries fines — granularite au-dela du "supermarche" |

**Resultat:** Le batiment a un profil de quartier complet — attractivite, commodites, securite, dynamique — utile pour transaction, assurance, location.

---

### PROGRAMME P — TRANSPORT & MOBILITE PROFOND (M0-M9)

**Constat:** On a la qualite TP (A-D) et les 5 arrets les plus proches. On peut aller enormement plus loin.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| P.1 | **Horaires CFF/TP temps reel** | transport.opendata.ch | M | ★★★★★ | Prochains departs depuis arrets proches, frequence, dernier depart |
| P.2 | **Temps trajet vers centres** | Routing API | M | ★★★★★ | "Lausanne gare: 12 min TP, Geneve: 45 min, Zurich: 2h10" |
| P.3 | **Frequence TP par tranche horaire** | GTFS data | M | ★★★★ | "Frequence bus 2: 6-8h = 5min, 8-18h = 10min, apres 20h = 30min" |
| P.4 | **Abonnement TP recommande** | Zones tarifaires | S | ★★★ | "Zone Mobilis 11-12 recommandee, AG rentable si >X trajets/mois" |
| P.5 | **Station Publibike/Lime** | API velo-partage | S | ★★★★ | Stations velo/trottinette partagees a proximite |
| P.6 | **Mobility (autopartage)** | Mobility API | S | ★★★ | Voiture partagee Mobility la plus proche |
| P.7 | **Parking public** | OSM + parkings.ch | M | ★★★★ | Places parking publiques, prix, disponibilite |
| P.8 | **Bornes recharge EV detaillees** | geo.admin + OFEN | S | ★★★★ | Type de prise, puissance, operateur, prix, disponibilite temps reel |
| P.9 | **Acces autoroute** | OSM routing | S | ★★★ | Distance et temps vers jonction autoroute la plus proche |
| P.10 | **Aeroport** | Calcul distance | S | ★★★ | Distance GVA/ZRH/BSL + temps TP |
| P.11 | **Trafic routier** | Viasuisse / TomTom | M | ★★★ | Densite trafic devant le batiment, heures de pointe |
| P.12 | **Score multimodal** | Composite | S | ★★★★★ | Score 0-10: TP + velo + voiture + marche + partage = "mobilite ideale" |
| P.13 | **Projection TP futur** | Plans cantonaux TP | M | ★★★★ | "Nouvelle ligne tram prevue 2028 a 200m — valorisation attendue" |
| P.14 | **Stationnement velo** | OSM bicycle_parking | S | ★★★ | Places velo couvertes, arceaux, securises a proximite |

**Resultat:** Profil mobilite complet — chaque mode de transport, chaque commodite, temps reels et projections futures.

---

### PROGRAMME Q — EDUCATION, SANTE & SERVICES PUBLICS (M3-M9)

**Constat:** On compte les ecoles et hopitaux (OSM). On ne connait pas leur qualite, capacite, specialisation.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| Q.1 | **Ecoles avec details** | Portails cantonaux education | M | ★★★★★ | Nom, degre (primaire/secondaire/gymanse), distance, temps a pied, rating si dispo |
| Q.2 | **Creches & garderies** | OSM + communal | M | ★★★★★ | Structures d'accueil petite enfance — distance, places, horaires |
| Q.3 | **Universites & hautes ecoles** | OSM + swissuniversities | S | ★★★ | Distance EPFL, UNIL, HES, etc. |
| Q.4 | **Medecins generalistes** | Annuaire FMH | M | ★★★★ | Medecins dans 1km, specialites, accepte nouveaux patients |
| Q.5 | **Pharmacie de garde** | Rotation cantonale | M | ★★★ | Pharmacie de garde la plus proche aujourd'hui |
| Q.6 | **Hopital + urgences** | OSM + hopitaux.ch | M | ★★★★ | Distance hopital, temps ambulance estime, specialites |
| Q.7 | **Pompiers — temps intervention** | Casernes + distance | S | ★★★★ | Temps intervention estime des pompiers → score securite |
| Q.8 | **Bibliotheques** | OSM + communal | S | ★★ | Distance a la bibliotheque |
| Q.9 | **Piscines & centres sportifs** | OSM + communal | S | ★★★ | Infrastructures sportives a proximite |
| Q.10 | **Dechetterie / points collecte** | Donnees communales | S | ★★★ | Distance dechetterie, horaires, types de dechets acceptes |
| Q.11 | **Services communaux** | Commune website | S | ★★ | Mairie, etat civil, office postal — distances |
| Q.12 | **Score famille** | Composite | S | ★★★★★ | Score 0-10: ecoles + creches + parcs + securite + sport = "ideal pour familles" |

**Resultat:** Profil "qualite de vie" complet — crucial pour transactions immobilieres et attractivite locative.

---

### PROGRAMME R — MARCHE IMMOBILIER & VALORISATION (M3-M12)

**Constat:** `building_valuation_service` a des matrices hardcodees. Aucune donnee de marche reelle.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| R.1 | **Prix au m2 par commune** | OFS / Wuest Partner / comparis | M | ★★★★★ | Prix median achat/location par commune, evolution 5 ans |
| R.2 | **Transactions recentes zone** | Registre foncier (public) | L | ★★★★★ | Dernieres transactions immobilieres dans un rayon de 500m |
| R.3 | **Taux de vacance** | OFS statistiques | M | ★★★★ | Taux de vacance locative par commune → tension du marche |
| R.4 | **Loyers de reference** | OBLF / statistiques cantonales | M | ★★★★★ | Loyer moyen par type/taille/commune → benchmark pour fixation loyer |
| R.5 | **Indice construction** | OFS / SBB index | M | ★★★ | Cout construction par region → estimation valeur a neuf |
| R.6 | **Tendance gentrification** | Evolution prix + commerces + demo | L | ★★★★ | "Quartier en gentrification rapide — valorisation attendue +15% sur 5 ans" |
| R.7 | **Multiplicateur fiscal commune** | Donnees communales | S | ★★★★ | Coefficient fiscal → impact sur attractivite et cout propriete |
| R.8 | **Valeur officielle vs marche** | TaxContext + marche | M | ★★★★ | Ecart valeur officielle / valeur marche → opportunite fiscale |
| R.9 | **Rendement locatif estime** | Loyers / valeur | S | ★★★★★ | "Rendement brut estime: 4.2% (median commune: 3.8%)" |
| R.10 | **Projection valeur 5-10 ans** | Tendances + facteurs | L | ★★★★ | "Valeur projetee 2031: +12% (facteurs: tram, renovation quartier, tension marche)" |
| R.11 | **Comparables marche** | Annonces (homegate/comparis) | L | ★★★★ | "3 biens similaires en vente dans le quartier: 850k, 920k, 780k" |
| R.12 | **Impact renovation sur valeur** | Delta valeur pre/post travaux | M | ★★★★★ | "Desamiantage + isolation: valeur +8-12%, attractivite locative +15%" |
| R.13 | **Attractivite locative score** | Composite | M | ★★★★★ | Score 0-10: emplacement + etat + energie + commodites + transport = demande locataire |
| R.14 | **Alerte marche** | Veille prix | M | ★★★★ | "Les prix au m2 dans votre commune ont augmente de 5% en 6 mois" |

**Resultat:** Chaque batiment a un profil marche complet — valeur, tendance, benchmark, rendement, projection.

---

### PROGRAMME S — METEO HISTORIQUE & STRESS BATIMENT (M3-M9)

**Constat:** Robin l'a demande explicitement. MeteoSwiss a des archives massives. Le climat impacte directement l'etat du batiment.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| S.1 | **Historique meteo 30 ans** | MeteoSwiss (IDAWEB/API) | L | ★★★★★ | Temperature, precipitations, vent, ensoleillement — 30 ans d'archives par station |
| S.2 | **Evenements extremes historiques** | MeteoSwiss + Swiss Re | M | ★★★★★ | Tempetes, greles, canicules, gels extremes qui ont touche la zone |
| S.3 | **Carte grele historique** | Mobiliar / MeteoSwiss | M | ★★★★★ | Frequence et intensite grele → risque toiture/facade — donnee assureur cle |
| S.4 | **Jours gel/degel par annee** | MeteoSwiss archives | M | ★★★★ | Cycles gel/degel → degradation joints, fissures, amiante friable |
| S.5 | **Charge neige historique** | SLF/MeteoSwiss | M | ★★★★ | Charge neige max par hiver → risque toiture, dimensionnement structure |
| S.6 | **Precipitation extreme** | MeteoSwiss | M | ★★★★ | "Pluie max 24h: 89mm (2021)" → risque infiltration, dimensionnement drainage |
| S.7 | **Vent max historique** | MeteoSwiss | M | ★★★ | "Rafale max: 120 km/h (Lothar 1999)" → risque toiture/facade |
| S.8 | **Foudre — densite impacts** | MeteoSwiss Blitzkarte | M | ★★★★ | Densite impacts foudre/km2/an → risque electrique, paratonnerre |
| S.9 | **Ilot chaleur urbain** | Satellites + modeles | L | ★★★★ | "Ce batiment est dans un ilot de chaleur: +3°C vs campagne" → impact confort/energie |
| S.10 | **Correlation meteo/incidents** | Meteo × incidents batiment | M | ★★★★★ | "80% des infiltrations surviennent apres precipitations >40mm — alerte preventive" |
| S.11 | **Prevision meteo 7 jours** | MeteoSwiss API | S | ★★★★ | Prevision locale → alerte "forte pluie prevue, verifier drainage" |
| S.12 | **Stress cumule facade** | UV + gel + pluie + vent | M | ★★★★★ | Indice d'usure climatique par facade (nord/sud/est/ouest) |
| S.13 | **Saison optimale travaux calculee** | Historique meteo local | M | ★★★★ | "Fenetre ideale travaux exterieurs: 15 mai - 15 sept (87% jours secs)" base sur 10 ans |
| S.14 | **Micro-climat batiment** | Altitude + orientation + masques | M | ★★★ | Exposition solaire reelle, vent dominant, ombre des voisins |

**Resultat:** Le batiment a une memoire climatique — 30 ans de meteo, stress cumule, predictions, saison optimale.

---

### PROGRAMME T — NATURE, ESPACES VERTS & ENVIRONNEMENT (M3-M9)

**Constat:** Aucune donnee sur la vegetation, les espaces verts, la qualite de l'air locale, la lumiere, le bruit fin.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| T.1 | **Indice vegetation (NDVI)** | Sentinel-2 satellite | L | ★★★★ | Pourcentage vegetation dans 200m — greenness score |
| T.2 | **Canopee arboree** | Swissimage + LiDAR | M | ★★★ | Couverture arboree autour du batiment → confort, ombrage, biodiversite |
| T.3 | **Distance lac/riviere** | OSM hydrography | S | ★★★★ | Distance au plan d'eau le plus proche → attractivite + risque inondation |
| T.4 | **Distance foret** | OSM + swisstopo | S | ★★★ | Distance a la foret → loisirs, qualite air |
| T.5 | **Qualite air locale** | NABEL + stations cantonales | M | ★★★★★ | PM2.5, PM10, NO2, O3 — station la plus proche, historique, tendance |
| T.6 | **Pollution lumineuse** | Atlas mondial lumiere | M | ★★★ | Niveau pollution lumineuse → impact sommeil, biodiversite |
| T.7 | **Biodiversite locale** | InfoSpecies / OFEV | M | ★★★ | Especes protegees dans la zone → contraintes amenagement |
| T.8 | **Espaces verts publics details** | OSM + communal | S | ★★★★ | Parcs, jardins, places de jeux — surface, equipements, distance |
| T.9 | **Jardins familiaux** | OSM + communal | S | ★★ | Jardins familiaux a proximite → attractivite |
| T.10 | **Cours d'eau souterrains** | Cartes geologiques | M | ★★★★ | Impact sur fondations, humidite, risque structurel |
| T.11 | **Score nature** | Composite | S | ★★★★★ | Score 0-10: vegetation + eau + foret + air + biodiversite = "environnement naturel" |
| T.12 | **Vue panoramique** | DEM + 3D buildings | L | ★★★★★ | Analyse de la vue depuis le batiment: lac, montagnes, ville — viewshed analysis |

**Resultat:** Profil "nature & environnement" — attractivite verte, qualite air, vue, biodiversite.

---

### PROGRAMME U — DEMOGRAPHIE, POPULATION & SOCIETE (M3-M9)

**Constat:** Zero donnee demographique. Les gerances ont besoin de comprendre qui habite la zone.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| U.1 | **Population par commune/quartier** | OFS STATPOP | M | ★★★★ | Population, densite, evolution 10 ans |
| U.2 | **Structure d'age** | OFS | M | ★★★★ | Repartition 0-18, 18-35, 35-65, 65+ → profil locataire type |
| U.3 | **Revenu median** | OFS / administration fiscale | M | ★★★★★ | Revenu median par commune → capacite locative, standing |
| U.4 | **Taux de proprietaires** | OFS | S | ★★★ | Proprietaires vs locataires par commune |
| U.5 | **Nationalites** | OFS | S | ★★★ | Composition demographique → besoin i18n, diversite services |
| U.6 | **Taille des menages** | OFS | S | ★★★★ | Menages 1/2/3/4+ personnes → demande type logement |
| U.7 | **Evolution population** | OFS historique + projection | M | ★★★★ | "Commune en croissance +2.3%/an — pression locative" |
| U.8 | **Taux de rotation locataires** | Donnees internes + OFS | M | ★★★★ | Rotation moyenne dans la zone → indicateur stabilite |
| U.9 | **Chomage par commune** | SECO | S | ★★★ | Taux chomage → risque impayes, dynamique economique |
| U.10 | **Emplois dans la zone** | OFS STATENT | M | ★★★ | Nombre d'emplois dans 2km → dynamique economique locale |
| U.11 | **Score socio-economique** | Composite | S | ★★★★★ | Score 0-10: revenu + emploi + education + stabilite = profil zone |

**Resultat:** Profil demographique complet — qui habite la, quel pouvoir d'achat, quelle dynamique — crucial pour valorisation et strategie locative.

---

### PROGRAMME V — GEOLOGIE, SOL & SOUS-SOL (M6-M12)

**Constat:** Le sous-sol impacte directement: fondations, radon, humidite, risque sismique, contamination.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| V.1 | **Carte geologique** | Swisstopo geocover | M | ★★★★ | Type de roche/sol sous le batiment → risque tassement, fondations |
| V.2 | **Permeabilite sol** | Cartes hydrogeologiques | M | ★★★ | Permeabilite → risque infiltration, drainage necessaire |
| V.3 | **Nappe phreatique** | geo.admin + cantonal | M | ★★★★ | Profondeur nappe → risque humidite sous-sol, contrainte construction |
| V.4 | **Sites archeologiques** | Cantonal heritage | M | ★★★ | Zones archeologiques → blocage potentiel travaux de fondation |
| V.5 | **Radon geologique** | Carte geologie + radon | S | ★★★★ | Correlation type sol → potentiel radon (granit, moraine, etc.) |
| V.6 | **Risque tassement** | Sol + nappe + construction | M | ★★★★ | "Sol argileux + nappe haute → risque tassement differentiel" |
| V.7 | **Infrastructures souterraines** | Cadastre LTSS | M | ★★★ | Conduites, canalisations, cables → contraintes travaux |
| V.8 | **Qualite eau du robinet** | Distributeurs d'eau | M | ★★★ | Durete, mineraux, qualite — impact installations sanitaires |
| V.9 | **Reseau gaz** | Distributeurs gaz | S | ★★★ | Raccordement gaz possible → option energetique |
| V.10 | **Stabilite terrain** | Modele geotechnique | M | ★★★★ | Score stabilite terrain 0-10 |

**Resultat:** Le batiment connait son sous-sol — risques fondations, humidite, contraintes, qualite eau.

---

### PROGRAMME W — VOISINAGE BATI & CONTEXTE ARCHITECTURAL (M3-M9)

**Constat:** Le batiment existe dans un tissu bati. Les voisins impactent directement: ombre, bruit, risque incendie, esthetique, valeur.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| W.1 | **Batiments voisins** | RegBL + OSM | M | ★★★★ | Identification des batiments dans 50m: age, type, hauteur, usage |
| W.2 | **Ombre portee voisins** | swissBUILDINGS3D + sun calc | L | ★★★★★ | "Le batiment voisin (28m) projette une ombre sur la facade sud de 14h a 17h en hiver" |
| W.3 | **Risque propagation incendie** | Distance + materiaux voisins | M | ★★★★ | "Distance au voisin: 3m, facade bois → risque propagation eleve" |
| W.4 | **Chantiers voisins actifs** | Portails permis cantonaux | M | ★★★★ | "Construction en cours a 30m — nuisances, poussiere, vibrations" |
| W.5 | **Projets construction prevus** | Mises a l'enquete publique | M | ★★★★★ | "Immeuble 6 etages prevu a 20m — impact vue, ombre, valeur" |
| W.6 | **Densite bati** | OSM + RegBL | S | ★★★ | COS/CUS reel de la parcelle et du quartier |
| W.7 | **Homogeneite architecturale** | Age + type voisins | M | ★★★ | "Quartier homogene 1960-1975 beton" → memes risques polluants probables |
| W.8 | **Servitudes de vue** | RDPPF | M | ★★★ | Servitudes impactant les possibilites de construction |
| W.9 | **Mitoyennete** | Cadastre | S | ★★★★ | Murs mitoyens → contraintes isolation, bruit, travaux |
| W.10 | **Antennes telecom** | OFCOM + OSM | S | ★★★ | Antennes 5G/4G dans 200m — info pour certains locataires |

**Resultat:** Le batiment comprend son contexte bati — voisins, ombres, chantiers, projets futurs, risques mutualises.

---

### PROGRAMME X — SATELLITE, IMAGERIE & REMOTE SENSING (M6-M12)

**Constat:** Des images satellites gratuites (Sentinel-2, Swissimage) permettent de deduire enormement sans aller sur site.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| X.1 | **Photo aerienne historique** | Swisstopo LUBIS / Zeitreise | L | ★★★★★ | Photos aeriennes 1940-2024 → evolution du batiment et du quartier |
| X.2 | **Detection changement toiture** | Sentinel-2 / Swissimage | L | ★★★★ | Comparaison images → "toiture modifiee entre 2019 et 2023" |
| X.3 | **Etat toiture depuis satellite** | Swissimage 10cm | L | ★★★★★ | Detection mousse, degats, panneaux solaires, equipements — sans aller sur site |
| X.4 | **Thermographie aerienne** | Images IR si disponibles | L | ★★★★★ | Deperditions thermiques detectees par satellite → isolation defaillante |
| X.5 | **Impermeabilisation sol** | Sentinel-2 NDVI | M | ★★★ | Taux surface impermeable parcelle → drainage, canicule |
| X.6 | **Ombre solaire annuelle** | DEM + 3D + sun calc | L | ★★★★ | Carte ensoleillement par mois — impact panneaux solaires et confort |
| X.7 | **Street View integration** | Google/Mapillary | M | ★★★★ | Vue facade depuis Street View directement dans la fiche batiment |
| X.8 | **Facade analysis par IA** | LLM vision + Street View | L | ★★★★★ | "Facade: enduit fissure, stores defectueux, vegetation envahissante" — detect auto |
| X.9 | **Comptage etages depuis image** | swissBUILDINGS3D + photo | M | ★★★ | Verification/correction nb etages depuis image |
| X.10 | **Historique evolution urbaine** | Swisstopo Zeitreise | L | ★★★★ | Animation: evolution du quartier 1950→2025 |

**Resultat:** Le batiment est observe depuis l'espace — etat toiture, facade, evolution historique, thermographie — sans visite sur site.

---

### PROGRAMME Y — DONNEES COMMUNALES & ADMINISTRATIVES (M3-M9)

**Constat:** Chaque commune suisse a ses specificites. Taxes, reglements, services — tout varie.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| Y.1 | **Coefficient fiscal commune** | Administrations fiscales | M | ★★★★★ | Multiplicateur fiscal → impact direct cout propriete |
| Y.2 | **Budget communal** | Comptes communaux | M | ★★★ | Sante financiere de la commune → services, investissements |
| Y.3 | **Reglement construction communal** | Reglements disponibles | L | ★★★★ | COS, CUS, hauteur max, distances, gabarits — par commune |
| Y.4 | **Taxe dechets** | Communes | S | ★★ | Cout dechets par commune (taxe au sac, forfait, etc.) |
| Y.5 | **Taxe eau/eaux usees** | Communes | S | ★★★ | Cout eau par commune → charge locataire |
| Y.6 | **Plan directeur communal** | Plans cantonaux | L | ★★★★ | Projets prevus: routes, ecoles, espaces verts, densification |
| Y.7 | **Elections/votations** | Commune data | S | ★★ | Tendance politique → prediction changements reglementaires |
| Y.8 | **Fusion communale prevue** | Canton | S | ★★★ | Fusion prevue → changement fiscal, reglementaire, services |
| Y.9 | **Services communaux en ligne** | E-gov cantonal | S | ★★ | Degre de numerisation → facilite demarches |
| Y.10 | **Protection civile / abris** | Commune + OFPP | S | ★★★ | Presence d'abri PC dans le batiment → obligation/atout |

**Resultat:** Profil administratif complet par commune — taxes, reglements, projets, tendances.

---

### PROGRAMME Z — CULTURE, LOISIRS & QUALITE DE VIE (M3-M9)

**Constat:** L'attractivite d'un batiment depend aussi de la vie culturelle et sociale autour.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| Z.1 | **Musees & galeries** | OSM + Google Places | S | ★★★ | Offre culturelle a proximite |
| Z.2 | **Cinemas & theatres** | OSM + Google Places | S | ★★★ | Loisirs culturels |
| Z.3 | **Centres sportifs & fitness** | OSM + Google Places | S | ★★★★ | Salles de sport, piscines, terrains — distance |
| Z.4 | **Terrains de jeux enfants** | OSM | S | ★★★★ | Places de jeux → attractivite familles |
| Z.5 | **Lieux de culte** | OSM | S | ★★ | Eglises, mosques, temples — diversite |
| Z.6 | **Vie associative** | Annuaires communaux | M | ★★★ | Clubs, associations, activites locales |
| Z.7 | **Marches & producteurs locaux** | OSM + communal | S | ★★★ | Marches, fermes, circuits courts |
| Z.8 | **Sentiers randonnee** | Swisstopo / Suisse Mobile | S | ★★★ | Acces randonnee, VTT, ski de fond |
| Z.9 | **Score qualite de vie globale** | Composite de TOUS les scores | S | ★★★★★ | Score 0-100: mobilite + nature + services + culture + securite + commerce + education + sante |
| Z.10 | **Comparaison quartier** | Benchmark inter-zones | M | ★★★★★ | "Ce quartier vs moyenne cantonale vs top 10% — forces et faiblesses" |

**Resultat:** Le batiment a un score qualite de vie complet, comparable, vendable.

---

### PROGRAMME AA — ASSURANCE, RISQUE & ACTUARIAT (M6-M12)

**Constat:** L'assurance immobiliere est un marche enorme. Les assureurs ont besoin de profils risque detailles.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| AA.1 | **Profil risque assureur** | Composite | M | ★★★★★ | Score risque composite: incendie + eau + tempete + gel + polluants + sismique |
| AA.2 | **Historique sinistres zone** | ECA / Mobiliar open data | L | ★★★★★ | Sinistres par commune/type/annee → frequence locale |
| AA.3 | **Carte grele Swiss Mobiliar** | Mobiliar open data | M | ★★★★★ | Frequence/intensite grele par zone → risque toiture |
| AA.4 | **Estimation prime** | Modele actuariel simplifie | L | ★★★★ | "Prime estimee: 2'400 CHF/an (vs 1'800 median commune)" |
| AA.5 | **Gap analysis couverture** | Policy vs risques | M | ★★★★★ | "Risque inondation eleve mais pas de couverture elementaire → lacune" |
| AA.6 | **Impact travaux sur prime** | Delta risque post-travaux | M | ★★★★ | "Apres desamiantage: risque -30%, prime estimee -15%" |
| AA.7 | **ECA canton** | Etablissements cantonaux | M | ★★★★ | Valeur d'assurance ECA, franchise, couverture — integration |
| AA.8 | **Responsabilite civile batiment** | RC analysis | M | ★★★ | Risques RC: chute de facade, chute neige, etc. |
| AA.9 | **Pack assureur complet** | Export structure | M | ★★★★★ | Profil risque + historique + mesures + recommandations → PDF assureur |
| AA.10 | **Benchmark assurance** | Cross-building | S | ★★★★ | "Votre batiment vs parc similar: plus/moins risque, prime justifiee?" |

**Resultat:** Profil assureur complet — risque, historique, couverture, gaps, benchmark. Marche assurance = nouveau canal commercial.

---

### PROGRAMME AB — ACCESSIBILITE & HANDICAP (M6-M12)

**Constat:** La conformite accessibilite est une obligation croissante. Aucune evaluation actuelle.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| AB.1 | **Evaluation accessibilite** | Norme SIA 500 | M | ★★★★ | Check: acces fauteuil, ascenseur, portes, sanitaires, parking |
| AB.2 | **Score accessibilite 0-10** | Composite | S | ★★★★ | Score global accessibilite PMR |
| AB.3 | **Recommandations accessibilite** | SIA 500 + batiment | M | ★★★★ | "Manque: rampe entree, ascenseur, porte 90cm au 2eme" |
| AB.4 | **Cout mise en conformite** | Estimation | M | ★★★ | "Mise aux normes accessibilite: ~35-50k CHF" |
| AB.5 | **Obligation legale accessibilite** | LHand + OHand | M | ★★★★ | "Obligation: mise en conformite si renovation >CHF 300k" |

---

### PROGRAMME AC — HISTORIQUE BATIMENT & GENEALOGIE PROFONDE (M3-M12)

**Constat:** Un batiment peut avoir 100 ans d'histoire. Archives, permis, transformations, proprietaires — tout raconte son histoire.

| # | Feature | Source | Effort | Impact | Detail |
|---|---------|--------|--------|--------|--------|
| AC.1 | **Genealogie proprietaires** | Registre foncier | L | ★★★★ | Chaine de propriete complete depuis construction |
| AC.2 | **Historique permis complet** | Archives cantonales | L | ★★★★ | Tous les permis: construction, transformation, demolition partielle |
| AC.3 | **Transformations detectees** | Permis + photos aeriennes | M | ★★★★★ | "1975: construction, 1992: surelevation 2eme etage, 2005: renovation facade" |
| AC.4 | **Photo historique batiment** | Swisstopo LUBIS + archives | L | ★★★★★ | Photos du batiment a travers les decennies — timeline visuelle |
| AC.5 | **Architecte original** | Archives permis | M | ★★★ | Qui a concu le batiment → style, qualite, materiaux typiques |
| AC.6 | **Evenements marquants** | Archives + incidents + travaux | M | ★★★★ | "1987: incendie partiel, 1999: tempete Lothar degats toiture, 2015: desamiantage partiel" |
| AC.7 | **Age reel composants** | Historique travaux | M | ★★★★★ | "Structure: 1965, toiture: 2005, facade: 1965 (originale), sanitaires: 1998" |
| AC.8 | **Frise chronologique riche** | Tous evenements | L | ★★★★★ | Timeline visuelle avec photos, documents, permis, incidents, travaux, proprietaires |
| AC.9 | **Valeur patrimoniale** | Heritage + architecte + age | M | ★★★★ | Score patrimonial: "batiment de valeur architecturale significative (Le Corbusier, 1932)" |
| AC.10 | **Jumeaux identiques** | Meme architecte + meme epoque + meme quartier | M | ★★★★★ | "Ce batiment a 3 jumeaux identiques au 14, 16 et 18 de la meme rue" → copier diagnostics |

**Resultat:** Le batiment a une biographie complete — 100 ans d'histoire, photos, transformations, proprietaires.

---

### RESUME PROGRAMMES ETENDUS M0-M12

| Programme | Items | Effort total | Theme |
|-----------|-------|-------------|-------|
| **A-N (existants)** | 157 | ~47-57 sprints | Geospatial, climat, materiaux, incidents, energie, fiscal, plans, registres, intelligence, IoT, visu, imports, rapports, conformite |
| **O. Vie de quartier** | 15 | ~3-4 sprints | Google Places, walkability, securite, commerces, isochrone |
| **P. Transport profond** | 14 | ~3-4 sprints | Horaires CFF, temps trajet, multimodal, parking, EV |
| **Q. Education & sante** | 12 | ~2-3 sprints | Ecoles detaillees, creches, medecins, urgences, score famille |
| **R. Marche immobilier** | 14 | ~4-5 sprints | Prix m2, transactions, loyers, rendement, projection |
| **S. Meteo historique** | 14 | ~4-5 sprints | 30 ans meteo, grele, gel/degel, stress facade, thermographie |
| **T. Nature & environnement** | 12 | ~3-4 sprints | NDVI, qualite air, biodiversite, vue panoramique |
| **U. Demographie** | 11 | ~2-3 sprints | Population, revenus, structure age, chomage, rotation |
| **V. Geologie & sous-sol** | 10 | ~3-4 sprints | Carte geologique, nappe, archeologie, stabilite |
| **W. Voisinage bati** | 10 | ~3-4 sprints | Ombre voisins, chantiers, projets futurs, mitoyennete |
| **X. Satellite & imagerie** | 10 | ~4-5 sprints | Photos aeriennes historiques, etat toiture, facade IA, thermographie |
| **Y. Donnees communales** | 10 | ~2-3 sprints | Coefficient fiscal, reglement, plan directeur, protection civile |
| **Z. Culture & loisirs** | 10 | ~2-3 sprints | Sport, culture, marches, randonnee, score qualite de vie |
| **AA. Assurance & risque** | 10 | ~3-4 sprints | Profil assureur, grele, sinistres, gap analysis, pack |
| **AB. Accessibilite** | 5 | ~1-2 sprints | SIA 500, score PMR, recommandations, cout |
| **AC. Genealogie profonde** | 10 | ~3-4 sprints | Proprietaires, permis, transformations, photos historiques, jumeaux |
| **AD. Building Credential & Verified Passport** | 15 | ~4-6 sprints | VC credentials, QR verification, SBT smart contract, API notaires/banques/assureurs, standard ouvert |
| **TOTAL ETENDU** | **~319 features** | **~94-113 sprints** | **30 programmes paralleles** |

---

## BRAINSTORM FRACTAL — EXPANSION (2026-04-01)

> Resultat du brainstorm fractal: sous-features manquees, croisements inter-programmes,
> donnees suisses oubliees, moonshots radicaux, usages derives, scores composites.

---

### FRACTAL 1 — SOUS-FEATURES MANQUEES PAR PROGRAMME

**A. Geospatial (ajouts):**
- A.21: Corridors ecologiques (ch.bafu.bundesinventare-amphibien) → contrainte construction
- A.22: Lignes haute tension (ch.bfe.starkstromleitungen) → champ electromagnetique, distance securite
- A.23: Antennes 5G/4G densité (ch.bakom.mobilfunkanlagen) → info locataires, controverse
- A.24: Zones militaires detail (ch.vbs) → restrictions acces, bruit exercices
- A.25: Perimetres danger Seveso (ch.bafu.stoerfallverordnung) → sites industriels dangereux proches
- A.26: Pipelines gaz/petrole (ch.bfe) → risque explosion, servitudes
- A.27: Stations de mesure air (ch.bafu.nabel) → qualite air locale mesuree
- A.28: Zones 30 km/h → securite enfants, bruit reduit

**B. Climat (ajouts):**
- B.11: Indice de confort thermique (PMV/PPD) basé sur meteo locale + orientation + isolation
- B.12: Risque canicule interieur → "Ce batiment sans clim aura >28°C pendant 35 jours/an en 2035"
- B.13: Potentiel geothermique → forages possibles, nappes exploitables
- B.14: Albedo toiture → impact ilot chaleur, temperature surface

**C. Materiaux (ajouts):**
- C.13: Base materiaux toxiques SUVA → correspondance directe avec liste SUVA des substances dangereuses
- C.14: Historique rappels fabricants → alertes si materiau/equipement rappele
- C.15: Cycle de vie materiau (LCA simplifie) → impact carbone par materiau installe
- C.16: Compatibilite materiaux → "Ce joint silicone n'est pas compatible avec le PCB present"
- C.17: Provenance materiau → lieu fabrication, transport, empreinte

**D. Incidents (ajouts):**
- D.11: Correlation incidents entre batiments voisins → "Le batiment voisin a aussi eu des fuites — cause commune?"
- D.12: Score resiliencedu batiment → frequence incidents × gravite × temps resolution
- D.13: Incidents saisonniers predits → "Historiquement, 70% des infiltrations surviennent en novembre"
- D.14: Integration protocole pompiers → rapport intervention pompiers → import automatique

**E. Energie (ajouts):**
- E.11: Potentiel pompe a chaleur → geothermique vs aerothermique vs hybride par batiment
- E.12: Calcul SIA 380/1 simplifie → besoins theoriques chauffage/refroidissement
- E.13: Comparaison sources energie → "Mazout actuel: 12k/an. PAC: 4k/an. Economie: 8k/an. ROI: 6 ans"
- E.14: Integration programme ProKilowatt → subventions efficacite electrique
- E.15: Smart meter virtual → estimation consommation par usage (chauffage, eau chaude, eclairage)

**F. Fiscalite (ajouts):**
- F.11: Optimisation fiscale renovation pluriannuelle → "Etaler les travaux sur 2 exercices fiscaux: economie 22k"
- F.12: TVA taux reduit renovation → calcul automatique TVA 7.7% vs 2.5% selon type travaux
- F.13: Deductions cantonales specifiques → chaque canton a ses propres deductions (VD ≠ GE ≠ BE)
- F.14: Amortissement comptable → plan amortissement immobilier automatise

**G. Plans (ajouts):**
- G.11: Superposition plan cadastral + plan batiment → alignement automatique
- G.12: Scan LiDAR → plan 3D de l'interieur depuis scan mobile
- G.13: Detection automatique surface par piece depuis plan → "Salon: 28m2, Chambre: 14m2"
- G.14: Historique modifications plan → diff entre versions de plans

**H. Registres (ajouts):**
- H.11: Registre du commerce → proprietaire = personne morale? Quel CA? Quel secteur?
- H.12: Poursuites/faillites proprietaire → risque de defaut
- H.13: PPE (propriete par etages) → parts, reglement, fonds de renovation
- H.14: Droits de superficie → baux emphyteotiques
- H.15: Annotations au registre foncier → mentions legales particulieres

**I. Intelligence (ajouts):**
- I.16: Prediction date prochain sinistre → ML sur historique + meteo + age + materiaux
- I.17: Score "ready to demo" → "Ce batiment est ideal pour montrer le produit a un prospect"
- I.18: Anomalie statistique auto → "Ce batiment a des valeurs anormales sur 3 dimensions — investigation"
- I.19: Recommandation sequencage travaux → "D'abord toiture (urgence), puis facade (ROI max), puis sanitaires (fin bail)"
- I.20: "Batiment jumeau virtuel" → modele predictif complet base sur 200+ dimensions

**O. Quartier (ajouts):**
- O.16: Taux Airbnb dans le quartier → pression touristique, bruit, rotation
- O.17: Chantiers futurs commune → projets votes, budget alloue, calendrier prevu
- O.18: Qualite reseau mobile (signal) → Swisscom/Sunrise/Salt mesure qualite
- O.19: Points de livraison (Amazon lockers, points relais) → praticite
- O.20: Zones pietonnes/rues limitees → impact acces, livraisons, demenagements

**R. Marche (ajouts):**
- R.15: Taux hypothecaire recommande → "Pour ce batiment, taux fixe 10 ans recommande a 1.8%"
- R.16: Estimation valeur par methode DCF → cash flows actualises
- R.17: Comparaison prix vente vs prix construction → "Ce batiment vaut plus en vente que sa reconstruction"
- R.18: Indice bulle immobiliere local → UBS Swiss Real Estate Bubble Index par region

---

### FRACTAL 2 — CROISEMENTS INTER-PROGRAMMES (30 croisements non-evidents)

| # | Croisement | Programme 1 | Programme 2 | Feature emergente |
|---|-----------|-------------|-------------|-------------------|
| X1 | Meteo × Materiaux | S | C | **Prediction degradation acceleree**: "30 cycles gel/degel/an + joints PCB 1975 = desagregation dans 2-3 ans" |
| X2 | Geologie × Incidents | V | D | **Correlation sol-sinistres**: "Sol argileux + secheresse 2022 = fissures structurelles dans 47 batiments" |
| X3 | Demographie × Energie | U | E | **Precarite energetique**: "Revenu median 4200 CHF + classe F = 18% du budget en energie" |
| X4 | Satellite × Incidents | X | D | **Detection degats depuis espace**: "Changement toiture detecte apres tempete — sinistre probable non declare" |
| X5 | Quartier × Marche | O | R | **Prediction gentrification**: walkability + nouveaux commerces + prix hausse = gentrification acceleree |
| X6 | Transport × Marche | P | R | **Impact TP sur valeur**: "Nouvelle ligne tram a 200m → +8-12% valeur estimee" |
| X7 | Geospatial × Assurance | A | AA | **Prime risque geolocalise**: score risque geo (inondation+seismique+grele) → estimation prime |
| X8 | Meteo × Energie | S | E | **Consommation energie predite**: DJU reels × isolation estimee = consommation previsible ce mois |
| X9 | Genealogie × Materiaux | AC | C | **Heritage materiau**: "Meme architecte 1968 = memes colles amiante dans tous ses batiments" |
| X10 | Education × Marche | Q | R | **Score ecole → valeur**: "Ecole primaire cotee dans top 10% → +5-7% valeur immobiliere" |
| X11 | Voisinage × Incidents | W | D | **Effet domino**: "Chantier voisin → vibrations → fissures apparues chez 3 batiments adjacents" |
| X12 | Nature × Sante | T | Q | **Sante environnementale**: "Espace vert <100m + qualite air bonne → score sante A" |
| X13 | Fiscalite × Energie | F | E | **Optimisation triple**: deduction fiscale + subvention + economie energie = ROI reel -40% |
| X14 | IoT × Assurance | J | AA | **Prime dynamique**: capteur radon OK + qualite air OK → reduction prime -10% |
| X15 | Registres × Genealogie | H | AC | **Due diligence automatique**: registre foncier + permis + proprietaires + hypotheques = DD en 1 clic |
| X16 | Meteo × Plans | S | G | **Orientation optimale**: ensoleillement reel × facade → "facade sud recoit 1200h soleil/an" |
| X17 | Demographe × Accessibilite | U | AB | **Besoin PMR predit**: "25% population >65 ans dans cette commune → demande accessibilite forte" |
| X18 | Satellite × Energie | X | E | **Thermographie aerienne**: detection deperditions thermiques depuis satellite IR → isolation defaillante |
| X19 | Commune × Fiscalite | Y | F | **Attractivite fiscale**: coefficient × deductions → "Demenager de Lausanne a Pully: -8k impots/an" |
| X20 | Geospatial × Nature | A | T | **Score bien-etre**: bruit + vert + air + eau + vue = score environnement global |
| X21 | Incidents × Energie | D | E | **Cout cache sinistres**: "Fuites recurrentes = +15% consommation eau chaude — 2400 CHF/an invisible" |
| X22 | Meteo × Voisinage | S | W | **Ombre + climat**: "Ombre voisin + orientation nord + 180 jours gel = moisissure facade probable" |
| X23 | Materiaux × Assurance | C | AA | **Risque materiau assure**: "Amiante friable + zone frequentee = risque sante = surprime 30%" |
| X24 | Transport × Education | P | Q | **Score accessibilite famille**: temps trajet ecole + creche + activites enfants en TP |
| X25 | Genealogie × Marche | AC | R | **Historique valorisation**: "Ce batiment: 420k (1998), 680k (2008), 950k (2020) → +5.2%/an" |
| X26 | IoT × Incidents | J | D | **Prevention proactive**: "Capteur humidite >80% depuis 72h au sous-sol → alerte pre-moisissure" |
| X27 | Geologie × Energie | V | E | **Potentiel geothermique reel**: "Type sol + nappe a 15m + pas de restriction → sonde geothermique ideale" |
| X28 | Registres × Conformite | H | N | **Permis vs realite**: "Permis 2005 autorise 3 etages, batiment a 4 etages → non-conformite" |
| X29 | Satellite × Nature | X | T | **Evolution vegetation**: "NDVI baisse de 30% en 5 ans autour du batiment → urbanisation, chaleur" |
| X30 | Commune × Assurance | Y | AA | **Risque communal**: "Commune sans plan d'urgence inondation + zone risque = surprime" |

---

### FRACTAL 3 — DONNEES SUISSES OUBLIEES (30 sources supplementaires)

| # | Source | Organisme | Type | Usage BatiConnect |
|---|--------|-----------|------|-------------------|
| DS.1 | **SUVA statistiques accidents** | SUVA | Statistiques | Taux accidents par type travaux → risque chantier |
| DS.2 | **ECA valeurs assurees** | ECA cantonaux | Registre | Valeur ECA officielle par batiment |
| DS.3 | **Registre du commerce (Zefix)** | OFRC | API | Identification proprietaire personne morale |
| DS.4 | **EAWAG qualite eau** | EAWAG/OFEV | Donnees | Qualite eau potable par commune |
| DS.5 | **SLF bulletins avalanches** | WSL/SLF | Previsions | Risque neige/avalanche zones montagnardes |
| DS.6 | **Swisscom couverture** | Swisscom | Carte | Qualite reseau fixe + mobile par adresse |
| DS.7 | **OFEN tarifs electricite** | OFEN/ElCom | Base | Tarif electricite par commune (elcom.admin.ch) |
| DS.8 | **PostFinance/Comparis loyers** | Comparis | Donnees | Loyers de reference par type + commune |
| DS.9 | **Homegate index** | Homegate/ZKB | Index | Evolution prix location par region |
| DS.10 | **OFAG zones viticoles** | OFAG | Carte | Zones viticoles protegees → contraintes |
| DS.11 | **ARE statistiques mobilite** | ARE | Etude | Distance domicile-travail, mode transport par commune |
| DS.12 | **BFS STATENT emploi** | OFS | Statistiques | Emplois par commune/branche → dynamique economique |
| DS.13 | **BFS STATPOP demographics** | OFS | Statistiques | Population, age, nationalite, menages par commune |
| DS.14 | **Indices UBS bulle** | UBS | Etude | Indice bulle immobiliere par region |
| DS.15 | **SNB taux hypothecaires** | BNS | Donnees | Taux de reference + historique |
| DS.16 | **SITG Geneve complet** | SITG | Geodonnees | Cadastre + parcelles + batiments + affectation GE |
| DS.17 | **AsitVD Vaud complet** | AsitVD | Geodonnees | Geodonnees cantonales VD detaillees |
| DS.18 | **GeoPortal BE** | Canton BE | Geodonnees | Geodonnees bernoises |
| DS.19 | **GIS ZH** | Canton ZH | Geodonnees | Geodonnees zurichoises |
| DS.20 | **Cadastre LTSS** | Cantons | Registre | Cadastre des conduites souterraines |
| DS.21 | **OFEV NABEL mesures** | OFEV | Temps reel | Qualite air (PM10, PM2.5, NO2, O3) par station |
| DS.22 | **SuissEnergie** | OFEN | Programme | Programmes d'encouragement federaux actifs |
| DS.23 | **Minergie registre** | Minergie | Base | Labels Minergie par batiment (EGID) |
| DS.24 | **GEAK registre** | CECB | Base | Certificats energetiques par batiment |
| DS.25 | **Geothermies.ch** | Swisstopo | Carte | Potentiel geothermique par localisation |
| DS.26 | **Swiss Federal Archives** | AFS | Archives | Plans historiques batiments federaux |
| DS.27 | **Protection civile abris** | OFPP | Registre | Abris PC par batiment → obligation |
| DS.28 | **Thermique solaire OFEN** | OFEN | Carte | Potentiel thermique solaire (eau chaude) |
| DS.29 | **Cadastre bruit route** | Cantons | Carte | Bruit routier mesure (plus precis que sonBASE) |
| DS.30 | **OPB valeurs limites** | OFEV | Reglement | Valeurs limites bruit par zone d'affectation |

---

### FRACTAL 4 — MOONSHOTS RADICAUX (15 idees folles mais faisables en 12 mois)

| # | Moonshot | Wow | Faisabilite | Detail |
|---|---------|-----|-------------|--------|
| MR.1 | **"Parle a ton batiment"** | ★★★★★ | LLM + RAG sur toutes donnees | Chat contextuel: "Quel est le risque amiante au 3eme?" → reponse avec sources |
| MR.2 | **Building Timelapse auto** | ★★★★★ | Swisstopo Zeitreise API | Animation 1940→2025 du batiment et son quartier — 1 clic |
| MR.3 | **Diagnostic predictif sans visite** | ★★★★★ | ML sur 200+ dimensions | "Probabilite 82% amiante dans colles, 65% PCB dans joints — diagnostic recommande" |
| MR.4 | **WhatsApp bot batiment** | ★★★★ | Twilio + LLM | Gestionnaire envoie photo par WhatsApp → identification materiau + alerte |
| MR.5 | **Passeport batiment NFC** | ★★★★ | NFC tag + QR | Coller un tag NFC sur le batiment → scan → tout le dossier |
| MR.6 | **Voice assistant terrain** | ★★★★ | Whisper + LLM | Sur le chantier: "Hey BatiConnect, est-ce que je peux percer ce mur?" → reponse contextuelle |
| MR.7 | **Carte des risques citoyenne** | ★★★★★ | Aggregation anonymisee | Carte publique: zones amiante probables par quartier — marketing viral |
| MR.8 | **Building match** | ★★★★ | Clustering + recommendation | "Trouvez des batiments similaires au votre qui ont deja ete renoves — apprenez de leur experience" |
| MR.9 | **Alert meteo → pre-action** | ★★★★★ | MeteoSwiss API + rules | "Tempete prevue demain: verifier toitures fragiles (3 batiments flagges)" → alerte 24h avant |
| MR.10 | **Renovation gamification** | ★★★★ | Score + badges + leaderboard | "Votre portefeuille est passe de C a B! Top 20% des gerances VD" |
| MR.11 | **AR mode terrain** | ★★★★★ | ARKit/ARCore + 3D | Pointer la camera → voir les zones polluants en AR sur la facade reelle |
| MR.12 | **Autonomous dossier bot** | ★★★★★ | Agent multi-step | "Complete mon dossier" → le bot identifie les lacunes, commande les diagnostics manquants, relance les parties |
| MR.13 | **Building Story auto** | ★★★★ | LLM + toutes donnees | "L'histoire de votre batiment" — narrative generee: construction, transformations, incidents, interventions |
| MR.14 | **Crowdsourced risk map** | ★★★★★ | Community + validation | Locataires/voisins signalent observations → validation croisee → carte risque enrichie |
| MR.15 | **Digital twin holographique** | ★★★★★ | Three.js + WebXR | Modele 3D interactif du batiment avec toutes les couches (polluants, materiaux, capteurs, risques) en VR/AR |

---

### FRACTAL 5 — USAGES DERIVES (produits pour d'autres acteurs)

| # | Acteur | Produit derive | Donnees utilisees | Modele |
|---|--------|---------------|-------------------|--------|
| UD.1 | **Notaires** | Pack due diligence immobilier | Registre foncier + dossier + readiness + risques | Per-transaction |
| UD.2 | **Banques** | Score hypothecaire batiment | Etat + risques + energie + valeur + polluants | API / per-query |
| UD.3 | **Assureurs** | Profil risque + historique | Sinistres + geo + meteo + materiaux + capteurs | Annual subscription |
| UD.4 | **Architectes** | Dossier pre-projet | Plans + contraintes + patrimoine + materiaux + reglementation | Per-building |
| UD.5 | **Bureaux ingenieurs** | Donnees techniques structurees | Geologie + materiaux + plans + diagnostics + capteurs | API |
| UD.6 | **Communes** | Dashboard parc communal | Portfolio + risques + conformite + energie par commune | Annual license |
| UD.7 | **Cantons** | Monitoring reglementaire | Conformite aggregate + tendances + anomalies | Institutional |
| UD.8 | **Confederation** | Donnees nationales anonymisees | Statistiques batiment, energie, polluants, renovation | Open data |
| UD.9 | **Chercheurs** | Dataset recherche | Correlations anonymisees 200+ dimensions | Academic license |
| UD.10 | **Promoteurs** | Score terrain/acquisition | Geo + marche + demographie + reglementation + potentiel | Per-query |
| UD.11 | **Investisseurs** | Due diligence portefeuille | Portfolio + risques + rendement + projection | Per-portfolio |
| UD.12 | **Agences immobilieres** | Fiche bien augmentee | Toutes dimensions + score + passport + photos | Per-listing |
| UD.13 | **Syndics PPE** | Dashboard copropriete | Etat + travaux + budget + fonds renovation + assemblees | Per-PPE |
| UD.14 | **Diagnosticiens** | Ciblage intelligent | "Batiments avec forte probabilite amiante non encore diagnostiques" | Subscription |
| UD.15 | **Entreprises remediation** | Pipeline prospects | Batiments avec besoin remediation identifie | Lead gen |
| UD.16 | **Energie** | Potentiel renovation energetique | CECB + consommation + potentiel solaire + subventions | Per-building |

---

### FRACTAL 6 — SCORES COMPOSITES MANQUANTS (25 nouveaux scores)

| # | Score | Calcul | Echelle | Usage |
|---|-------|--------|---------|-------|
| SC.1 | **Score Sante Batiment** | polluants + incidents + ventilation + qualite air + eau | 0-100 (A-F) | Vue globale sante |
| SC.2 | **Score Investissement** | rendement + valorisation + risques + energie + subventions | 0-100 | Decision achat/vente |
| SC.3 | **Score Famille** | ecoles + creches + parcs + securite + transport + bruit | 0-10 | Attractivite familiale |
| SC.4 | **Score Retraite** | accessibilite + sante + commerces + transport + calme | 0-10 | Attractivite seniors |
| SC.5 | **Score Teletravail** | fibre + coworking + calme + espace + luminosite | 0-10 | Attractivite remote |
| SC.6 | **Score Resilience** | sinistres + materiaux + structure + assurance + maintenance | 0-100 | Resistance aux chocs |
| SC.7 | **Score Carbone** | energie + materiaux + transport + dechets | kg CO2eq/m2/an | Empreinte carbone |
| SC.8 | **Score Urgence** | risque sante + reglementaire + fenetre + budget + bail | 0-10 | Priorisation intervention |
| SC.9 | **Score Digital Twin** | completude modele numerique: dimensions renseignees / total | 0-100% | Maturite donnees |
| SC.10 | **Score Potentiel** | renovation + solaire + geothermie + subventions + marche | 0-100 | Potentiel amelioration |
| SC.11 | **Score Locataire** | qualite vie + prix + transport + services + securite | 0-100 | Attractivite location |
| SC.12 | **Score Vendabilite** | conformite + documentation + readiness + marche + attractivite | 0-100 | Facilite de vente |
| SC.13 | **Score Assurabilite** | risques geo + materiaux + incidents + maintenance + capteurs | 0-100 | Facilite assurance |
| SC.14 | **Score Bancabilite** | valeur + revenus + risques + documentation + conformite | 0-100 | Facilite financement |
| SC.15 | **Score Durabilite** | energie + materiaux + eau + dechets + biodiversite + climat | 0-100 (A-F) | Performance environnementale |
| SC.16 | **Score Confort** | bruit + temperature + lumiere + humidite + vue + espace vert | 0-10 | Confort occupant |
| SC.17 | **Score Quartier Premium** | commerces + culture + restos + espace vert + transport | 0-10 | Standing quartier |
| SC.18 | **Score Risque Climatique** | inondation + canicule + gel + tempete + secheresse futur | 0-100 | Vulnerabilite climat 2050 |
| SC.19 | **Score Autonomie** | solaire + batterie + eau pluie + potager + isolation | 0-10 | Autosuffisance |
| SC.20 | **Score Heritage** | ISOS + monuments + architecte + age + authenticite | 0-10 | Valeur patrimoniale |
| SC.21 | **Score Mobilite** | TP + velo + voiture + marche + partage + multimodal | 0-10 | Accessibilite tous modes |
| SC.22 | **Score Smart Building** | capteurs + domotique + compteurs + connectivite + automation | 0-10 | Intelligence technique |
| SC.23 | **Score Conformite Globale** | polluants + securite + energie + accessibilite + incendie | 0-100 | Conformite toutes regles |
| SC.24 | **Score Maintenance** | age composants + garanties + entretien + incidents recurrents | 0-100 | Etat maintenance |
| SC.25 | **Score Pret-a-Renover** | documentation + budget + bail + saison + entreprises + permis | 0-100 | Readiness travaux global |

| Programme | Items | Effort total | Theme |
|-----------|-------|-------------|-------|
| **A. Geospatial** | 20 | ~3-4 sprints | 24 layers geo.admin, carte interactive, score risque |
| **B. Climat & Environnement** | 10 | ~2-3 sprints | Profil climatique, fenetres opportunite, durabilite |
| **C. Materiaux & Inventaire** | 12 | ~3-4 sprints | Inventaire vivant, prediction polluants, reconnaissance photo |
| **D. Incidents & Sinistres** | 10 | ~2-3 sprints | Memoire sinistres, patterns, predictions |
| **E. Energie & Certification** | 10 | ~3-4 sprints | CECB reel, trajectoire, simulation renovation |
| **F. Fiscalite & Subventions** | 10 | ~3-4 sprints | Deductions, eligibilite auto, ROI complet |
| **G. Plans & Visualisation** | 10 | ~4-5 sprints | Viewer interactif, overlays, 3D |
| **H. Registres publics** | 10 | ~4-5 sprints | RDPPF, registre foncier, permis, ISOS |
| **I. Intelligence croisee** | 15 | ~4-5 sprints | Predictions, correlations, heatmaps, anomalies |
| **J. Capteurs & IoT** | 10 | ~3-4 sprints | Radon reel, qualite air, preuves mesure |
| **K. Visualisations** | 15 | ~5-6 sprints | Timeline immersive, 3D, graphe evidence, infographies |
| **L. Connecteurs & Imports** | 15 | ~5-6 sprints | RegBL complet, cadastres, PDF auto, ERP, email |
| **M. Generation rapports** | 10 | ~3-4 sprints | Rapports auto: autorite, proprio, assureur, banque |
| **N. Conformite proactive** | 10 | ~3-4 sprints | Scan auto, delais, veille, diff cantonale |
| **TOTAL** | **157 features** | **~47-57 sprints** | **14 programmes paralleles** |

Avec capacite dev massive, 5-8 programmes en parallele = le tout en 12 mois.

**Top 25 features les plus impressionnantes (killer demos):**

*Intelligence & prediction:*
1. Prediction risque polluant par similarite cross-building (I.2)
2. Detection lacunes par comparaison: "95% des similaires ont un diagnostic radon — pas vous" (I.4)
3. Correlation meteo/incidents: alertes preventives avant intemperies (S.10)
4. Stress cumule facade par orientation + 30 ans meteo (S.12)
5. "Jumeaux identiques": meme architecte, meme epoque, meme rue → copier diagnostics (AC.10)

*Visualisation & demo:*
6. Carte interactive 24+ layers avec heatmap risque par quartier (A.17)
7. Heatmap confiance sur plan technique: bleu=bien documente, rouge=lacune (G.4)
8. Carte isochrone: tout accessible en 5/10/15 min a pied (O.10)
9. Ombre portee des voisins calcule en 3D par saison (W.2)
10. Photos aeriennes historiques 1940→2024: evolution du batiment (X.1)
11. Timeline immersive "vie du batiment" avec photos, documents, incidents (K.1)
12. Vue panoramique depuis le batiment: viewshed analysis (T.12)
13. Portfolio map 3D avec batiments colores par risque (K.13)

*Donnees & enrichissement:*
14. Profil risque assureur complet avec historique sinistres zone (AA.1+AA.2)
15. Etat toiture detecte depuis satellite sans visite sur site (X.3)
16. Facade analysis par IA depuis Street View (X.8)
17. Reconnaissance materiau sur photo terrain (C.6)
18. 30 ans d'historique meteo local correle au batiment (S.1)

*Business & finance:*
19. Simulation renovation energetique complete: cout, subvention, deduction, ROI (E.6+F.3)
20. Eligibilite subvention automatique: "3 programmes ouverts, total max 68k" (F.5)
21. Rendement locatif estime + benchmark commune (R.9)
22. Projection valeur 5-10 ans avec facteurs (R.10)

*Rapports & conformite:*
23. Rapport autorite 20+ pages genere en 1 clic (M.1)
24. Scan conformite automatique: "3 non-conformites, 2 obligations a venir" (N.1)
25. Score qualite de vie global 0-100 comparatif entre quartiers (Z.9)

**Mission:** Le batiment devient un objet vivant — memoire, passeport, operations, intelligence.

**Critere de passage:** Building Home est le centre de gravite quotidien pour les gestionnaires. Chaque batiment a un passeport, un historique, des operations actives.

### Q3-Q4 (M6-M12) — Living Building

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 5.1 | **Building Home 7 tabs complet** | P0 | Overview, Diagnostics, Documents, Actions, Timeline, Plans, Intelligence |
| 5.2 | Building Memory timeline v2 | P0 | Tout evenement trace chronologiquement |
| 5.3 | Building Passport persistent | P0 | Versionne, exportable, grade A-F |
| 5.4 | Evidence Graph navigable | P1 | Chaque score/action → preuve source |
| 5.5 | Time Machine v1 | P1 | "Que savait-on au 15 mars 2025?" |
| 5.6 | Plan annotation v1 | P1 | Plans techniques avec overlays |
| 5.7 | Zone safety status live | P1 | Statut securite par zone |
| 5.8 | Material inventory v1 | P1 | Inventaire materiaux par batiment |
| 5.9 | Component genealogy v1 | P2 | Historique des composants |
| 5.10 | Intervention simulator v2 | P2 | "Si on desamiante le 3eme, quel impact?" |

### Q5-Q6 (M12-M18) — Operations Layer

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 6.1 | **Lease Ops complet** | P0 | Baux, echeances, renouvellements |
| 6.2 | **Contract Ops complet** | P0 | Contrats, obligations, alertes |
| 6.3 | **Ownership Ops complet** | P0 | Mutations, historique, genealogie |
| 6.4 | Insurance policy management | P1 | Polices, couvertures, echeances |
| 6.5 | Permit tracking complet | P1 | Autorisations de construire, suivi statut |
| 6.6 | Maintenance forecast v1 | P1 | Prevision entretien predictif |
| 6.7 | Energy performance tracking | P1 | CECB, consommation, trajectoire |
| 6.8 | Tenant impact assessment | P2 | Impact travaux sur locataires |
| 6.9 | Occupant safety v2 | P2 | Evaluation securite occupants avancee |
| 6.10 | Warranty tracking | P2 | Garanties, echeances, rappels |
| 6.11 | Recurring service management | P2 | Services recurrents (chauffage, ventilation, etc.) |
| 6.12 | Work phase management | P2 | Phases de travaux structurees |
| 6.13 | Incident tracking v1 | P2 | Incidents, dommages, suivi |
| 6.14 | Ventilation assessment | P3 | Evaluation ventilation/qualite air |
| 6.15 | Climate exposure profiling | P3 | Profil exposition climatique |

### Engines a construire (Gate 2)

| Engine | Status actuel | Cible Gate 2 |
|--------|--------------|--------------|
| Building Passport Engine | v1 (passport_service) | Persistent, versionne, transferable |
| Evidence Graph Engine | v1 (evidence_graph_service) | Navigable, complet, chaque score→preuve |
| Readiness Engine | v1 (readiness_reasoner) | 7 safe_to_X states operationnels |
| Unknowns Engine | v1 (unknown_generator) | Auto-detect + resolution tracking |
| Contradiction Engine | v1 (contradiction_detector) | 5 types + resolution workflow |
| Post-Works Truth Engine | v1 (post_works_service) | Before/after complet + residual risk |
| Plan Annotation Engine | v0 (plan_heatmap_service) | Annotations interactives sur plans |
| Memory Engine | v0 (time_machine_service) | Point-in-time + diff + replay |

**Gate 2 PASS criteria:**
- [ ] Building Home = interface quotidienne (#1 page visitee)
- [ ] 100% des buildings pilotes ont un passport
- [ ] Evidence graph couvre 80%+ des scores
- [ ] Operations (lease/contract/ownership) utilisees en prod
- [ ] Time Machine fonctionnel sur 6+ mois d'historique

---

## GATE 3 — PORTFOLIO & CAPITAL SYSTEM (M12-M30)

**Mission:** Du batiment individuel au portefeuille — arbitrage, priorisation, budget, campagnes.

**Critere de passage:** Un gestionnaire peut piloter 50+ immeubles, prioriser les interventions, et justifier les budgets.

### Q5-Q6 (M12-M18) — Portfolio Intelligence

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 7.1 | **Portfolio Command Center v2** | P0 | Vue multi-building avec filtres, KPIs, carte |
| 7.2 | Portfolio risk heatmap | P0 | Carte des risques a l'echelle portefeuille |
| 7.3 | Campaign management v2 | P1 | Campagnes avec suivi, progression, ROI |
| 7.4 | Priority matrix v2 | P1 | Matrice risque/cout/urgence |
| 7.5 | Building clustering v2 | P1 | Groupes de buildings similaires |
| 7.6 | Saved simulations persistantes | P1 | Scenarios sauvegardes et comparables |
| 7.7 | CAPEX planning v1 | P2 | Planification budget investissement |
| 7.8 | Cost-benefit analysis v1 | P2 | ROI par intervention |
| 7.9 | Portfolio triage automatise | P2 | "Top 10 buildings a traiter en priorite" |
| 7.10 | Cross-building pattern mining | P2 | Patterns recurrents detectes |

### Q7-Q8 (M18-M24) — Capital Allocation

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 8.1 | **Budget tracking complet** | P0 | Suivi budgetaire par building/campagne |
| 8.2 | **CAPEX planning v2** | P0 | Multi-annuel, scenarios, arbitrage |
| 8.3 | Renovation sequencer v2 | P1 | Sequencage optimal des travaux |
| 8.4 | Cost-benefit analysis v2 | P1 | Multi-variable, avec subventions |
| 8.5 | Subsidy optimization | P1 | Maximiser Programme Batiments |
| 8.6 | Risk-to-CAPEX translator | P1 | Risque → impact budget |
| 8.7 | Finance workflow complet | P1 | Workflow financier de bout en bout |
| 8.8 | Portfolio scenario comparison | P2 | Comparer scenarios d'investissement |
| 8.9 | Multi-year projection | P2 | Projection 5-10 ans |
| 8.10 | Benchmark inter-portefeuilles | P2 | Comparaison entre gerances |

### Q9-Q10 (M24-M30) — Strategic Steering

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 9.1 | **Portfolio Opportunity Engine** | P0 | Quick wins, sequence optimale, recommandations |
| 9.2 | **Decision support dashboard** | P0 | Vue decideur avec scenarios |
| 9.3 | National-scale data accumulation v1 | P1 | Donnees multi-cantons aggregees |
| 9.4 | Cross-portfolio learning | P1 | Patterns inter-gerances (anonymises) |
| 9.5 | Reporting metrics v2 | P1 | Rapports automatises pour direction |
| 9.6 | ERP integration v1 | P1 | Overlay fonctionnel au-dessus des ERP existants |
| 9.7 | Stakeholder reporting v2 | P2 | Rapports stakeholders (CA, direction, autorites) |
| 9.8 | Environmental impact portfolio | P2 | Impact environnemental a l'echelle |
| 9.9 | Tax context integration | P2 | Contexte fiscal par building |
| 9.10 | ROI dashboard for management | P2 | "Combien BatiConnect nous fait economiser" |

**Gate 3 PASS criteria:**
- [ ] 3+ gerances avec 50+ buildings chacune
- [ ] Campagnes utilisees pour prioriser les travaux
- [ ] Budget tracking utilise pour justifier CAPEX
- [ ] Comparaison portfolio fonctionnelle
- [ ] Scenarios sauvegardes et partages

---

## GATE 4 — INFRASTRUCTURE & MARKET STANDARD (M24-M48)

**Mission:** De produit fort a reference de marche — echanges, standards, confiance legale, Europe.

**Critere de passage:** BatiConnect est reconnu comme standard de fait pour le dossier batiment en Suisse romande, avec expansion DACH engagee.

### Q9-Q10 (M24-M30) — Exchange & Trust

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 10.1 | **Passport Exchange Protocol v1** | P0 | Export/import standardise entre acteurs |
| 10.2 | **Partner Gateway v2** | P0 | API partenaires avec contracts |
| 10.3 | Legal-grade trust chain | P1 | Provenance prouvable, hash, timestamps |
| 10.4 | Partner trust profiles | P1 | Scoring fiabilite partenaires |
| 10.5 | Delegated access v2 | P1 | Acces granulaire par role/perimetre |
| 10.6 | GDPR compliance complet | P1 | Export, suppression, consentement |
| 10.7 | Digital vault v2 | P2 | Coffre-fort numerique certifie |
| 10.8 | Webhook ecosystem | P2 | Events temps reel pour partenaires |
| 10.9 | Audit export complet | P2 | Piste d'audit exportable |
| 10.10 | Exchange hardening v2 | P2 | Securite echanges renforcee |

### Q11-Q12 (M30-M36) — Swiss Standard

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 11.1 | **Rules Pack VD v3 (complet)** | P0 | Couverture reglementaire VD exhaustive |
| 11.2 | **Rules Pack GE v2 (complet)** | P0 | Couverture reglementaire GE exhaustive |
| 11.3 | Rules Pack BE v1 | P1 | Premier canton germanophone |
| 11.4 | Rules Pack ZH v1 | P1 | Zurich — plus grand marche |
| 11.5 | Swiss Rules Spine complet | P1 | OTConst, ORRChim, OLED, ORaP, CFST exhaustifs |
| 11.6 | Building Passport Export Standard v1 | P1 | Format d'export standardise (JSON-LD / openBIM?) |
| 11.7 | Authority submission digital v1 | P1 | Soumission numerique directe aux autorites |
| 11.8 | Regulatory Diff Engine v1 | P2 | Comparer regles entre cantons/dates |
| 11.9 | Public sector API v1 | P2 | API pour autorites/communes |
| 11.10 | Certification partnerships | P2 | Partenariats avec certificateurs |

### Q13-Q14 (M36-M42) — DACH Expansion

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 12.1 | **European Rules Layer architecture** | P0 | EU→Country→Region hierarchy |
| 12.2 | **Rules Pack AT v1** (Autriche) | P0 | Premier marche hors Suisse |
| 12.3 | **Rules Pack DE-BW v1** (Bade-Wurtemberg) | P1 | Land allemand frontalier |
| 12.4 | EPBD compliance mapping | P1 | Directive EU batiments mapee |
| 12.5 | Multi-language v2 (DE renforcé) | P1 | Allemand production-quality |
| 12.6 | Partner network DACH | P1 | Diagnosticiens/entreprises DACH |
| 12.7 | Data import adapters AT/DE | P2 | Registres publics AT/DE |
| 12.8 | Currency/tax adaptation | P2 | EUR, TVA locale |
| 12.9 | Market-specific packs | P2 | Packs adaptes par marche |
| 12.10 | Reference customers DACH | P2 | 2-3 clients references hors CH |

### Q15-Q16 (M42-M48) — European Reference

| # | Deliverable | Priority | Detail |
|---|-------------|----------|--------|
| 13.1 | **Building Passport as interoperable standard** | P0 | Format echangeable Europe |
| 13.2 | **Rules Pack FR v1** (France) | P1 | DPE, amiante avant travaux, etc. |
| 13.3 | Digital Building Logbook (EU alignment) | P1 | Alignement directive EU carnet numerique |
| 13.4 | Open API ecosystem | P1 | API publique documentee |
| 13.5 | Marketplace international | P2 | Contractors/diagnosticiens multi-pays |
| 13.6 | Cross-border portfolio management | P2 | Portefeuilles multi-pays |
| 13.7 | Agent ecosystem (third-party agents) | P2 | Agents tiers sur la plateforme |
| 13.8 | Academic/research partnerships | P3 | Collaborations EPFL, ETH, etc. |
| 13.9 | Standards body participation | P3 | Participation aux normes (SIA, CEN, ISO) |
| 13.10 | European reference status | P3 | Reconnu comme reference de marche |

**Gate 4 PASS criteria:**
- [ ] Passport export standard adopte par 2+ acteurs externes
- [ ] API partenaire utilisee par 5+ integrations
- [ ] 4+ cantons couverts (VD, GE, BE, ZH)
- [ ] 1+ marche hors Suisse actif
- [ ] Soumission autorite numerique fonctionnelle
- [ ] EPBD mapping complet

---

## CROSS-CUTTING: AI LAYER (M0-M48)

La couche AI evolue en 3 phases transversales:

### Phase 1 — LLM Does the Work (M0-M12)

| # | Capability | Status | Detail |
|---|-----------|--------|--------|
| AI-1.1 | Document classification (hybrid OCR+rules+LLM) | BUILT | document_classifier_service |
| AI-1.2 | Diagnostic extraction | BUILT | ai_extraction_service |
| AI-1.3 | Quote extraction | BUILT | quote_extraction_service |
| AI-1.4 | Feedback collection | PARTIAL | ai_feedback table existe |
| AI-1.5 | Recommendation engine v1 | BUILT | recommendation_engine |
| AI-1.6 | Campaign recommender v1 | BUILT | campaign_recommender |
| AI-1.7 | **Autonomous dossier completion agent v1** | BUILT | dossier_completion_agent |
| AI-1.8 | Score explainability v1 | BUILT | score_explainability_service |
| AI-1.9 | Nudge engine v1 | BUILT | nudge_engine |
| AI-1.10 | Material recommendation v1 | BUILT | material_recommendation_service |
| AI-1.11 | Lab result interpretation | TODO | lab_result_service existe mais LLM pas wire |
| AI-1.12 | Plan annotation via LLM | TODO | Annotations auto sur plans techniques |
| AI-1.13 | Narrative generation (passport) | TODO | passport_narrative_service existe |
| AI-1.14 | Obligation extraction from contracts | TODO | Extraction auto d'obligations |
| AI-1.15 | Regulatory text interpretation | TODO | Textes legaux → regles structurees |

### Phase 2 — Deterministic Rules Replace Proven LLM Patterns (M12-M30)

| # | Capability | Detail |
|---|-----------|--------|
| AI-2.1 | **Classification rules codified** | Top 80% des documents classes par regles, LLM = fallback |
| AI-2.2 | **Extraction templates** | Champs recurents extraits par templates, LLM = edge cases |
| AI-2.3 | **Readiness rules engine** | Regles deterministes pour 7 safe_to_X |
| AI-2.4 | **Action generation rules** | Actions auto par regles, plus par LLM |
| AI-2.5 | **Contradiction detection rules** | Regles de detection, LLM = cas ambigus |
| AI-2.6 | **Unknown generation rules** | Detection lacunes par regles |
| AI-2.7 | **Threshold-based alerts** | Alertes par seuils, plus par inference |
| AI-2.8 | **Compliance mapping rules** | Mapping reglementaire deterministe |
| AI-2.9 | **Pattern library** | Patterns appris → regles figees |
| AI-2.10 | **Cost estimation rules** | Estimations par baremes, LLM = ajustement |

### Phase 3 — LLM Supervises Rule Engine (M24-M48)

| # | Capability | Detail |
|---|-----------|--------|
| AI-3.1 | **Anomaly supervisor** | LLM surveille les outputs du rule engine |
| AI-3.2 | **Edge case handler** | LLM traite les cas que les regles ne couvrent pas |
| AI-3.3 | **Rule drift detector** | LLM detecte quand les regles deviennent obsoletes |
| AI-3.4 | **Cross-building pattern supervisor** | LLM identifie patterns emergents |
| AI-3.5 | **Regulatory change interpreter** | LLM interprete nouvelles lois → propose nouvelles regles |
| AI-3.6 | **Quality assurance supervisor** | LLM QA les outputs de la plateforme |
| AI-3.7 | **Autonomous agent v2** | Agent autonome pour completion dossier avancee |
| AI-3.8 | **Conversational building assistant** | "Parle-moi de ce batiment" — assistant contextuel |
| AI-3.9 | **Portfolio advisor** | Conseils strategiques sur portefeuille |
| AI-3.10 | **Agent Audit Console** | Console de supervision des agents AI |
| AI-3.11 | **Third-party agent SDK** | SDK pour agents tiers |
| AI-3.12 | **Multi-agent orchestration** | Agents specialises coordonnes |

---

## CROSS-CUTTING: PLATFORM & DEVOPS (M0-M48)

### Infrastructure (M0-M12)

| # | Item | Status | Priority |
|---|------|--------|----------|
| P-1 | Docker Compose 9 services | DONE | — |
| P-2 | PostgreSQL + PostGIS | DONE | — |
| P-3 | MinIO (S3) | DONE | — |
| P-4 | Redis (queues) | DONE | — |
| P-5 | Gotenberg (PDF) | DONE | — |
| P-6 | Meilisearch (search) | DONE | — |
| P-7 | GlitchTip (errors) | TODO | P1 |
| P-8 | OCRmyPDF + ClamAV | DONE | — |
| P-9 | Dramatiq workers | PARTIAL | P1 |
| P-10 | Nginx reverse proxy | DONE | — |
| P-11 | CI/CD pipeline (GitHub Actions) | TODO | P0 |
| P-12 | Staging environment | TODO | P0 |
| P-13 | Database migrations (Alembic) | DONE | — |
| P-14 | Automated backups | TODO | P0 |

### Scale (M12-M24)

| # | Item | Detail |
|---|------|--------|
| P-15 | Read replicas PostgreSQL | Pour queries analytics lourdes |
| P-16 | CDN frontend | CloudFlare ou equivalent |
| P-17 | Horizontal scaling backend | Multi-worker, load balancer |
| P-18 | Async job queue v2 | Dramatiq + Redis robuste |
| P-19 | Database partitioning | Par org ou par canton |
| P-20 | Object storage lifecycle | Policies retention MinIO |
| P-21 | Monitoring stack (Grafana + Prometheus) | Metriques, alertes, dashboards |
| P-22 | Log aggregation | Loki ou equivalent |
| P-23 | Uptime monitoring | Healthchecks, status page |
| P-24 | Performance benchmarks | Baseline + regression tests |

### Enterprise (M24-M48)

| # | Item | Detail |
|---|------|--------|
| P-25 | Multi-tenant architecture v2 | Isolation complete par org |
| P-26 | SSO/SAML integration | Auth entreprise |
| P-27 | API rate limiting v2 | Par partenaire, quotas |
| P-28 | Data residency options | Donnees en Suisse garanti |
| P-29 | Disaster recovery plan | RTO/RPO documentes et testes |
| P-30 | SOC 2 readiness | Preparation certification |
| P-31 | Penetration testing | Tests securite annuels |
| P-32 | API versioning v2 | Sunset policy, backwards compat |
| P-33 | Feature flags v2 | Rollout granulaire par org |
| P-34 | White-label capability | Pour partenaires revendeurs |

---

## CROSS-CUTTING: MOBILE & FIELD (M6-M36)

### Phase 1 — PWA Enhanced (M6-M12)

| # | Item | Detail |
|---|------|--------|
| M-1 | PWA offline mode v1 | Consultation dossier hors ligne |
| M-2 | Field observation mobile | Formulaire saisie terrain |
| M-3 | Photo capture + geotagging | Photos terrain avec GPS |
| M-4 | QR code building access | Scan QR → fiche batiment |
| M-5 | Push notifications | Alertes temps reel mobile |

### Phase 2 — Field Companion (M12-M24)

| # | Item | Detail |
|---|------|--------|
| M-6 | Offline sync engine | Sync bidirectionnel fiable |
| M-7 | Plan viewer mobile | Navigation plans sur tablette |
| M-8 | Sample collection workflow | Workflow prelevement terrain |
| M-9 | Voice notes with transcription | Notes vocales → texte |
| M-10 | Barcode/material scanning | Scan materiaux → identification |

### Phase 3 — Native App (M24-M36)

| # | Item | Detail |
|---|------|--------|
| M-11 | React Native ou Flutter app | Application native |
| M-12 | Offline-first architecture | Tout fonctionne hors ligne |
| M-13 | AR overlay on plans | Realite augmentee sur plans |
| M-14 | Sensor data collection | Integration capteurs (radon, etc.) |
| M-15 | Field team coordination | Coordination equipes terrain |

---

## CROSS-CUTTING: ECOSYSTEM & PARTNERS (M6-M48)

### Diagnosticiens (M6-M18)

| # | Item | Detail |
|---|------|--------|
| E-1 | Diagnostic import API | API reception rapports diagnostics |
| E-2 | Diagnostician portal | Interface diagnosticiens |
| E-3 | Lab result integration | Import resultats labo |
| E-4 | Quality feedback loop | Retour qualite → diagnosticien |
| E-5 | Mission order generation | Bon de commande diagnostic auto |

### Contractors (M12-M24)

| # | Item | Detail |
|---|------|--------|
| E-6 | Contractor portal v1 | Interface entreprises |
| E-7 | RFQ/tender response workflow | Reponse appels d'offres |
| E-8 | Work progress tracking | Suivi avancement travaux |
| E-9 | Post-works report upload | Upload rapport post-travaux |
| E-10 | Contractor acknowledgment v2 | Workflow acquittement avance |

### Authorities (M18-M36)

| # | Item | Detail |
|---|------|--------|
| E-11 | Authority submission portal | Soumission numerique |
| E-12 | Authority review workflow | Workflow revue autorite |
| E-13 | Decision notification | Notification decisions |
| E-14 | Public data exchange | Echange donnees publiques |
| E-15 | Permit tracking integration | Suivi autorisations integre |

### ERP & Systems (M18-M36)

| # | Item | Detail |
|---|------|--------|
| E-16 | Rimo integration | ERP immobilier #1 Suisse |
| E-17 | Abacus integration | ERP comptabilite |
| E-18 | ImmoTop integration | ERP gestion immobiliere |
| E-19 | SharePoint connector | Import docs SharePoint |
| E-20 | Email inbox processing | Import docs par email |

### Insurance & Finance (M24-M42)

| # | Item | Detail |
|---|------|--------|
| E-21 | Insurance company portal | Interface assureurs |
| E-22 | Lender readiness pack | Pack pour pret hypothecaire |
| E-23 | Notary integration | Integration etude notariale |
| E-24 | Property valuation feed | Estimation valeur immobiliere |
| E-25 | Due diligence pack export | Pack due diligence export |

---

## CROSS-CUTTING: DATA & INTELLIGENCE (M0-M48)

### Data Sources (M0-M18)

| # | Source | Status | Detail |
|---|--------|--------|--------|
| D-1 | GWR/RegBL (federal) | DONE | Registre federal batiments |
| D-2 | Vaud public (vd.batiment_rcb) | DONE | 3 layers Vaud |
| D-3 | Geneva cadastre | TODO | Donnees genevoises |
| D-4 | MADD | TODO | Registre adresses |
| D-5 | swissBUILDINGS3D | TODO | Modele 3D batiments |
| D-6 | CECB (certificat energetique) | TODO | Certificats energetiques |
| D-7 | Commercial diagnostics | TODO | Rapports diagnostics reels |
| D-8 | OpenStreetMap enrichment | TODO | Donnees OSM complementaires |
| D-9 | Swiss Topo | TODO | Geodonnees federales |
| D-10 | Cantonal geodata (VD/GE/BE/ZH) | PARTIAL | Geodonnees cantonales |

### Data Quality (M6-M24)

| # | Item | Detail |
|---|------|--------|
| D-11 | Data quality scoring v2 | Score qualite par champ |
| D-12 | Source reliability tracking | Fiabilite par source |
| D-13 | Freshness monitoring v2 | Fraicheur donnees automatique |
| D-14 | Deduplication engine | Dedup buildings/diagnostics |
| D-15 | Data lineage v2 | Tracabilite complete |
| D-16 | Automated validation rules | Regles validation automatiques |
| D-17 | Data enrichment pipeline | Enrichissement multi-source |
| D-18 | Quality dashboard v2 | Dashboard qualite donnees |

### Intelligence (M18-M48)

| # | Item | Detail |
|---|------|--------|
| D-19 | Cross-building learning v2 | Apprentissage inter-batiments |
| D-20 | Typology engine | Typologie batiments (age, construction, usage) |
| D-21 | Regional risk heatmap | Carte risques par region |
| D-22 | Material aging predictor | Prediction vieillissement materiaux |
| D-23 | Building DNA / Material Genome | Genome materiau par batiment |
| D-24 | Neighbor learning engine | Apprentissage par voisinage |
| D-25 | National-scale analytics | Analytique echelle nationale |
| D-26 | Predictive compliance | Prediction obligations futures |
| D-27 | Trend detection | Detection tendances macro |
| D-28 | Anonymized benchmark database | Base benchmark anonymisee |

---

## MOONSHOTS (M12-M48)

Les "killer demo surfaces" — high-impact, high-wow.

| # | Moonshot | Gate | Status actuel | Cible | Impact |
|---|---------|------|--------------|-------|--------|
| MS-1 | **Building Time Machine** | G2 | v1 built (time_machine_service) | Full replay interactif | "Remontez dans le temps" |
| MS-2 | **Proof Heatmap on Plans** | G2 | v1 built (plan_heatmap_service) | Overlay interactif temps reel | "Voyez la preuve sur le plan" |
| MS-3 | **Intervention Simulator** | G2 | v1 built (intervention_simulator) | Multi-scenario, what-if avance | "Simulez avant d'agir" |
| MS-4 | **Readiness Wallet** | G2 | v1 built (ReadinessWallet page) | Multi-state, dashboard | "7 etats de pret en un coup d'oeil" |
| MS-5 | **Autonomous Dossier Agent** | G2 | v1 built (dossier_completion_agent) | Agent autonome v2 | "L'agent complete votre dossier" |
| MS-6 | **Regulatory Diff Engine** | G4 | Not built | Cross-canton/cross-time comparison | "Comparez les regles entre cantons" |
| MS-7 | **Cross-Building Pattern Engine** | G3 | v1 built (cross_building_pattern) | Apprentissage a l'echelle | "Votre batiment ressemble a ceux-ci" |
| MS-8 | **Building Passport Standard** | G4 | Format interne | JSON-LD exportable, interoperable | "Le passeport voyage" |
| MS-9 | **European Rules Layer** | G4 | Architecture only | Multi-pays operationnel | "Memes regles, autres pays" |
| MS-10 | **Agent Audit Console** | G4 | Not built | Console supervision AI | "Supervisez vos agents" |
| MS-11 | **Conversational Building Assistant** | G3 | Not built | "Parle-moi de ce batiment" | Chat contextuel |
| MS-12 | **AR Plan Overlay** | G4 | Not built | Realite augmentee terrain | "Voyez les risques en AR" |

---

## METRICS & KPIs PAR GATE

### Gate 1 KPIs
| Metric | Target | Measurement |
|--------|--------|-------------|
| Clients actifs | 5-10 | Count |
| Buildings manages | 100+ | Count |
| Completude dossier | ≥95% | completeness_engine |
| Rework reduction | ≥50% | Before/after measure |
| Pack generation time | <2h | Chronometre |
| Provenance integrity | 100% | Audit trail |
| NPS | >50 | Survey |

### Gate 2 KPIs
| Metric | Target | Measurement |
|--------|--------|-------------|
| Building Home daily usage | >80% users | Analytics |
| Passport coverage | 100% buildings | passport_service |
| Evidence graph coverage | >80% scores | evidence_graph |
| Operations adoption | >60% clients | Feature usage |
| Time Machine queries | >10/month/client | Analytics |

### Gate 3 KPIs
| Metric | Target | Measurement |
|--------|--------|-------------|
| Portfolio size managed | 500+ buildings | Count |
| Campaign completion rate | >70% | campaign_service |
| CAPEX planning usage | >50% clients | Feature usage |
| Cross-building insights | >5/month | pattern_service |
| Budget tracking adoption | >40% | Feature usage |

### Gate 4 KPIs
| Metric | Target | Measurement |
|--------|--------|-------------|
| Partner integrations | 5+ | API contracts |
| Cantons covered | 4+ | rules_packs |
| International markets | 1+ | Active clients |
| Passport exports | >100/month | Export count |
| API calls (partners) | >10k/month | API metrics |
| Revenue growth | >100% YoY | Financials |

---

## SUMMARY — 48 MOIS EN CHIFFRES

| Dimension | Aujourd'hui (M0) | M12 | M24 | M36 | M48 |
|-----------|-----------------|-----|-----|-----|-----|
| **Clients** | 0 (pilotes) | 5-10 | 30-50 | 100+ | 300+ |
| **Buildings** | ~20 (seed) | 100+ | 500+ | 2000+ | 10'000+ |
| **Cantons** | VD | VD+GE | VD+GE+BE | +ZH+BS | +AT/DE |
| **Countries** | CH | CH | CH | CH+AT | CH+AT+DE+FR |
| **Data dimensions/building** | ~47 | **200+** | 250+ | 300+ | 350+ |
| **Data sources integrated** | ~6 active | **30+** | 45+ | 60+ | 80+ |
| **Backend services** | 292 | **350+** | 380+ | 410+ | 440+ |
| **Frontend pages** | 73 | **95+** | 110+ | 125+ | 140+ |
| **Models** | 162 | **195+** | 215+ | 235+ | 255+ |
| **API routes** | 252+ | **320+** | 360+ | 400+ | 440+ |
| **Tests** | ~8000 | **15000+** | 22000+ | 30000+ | 40000+ |
| **i18n keys** | ~1110 | **2000+** | 2800+ | 3500+ | 4200+ |
| **Computed scores/building** | ~5 | **25+** | 35+ | 45+ | 50+ |
| **Rules packs** | VD v1 | VD v2+GE v1 | +BE+ZH | +BS+AT | +DE+FR |
| **AI Phase** | Phase 1 | Phase 1→2 | Phase 2 | Phase 2→3 | Phase 3 |
| **M0-M12 features planned** | — | **319** | — | — | — |
| **M0-M12 programmes** | — | **30** | — | — | — |
| **Revenue** | 0 | ARR naissant | ARR croissant | ARR significatif | Scale |
| **Team** | Robin+AI | +1-2 | +3-5 | +8-12 | +15-25 |
| **Engines (12)** | 8 v0-v1 | 12 v1+ | 12 v2+ | 12 v3+ | 12 v4+ |

---

## WHAT MAKES THIS POSSIBLE

La raison pour laquelle 319 features en 12 mois est realiste:

1. **Infrastructure existante massive**: 292 services, 162 modeles, 252 routes — on *enrichit*, on ne *cree* pas from scratch
2. **Fetchers deja codes**: 24+ geo.admin fetchers existent, il suffit de les brancher
3. **Modeles deja definis**: ClimateExposureProfile, OpportunityWindow, FieldObservation, Incident, Material, InventoryItem — schemas riches, zero logique
4. **APIs publiques suisses**: geo.admin.ch, transport.opendata.ch, MeteoSwiss, OFS, opendata.swiss — donnees gratuites, bien documentees
5. **Enrichissement pipeline existe**: `enrichment/orchestrator.py` orchestre deja 50+ data points — ajouter un fetcher = ajouter une ligne
6. **Scores composites**: ajouter un score = une fonction qui combine des champs existants
7. **Frontend components**: 68 building-detail components existent — beaucoup ont juste besoin de donnees backend
8. **AI capacity massive**: agents paralleles, brainstorm, codex — execution 10x humain
9. **LLM vision**: reconnaissance materiau, facade analysis, plan extraction — Claude/GPT vision ready
10. **Pas de dette technique majeure**: 8000+ tests verts, fitness functions, CI ready

---

## PROGRAMME AD — BUILDING CREDENTIAL & VERIFIED PASSPORT (M6-M18)

**Constat:** Le dossier batiment est un PDF dans un email — pas de chaine de confiance, pas d'historique prouvable, pas de verification sans login, pas de transfert automatique lors de vente. Les tiers (autorites, banques, assureurs, notaires) n'ont aucun moyen de verifier l'authenticite et l'etat d'un dossier.

> Source: [brainstorm archive](archive/brainstorms/nft-building-passport-brainstorm.md)

### Phase 1 — Verifiable Credential sans blockchain (M6-M9, ~4 semaines dev)

| # | Feature | Effort | Detail |
|---|---------|--------|--------|
| AD.1 | **Signature QES passeport** | M | Signature electronique qualifiee (Swisscom Digital Trust / SwissSign) sur chaque passeport |
| AD.2 | **W3C Verifiable Credentials** | L | VC signee par BatiConnect pour chaque attestation (diagnostic, conformite, readiness) |
| AD.3 | **QR code verification sur packs** | S | QR auto sur tous les packs PDF → verify.baticonnect.ch/{egid} |
| AD.4 | **Page publique verification** | M | verify.baticonnect.ch/{egid}: grade, completeness, emetteur, date — sans compte ni login |
| AD.5 | **Registre de revocation** | M | Revocation list pour credentials expirees ou invalidees |

### Phase 2 — Soulbound Building Token (M9-M12, conditionnel)

> Deploye SEULEMENT si Phase 1 prouve la demande tiers (notaires, banques).

| # | Feature | Effort | Detail |
|---|---------|--------|--------|
| AD.6 | **Smart contract SBT** | L | ERC-721 + ERC-5192 soulbound sur Base ou Tezos — non-transferable, lie a l'EGID |
| AD.7 | **On-chain passport state** | M | EGID + grade + completeness + SHA-256 content hash + metadata URI (~500 bytes) |
| AD.8 | **Version lineage** | M | Chaque version liee a la precedente — historique immuable on-chain |
| AD.9 | **Testnet → mainnet migration** | M | Validation testnet puis deploiement mainnet |
| AD.10 | **Page portfolio public** | S | "X batiments verifies sur BatiConnect" — compteur public |

### Phase 3 — Ecosysteme partenaires (M12-M18)

| # | Feature | Effort | Detail |
|---|---------|--------|--------|
| AD.11 | **API verification notaires** | L | REST API: GET /verify/{egid} — due diligence en 5 min au lieu de 2 semaines |
| AD.12 | **API score hypothecaire banques** | L | Feed verifiable: bancabilite, polluants, energie, assurance |
| AD.13 | **Feed risque assureurs** | L | API temps reel: profil risque actualise, sinistres, capteurs |
| AD.14 | **Alignement eGRIS + e-ID suisse** | L | Pont vers registre foncier numerique et infrastructure nationale credentials |
| AD.15 | **Standard ouvert publie** | M | Specification Building Passport Token — interop cross-platform |

### Killer use cases

- **Autorite (P0):** scanne QR sur pack → voit emetteur/date/statut/scope verifie instantanement, sans compte
- **Mutation immobiliere (P0):** notaire scanne SBT → historique complet, due diligence 5 min au lieu de 2 semaines
- **Hypotheque bancaire (P1):** banque verifie score bancabilite → pre-approbation acceleree, expertise reduite
- **Assurance (P1):** assureur verifie profil risque temps reel → tarification dynamique, sans paperasse
- **ESG / green bond (P2):** score durabilite on-chain verifiable par investisseurs

### Gardes-fous (Codex warnings)

- **NE JAMAIS dire "NFT"** aux clients — dire "passeport certifie", "certificat verifiable", "sceau numerique"
- **Pas de titre de propriete** — les droits reels passent par le registre foncier, jamais par un token
- **Pas de token transferable** = pas de transfert immobilier — le transfert juridique reste notarial/foncier
- **Pas de wallet owner-facing** avec seed phrase — trop de friction pour gerances/notaires
- **Pas d'asset token** avec droits economiques — eviter classification FINMA lourde
- **Classification cible:** utility token (non-transferable, pas de valeur marchande, acces service)

### Modele economique

| Acteur | Ce qu'il paie | Prix indicatif | Valeur recue |
|--------|--------------|----------------|-------------|
| Proprietaire/gerance | Abonnement BatiConnect (inclut) | 0 CHF add. | Passeport verifiable, transfert facile |
| Notaire | Verification due diligence | 50-200 CHF/tx | DD en 5 min au lieu de 2 semaines |
| Banque | API verification score | 20-100 CHF/query | Pre-approbation acceleree |
| Assureur | Feed risque temps reel | 500-2000 CHF/an/1000 bat. | Tarification dynamique |
| Autorite | Gratuit (adoption) | 0 CHF | Verification instantanee |

**Revenue additionnel:** ~12k CHF/an pour 1000 batiments, ~120k CHF/an pour 10'000 batiments. La vraie valeur = lock-in + moat (batiment inscrit = batiment verrouille, tiers s'habituent a verifier via SBT).

### Budget realiste

| Phase | Budget | Scope |
|-------|--------|-------|
| MVP credentials (Phase 1) | CHF 150-300k | Credential + QR verifier + revocation + export |
| + juridique + audit (Phase 2) | CHF 300-700k | Avis juridique, audit secu, pilote partenaire |
| Full produit (Phase 3) | > CHF 1M | Wallet, public chain, partenaires multiples |

### Infrastructure suisse pertinente

- **eGRIS** (egris.admin.ch): numerisation registre foncier suisse — futur pont possible
- **e-ID suisse** (eid.admin.ch): infrastructure nationale credentials en construction
- **Swisscom Digital Trust**: signature electronique qualifiee
- **Loi DLT (2021)**: securite juridique pour droits tokenises (Art. 973d CO)

**Resultat:** Passeport batiment certifie et verifiable — chaine de confiance, historique immuable, verification sans login, revenus B2B. Moat quasi-irreversible.

---

## VISION BEYOND M48

> Au-dela de la roadmap 48 mois: le batiment devient un agent autonome.

### Tier 1 — Batiment qui parle, predit, scanne (M24-M36)

- **Batiment qui parle:** le building a une voix — rapports auto-generes, alertes proactives, "je vieillis mal cote facade"
- **Batiment qui predit:** ML sur historique → prediction pannes, degradation, couts futurs, fenetres d'opportunite
- **Batiment qui scanne:** LiDAR mobile + drone + vision IA → scan automatique etat facade, toiture, structure

### Tier 2 — Batiment tokenise, social, negocie (M36-M48)

- **Batiment tokenise:** SBT full ecosystem — chaque batiment a une identite on-chain verifiable par tous les acteurs
- **Batiment social:** batiments voisins communiquent — "mon voisin a eu le meme probleme, voici sa solution"
- **Batiment qui negocie:** le dossier batiment negocie automatiquement primes, devis, conditions — agent autonome

### Tier 3 — Batiment vivant (M48+)

- **Time Travel v3:** reconstruction complete de l'etat du batiment a n'importe quelle date passee ou future
- **Planetary OS:** reseau continental de batiments intelligents — CH → DACH → EU → global
- **Building DAO:** gouvernance decentralisee par les occupants/proprietaires — votes, budgets, decisions collectives

---

## DECISION LOG

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-01 | Roadmap 48 mois structure par gates, pas par dates | Gates = preuve, dates = fiction |
| 2026-04-01 | Gate 1 = priorite absolue (wedge proof) | Rien d'autre ne compte sans clients |
| 2026-04-01 | M0-M12 = 30 programmes / 319 features | Capacite dev massive en arrivage, infrastructure deja la |
| 2026-04-01 | Tout rattacher au batiment | Le batiment = hub de TOUTE l'info: geo, meteo, quartier, transport, demographie, marche, geologie, histoire, assurance |
| 2026-04-01 | Enrichissement > creation | 80% du travail = brancher des sources sur des modeles existants |
| 2026-04-01 | AI Phase 2 commence a M12, pas avant | Phase 1 doit accumuler assez de feedback |
| 2026-04-01 | Mobile = PWA d'abord, native a M24+ | PWA suffisant pour field v1 |
| 2026-04-01 | International = DACH avant EU-wide | Proximite culturelle, reglementaire, commerciale |
| 2026-04-01 | ERP = overlay, jamais remplacement | Adoption facilitee, pas competition |
| 2026-04-01 | Programme AD: credential d'abord, blockchain ensuite | VC + QES sans blockchain d'abord (Phase 1); SBT seulement si demande tiers prouvee (Phase 2) |
| 2026-04-01 | Jamais dire "NFT" — wording = "passeport certifie" | Baggage negatif crypto; technology bonne, branding sobre |

---

## NEXT IMMEDIATE ACTIONS (retour au present)

Les 10 prochaines actions concretes pour avancer Gate 1:

1. **Stabiliser e2e real preflight** — `e2e_real_preflight.mjs` est dirty
2. **CI/CD pipeline** — GitHub Actions basique (lint + test + build)
3. **Staging environment** — VPS staging separe de prod
4. **Automated backups** — PostgreSQL + MinIO backup quotidien
5. **GlitchTip setup** — Error tracking en prod
6. **Demo path harden** — Parcours demo fluide pour prospects
7. **Onboarding wizard completion** — Flow d'onboarding complet
8. **Pilot #1 prospect identification** — Identifier la premiere gerance VD
9. **Authority pack validation** — Faire valider un pack par une autorite VD reelle
10. **Feedback loop v1** — User corrections → ai_feedback table operationnel
