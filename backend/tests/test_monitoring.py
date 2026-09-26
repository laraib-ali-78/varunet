"""
Unit tests for Prometheus Metrics Instrumentation
Verifies:
1. /metrics endpoint exposes Prometheus metrics without authentication.
2. Request count and request latency metrics are tracked.
"""

import unittest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestPrometheusMetrics(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_metrics_endpoint_available(self):
        """
        Verifies /metrics endpoint returns standard Prometheus text format.
        """
        # Trigger an API call first to increment metrics
        self.client.get("/")

        res = self.client.get("/metrics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/plain", res.headers.get("content-type", ""))

        content = res.text
        # Verify request count metric
        self.assertIn("http_requests_total", content)
        # Verify request latency metric
        self.assertIn("http_request_duration_seconds", content)


if __name__ == "__main__":
    unittest.main()
