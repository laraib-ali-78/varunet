"""
VaruNet SHAP Explainability Engine
Generates model-agnostic and TreeSHAP attributions for the XGBoost weighting model
and produces deterministic template-based natural language explanations.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union

import numpy as np
import pandas as pd
import joblib

logger = logging.getLogger("varunet.explainability")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# Default location for trained XGBoost weighting model
DEFAULT_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "varunet_weighting_xgb.joblib")
)

# Friendly readable descriptions for model features
FEATURE_NAME_DESCRIPTIONS = {
    "forecast_variance": "inter-source forecast variance",
    "forecast_std": "spread across NWP and AI models",
    "forecast_spread": "range of forecast divergence",
    "lead_time_hrs": "forecast lead time",
    "lead_time_bucket_code": "lead-time horizon stratum",
    "season_code": "seasonal climatology",
    "sin_doy": "day-of-year seasonal cycle",
    "cos_doy": "annual solar cycle phase",
    "region_id": "regional topography and microclimate",
    "regime_id": "prevailing synoptic weather regime",
    "anom_fcst_nwp": "NWP deviation from consensus mean",
    "anom_fcst_aiml": "AI/ML deviation from consensus mean",
    "anom_fcst_ensemble": "Ensemble deviation from consensus mean",
}

SOURCE_DISPLAY_NAMES = {
    "fcst_nwp": "NWP-proxy (Numerical Weather Prediction)",
    "fcst_aiml": "AI/ML-proxy (Deep/ML Forecast)",
    "fcst_ensemble": "Ensemble-proxy (Multi-Model Average)",
}


def compute_shap_values(
    feature_vector: np.ndarray,
    model_payload: Optional[Dict[str, Any]] = None,
    model_path: str = DEFAULT_MODEL_PATH,
) -> Dict[str, Any]:
    """
    1. Computes exact TreeSHAP attribution values for a single prediction row
       across all predicted source weights.
    """
    import shap

    if model_payload is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
        model_payload = joblib.load(model_path)

    model = model_payload["model"]
    feature_names = model_payload["feature_names"]
    source_cols = model_payload["source_cols"]

    if feature_vector.ndim == 1:
        X = feature_vector.reshape(1, -1)
    else:
        X = feature_vector

    attributions_by_source = {}
    base_values_by_source = {}

    # Handle MultiOutputRegressor with individual XGBoost estimators
    if hasattr(model, "estimators_"):
        estimators = model.estimators_
    else:
        estimators = [model]

    for idx, (source_col, estimator) in enumerate(zip(source_cols, estimators)):
        explainer = shap.TreeExplainer(estimator)
        shap_vals = explainer.shap_values(X)

        if isinstance(shap_vals, list):
            sv = np.array(shap_vals[0]).flatten()
        elif hasattr(shap_vals, "values"):
            sv = np.array(shap_vals.values).flatten()
        else:
            sv = np.array(shap_vals).flatten()

        base_val = float(explainer.expected_value) if np.isscalar(explainer.expected_value) else float(explainer.expected_value[0])
        base_values_by_source[source_col] = base_val

        # Map feature names to attribution values
        feat_dict = {}
        for fn, val in zip(feature_names, sv):
            feat_dict[fn] = float(val)

        attributions_by_source[source_col] = feat_dict

    return {
        "attributions_by_source": attributions_by_source,
        "base_values": base_values_by_source,
        "feature_names": feature_names,
        "source_cols": source_cols,
    }


def generate_explanation_text(
    shap_results: Dict[str, Any],
    predicted_weights: Dict[str, float],
    region_name: str = "Region",
    regime_name: str = "Normal",
    ambiguity_threshold: float = 0.08,
    top_k: int = 2,
) -> str:
    """
    2. Template-based natural language generator taking top 2-3 SHAP-ranked features.
    Produces one sentence.
    Handles the ambiguous case explicitly: if top features or weights are close
    in magnitude, generates a sentence stating sources were comparably weighted,
    rather than forcing an artificially confident explanation.
    """
    source_cols = shap_results["source_cols"]
    attributions = shap_results["attributions_by_source"]

    # Rank sources by predicted weight
    sorted_sources = sorted(predicted_weights.items(), key=lambda x: x[1], reverse=True)
    top_source, top_weight = sorted_sources[0]
    second_source, second_weight = sorted_sources[1] if len(sorted_sources) > 1 else (None, 0.0)

    # Edge Case: Ambiguous / Comparably Weighted
    weight_diff = abs(top_weight - second_weight)
    if weight_diff < ambiguity_threshold:
        top_name = SOURCE_DISPLAY_NAMES.get(top_source, top_source)
        second_name = SOURCE_DISPLAY_NAMES.get(second_source, second_source)
        return (
            f"Forecast sources were comparably weighted (with {top_name} at {top_weight:.1%} "
            f"and {second_name} at {second_weight:.1%}) due to close model consensus and balanced "
            f"atmospheric signals in this {region_name} ({regime_name} regime) context."
        )

    # Dominant source: extract top SHAP features positively pushing this source's weight
    source_attr = attributions.get(top_source, {})
    # Sort features by signed SHAP attribution
    sorted_feats = sorted(source_attr.items(), key=lambda x: abs(x[1]), reverse=True)

    # Select top-k features
    top_features = sorted_feats[:top_k]
    feature_phrases = []
    for fn, attr_val in top_features:
        desc = FEATURE_NAME_DESCRIPTIONS.get(fn, fn.replace("_", " "))
        direction = "higher" if attr_val >= 0 else "lower"
        feature_phrases.append(f"{desc} (driving {direction} weight)")

    reasons_text = " and ".join(feature_phrases) if feature_phrases else "historical performance consistency"
    top_display = SOURCE_DISPLAY_NAMES.get(top_source, top_source)

    return (
        f"{top_display} was weighted highest ({top_weight:.1%}) due to {reasons_text} "
        f"in this {region_name} ({regime_name} regime) context."
    )


def write_explanation(
    db_session,
    blend_id: int,
    explanation_text: str,
    feature_attributions_json: Dict[str, Any],
) -> Optional[int]:
    """
    3. Writes the explanation text and raw feature_attributions_json
       into the `explanations` table from Section 1, linked to the correct blend_id.
    """
    insert_sql = """
    INSERT INTO explanations (
        blend_id, explanation_text, feature_attributions_json
    ) VALUES (
        :blend_id, :explanation_text, :feature_attributions_json
    ) RETURNING explanation_id;
    """

    params = {
        "blend_id": int(blend_id),
        "explanation_text": str(explanation_text),
        "feature_attributions_json": json.dumps(feature_attributions_json),
    }

    explanation_id = None
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
            explanation_id = row[0]
        db_session.commit()
    elif hasattr(db_session, "execute"):
        # Generic session or mock with execute method
        res = db_session.execute(insert_sql, params)
        if res and hasattr(res, "fetchone"):
            row = res.fetchone()
            if row:
                explanation_id = row[0]
        if hasattr(db_session, "commit"):
            db_session.commit()
    else:
        cursor = db_session.cursor()
        psycopg2_sql = insert_sql.replace(":", "%(") + ")"
        cursor.execute(psycopg2_sql, params)
        row = cursor.fetchone()
        if row:
            explanation_id = row[0]
        db_session.commit()

    logger.info("Saved explanation record explanation_id=%s for blend_id=%d",
                explanation_id, blend_id)
    return explanation_id


def explain_and_store(
    db_session,
    blend_id: int,
    feature_vector: np.ndarray,
    predicted_weights: Dict[str, float],
    region_name: str = "Region",
    regime_name: str = "Active Monsoon",
    model_payload: Optional[Dict[str, Any]] = None,
    ambiguity_threshold: float = 0.08,
) -> Dict[str, Any]:
    """
    Full explanation pipeline:
    1. Computes SHAP values
    2. Generates natural language explanation text
    3. Writes to explanations table linked to blend_id
    """
    shap_results = compute_shap_values(
        feature_vector=feature_vector,
        model_payload=model_payload,
    )

    explanation_text = generate_explanation_text(
        shap_results=shap_results,
        predicted_weights=predicted_weights,
        region_name=region_name,
        regime_name=regime_name,
        ambiguity_threshold=ambiguity_threshold,
    )

    explanation_id = None
    if db_session is not None:
        explanation_id = write_explanation(
            db_session=db_session,
            blend_id=blend_id,
            explanation_text=explanation_text,
            feature_attributions_json=shap_results["attributions_by_source"],
        )

    return {
        "explanation_id": explanation_id,
        "blend_id": blend_id,
        "explanation_text": explanation_text,
        "feature_attributions": shap_results["attributions_by_source"],
    }
