# VaruNet Production & PaaS Deployment Guide

## 1. Overview & Architectural Deployment Targets

VaruNet is designed as a cloud-native, modular multi-model meteorological blending platform. The architecture separates computation into high-throughput microservices, enabling flexible orchestration:

1. **Local Multi-Service Orchestration**: Fully containerized 5-service stack via **Docker Compose** (`db`, `backend`, `frontend`, `prometheus`, `grafana`).
2. **PaaS Cloud Staging & Live Demonstration**: Zero-cost, high-availability deployment to **Render** utilizing Render Web Services, Static Sites, and Managed PostgreSQL with PostGIS extensions.
3. **Target Production Clusters**: Future scalable transition to managed Kubernetes (EKS/GKE) with horizontal pod autoscalers (HPA) without changing container contracts.

---

## 2. Local Deployment with Docker Compose

The repository root includes a production-ready `docker-compose.yml` orchestrating all five required services on the isolated bridge network `varunet-net`.

### Prerequisites
- Docker Engine 24.0+ and Docker Compose v2.20+
- At least 4 GB available system RAM

### Quickstart
1. **Initialize Environment Variables**:
   Copy the provided `.env.example` template to `.env` at the repository root:
   ```bash
   cp .env.example .env
   ```
   *(Update any default passwords or secrets as appropriate. Never commit `.env` to source control.)*

2. **Build and Launch All Services**:
   ```bash
   docker-compose up --build -d
   ```

3. **Verify Service Health**:
   ```bash
   docker-compose ps
   ```
   All five containers should show state `running` (with `db` healthy):
   - `varunet-db` (Port 5432): PostgreSQL 15 + PostGIS 3.3
   - `varunet-backend` (Port 8000): FastAPI, XGBoost ML engine, TreeSHAP explainer, RBAC
   - `varunet-frontend` (Port 3000): Nginx-served React 18 TypeScript application
   - `varunet-prometheus` (Port 9090): Telemetry scraper polling `backend:8000/metrics`
   - `varunet-grafana` (Port 3001): Dashboards pre-provisioned from `docs/grafana_dashboard.json`

4. **Shutdown and Clean Up**:
   ```bash
   docker-compose down -v
   ```

---

## 3. PaaS Deployment on Render (Recommended Free-Tier)

Render provides native Docker runtime support, managed PostgreSQL, and global CDN static site hosting with automated SSL/TLS certificates.

### Method A: Automated Infrastructure-as-Code via Blueprint (`render.yaml`)

VaruNet includes a root-level `render.yaml` blueprint declaring the database, backend, and frontend services in a single reproducible specification.

1. Push your repository to GitHub or GitLab.
2. Log in to the [Render Dashboard](https://dashboard.render.com).
3. Navigate to **Blueprints** > **New Blueprint Instance**.
4. Connect your VaruNet repository and select the target branch.
5. Render will detect `render.yaml` and provision:
   - `varunet-db`: Managed PostgreSQL 15 database.
   - `varunet-backend`: Docker Web Service running the FastAPI backend.
   - `varunet-frontend`: Static Site serving the Vite/React application.
6. Click **Apply**. Render will generate secure secrets for `JWT_SECRET_KEY` and link `DATABASE_URL` automatically.

---

### Method B: Manual Dashboard Step-by-Step Configuration

#### Step 1: Provision Managed PostgreSQL + PostGIS
1. In Render Dashboard, click **New +** > **PostgreSQL**.
2. Configure settings:
   - **Name**: `varunet-db`
   - **Database**: `varunet`
   - **User**: `postgres`
   - **Region**: Choose Oregon (US West) or your nearest region.
   - **PostgreSQL Version**: 15
   - **Plan**: Free
3. Once provisioned, copy the **Internal Database URL** (for backend communication within Render) or **External Database URL**.
4. Enable PostGIS and initialize schema:
   Connect via `psql` or the Render SQL Console:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```
   Apply the consolidated schema from `database/schema.sql`:
   ```bash
   psql "<EXTERNAL_DATABASE_URL>" -f database/schema.sql
   ```

#### Step 2: Deploy Backend Web Service
1. In Render Dashboard, click **New +** > **Web Service**.
2. Select your repository.
3. Configure settings:
   - **Name**: `varunet-backend`
   - **Region**: Same region as database (e.g., Oregon).
   - **Language / Environment**: `Docker`
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Docker Context**: `.` (Repository root)
   - **Plan**: Free
   - **Health Check Path**: `/` *(returns `{"status":"healthy","service":"VaruNet API"}`)*
4. Under **Environment Variables**, add:
   | Key | Value / Source |
   |-----|----------------|
   | `ENVIRONMENT` | `production` |
   | `PORT` | `8000` |
   | `DATABASE_URL` | *Paste Render Internal Database URL* |
   | `JWT_SECRET_KEY` | *Click "Generate" or provide a secure 64-char random hex string* |
   | `ACCESS_TOKEN_EXPIRE_HOURS` | `24` |
   | `CORS_ORIGINS` | `https://varunet-frontend.onrender.com,http://localhost:3000` |
5. Click **Create Web Service**. Deploy logs will show dependencies installing, the XGBoost model initializing, and Uvicorn starting on `0.0.0.0:8000`.

#### Step 3: Deploy Frontend Static Site
1. In Render Dashboard, click **New +** > **Static Site**.
2. Select your repository.
3. Configure settings:
   - **Name**: `varunet-frontend`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Under **Environment Variables**, add:
   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | `https://varunet-backend.onrender.com/api` |
5. Under **Redirects/Rewrites**:
   - Add a rewrite rule for Single Page Application (SPA) routing:
     - **Source**: `/*`
     - **Destination**: `/index.html`
     - **Action**: `Rewrite`
6. Click **Create Static Site**. Vite will bundle TypeScript modules and publish to Render's CDN.

---

## 4. Environment Variables Reference Guide

All runtime configuration parameters are governed by `.env.example`. No credentials or secret keys are hardcoded in the codebase.

| Variable | Description | Required in Production | Default / Example Value |
|---|---|:---:|---|
| `POSTGRES_DB` | PostgreSQL database name | Yes | `varunet` |
| `POSTGRES_USER` | PostgreSQL superuser username | Yes | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL master password | Yes | *(set securely)* |
| `POSTGRES_HOST` | Database host (Docker service or cloud host) | Yes | `db` or `dpg-xxxx.render.com` |
| `POSTGRES_PORT` | PostgreSQL TCP port | Yes | `5432` |
| `DATABASE_URL` | Full SQLAlchemy/async connection string | Yes | `postgresql://user:pass@host:5432/varunet` |
| `ENVIRONMENT` | Runtime mode (`development` / `production`) | Yes | `production` |
| `PORT` | Backend binding port | No | `8000` |
| `JWT_SECRET_KEY` | HMAC-SHA256 secret key for custom tokens | Yes | *(cryptographically random string)* |
| `ACCESS_TOKEN_EXPIRE_HOURS` | Expiration window for issued JWT tokens | No | `24` |
| `CORS_ORIGINS` | Comma-separated list of allowed web origins | Yes | `https://varunet-frontend.onrender.com` |
| `VITE_API_URL` | Backend API base URL consumed by React client | Yes | `https://varunet-backend.onrender.com/api` |
| `PROMETHEUS_PORT` | Port for local Prometheus scraper | Local Only | `9090` |
| `GRAFANA_PORT` | Port for local Grafana dashboard web UI | Local Only | `3001` |
| `GRAFANA_ADMIN_USER` | Grafana administrator username | Local Only | `admin` |
| `GRAFANA_ADMIN_PASSWORD` | Grafana administrator password | Local Only | *(set securely)* |

---

## 5. Post-Deployment Verification & Smoke Tests

Run these smoke tests against your deployed Render URLs:

### 1. Unauthenticated Public Health Check
```bash
curl -i https://varunet-backend.onrender.com/
```
**Expected Response**: `HTTP/1.1 200 OK`
```json
{
  "status": "healthy",
  "service": "VaruNet Multi-Model Forecast Blending System",
  "version": "1.0.0",
  "timestamp": "2026-09-26T17:15:00.000Z"
}
```

### 2. Prometheus Telemetry Endpoint
```bash
curl -i https://varunet-backend.onrender.com/metrics
```
**Expected Response**: `HTTP/1.1 200 OK` with Prometheus metrics lines including `http_requests_total` and `http_request_duration_highr_seconds_bucket`.

### 3. Interactive OpenAPI Documentation
Visit `https://varunet-backend.onrender.com/docs` in a web browser to inspect Swagger UI interactive schemas and models.

### 4. JWT Authentication Smoke Test
```bash
curl -X POST https://varunet-backend.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"forecaster@varunet.in","password":"password123"}'
```
**Expected Response**: `HTTP/1.1 200 OK`
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "role": "forecaster",
  "email": "forecaster@varunet.in",
  "full_name": "Lead IMD Forecaster",
  "expires_in_hours": 24
}
```

### 5. Blended Inference with SHAP Explanation
```bash
curl -X GET "https://varunet-backend.onrender.com/api/blend?region_id=1&lead_time_hrs=24&variable=rainfall" \
  -H "Authorization: Bearer <TOKEN>"
```
**Expected Response**: `HTTP/1.1 200 OK` with `blended_value`, `confidence_score`, `weights_json`, and natural language `explanation_text`.

### 6. Citizen Public Access Rate Limiting
```bash
curl -i "https://varunet-backend.onrender.com/api/blend/citizen?region_id=1"
```
**Expected Response**: `HTTP/1.1 200 OK` with simplified plain-language labels (`"high confidence"`) and advisory text, rate-limited to 60 requests/minute per client IP.

---

## 6. Live Demonstration Troubleshooting

| Symptom | Root Cause | Solution |
|---|---|---|
| Frontend displays `NetworkError` or `Failed to fetch` | Misconfigured `VITE_API_URL` or CORS mismatch | Verify `VITE_API_URL` in Render Static Site environment points to `https://varunet-backend.onrender.com/api` (without trailing slash) and ensure backend `CORS_ORIGINS` includes the frontend domain. |
| PostGIS functions fail with `type "geometry" does not exist` | PostGIS extension not initialized | Connect to the database and execute `CREATE EXTENSION IF NOT EXISTS postgis;` followed by `\i database/schema.sql`. |
| Backend container build times out on pip install | Slow dependency compilation on free-tier | `backend/Dockerfile` uses `python:3.11-slim` with wheel pre-installs for `scipy`, `xgboost`, and `shap` to minimize compile time. Ensure Docker layer caching is enabled. |
| Memory usage spikes during cold start | SHAP TreeExplainer loading model into RAM | The XGBoost weighting model is lightweight (~627 KB) and consumes under 180 MB RSS RAM during inference, well within Render's 512 MB free-tier limit. |
