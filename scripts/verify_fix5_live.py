import requests

BACKEND = 'https://backend-production-538ef.up.railway.app'

print("=== 1. OPERATOR LOGIN & AUTHENTICATION ===")
login_res = requests.post(f"{BACKEND}/api/auth/login", json={
    "email": "forecaster@varunet.in",
    "password": "Forecaster@123"
})
print("Login status:", login_res.status_code)
assert login_res.status_code == 200, f"Login failed: {login_res.text}"
token_data = login_res.json()
token = token_data.get("access_token")
print(f"Logged in as {token_data.get('email')} with role {token_data.get('role')}")

headers = {"Authorization": f"Bearer {token}"}

print("\n=== 2. OPERATOR ACCESS TO /forecasts ===")
fcst_res = requests.get(f"{BACKEND}/api/forecasts?region_id=1&limit=5", headers=headers)
print("GET /api/forecasts status:", fcst_res.status_code)
assert fcst_res.status_code == 200, f"Forecasts failed: {fcst_res.text}"
fcsts = fcst_res.json()
print(f"Fetched {len(fcsts)} forecast records without 401. Sample: Source {fcsts[0]['source_id']} = {fcsts[0]['value']} mm")

print("\n=== 3. OPERATOR ACCESS TO /skill-scores ===")
skill_res = requests.get(f"{BACKEND}/api/skill-scores?region_id=1&limit=5", headers=headers)
print("GET /api/skill-scores status:", skill_res.status_code)
assert skill_res.status_code == 200, f"Skill scores failed: {skill_res.text}"
skills = skill_res.json()
print(f"Fetched {len(skills)} skill score records without 401. Sample: Source {skills[0]['source_id']} RMSE = {skills[0]['rmse']}")

print("\n=== 4. CITIZEN PORTAL (COMPLETELY UNAUTHENTICATED) ===")
# 4a. Citizen Alerts (No token)
citizen_alerts = requests.get(f"{BACKEND}/api/alerts/citizen?region_id=1")
print("GET /api/alerts/citizen status:", citizen_alerts.status_code)
assert citizen_alerts.status_code == 200, f"Citizen alerts failed: {citizen_alerts.text}"
print(f"Citizen alerts returned HTTP {citizen_alerts.status_code} (Zero 401s)")

# 4b. Citizen Blend (No token, with real 2024-06-15 date)
citizen_blend = requests.get(f"{BACKEND}/api/blend/citizen?region_id=1&valid_time=2024-06-15T00:00:00Z&lead_time_hrs=24&variable=rainfall")
print("GET /api/blend/citizen status:", citizen_blend.status_code)
assert citizen_blend.status_code == 200, f"Citizen blend failed: {citizen_blend.text}"
c_data = citizen_blend.json()
print(f"Citizen blend returned HTTP {citizen_blend.status_code} (Zero 401s):")
print(f"  Confidence: {c_data.get('confidence_label')}")
print(f"  Summary: {c_data.get('plain_language_summary')}")
print(f"  Blended Value: {c_data.get('blended_value'):.2f}")

print("\nALL FIX 5 CHECKS PASSED: Operator authenticated without 401s, Citizen loads without login and without 401s!")
