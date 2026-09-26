"""
VaruNet Weighting Model Training Pipeline
Fits an XGBoost regressor on retrospective optimal blending weights using
strict chronological train/validation temporal split.
"""

import os
import joblib
import logging
from typing import List, Tuple, Optional, Any
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor

from ml.training.feature_engineering import (
    build_feature_set,
    compute_retrospective_optimal_weights,
)

logger = logging.getLogger("varunet.ml_training")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models")
)
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_SAVE_PATH = os.path.join(MODEL_DIR, "varunet_weighting_xgb.joblib")


def generate_synthetic_historical_dataset(
    n_days: int = 365,
    start_date: str = "2024-01-01",
    regions: List[int] = None,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generates a realistic historical dataset with:
    - Multiple forecast sources: NWP-proxy (Source 1), AI/ML-proxy (Source 2), Ensemble-proxy (Source 3)
    - Ground truth observation
    - Distinct regime and seasonal dynamics across time
    """
    if regions is None:
        regions = [1, 2, 3]

    np.random.seed(seed)
    records = []
    base_dt = datetime.strptime(start_date, "%Y-%m-%d")

    lead_times = [24, 48, 72]

    for day in range(n_days):
        cur_dt = base_dt + timedelta(days=day)
        month = cur_dt.month
        # Assign meteorological season
        if month in (1, 2):
            season = "Winter"
        elif month in (3, 4, 5):
            season = "Pre-Monsoon"
        elif month in (6, 7, 8, 9):
            season = "Monsoon"
        else:
            season = "Post-Monsoon"

        # Regime dynamics: 1 = Active / Normal, 2 = Break / Intense
        regime_id = 2 if (season == "Monsoon" and day % 7 in (0, 1)) else 1

        for r in regions:
            for lt in lead_times:
                lt_bucket = "0-24h" if lt <= 24 else ("24-48h" if lt <= 48 else "48-72h")

                # Ground truth weather state (e.g. rainfall in mm)
                base_truth = 15.0 if season == "Monsoon" else 3.0
                obs = max(0.0, float(np.random.gamma(shape=2.0, scale=base_truth)))

                # Source 1 (NWP-proxy): Physics-based, slightly over-predicts in Monsoon
                nwp_bias = 2.5 if season == "Monsoon" else 0.5
                nwp_fcst = max(0.0, obs + np.random.normal(nwp_bias, 4.0 + lt * 0.05))

                # Source 2 (AI/ML-proxy): Good at extremes, under-predicts light rain
                aiml_bias = -1.0 if obs < 10.0 else 0.2
                aiml_fcst = max(0.0, obs + np.random.normal(aiml_bias, 3.2 + lt * 0.04))

                # Source 3 (Ensemble-proxy): Conservative smoother
                ens_fcst = max(0.0, (nwp_fcst * 0.5 + aiml_fcst * 0.5) + np.random.normal(0.0, 2.0))

                records.append({
                    "region_id": r,
                    "valid_time": cur_dt,
                    "lead_time_hrs": lt,
                    "lead_time_bucket": lt_bucket,
                    "season": season,
                    "regime_id": regime_id,
                    "variable": "rainfall",
                    "fcst_nwp": nwp_fcst,
                    "fcst_aiml": aiml_fcst,
                    "fcst_ensemble": ens_fcst,
                    "observation": obs,
                })

    return pd.DataFrame(records)


def train_blending_weight_model(
    dataset_df: Optional[pd.DataFrame] = None,
    train_val_split_date: str = "2024-10-01",
    save_model: bool = True,
) -> Tuple[Any, pd.DataFrame, pd.DataFrame, List[str]]:
    """
    Executes training routine:
    1. Prepares dataset and computes retrospective optimal weights per row.
    2. Enforces strict chronological train/validation temporal split.
    3. Fits an XGBoost multi-output regressor to predict optimal weights.
    4. Saves model to ml/models/varunet_weighting_xgb.joblib.
    """
    if dataset_df is None:
        logger.info("Generating synthetic historical benchmark dataset...")
        dataset_df = generate_synthetic_historical_dataset(n_days=365, start_date="2024-01-01")

    source_cols = ["fcst_nwp", "fcst_aiml", "fcst_ensemble"]

    logger.info("Computing exact retrospective optimal weights label vector...")
    f_matrix = dataset_df[source_cols].to_numpy(dtype=np.float64)
    obs_vector = dataset_df["observation"].to_numpy(dtype=np.float64)

    # 2. Retrospective optimal weights calculation
    optimal_weights = compute_retrospective_optimal_weights(f_matrix, obs_vector)
    for i, col in enumerate(source_cols):
        dataset_df[f"target_weight_{col}"] = optimal_weights[:, i]

    # Feature engineering
    logger.info("Building features...")
    df_features, feature_names = build_feature_set(dataset_df, source_cols=source_cols)

    # 3. Train/validation split using genuine held-out chronological cutoff
    split_dt = pd.to_datetime(train_val_split_date)
    train_mask = df_features["valid_time"] < split_dt
    val_mask = df_features["valid_time"] >= split_dt

    train_df = df_features[train_mask].copy()
    val_df = df_features[val_mask].copy()

    logger.info(
        "Chronological Split: Train=%d samples (%s to %s), Validation=%d samples (%s to %s)",
        len(train_df),
        train_df["valid_time"].min().strftime("%Y-%m-%d"),
        train_df["valid_time"].max().strftime("%Y-%m-%d"),
        len(val_df),
        val_df["valid_time"].min().strftime("%Y-%m-%d"),
        val_df["valid_time"].max().strftime("%Y-%m-%d"),
    )

    X_train = train_df[feature_names].to_numpy(dtype=np.float64)
    target_weight_cols = [f"target_weight_{c}" for c in source_cols]
    y_train = train_df[target_weight_cols].to_numpy(dtype=np.float64)

    # Fit XGBoost MultiOutputRegressor
    logger.info("Fitting XGBoost regressor for forecast weight vector prediction...")
    base_xgb = xgb.XGBRegressor(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
    )
    model = MultiOutputRegressor(base_xgb)
    model.fit(X_train, y_train)

    if save_model:
        model_payload = {
            "model": model,
            "feature_names": feature_names,
            "source_cols": source_cols,
            "split_date": train_val_split_date,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        joblib.dump(model_payload, MODEL_SAVE_PATH)
        logger.info("Trained model saved successfully to: %s", MODEL_SAVE_PATH)

    return model, train_df, val_df, feature_names


if __name__ == "__main__":
    train_blending_weight_model()
