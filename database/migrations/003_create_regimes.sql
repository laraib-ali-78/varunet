-- Migration 003: Create regimes table

CREATE TABLE IF NOT EXISTS regimes (
    regime_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);
