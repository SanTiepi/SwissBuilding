# SwissRules Regulatory Research Pack

Date de controle: `25 mars 2026`

## But

Transformer la recherche juridique et procedurale suisse en matiere exploitable
pour `SwissBuilding`, sans la laisser sous forme de notes dispersées.

Ce document est volontairement oriente produit:

- quelles couches reglementaires existent
- quelles sources officielles doivent etre surveillees
- quelles implications produit elles ont
- quels gaps restent a couvrir

## Couches reglementaires a modeliser

### 1. Federal

- amenagement du territoire et hors zone a batir
  - ARE hors zone a batir: <https://www.are.admin.ch/fr/horszone>
  - ARE LAT/OAT: <https://www.are.admin.ch/fr/newnsb/j4neypyAUUfxheQESMmda>
  - implication produit:
    - `PermitProcedure`
    - `ControlTower` procedural blockers
    - review manuelle pour hors zone et cas hybrides

- environnement, dechets, polluants
  - BAFU OLED: <https://www.bafu.admin.ch/fr/oled>
  - BAFU droit dechets: <https://www.bafu.admin.ch/bafu/fr/home/themes/dechets/droit/lois-ordonnances.html>
  - BAFU PCB dans les joints: <https://www.bafu.admin.ch/fr/masses-detancheite-des-joints>
  - implication produit:
    - `regulatory_filing`
    - classification dechets
    - preuves de filiere et de destination

- radon
  - BAG protection contre le radon: <https://www.bag.admin.ch/fr/protection-contre-le-radon>
  - BAG bases legales radon: <https://www.bag.admin.ch/fr/dispositions-legales-concernant-le-radon>
  - implication produit:
    - obligation ou review radon selon contexte
    - blocker readiness si mesure ou mitigation manquante

- securite chantier / amiante
  - SUVA amiante: <https://www.suva.ch/fr-ch/prevention/matieres-substances/amiante>
  - CFST 6503: <https://www.ekas.admin.ch/fr/directive-cfst-6503-directive-amiante-mise-a-jour>
  - implication produit:
    - `regulatory_filing` SUVA
    - worker protection plan
    - lien direct diagnostic -> procedure -> preuve

### 2. Intercantonal

- energie
  - EnDK / MoPEC: <https://www.endk.ch/fr/politique-energetique/mopec>
  - implication produit:
    - justification energie dans le dossier
    - pont entre passeport, travaux et procedure

- incendie
  - VKF / AEAI: <https://www.vkf.ch/>
  - implication produit:
    - review incendie pour usages sensibles
    - concept incendie dans les packs autorite

### 3. Cantonal

- Vaud
  - CAMAC / permis: <https://www.vd.ch/territoire-et-construction/permis-de-construire>
- Geneve
  - autorisation de construire: <https://www.ge.ch/demander-autorisation-construire>
- Fribourg
  - SeCA: <https://www.fr.ch/territoire-amenagement-et-constructions/territoire/seca-presentation-du-service>

Implication produit:

- adapters cantonaux
- routage vers l’autorite competente
- variantes de depot et de pieces
- demandes de complements et accusés

### 4. Communal

Realite importante:

- il n’existe pas de flux unique national pour les reglements communaux
- il faut une couche `communal adapter`
- fallback obligatoire: `manual_review`

Ce niveau couvre notamment:

- affectation locale
- gabarits
- integration/esthetique
- stationnement
- restrictions de quartier
- patrimoine local
- taxes/reseaux/exigences de depot locales

### 5. Registres et restrictions publiques

- RegBL / EGID
  - OFS RegBL: <https://www.delimo.bfs.admin.ch/fr/index.html>
- cadastre RDPPF / restrictions de droit public
  - cadastre RDPPF: <https://www.cadastre.ch/fr/cadastre-rdppf>

Implication produit:

- verifier l’identite officielle du batiment
- relier `EGID` et contraintes parcelle / bien-fonds
- eviter les erreurs de dossier et de matching

### 6. Patrimoine, sites et accessibilite

- ISOS / protection des sites
  - BAK ISOS et protection des sites: <https://www.bak.admin.ch/bak/fr/home/baukultur/isos-und-ortsbildschutz.html>
- accessibilite
  - LHand / BFEH: <https://www.ebgb.admin.ch/fr/loi-sur-legalite-pour-les-personnes-handicapees-lhand>

Implication produit:

- cas a revue manuelle structurelle
- justification supplementaire dans le dossier
- contraintes d’usage et d’exploitation

### 7. Dangers naturels et eaux souterraines

- dangers naturels
  - BAFU faire face aux dangers naturels: <https://www.bafu.admin.ch/bafu/fr/home/themes/dangers-naturels/umgang-mit-naturgefahren.html>
- protection des eaux souterraines
  - BAFU zones de protection des eaux souterraines: <https://www.bafu.admin.ch/dam/fr/sd-web/MagXxADIZu1m/grundwasserschutzzonenbeilockergesteinen%2520%283%29.pdf>

Implication produit:

- blocage ou review specifique en zone exposee
- procedure ou piece supplementaire
- couplage avec RDPPF/geodata

## Ce qui doit devenir explicable dans l'app

Pour chaque action, blocage ou obligation, `SwissBuilding` doit pouvoir montrer:

- la juridiction concernee
- la source officielle
- la date/version de la source si connue
- la force normative:
  - loi
  - ordonnance/reglement
  - directive officielle d’execution
  - standard intercantonal
  - standard prive
  - label
- la condition d’applicabilite
- la preuve attendue
- l’autorite competente

## Gaps de recherche encore ouverts

- couverture communale detaillee
- heritage / monuments par canton et commune
- accessibilite selon type d’usage et seuils d’application
- services et formulaires cantonaux supplementaires hors `VD/GE/FR`
- contraintes reseaux / utilities / concessionnaires
- zones de protection, dangers naturels et geodata exploitables de facon stable
- subventions / aides / programmes publics par canton
- cas speciaux:
  - ecoles
  - hopitaux
  - industriel
  - agricole
  - telecom
  - grandes infrastructures

## Consequences produit immediates

- ne jamais traiter la regulation comme un simple texte; il faut des sorties produit:
  - `ApplicabilityEvaluation`
  - `RequirementTemplate`
  - `ProcedureTemplate`
  - `Obligation`
  - `ControlTower action`
- la surveillance doit couvrir:
  - textes
  - portails
  - formulaires
  - directives d’execution
- la bonne architecture est:
  - `source -> snapshot -> impact review -> rule template -> procedure/obligation/action/proof`
