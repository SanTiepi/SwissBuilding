# Enterprise Rollout Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [enterprise-identity-and-tenant-governance-program.md](./enterprise-identity-and-tenant-governance-program.md)
- [product-excellence-vs-adoption-and-market-lock-in-2026-03-25.md](./product-excellence-vs-adoption-and-market-lock-in-2026-03-25.md)

The goal is to make SwissBuilding easier to roll out inside serious accounts
without turning it into identity middleware first.

## Hard rule

Enterprise rollout should reduce friction at adoption boundaries:

- who gets access
- what they can see
- how they are invited
- how they are revoked
- how support actions are audited

If a feature does not reduce rollout friction or governance risk, it is not
enterprise rollout.

## Build posture

Build:

- clearer organization boundaries
- delegated and temporary access
- audited privileged actions
- buyer-safe rollout semantics

Do not build:

- full IAM replacement
- deep SSO plumbing before product boundaries are clear
- enterprise clutter without buyer pull

## Minimum objects

### TenantBoundary

Represents the effective boundary for an account or organization scope.

Minimum shape:

- `id`
- `tenant_code`
- `scope_type`
- `visibility_rules`
- `support_policy`

### DelegatedAccessGrant

Represents bounded delegated or temporary access.

Minimum shape:

- `id`
- `target_scope`
- `grantee_org_id`
- `grantee_user_id`
- `grant_reason`
- `starts_at`
- `ends_at`
- `revoked_at`

### PrivilegedAccessEvent

Represents a support or admin action that needs auditability.

Minimum shape:

- `id`
- `actor_user_id`
- `event_type`
- `target_scope`
- `reason`
- `occurred_at`

## Existing anchors to reuse

Enterprise rollout should extend:

- `WorkspaceMembership`
- shared packs and viewer flows
- future partner trust and authority flow surfaces

It should not create:

- a separate enterprise product shell
- a second permission system detached from building truth

## First useful outputs

The first valuable outputs are:

- safer external viewer grants
- clearer tenant or org scoping
- audited support actions
- bounded temporary access

## Sequence

### ER1

Boundary and grant layer only.

### ER2

Privileged audit layer.

### ER3

Later:

- enterprise identity provider mapping
- broader admin control plane

## Acceptance

This pack is useful when SwissBuilding becomes easier to deploy, explain, and
trust inside larger accounts.
