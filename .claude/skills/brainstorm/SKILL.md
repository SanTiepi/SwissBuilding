---
name: brainstorm
description: "Brainstorm adaptatif multi-agents. Usage: /brainstorm <idée>. De la question rapide à l'exploration radicale."
user-invocable: true
---

# /brainstorm

## Classifie

- **Quick** — question simple → Claude seul, 3-5 lignes
- **Standard** — feature, architecture → Codex + Claude, pensée divergente
- **Deep** — stratégie, business → Codex obligatoire, contraire vrai, analogie forcée
- **Explore** — innovation, nouvelles pistes → simulation multi-agents, exploration large

Détecte automatiquement. Ne demande jamais le mode.

## Quick
3-5 lignes. Verdict + pourquoi + alternative.

## Standard
Codex + Claude. Avant tout : cadre implicite, ce qu'il empêche de voir, idée hors cadre. Timeout 45s.

## Deep
Comme Standard + contraire vrai + analogie forcée. Codex obligatoire 90s.

## Explore

Le mode le plus important. On explore LARGE — volontairement trop large au début pour ne rien louper. On affine après.

### Principe fondamental
Ne PAS converger trop vite. Ouvrir le champ au maximum AVANT de trier. Les meilleures idées sont aux intersections les plus improbables.

### Process

**Phase 1 — Ouverture maximale**

Génère 7-10 points de vue radicalement différents. Pas des variations — des MONDES différents :
- 3 experts du sujet (mais de sous-domaines éloignés)
- 3 experts de domaines SANS RAPPORT (sciences, arts, nature, sports, cuisine, musique, médecine, justice, jeux...)
- 1-2 profils impossibles ou inventés ("un historien de l'an 3000", "un océan qui pense", "un enfant-philosophe")

Chaque point de vue : 1 mécanisme transférable de son domaine, pas une opinion. 2 lignes max.

Ne trie PAS encore. Ne juge PAS. Accumule.

**Phase 2 — Collisions**

Prends les points de vue les plus ÉLOIGNÉS et force des collisions par paires :
- Qu'est-ce qui émerge quand on connecte A et B ?
- Quel produit/concept/approche existe à cette intersection ?
- Qu'est-ce qui est IMPOSSIBLE à trouver sans cette collision ?

3-5 collisions. Cherche celles qui produisent un "c'est bizarre mais..." — c'est là que l'innovation est.

**Phase 3 — Patterns**

Regarde l'ensemble des points de vue et collisions. Quels PATTERNS émergent ?
- Qu'est-ce que plusieurs experts disent sans le savoir ?
- Quelle direction revient sous des formes différentes ?
- Quel problème sous-jacent est révélé par les collisions ?

**Phase 4 — Synthèse ouverte**

Présente à l'utilisateur :
- Les 3-5 insights les plus surprenants
- Les 2-3 collisions les plus fertiles
- Le pattern émergent
- 2-3 directions possibles (pas 1 seule — garder le champ ouvert)
- Pour chaque direction : 1 ligne de ce que ça donne concrètement

**Ne conclus PAS.** L'explore ouvre des portes. L'utilisateur choisit laquelle franchir. Si l'utilisateur veut creuser une direction, relance un brainstorm Standard ou Deep dessus.

### Relancer en cours de projet

L'explore n'est pas que pour le début. Relance-le :
- Quand le projet stagne
- Quand une décision importante approche
- Quand l'utilisateur dit "on rate peut-être quelque chose"
- Toutes les 2-3 semaines sur un projet actif

À chaque relance, les experts changent. Le contexte du projet nourrit de nouvelles collisions.

## Après chaque brainstorm

`.claude/brainstorm_log.md` :
```
- [date] [mode] [résultat] [titre] — [1 ligne]
```

## Principes

- Quick/Standard/Deep = DÉCIDER. Explore = DÉCOUVRIR.
- En Explore : ne jamais converger trop tôt. La largeur est une force, pas un défaut.
- Les meilleures idées viennent des collisions les plus improbables
- Si tu ne surprends pas l'utilisateur, recommence
- Anticipe ce que l'utilisateur n'a pas encore pensé — c'est ta valeur
