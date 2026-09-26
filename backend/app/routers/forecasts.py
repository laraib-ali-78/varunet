"""
Forecasts and Observations Router
Retrieves raw forecast data and observations by region/time/lead-time.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from backend.app.models.schemas import ForecastResponse, ObservationResponse
from backend.app.services.query_service import fetch_forecasts, fetch_observations
from backend.app.db.session import get_db
from backend.app.auth.dependencies import require_roles

router = APIRouter(prefix="/api", tags=["Forecasts & Observations"])

operator_auth = require_roles(["forecaster", "admin"])


@router.get("/forecasts", response_model=List[ForecastResponse])
def get_raw_forecasts(
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    valid_time: Optional[datetime] = Query(None, description="Filter by valid timestamp"),
    lead_time_hrs: Optional[int] = Query(None, description="Filter by lead time in hours"),
    variable: Optional[str] = Query(None, description="Filter by variable name (e.g. rainfall)"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    user=Depends(operator_auth),
    db=Depends(get_db),
):
    """
    Retrieve raw multi-model forecasts filtered by region, valid time, and lead time.
    """
    return fetch_forecasts(
        db_session=db,
        region_id=region_id,
        valid_time=valid_time,
        lead_time_hrs=lead_time_hrs,
        variable=variable,
        limit=limit,
    )


@router.get("/observations", response_model=List[ObservationResponse])
def get_observations(
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    valid_time: Optional[datetime] = Query(None, description="Filter by valid timestamp"),
    variable: Optional[str] = Query(None, description="Filter by variable name"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    db=Depends(get_db),
):
    """
    Retrieve ground-truth observation records filtered by region and valid time.
    """
    return fetch_observations(
        db_session=db,
        region_id=region_id,
        valid_time=valid_time,
        variable=variable,
        limit=limit,
    )
