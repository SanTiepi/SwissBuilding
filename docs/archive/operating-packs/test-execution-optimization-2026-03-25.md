# Test Execution Optimization

Date de controle: `25 mars 2026`

## But

Eviter de perdre du temps localement avec:

- des full runs inutiles
- des commandes trop longues a taper
- des suites trop larges pour la boucle de dev
- des validations qui n'apportent pas plus de signal qu'une suite ciblee

Le principe est simple:

- `inner loop`: le plus petit signal utile
- `confidence loop`: une suite ciblee representative
- `full loop`: reservee aux moments ou cela vaut vraiment le cout

## Probleme observe

Le repo a maintenant:

- des milliers de tests backend
- plusieurs couches frontend
- du mock e2e
- du real e2e

Donc utiliser par defaut:

- `python -m pytest tests/ -q`
- `npm test`
- `npm run test:e2e:real`

comme boucle normale est trop lent.

## Regle

Ne jamais lancer la suite la plus large par reflexe.

Ordre recommande:

### Backend

1. `ruff check` / `ruff format --check`
2. `python scripts/run_local_test_loop.py changed`
3. `python scripts/run_local_test_loop.py last-failed`
4. `python scripts/run_local_test_loop.py confidence`
5. `python -m pytest tests/ -q` seulement si necessaire

### Frontend

1. `npm run typecheck`
2. `npm run test:changed`
3. `npm run test:changed:strict`
4. `npm run test:unit:critical`
5. `npm run test:e2e:smoke` seulement si la surface touche le flow
6. `npm run test:e2e:real` seulement pour preuve reelle

## Nouveaux outils locaux

### Backend

Nouveau runner:

- [run_local_test_loop.py](/C:/PROJET%20IA/SwissBuilding/backend/scripts/run_local_test_loop.py)

Modes:

- `changed`
  - detecte les chemins backend modifies
  - infere les tests cibles
  - fallback sur la confidence suite si l'inference est vide
- `last-failed`
  - relance les derniers echecs
- `confidence`
  - lance le sous-ensemble backend significatif deja defini
- `full`
  - lance toute la suite
- `files`
  - lance explicitement les fichiers fournis

Optimisation:

- utilise `pytest-xdist` en local si disponible
- parallelise par fichier de test

Exemples:

- `python scripts/run_local_test_loop.py changed`
- `python scripts/run_local_test_loop.py changed --maxfail 1`
- `python scripts/run_local_test_loop.py confidence`
- `python scripts/run_local_test_loop.py last-failed`
- `python scripts/run_local_test_loop.py files tests/test_buildings.py tests/test_workspace_membership.py`

### Frontend

Nouveau runner:

- [run_local_fast_suite.mjs](/C:/PROJET%20IA/SwissBuilding/frontend/scripts/run_local_fast_suite.mjs)

Scripts ajoutes:

- `npm run test:changed`
- `npm run test:changed:strict`
- `npm run test:fast`

Optimisation:

- detecte les fichiers frontend modifies
- utilise `vitest related --run` au lieu d'un `vitest run` large
- fallback sur la suite critique si rien n'est inferable
- peut relancer les specs Playwright modifiees avec `--e2e`

Exemples:

- `npm run test:changed`
- `npm run test:changed:strict`
- `node scripts/run_local_fast_suite.mjs changed --e2e`
- `npm run test:fast`

## Quand lancer quoi

### Changement local borne

Exemples:

- un service backend
- un composant frontend
- un endpoint
- une carte UI

Utiliser:

- `changed`
- `last-failed`
- ciblage explicite si necessaire

### Wave backend importante

Utiliser:

- `ruff check`
- `ruff format --check`
- `confidence`
- quelques tests explicites de la surface touchee

### Wave frontend importante

Utiliser:

- `typecheck`
- `test:changed:strict`
- `test:unit:critical`
- `test:e2e:smoke` si flow touche

### Preuve finale

Utiliser seulement la ou c'est utile:

- full backend
- full validate frontend
- real e2e

## Ce qu'il faut eviter

- lancer `pytest tests/` pendant la boucle d'edition normale
- lancer `npm test` quand `vitest related` suffit
- lancer `real e2e` pour un changement purement structurel ou typage
- empiler lint + format + typecheck + full tests a chaque micro-edit

## Doctrine

Le bon objectif n'est pas:

- "faire tourner le plus de tests possible tout le temps"

Le bon objectif est:

- "obtenir le plus de signal utile le plus vite possible"

Donc:

- petit signal rapide en boucle
- signal representatif avant merge
- preuve large seulement aux moments ou elle compte

## Notes

- `pytest-xdist` a ete ajoute comme optimisation locale simple.
- La suite complete reste importante, mais ce n'est pas la boucle de travail
  par defaut.
- Si une surface n'a besoin que d'un petit sous-ensemble de tests pour fournir
  un signal fiable, il faut privilegier ce sous-ensemble.
