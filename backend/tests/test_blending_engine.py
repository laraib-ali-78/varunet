"""
Unit tests for VaruNet Blending Engine
Verifies:
1. Weight prediction and normalization (sums to 1, non-negative).
2. Applying weight vector to produce blended_value.
3. Statistical confidence estimation (higher agreement -> higher confidence, higher spread -> lower confidence).
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from backend.app.services.blending_engine import (
    compute_confidence_score,
    predict_weights,
    apply_weights,
    blend_and_store,
)


class TestBlendingEngine(unittest.TestCase):
    def test_statistical_confidence_calculation(self):
        """
        Confidence estimation hard rule:
        Higher agreement -> higher confidence.
        Higher disagreement -> explicitly lower confidence.
        No separate ML model.
        """
        # Case A: Perfect agreement across sources
        fcst_perfect = [20.0, 20.0, 20.0]
        conf_perfect = compute_confidence_score(fcst_perfect)
        self.assertAlmostEqual(conf_perfect, 1.0, places=5)

        # Case B: Slight spread
        fcst_slight = [19.0, 20.0, 21.0]
        conf_slight = compute_confidence_score(fcst_slight)

        # Case C: High spread / disagreement
        fcst_high_spread = [5.0, 20.0, 35.0]
        conf_high_spread = compute_confidence_score(fcst_high_spread)

        # Case D: Extreme disagreement
        fcst_extreme = [0.0, 50.0, 100.0]
        conf_extreme = compute_confidence_score(fcst_extreme)

        # Strictly monotonic confidence degradation with increasing spread
        self.assertGreater(conf_perfect, conf_slight)
        self.assertGreater(conf_slight, conf_high_spread)
        self.assertGreater(conf_high_spread, conf_extreme)
        self.assertGreaterEqual(conf_extreme, 0.0)
        self.assertLessEqual(conf_perfect, 1.0)

    def test_predict_and_apply_weights(self):
        """
        Verifies weight vector prediction from trained model, normalization,
        and application to source forecasts.
        """
        source_fcsts = {
            "fcst_nwp": 12.0,
            "fcst_aiml": 15.0,
            "fcst_ensemble": 13.5,
        }

        weights = predict_weights(
            region_id=1,
            valid_time="2024-11-15 12:00:00",
            lead_time_hrs=24,
            variable="rainfall",
            source_forecasts=source_fcsts,
            regime_id=1,
        )

        # 1. Weights structure & normalization checks
        self.assertIn("fcst_nwp", weights)
        self.assertIn("fcst_aiml", weights)
        self.assertIn("fcst_ensemble", weights)

        for src, w in weights.items():
            self.assertGreaterEqual(w, 0.0)
            self.assertLessEqual(w, 1.0)

        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

        # 2. Applying weights
        blended_val = apply_weights(source_fcsts, weights)
        expected_manual = (
            weights["fcst_nwp"] * 12.0
            + weights["fcst_aiml"] * 15.0
            + weights["fcst_ensemble"] * 13.5
        )
        self.assertAlmostEqual(blended_val, expected_manual, places=6)

    def test_blend_and_store_pipeline(self):
        """
        Verifies end-to-end blend generation with mock DB session.
        """
        mock_db = MagicMock()
        mock_res = MagicMock()
        mock_res.fetchone.return_value = (101,)  # mocked blend_id
        mock_db.execute.return_value = mock_res

        source_fcsts = {
            "fcst_nwp": 22.0,
            "fcst_aiml": 24.0,
            "fcst_ensemble": 23.0,
        }

        result = blend_and_store(
            db_session=mock_db,
            region_id=2,
            valid_time="2024-12-01 06:00:00",
            lead_time_hrs=48,
            variable="rainfall",
            source_forecasts=source_fcsts,
            regime_id=1,
        )

        self.assertEqual(result["blend_id"], 101)
        self.assertEqual(result["region_id"], 2)
        self.assertIn("fcst_nwp", result["weights_json"])
        self.assertGreaterEqual(result["confidence_score"], 0.0)
        self.assertLessEqual(result["confidence_score"], 1.0)
        self.assertTrue(mock_db.commit.called)


if __name__ == "__main__":
    unittest.main()
