# Proxy Seed Data Format

This directory holds seed data for the VaruNet PostgreSQL + PostGIS database.

## Supported Formats

Seed data files are provided in standardized CSV and GeoJSON formats matching the schema specifications:

1. **`forecast_sources.csv`**: `source_id,name,type`
2. **`regions.geojson`** (or `regions.csv` with WKT geometry in EPSG:4326): `region_id,name,geometry`
3. **`regimes.csv`**: `regime_id,name`
4. **`forecasts.csv`**: `forecast_id,source_id,region_id,valid_time,lead_time_hrs,variable,value`
5. **`observations.csv`**: `region_id,valid_time,variable,value`
6. **`skill_scores.csv`**: `score_id,source_id,region_id,regime_id,season,lead_time_bucket,variable,rmse,mae,bias,sample_size,last_updated`
7. **`blended_forecasts.csv`**: `blend_id,region_id,valid_time,lead_time_hrs,variable,blended_value,weights_json,confidence_score`
8. **`alerts.csv`**: `alert_id,region_id,valid_time,alert_type,severity,sector_guidance_text,triggered_by`
9. **`users.csv`**: `user_id,email,password_hash,role`
10. **`explanations.csv`**: `explanation_id,blend_id,explanation_text,feature_attributions_json`

*Note: Actual proxy data generation will be executed in subsequent steps.*
