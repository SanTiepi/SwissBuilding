# Pilot Communes Pack

Date de controle: `25 mars 2026`

## Purpose

Communal rules are too fragmented to treat as a fake national feed.

This pack defines how to start with pilot communes in a disciplined way:

- limited scope
- adapter pattern first
- manual review fallback always available

## Hard rule

Do not claim commune-wide automation unless the adapter is:

- source-anchored
- explainable
- testable
- still safe with manual review fallback

## Pilot strategy

Start with a small set of communes linked to the cantonal anchors already in
the repo:

- one or two communes in `VD`
- one or two communes in `GE`
- one or two communes in `FR`

Selection criteria:

- clear public construction or zoning pages
- realistic customer relevance
- rule differences that actually change workflow

Current shortlist:

- [pilot-commune-candidates-2026-03-25.md](./pilot-commune-candidates-2026-03-25.md)
- [communal-adapter-projection-map-2026-03-25.md](./communal-adapter-projection-map-2026-03-25.md)
- `pilot-commune-watch-seeds-2026-03-25.yaml`

## Minimum objects

### CommunalAdapterProfile

Represents a commune-specific adapter.

Minimum shape:

- `id`
- `commune_code`
- `canton_code`
- `adapter_status`
- `source_ids`
- `supports_procedure_projection`
- `supports_rule_projection`
- `fallback_mode`

### CommunalRuleOverride

Represents a commune-specific override or stricter local rule.

Minimum shape:

- `id`
- `commune_code`
- `override_type`
- `source_id`
- `impact_summary`
- `review_required`

### CommunalProcedureVariant

Represents a local procedural variant tied to a commune.

Minimum shape:

- `id`
- `commune_code`
- `procedure_code`
- `variant_type`
- `authority_code`
- `notes`

## Existing anchors to reuse

Pilot communes should feed:

- `SwissRules`
- `permit_tracking`
- future `PermitProcedure`
- `ControlTower`

They should not create:

- a separate communal engine
- a fake nationwide commune layer with no source depth

## First useful outputs

The first valuable outputs are:

- commune-level stricter review flag
- commune-level procedure variant
- commune-level blocker or proof requirement
- explicit manual-review fallback if confidence is low

## Sequence

### PC1

Adapter profile and override layer only.

Use the first build pair from the shortlist:

- `Nyon`
- `Meyrin`

### PC2

Procedure variants and blocker projection.

Use the second build pair from the shortlist:

- `Lausanne`
- `Ville de Fribourg`

### PC3

Later:

- more communes
- richer geodata overlays
- tighter public-system coordination

## Acceptance

This pack is succeeding when SwissBuilding can handle a few communes deeply and
honestly before pretending to cover all communes superficially.
