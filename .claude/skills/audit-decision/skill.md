# /audit-decision — Audit épistémique d'une décision

Remplace un framework de 13 modules par 1 prompt intelligent.
Utilise la puissance native du LLM au lieu de réinventer la roue.

## Déclenchement
- `/audit-decision <décision à auditer>`
- Quand l'utilisateur demande de vérifier/challenger/valider une décision

## Process

### 1. Typage épistémique
Pour chaque argument qui soutient la décision, classe-le :
- **FAIT** — vérifié, sourcé, reproductible
- **HYPOTHÈSE** — plausible mais non testée
- **INFÉRENCE** — dérivé d'autres arguments (cite les prémisses)
- **RUMEUR** — non vérifié, non sourcé

Si la décision repose uniquement sur des hypothèses ou des rumeurs → **ALERTE**.

### 2. Score de fragilité
Évalue : "Si on retire UN argument, la décision tient-elle encore ?"
- Score 0-10 (0 = rock solid, 10 = château de cartes)
- Identifie les **points de rupture** : les 1-2 arguments sans lesquels tout s'effondre
- Si 1 seul argument porte >50% du poids → **FRAGILE**

### 3. Coup épistémique (findCoup)
Trouve la **plus petite intervention** qui retournerait la décision :
- "Il suffit de changer X pour que la conclusion s'inverse"
- Combien de mots/faits faut-il modifier ?
- Si le seuil est bas → la décision est vulnérable

### 4. Contre-récit
Construis l'**histoire alternative** la plus convaincante :
- Mêmes faits, conclusion opposée
- Identifie le point de divergence exact
- Si le contre-récit est aussi convaincant que l'original → **DANGER**

### 5. Architecture de défense
Pour chaque vulnérabilité trouvée, propose :
- Comment renforcer l'argument
- Quelle preuve manque
- Quel test permettrait de trancher

## Output

```
DÉCISION: [la décision auditée]

TYPAGE:
- [argument 1] → FAIT (source: ...)
- [argument 2] → HYPOTHÈSE
- [argument 3] → RUMEUR ⚠️

FRAGILITÉ: X/10
- Point de rupture: [argument clé]
- Si retiré: [conséquence]

COUP MINIMAL: [la plus petite intervention qui inverse tout]

CONTRE-RÉCIT: [2-3 lignes, l'histoire alternative]

DÉFENSE:
1. [action pour renforcer]
2. [preuve à chercher]
3. [test à faire]

VERDICT: SOLIDE | FRAGILE | CRITIQUE
```

## Principes
- Pas de complaisance — le but est de TROUVER les failles, pas de rassurer
- Concis — le rapport tient en 1 écran
- Actionnable — chaque vulnérabilité a une recommandation concrète
- Si la décision est solide, dis-le en 2 lignes et passe à autre chose
