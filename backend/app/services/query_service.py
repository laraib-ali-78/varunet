import re
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger("varunet.query")


def execute_query(db_session, sql: str, params: Optional[Dict[str, Any]] = None):
    if db_session is None:
        return []
    if params is None:
        params = {}
    try:
        if hasattr(db_session, "execute") and hasattr(db_session, "commit"):
            from sqlalchemy import text
            res = db_session.execute(text(sql), params)
            if hasattr(res, "fetchall"):
                return res.fetchall()
            return []
        elif hasattr(db_session, "cursor"):
            cursor = db_session.cursor()
            p_sql = re.sub(r':([a-zA-Z0-9_]+)', r'%(\1)s', sql)
            cursor.execute(p_sql, params)
            if hasattr(cursor, "fetchall"):
                return cursor.fetchall()
            return []
        elif hasattr(db_session, "fetchall"):
            return db_session.fetchall()
        return []
    except Exception as e:
        logger.error("Query execution error on SQL '%s': %s", sql[:60], str(e))
        return []


def fetch_forecasts(
    db_session,
    region_id: Optional[int] = None,
    valid_time: Optional[datetime] = None,
    lead_time_hrs: Optional[int] = None,
    variable: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Retrieves raw forecasts by region/time/lead-time.
    """
    if db_session is None:
        return []

    sql = "SELECT forecast_id, source_id, region_id, valid_time, lead_time_hrs, variable, value FROM forecasts WHERE 1=1"
    params = {}
    if region_id is not None:
        sql += " AND region_id = :region_id"
        params["region_id"] = region_id
    if valid_time is not None:
        sql += " AND valid_time = :valid_time"
        params["valid_time"] = valid_time
    if lead_time_hrs is not None:
        sql += " AND lead_time_hrs = :lead_time_hrs"
        params["lead_time_hrs"] = lead_time_hrs
    if variable is not None:
        sql += " AND variable = :variable"
        params["variable"] = variable
    sql += " ORDER BY valid_time DESC LIMIT :limit;"
    params["limit"] = limit

    rows = execute_query(db_session, sql, params)
    return [
        {
            "forecast_id": r[0],
            "source_id": r[1],
            "region_id": r[2],
            "valid_time": r[3],
            "lead_time_hrs": r[4],
            "variable": r[5],
            "value": r[6],
        }
        for r in rows
    ]


def fetch_observations(
    db_session,
    region_id: Optional[int] = None,
    valid_time: Optional[datetime] = None,
    variable: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Retrieves observations by region/time.
    """
    if db_session is None:
        return []

    sql = "SELECT region_id, valid_time, variable, value FROM observations WHERE 1=1"
    params = {}
    if region_id is not None:
        sql += " AND region_id = :region_id"
        params["region_id"] = region_id
    if valid_time is not None:
        sql += " AND valid_time = :valid_time"
        params["valid_time"] = valid_time
    if variable is not None:
        sql += " AND variable = :variable"
        params["variable"] = variable
    sql += " ORDER BY valid_time DESC LIMIT :limit;"
    params["limit"] = limit

    rows = execute_query(db_session, sql, params)
    return [
        {
            "region_id": r[0],
            "valid_time": r[1],
            "variable": r[2],
            "value": r[3],
        }
        for r in rows
    ]


def fetch_skill_scores(
    db_session,
    source_id: Optional[int] = None,
    region_id: Optional[int] = None,
    regime_id: Optional[int] = None,
    season: Optional[str] = None,
    lead_time_bucket: Optional[str] = None,
    variable: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Retrieves skill scores by source/region/regime/season/lead-time.
    """
    if db_session is None:
        return []

    sql = """
    SELECT score_id, source_id, region_id, regime_id, season, lead_time_bucket,
           variable, rmse, mae, bias, sample_size, last_updated
    FROM skill_scores WHERE 1=1
    """
    params = {}
    if source_id is not None:
        sql += " AND source_id = :source_id"
        params["source_id"] = source_id
    if region_id is not None:
        sql += " AND region_id = :region_id"
        params["region_id"] = region_id
    if regime_id is not None:
        sql += " AND regime_id = :regime_id"
        params["regime_id"] = regime_id
    if season is not None:
        sql += " AND season = :season"
        params["season"] = season
    if lead_time_bucket is not None:
        sql += " AND lead_time_bucket = :lead_time_bucket"
        params["lead_time_bucket"] = lead_time_bucket
    if variable is not None:
        sql += " AND variable = :variable"
        params["variable"] = variable
    sql += " ORDER BY last_updated DESC LIMIT :limit;"
    params["limit"] = limit

    rows = execute_query(db_session, sql, params)
    return [
        {
            "score_id": r[0],
            "source_id": r[1],
            "region_id": r[2],
            "regime_id": r[3],
            "season": r[4],
            "lead_time_bucket": r[5],
            "variable": r[6],
            "rmse": r[7],
            "mae": r[8],
            "bias": r[9],
            "sample_size": r[10],
            "last_updated": r[11],
        }
        for r in rows
    ]


def fetch_or_compute_blend(
    db_session,
    region_id: int,
    valid_time: datetime,
    lead_time_hrs: int,
    variable: str,
    regime_id: int = 1,
    source_forecasts: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Retrieves existing blended forecast or triggers computation using
    the blending and explainability services.
    """
    # 1. Check if blended forecast already exists in database
    if db_session is not None:
        sql = """
        SELECT b.blend_id, b.region_id, b.valid_time, b.lead_time_hrs, b.variable,
               b.blended_value, b.weights_json, b.confidence_score,
               e.explanation_text, e.feature_attributions_json
        FROM blended_forecasts b
        LEFT JOIN explanations e ON b.blend_id = e.blend_id
        WHERE b.region_id = :region_id
          AND b.valid_time = :valid_time
          AND b.lead_time_hrs = :lead_time_hrs
          AND b.variable = :variable
        ORDER BY b.blend_id DESC LIMIT 1;
        """
        try:
            import json
            from sqlalchemy import text
            res = db_session.execute(text(sql), {
                "region_id": region_id,
                "valid_time": valid_time,
                "lead_time_hrs": lead_time_hrs,
                "variable": variable,
            })
            row = res.fetchone()
            if row:
                weights = json.loads(row[6]) if isinstance(row[6], str) else row[6]
                attributions = json.loads(row[9]) if isinstance(row[9], str) else row[9]
                return {
                    "blend_id": row[0],
                    "region_id": row[1],
                    "valid_time": row[2],
                    "lead_time_hrs": row[3],
                    "variable": row[4],
                    "blended_value": row[5],
                    "weights_json": weights,
                    "confidence_score": row[7],
                    "explanation_text": row[8],
                    "feature_attributions": attributions,
                }
        except Exception:
            pass

    # 2. Trigger computation if not found or on demand
    from backend.app.services.blending_engine import blend_and_store, predict_weights
    from ml.explainability.shap_explainer import explain_and_store

    if not source_forecasts and db_session is not None:
        source_forecasts = {}
        sql_fcsts = """
        SELECT source_id, value 
        FROM forecasts 
        WHERE region_id = :region_id 
          AND valid_time = :valid_time 
          AND lead_time_hrs = :lead_time_hrs 
          AND variable = :variable;
        """
        source_map = {1: "fcst_nwp", 2: "fcst_aiml", 3: "fcst_ensemble"}
        params = {
            "region_id": region_id,
            "valid_time": valid_time,
            "lead_time_hrs": lead_time_hrs,
            "variable": variable,
        }
        try:
            if hasattr(db_session, "execute") and hasattr(db_session, "commit"):
                from sqlalchemy import text
                f_rows = db_session.execute(text(sql_fcsts), params).fetchall()
            elif hasattr(db_session, "cursor"):
                import re
                cursor = db_session.cursor()
                p_sql = re.sub(r':([a-zA-Z0-9_]+)', r'%(\1)s', sql_fcsts)
                cursor.execute(p_sql, params)
                f_rows = cursor.fetchall()
            else:
                f_rows = []

            for r in f_rows:
                s_name = source_map.get(r[0])
                if s_name:
                    source_forecasts[s_name] = float(r[1])
        except Exception as e:
            logger.warning("Error querying forecasts for blend: %s", str(e))

    if not source_forecasts or len(source_forecasts) == 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"No forecast data available for region {region_id}, lead_time {lead_time_hrs}h, variable '{variable}' at valid_time {valid_time}."
        )

    blend_result = blend_and_store(
        db_session=db_session,
        region_id=region_id,
        valid_time=valid_time,
        lead_time_hrs=lead_time_hrs,
        variable=variable,
        source_forecasts=source_forecasts,
        regime_id=regime_id,
    )

    # Compute SHAP explanation
    import joblib
    from backend.app.services.blending_engine import DEFAULT_MODEL_PATH
    import numpy as np

    explanation_text = None
    feature_attributions = None

    try:
        model_payload = joblib.load(DEFAULT_MODEL_PATH)
        feat_len = len(model_payload["feature_names"])
        sample_vec = np.zeros(feat_len)
        idx_map = {fn: i for i, fn in enumerate(model_payload["feature_names"])}
        if "region_id" in idx_map: sample_vec[idx_map["region_id"]] = float(region_id)
        if "regime_id" in idx_map: sample_vec[idx_map["regime_id"]] = float(regime_id)
        if "lead_time_hrs" in idx_map: sample_vec[idx_map["lead_time_hrs"]] = float(lead_time_hrs)

        exp_result = explain_and_store(
            db_session=db_session,
            blend_id=blend_result["blend_id"] if blend_result["blend_id"] else 1,
            feature_vector=sample_vec,
            predicted_weights=blend_result["weights_json"],
            region_name=f"Region {region_id}",
            regime_name="Monsoon Active" if regime_id == 2 else "Normal Synoptic",
            model_payload=model_payload,
        )
        explanation_text = exp_result["explanation_text"]
        feature_attributions = exp_result["feature_attributions"]
    except Exception:
        explanation_text = "Forecast sources were blended using the trained XGBoost model."

    blend_result["explanation_text"] = explanation_text
    blend_result["feature_attributions"] = feature_attributions
    return blend_result
