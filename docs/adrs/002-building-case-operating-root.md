# ADR-002: BuildingCase as Operating Root

Status: Accepted
Date: 2026-03-28

## Decision

BuildingCase is the operating episode root that unifies all bounded engagements with a building: works, permits, authority submissions, tenders, claims, incidents, maintenance, funding, transactions, transfers.

## Allowed

- Linking Intervention, TenderRequest, FormInstance, ComplianceArtefact to BuildingCase
- Creating new case types as the product evolves
- Using case_id as optional FK on Change, Truth, Intent, Transfer objects

## Forbidden

- Creating new episode-level objects that bypass BuildingCase
- Implementing case-like lifecycle management in domain-specific services without linking to BuildingCase
- Treating Intervention or TenderRequest as standalone operating roots for new features

## Compatibility

Intervention and TenderRequest remain as domain objects. BuildingCase wraps them via optional FKs. Existing code that uses Intervention directly continues to work. New features should create/link a BuildingCase.
