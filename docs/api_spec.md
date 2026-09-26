# VaruNet REST API Specification

## Base URL
- **Local Development**: `http://localhost:8000`
- **Render Production**: `https://varunet-backend.onrender.com`

---

## 1. Public & Monitoring Endpoints

### `GET /`
- **Description**: Public liveness and service health check (Unauthenticated).
- **Response**: `200 OK`
```json
{
  "status": "healthy",
  "service": "VaruNet Multi-Model Forecast Blending System",
  "version": "1.0.0",
  "timestamp": "2026-09-26T17:15:00.000Z"
}
```

### `GET /metrics`
- **Description**: Prometheus telemetry scrape target exposing request latency, throughput, and error rates.
- **Response**: `200 OK` (Standard Prometheus exposition format)

### `GET /docs` & `GET /openapi.json`
- **Description**: Interactive OpenAPI Swagger documentation and JSON schema definitions.

---

## 2. Authentication & Authorization Endpoints

### `POST /api/auth/login`
- **Description**: Authenticate user and issue JWT bearer token with embedded role claims.
- **Request Body**:
```json
{
  "email": "forecaster@varunet.in",
  "password": "password123"
}
```
- **Response**: `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "role": "forecaster",
  "email": "forecaster@varunet.in",
  "full_name": "Lead IMD Forecaster",
  "expires_in_hours": 24
}
```

### `GET /api/auth/me`
- **Description**: Retrieve current user profile and role privileges.
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Response**: `200 OK`

---

## 3. Operator Forecasting & Blending Endpoints

### `GET /api/blend`
- **Access**: Forecaster, Admin
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Query Parameters**:
  - `region_id` (integer, required): Target region ID (1–36)
  - `valid_time` (string ISO, optional): Valid date and hour
  - `lead_time_hrs` (integer, optional, default: 24): Forecast lead time (24, 48, 72, 96, 120)
  - `variable` (string, optional, default: "rainfall"): Target variable
  - `regime_id` (integer, optional): Synoptic regime ID
- **Response**: `200 OK`
```json
{
  "blend_id": 101,
  "region_id": 1,
  "region_name": "Kerala",
  "valid_time": "2024-11-20T12:00:00",
  "lead_time_hrs": 24,
  "variable": "rainfall",
  "blended_value": 42.85,
  "confidence_score": 0.88,
  "weights_json": {
    "ECMWF IFS": 0.44,
    "IMD GFS": 0.28,
    "NCMRWF NCUM": 0.16,
    "GraphCast": 0.12
  },
  "explanation_text": "ECMWF IFS received highest weight (44.0%) due to superior historical skill in Kerala during active monsoon regimes.",
  "source_forecasts": {
    "IMD GFS": 40.2,
    "NCMRWF NCUM": 38.5,
    "ECMWF IFS": 45.6,
    "GraphCast": 44.1
  },
  "observed_value": null
}
```

### `GET /api/forecasts`
- **Access**: Forecaster, Admin
- **Query Parameters**: `region_id`, `source_id`, `lead_time_hrs`, `start_time`, `end_time`
- **Description**: Retrieve raw forecasts from underlying NWP and AI sources.

### `GET /api/skill-scores`
- **Access**: Forecaster, Admin
- **Query Parameters**: `region_id`, `source_id`, `season`, `lead_time_bucket`
- **Description**: Retrieve deterministic historical RMSE, MAE, and signed bias records.

### `GET /api/alerts`
- **Access**: Forecaster, Admin
- **Query Parameters**: `region_id`, `severity` (`Yellow`, `Orange`, `Red`), `active_only`
- **Description**: Retrieve prioritized meteorological alerts with full sector guidance breakdown (agriculture, aviation, public safety).

---

## 4. Citizen Public Endpoints

### `GET /api/blend/citizen`
- **Access**: Public / Citizen (Rate-limited: 60 req/min)
- **Query Parameters**: `region_id`, `valid_time`, `lead_time_hrs`
- **Response**: `200 OK`
```json
{
  "city_name": "Kochi",
  "region_name": "Kerala",
  "forecast_summary": "Moderate to heavy rainfall expected across coastal districts (approx 43 mm).",
  "confidence_label": "High Confidence",
  "advisory_sentence": "Take necessary precautions when traveling near low-lying coastal areas.",
  "valid_time": "2024-11-20T12:00:00"
}
```

### `GET /api/alerts/citizen`
- **Access**: Public / Citizen (Rate-limited: 60 req/min)
- **Query Parameters**: `region_id`
- **Response**: `200 OK` (Simplified public safety alert summaries without technical telemetry).
