# SwissRules Watch Priority Backlog

Date de controle: `25 mars 2026`

## Goal

Donner a Claude un ordre de veille clair pour `SwissRules Watch`, sans
surveiller toutes les sources au meme niveau de frequence.

La priorite de watch ne suit pas seulement la force normative.
Elle suit aussi:

- volatilite du portail ou du formulaire
- impact procedurale immediat
- risque de blocage reel pour l'utilisateur

## Tier 1: daily watch

Ces sources changent peu juridiquement, mais elles changent vite
proceduralement et peuvent casser un depot reel.

- `vd_camac`
  - why: portail et consignes de depot
  - impact: dossiers permis et pieces
- `ge_building_auth`
  - why: portail autorisation et exigences de depot
  - impact: procedure et complements
- `fr_seca`
  - why: portail service instructeur
  - impact: pieces, canaux et workflow

## Tier 2: weekly watch

Ces sources peuvent modifier des obligations ou des exigences
substantielles a forte valeur produit.

- `are_hors_zone`
- `are_lat_oat`
- `bafu_oled`
- `bafu_waste_law`
- `bag_radon_legal`
- `suva_asbestos`
- `ekas_cfst_6503`

Focus:

- changements de procedure
- formulaires ou preuves exigees
- evolution de delais ou de seuils

## Tier 3: monthly watch

Ces sources doivent etre tenues fraiches, mais leur rythme de changement est
moins critique pour la boucle quotidienne.

- `bafu_pcb_joints`
- `bag_radon`
- `endk_mopec`
- `vkf_fire`
- `bfs_regbl`
- `cadastre_rdppf`
- `bafu_natural_hazards`
- `bafu_groundwater_protection`
- `bak_isos`
- `ebgb_lhand`

## Tier 4: quarterly watch

Ces sources restent importantes comme couche complementaire ou
quasi-normative, mais pas comme premier moteur de blocage quotidien.

- `minergie_label`
- `fach_guidance`
- `asca_guidance`

## What to detect

For each watched source, classify deltas as:

- `new_rule`
- `amended_rule`
- `repealed_rule`
- `portal_change`
- `form_change`
- `procedure_change`

The product reaction is different:

- `portal_change` can create an admin action without changing the legal rule
- `form_change` can invalidate a ready-to-send pack
- `procedure_change` can create blockers and new obligations
- `amended_rule` can require republishing templates and re-evaluating buildings

## First expansion backlog

When Claude resumes `SwissRules Watch`, the first sources to add after the
current registry should be:

1. Vaud communal and heritage-specific pages linked from CAMAC contexts
2. Geneva procedure variants for protected or special-use cases
3. Fribourg execution documents and forms beyond the landing page
4. commune-level zoning and construction rules for pilot communes
5. utility and network approval sources for common intervention types
6. cantonal subsidy and public-funding procedure pages

## Product rule

Watch should only matter if it triggers one of these:

- new or changed blocker
- new or changed obligation
- changed required proof
- changed authority or route
- changed pack or filing requirement

If a detected delta does not change one of those, it stays an admin review
signal, not a user-facing disruption.
