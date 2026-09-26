"""
VaruNet Blending Engine
Executes AI-NWP multi-model forecast blending:
1. Loads XGBoost weighting model and predicts dynamic weight vector.
2. Applies weights to produce blended_value.
3. Computes statistical confidence_score from inter-source disagreement.
4. Writes blended record into blended_forecasts table.
"""

import os
import json
import math
import joblib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union

import numpy as np
import pandas as pd

from backend.app.services.skill_scoring_engine import get_season, get_lead_time_bucket

logger = logging.getLogger("varunet.blending")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# Default location for trained XGBoost weighting model
DEFAULT_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "models", "varunet_weighting_xgb.joblib")
)

# Global cached model payload to prevent redundant file I/O
_CACHED_MODEL_PAYLOAD: Optional[Dict[str, Any]] = None


def load_blending_model(model_path: str = DEFAULT_MODEL_PATH) -> Dict[str, Any]:
    """
    Loads and caches the trained XGBoost weighting model artifact.
    """
    global _CACHED_MODEL_PAYLOAD
    if _CACHED_MODEL_PAYLOAD is not None:
        return _CACHED_MODEL_PAYLOAD

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Trained weighting model not found at {model_path}. "
            "Please train the model first using ml.training.train_weighting_model."
        )

    logger.info("Loading VaruNet XGBoost weighting model from %s", model_path)
    payload = joblib.load(model_path)
    _CACHED_MODEL_PAYLOAD = payload
    return payload


def compute_confidence_score(
    forecast_values: List[float],
    weights: Optional[List[float]] = None,
    scale: float = 5.0,
) -> float:
    """
    Plain statistical confidence calculation from inter-source disagreement/spread.
    Higher agreement (lower spread) -> higher confidence (approaches 1.0).
    Higher disagreement (higher spread) -> explicitly lower confidence (approaches 0.0).

    Uses weighted standard deviation of forecasts:
    confidence = exp(-dispersion / scale)
    Bounded strictly in [0.0, 1.0].
    """
    arr = np.array(forecast_values, dtype=np.float64)
    k = len(arr)
    if k <= 1:
        return 1.0

    if weights is not None and len(weights) == k:
        w = np.array(weights, dtype=np.float64)
        w_sum = np.sum(w)
        if w_sum > 0:
            w = w / w_sum
            weighted_mean = np.sum(w * arr)
            variance = np.sum(w * ((arr - weighted_mean) ** 2))
            dispersion = math.sqrt(max(0.0, variance))
        else:
            dispersion = float(np.std(arr, ddof=1))
    else:
        dispersion = float(np.std(arr, ddof=1))

    # Exponential decay from inter-model dispersion
    confidence = math.exp(-dispersion / scale)
    return float(np.clip(confidence, 0.0, 1.0))


def predict_weights(
    region_id: int,
    valid_time: Union[datetime, str],
    lead_time_hrs: int,
    variable: str,
    source_forecasts: Dict[str, float],
    regime_id: int = 1,
    skill_scores_stratum: Optional[Dict[str, float]] = None,
    model_path: str = DEFAULT_MODEL_PATH,
) -> Dict[str, float]:
    """
    1. Loads the trained model, builds context features for the request,
       and predicts the normalized weight vector.
    """
    payload = load_blending_model(model_path)
    model = payload["model"]
    feature_names = payload["feature_names"]
    expected_sources = payload["source_cols"]

    if isinstance(valid_time, str):
        valid_dt = pd.to_datetime(valid_time)
    else:
        valid_dt = valid_time

    # Align forecasts with expected model input order
    source_vals = []
    for col in expected_sources:
        if col in source_forecasts:
            source_vals.append(float(source_forecasts[col]))
        else:
            # Fallback to mean of provided forecasts if a source key differs
            mean_val = float(np.mean(list(source_forecasts.values())))
            source_vals.append(mean_val)

    source_vals_arr = np.array(source_vals, dtype=np.float64)

    # Compute features
    doy = valid_dt.timetuple().tm_yday
    angle = 2.0 * math.pi * doy / 365.25
    sin_doy = math.sin(angle)
    cos_doy = math.cos(angle)

    var_fcst = float(np.var(source_vals_arr, ddof=1 if len(source_vals_arr) > 1 else 0))
    std_fcst = math.sqrt(var_fcst)
    spread_fcst = float(np.ptp(source_vals_arr))
    ens_mean = float(np.mean(source_vals_arr))

    # Map season and lead time bucket
    season = get_season(valid_dt)
    season_map = {"Winter": 0, "Pre-Monsoon": 1, "Monsoon": 2, "Post-Monsoon": 3}
    season_code = season_map.get(season, 0)

    lt_bucket = get_lead_time_bucket(lead_time_hrs)
    bucket_map = {"0-24h": 0, "24-48h": 1, "48-72h": 2, "72-120h": 3, ">120h": 4}
    bucket_code = bucket_map.get(lt_bucket, 0)

    feature_dict = {
        "region_id": float(region_id),
        "regime_id": float(regime_id),
        "sin_doy": sin_doy,
        "cos_doy": cos_doy,
        "lead_time_hrs": float(lead_time_hrs),
        "forecast_variance": var_fcst,
        "forecast_std": std_fcst,
        "forecast_spread": spread_fcst,
        "season_code": float(season_code),
        "lead_time_bucket_code": float(bucket_code),
    }

    # Add anomalies
    for i, col in enumerate(expected_sources):
        feature_dict[f"anom_{col}"] = float(source_vals_arr[i] - ens_mean)

    # Add skill score features if model expects them
    if skill_scores_stratum:
        for k_s, v_s in skill_scores_stratum.items():
            feature_dict[k_s] = float(v_s)

    # Build input vector matching feature_names
    x_input = []
    for fn in feature_names:
        x_input.append(feature_dict.get(fn, 0.0))

    X_mat = np.array([x_input], dtype=np.float64)

    # Predict raw weights
    raw_weights = model.predict(X_mat)[0]

    # Normalize weights: clip negative values, sum to 1.0
    clipped = np.clip(raw_weights, 0.0, 1.0)
    total = np.sum(clipped)
    if total > 0:
        normalized_w = clipped / total
    else:
        # Uniform fallback
        normalized_w = np.full(len(expected_sources), 1.0 / len(expected_sources))

    # Return full weights dict
    return {col: float(normalized_w[i]) for i, col in enumerate(expected_sources)}


def apply_weights(
    source_forecasts: Dict[str, float],
    weights: Dict[str, float],
) -> float:
    """
    2. Applies the weight vector to the individual forecasts to produce
       a single blended_value.
    """
    blended = 0.0
    weight_sum = 0.0

    for src_name, w in weights.items():
        if src_name in source_forecasts:
            val = float(source_forecasts[src_name])
            blended += w * val
            weight_sum += w

    if weight_sum > 0:
        return float(blended / weight_sum)
    return float(np.mean(list(source_forecasts.values())))


def write_blended_forecast(
    db_session,
    region_id: int,
    valid_time: Union[datetime, str],
    lead_time_hrs: int,
    variable: str,
    blended_value: float,
    weights_json: Dict[str, float],
    confidence_score: float,
) -> Optional[int]:
    """
    4. Writes the blended forecast record into the blended_forecasts table.
       Supports SQLAlchemy session or standard DB-API 2.0 cursor.
    """
    insert_sql = """
    INSERT INTO blended_forecasts (
        region_id, valid_time, lead_time_hrs, variable, blended_value, weights_json, confidence_score
    ) VALUES (
        :region_id, :valid_time, :lead_time_hrs, :variable, :blended_value, :weights_json, :confidence_score
    ) RETURNING blend_id;
    """

    if isinstance(valid_time, str):
        valid_dt = pd.to_datetime(valid_time)
    else:
        valid_dt = valid_time

    params = {
        "region_id": int(region_id),
        "valid_time": valid_dt,
        "lead_time_hrs": int(lead_time_hrs),
        "variable": str(variable),
        "blended_value": float(blended_value),
        "weights_json": json.dumps(weights_json),
        "confidence_score": float(confidence_score),
    }

    blend_id = None
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
            blend_id = row[0]
        db_session.commit()
    elif hasattr(db_session, "execute"):
        # Generic session or mock with execute method
        res = db_session.execute(insert_sql, params)
        if res and hasattr(res, "fetchone"):
            row = res.fetchone()
            if row:
                blend_id = row[0]
        if hasattr(db_session, "commit"):
            db_session.commit()
    else:
        import re
        cursor = db_session.cursor()
        psycopg2_sql = re.sub(r':([a-zA-Z0-9_]+)', r'%(\1)s', insert_sql)
        cursor.execute(psycopg2_sql, params)
        row = cursor.fetchone()
        if row:
            blend_id = row[0]
        db_session.commit()

    logger.info("Saved blended_forecast record blend_id=%s for region=%d, valid_time=%s",
                blend_id, region_id, str(valid_dt))
    return blend_id


def blend_and_store(
    db_session,
    region_id: int,
    valid_time: Union[datetime, str],
    lead_time_hrs: int,
    variable: str,
    source_forecasts: Dict[str, float],
    regime_id: int = 1,
    scale: float = 5.0,
    model_path: str = DEFAULT_MODEL_PATH,
) -> Dict[str, Any]:
    """
    Full pipeline execution:
    1. Predicts weight vector
    2. Computes blended_value
    3. Computes statistical confidence_score
    4. Writes into blended_forecasts table
    """
    # 1. Predict weights
    weights = predict_weights(
        region_id=region_id,
        valid_time=valid_time,
        lead_time_hrs=lead_time_hrs,
        variable=variable,
        source_forecasts=source_forecasts,
        regime_id=regime_id,
        model_path=model_path,
    )

    # 2. Produce blended value
    blended_value = apply_weights(source_forecasts, weights)

    # 3. Compute statistical confidence score
    raw_vals = [source_forecasts[s] for s in weights.keys() if s in source_forecasts]
    w_vals = [weights[s] for s in weights.keys() if s in source_forecasts]
    confidence_score = compute_confidence_score(raw_vals, weights=w_vals, scale=scale)

    # 4. Write to database if db_session provided
    blend_id = None
    if db_session is not None:
        blend_id = write_blended_forecast(
            db_session=db_session,
            region_id=region_id,
            valid_time=valid_time,
            lead_time_hrs=lead_time_hrs,
            variable=variable,
            blended_value=blended_value,
            weights_json=weights,
            confidence_score=confidence_score,
        )

    return {
        "blend_id": blend_id,
        "region_id": region_id,
        "valid_time": valid_time,
        "lead_time_hrs": lead_time_hrs,
        "variable": variable,
        "blended_value": blended_value,
        "weights_json": weights,
        "confidence_score": confidence_score,
    }
