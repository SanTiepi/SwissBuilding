# BatiConnect - Manifeste du produit ultime

Date de reference: `28 mars 2026`

## Comment utiliser ce document

Ce document sert de north star produit.

Il est fait pour:
- clarifier la vision ultime de BatiConnect
- donner un cadre transmissible a `Claude`
- pousser l'ambition tres loin sans brouiller le wedge actuel
- separer la promesse visible aujourd'hui de l'horizon complet du produit

Interpretation importante:
- ce document ne change pas le wedge commercial court terme
- il ne dit pas que tout doit etre expose maintenant
- il fixe ce que l'application peut devenir si on garde une spine canonique unique

Le wedge visible reste:
- `VD/GE`
- dossiers polluants pre-travaux
- gerances multi-batiments
- `readiness layer + proof engine`

Mais cette entree n'est qu'une porte d'acces.

## Documents du repo a croiser avec ce manifeste

Ce manifeste est la version la plus transmissible de la vision produit.

Il doit etre lu avec les documents deja existants qui poussent certains axes plus loin:

- `docs/vision-100x-master-brief.md`
  - vision categorie, anneaux strategiques, scope map 12 macro-domaines
- `docs/product-frontier-map.md`
  - frontier complet, engines majeurs, uses deja couverts vs encore manquants
- `docs/projects/swissbuilding-10-15-20-year-vision-and-synergy-map-2026-03-25.md`
  - trajectoire 10/15/20 ans, standards d'echange, outils complementaires
- `docs/projects/openbim-digital-logbook-and-passport-convergence-program.md`
  - convergence `openBIM`, `IFC`, `BCF`, `IDS`, digital logbook, renovation passport
- `docs/projects/semantic-building-operations-and-systems-program.md`
  - systemes techniques, operations semantiques, bridge vers `Brick` / `Haystack`
- `docs/projects/permit-procedure-and-public-funding-program.md`
  - procedure permis, subventions, blockers proceduraux
- `docs/projects/transaction-insurance-finance-readiness-program.md`
  - readiness `safe_to_sell`, `safe_to_insure`, `safe_to_finance`
- `docs/projects/legal-grade-proof-and-chain-of-custody-program.md`
  - chaine de garde, archivage, signatures, accuses, version canonique
- `docs/projects/ecosystem-network-and-market-infrastructure-program.md`
  - contributor exchange, API/webhooks, delta monitoring, network learning
- `docs/projects/partner-network-and-contributor-reputation-program.md`
  - qualite partenaires, trust profiles, routing et fairness controls

Regle de lecture:
- ce manifeste donne la forme generale la plus claire
- les autres docs donnent de la profondeur specialisee
- aucune de ces pieces ne doit contredire la spine canonique du produit

## Vision centrale

BatiConnect doit devenir l'application que n'importe quel proprietaire, gerance, ou operateur reve d'avoir pour comprendre, faire vivre, proteger, transformer et transmettre un batiment.

Le produit ultime n'est pas:
- un outil de diagnostics
- un meilleur drive
- un ERP overlay seulement
- un simple dashboard reglementaire
- une marketplace travaux

Le produit ultime est:

**le systeme pratique du batiment vivant**

Il doit:
- comprendre ce qu'est le batiment
- comprendre ce qu'il contient
- comprendre ce qu'on veut lui faire
- comprendre quelles regles s'appliquent
- preparer les actions utiles
- generer les bons dossiers
- faire circuler les bons packs
- recuperer les retours
- garder la memoire de tout
- rendre l'actif plus lisible, plus pilotable et plus transmissible avec le temps

La phrase la plus haute du produit est:

**rendre un batiment non opaque**

Ou, de maniere encore plus concrete:

**prendre un batiment mal compris, le transformer en verite exploitable, puis en actions reelles, puis en memoire durable**

## La promesse ultime au proprietaire

L'application ultime doit donner au proprietaire six capacites permanentes:

### 1. Comprendre

Savoir a tout moment:
- ce qu'est le batiment
- quel est son etat
- quels sont ses risques
- ce qui manque
- ce qui a ete fait
- ce qui n'est pas encore prouve

### 2. Anticiper

Voir avant les problemes:
- ce qui va expirer
- ce qui va couter
- ce qui va bloquer
- ce qui doit etre renouvele
- ce qui devient urgent a 30 / 90 / 365 jours

### 3. Agir

Lancer sans repartir de zero:
- un dossier autorite
- une demande d'offres
- un pack assureur
- une intervention
- une transmission a un acheteur, notaire, gerance, syndic ou expert

### 4. Decider

Arbitrer plus vite:
- urgence
- cout
- sequence des travaux
- couverture assurance
- timing d'une intervention
- comparaison de devis
- priorites du portefeuille

### 5. Prouver

Montrer immediatement:
- la bonne piece
- la bonne version
- la bonne source
- la bonne date
- le bon historique de transmission

### 6. Transmettre

Permettre que le batiment survive aux changements:
- de gerance
- de proprietaire
- d'assureur
- d'artisan
- de procedure
- de cycle de vie

Le reve produit n'est donc pas juste "plus de gestion".
Le reve produit est:
- moins d'angoisse
- moins de paperasse
- moins de perte de memoire
- moins d'angles morts
- plus de controle
- plus de pouvoir d'agir

## Le noyau canonique non negociable

Si BatiConnect veut aller tres loin sans se fragmenter, tout doit se brancher sur le meme noyau.

La spine canonique est:

`batiment -> parcelle -> zones -> elements -> materiaux -> systemes -> preuves -> regles -> interventions -> etat -> actions -> packs -> memoire`

### Objets centraux

- `Building`
- `Parcel / Site`
- `Zone / Level / Room / Space`
- `BuildingElement`
- `MaterialLayer / MaterialAssembly`
- `TechnicalSystem`
- `Document / Plan / Form / Quote / Evidence`
- `EvidenceLink / Provenance / Version`
- `RegulatoryLayer / Procedure / Requirement / FormTemplate`
- `Intervention / WorkScope / Project`
- `ReadinessState / CompletenessState / TrustState`
- `Action / Deadline / Request / Follow-up`
- `AudiencePack / Submission / Delivery / Receipt`
- `Snapshot / Timeline / PostWorksTruth`

Regle absolue:
- toute nouvelle fonctionnalite doit enrichir ce noyau
- aucune famille de features ne doit creer une deuxieme verite parallele

## Les 8 grandes boucles du produit ultime

Le produit doit etre pense en boucles pratiques, pas seulement en modules.

### Boucle 1 - Faire entrer un batiment

Declencheur:
- nouveau mandat
- acquisition
- nouveau bien dans le portefeuille
- batiment ancien mal documente

Sortie attendue:
- un `premier batiment vivant` en quelques minutes

Le systeme:
- resout l'identite (`EGID`, adresse, parcelle)
- enrichit automatiquement
- ingere les documents
- extrait les donnees structurantes
- cree une baseline `passport + completude + readiness`

### Boucle 2 - Savoir si le dossier est pret

Declencheur:
- soumission
- appel d'offres
- lancement de chantier
- revue interne

Sortie attendue:
- `pret / pas pret / pret sous conditions`
- avec raisons, preuves, angles morts et prochaines actions

### Boucle 3 - Lancer un projet de travaux

Declencheur:
- besoin d'intervenir
- renovation
- assainissement
- maintenance lourde
- remplacement systeme

Sortie attendue:
- un projet cree avec perimetre, zones, elements, materiaux, obligations et pieces deja prepares

### Boucle 4 - Generer et faire circuler une demande d'offres

Declencheur:
- dossier assez mature pour consulter des entreprises

Sortie attendue:
- un `RFQ draft` pre-rempli, envoye proprement, suivi, recu et comparable

Le systeme:
- pre-remplit la demande
- attache les bonnes pieces
- route vers un panel verifie
- recoit les retours
- extrait les devis PDF
- compare les reponses sur une base homogene

### Boucle 5 - Executer la couche reglementaire

Declencheur:
- une procedure exige un depot, un formulaire, un complement ou une validation

Sortie attendue:
- des formulaires pre-remplis
- les bonnes pieces
- un etat de soumission clair
- une trace de reception et de complement

### Boucle 6 - Faire circuler des packs vers les bons acteurs

Declencheur:
- autorite
- assureur
- entreprise
- notaire
- acheteur
- syndic
- financeur

Sortie attendue:
- un pack adapte a l'audience, avec redaction, preuve, provenance, et suivi d'envoi

### Boucle 7 - Mettre a jour la verite post-travaux

Declencheur:
- fin d'intervention
- nouvelle attestation
- reception travaux
- confirmation duale

Sortie attendue:
- un `post-works truth`
- un avant/apres
- une mise a jour du passport, du trust et de la memoire

### Boucle 8 - Faire vivre le batiment et le portefeuille

Declencheur:
- vie courante du batiment
- renouvellements
- incidents
- claims
- garanties
- campagnes
- arbitrages budgetaires

Sortie attendue:
- une gestion active du batiment et du portefeuille dans le temps

## Les couches reglementaires et operationnelles

Le produit ultime doit integrer des couches reglementaires reelles et executables.

Pas juste des regles affichees.
Pas juste des liens vers des textes.

Il faut modeliser:
- la couche federale
- la couche cantonale
- la couche communale
- les organismes d'execution
- les labels et standards utiles
- les variantes de procedure
- les formulaires
- les pieces requises
- les cas ambigus
- les points de revue manuelle

Le systeme doit savoir:
- quelles regles s'appliquent
- a quel type de projet
- sur quelles zones, materiaux, systemes ou contextes
- quels formulaires et pieces sont requis
- quels delais, circuits, preavis et complements existent

### Formulaires pre-remplis

C'est une couche centrale du produit ultime.

L'app doit pouvoir:
- identifier les formulaires applicables
- pre-remplir les champs a partir du batiment et du projet
- attacher les bonnes pieces
- signaler ce qui manque
- versionner le formulaire utilise
- garder la source de chaque champ
- enregistrer l'envoi, la reception, les complements et les re-soumissions

Types de formulaires a viser dans le temps:
- autorite / permis / declarations
- polluants
- securite chantier / SUVA
- dechets / tracabilite / filieres
- assureur / underwriting / renouvellement
- subventions
- transmission / notaire / vente / due diligence

Regles non negociables:
- aucune fausse automatisation
- `manual_review_required` quand le cas est ambigu
- source officielle + date de revue
- aucun verdict sans provenance explicable

## Les 10 surfaces maitresses de l'application ultime

Le produit ultime doit rester simple en facade et profond a la demande.

### 1. Aujourd'hui

L'ecran qu'on ouvre tous les jours.

Il repond a:
- qu'est-ce qui demande une action maintenant ?
- qu'est-ce qui va me tomber dessus bientot ?
- qu'est-ce qui est bloque ?

### 2. Mon batiment

Le cockpit vivant du batiment:
- etat
- readiness
- risques
- preuves
- historique
- prochaines actions

### 3. Mon projet

Le cockpit d'une intervention ou d'un programme de travaux:
- perimetre
- zones
- pieces
- obligations
- progression

### 4. Readiness Room

Le lieu ou l'on voit:
- ce qui est pret
- ce qui manque
- pourquoi
- ce qu'il faut faire maintenant

### 5. Forms Workspace

Le cockpit de formulaires et procedures:
- formulaires applicables
- niveau de pre-remplissage
- champs manquants
- variantes locales
- historique de soumission

### 6. RFQ & Quotes

Le cockpit demande d'offres:
- RFQ
- panel verifie
- invitations
- retours
- extraction devis
- comparaison
- attribution

### 7. Pack Builder & Delivery

Le lieu ou l'on genere et suit:
- authority pack
- owner pack
- insurer pack
- contractor pack
- transfer pack

### 8. Building Life

Le cockpit de vie continue:
- garanties
- assurances
- renouvellements
- incidents
- contrats
- echeances
- post-travaux

### 9. Material & Element Explorer

Le lieu d'exploration du batiment physique:
- zones
- elements
- couches materielles
- risques
- etat
- preuves liees

### 10. Portfolio Command Center

Le cockpit de direction:
- urgences
- readiness
- cout a venir
- campagnes
- mutualisations
- arbitrages 30 / 90 / 365 jours

## Les services pratiques ultimes

Pour etre "plus facile mais plus complet", le produit doit sur-indexer les services suivants:

- `nouveau batiment en 10 minutes`
- baseline immediate `passport + completude + readiness`
- inbox intelligente orientee actions
- wizard `lancer un projet`
- formulaires pre-remplis
- `authority complement inbox`
- `RFQ draft -> envoi -> retour -> comparaison`
- extraction structuree de devis
- `insurer / owner / transfer packs`
- calendrier de garanties / assurances / obligations
- `annual building review`
- mise a jour post-travaux assistee
- transmission propre a un nouvel acteur

Ces services doivent rendre la complexite invisible.
L'utilisateur ne doit pas sentir un produit "plus gros".
Il doit sentir un produit qui porte la charge a sa place.

## Principes non negociables

### 1. Aucun verdict sans provenance explicable

Chaque score, statut, formulaire pre-rempli ou recommandation de prochaine action doit montrer:
- d'ou cela vient
- avec quel niveau de confiance
- quelle part est verifiee, declaree, inferee ou manquante

### 2. Simple par defaut, profond a la demande

L'application doit toujours avoir:
- un niveau simple
- un niveau operationnel
- un niveau preuve / expert

### 3. Les intentions avant les modules

On n'entre pas dans l'app pour "ouvrir une fonctionnalite".
On y entre pour:
- comprendre
- verifier
- lancer
- envoyer
- comparer
- transmettre

### 4. Une preuve saisie une fois doit servir plusieurs fois

Une piece ou information utile doit etre reutilisable:
- pour l'autorite
- pour un RFQ
- pour l'assureur
- pour le notaire
- pour le post-travaux
- pour la memoire batiment

### 5. Pas de faux marketplace

Pour les artisans et prestataires:
- oui a la mise en concurrence encadree
- oui au pre-remplissage et a la comparaison
- non a la recommandation opaque
- non au ranking influence par paiement

### 6. Toujours convertir un probleme en action

Un trou non actionnable est une frustration.
Chaque manque, contradiction ou risque doit mener a:
- une relance
- une demande
- un formulaire
- une correction
- un envoi
- une decision

## Vision future - ce que l'application peut devenir

### Horizon 1 - Application indispensable du batiment

Le produit devient l'application qu'un proprietaire ou une gerance ouvre chaque semaine pour:
- savoir ou en sont ses batiments
- anticiper les problemes
- lancer les actions utiles
- transmettre les bons dossiers

### Horizon 2 - OS du batiment vivant

Le produit devient:
- le passport vivant du batiment
- le journal de verite du bati
- le centre de procedure
- le moteur de transmission des packs
- le cockpit de vie continue du batiment

### Horizon 3 - Couche d'execution reglementaire

Le produit devient un `regulatory execution OS`:
- procedures
- formulaires
- variantes cantonales et communales
- complements
- circuits de soumission
- preuves liees

### Horizon 4 - Couche d'orchestration des travaux et acteurs

Le produit devient la couche qui:
- prepare les demandes d'offres
- structure les reponses
- facilite la comparaison
- relie l'attribution au post-travaux
- apprend de la qualite des contributions

### Horizon 5 - Systeme de pilotage proprietaire et portefeuille

Le produit devient un copilote de:
- valeur
- risque
- CAPEX
- assurance
- maintenance
- transmission
- mutualisation a l'echelle d'un parc

### Horizon 6 - Infrastructure de marche du batiment non opaque

Le produit peut, a terme, devenir:
- la couche de verite partagee du bati
- la couche de memoire transmissible
- la couche d'echange entre proprietaires, gerances, artisans, assureurs, autorites, acheteurs et financeurs

Pas une promesse commerciale immediate.
Mais une direction de reference pour l'architecture et les paris produit.

## Axes long terme deja documentes et a ne pas oublier

Le manifeste central doit rester lisible.
Mais la vision complete du produit inclut deja, ailleurs dans le repo, les axes suivants.

### 1. Owner, household, et everyday ops

L'application peut aller au-dela des projets ponctuels et devenir utile en continu pour:
- contrats de services recurrents
- utilites et compteurs
- factures recurrentes
- SLA de maintenance
- renouvellements
- revue annuelle du batiment

L'enjeu:
- que le produit serve aussi entre deux gros travaux
- que la memoire de cout, de fournisseur et de dependance ne reparte jamais a zero

### 2. Resident, occupant, et co-ownership

L'app ne doit pas penser seulement "proprietaire unique".

Il faut garder la place pour:
- securite occupant
- notices bornees avant / pendant / apres intervention
- acknowledgement et delivery tracking
- co-propriete / PPE
- votes, resolutions, gouvernance collective

L'enjeu:
- rendre l'application credible dans les batiments reels, pas seulement dans les schemas simples

### 3. Assurance, transaction, finance, fiscalite, subventions

Le dossier ne sert pas seulement a faire des travaux.
Il peut devenir un moteur de readiness pour:
- vente
- acquisition
- due diligence
- assurance
- refinancement
- fiscalite
- subventions et financement public

L'enjeu:
- transformer la qualite du dossier en valeur economique et institutionnelle directe

### 4. Utility, territoire, et public systems

Certains blockers ne vivent pas dans le batiment.

Il faut garder la place pour:
- interruptions utilites
- contraintes reseaux
- contexte district / quartier
- dependances publiques
- modes d'exploitation public-owner
- revue municipale ou comite

L'enjeu:
- faire monter le produit du "building OS" vers une vraie couche built-environment

### 5. openBIM, plans, geometie, logbook, passeport exportable

Le batiment vivant doit pouvoir converger avec:
- `IFC`
- `BCF`
- `IDS`
- digital building logbook
- renovation passport
- openBIM et geometry intelligence

L'enjeu:
- ne pas rester un modele proprietaire ferme
- rendre le passeport exportable, interrogeable et europe-ready

### 6. Materiaux, circularite, et systemes techniques

Le produit ne doit pas s'arreter aux polluants.

Il doit pouvoir comprendre:
- couches materielles
- provenance
- fin de vie
- reutilisation
- systemes techniques
- equipements
- relations systeme-zone-plan

L'enjeu:
- relier le batiment physique, les travaux, les risques et les operations futures

### 7. Energie, carbone, performance et donnees live

Le dossier statique peut devenir un cockpit de performance recurrente:
- energy state
- carbon state
- performance snapshots
- drift signals
- meter feeds
- sensor windows

L'enjeu:
- passer d'une verite statique a une intelligence vivante du batiment

### 8. Chaine de preuve legale et trust institutionnel

La preuve ne doit pas etre seulement visible.
Elle doit devenir difficile a contester.

Il faut garder la place pour:
- version canonique d'un pack
- lineage
- content hash
- custody events
- delivery receipts
- acknowledgement records
- archive posture
- signature / seal hooks

L'enjeu:
- rendre les exports et transmissions defendables en contexte autorite, assurance, litige ou transaction

### 9. Ecosysteme, exchange, network effects

Le produit peut devenir plus qu'un outil local s'il structure les echanges.

Il faut garder la place pour:
- contributor uploads
- partner APIs / webhooks
- exchange contracts
- publications / receipts
- public-data delta monitoring
- requalification apres changement
- partner trust profiles
- routing plus intelligent mais explicable

L'enjeu:
- faire de SwissBuilding un point de passage naturel plutot qu'un simple coffre interne

### 10. Agent operating layer

L'IA ne doit pas seulement "assister".
Elle peut devenir une couche d'orchestration specialisee et invisible:
- extraction
- verification
- contradiction detection
- routing
- comparaison devis
- requalification
- simulations
- research sur sources reglementaires

L'enjeu:
- rendre la plateforme beaucoup plus rapide et proactive qu'un outil statique
- sans jamais casser le principe `aucun verdict sans provenance explicable`

## Comment Claude doit l'interpreter

Pour `Claude`, ce document doit etre lu comme suit:

- construire loin est autorise
- proposer activement des expansions generiques est voulu
- ne pas freiner l'ambition par peur d'etre "trop complet"
- mais ne jamais casser la spine canonique
- ne jamais remplacer le wedge actuel par une dispersion confuse

Regle d'interpretation:
- on peut construire large
- on peut construire profond
- on peut anticiper bas niveau et objets metier
- mais toute expansion doit se brancher proprement sur:
  - batiment
  - preuves
  - regles
  - interventions
  - etat
  - actions
  - memoire

En resume:

**le wedge court terme est la porte**

**le produit ultime est le systeme pratique, reglementaire, operationnel et memoire du batiment vivant**
