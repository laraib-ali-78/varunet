-- Migration 007: Create blended_forecasts table

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
