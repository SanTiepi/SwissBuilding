# ADR-001: V3 Canonical Roots

Status: Accepted
Date: 2026-03-28

## Decision

SwissBuilding defines 14 canonical root families. No module, page, workflow, or domain pack may become first-class unless it strengthens at least one root family.

## Root Families

Building, Spatial, Party, BuildingCase, Document, Evidence, Claim, Decision, Publication, Action, OperationalFinance, Transfer, Change, Intent.

## Allowed

- New models that strengthen a canonical root
- New services that compose canonical roots
- New projections (read-side) from canonical roots

## Forbidden

- New models that create a parallel root outside the 14 families
- New services that introduce their own truth/state independent of canonical roots
- Domain packs that cannot name which roots they strengthen

## Compatibility

Legacy models (Intervention, ChangeSignal, ComplianceArtefact, etc.) remain as subordinate domain objects or compatibility surfaces. They do not introduce new canonical semantics.

## Triggers for Review

- Any PR that adds a new model not attached to a canonical root
- Any PR that adds a new standalone page not under a master workspace
