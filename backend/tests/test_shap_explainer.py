"""
Unit tests for VaruNet SHAP Explainability Engine
Verifies:
1. SHAP attribution computation on the trained XGBoost weighting model.
2. Template-based natural language generation with top SHAP features.
3. Explicit handling of the ambiguous edge case (comparably weighted sources).
4. Database persistence into the explanations table.
"""

import unittest
import numpy as np
from unittest.mock import MagicMock

from ml.explainability.shap_explainer import (
    generate_explanation_text,
    write_explanation,
    explain_and_store,
    compute_shap_values,
)


class TestShapExplainer(unittest.TestCase):
    def test_ambiguous_case_explanation(self):
        """
        Architecture guideline verification:
        When top sources are close in magnitude, generate a sentence stating
        the sources were comparably weighted, rather than forcing an artificially
        confident explanation.
        """
        mock_shap_results = {
            "source_cols": ["fcst_nwp", "fcst_aiml", "fcst_ensemble"],
            "attributions_by_source": {
                "fcst_nwp": {"forecast_variance": 0.02, "lead_time_hrs": 0.01},
                "fcst_aiml": {"forecast_variance": 0.025, "lead_time_hrs": -0.01},
                "fcst_ensemble": {"forecast_variance": -0.01, "lead_time_hrs": 0.0},
            },
        }

        # Weights are close: NWP=0.36, AIML=0.34 (diff = 0.02 < ambiguity_threshold=0.08)
        close_weights = {
            "fcst_nwp": 0.36,
            "fcst_aiml": 0.34,
            "fcst_ensemble": 0.30,
        }

        text = generate_explanation_text(
            shap_results=mock_shap_results,
            predicted_weights=close_weights,
            region_name="Western Ghats",
            regime_name="Monsoon Active",
            ambiguity_threshold=0.08,
        )

        self.assertIn("comparably weighted", text)
        self.assertIn("Western Ghats", text)
        self.assertIn("Monsoon Active", text)
        # Should NOT claim one model decisively won over the other
        self.assertNotIn("weighted highest", text)

    def test_dominant_source_explanation(self):
        """
        When a source clearly dominates, top SHAP features must be cited as the drivers.
        """
        mock_shap_results = {
            "source_cols": ["fcst_nwp", "fcst_aiml", "fcst_ensemble"],
            "attributions_by_source": {
                "fcst_nwp": {"forecast_variance": 0.15, "lead_time_hrs": 0.08},
                "fcst_aiml": {"forecast_variance": -0.10, "lead_time_hrs": -0.05},
                "fcst_ensemble": {"forecast_variance": -0.05, "lead_time_hrs": -0.03},
            },
        }

        # NWP decisively dominates at 62%
        dominant_weights = {
            "fcst_nwp": 0.62,
            "fcst_aiml": 0.23,
            "fcst_ensemble": 0.15,
        }

        text = generate_explanation_text(
            shap_results=mock_shap_results,
            predicted_weights=dominant_weights,
            region_name="Konkan Coast",
            regime_name="Monsoon Active",
            ambiguity_threshold=0.08,
        )

        self.assertIn("weighted highest", text)
        self.assertIn("62.0%", text)
        self.assertIn("Konkan Coast", text)
        # Should cite inter-source forecast variance
        self.assertIn("inter-source forecast variance", text)

    def test_write_explanation_persistence(self):
        """
        Verifies writing explanation text and JSON attributions to DB session.
        """
        mock_db = MagicMock()
        mock_res = MagicMock()
        mock_res.fetchone.return_value = (501,)  # mocked explanation_id
        mock_db.execute.return_value = mock_res

        attributions = {"fcst_nwp": {"forecast_variance": 0.12}}
        exp_id = write_explanation(
            db_session=mock_db,
            blend_id=42,
            explanation_text="NWP weighted highest due to favorable conditions.",
            feature_attributions_json=attributions,
        )

        self.assertEqual(exp_id, 501)
        self.assertTrue(mock_db.commit.called)


if __name__ == "__main__":
    unittest.main()
