# VaruNet — Hybrid AI–NWP Multi-Model Forecast Blending System
> **Smart India Hackathon (SIH) — Problem Statement SIH26081**

VaruNet is an operational-grade meteorological intelligence platform that synthesizes numerical weather prediction (NWP) models (**IMD GFS**, **NCMRWF NCUM**, **ECMWF IFS**) with state-of-the-art AI weather models (**DeepMind GraphCast**). 

By dynamically computing situational weights with an **XGBoost regressor** and explaining feature attributions using **TreeSHAP**, VaruNet delivers high-accuracy blended forecasts with deterministic confidence intervals, outperforming naive ensemble averages by **+7.63% RMSE** and **+8.16% MAE** (and +39.0% over raw NWP models).

---

## Key Capabilities

1. **Dynamic Situational Weighting**: MultiOutput XGBoost trained on spatio-temporal features, cyclical day-of-year embeddings, lead time, and inter-source variance.
2. **Local Explainability (TreeSHAP)**: Generates deterministic natural-language justifications for every blend without hallucinations.
3. **Statistical Confidence Intervals**: Formulated directly from inter-source dispersion — high convergence indicates high confidence, divergence triggers calibrated warnings.
4. **Sector-Specific Early Warnings**: Automatically prioritizes severe weather alerts for **Agriculture**, **Aviation**, and **Public Safety**.
5. **Dual Interface**:
   - **Operator Command Dashboard**: Interactive geospatial vector map (**Leaflet**) and performance analytics (**Recharts**).
   - **Citizen Weather Portal**: Clean, plain-language forecasts and one-sentence public advisories with non-technical confidence badges.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend API** | Python 3.11, FastAPI, Pydantic v2, Custom JWT RBAC, Prometheus Instrumentator |
| **Machine Learning** | XGBoost, TreeSHAP, Scipy Constrained Quadratic Optimization |
| **Database** | PostgreSQL 15/16 + PostGIS Extension (10 relational spatial tables) |
| **Frontend** | React 18, TypeScript, Vite, Recharts, Leaflet (`react-leaflet`) |
| **Observability** | Prometheus (metrics scraping) + Grafana (latency dashboard) |
| **Orchestration** | Docker Compose (local) / Railway + Vercel (cloud production) |

---

## Quickstart: Run Locally in Under 2 Minutes

### Prerequisites
- Docker Engine & Docker Compose (`docker-compose`)

### Launch
```bash
# 1. Clone repository
git clone <REPO_URL>
cd varunet

# 2. Configure environment
cp .env.example .env

# 3. Start all 5 microservices
docker-compose up --build -d
```

### Access Services
- **Citizen Portal & Operator Dashboard**: `http://localhost:3000`
- **FastAPI OpenAPI Interactive Docs**: `http://localhost:8000/docs`
- **Public Health Check**: `http://localhost:8000/`
- **Prometheus Telemetry Scraper**: `http://localhost:9090`
- **Grafana Latency Dashboard**: `http://localhost:3001` (Default login: `admin` / `admin`)

---

## Testing & Verification

```bash
# Run complete backend unit test suite (24 tests)
python -m pytest backend/tests

# Run held-out validation evaluation
python -m ml.training.evaluate

# Build frontend production bundle
cd frontend && npm install && npm run build
```

---

## Live Deployment Links

- **Live Frontend Portal (Vercel)**: [https://frontend-two-tan-24.vercel.app](https://frontend-two-tan-24.vercel.app)
- **Live Backend API (Railway)**: [https://backend-production-538ef.up.railway.app](https://backend-production-538ef.up.railway.app)
- **Interactive OpenAPI / Swagger Documentation**: [https://backend-production-538ef.up.railway.app/docs](https://backend-production-538ef.up.railway.app/docs)
- **Prometheus Telemetry Scraper**: [https://prometheus-production-3385.up.railway.app](https://prometheus-production-3385.up.railway.app)
- **Grafana Live Latency Dashboard**: [https://grafana-production-67a9.up.railway.app/d/varunet-api-latency](https://grafana-production-67a9.up.railway.app/d/varunet-api-latency) (Login: `admin` / `admin`)
