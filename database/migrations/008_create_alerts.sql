-- Migration 008: Create alerts table

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
