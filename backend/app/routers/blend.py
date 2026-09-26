"""
Blended Forecast Router
Retrieves or triggers computation of an AI-NWP blended forecast,
including dynamic weights_json, statistical confidence_score, and SHAP explanation text.
Supports citizen-scoped views with rate limiting and operator views with RBAC.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from backend.app.models.schemas import BlendedForecastResponse, CitizenBlendResponse
from backend.app.services.query_service import fetch_or_compute_blend
from backend.app.db.session import get_db
from backend.app.auth.dependencies import check_rate_limit

router = APIRouter(prefix="/api", tags=["Forecast Blending"])


def get_confidence_word_label(score: float) -> str:
    if score >= 0.70:
        return "High Confidence"
    elif score >= 0.40:
        return "Moderate Confidence"
    return "Some Uncertainty"


def get_plain_language_summary(val: float, var: str) -> str:
    if "rain" in var.lower() or "precip" in var.lower():
        if val < 2.5:
            return "Mostly dry and clear skies. No rain gear required."
        elif val < 15.5:
            return "Light passing drizzles. Carry an umbrella for outdoor activities."
        elif val < 64.5:
            return "Moderate steady rainfall expected throughout the day."
        elif val < 115.5:
            return "Heavy rainfall expected with localized waterlogging."
        return "Torrential downpours likely. Significant travel disruption expected."
    elif "temp" in var.lower():
        return f"Expected temperature around {val:.1f}°C."
    return f"Forecasted {var}: {val:.1f}"


@router.get("/blend", response_model=BlendedForecastResponse)
def get_or_compute_blend(
    region_id: int = Query(..., description="Target region ID"),
    valid_time: datetime = Query(..., description="Forecast valid timestamp"),
    lead_time_hrs: int = Query(..., ge=0, le=240, description="Lead time in hours"),
    variable: str = Query("rainfall", description="Meteorological variable name"),
    regime_id: int = Query(1, description="Current synoptic regime ID"),
    db=Depends(get_db),
    _rate_limit=Depends(check_rate_limit),
):
    """
    Retrieve existing blended forecast or trigger dynamic XGBoost blending
    with statistical confidence scoring and TreeSHAP feature explanation.
    """
    return fetch_or_compute_blend(
        db_session=db,
        region_id=region_id,
        valid_time=valid_time,
        lead_time_hrs=lead_time_hrs,
        variable=variable,
        regime_id=regime_id,
    )


@router.get("/blend/citizen", response_model=CitizenBlendResponse)
def get_citizen_blend(
    request: Request,
    region_id: int = Query(..., description="Target region ID"),
    valid_time: datetime = Query(..., description="Forecast valid timestamp"),
    lead_time_hrs: int = Query(24, ge=0, le=240, description="Lead time in hours"),
    variable: str = Query("rainfall", description="Meteorological variable"),
    db=Depends(get_db),
    _rate_limit=Depends(check_rate_limit),
):
    """
    Citizen-scoped forecast view: Returns plain-language summary and word-based
    confidence label. Protected by client rate limiting.
    """
    full_blend = fetch_or_compute_blend(
        db_session=db,
        region_id=region_id,
        valid_time=valid_time,
        lead_time_hrs=lead_time_hrs,
        variable=variable,
        regime_id=1,
    )

    conf_label = get_confidence_word_label(full_blend["confidence_score"])
    summary_text = get_plain_language_summary(full_blend["blended_value"], variable)

    return {
        "region_id": region_id,
        "valid_time": valid_time,
        "variable": variable,
        "blended_value": full_blend["blended_value"],
        "confidence_label": conf_label,
        "plain_language_summary": summary_text,
    }
