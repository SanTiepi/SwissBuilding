# Truth API v1

Read-first external API layer exposing canonical building intelligence projections.

## Versioning

All Truth API endpoints live under `/api/v1/truth/`. The `v1` prefix is embedded in the URL path. Every response includes `api_version: "1.0"` and `generated_at` timestamp.

When breaking changes are needed, a `/v2/truth/` prefix will be introduced. V1 remains stable until explicitly deprecated.

## Authentication

All endpoints require a valid JWT bearer token (same auth as internal APIs). Role-based access control applies — the user must have `read` permission on the relevant resource.

## Response Format

Every response is a JSON envelope containing:

| Field | Type | Description |
|---|---|---|
| `api_version` | string | Always `"1.0"` for this version |
| `generated_at` | ISO datetime | Server timestamp when response was computed |
| `links` | object | HATEOAS-style links to related endpoints |
| (payload) | varies | Endpoint-specific data |

## Rate Limiting

Rate limiting is not yet enforced. Future versions will include:
- Per-token rate limits (e.g. 100 req/min)
- `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers
- 429 responses with `Retry-After` header

## Endpoint Inventory

### Building Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/truth/buildings/{id}/summary` | Building summary with optional section filtering |
| GET | `/api/v1/truth/buildings/{id}/identity-chain` | EGID, EGRID, RDPPF identity chain |
| GET | `/api/v1/truth/buildings/{id}/safe-to-x` | SafeToX verdicts (start, sell, insure, etc.) |
| GET | `/api/v1/truth/buildings/{id}/unknowns` | Unknowns ledger |
| GET | `/api/v1/truth/buildings/{id}/changes` | Change timeline with optional `since` filter |
| GET | `/api/v1/truth/buildings/{id}/passport` | Full passport envelope with optional redaction |
| GET | `/api/v1/truth/buildings/{id}/packs/{type}` | Audience-specific pack (authority, owner, etc.) |

### Portfolio Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/truth/portfolio/overview` | Portfolio-level overview with grades, priorities, budget |
| GET | `/api/v1/truth/portfolio/alerts` | Predictive alerts across portfolio |

## Query Parameters

### Summary sections

`GET /buildings/{id}/summary?include_sections=identity&include_sections=grade`

Available sections: `identity`, `spatial`, `grade`, `completeness`, `readiness`, `trust`, `pollutants`, `diagnostics_summary`. Omit to get all sections.

### SafeToX type filter

`GET /buildings/{id}/safe-to-x?types=start&types=sell`

Available types: `start`, `tender`, `reopen`, `requalify`, `sell`, `insure`, `finance`, `lease`.

### Change timeline

`GET /buildings/{id}/changes?since=2025-01-01T00:00:00Z`

### Redaction profiles

`GET /buildings/{id}/passport?redaction_profile=external`

Profiles:
- `none` (default) — full data
- `external` — strips detailed trust breakdown, masks sensitive fields

### Pack types

`GET /buildings/{id}/packs/authority`

Available: `authority`, `owner`, `insurer`, `contractor`, `notary`, `transfer`.

## What This API Does NOT Allow

- **No writes** — all endpoints are GET-only, no mutations
- **No creation** — cannot create buildings, diagnostics, or any entities
- **No deletion** — cannot remove or archive anything
- **No side effects** — reading does not trigger generators or background jobs
- **No raw data** — returns projections/summaries, not raw database rows

## Schema Versioning

All response models are suffixed with `V1` (e.g. `BuildingSummaryV1`, `PassportV1`). When the schema evolves in a backward-incompatible way, new `V2` models will be created alongside a `/v2/truth/` endpoint prefix.
