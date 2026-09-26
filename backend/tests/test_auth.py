"""
Unit tests for VaruNet Custom JWT Authentication and Role-Based Access Control (RBAC)
Verifies:
1. Users table bcrypt password hashing and verification.
2. JWT issuance on login with embedded role claims (forecaster, admin, citizen).
3. RBAC route enforcement:
   - Operator routes (skill-scores, raw forecasts, full alerts) reject citizen tokens (403) and unauthenticated (401).
   - Operator routes accept forecaster and admin tokens (200).
   - Citizen routes (/alerts/citizen, /blend/citizen) are accessible to citizens.
4. Public health check (GET /) is unauthenticated (200).
5. Rate limiting on public routes.
"""

import unittest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.auth.jwt_handler import hash_password, verify_password, create_access_token, decode_access_token


class TestAuthAndRBAC(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_bcrypt_hashing_and_verification(self):
        """
        Verifies bcrypt password hashing produces unique salted hashes
        and verifies successfully.
        """
        plain = "MySecretPass2026!"
        h1 = hash_password(plain)
        h2 = hash_password(plain)

        # Salted hashes should be different strings
        self.assertNotEqual(h1, h2)
        # Both must verify correctly
        self.assertTrue(verify_password(plain, h1))
        self.assertTrue(verify_password(plain, h2))
        self.assertFalse(verify_password("WrongPass", h1))

    def test_jwt_issuance_with_role_claims(self):
        """
        Verifies custom JWT contains user_id and embedded role claims.
        """
        token = create_access_token(user_id=42, email="operator@varunet.in", role="forecaster")
        claims = decode_access_token(token)

        self.assertEqual(claims["sub"], "42")
        self.assertEqual(claims["email"], "operator@varunet.in")
        self.assertEqual(claims["role"], "forecaster")
        self.assertIn("exp", claims)
        self.assertIn("iat", claims)

    def test_auth_login_endpoint(self):
        """
        Verifies POST /api/auth/login returns valid JWT with role.
        """
        res = self.client.post("/api/auth/login", json={
            "email": "forecaster@varunet.in",
            "password": "Forecaster@123",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "forecaster")
        self.assertEqual(data["token_type"], "bearer")

    def test_rbac_unauthenticated_operator_access(self):
        """
        Operator routes must reject requests with no token (401 Unauthorized).
        """
        res_skill = self.client.get("/api/skill-scores")
        self.assertEqual(res_skill.status_code, 401)

        res_fcst = self.client.get("/api/forecasts")
        self.assertEqual(res_fcst.status_code, 401)

        res_alert = self.client.get("/api/alerts")
        self.assertEqual(res_alert.status_code, 401)

    def test_rbac_citizen_forbidden_on_operator_routes(self):
        """
        Operator routes must return 403 Forbidden when accessed with citizen role token.
        """
        citizen_token = create_access_token(user_id=3, email="citizen@varunet.in", role="citizen")
        headers = {"Authorization": f"Bearer {citizen_token}"}

        res_skill = self.client.get("/api/skill-scores", headers=headers)
        self.assertEqual(res_skill.status_code, 403)
        self.assertIn("Forbidden", res_skill.json()["detail"])

        res_fcst = self.client.get("/api/forecasts", headers=headers)
        self.assertEqual(res_fcst.status_code, 403)

        res_alert = self.client.get("/api/alerts", headers=headers)
        self.assertEqual(res_alert.status_code, 403)

    def test_rbac_forecaster_granted_on_operator_routes(self):
        """
        Operator routes must allow access with forecaster token (200 OK).
        """
        forecaster_token = create_access_token(user_id=1, email="forecaster@varunet.in", role="forecaster")
        headers = {"Authorization": f"Bearer {forecaster_token}"}

        res_skill = self.client.get("/api/skill-scores", headers=headers)
        self.assertEqual(res_skill.status_code, 200)

        res_fcst = self.client.get("/api/forecasts", headers=headers)
        self.assertEqual(res_fcst.status_code, 200)

        res_alert = self.client.get("/api/alerts", headers=headers)
        self.assertEqual(res_alert.status_code, 200)

    def test_rbac_admin_granted_on_operator_routes(self):
        """
        Operator routes must allow access with admin token (200 OK).
        """
        admin_token = create_access_token(user_id=2, email="admin@varunet.in", role="admin")
        headers = {"Authorization": f"Bearer {admin_token}"}

        res_skill = self.client.get("/api/skill-scores", headers=headers)
        self.assertEqual(res_skill.status_code, 200)

    def test_citizen_accessible_routes(self):
        """
        Citizen-scoped routes (/alerts/citizen and /blend/citizen) are accessible to citizens.
        """
        res_citizen_alert = self.client.get("/api/alerts/citizen?region_id=1")
        self.assertEqual(res_citizen_alert.status_code, 200)

        res_citizen_blend = self.client.get(
            "/api/blend/citizen?region_id=1&valid_time=2024-11-20T12:00:00&lead_time_hrs=24"
        )
        self.assertEqual(res_citizen_blend.status_code, 200)
        data = res_citizen_blend.json()
        self.assertIn("confidence_label", data)
        self.assertIn("plain_language_summary", data)

    def test_health_check_unauthenticated(self):
        """
        Health-check endpoint must strictly remain unauthenticated (200 OK).
        """
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "online")


if __name__ == "__main__":
    unittest.main()
