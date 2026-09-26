-- =============================================================================
-- VaruNet Database Schema
-- Target: PostgreSQL with PostGIS extension
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. forecast_sources
CREATE TABLE IF NOT EXISTS forecast_sources (
    source_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL
);

-- 2. regions
CREATE TABLE IF NOT EXISTS regions (
    region_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    geometry GEOMETRY(Geometry, 4326) NOT NULL
);

-- 3. regimes
CREATE TABLE IF NOT EXISTS regimes (
    regime_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- 4. forecasts
CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id BIGSERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES forecast_sources(source_id) ON DELETE CASCADE,
    region_id INTEGER NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    valid_time TIMESTAMPTZ NOT NULL,
    lead_time_hrs INTEGER NOT NULL,
    variable VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_forecasts_source_id ON forecasts(source_id);
CREATE INDEX IF NOT EXISTS idx_forecasts_region_id ON forecasts(region_id);
CREATE INDEX IF NOT EXISTS idx_forecasts_valid_time ON forecasts(valid_time);

-- 5. observations
CREATE TABLE IF NOT EXISTS observations (
    region_id INTEGER NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    valid_time TIMESTAMPTZ NOT NULL,
    variable VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (region_id, valid_time, variable)
);

CREATE INDEX IF NOT EXISTS idx_observations_region_id ON observations(region_id);
CREATE INDEX IF NOT EXISTS idx_observations_valid_time ON observations(valid_time);

-- 6. skill_scores
CREATE TABLE IF NOT EXISTS skill_scores (
    score_id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES forecast_sources(source_id) ON DELETE CASCADE,
    region_id INTEGER NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    regime_id INTEGER NOT NULL REFERENCES regimes(regime_id) ON DELETE CASCADE,
    season VARCHAR(50) NOT NULL,
    lead_time_bucket VARCHAR(50) NOT NULL,
    variable VARCHAR(50) NOT NULL,
    rmse DOUBLE PRECISION,
    mae DOUBLE PRECISION,
    bias DOUBLE PRECISION,
    sample_size INTEGER NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_skill_scores_source_id ON skill_scores(source_id);
CREATE INDEX IF NOT EXISTS idx_skill_scores_region_id ON skill_scores(region_id);
CREATE INDEX IF NOT EXISTS idx_skill_scores_season ON skill_scores(season);
CREATE INDEX IF NOT EXISTS idx_skill_scores_lead_time_bucket ON skill_scores(lead_time_bucket);

-- 7. blended_forecasts
CREATE TABLE IF NOT EXISTS blended_forecasts (
    blend_id BIGSERIAL PRIMARY KEY,
    region_id INTEGER NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    valid_time TIMESTAMPTZ NOT NULL,
    lead_time_hrs INTEGER NOT NULL,
    variable VARCHAR(50) NOT NULL,
    blended_value DOUBLE PRECISION NOT NULL,
    weights_json JSONB NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_blended_forecasts_region_id ON blended_forecasts(region_id);
CREATE INDEX IF NOT EXISTS idx_blended_forecasts_valid_time ON blended_forecasts(valid_time);

-- 8. alerts
CREATE TABLE IF NOT EXISTS alerts (
    alert_id SERIAL PRIMARY KEY,
    region_id INTEGER NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    valid_time TIMESTAMPTZ NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    sector_guidance_text TEXT NOT NULL,
    triggered_by BIGINT NOT NULL REFERENCES blended_forecasts(blend_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alerts_region_id ON alerts(region_id);
CREATE INDEX IF NOT EXISTS idx_alerts_valid_time ON alerts(valid_time);

-- 9. users
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL
);

-- 10. explanations
CREATE TABLE IF NOT EXISTS explanations (
    explanation_id SERIAL PRIMARY KEY,
    blend_id BIGINT NOT NULL REFERENCES blended_forecasts(blend_id) ON DELETE CASCADE,
    explanation_text TEXT NOT NULL,
    feature_attributions_json JSONB NOT NULL
);
