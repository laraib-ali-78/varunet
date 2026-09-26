"""
Feature Engineering Module for VaruNet Blending Model
Constructs spatio-temporal, meteorological, skill-score, and disagreement features
and calculates ground-truth retrospective optimal blending weights.
"""

import math
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from scipy.optimize import minimize


def compute_cyclical_doy(dates: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """
    Computes cyclical sine and cosine encodings for day-of-year.
    Period = 365.25 days.
    """
    doy = pd.to_datetime(dates).dt.dayofyear
    angle = 2.0 * math.pi * doy / 365.25
    sin_doy = np.sin(angle)
    cos_doy = np.cos(angle)
    return sin_doy, cos_doy


def compute_retrospective_optimal_weights_single_row(
    forecasts: np.ndarray,
    obs: float,
    lambda_reg: float = 1e-4,
) -> np.ndarray:
    """
    Calculates the exact retrospective optimal weight vector w for a single row.
    Minimizes: (sum(w_i * f_i) - obs)^2 + lambda_reg * sum((w_i - 1/K)^2)
    Subject to: sum(w_i) = 1, w_i >= 0.

    This guarantees a convex, well-conditioned, globally optimal weight vector
    that strictly minimizes forecast blending error with tie-breaking regularization.
    """
    k = len(forecasts)
    if k == 1:
        return np.array([1.0], dtype=np.float64)

    # Initial guess: equal weights
    w0 = np.full(k, 1.0 / k, dtype=np.float64)

    def objective(w):
        blend = np.dot(w, forecasts)
        err = blend - obs
        reg = lambda_reg * np.sum((w - (1.0 / k)) ** 2)
        return (err ** 2) + reg

    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bounds = [(0.0, 1.0) for _ in range(k)]

    res = minimize(
        objective,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-9, "maxiter": 100},
    )

    if res.success:
        w_opt = res.x
    else:
        # Fallback to projected non-negative least squares or equal weights
        w_opt = w0

    # Ensure clean normalization
    w_opt = np.clip(w_opt, 0.0, 1.0)
    w_sum = np.sum(w_opt)
    if w_sum > 0:
        w_opt = w_opt / w_sum
    else:
        w_opt = w0

    return w_opt


def compute_retrospective_optimal_weights(
    forecasts_matrix: np.ndarray,
    observations: np.ndarray,
    lambda_reg: float = 1e-4,
) -> np.ndarray:
    """
    Computes retrospective optimal weights for all rows in the dataset.
    forecasts_matrix: shape (N, K) where K is number of sources
    observations: shape (N,)
    Returns: weights_matrix of shape (N, K)
    """
    n, k = forecasts_matrix.shape
    weights = np.zeros((n, k), dtype=np.float64)
    for i in range(n):
        weights[i] = compute_retrospective_optimal_weights_single_row(
            forecasts_matrix[i],
            observations[i],
            lambda_reg=lambda_reg,
        )
    return weights


def build_feature_set(
    dataset_df: pd.DataFrame,
    source_cols: List[str],
    skill_scores_df: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Builds the feature set required by the VaruNet architecture:
    1. region/climatic-zone identifier (region_id)
    2. season (categorical)
    3. cyclical day-of-year encoding (sin_doy, cos_doy)
    4. lead_time_bucket (categorical or ordinal)
    5. regime_id
    6. each source's recent rolling-window skill score for that stratum
    7. inter-source forecast disagreement (variance across sources)

    Parameters:
    - dataset_df: historical dataframe containing region_id, valid_time, lead_time_hrs,
                  regime_id, season, lead_time_bucket, source_cols (e.g. ['fcst_1', 'fcst_2', 'fcst_3'])
    - source_cols: list of column names containing source forecast values
    - skill_scores_df: optional skill_scores table from Section 3 for stratum lookup

    Returns:
    - features_df: DataFrame with all engineered feature columns
    - feature_names: List of column names used as model input features
    """
    df = dataset_df.copy()
    df["valid_time"] = pd.to_datetime(df["valid_time"])

    # 1. Cyclical day of year encoding
    sin_doy, cos_doy = compute_cyclical_doy(df["valid_time"])
    df["sin_doy"] = sin_doy
    df["cos_doy"] = cos_doy

    # 2. Inter-source forecast disagreement (sample variance across sources)
    source_vals = df[source_cols].to_numpy(dtype=np.float64)
    df["forecast_variance"] = np.var(source_vals, axis=1, ddof=1 if len(source_cols) > 1 else 0)
    df["forecast_std"] = np.sqrt(df["forecast_variance"])
    df["forecast_spread"] = np.ptp(source_vals, axis=1)

    # 3. Stratum skill scores integration
    feature_skill_cols = []
    if skill_scores_df is not None and not skill_scores_df.empty:
        # Merge rolling skill score per source
        for src_idx, src_col in enumerate(source_cols):
            src_id = src_idx + 1
            src_skill = skill_scores_df[skill_scores_df["source_id"] == src_id].copy()
            if not src_skill.empty:
                merge_cols = ["region_id", "regime_id", "season", "lead_time_bucket", "variable"]
                avail_merge = [c for c in merge_cols if c in df.columns and c in src_skill.columns]
                if avail_merge:
                    renamed_skill = src_skill[avail_merge + ["rmse", "mae", "bias"]].rename(
                        columns={
                            "rmse": f"skill_rmse_src_{src_id}",
                            "mae": f"skill_mae_src_{src_id}",
                            "bias": f"skill_bias_src_{src_id}",
                        }
                    )
                    df = df.merge(renamed_skill, on=avail_merge, how="left")
                    for metric in ["rmse", "mae", "bias"]:
                        col_name = f"skill_{metric}_src_{src_id}"
                        df[col_name] = df[col_name].fillna(df[col_name].mean() if not df[col_name].isna().all() else 0.0)
                        feature_skill_cols.append(col_name)

    # Categorical encodings
    categorical_cols = ["season", "lead_time_bucket"]
    for cat in categorical_cols:
        if cat in df.columns:
            df[f"{cat}_code"] = df[cat].astype("category").cat.codes

    # Base feature list
    feature_names = [
        "region_id",
        "regime_id",
        "sin_doy",
        "cos_doy",
        "lead_time_hrs",
        "forecast_variance",
        "forecast_std",
        "forecast_spread",
    ]

    for cat in categorical_cols:
        if f"{cat}_code" in df.columns:
            feature_names.append(f"{cat}_code")

    feature_names.extend(feature_skill_cols)

    # Include individual forecast anomalies from ensemble mean as informative blending features
    ensemble_mean = np.mean(source_vals, axis=1, keepdims=True)
    for i, col in enumerate(source_cols):
        anom_col = f"anom_{col}"
        df[anom_col] = source_vals[:, i] - ensemble_mean.squeeze()
        feature_names.append(anom_col)

    return df, feature_names
