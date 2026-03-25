# Consumer Bridge v1 — Runbook

## Fetch a diagnostic package (pull-mode)

```
POST /diagnostic-publications/fetch/{dossier_ref}
Authorization: Bearer <jwt>
```

The endpoint fetches the package from Batiscan, validates the contract, maps to internal schema, and ingests. Returns `consumer_state` and `publication_id`.

## Read consumer state

Check `DiagnosticReportPublication` fields:
- `consumer_state` — current state (matched, ingested, review_required, auth_error, not_found, fetch_error, validation_error, rejected_source)
- `contract_version` — schema version used (canonical: "v1")
- `fetch_error` — last error message if fetch failed
- `fetched_at` — timestamp of last fetch

```
GET /diagnostic-publications/{id}
```

## Identify a replay (idempotent)

When `payload_hash` matches an existing publication, the system:
1. Returns the existing publication (no duplicate row)
2. Does NOT emit new domain events
3. Updates `consumer_state` and `fetched_at`

The caller sees the same `publication_id` on repeated calls.

## Handle review_required

When building matching is ambiguous (e.g., address partial match with multiple candidates), `consumer_state` is set to `review_required`.

Admin manual match:
```
POST /diagnostic-publications/{id}/match
Body: {"building_id": "<uuid>"}
Authorization: Bearer <admin-jwt>
```

## Push-mode webhook

```
POST /diagnostic-publications
Body: DiagnosticPublicationPackage JSON
```

Contract validation runs on push-mode too. Invalid payloads return 422.

## Status codes and meaning

| consumer_state | Meaning |
|---|---|
| `matched` | Building auto-matched (egid/egrid) |
| `ingested` | Ingested but no building match found |
| `review_required` | Ambiguous match, needs admin review |
| `auth_error` | BATISCAN_API_KEY invalid or expired |
| `not_found` | Dossier reference not found on producer |
| `rejected_source` | Producer returned 422 (package not eligible, readiness_blocked, etc.) |
| `fetch_error` | Network error (timeout, connection refused, invalid JSON, unexpected HTTP status) |
| `validation_error` | Payload failed contract validation (missing fields, unknown source_system, etc.) |
| `ingest_error` | Unexpected error during DB ingestion |

## What 422 means

When the producer (Batiscan) returns 422, the package is not eligible for publication. Common reasons:
- `readiness_blocked` — diagnostic not yet validated
- Missing required fields on the producer side
- Publication snapshot incomplete

The consumer stores this as `rejected_source`.

## What auth_error means

`BATISCAN_API_KEY` is invalid or expired. Check:
1. `BATISCAN_API_KEY` environment variable is set
2. The key has not been rotated on the Batiscan side
3. The key has the correct scopes

## Known limitations of v1

1. Only `source_system: "batiscan"` is supported
2. Schema version normalized to "v1" (accepts "1", "1.0", "v1")
3. `object_type` field is logged but not enforced (forward compat)
4. Building matching by address is partial (ILIKE) and may need manual review
5. Domain event handlers are placeholders (log only) — passport/trust refresh is future work
6. No retry mechanism for transient fetch errors — caller must retry
7. No webhook authentication (push-mode) — relies on network-level security

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `auth_error` on every fetch | API key invalid | Rotate `BATISCAN_API_KEY` |
| `fetch_error: timed out` | Batiscan unreachable | Check network/firewall, verify `BATISCAN_API_URL` |
| `fetch_error: Cannot connect` | DNS/network issue | Verify `BATISCAN_API_URL` resolves |
| `validation_error: Missing required field: payload_hash` | Producer sent empty hash | Fix on producer side |
| `review_required` stuck | Ambiguous address match | Admin manual match via POST .../match |
| Same publication_id on repeated fetch | Idempotent replay (same payload_hash) | Expected behavior, no action needed |
| `validation_error` on webhook | Push payload missing required fields | Fix producer payload |
| `ingest_error` | Unexpected DB error | Check backend logs, verify DB connectivity |
| `rejected_source` | Producer says not eligible | Check diagnostic status on Batiscan side |
| Malformed egid warning in logs | egid value not numeric | Producer should send integer egid |
