-- Migration 001: Create forecast_sources table

CREATE TABLE IF NOT EXISTS forecast_sources (
    source_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL
);
