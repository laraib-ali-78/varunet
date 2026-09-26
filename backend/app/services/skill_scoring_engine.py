"""
Skill Scoring Engine for VaruNet
Deterministic statistical computation of NWP and AI/ML model verification metrics
(RMSE, MAE, signed Bias) stratified by (source, region, regime, season, lead time bucket, variable).
"""

import math
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

logger = logging.getLogger("varunet.skill_scoring")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# Hard rule: Named constant for minimum sample size threshold
MIN_SAMPLE_SIZE: int = 10


def get_season(dt: datetime) -> str:
    """
    Classifies a timestamp into Indian meteorological seasons:
    - Winter: Jan - Feb
    - Pre-Monsoon: Mar - May
    - Monsoon: Jun - Sep
    - Post-Monsoon: Oct - Dec
    """
    month = dt.month
    if month in (1, 2):
        return "Winter"
    elif month in (3, 4, 5):
        return "Pre-Monsoon"
    elif month in (6, 7, 8, 9):
        return "Monsoon"
    else:
        return "Post-Monsoon"


def get_lead_time_bucket(lead_time_hrs: int) -> str:
    """
    Maps lead time hours to standard verification lead time buckets:
    - 0-24h
    - 24-48h
    - 48-72h
    - 72-120h
    - >120h
    """
    if lead_time_hrs <= 24:
        return "0-24h"
    elif lead_time_hrs <= 48:
        return "24-48h"
    elif lead_time_hrs <= 72:
        return "48-72h"
    elif lead_time_hrs <= 120:
        return "72-120h"
    else:
        return ">120h"


def compute_metrics(
    forecast_values: List[float],
    observation_values: List[float],
    min_sample_size: int = MIN_SAMPLE_SIZE,
    stratum_info: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, float]]:
    """
    Computes RMSE, MAE, and signed bias (mean forecast - mean observation).
    Enforces minimum sample_size threshold: skips and logs if sample_size < min_sample_size.
    """
    n = len(forecast_values)
    if n != len(observation_values):
        raise ValueError(
            f"Forecast count ({n}) does not match observation count ({len(observation_values)})."
        )

    if n < min_sample_size:
        stratum_str = str(stratum_info) if stratum_info else "unspecified"
        logger.warning(
            "Low-data stratum skipped: sample_size=%d < MIN_SAMPLE_SIZE=%d (Stratum: %s)",
            n,
            min_sample_size,
            stratum_str,
        )
        return None

    # Deterministic statistical calculation without ML libraries
    sum_err = 0.0
    sum_abs_err = 0.0
    sum_sq_err = 0.0

    for f, o in zip(forecast_values, observation_values):
        err = f - o
        sum_err += err
        sum_abs_err += abs(err)
        sum_sq_err += err * err

    bias = sum_err / n  # Mean forecast minus mean observation
    mae = sum_abs_err / n
    rmse = math.sqrt(sum_sq_err / n)

    return {
        "rmse": rmse,
        "mae": mae,
        "bias": bias,
        "sample_size": n,
    }


def compute_skill_scores(
    forecasts_df: pd.DataFrame,
    observations_df: pd.DataFrame,
    min_sample_size: int = MIN_SAMPLE_SIZE,
    default_regime_id: int = 1,
) -> pd.DataFrame:
    """
    1. Joins forecasts to observations on region_id + valid_time + variable.
    2. Derives season, lead_time_bucket, and regime_id if not present.
    3. Groups by (source_id, region_id, regime_id, season, lead_time_bucket, variable).
    4. Computes RMSE, MAE, signed bias for strata meeting MIN_SAMPLE_SIZE.
    5. Returns a DataFrame ready for upsert into the skill_scores table.
    """
    if forecasts_df.empty or observations_df.empty:
        logger.info("Empty forecasts or observations dataframe. No skill scores to compute.")
        return pd.DataFrame(
            columns=[
                "source_id",
                "region_id",
                "regime_id",
                "season",
                "lead_time_bucket",
                "variable",
                "rmse",
                "mae",
                "bias",
                "sample_size",
                "last_updated",
            ]
        )

    # Ensure valid_time is datetime
    forecasts = forecasts_df.copy()
    observations = observations_df.copy()
    forecasts["valid_time"] = pd.to_datetime(forecasts["valid_time"])
    observations["valid_time"] = pd.to_datetime(observations["valid_time"])

    # 1. Join forecasts to observations on region_id + valid_time + variable
    merged = pd.merge(
        forecasts,
        observations,
        on=["region_id", "valid_time", "variable"],
        suffixes=("_fcst", "_obs"),
    )

    if merged.empty:
        logger.warning("No matching forecast-observation pairs found for skill scoring.")
        return pd.DataFrame(
            columns=[
                "source_id",
                "region_id",
                "regime_id",
                "season",
                "lead_time_bucket",
                "variable",
                "rmse",
                "mae",
                "bias",
                "sample_size",
                "last_updated",
            ]
        )

    # Derive season if not already present
    if "season" not in merged.columns:
        merged["season"] = merged["valid_time"].apply(get_season)

    # Derive lead_time_bucket if not already present
    if "lead_time_bucket" not in merged.columns:
        if "lead_time_hrs" in merged.columns:
            merged["lead_time_bucket"] = merged["lead_time_hrs"].apply(get_lead_time_bucket)
        else:
            merged["lead_time_bucket"] = "0-24h"

    # Derive regime_id if not already present
    if "regime_id" not in merged.columns:
        merged["regime_id"] = default_regime_id

    group_cols = [
        "source_id",
        "region_id",
        "regime_id",
        "season",
        "lead_time_bucket",
        "variable",
    ]

    records = []
    now = datetime.now(timezone.utc)

    # 2. Group by (source_id, region_id, regime_id, season, lead_time_bucket, variable)
    for group_keys, group_data in merged.groupby(group_cols):
        source_id, region_id, regime_id, season, lead_time_bucket, variable = group_keys
        stratum_info = {
            "source_id": int(source_id),
            "region_id": int(region_id),
            "regime_id": int(regime_id),
            "season": str(season),
            "lead_time_bucket": str(lead_time_bucket),
            "variable": str(variable),
        }

        fcst_vals = group_data["value_fcst"].astype(float).tolist()
        obs_vals = group_data["value_obs"].astype(float).tolist()

        # 3. Minimum sample_size threshold enforcement
        metrics = compute_metrics(
            fcst_vals,
            obs_vals,
            min_sample_size=min_sample_size,
            stratum_info=stratum_info,
        )

        if metrics is not None:
            records.append(
                {
                    "source_id": int(source_id),
                    "region_id": int(region_id),
                    "regime_id": int(regime_id),
                    "season": str(season),
                    "lead_time_bucket": str(lead_time_bucket),
                    "variable": str(variable),
                    "rmse": metrics["rmse"],
                    "mae": metrics["mae"],
                    "bias": metrics["bias"],
                    "sample_size": metrics["sample_size"],
                    "last_updated": now,
                }
            )

    return pd.DataFrame(records)


def upsert_skill_scores(db_connection_or_session, scores_df: pd.DataFrame) -> int:
    """
    4. Writes results into the `skill_scores` table using an incremental update
    (upsert on the natural key: source_id, region_id, regime_id, season, lead_time_bucket, variable).
    Works with raw cursor, psycopg2, or SQLAlchemy session executing raw SQL.
    """
    if scores_df.empty:
        logger.info("No skill scores to upsert.")
        return 0

    upsert_sql = """
    UPDATE skill_scores
    SET rmse = :rmse,
        mae = :mae,
        bias = :bias,
        sample_size = :sample_size,
        last_updated = :last_updated
    WHERE source_id = :source_id
      AND region_id = :region_id
      AND regime_id = :regime_id
      AND season = :season
      AND lead_time_bucket = :lead_time_bucket
      AND variable = :variable;

    INSERT INTO skill_scores (source_id, region_id, regime_id, season, lead_time_bucket, variable, rmse, mae, bias, sample_size, last_updated)
    SELECT :source_id, :region_id, :regime_id, :season, :lead_time_bucket, :variable, :rmse, :mae, :bias, :sample_size, :last_updated
    WHERE NOT EXISTS (
        SELECT 1 FROM skill_scores
        WHERE source_id = :source_id
          AND region_id = :region_id
          AND regime_id = :regime_id
          AND season = :season
          AND lead_time_bucket = :lead_time_bucket
          AND variable = :variable
    );
    """

    count = 0
    # Support both SQLAlchemy session and raw DB-API 2.0 cursor
    is_sqlalchemy = hasattr(db_connection_or_session, "execute") and hasattr(
        db_connection_or_session, "commit"
    )

    for _, row in scores_df.iterrows():
        params = {
            "source_id": int(row["source_id"]),
            "region_id": int(row["region_id"]),
            "regime_id": int(row["regime_id"]),
            "season": str(row["season"]),
            "lead_time_bucket": str(row["lead_time_bucket"]),
            "variable": str(row["variable"]),
            "rmse": float(row["rmse"]),
            "mae": float(row["mae"]),
            "bias": float(row["bias"]),
            "sample_size": int(row["sample_size"]),
            "last_updated": row["last_updated"],
        }

        if is_sqlalchemy:
            from sqlalchemy import text

            db_connection_or_session.execute(text(upsert_sql), params)
        else:
            # psycopg2 style parameter mapping
            import re
            cursor = db_connection_or_session.cursor()
            psycopg2_sql = re.sub(r':([a-zA-Z0-9_]+)', r'%(\1)s', upsert_sql)
            cursor.execute(psycopg2_sql, params)
        count += 1

    if is_sqlalchemy:
        db_connection_or_session.commit()
    else:
        db_connection_or_session.commit()

    logger.info("Successfully upserted %d skill score strata.", count)
    return count
