# Stack Frontier Map and Build-vs-Integrate

Date de controle: `25 mars 2026`

## But

Donner a `Claude` une regle de priorisation plus dure que "bonne idee = on la
construit".

Le probleme a eviter:

- construire trop large
- concurrencer des categories deja fortes sans angle de rupture
- diluer les waves sur des modules qui devraient etre des integrations

Le bon cadre est:

- `core now`
- `next moat`
- `future infrastructure`
- `integrate instead of build`
- `not now`

## Regle centrale

Construire seulement ce qui augmente au moins 2 de ces 4 choses:

- valeur cumulative du dossier
- clarte procedurale
- reutilisation de preuve
- dependance utile multi-acteurs

Si une proposition n'augmente pas clairement au moins `2/4`, elle doit
probablement etre:

- une integration
- un partenariat
- ou une idee a reporter

## Core now

Ce sont les couches qui doivent devenir excellentes avant toute expansion
ambitieuse.

### 1. Canonical building workspace

Objets:

- `Building`
- `WorkspaceMembership`
- timeline / activity
- building context
- actor scoping

Pourquoi c'est coeur:

- sans cela, pas de verite partagee
- sans cela, tout le reste flotte

Decision:

- `build deeply`

### 2. Operating inbox / ControlTower

Objets:

- `ControlTower`
- action aggregation
- routing
- assignment
- blockers
- due soon / overdue

Pourquoi c'est coeur:

- c'est l'habitude produit
- c'est l'endroit ou la valeur devient visible quotidiennement

Decision:

- `build deeply`

### 3. Obligations and deadlines

Objets:

- `Obligation`
- recurrence
- deadlines
- escalation

Pourquoi c'est coeur:

- sans deadline unifiee, pas d'operating model fiable

Decision:

- `build deeply`

### 4. Procedure engine

Objets:

- `PermitProcedure`
- `PermitStep`
- `AuthorityRequest`
- blockers proceduraux

Pourquoi c'est coeur:

- c'est encore le gap principal du marche
- c'est ce qui fait passer de `documente` a `proceduralement pret`

Decision:

- `build deeply`

### 5. Proof and delivery layer

Objets:

- packs
- `ProofDelivery`
- provenance
- versions
- acknowledgements

Pourquoi c'est coeur:

- c'est ce qui donne de la valeur institutionnelle et inter-acteurs

Decision:

- `build deeply`

### 6. SwissRules spine

Objets:

- `RuleSource`
- `RuleTemplate`
- `ApplicabilityEvaluation`
- watch / diff / review

Pourquoi c'est coeur:

- sans moteur reglementaire vivant, SwissBuilding ne sera jamais profondement
  suisse ni proceduralement fiable

Decision:

- `build deeply`

### 7. Passport and exchange contract

Objets:

- passport package
- transfer package
- publication package
- import/export discipline

Pourquoi c'est coeur:

- sans contrat d'echange, on reste une app locale

Decision:

- `build now, harden continuously`

## Next moat

Ce sont les couches qui ne sont pas toutes necessaires pour vendre le wedge,
mais qui peuvent creer une superiorite durable.

### 1. Portfolio intelligence grounded in proof

A construire seulement si ancre sur:

- dossiers reels
- obligations
- procedures
- blockers
- pack quality

Ne pas construire:

- un simple scenario planner abstrait

Decision:

- `build selectively`

### 2. Contributor quality and partner trust

Objets:

- contributor signals
- partner trust
- routing hints

Pourquoi c'est moat:

- la qualite reseau peut devenir tres dure a copier

Decision:

- `build selectively`

### 3. Geometry / openBIM / spatial intelligence

Pourquoi c'est moat:

- fort potentiel pour rendre les preuves, blockers et interventions beaucoup
  plus lisibles

Risque:

- devenir un faux outil BIM auteur

Decision:

- `build narrow, integrate broad`

### 4. Benchmarking and learning loops

Pourquoi c'est moat:

- plus il y a de dossiers, plus le produit apprend

Risque:

- analytics sans effet workflow

Decision:

- `build only if explainable and tied to actions`

### 5. Material and circularity intelligence

Pourquoi c'est moat:

- peut faire converger preuve, travaux, produits et valeur residuelle

Risque:

- devenir un module nice-to-have trop tot

Decision:

- `phase after proof/procedure strength`

## Future infrastructure

Ces couches peuvent faire de SwissBuilding une piece du marche, pas seulement
un produit fort.

### 1. Passport Exchange Network

Role:

- standard d'echange de fait

Decision:

- `prepare now, scale later`

### 2. Authority Flow

Role:

- interaction procedurale native avec autorites

Decision:

- `start with bounded submission/response flows`

### 3. Trust Vault / chain of custody

Role:

- conservation, signatures, acknowledgements, delivery evidence

Decision:

- `layer progressively on top of ProofDelivery`

### 4. Territory and public systems coordination

Role:

- contraintes hors batiment
- utilities
- district constraints
- public dependencies

Decision:

- `prepare schema now, productize later`

### 5. Agent operating layer

Role:

- qualification
- verification
- completion
- routing
- requalification

Decision:

- `build as accelerators on canonical objects, not as parallel product logic`

## Integrate instead of build

Ces categories ont de la valeur, mais il est irrationnel de les reconstruire de
front.

### 1. Full property ERP

Exemples:

- comptabilite complete
- loyers
- ledger back office
- payroll
- fiscal back office large

Decision:

- `integrate`

### 2. Generic chantier collaboration suite

Exemples:

- full defect suite
- chantier diary complet
- resource planning chantier
- generic site collaboration platform

Decision:

- `integrate when needed`

### 3. BIM authoring

Exemples:

- model authoring
- full clash coordination
- heavy design collaboration

Decision:

- `do not build`

### 4. Generic DMS / drive replacement

Exemples:

- folders first
- storage-first product
- unstructured document vault

Decision:

- `only build contextual document flows`

### 5. Generic portfolio planning detached from proof

Decision:

- `do not build unless grounded in building truth`

## Not now

Ces zones peuvent etre strategiques plus tard, mais ne doivent pas voler de
focus aujourd'hui.

### 1. Full insurer platform

- garder les packs et evidences
- ne pas devenir assureur software suite

### 2. Full lender stack

- garder la finance readiness
- ne pas devenir core banking workflow

### 3. Full resident super-app

- garder les communications critiques
- ne pas basculer en produit consumer large

### 4. Remediation module (moved to validated axis)

- now an internal BatiConnect module, not deferred
- see `docs/vision-100x-master-brief.md` for strategic details

## Build-vs-integrate test

Avant toute nouvelle wave importante, tester:

### 1. Est-ce un objet canonique du dossier batiment?

Si oui, tendance `build`.

### 2. Est-ce que cela augmente la valeur cumulative du dossier dans le temps?

Si oui, tendance `build`.

### 3. Est-ce que cela augmente la puissance multi-acteurs?

Si oui, tendance `build`.

### 4. Est-ce que le marche a deja des leaders puissants sur cette couche?

Si oui, tendance `integrate`.

### 5. Est-ce que notre differenciation est procedure/preuve/continuite?

Si non, danger de dilution.

## Traduction immediate pour Claude

### A pousser maintenant

- workspace
- obligations
- procedures
- control tower
- proof delivery
- SwissRules
- exchange contracts

### A cadrer sans trop ouvrir

- portfolio intelligence
- partner trust
- geometry intelligence
- learning loops

### A preparer architecturalement

- authority flow
- trust vault
- territory/public systems
- agent operating layer

### A traiter comme integration boundary

- ERP
- chantier suite
- BIM authoring
- generic storage

## Conclusion

Le cap n'est pas:

- `tout construire`

Le cap est:

- `construire la couche canonique`
- `construire la couche procedurale`
- `construire la couche de preuve`
- `construire la couche d'echange`

Puis laisser le reste s'y brancher.
