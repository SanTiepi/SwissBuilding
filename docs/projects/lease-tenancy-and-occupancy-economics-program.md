# Lease, Tenancy, and Occupancy Economics Program

## Mission

Extend SwissBuilding from building truth into occupancy-aware economics:
- lease-aware impact
- resident disruption memory
- vacant or impacted unit tracking
- rent and occupancy consequences tied to works and readiness

## Why This Matters

A building can be technically ready while still being commercially or operationally constrained by:
- tenant occupancy
- lease commitments
- rent-impact windows
- unit-level disruption

## Core Outcomes

1. `LeaseRecord` becomes a first-class object.
2. impacted unit / vacant unit tracking becomes explicit.
3. works and restrictions can be translated into occupancy and rent-impact surfaces.
4. owner/manager packs can include tenancy-aware consequences.

## Candidate Objects

- `LeaseRecord`
- `UnitOccupancyState`
- `OccupancyImpactWindow`
- `TenantClaimRecord`
- `RentReductionSupportPack`

## Acceptance

- occupancy economics are modeled without turning SwissBuilding into a generic PM tool
- works/readiness can be translated into occupant and lease impact
- the layer compounds building truth rather than drifting away from it
