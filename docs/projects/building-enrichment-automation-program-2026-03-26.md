# Building Enrichment Automation Program

Date de controle: `26 mars 2026`

## Mission

Automatiser beaucoup plus agressivement le remplissage des dossiers batiment existants
sans melanger:

- la verite officielle
- l'observation visuelle
- l'inference IA

Le but n'est pas de "faire joli plus vite".
Le but est de produire plus vite un dossier batiment defensible, explicable et
pilotable.

## Pourquoi maintenant

Le socle actuel le permet deja:

- le modele `Building` peut deja porter `egid`, `egrid`, `official_id`,
  `parcel_number`, geometrie, annees, surfaces et `source_metadata_json`
- le repo a deja une premiere ingestion publique avec
  `backend/app/importers/vaud_public.py`
- le spine suisse connait deja `RegBL` et `cadastre RDPPF`
- le produit sait deja versionner, tracer la custody chain et exposer des surfaces
  decision-grade

Le bon move n'est donc pas d'ajouter une nouvelle surface produit.
Le bon move est de monter une machine d'enrichissement par couches.

## Regles du systeme

1. `egid`, `egrid`, `official_id` ne sont jamais interchangeables
2. une donnee officielle gagne toujours contre une inference ou un signal visuel
3. toute donnee derivee garde `source`, `captured_at`, `freshness`, `confidence`
4. toute sortie IA porte `ai_generated=true`
5. pas de scraping d'UI si une API officielle, un bulk dump, un webservice ou un
   download dataset existe
6. tout enrichissement est idempotent et rejouable

## La pile d'autoremplissage cible

### Couche 1 - Resolution d'identite canonique

Objectif:

- partir d'une adresse, d'un EGID, d'un EGRID, d'un numero de parcelle ou d'un
  point sur la carte
- retomber sur une identite batiment stable et reconciliee

Champs a remplir en priorite:

- `egid`
- `egrid`
- `official_id`
- adresse normalisee
- `municipality_ofs`
- `postal_code`, `city`, `canton`
- `latitude`, `longitude`, `geom`
- `parcel_number`

Sources a privilegier:

- `geo.admin SearchServer` pour resolution adresse -> couches officielles
- `RegBL / MADD` pour EGID, entrees, attributs publics batiment
- `cadastre RDPPF / EGRID` pour l'ancrage parcellaire

### Couche 2 - Remplissage structurel deterministe

Objectif:

- remplir automatiquement ce qui peut l'etre sans interpretation humaine

Champs typiques:

- annee de construction
- type de batiment
- nombre d'etages
- surface
- volume si disponible
- empreinte et geometrie 2D/3D

Sources a privilegier:

- `RegBL / MADD`
- importeurs cantonaux type Vaud
- `swissBUILDINGS3D`
- jeux cantonaux de footprints / surfaces quand ils sont plus riches

### Couche 3 - Contexte parcellaire et reglementaire

Objectif:

- pre-remplir le dossier "decision-grade" sans attendre une recherche manuelle

Signaux typiques:

- restrictions RDPPF
- servitudes / contraintes publiques exposees
- contexte communal / cantonal
- couches hazards
- bruit
- eau / groundwater
- couches energie / solaire si disponibles

Sortie attendue:

- blocs de contexte attaches au batiment
- blockers / conditions explicables
- liens directs vers la source publique et l'extrait

### Couche 4 - Observation visuelle

Objectif:

- voir le batiment sans demander tout de suite une visite terrain

Sources prioritaires:

- `swissimage` / orthophoto officielle pour la vue aerienne
- `swissBUILDINGS3D` pour la forme du toit, volumes, pente et envelopes
- Google Street View pour la vue rue si couverture disponible
- Mapillary comme backup communautaire de vue rue quand utile
- photos deja presentes dans les dossiers, rapports et packs

Important:

- l'imagerie n'est pas une source d'identite canonique
- c'est une couche d'observation

### Couche 5 - Inference IA assistee

Objectif:

- extraire des hypotheses utiles a partir des images et documents

Exemples:

- etat apparent de facade
- presence visible de fissures, vegetations parasites, humidite exterieure
- typologie de toiture
- presence probable de panneaux solaires
- indices de renovation apparente
- nombre d'ouvertures / balcons / extensions visibles
- cues sur l'epoque constructive quand la source officielle est absente

Important:

- ces sorties restent des `claims`, pas des verites source
- elles doivent etre reviewables et corrigeables

## Ordre d'automatisation recommande

### Lot A - Backbone identite + verite publique

But:

- rendre chaque batiment resolvable proprement avant toute magie IA

A livrer:

- `BuildingIdentityResolutionService`
- pipeline adresse -> `geo.admin` -> `RegBL/MADD` -> `RDPPF/EGRID`
- strategy de matching et de conflict resolution
- snapshots de source avec provenance et freshness
- score de confiance par champ, pas seulement par batiment

Resultat:

- un dossier vide devient un dossier deja ancre, geo-localise et partiellement
  renseigne en quelques secondes

### Lot B - Imagerie evidence layer

But:

- brancher une couche visuelle systematique et propre

A livrer:

- `ImageryIngestionService`
- manifest d'assets images par batiment
- thumbnails / previews / metadata / dates / provider
- fallback tree:
  - orthophoto officielle d'abord
  - street-level ensuite
  - photos terrain ensuite
- policy claire de stockage:
  - stocker les references, metadata et derives par defaut
  - ne stocker le raw que si la licence le permet

Resultat:

- chaque batiment peut ouvrir sur une vue aerienne + une vue rue quand la
  couverture existe

### Lot C - Derived claims engine

But:

- transformer documents + images en hypotheses utiles, sans polluer la verite

A livrer:

- `BuildingObservation`
- `DerivedClaim`
- `ObservationEvidenceLink`
- jobs CV/LLM sur imagerie et pieces du dossier
- confidence, review state, correction loop vers `ai_feedback`

Resultat:

- on remplit les trous du dossier par hypotheses visibles et auditables

### Lot D - Decision-grade overlays

But:

- convertir l'enrichissement en vraie acceleration de decision

A livrer:

- auto-preload des restrictions RDPPF et couches geoadmin pertinentes
- resume des blockers potentiels par audience:
  - authority
  - insurer
  - lender
  - transaction
- refresh cadence par type de source
- timeline events quand une source publique change

Resultat:

- le cockpit decision ne part plus de zero

## Comment utiliser Google sans faire n'importe quoi

Google est utile, mais pas comme source canonique.

A utiliser pour:

- imagery rue
- metadata de panorama
- fallback geocoding quand la resolution officielle echoue
- potentiel solaire en couche optionnelle d'observation

A ne pas faire:

- traiter Google comme source de verite identitaire suisse
- stocker des identifiants transitoires comme si c'etaient des identifiants
  metier
- scraper des captures d'ecran de l'UI Maps

Bonne pratique:

- garder les coordonnees comme ancrage persistant
- utiliser l'API metadata avant l'image pour tester la couverture
- afficher l'attribution requise par provider
- suivre les contraintes de quota et de stockage du provider

## Modele de donnees recommande

Sans casser le modele `Building`, ajouter des couches autour:

- `building_identity_snapshot`
- `building_source_snapshot`
- `building_imagery_asset`
- `building_observation`
- `building_derived_claim`
- `building_enrichment_run`

Chaque objet doit savoir:

- d'ou il vient
- quand il a ete capture
- sur quel batiment / parcelle il s'ancre
- s'il est officiel, observe ou derive
- s'il est accepte, rejete ou obsolete

## Impact produit attendu

Si cette pile est bien executee:

- creation d'un dossier batiment beaucoup plus rapide
- moins de saisie manuelle repetitive
- meilleurs demos et pilotes sur stock existant
- meilleure qualite des blockers / conditions des le premier passage
- meilleur feed pour la boucle IA sans casser la confiance

## Source anchors

Sources officielles et providers a brancher en priorite:

- `geo.admin / Search + geoservices`
  - <https://api3.geo.admin.ch/services/sdiservices.html#search>
- `FSO / Building and Dwelling Register`
  - <https://www.bfs.admin.ch/bfs/en/home/registers/buildings-dwellings.html>
- `MADD public access`
  - <https://www.housing-stat.ch/en/madd/public.html>
- `cadastre RDPPF`
  - <https://www.cadastre.ch/en/cadastre-rdppf.html>
- `cadastre EGRID services`
  - <https://www.cadastre.ch/en/manual-av/services/egrid.html>
- `swisstopo swissBUILDINGS3D`
  - <https://www.swisstopo.admin.ch/en/height-model-swissbuildings3d>
- `swisstopo swissBUILDINGS3D 3.0 beta`
  - <https://www.swisstopo.admin.ch/en/landscape-model-swissbuildings3d-3-0-beta>
- `Google Street View Static API`
  - <https://developers.google.com/maps/documentation/streetview/overview>
- `Google Street View metadata`
  - <https://developers.google.com/maps/documentation/streetview/metadata>
- `Google Geocoding API`
  - <https://developers.google.com/maps/documentation/geocoding/overview>
- `Google Solar API`
  - <https://developers.google.com/maps/documentation/solar/overview>
- `Mapillary developers`
  - <https://help.mapillary.com/hc/en-us/categories/17361771500956-Mapillary-for-Developers>
- `Mapillary derived metadata rules`
  - <https://help.mapillary.com/hc/en-us/articles/115001777705-OpenStreetMap-compatibility>

## Recommandation nette

Ne pas commencer par la computer vision pure.

Commencer par:

1. identite canonique multi-source
2. geodata et contexte parcellaire
3. couche imagerie evidence
4. derives IA reviewables

Autrement dit:

`official truth -> observed evidence -> derived claims -> operator confirmation`

Pas l'inverse.
