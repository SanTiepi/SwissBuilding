# ADR-004: ChangeSignal Compatibility and BuildingSignal Canonicalization

Status: Accepted
Date: 2026-03-28

## Decision

`BuildingSignal` (in `building_change.py`) is the canonical signal model. `ChangeSignal` (legacy) is a compatibility surface only.

## Allowed

- Reading ChangeSignal for existing consumers
- Bridging ChangeSignal reads through change_tracker_service
- Keeping change_signal_generator as a detection engine that feeds BuildingSignal

## Forbidden

- Adding new fields or semantics to ChangeSignal
- Creating new consumers that depend on ChangeSignal
- Expanding the change_signals API with new routes or response shapes

## Migration Path

1. Inventory all ChangeSignal consumers (frontend pages, API consumers, services)
2. Migrate each consumer to BuildingSignal reads
3. Once consumer count reaches near-zero, plan data migration and table retirement
4. Bridge remains until retirement is safe

## Trigger for Removal

- All frontend pages read from canonical change objects
- No service writes to ChangeSignal directly (only through bridge)
- Confidence that historical signal data is either migrated or no longer needed
