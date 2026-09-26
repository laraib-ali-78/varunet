"""
Alerts Router
Retrieves active and historical weather hazard alerts filtered by region and severity.
Implements role-based access control and rate limiting.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request

from backend.app.models.schemas import AlertResponse
from backend.app.services.alerting_service import get_alerts
from backend.app.db.session import get_db
from backend.app.auth.dependencies import require_roles, check_rate_limit

router = APIRouter(prefix="/api", tags=["Alerts & Early Warning"])

# Operator role requirement for full cross-sector alert details
operator_auth = require_roles(["forecaster", "admin"])


@router.get("/alerts", response_model=List[AlertResponse])
def list_operator_alerts(
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (Yellow, Orange, Red)"),
    limit: int = Query(50, ge=1, le=500, description="Max alerts to retrieve"),
    user=Depends(operator_auth),
    db=Depends(get_db),
):
    """
    Operator-facing: Retrieve full meteorological hazard alerts with cross-sector guidance.
    Requires 'forecaster' or 'admin' role.
    """
    return get_alerts(
        db_session=db,
        region_id=region_id,
        severity=severity,
        limit=limit,
    )


@router.get("/alerts/citizen", response_model=List[AlertResponse])
def list_citizen_alerts(
    request: Request,
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    limit: int = Query(20, ge=1, le=100, description="Max alerts to retrieve"),
    db=Depends(get_db),
    _rate_limit=Depends(check_rate_limit),
):
    """
    Citizen-accessible: Public safety hazard advisories.
    Protected by client IP rate limiting (max 60 requests/minute).
    """
    return get_alerts(
        db_session=db,
        region_id=region_id,
        limit=limit,
    )
