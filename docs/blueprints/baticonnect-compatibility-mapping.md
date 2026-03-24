# BatiConnect Compatibility Mapping

## Purpose
Maps current SwissBuildingOS API endpoints to BatiConnect canonical entities. Current endpoints continue working unchanged. Canonical endpoints will be added alongside in future waves.

## Current API → Canonical Entity Mapping

### Buildings → Asset (first shape)
| Current Endpoint | Current Entity | Canonical Entity | Adapter Path |
|---|---|---|---|
| GET /api/v1/buildings | Building | Asset (via adapter) | AssetView composes BuildingRead + ownership + units + portfolios |
| POST /api/v1/buildings | Building | Asset | BuildingCreate stays, organization_id added as optional field |
| GET /api/v1/buildings/{id} | Building | Asset | BuildingRead stays, AssetView adds relations |
| PUT /api/v1/buildings/{id} | Building | Asset | BuildingUpdate stays unchanged |
| GET /api/v1/buildings/{id}/diagnostics | Diagnostic | Diagnostic (unchanged) | No adapter needed |
| GET /api/v1/buildings/{id}/zones | Zone | Zone (unchanged) | No adapter needed |
| GET /api/v1/buildings/{id}/documents | Document | Document (unchanged) | DocumentLink junction in BC2 |

### Organizations → Organization + Party link
| Current Endpoint | Canonical Entity | Change |
|---|---|---|
| GET/POST /api/v1/organizations | Organization | Gains optional contact_person_id |
| GET /api/v1/organizations/{id}/members | User | Unchanged |

### Users → User + Party link
| Current Endpoint | Canonical Entity | Change |
|---|---|---|
| POST /api/v1/auth/login | User | Unchanged |
| GET /api/v1/users | User | Gains optional linked_contact_id |

### New Canonical Endpoints (future waves)
| Planned Endpoint | Entity | Wave |
|---|---|---|
| /api/v1/contacts | Contact (Party) | post-BC1 supervisor wiring |
| /api/v1/party-roles | PartyRoleAssignment | post-BC1 supervisor wiring |
| /api/v1/portfolios | Portfolio | post-BC1 supervisor wiring |
| /api/v1/buildings/{id}/units | Unit | post-BC1 supervisor wiring |
| /api/v1/buildings/{id}/ownership | OwnershipRecord | post-BC1 supervisor wiring |
| /api/v1/assets/{id} | AssetView | post-BC1 supervisor wiring |

## Adapter Strategy

### Building → Asset Adapter
- `AssetView` schema wraps `BuildingRead` and adds:
  - `ownership_records: list[OwnershipRecordListRead]`
  - `units: list[UnitListRead]`
  - `portfolios: list[PortfolioListRead]`
- No data duplication — same DB row, different projection
- Current GET /api/v1/buildings/{id} returns BuildingRead (unchanged)
- Future GET /api/v1/assets/{id} returns AssetView (new endpoint)

### Party → Contact + User Bridge
- Contact exists for non-platform parties (owners, tenants, notaries)
- User.linked_contact_id optionally bridges to Contact
- PartyRoleAssignment.party_type distinguishes: contact, user, organization
- Old Assignment model stays for backward compat

### Ownership → OwnershipRecord + PartyRoleAssignment
- Building.owner_id (legacy) stays for backward compat
- OwnershipRecord provides full ownership history with shares, acquisition data
- PartyRoleAssignment with role=legal_owner provides lightweight role view

## Breaking Changes
None. All current API endpoints continue working unchanged.

## Migration Path
1. BC1 (this wave): models + schemas + migrations — no routes
2. Post-BC1 supervisor: hub-file wiring + new routes
3. BC2: Lease/Contract/Insurance/Financial + DocumentLink
4. BC3: Read-model extensions + adapter endpoints
