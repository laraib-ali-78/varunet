-- Migration 005: Create observations table

CREATE TABLE IF NOT EXISTS observations (
    region_id INTEGER NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    valid_time TIMESTAMPTZ NOT NULL,
    variable VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (region_id, valid_time, variable)
);

CREATE INDEX IF NOT EXISTS idx_observations_region_id ON observations(region_id);
CREATE INDEX IF NOT EXISTS idx_observations_valid_time ON observations(valid_time);
