# SwissBuildingOS — API Reference

Base URL: `/api/v1`

All endpoints return JSON. Authenticated endpoints require a `Bearer` token in the `Authorization` header.

---

## Authentication

| Method | Path                  | Description        | Permission |
|--------|-----------------------|--------------------|------------|
| POST   | `/api/v1/auth/login`    | Login              | public     |
| POST   | `/api/v1/auth/register` | Register (owner role only) | public |
| GET    | `/api/v1/auth/me`       | Get current user   | authenticated |

## Buildings

| Method | Path                        | Description      | Permission       |
|--------|-----------------------------|------------------|------------------|
| GET    | `/api/v1/buildings`           | List buildings   | buildings:list   |
| POST   | `/api/v1/buildings`           | Create building  | buildings:create |
| GET    | `/api/v1/buildings/{id}`      | Get building     | buildings:read   |
| PUT    | `/api/v1/buildings/{id}`      | Update building  | buildings:update |
| DELETE | `/api/v1/buildings/{id}`      | Delete building  | buildings:delete |

## Diagnostics

| Method | Path                                          | Description          | Permission           |
|--------|-----------------------------------------------|----------------------|----------------------|
| GET    | `/api/v1/buildings/{building_id}/diagnostics`   | List diagnostics     | diagnostics:list     |
| POST   | `/api/v1/buildings/{building_id}/diagnostics`   | Create diagnostic    | diagnostics:create   |
| GET    | `/api/v1/diagnostics/{id}`                      | Get diagnostic       | diagnostics:read     |
| PUT    | `/api/v1/diagnostics/{id}`                      | Update diagnostic    | diagnostics:update   |
| PATCH  | `/api/v1/diagnostics/{id}/validate`             | Validate diagnostic  | diagnostics:validate |
| POST   | `/api/v1/diagnostics/{id}/upload-report`        | Upload report PDF    | diagnostics:update   |

## Samples

| Method | Path                                          | Description    | Permission     |
|--------|-----------------------------------------------|----------------|----------------|
| GET    | `/api/v1/diagnostics/{diagnostic_id}/samples`   | List samples   | samples:list   |
| POST   | `/api/v1/diagnostics/{diagnostic_id}/samples`   | Create sample  | samples:create |
| PUT    | `/api/v1/samples/{id}`                          | Update sample  | samples:update |
| DELETE | `/api/v1/samples/{id}`                          | Delete sample  | samples:delete |

## Risk Analysis

| Method | Path                                          | Description                | Permission            |
|--------|-----------------------------------------------|----------------------------|-----------------------|
| POST   | `/api/v1/risk-analysis/simulate`                | Run renovation simulation  | risk_analysis:execute |
| GET    | `/api/v1/risk-analysis/building/{building_id}`  | Get building risk score    | risk_analysis:read    |

## Pollutant Map

| Method | Path                              | Description          | Permission         |
|--------|-----------------------------------|----------------------|--------------------|
| GET    | `/api/v1/pollutant-map/buildings`   | Map buildings query  | pollutant_map:read |
| GET    | `/api/v1/pollutant-map/heatmap`     | Heatmap data         | pollutant_map:read |
| GET    | `/api/v1/pollutant-map/clusters`    | Cluster data         | pollutant_map:read |

## Documents

| Method | Path                                          | Description       | Permission       |
|--------|-----------------------------------------------|-------------------|------------------|
| POST   | `/api/v1/buildings/{building_id}/documents`     | Upload document   | documents:create |
| GET    | `/api/v1/buildings/{building_id}/documents`     | List documents    | documents:list   |
| GET    | `/api/v1/documents/{id}/download`               | Download document | documents:read   |

## Events

| Method | Path                                      | Description   | Permission    |
|--------|-------------------------------------------|---------------|---------------|
| GET    | `/api/v1/buildings/{building_id}/events`    | List events   | events:list   |
| POST   | `/api/v1/buildings/{building_id}/events`    | Create event  | events:create |

## Users

| Method | Path                  | Description      | Permission   |
|--------|-----------------------|------------------|--------------|
| GET    | `/api/v1/users`         | List users       | users:list   |
| POST   | `/api/v1/users`         | Create user      | users:create |
| PUT    | `/api/v1/users/{id}`    | Update user      | users:update |
| DELETE | `/api/v1/users/{id}`    | Deactivate user  | users:delete |

## System

| Method | Path       | Description        | Permission |
|--------|------------|--------------------|------------|
| GET    | `/health`    | Health check       | public     |
| GET    | `/metrics`   | Prometheus metrics | public     |

---

## Request / Response Examples

### POST /api/v1/auth/login

**Request**
```json
{
  "email": "diagnostician@example.ch",
  "password": "s3cur3Pa$$"
}
```

**Response** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "b7e2c1a0-4f3d-4e5a-9c8b-1a2b3c4d5e6f",
    "email": "diagnostician@example.ch",
    "role": "diagnostician",
    "organization_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

### POST /api/v1/buildings

**Request**
```json
{
  "name": "Immeuble Rue du Lac 12",
  "address": "Rue du Lac 12",
  "postal_code": "1000",
  "city": "Lausanne",
  "canton": "VD",
  "construction_year": 1965,
  "building_type": "residential",
  "latitude": 46.5197,
  "longitude": 6.6323,
  "organization_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response** `201 Created`
```json
{
  "id": "c3d4e5f6-a1b2-7890-cdef-567890abcdef",
  "name": "Immeuble Rue du Lac 12",
  "address": "Rue du Lac 12",
  "postal_code": "1000",
  "city": "Lausanne",
  "canton": "VD",
  "construction_year": 1965,
  "building_type": "residential",
  "latitude": 46.5197,
  "longitude": 6.6323,
  "organization_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "created_at": "2026-03-07T10:30:00Z",
  "updated_at": "2026-03-07T10:30:00Z"
}
```

### POST /api/v1/risk-analysis/simulate

**Request**
```json
{
  "building_id": "c3d4e5f6-a1b2-7890-cdef-567890abcdef",
  "scenario": "full_decontamination",
  "pollutants": ["asbestos", "lead", "pcb"],
  "affected_area_m2": 320.5
}
```

**Response** `200 OK`
```json
{
  "building_id": "c3d4e5f6-a1b2-7890-cdef-567890abcdef",
  "scenario": "full_decontamination",
  "estimated_cost_chf": 185000,
  "cost_breakdown": {
    "asbestos_removal": 95000,
    "lead_remediation": 52000,
    "pcb_remediation": 38000
  },
  "duration_weeks": 12,
  "regulations_applicable": ["CFST 6503", "OLED", "ORRChim"],
  "compliance_status": "requires_action",
  "generated_at": "2026-03-07T10:45:00Z"
}
```
