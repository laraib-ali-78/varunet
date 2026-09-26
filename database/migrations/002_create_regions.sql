-- Migration 002: Create regions table with PostGIS geometry column

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS regions (
    region_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    geometry GEOMETRY(Geometry, 4326) NOT NULL
);
