# SwissBuildingOS

**Built Environment Meta-OS for at-risk buildings**

SwissBuildingOS est un systeme d'intelligence operationnelle pour batiments a risque. Le produit ne se limite pas a centraliser des diagnostics: il transforme documents, donnees publiques, diagnostics, evenements et historique d'un batiment en **preuves, decisions, actions, packs et strategie portefeuille**.

La these produit est simple:
- le batiment **se comprend**
- le batiment **s'explique**
- le batiment **se pilote**
- le batiment **se prepare**
- le portefeuille **s'arbitre**

L'ambition du projet est de montrer jusqu'ou un developpeur debutant peut aller avec l'IA pour construire un PoC commercial tres ambitieux, credible et demonstrable.

Le positionnement vise va plus loin qu'une simple application de diagnostic:
SwissBuildingOS cherche a devenir le **systeme d'intelligence du bati**, puis a terme le **Built Environment Meta-OS**: une couche d'infrastructure qui relie batiments, travaux, exploitation, finances, occupants, procedures, portefeuilles et ecosystemes d'echange.

## Pertinence client aujourd'hui

La pertinence commerciale actuelle est forte surtout pour un segment:

- **gerances immobilieres multi-batiments**
- actives en `VD` et/ou `GE`
- avec des **travaux a lancer sur batiments anciens**
- qui jonglent deja entre **PDF, annexes labo, plans, emails et ERP**

Le produit est donc plus pertinent quand il est presente comme:

**une couche de preuve et de readiness pour les dossiers pre-travaux reglementes**

plutot que comme un logiciel immobilier generaliste.

Ce qu'un client achete aujourd'hui:
- savoir **ce qui est prouve**
- voir **ce qui manque**
- reduire le **rework documentaire**
- produire un **safe-to-start dossier** plus vite
- conserver une **memoire batiment** reutilisable entre projets

Une evaluation plus detaillee des segments, freins commerciaux et priorites d'amelioration est disponible dans [docs/market/client-fit-evaluation-fr.md](docs/market/client-fit-evaluation-fr.md).

---

## Ce que le produit cherche a devenir

SwissBuildingOS est pense comme un systeme compose de 5 couches:

- **Evidence OS** — Le produit relie scores, diagnostics, documents et regles a des preuves explicites.
- **Building Memory OS** — Chaque batiment devient une memoire vivante et versionnee, pas une simple fiche statique.
- **Action OS** — Les risques et manques se transforment en actions, playbooks et orchestration.
- **Portfolio OS** — Le parc immobilier devient pilotable a l'echelle: priorisation, CAPEX, campagnes, arbitrage.
- **Agent OS** — Des agents invisibles lisent, rapprochent, detectent, suggerent, emballent et relancent avant qu'un copilote visible ne soit expose.

Le brief strategique long terme est documente dans [docs/vision-100x-master-brief.md](docs/vision-100x-master-brief.md).
La carte la plus complete des futurs moteurs, usages non couverts et moonshots est documentee dans [docs/product-frontier-map.md](docs/product-frontier-map.md).

## Built Environment Meta-OS

Le produit est maintenant cadre comme une infrastructure du cycle de vie immobilier physique, pas seulement comme une super app du batiment.

Le scope officiel couvre 12 macro-domaines:

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

En pratique, cela veut dire que SwissBuilding doit a terme supporter:
- la verite du batiment
- les travaux
- l'exploitation
- la propriete
- l'occupation
- la finance
- l'assurance
- la vente
- la procedure
- le portefeuille
- l'echange ecosystemique

## Horizon de rupture

Le produit ne vise pas seulement une meilleure gestion documentaire ou un meilleur workflow.
La cible est beaucoup plus haute:

- **Building Passport** — un passeport vivant, versionne et transmissible du batiment
- **Evidence Graph** — chaque score, obligation, action et recommandation pointe vers ses preuves
- **Readiness Engine** — le systeme dit si un actif est `safe_to_start`, `safe_to_renovate`, `safe_to_sell`, `safe_to_insure` ou non
- **Post-Works Truth** — le produit sait ce qui a ete retire, ce qui reste, ce qui est assaini et ce qui doit etre reverifie
- **Portfolio Intelligence** — le parc devient arbitrable par urgence, cout, preuve, sequence et impact
- **European Rules Layer** — un modele Europeen avec couches pays / canton / region / autorite
- **Invisible Agent Layer** — des agents lisent, relient, detectent les trous, preparent les packs et relancent les acteurs

Autrement dit:
SwissBuildingOS veut devenir la couche de verite operationnelle du bati, pas juste une app de diagnostics.

Le niveau vise n'est pas celui d'un outil local opportuniste.
Le produit doit tendre vers un standard **international-class**:
- modele Europe-ready
- execution locale par packs reglementaires
- multilingue par conception
- preuve, auditabilite, exportabilite et interop comme fondations
- qualite suffisante pour devenir, a terme, une couche de reference du marche

## Fonctionnalites actuelles et trajectoire

- **Diagnostics et echantillons** — Creation, suivi et exploitation de diagnostics polluants (amiante, PCB, plomb, HAP, radon).
- **Risque et conformite** — Evaluation automatisee du risque et lecture des obligations suisses.
- **Documents** — Gestion documentaire et flux de rapports de diagnostic.
- **Simulation** — Estimation des couts, diagnostics requis, obligations et delais.
- **Carte** — Visualisation geospatiale des batiments et signaux de risque.
- **Dossier batiment** — Le coeur produit evolue vers un dossier vivant, explicable et actionnable.
- **Portefeuille** — La trajectoire cible va vers le pilotage multi-batiments, les campagnes, la priorisation et l'arbitrage budgetaire.

## Point d'entree marche

Le point d'entree volontairement choisi est:

**les diagnostics polluants avant renovation**

Pourquoi:
- obligation legale
- budget identifiable
- douleur metier claire
- forte fragmentation documentaire et operationnelle

Ce point d'entree sert a construire la memoire batiment, la preuve, les actions et, plus tard, une infrastructure beaucoup plus large.
L'execution commerciale near-term reste volontairement plus etroite:
- Europe-shaped product model
- Switzerland-first launch
- `VD/GE` as first rules-pack execution zones
- `amiante-first`
- `AvT -> ApT`
- `safe-to-start dossier`
- overlay au-dessus des ERP et archives existants

La logique d'expansion assumee est:
- modele de categorie Europeen
- couche de lancement Suisse
- packs reglementaires locaux
- extension multi-polluants
- extension portefeuille / preuve / arbitrage
- extension owner / finance / operations
- extension territoire / procedure / public systems
- extension vers une infrastructure de connaissance et d'orchestration du patrimoine bati

## Ce qui rend le produit differenciant

Le moat vise n'est pas un chatbot ou un simple dashboard.
La differenciation principale repose sur:
- la **preuve**
- la **memoire**
- l'**orchestration**
- le **pilotage portefeuille**
- l'**agentivite controlee**

Autrement dit: SwissBuildingOS ne veut pas seulement decrire le risque, mais **le justifier, le transformer en plan d'action et le rendre gouvernable dans le temps**.

---

## Stack technique

| Couche | Technologies |
|---|---|
| **Backend** | FastAPI, async SQLAlchemy, PostgreSQL / PostGIS, MinIO (stockage objet) |
| **Frontend** | React, TypeScript, Vite, Tailwind CSS, Mapbox GL JS, Recharts |
| **Infrastructure** | Docker Compose, Nginx (reverse proxy) |

---

## Demarrage rapide

### Prerequis

- Docker et Docker Compose installés
- Git

### Installation

```bash
git clone <repository-url> && cd SwissBuilding
cp .env.example .env
docker compose -f infrastructure/docker-compose.yml up --build
```

L'application est prete lorsque tous les conteneurs sont demarres.

### Identifiants par defaut

| Champ | Valeur |
|---|---|
| Email | `admin@swissbuildingos.ch` |
| Mot de passe | `noob` |

> **Attention** : changez imperativement le mot de passe administrateur avant tout deploiement en production.

En cas de decalage des credentials en local:

```bash
cd backend
python -m app.seeds.reset_demo_admin_password --password noob
```

### URLs d'acces

| Service | URL |
|---|---|
| Application (staging) | [https://swissbuilding.batiscan.ch](https://swissbuilding.batiscan.ch) |
| Documentation API (Swagger) | [https://swissbuilding.batiscan.ch/docs](https://swissbuilding.batiscan.ch/docs) |

---

## Vision de demonstration

Le projet est aussi pense comme une preuve de concept demonstrable. Une bonne demo doit montrer:
- ingestion de donnees reelles et documents
- explication du risque et de ses preuves
- transformation automatique en actions
- preparation de livrables et de packs
- pilotage d'un portefeuille de batiments
- trajectoire credible vers un reseau d'intelligence du bati

## Tests

Executer la suite de tests du backend :

```bash
docker compose exec backend pytest -v
```

---

## Structure du projet

```
SwissBuilding/
├── backend/                # API FastAPI
│   ├── app/
│   │   ├── api/            # Routes et endpoints
│   │   ├── core/           # Configuration, sécurité, conformité
│   │   ├── models/         # Modèles SQLAlchemy
│   │   ├── schemas/        # Schémas Pydantic
│   │   ├── services/       # Logique métier et moteur de conformité
│   │   └── utils/          # Utilitaires
│   ├── tests/              # Tests pytest
│   └── Dockerfile
├── frontend/               # Application React
│   ├── src/
│   │   ├── components/     # Composants React
│   │   ├── pages/          # Pages de l'application
│   │   ├── services/       # Appels API
│   │   ├── hooks/          # Hooks personnalisés
│   │   └── utils/          # Utilitaires
│   └── Dockerfile
├── infrastructure/
│   ├── docker-compose.yml  # Orchestration des services
│   └── nginx/              # Configuration du reverse proxy
├── .env.example            # Variables d'environnement (modèle)
└── README.md
```

---

## Cadre legal suisse

SwissBuildingOS s'appuie sur les textes reglementaires federaux suivants :

| Abréviation | Texte | Domaine |
|---|---|---|
| **OTConst** | Ordonnance sur les travaux de construction | Règles de sécurité et de santé pour les travaux de construction, y compris la manipulation de substances dangereuses |
| **CFST 6503** | Directive CFST relative à l'amiante | Identification, évaluation et gestion de l'amiante dans les bâtiments |
| **ORRChim** | Ordonnance sur la réduction des risques liés aux produits chimiques | Restrictions d'utilisation des substances dangereuses (PCB, plomb, etc.) |
| **OLED** | Ordonnance sur la limitation et l'élimination des déchets | Traitement et élimination des déchets contenant des polluants du bâtiment |
| **ORaP** | Ordonnance sur la radioprotection | Protection contre le radon dans les bâtiments, valeurs limites et mesures |

---

## Licence

*À définir* — Ce projet n'est pas encore sous licence. Veuillez contacter les responsables du projet pour toute question relative aux droits d'utilisation.
