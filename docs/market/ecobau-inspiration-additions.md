# ecobau Inspiration -> SwissBuilding Additions

## Why this note exists

Turn ecobau inspiration into concrete SwissBuilding additions that:
- strengthen the `safe-to-start dossier` wedge
- stay claim-disciplined (readiness/proof, not legal guarantee)
- remain executable by agents with bounded scopes

Execution brief:
- `docs/projects/ecobau-inspired-readiness-and-eco-specs-program.md`

## What ecobau does that is directly relevant

1. Product-level ecological/health data
- ecoProduits publishes product sheets with `eco1 / eco2 / ecoBase` style status and criteria dimensions (health, ecology, circularity, climate).

2. Tender-oriented ecological specifications
- ecoDevis and ecoCFC are built to inject environmental/health constraints into specifications and procurement language (CFC/CAN-oriented workflows).

3. Pollutant-first guidance before works
- guidance references Polludoc-style diagnostics before works, notably with building-era and intervention-volume triggers.

4. Software integration pathway for ecobalance data
- ecobau provides a software developer path for ecobalance data use, but with accreditation/licensing constraints.

## What we already have in SwissBuilding

- strong readiness/proof/dossier chain
- OLED waste and disposal logic already modeled
- certification surfaces already present (Minergie/CECB/SNBS/GEAK readiness)
- authority pack and compliance artifacts already in progress

## Highest-value gaps vs ecobau-style expectations

1. No first-class `material recommendation + eco evidence` layer in operator flows.
2. No ecological tender clause generator (CFC/CAN-aligned language pack).
3. No explicit Polludoc-style trigger assistant in `safe-to-start` UX.
4. No PFAS-first extension in the pollutant readiness wallet.
5. No ecobalance integration adapter strategy for licensed external data.

## Priority Additions (ranked)

## A1 - Polludoc-style trigger assistant (quick win, wedge-critical)

Outcome:
- in building readiness flow, show a deterministic pre-work trigger card:
  - building-era risk signal
  - intervention-scale signal
  - required diagnostic pathway

Why now:
- reinforces external scenario #1 and improves buyer legibility fast.

Suggested scope:
- frontend card + backend rule helper (minimal glue only)
- legal-basis text from existing regulatory-pack layer

## A2 - Eco tender clause generator (quick win, commercial)

Outcome:
- generate reusable procurement clauses for interventions:
  - hazardous-material handling requirements
  - waste/disposal chain requirements
  - documentation/provenance obligations

Why now:
- converts readiness insight into purchasing/execution language.

Suggested scope:
- structured clause templates per intervention type
- export as part of authority/contractor pack

## A3 - Material recommendation shelf with eco status (medium)

Outcome:
- intervention planning includes suggested material options with:
  - eco status (`eco1/eco2`-style internal classification)
  - evidence requirements
  - circularity and health impact notes

Why now:
- bridges diagnosis -> decision -> execution quality.

Suggested scope:
- internal classification first (no external licensed sync in phase 1)
- product-sheet object + evidence links

## A4 - PFAS extension in readiness wallet (medium)

Outcome:
- add PFAS-aware checks and blocker logic in pre-work readiness.

Why now:
- market relevance is rising and fits pollutant-first identity.

Suggested scope:
- new pollutant profile in readiness reasoner + legal basis metadata
- targeted UI checks and disclaimer wording

## A5 - Ecobalance adapter strategy (strategic)

Outcome:
- define licensed integration path for ecobalance datasets.

Why now:
- unlocks early-stage gray-energy / CO2 intelligence with trusted data.

Suggested scope:
- adapter contract + provenance model + licensing gate
- no scraping; official integration only

## 6 Claude-ready tasks (disjoint, no hub contention)

1. Add Polludoc-style trigger card contract + API response fields.
2. Implement readiness UI card for trigger assistant on building detail/readiness page.
3. Add eco tender clause template service + tests.
4. Add clause export section to authority/contractor pack flow.
5. Add PFAS readiness checks + legal basis mapping.
6. Add PFAS UI status and blockers in readiness wallet.

## Execution constraints

- keep backend freeze policy in mind: only minimal glue for active frontend productization when freeze is active
- no legal guarantee claims
- keep source provenance explicit for every external rule/data point
- prefer official data access and licensing over scraping

## Sources (official/ecobau ecosystem)

- ecobau home and instruments: `https://www.ecobau.ch/`
- ecoProduits context and scale: `https://www.ecobau.ch/fr/instruments/eco-produits/guide/`
- example product sheet dimensions and status: `https://www.ecobau.ch/fr/produits/produit/produit/866166/`
- ecoCFC (CFC/CAN-oriented ecological specs): `https://www.ecobau.ch/instrumente/eco-bkp/`
- ecoDevis guide: `https://www.ecobau.ch/fr/instruments/eco-devis/guide/`
- software integration/ecobalance pathway: `https://www.ecobau.ch/de/instrumente/oekobilanzdaten-fuer-bauteile/fuer-softwareentwickler/`
- pollutant before-work guidance (Polludoc references): `https://www.ecobau.ch/fr/themes/polluants-du-batiment/recommandation-diagnostic-des-batiments/`
- Polludoc framing page (French): `https://www.ecobau.ch/fr/themes/polluants-du-batiment/pfas/`
