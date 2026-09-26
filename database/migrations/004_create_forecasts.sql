-- Migration 004: Create forecasts table

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
