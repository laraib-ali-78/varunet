"""
Pydantic Request and Response Schemas for VaruNet API
Strict validation matching PostgreSQL schema definitions.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class ForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    forecast_id: int = Field(..., description="Unique forecast record ID")
    source_id: int = Field(..., description="Forecast source identifier (NWP, AI/ML, Ensemble)")
    region_id: int = Field(..., description="Target region identifier")
    valid_time: datetime = Field(..., description="Forecast valid timestamp")
    lead_time_hrs: int = Field(..., description="Forecast lead time in hours")
    variable: str = Field(..., description="Meteorological variable name")
    value: float = Field(..., description="Forecast value")


class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_id: int = Field(..., description="Observed region identifier")
    valid_time: datetime = Field(..., description="Observation valid timestamp")
    variable: str = Field(..., description="Observed meteorological variable")
    value: float = Field(..., description="Ground-truth observed value")


class SkillScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score_id: int = Field(..., description="Unique skill score record ID")
    source_id: int = Field(..., description="Forecast source identifier")
    region_id: int = Field(..., description="Target region identifier")
    regime_id: int = Field(..., description="Synoptic weather regime ID")
    season: str = Field(..., description="Meteorological season")
    lead_time_bucket: str = Field(..., description="Lead time bucket (e.g. 0-24h)")
    variable: str = Field(..., description="Meteorological variable name")
    rmse: Optional[float] = Field(None, description="Root Mean Squared Error")
    mae: Optional[float] = Field(None, description="Mean Absolute Error")
    bias: Optional[float] = Field(None, description="Signed Mean Bias (forecast - observation)")
    sample_size: int = Field(..., description="Number of evaluated verification cases")
    last_updated: datetime = Field(..., description="Timestamp when score was last updated")


class BlendedForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    blend_id: Optional[int] = Field(None, description="Unique blended forecast ID")
    region_id: int = Field(..., description="Target region identifier")
    valid_time: datetime = Field(..., description="Forecast valid timestamp")
    lead_time_hrs: int = Field(..., description="Forecast lead time in hours")
    variable: str = Field(..., description="Meteorological variable name")
    blended_value: float = Field(..., description="AI-NWP dynamically blended value")
    weights_json: Dict[str, float] = Field(..., description="Full weight vector across all sources")
    confidence_score: float = Field(..., description="Statistical confidence score [0.0 - 1.0]")
    explanation_text: Optional[str] = Field(None, description="TreeSHAP template-based natural language explanation")
    feature_attributions: Optional[Dict[str, Any]] = Field(None, description="SHAP feature attribution breakdown")


class CitizenBlendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_id: int = Field(..., description="Target region ID")
    valid_time: datetime = Field(..., description="Forecast valid time")
    variable: str = Field(..., description="Weather variable")
    blended_value: float = Field(..., description="Blended value")
    confidence_label: str = Field(..., description="Word-based confidence: High Confidence / Moderate Confidence / Some Uncertainty")
    plain_language_summary: str = Field(..., description="Citizen friendly forecast summary")


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alert_id: int = Field(..., description="Unique alert ID")
    region_id: int = Field(..., description="Affected region identifier")
    valid_time: datetime = Field(..., description="Valid timestamp of hazard")
    alert_type: str = Field(..., description="Hazard type (e.g. heavy_rainfall, heatwave, high_wind)")
    severity: str = Field(..., description="Severity level: Yellow, Orange, Red")
    sector_guidance_text: str = Field(..., description="Plain-language guidance for agriculture, aviation, and public safety")
    triggered_by: int = Field(..., description="Foreign key to triggering blended_forecasts record")
