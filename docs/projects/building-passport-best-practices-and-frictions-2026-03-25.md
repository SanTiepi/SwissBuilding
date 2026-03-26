# Building Passport Best Practices and Frictions

Date de controle: `25 mars 2026`

## But

Donner a `Claude` un pack de reference produit qui transforme la recherche en
decisions de design et d’execution.

## Ce que le produit doit faire de l'information

Le produit ne doit pas seulement `regrouper` l'information.

Il doit la rendre:

- utilisable
- comprehensible
- lisible
- mise en valeur
- mise en synergie avec le reste du dossier

La bonne chaine de valeur est:

`information brute -> evidence contextualisee -> exigence comprise -> action
priorisee -> procedure executable -> pack reutilisable -> memoire durable`

Implication produit:

- un document seul n'a pas assez de valeur
- une timeline seule n'a pas assez de valeur
- une checklist seule n'a pas assez de valeur

La vraie valeur apparait quand le systeme sait:

- pourquoi c'est important
- pour qui c'est important
- ce que ca debloque
- ce que ca risque si on ne le traite pas
- comment le reutiliser ailleurs

## La barre produit a tenir

### 1. Toute information importante doit avoir un usage clair

Usage minimal attendu:

- expliquer
- declencher une action
- satisfaire une exigence
- alimenter un pack
- enrichir la memoire du batiment

### 2. Toute information importante doit etre lisible a plusieurs niveaux

Le meme contenu doit pouvoir exister en:

- resume lisible
- detail exploitable
- preuve source

### 3. Toute information importante doit etre reliee au reste

Elle doit pouvoir se raccrocher a:

- un batiment
- une procedure
- une obligation
- une audience
- une deadline
- une version

### 4. Toute information importante doit produire un effet produit

Exemples:

- un diagnostic publie cree des blockers ou leve des blockers
- un complement autorite cree une action prioritaire
- un document qualifie alimente un pack et une procedure
- une regle applicable ouvre une obligation ou une revue

### 5. Toute information importante doit pouvoir etre reexpliquee facilement

Le produit doit permettre de dire:

- ce que c'est
- pourquoi c'est la
- ce qu'on en fait
- qui doit agir
- ou on en est
- quelle est la source

## Frictions a tuer en priorite absolue

### 1. Procedure invisible

Les utilisateurs ont des documents, mais ne savent pas si le dossier peut
reellement avancer.

Ce qu’il faut dans le produit:

- un etat `proceduralement pret`
- une timeline de procedure
- les blockers visibles
- les demandes de complements, reponses et accusés traces

### 2. Delais disperses

Les dates critiques vivent dans les emails, les agendas et les tetes.

Ce qu’il faut:

- une seule entite deadline: `Obligation`
- un operating inbox qui agrège:
  - obligations
  - complements
  - expirations
  - filings
  - preuves manquantes

### 3. Documents morts

Des fichiers sans contexte, sans preuve de provenance, sans lien a une etape.

Ce qu’il faut:

- rattachement explicite a:
  - une exigence
  - une procedure
  - une audience
  - une version
- historique d’envoi/consultation/accusé

### 4. Dossier a refaire pour chaque acteur

Le meme batiment est reconstruit pour l’autorite, l’assureur, le diagnostiqueur,
la gerance, la fiduciaire.

Ce qu’il faut:

- un `workspace batiment` canonique
- des packs par audience
- reutilisation de preuve
- versioning des sorties

### 5. Coordination floue

On ne sait pas clairement qui doit agir, ni a quel moment.

Ce qu’il faut:

- routing org/user
- prochain responsable explicite
- snooze/dismiss sur l’inbox d’agregation
- historique des decisions et escalades

## Habitudes d’usage a creer

### Proprietaire

Reflexe quotidien:

- ouvrir le batiment
- voir ce qui manque, bloque, expire
- sortir un pack propre quand un tiers le demande

### Gerance

Reflexe quotidien:

- ouvrir la vue portefeuille
- traiter une file priorisee cross-building
- router ensuite vers le bon batiment, la bonne procedure, le bon acteur

### Entreprise / intervenant

Reflexe quotidien:

- voir seulement les preuves, consignes et etapes qui la concernent
- ne pas reconstruire le contexte

### Autorite

Reflexe cible:

- consulter un dossier proceduralement propre
- demander un complement
- retrouver versions, preuve et accusés sans bruit inutile

## Best practices externes a retenir

### 1. Resoudre le probleme complet, pas seulement une transaction

Reference utile:

- GDS / service standard et ecosysteme public de design de service
  - <https://www.gov.uk/service-manual/service-standard>

Implication:

- `SwissBuilding` ne doit pas etre seulement un formulaire, une GED ou un PDF generator
- il doit couvrir la chaine:
  - preparation
  - preuve
  - procedure
  - reponse
  - suivi

### 2. One-stop shop pour les processus complexes

Reference utile:

- BUILD UP, `Delivering the EU Buildings Directive`, publie en novembre 2025
  - <https://build-up.ec.europa.eu/system/files/2025-11/STO73kA9O5_05_11_2025_162658.pdf>

Implication:

- pour un utilisateur, tout ce qui touche au batiment doit donner l’impression
  d’un seul systeme coherent
- meme si les backends, autorites ou experts sont multiples

### 3. Le passeport n’a de valeur que s’il est vivant et reutilisable

References utiles:

- BUILD UP / renovation passport material
  - <https://build-up.ec.europa.eu/>

Implication:

- un passeport statique n’est pas assez fort
- il faut un dossier vivant:
  - mis a jour
  - versionne
  - reutilisable par audience
  - branche sur les procedures reelles

### 4. L’upload n’est pas une solution, c’est une etape

References utiles:

- bonnes pratiques de services publics numeriques sur les formulaires, uploads,
  notifications et joins-up journeys
  - <https://www.gov.uk/service-manual>

Implication:

- demander un document doit declencher:
  - qualification
  - rattachement
  - verification
  - usage
- pas seulement stockage

### 5. L’accessibilite et la lisibilite ne sont pas optionnelles

References utiles:

- GDS Service Standard
  - <https://www.gov.uk/service-manual/service-standard>
- BFEH / LHand
  - <https://www.ebgb.admin.ch/fr/loi-sur-legalite-pour-les-personnes-handicapees-lhand>

Implication:

- l’outil doit etre clair, robuste, lisible et tolerant a la complexite
- ce n’est pas seulement un sujet de design system, mais de structure produit

## Ce qu’un produit 10x meilleur doit faire

- dire `ce qui s’applique` sans obliger l’utilisateur a lire toute la base legale
- dire `ce qui manque` sans scan manuel des pieces
- dire `ce qui bloque` avant que le chantier ou le depot soit stoppe
- dire `quoi faire ensuite` avec responsable et preuve attendue
- dire `pourquoi c'est important` en une lecture
- sortir un dossier adapte a l’audience sans refaire la compilation
- tracer la diffusion du dossier et les retours
- rester a jour quand les textes, portails ou formulaires changent

## Anti-patterns a eviter

- une deuxieme inbox parallele
- une deuxieme entite deadline
- une logique permis separee du read model existant
- des documents lies en JSON libre sans objet canonique
- un dashboard descriptif sans action utile
- un passeport joli mais non procedurable

## Decision produit qui ressort

Le bon coeur produit n’est pas:

- `GED`
- `CRM`
- `ERP`
- `BI`

Le bon coeur produit est:

- `operating memory`
- `procedural control tower`
- `proof distribution layer`
- `shared building workspace`
