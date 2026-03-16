# Partner Network and Contributor Reputation Program

## Mission

Turn contributor participation into a structured network advantage by making partner quality, responsiveness, evidence reliability, and workflow fit visible and operationally useful.

## Why This Matters

SwissBuilding increasingly depends on:
- diagnosticians
- labs
- contractors
- architects
- authorities
- due diligence contributors

The product should not only let them contribute.
It should learn from contribution quality and make the ecosystem itself more valuable over time.

Without this layer, partner activity remains a dependency.
With it, the network starts becoming a moat.

## Strategic Outcomes

- contributor quality becomes measurable
- partner trust becomes operationally useful
- work can be routed more intelligently
- repeated collaboration patterns create stronger ecosystem pull

## Product Scope

This program should produce:
- contributor quality signals
- partner trust profiles
- routing and recommendation primitives
- network pull indicators

It should not become:
- a simplistic star-rating marketplace
- a noisy public ranking system

## Recommended Workstreams

### Workstream A - Contributor quality signals

Measure the behaviors that matter:
- response time
- completeness
- rework rate
- evidence quality
- consistency
- pack readiness

Candidate objects:
- `ContributorQualitySignal`
- `DeliveryReliabilityScore`
- `ReworkRateSignal`

### Workstream B - Partner trust layer

Build internal trust semantics rather than vanity reputation.

Expected outputs:
- trust profile by partner
- domain-specific strengths
- confidence in partner fit for a workflow
- signal boundaries by evidence sufficiency

Candidate objects:
- `PartnerTrustProfile`
- `WorkflowFitScore`

### Workstream C - Routing and recommendation support

Use partner signals to improve orchestration.

Examples:
- suggest the right diagnostician profile
- route missing-piece requests more intelligently
- prefer contributors who deliver cleaner proof
- identify escalation candidates when responsiveness degrades

Candidate objects:
- `RoutingSuggestion`
- `ContributorFitHint`

### Workstream D - Network pull and expansion signals

Detect when partner behavior is increasing product leverage.

Examples:
- repeated high-quality partner collaboration
- contributor-led account pull
- ecosystem density in a canton or sector
- trusted supply-side loops

Candidate objects:
- `NetworkPullIndicator`
- `PartnerExpansionSignal`

### Workstream E - Governance and fairness controls

Prevent the layer from becoming noisy or unfair.

Expected controls:
- confidence thresholds
- explanation of signals
- internal-only versus shareable outputs
- review / override semantics

## Candidate Improvements

- `ContributorQualitySignal`
- `DeliveryReliabilityScore`
- `ReworkRateSignal`
- `PartnerTrustProfile`
- `WorkflowFitScore`
- `RoutingSuggestion`
- `ContributorFitHint`
- `NetworkPullIndicator`
- `PartnerExpansionSignal`

## Acceptance Criteria

- contributor participation becomes measurable and strategically useful
- the platform can route or prioritize partners more intelligently
- ecosystem activity starts compounding into advantage
- partner quality is reflected without devolving into shallow marketplace metrics

## Validation

Backend if touched:
- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend if touched:
- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run test:e2e`
- `npm run build`
