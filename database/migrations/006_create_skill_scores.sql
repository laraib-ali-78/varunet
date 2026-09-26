-- Migration 006: Create skill_scores table

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
