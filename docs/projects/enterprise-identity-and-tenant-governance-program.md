# Enterprise Identity and Tenant Governance Program

## Mission

Prepare SwissBuildingOS for enterprise-grade identity, delegation, tenant boundaries, and audited support workflows without turning the product into identity middleware.

## Why This Matters

As SwissBuilding moves toward:
- organizations
- invitations
- external viewers
- embedded channels
- partner gateways
- insurer / lender / authority packs

it must become safer to explain:
- who can see what
- for how long
- under which tenant boundary
- under which delegated authority
- under what support or impersonation context

Without this layer, enterprise accounts will see the product as operationally powerful but governance-light.

## Strategic Outcomes

- stronger tenant isolation semantics
- enterprise-ready identity posture
- safer delegation and temporary access models
- auditable support operations
- lower retrofit debt for larger European accounts

## Product Scope

This program should produce:
- clearer tenant and organization boundaries
- stronger identity-provider readiness
- bounded delegated access
- auditable privileged operations
- safer foundations for embedded and externally shared surfaces

It should not become:
- a full IAM replacement
- a premature enterprise feature maze

## Recommended Workstreams

### Workstream A - Identity provider readiness

Prepare a credible path for:
- OIDC
- SAML
- enterprise SSO mapping
- future SCIM-like provisioning direction

Expected outputs:
- architecture direction
- config surface
- role/group mapping model
- session boundary expectations

Candidate objects:
- `IdentityProviderConfig`
- `RoleMappingRule`

### Workstream B - Tenant and organization boundary hardening

Make tenant semantics easier to reason about across:
- organizations
- projects
- buildings
- shared packs
- contributor surfaces

Expected outputs:
- clearer ownership model
- explicit tenant-bound queries where needed
- documented rules for cross-org visibility

Candidate objects:
- `TenantBoundary`
- `TenantScopeRule`

### Workstream C - Delegation and temporary access

Support controlled access for:
- contractors
- reviewers
- due diligence viewers
- support engineers
- temporary external participants

Expected semantics:
- scope
- duration
- reason
- revocation
- auditability

Candidate objects:
- `DelegatedAccessGrant`
- `TemporaryRoleGrant`

### Workstream D - Audited admin and support actions

Prepare for safe support workflows:
- impersonation
- delegated troubleshooting
- emergency access
- read-only support mode

Expected outputs:
- explicit privileged-action audit trail
- UI warnings / visibility
- revocation and session boundaries

Candidate objects:
- `ImpersonationAudit`
- `PrivilegedAccessEvent`

### Workstream E - Enterprise control plane hooks

Make the product ready for enterprise deployment questions:
- account-level controls
- policy inheritance
- access review
- external sharing constraints
- IP/domain/user-group restrictions later if needed

## Candidate Improvements

- `TenantBoundary`
- `TenantScopeRule`
- `DelegatedAccessGrant`
- `TemporaryRoleGrant`
- `ImpersonationAudit`
- `PrivilegedAccessEvent`
- `IdentityProviderConfig`
- `RoleMappingRule`

## Acceptance Criteria

- the product has a credible enterprise identity direction
- tenant boundaries are clearer and less implicit
- delegation and support access have safer semantics
- future embedded, partner, and external sharing programs rest on stronger governance foundations

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
