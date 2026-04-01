# Pilot Commune Candidates

Date de controle: `25 mars 2026`

## Purpose

This shortlist turns the abstract `pilot communes` idea into a concrete first
adapter batch with official anchors and clear product reasons.

It is not a claim of national communal coverage.

It is a disciplined entry point for:

- local procedure variants
- stricter communal review flags
- local proof requirements
- manual-review fallback when the local rule is too ambiguous

## Selection rule

A pilot commune is worth the first adapter work only if it has all of:

- official public construction or urbanism pages
- real customer relevance for the target wedge
- communal deltas that change workflow, proof, or routing
- enough procedural clarity to support explainable manual-review fallback

## Recommended shortlist

### Phase 1

#### Nyon (`VD`)

Why it is a strong pilot:

- strong fit with the current `VD` wedge
- explicit commune-level permit framing
- public inquiry timing is visible
- official surveyor plan requirement is visible

Signals worth modeling:

- local public inquiry timing
- commune-level permit intake framing
- proof requirement around official plans

Official sources:

- <https://www.nyon.ch/demarches/permis-de-construire-1729/>
- <https://www.nyon.ch/nyon-officiel/administration/urbanisme-1387/>

#### Meyrin (`GE`)

Why it is a strong pilot:

- strong fit with the current `GE` wedge
- visible commune and canton split for authorizations
- local public-domain occupation path adds real procedural branching

Signals worth modeling:

- commune preavis or local review branch
- split between local and cantonal actions
- public-domain occupation dependency when relevant

Official sources:

- <https://www.meyrin.ch/fr/votre-mairie-administration-urbanisme-travaux-publics-et-energie/demande-dautorisation>
- <https://www.meyrin.ch/fr/fao>

### Phase 2

#### Lausanne (`VD`)

Why it is a strong pilot:

- major market relevance
- explicit building-permit office and permit-exempt work framing
- stronger heritage and urban-integration signal than a simpler commune

Signals worth modeling:

- permit-exempt vs permit-required branch
- commune-level heritage or urban-review preavis flag
- local document set for work declaration vs permit

Official sources:

- <https://www.lausanne.ch/de/dam/jcr%3Ac7352426-4422-4327-9b7e-f7860f019b4c/Brochure-permis-de-construire.pdf>
- <https://www.lausanne.ch/dam/jcr%3Ad6cdf7ac-b627-41dc-aa2e-63cdc49b1028/250409_formulaire-demande-de-travaux.pdf>

#### Ville de Fribourg (`FR`)

Why it is a strong pilot:

- useful counterweight outside `VD/GE`
- visible split between communal and cantonal handling
- explicit urban or heritage review body signal

Signals worth modeling:

- commune vs prefecture or canton routing branch
- local urban or heritage review flag
- `FRIAC`-style filing context carried into workflow

Official sources:

- <https://www.ville-fribourg.ch/urbanisme-architecture/inspectorat-constructions>
- <https://www.fr.ch/territoire-amenagement-et-constructions/permis-de-construire-et-autorisations/permis-de-construire>
- <https://www.ville-fribourg.ch/commissions/commission-paysage-urbain-patrimoine>

## Rollout recommendation

### First build pair

Build first:

- `Nyon`
- `Meyrin`

Why:

- they sit directly on top of the strongest current wedge
- they maximize communal value while keeping the first adapter batch small
- they force useful handling of `VD` and `GE` local variants early

### Second build pair

Add next:

- `Lausanne`
- `Ville de Fribourg`

Why:

- they increase depth and complexity honestly
- they pressure-test heritage, urban review, and cross-authority routing
- they widen the product beyond the first wedge without pretending to cover
  every commune

## Adapter outputs expected from this shortlist

The first communal slice should only emit a few high-signal outputs:

- `CommunalAdapterProfile`
- `CommunalRuleOverride`
- `CommunalProcedureVariant`
- `manual_review_required`
- `communal_blocker_reason`
- `communal_proof_requirement`

## Product rule

Do not build commune adapters as metadata-only enrichment.

A commune adapter is worth shipping only if it improves at least one of:

- procedural clarity
- required proof clarity
- blocker visibility
- routing to the right authority

## Notes

This shortlist is a research snapshot, not a legal guarantee.

The product should preserve:

- source links
- last review date
- explicit manual-review fallback
- explainability of why a communal rule changed the workflow
