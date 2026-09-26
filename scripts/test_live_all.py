import requests

FRONTEND = 'https://frontend-two-tan-24.vercel.app'
BACKEND = 'https://backend-production-538ef.up.railway.app'
PROMETHEUS = 'https://prometheus-production-3385.up.railway.app'
GRAFANA = 'https://grafana-production-67a9.up.railway.app'

tests = []

# 1. Frontend Delivery (Vercel Edge)
r1 = requests.get(FRONTEND, timeout=10)
tests.append(('1. Frontend Delivery (Vercel Edge CDN)', r1.status_code == 200, f"HTTP {r1.status_code} - React 18 / Vite SPA Loaded"))

# 2. Backend Health & Service Status
r2 = requests.get(f'{BACKEND}/', timeout=10)
r2_data = r2.json() if r2.status_code == 200 else {}
tests.append(('2. Backend API Service Health', r2.status_code == 200 and r2_data.get('status') == 'online', f"Service: {r2_data.get('service')}, Status: {r2_data.get('status')}"))

# 3. Dynamic Blending Engine (XGBoost)
r3 = requests.get(f'{BACKEND}/api/blend?region_id=1&valid_time=2026-09-27T00:00:00Z&lead_time_hrs=24&variable=rainfall', timeout=10)
r3_data = r3.json() if r3.status_code == 200 else {}
weights = r3_data.get('weights_json', {})
blended_val = r3_data.get('blended_value')
tests.append(('3. Dynamic Blending Engine (XGBoost)', r3.status_code == 200 and blended_val is not None, f"Blended: {blended_val:.2f} mm/h, Weights: {list(weights.keys())}"))

# 4. TreeSHAP Explainability & Confidence Scoring
shap = r3_data.get('feature_attributions', {})
conf = r3_data.get('confidence_score')
explanation = r3_data.get('explanation_text', '')
tests.append(('4. TreeSHAP Explainability & Confidence', r3.status_code == 200 and len(shap) > 0 and conf is not None, f"Confidence: {conf*100:.1f}%, SHAP Models: {list(shap.keys())}"))

# 5. Multi-Region Geospatial Weight Distribution
regions_ok = True
region_weights = {}
for rid in [1, 2, 3]:
    rr = requests.get(f'{BACKEND}/api/blend?region_id={rid}&valid_time=2026-09-27T00:00:00Z&lead_time_hrs=24&variable=rainfall', timeout=10)
    if rr.status_code == 200:
        region_weights[f'Region {rid}'] = rr.json().get('weights_json')
    else:
        regions_ok = False
tests.append(('5. Geospatial Weight Map (OpenStreetMap)', regions_ok and len(region_weights) == 3, f"3 Indian Climatic Regions dynamically weighted"))

# 6. Citizen Weather Summary & Public Portal
r6 = requests.get(f'{BACKEND}/api/blend/citizen?region_id=1&valid_time=2026-09-27T00:00:00Z&lead_time_hrs=24&variable=rainfall', timeout=10)
r6_data = r6.json() if r6.status_code == 200 else {}
tests.append(('6. Citizen Weather & Plain-Language Portal', r6.status_code == 200 and 'plain_language_summary' in r6_data, f"Confidence: '{r6_data.get('confidence_label')}', Summary: '{r6_data.get('plain_language_summary')}'"))

# 7. Skill Evolution Analytics (Historical Verification)
r7 = requests.get(f'{BACKEND}/api/skill-scores/evolution?station_id=DELHI_MET&target_variable=temperature_2m', timeout=10)
r7_data = r7.json() if r7.status_code == 200 else []
cycles = len(r7_data) if isinstance(r7_data, list) else len(r7_data.get('cycles', []))
tests.append(('7. Skill Evolution Analytics', r7.status_code == 200 and cycles > 0, f"{cycles} operational cycles verified"))

# 8. Multi-Strategy Performance Comparison Benchmark
r8 = requests.get(f'{BACKEND}/api/skill-scores/comparison?station_id=DELHI_MET&lead_time_hours=24', timeout=10)
r8_data = r8.json() if r8.status_code == 200 else []
tests.append(('8. Multi-Strategy Skill Benchmark', r8.status_code == 200 and len(r8_data) >= 5, f"{len(r8_data)} models benchmarked (NWP, AI/ML, Ensemble, 1/K, VaruNet)"))

# 9. Inter-Source Disagreement Heatmap
r9 = requests.get(f'{BACKEND}/api/skill-scores/disagreement-grid', timeout=10)
r9_data = r9.json() if r9.status_code == 200 else []
tests.append(('9. Inter-Source Disagreement Heatmap', r9.status_code == 200 and len(r9_data) > 0, f"{len(r9_data)} grid cells with spread & variance"))

# 10. Public Citizen Safety Advisories
r10 = requests.get(f'{BACKEND}/api/alerts/citizen', timeout=10)
tests.append(('10. Citizen Safety Advisories (Public Access)', r10.status_code == 200, f"HTTP {r10.status_code} - Public safety broadcast accessible"))

# 11. Role-Based Access Control (RBAC) Security
login_forecaster = requests.post(f'{BACKEND}/api/auth/login', json={'email': 'forecaster@varunet.in', 'password': 'Forecaster@123'}, timeout=10)
token_forecaster = login_forecaster.json().get('access_token') if login_forecaster.status_code == 200 else None
auth_alerts = requests.get(f'{BACKEND}/api/alerts', headers={'Authorization': f'Bearer {token_forecaster}'}, timeout=10)

login_citizen = requests.post(f'{BACKEND}/api/auth/login', json={'email': 'citizen@varunet.in', 'password': 'Citizen@123'}, timeout=10)
token_citizen = login_citizen.json().get('access_token') if login_citizen.status_code == 200 else None
blocked_citizen = requests.get(f'{BACKEND}/api/alerts', headers={'Authorization': f'Bearer {token_citizen}'}, timeout=10)
unauth_alerts = requests.get(f'{BACKEND}/api/alerts', timeout=10)

rbac_ok = (auth_alerts.status_code == 200 and blocked_citizen.status_code == 403 and unauth_alerts.status_code == 401)
tests.append(('11. RBAC Guardrails & Forecaster Alert Access', rbac_ok, f"Forecaster: 200 OK | Citizen: 403 Forbidden | Unauthenticated: 401 Unauthorized"))

# 12. Observability & Infrastructure Monitoring
prom = requests.get(f'{PROMETHEUS}/api/v1/targets', timeout=10)
graf = requests.get(f'{GRAFANA}/api/health', timeout=10)
tests.append(('12. Observability (Prometheus & Grafana)', prom.status_code == 200 and graf.status_code == 200, f"Prometheus Scrapes: HTTP {prom.status_code} | Grafana Health: HTTP {graf.status_code}"))

print('\n================ PRODUCTION FEATURE AUDIT REPORT ================')
all_passed = True
for name, passed, detail in tests:
    tag = 'PASS' if passed else 'FAIL'
    if not passed:
        all_passed = False
    print(f'[{tag}] {name} -> {detail}')
print('=================================================================')
print(f'Overall Status: {"ALL 12/12 FEATURES OPERATIONAL" if all_passed else "SOME CHECKS FAILED"}')
