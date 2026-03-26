# SwissRules Source Map

## Purpose

This file is the human-readable companion to the bootstrap registry in
`backend/app/services/swiss_rules_spine_service.py`.

It helps execution waves understand:

- which Swiss regulatory domains are already anchored
- which official sources are the current starting points
- which existing SwissBuilding subsystems those sources should feed
- which research gaps still need explicit adapters

## Anchored domains

| Domain | Level | Starting sources | Existing subsystem anchors |
|---|---|---|---|
| Permit and planning | federal + cantonal + communal | ARE LAT/OAT, ARE hors zone, CAMAC, Geneva building authorization, Fribourg SeCA | `permit_tracking`, future `PermitProcedure`, `ControlTower`, `authority_pack` |
| Pollutant declarations | federal + cantonal | SUVA, CFST 6503, canton portals, BAFU PCB guidance | `regulatory_filing`, `authority_pack`, `obligation`, `ControlTower` |
| Waste / OLED | federal | BAFU OLED, BAFU waste law | `regulatory_filing`, future `proof_delivery`, `authority_pack`, `ControlTower` |
| Radon | federal | BAG radon, BAG legal radon basis | `authority_pack`, `obligation`, `ControlTower` |
| Energy | intercantonal + cantonal | EnDK / MoPEC, cantonal permit portals, Minergie as labeled layer | `permit_tracking`, `authority_pack`, future `PermitProcedure` |
| Fire safety | intercantonal + cantonal + communal | VKF / AEAI, cantonal permit portals | `authority_pack`, `ControlTower`, future `PermitProcedure` |
| Heritage / outside-zone review | federal + cantonal + communal | ARE hors zone, cantonal permit portals, commune-specific rules | `permit_tracking`, future `PermitProcedure`, `ControlTower` |
| RDPPF / cadastral restrictions | federal + cantonal + communal | cadastre RDPPF, RegBL, cantonal permit portals | `permit_tracking`, `authority_pack`, `ControlTower` |
| Natural hazards | federal + cantonal + communal | BAFU natural hazards, hazard maps, cantonal permit portals | `permit_tracking`, `authority_pack`, `ControlTower`, future `PermitProcedure` |
| Groundwater protection | federal + cantonal + communal | BAFU groundwater protection, RDPPF | `permit_tracking`, `authority_pack`, `ControlTower`, future `PermitProcedure` |
| Accessibility | federal + cantonal + communal | LHand / BFEH, cantonal permit portals | `permit_tracking`, `authority_pack`, `ControlTower`, future `PermitProcedure` |

## Source principles

- `binding_law`
  - legal texts and binding public regulations
- `official_execution_guideline`
  - official execution guidance and authority procedures
- `intercantonal_standard`
  - cross-canton standards used in practice
- `private_standard`
  - non-state standards like `FACH`, `ASCA`, `SIA`
- `label`
  - optional labels like `Minergie`

SwissBuilding should always show which layer a recommendation comes from.

## Canton anchors already chosen

- `VD`
  - CAMAC and Vaud construction permit flow
- `GE`
  - Geneva building authorization flow
- `FR`
  - Fribourg SeCA flow

These are anchors, not exclusive targets. The future model still needs a
generic canton adapter pattern.

## Communal reality

There is no single Swiss communal rule feed.

The model must support:

- a generic communal jurisdiction layer
- commune-specific adapters when structured sources exist
- manual review fallback when the communal rule is document-only or portal-only

## Research gaps still to close

- commune-by-commune construction rules and zoning specifics
- protected building / heritage adapters by canton and commune
- utility / network approval constraints
- accessibility / disability requirements by use case
- natural hazards execution rules by canton
- public-funding and subsidy procedural sources by canton
- special building classes:
  - schools
  - hospitals
  - industrial sites
  - agricultural buildings
  - telecom / antennas
  - water-catchment or highly protected areas

## Execution note

When a new regulatory source is added, the preferred path is:

1. add it to the SwissRules registry
2. classify its normative force
3. decide which existing subsystem it should feed
4. add a scenario fixture and projection test
5. only then wire the product behavior
