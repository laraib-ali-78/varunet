"""
VaruNet Alerting Service
1. Detects meteorological hazards using named threshold constants.
2. Scores severity using anomaly magnitude and regional exposure.
3. Generates deterministic sector guidance templates (agriculture, aviation, public safety).
4. Persists alerts into the alerts table linked to triggered_by FK -> blended_forecasts.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple

logger = logging.getLogger("varunet.alerting")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# 1. Named Constants for Meteorological Hazard Thresholds (IMD-aligned)
RAINFALL_HEAVY_THRESHOLD_MM: float = 64.5        # Yellow alert: Heavy rain (64.5 - 115.5 mm)
RAINFALL_VERY_HEAVY_THRESHOLD_MM: float = 115.6  # Orange alert: Very heavy rain (115.6 - 204.4 mm)
RAINFALL_EXTREME_THRESHOLD_MM: float = 204.5     # Red alert: Extremely heavy rain (>= 204.5 mm)

TEMPERATURE_HEATWAVE_THRESHOLD_C: float = 40.0         # Yellow alert: Heatwave conditions (>= 40 C)
TEMPERATURE_SEVERE_HEATWAVE_THRESHOLD_C: float = 45.0  # Red alert: Severe heatwave (>= 45 C)

WIND_STRONG_THRESHOLD_KMH: float = 50.0   # Orange alert: Strong Gale (>= 50 km/h)
WIND_STORM_THRESHOLD_KMH: float = 75.0    # Red alert: Severe Storm (>= 75 km/h)

# Default region exposure weights (population and critical infrastructure density)
DEFAULT_REGION_EXPOSURE: Dict[int, float] = {
    1: 1.0,  # Dense coastal basin / urban center
    2: 0.85, # Major agricultural belt
    3: 0.70, # Hilly / catchment zone
}

# 3. Deterministic Sector Guidance Lookup Templates (Plain-language sentences)
SECTOR_GUIDANCE_TEMPLATES = {
    "heavy_rainfall": {
        "Yellow": {
            "agriculture": "Ensure drainage channels in standing crop fields remain unobstructed to prevent local water stagnation.",
            "aviation": "Monitor crosswinds and wet runway braking action reports during approach.",
            "public_safety": "Avoid crossing low-lying submerged causeways and stay updated with local weather bulletins.",
        },
        "Orange": {
            "agriculture": "Delay fertilizer and pesticide application immediately and protect harvested produce under tarpaulins.",
            "aviation": "Anticipate holding patterns, fuel diversion reserves, and convective SIGMET advisories around terminal airspace.",
            "public_safety": "Relocate livestock from floodplains and avoid non-essential road transit through waterlogged underpasses.",
        },
        "Red": {
            "agriculture": "Initiate emergency drainage pumping in submerged orchards and secure agricultural machinery on elevated grounds.",
            "aviation": "Prepare for flight diversions, ramp operation suspensions, and aerodrome flash flooding contingencies.",
            "public_safety": "Evacuate vulnerable riverbank and landslide-prone settlements immediately to designated cyclone/flood shelters.",
        },
    },
    "heatwave": {
        "Yellow": {
            "agriculture": "Schedule light and frequent crop irrigation during early morning or late evening hours.",
            "aviation": "Factor higher density altitude into takeoff thrust and payload calculations.",
            "public_safety": "Maintain hydration and avoid direct sunlight exposure between 12:00 PM and 3:00 PM.",
        },
        "Orange": {
            "agriculture": "Provide adequate thatch shading and misting systems for poultry and dairy livestock sheds.",
            "aviation": "Monitor runway asphalt surface temperature and tire thermal pressure limits.",
            "public_safety": "Vulnerable populations (children and elderly) should remain indoors in well-ventilated or cool areas.",
        },
        "Red": {
            "agriculture": "Halt all outdoor agricultural labor during peak daylight hours to prevent fatal heatstroke among workers.",
            "aviation": "Restrict maximum takeoff weight (MTOW) where runway density altitude exceeds certified safety envelopes.",
            "public_safety": "Activate municipal heat-action cooling shelters and ensure emergency saline fluid availability at health centers.",
        },
    },
    "high_wind": {
        "Orange": {
            "agriculture": "Stake tall crops, banana plantations, and horticultural trees to minimize lodging damage.",
            "aviation": "Expect low-level wind shear warnings on final approach and ensure mooring of unhangared aircraft.",
            "public_safety": "Secure loose tin roofs, scaffolding, and commercial billboards against wind gust dislodgement.",
        },
        "Red": {
            "agriculture": "Suspend all aerial and drone spraying operations and prepare for fallen tree obstruction in access roads.",
            "aviation": "Halt ground service equipment and suspend runway operations when crosswind limits are breached.",
            "public_safety": "Stay indoors away from glass facades, high-voltage electric poles, and old trees until wind subsides.",
        },
    },
}


def detect_hazard(variable: str, blended_value: float) -> Optional[Tuple[str, str]]:
    """
    1. Threshold/anomaly-based detection flagging blended_forecasts as hazards
       using named constants.
       Returns tuple: (hazard_type, base_severity) or None.
    """
    var_lower = variable.lower().strip()

    if "rain" in var_lower or "precip" in var_lower:
        if blended_value >= RAINFALL_EXTREME_THRESHOLD_MM:
            return "heavy_rainfall", "Red"
        elif blended_value >= RAINFALL_VERY_HEAVY_THRESHOLD_MM:
            return "heavy_rainfall", "Orange"
        elif blended_value >= RAINFALL_HEAVY_THRESHOLD_MM:
            return "heavy_rainfall", "Yellow"

    elif "temp" in var_lower:
        if blended_value >= TEMPERATURE_SEVERE_HEATWAVE_THRESHOLD_C:
            return "heatwave", "Red"
        elif blended_value >= TEMPERATURE_HEATWAVE_THRESHOLD_C:
            return "heatwave", "Orange"

    elif "wind" in var_lower:
        if blended_value >= WIND_STORM_THRESHOLD_KMH:
            return "high_wind", "Red"
        elif blended_value >= WIND_STRONG_THRESHOLD_KMH:
            return "high_wind", "Orange"

    return None


def calculate_severity(
    base_severity: str,
    region_id: int,
    exposure_weights: Optional[Dict[int, float]] = None,
) -> str:
    """
    2. Severity-scoring function ranking detected hazards using both anomaly
       magnitude and region exposure factor.
    """
    if exposure_weights is None:
        exposure_weights = DEFAULT_REGION_EXPOSURE

    exposure = exposure_weights.get(region_id, 0.75)

    severity_levels = ["Yellow", "Orange", "Red"]
    idx = severity_levels.index(base_severity) if base_severity in severity_levels else 0

    # If region has maximum exposure (>= 1.0) and severity is Yellow, escalate to Orange
    if exposure >= 1.0 and idx == 0:
        idx = 1
    # If region has low exposure (<= 0.5) and severity is Orange, demote to Yellow
    elif exposure <= 0.5 and idx == 1:
        idx = 0

    return severity_levels[idx]


def generate_sector_guidance(hazard_type: str, severity: str) -> str:
    """
    3. Template generator converting detected hazard type + severity into
       one plain-language sentence per sector (agriculture, aviation, public safety).
    """
    hazard_templates = SECTOR_GUIDANCE_TEMPLATES.get(hazard_type, {})
    sev_templates = hazard_templates.get(severity, {})

    if not sev_templates:
        # Fallback template
        return (
            f"Agriculture: Maintain field vigil for {hazard_type}. "
            f"Aviation: Check meteorological briefing before departure. "
            f"Public Safety: Follow local civil administration advisories."
        )

    agri = sev_templates.get("agriculture", "Monitor field conditions.")
    av = sev_templates.get("aviation", "Follow standard aerodrome operating procedures.")
    pub = sev_templates.get("public_safety", "Heed local safety advisories.")

    return f"Agriculture: {agri} Aviation: {av} Public Safety: {pub}"


def write_alert(
    db_session,
    region_id: int,
    valid_time: Union[datetime, str],
    alert_type: str,
    severity: str,
    sector_guidance_text: str,
    triggered_by: int,
) -> Optional[int]:
    """
    4. Writes results into the alerts table linked to triggered_by FK -> blended_forecasts.
    """
    insert_sql = """
    INSERT INTO alerts (
        region_id, valid_time, alert_type, severity, sector_guidance_text, triggered_by
    ) VALUES (
        :region_id, :valid_time, :alert_type, :severity, :sector_guidance_text, :triggered_by
    ) RETURNING alert_id;
    """

    params = {
        "region_id": int(region_id),
        "valid_time": valid_time,
        "alert_type": str(alert_type),
        "severity": str(severity),
        "sector_guidance_text": str(sector_guidance_text),
        "triggered_by": int(triggered_by),
    }

    alert_id = None
    has_sqlalchemy = False
    try:
        from sqlalchemy import text
        has_sqlalchemy = True
    except ImportError:
        has_sqlalchemy = False

    is_sqla = has_sqlalchemy and hasattr(db_session, "execute") and type(db_session).__module__.startswith("sqlalchemy")

    if is_sqla:
        from sqlalchemy import text
        res = db_session.execute(text(insert_sql), params)
        row = res.fetchone()
        if row:
            alert_id = row[0]
        db_session.commit()
    elif hasattr(db_session, "execute"):
        res = db_session.execute(insert_sql, params)
        if res and hasattr(res, "fetchone"):
            row = res.fetchone()
            if row:
                alert_id = row[0]
        if hasattr(db_session, "commit"):
            db_session.commit()
    else:
        cursor = db_session.cursor()
        psycopg2_sql = insert_sql.replace(":", "%(") + ")"
        cursor.execute(psycopg2_sql, params)
        row = cursor.fetchone()
        if row:
            alert_id = row[0]
        db_session.commit()

    logger.info("Saved alert record alert_id=%s, type=%s, severity=%s",
                alert_id, alert_type, severity)
    return alert_id


def evaluate_and_create_alert(
    db_session,
    blend_id: int,
    region_id: int,
    valid_time: Union[datetime, str],
    variable: str,
    blended_value: float,
    exposure_weights: Optional[Dict[int, float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Evaluates a blended forecast, detects any hazard, computes severity,
    generates guidance, and saves to database if triggered.
    """
    detected = detect_hazard(variable, blended_value)
    if not detected:
        return None

    hazard_type, base_sev = detected
    final_sev = calculate_severity(base_sev, region_id, exposure_weights)
    guidance = generate_sector_guidance(hazard_type, final_sev)

    alert_id = None
    if db_session is not None:
        alert_id = write_alert(
            db_session=db_session,
            region_id=region_id,
            valid_time=valid_time,
            alert_type=hazard_type,
            severity=final_sev,
            sector_guidance_text=guidance,
            triggered_by=blend_id,
        )

    return {
        "alert_id": alert_id,
        "region_id": region_id,
        "valid_time": valid_time,
        "alert_type": hazard_type,
        "severity": final_sev,
        "sector_guidance_text": guidance,
        "triggered_by": blend_id,
    }


def get_alerts(
    db_session,
    region_id: Optional[int] = None,
    severity: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Retrieves active/historical alerts by region and severity.
    """
    if db_session is None:
        return []

    query = "SELECT alert_id, region_id, valid_time, alert_type, severity, sector_guidance_text, triggered_by FROM alerts WHERE 1=1"
    params = {}
    if region_id is not None:
        query += " AND region_id = :region_id"
        params["region_id"] = region_id
    if severity is not None:
        query += " AND severity = :severity"
        params["severity"] = severity
    query += " ORDER BY valid_time DESC LIMIT :limit;"
    params["limit"] = limit

    has_sqlalchemy = False
    try:
        from sqlalchemy import text
        has_sqlalchemy = True
    except ImportError:
        has_sqlalchemy = False

    is_sqla = has_sqlalchemy and hasattr(db_session, "execute") and type(db_session).__module__.startswith("sqlalchemy")

    results = []
    if is_sqla:
        from sqlalchemy import text
        res = db_session.execute(text(query), params)
        for r in res.fetchall():
            results.append({
                "alert_id": r[0],
                "region_id": r[1],
                "valid_time": r[2],
                "alert_type": r[3],
                "severity": r[4],
                "sector_guidance_text": r[5],
                "triggered_by": r[6],
            })
    elif hasattr(db_session, "execute"):
        res = db_session.execute(query, params)
        if res and hasattr(res, "fetchall"):
            for r in res.fetchall():
                results.append({
                    "alert_id": r[0],
                    "region_id": r[1],
                    "valid_time": r[2],
                    "alert_type": r[3],
                    "severity": r[4],
                    "sector_guidance_text": r[5],
                    "triggered_by": r[6],
                })
    return results
