"""
Unit tests for VaruNet Skill Scoring Engine
Verifies deterministic statistical calculations of RMSE, MAE, and signed Bias
against hand-computed known values and tests the sample size threshold enforcement.
"""

import math
import unittest
import pandas as pd
from datetime import datetime

from backend.app.services.skill_scoring_engine import (
    MIN_SAMPLE_SIZE,
    compute_metrics,
    compute_skill_scores,
    get_season,
    get_lead_time_bucket,
)


class TestSkillScoringEngine(unittest.TestCase):
    def test_hand_computed_metrics(self):
        """
        Hand-computed ground truth verification:
        Forecasts:    f = [10.0, 15.0, 20.0, 25.0]
        Observations: o = [12.0, 14.0, 17.0, 29.0]
        Errors (f-o):     [-2.0,  1.0,  3.0, -4.0]

        1. Absolute Errors: [2.0, 1.0, 3.0, 4.0]
           Sum = 10.0
           MAE = 10.0 / 4 = 2.5

        2. Squared Errors: [4.0, 1.0, 9.0, 16.0]
           Sum = 30.0
           MSE = 30.0 / 4 = 7.5
           RMSE = sqrt(7.5) = 2.7386127875258306

        3. Signed Bias:
           mean(f) = (10 + 15 + 20 + 25) / 4 = 17.5
           mean(o) = (12 + 14 + 17 + 29) / 4 = 18.0
           Bias = mean(f) - mean(o) = 17.5 - 18.0 = -0.5
        """
        f = [10.0, 15.0, 20.0, 25.0]
        o = [12.0, 14.0, 17.0, 29.0]

        # Explicitly pass min_sample_size=4 to allow computing on this small test batch
        metrics = compute_metrics(f, o, min_sample_size=4)

        self.assertIsNotNone(metrics)
        self.assertAlmostEqual(metrics["mae"], 2.5, places=7)
        self.assertAlmostEqual(metrics["rmse"], math.sqrt(7.5), places=7)
        self.assertAlmostEqual(metrics["bias"], -0.5, places=7)
        self.assertEqual(metrics["sample_size"], 4)

    def test_min_sample_size_enforcement(self):
        """
        Verifies that when sample size is below MIN_SAMPLE_SIZE (10),
        the engine returns None and does not emit an unreliable score.
        """
        f = [10.0, 15.0, 20.0, 25.0]
        o = [12.0, 14.0, 17.0, 29.0]

        # len is 4, default MIN_SAMPLE_SIZE is 10
        self.assertEqual(MIN_SAMPLE_SIZE, 10)
        metrics = compute_metrics(f, o, min_sample_size=MIN_SAMPLE_SIZE)

        # Must return None for low-data stratum
        self.assertIsNone(metrics)

    def test_dataframe_skill_scoring_pipeline(self):
        """
        Tests the end-to-end DataFrame join on region_id + valid_time + variable,
        grouping, and computation of skill scores.
        """
        # Create 10 forecast-observation pairs to satisfy MIN_SAMPLE_SIZE
        dates = [f"2026-07-{d:02d} 00:00:00" for d in range(1, 11)]

        forecasts_data = {
            "source_id": [1] * 10,
            "region_id": [2] * 10,
            "valid_time": dates,
            "lead_time_hrs": [24] * 10,
            "variable": ["rainfall"] * 10,
            "value": [10.0 + i for i in range(10)],  # 10.0 to 19.0
        }
        observations_data = {
            "region_id": [2] * 10,
            "valid_time": dates,
            "variable": ["rainfall"] * 10,
            "value": [9.0 + i for i in range(10)],   # 9.0 to 18.0 (error is constant +1.0)
        }

        fcst_df = pd.DataFrame(forecasts_data)
        obs_df = pd.DataFrame(observations_data)

        scores_df = compute_skill_scores(
            fcst_df,
            obs_df,
            min_sample_size=10,
            default_regime_id=1,
        )

        self.assertEqual(len(scores_df), 1)
        row = scores_df.iloc[0]
        self.assertEqual(row["source_id"], 1)
        self.assertEqual(row["region_id"], 2)
        self.assertEqual(row["season"], "Monsoon")  # July is Monsoon
        self.assertEqual(row["lead_time_bucket"], "0-24h")
        self.assertEqual(row["variable"], "rainfall")
        self.assertEqual(row["sample_size"], 10)
        # Constant error of +1.0:
        self.assertAlmostEqual(row["mae"], 1.0, places=6)
        self.assertAlmostEqual(row["rmse"], 1.0, places=6)
        self.assertAlmostEqual(row["bias"], 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
