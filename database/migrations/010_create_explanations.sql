-- Migration 010: Create explanations table

CREATE TABLE IF NOT EXISTS explanations (
    explanation_id SERIAL PRIMARY KEY,
    blend_id BIGINT NOT NULL REFERENCES blended_forecasts(blend_id) ON DELETE CASCADE,
    explanation_text TEXT NOT NULL,
    feature_attributions_json JSONB NOT NULL
);
