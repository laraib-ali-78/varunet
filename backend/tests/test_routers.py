"""
Unit tests for VaruNet FastAPI Routers
Verifies:
1. /docs and /openapi.json OpenAPI spec availability.
2. /api/forecasts and /api/observations endpoints.
3. /api/skill-scores endpoint.
4. /api/blend dynamic blending with confidence and SHAP explanation.
5. /api/alerts hazard alert endpoint.
"""

import unittest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.auth.jwt_handler import create_access_token


class TestVaruNetRouters(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.forecaster_token = create_access_token(
            user_id=1, email="forecaster@varunet.in", role="forecaster"
        )
        self.auth_headers = {"Authorization": f"Bearer {self.forecaster_token}"}

    def test_health_and_docs_endpoints(self):
        """
        Verifies health check and automatic OpenAPI documentation.
        """
        res_health = self.client.get("/")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "online")

        res_docs = self.client.get("/docs")
        self.assertEqual(res_docs.status_code, 200)

        res_openapi = self.client.get("/openapi.json")
        self.assertEqual(res_openapi.status_code, 200)
        openapi_spec = res_openapi.json()
        self.assertIn("/api/forecasts", openapi_spec["paths"])
        self.assertIn("/api/observations", openapi_spec["paths"])
        self.assertIn("/api/skill-scores", openapi_spec["paths"])
        self.assertIn("/api/blend", openapi_spec["paths"])
        self.assertIn("/api/alerts", openapi_spec["paths"])

    def test_forecasts_and_observations_routes(self):
        """
        Verifies GET /api/forecasts and GET /api/observations response structures.
        """
        res_fcst = self.client.get("/api/forecasts?region_id=1&lead_time_hrs=24", headers=self.auth_headers)
        self.assertEqual(res_fcst.status_code, 200)
        self.assertIsInstance(res_fcst.json(), list)

        res_obs = self.client.get("/api/observations?region_id=1")
        self.assertEqual(res_obs.status_code, 200)
        self.assertIsInstance(res_obs.json(), list)

    def test_skill_scores_route(self):
        """
        Verifies GET /api/skill-scores response structure.
        """
        res_scores = self.client.get("/api/skill-scores?region_id=1&season=Monsoon", headers=self.auth_headers)
        self.assertEqual(res_scores.status_code, 200)
        self.assertIsInstance(res_scores.json(), list)

    def test_blend_route_computation(self):
        """
        Verifies GET /api/blend computes dynamic weights, confidence, and SHAP explanation.
        """
        params = {
            "region_id": 1,
            "valid_time": "2024-11-20T12:00:00",
            "lead_time_hrs": 24,
            "variable": "rainfall",
            "regime_id": 1,
        }
        res_blend = self.client.get("/api/blend", params=params)
        self.assertEqual(res_blend.status_code, 200)
        data = res_blend.json()

        self.assertEqual(data["region_id"], 1)
        self.assertIn("blended_value", data)
        self.assertIn("weights_json", data)
        self.assertIn("confidence_score", data)
        self.assertIn("explanation_text", data)

        # Confidence bounded [0, 1]
        self.assertGreaterEqual(data["confidence_score"], 0.0)
        self.assertLessEqual(data["confidence_score"], 1.0)

        # Full weight vector
        self.assertIn("fcst_nwp", data["weights_json"])
        self.assertIn("fcst_aiml", data["weights_json"])
        self.assertIn("fcst_ensemble", data["weights_json"])
        self.assertAlmostEqual(sum(data["weights_json"].values()), 1.0, places=4)

        # Explanation sentence generated
        self.assertIsInstance(data["explanation_text"], str)
        self.assertGreater(len(data["explanation_text"]), 10)

    def test_alerts_route(self):
        """
        Verifies GET /api/alerts response structure.
        """
        res_alerts = self.client.get("/api/alerts?region_id=1&severity=Orange", headers=self.auth_headers)
        self.assertEqual(res_alerts.status_code, 200)
        self.assertIsInstance(res_alerts.json(), list)


if __name__ == "__main__":
    unittest.main()
