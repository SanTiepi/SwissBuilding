# ADR-003: TruthRitual as Sole Transition Layer

Status: Accepted
Date: 2026-03-28

## Decision

All truth/publication transitions (validate, freeze, publish, transfer, acknowledge, reopen, supersede, receipt) must go through `ritual_service.py` and be recorded in the `truth_rituals` table.

## Allowed

- Domain services calling ritual_service after their domain-specific logic
- Domain services adding domain context alongside the ritual trace
- Reading ritual history for audit, provenance, and compliance

## Forbidden

- Implementing freeze/publish/acknowledge/supersede/reopen/receipt in domain services without calling ritual_service
- Creating domain-specific audit tables that duplicate ritual semantics
- Any truth transition that is not traceable in truth_rituals

## Current State

- passport_envelope_service: wired (freeze/publish/transfer/acknowledge/supersede call ritual_service)
- truth_service: wired (verify_claim and supersede_claim call ritual_service)
- compliance_artefact_service: NOT YET wired (legacy, to be bridged in Pass 2)
