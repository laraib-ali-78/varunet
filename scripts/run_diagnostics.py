import requests
import re
import json

FRONTEND = 'https://frontend-two-tan-24.vercel.app'
BACKEND = 'https://backend-production-538ef.up.railway.app'

print("=== STEP 1: FRONTEND CHECK ===")
r_front = requests.get(FRONTEND)
print(f"Status Code: {r_front.status_code}")
print(f"Response Length: {len(r_front.text)} bytes")
print("HTML Content snippet:")
print(r_front.text[:400])

js_files = re.findall(r'src="(/assets/[^"]+\.js)"', r_front.text)
print("JS Bundles found:", js_files)
for js in js_files:
    js_url = FRONTEND + js
    r_js = requests.get(js_url)
    print(f"Bundle {js} -> Status: {r_js.status_code}, Length: {len(r_js.text)} bytes")
    # check for api base url
    urls = set(re.findall(r'https://[a-zA-Z0-9\.\-_:]+\.railway\.app', r_js.text))
    print(f"Railway URLs found in JS bundle: {urls}")
    localhosts = set(re.findall(r'http://localhost:[0-9]+', r_js.text))
    print(f"Localhost URLs found in JS bundle: {localhosts}")

print("\n=== STEP 2: BACKEND /docs & REAL DATA ENDPOINT CHECK ===")
r_docs = requests.get(f"{BACKEND}/docs")
print(f"/docs Status Code: {r_docs.status_code}")
print(f"/docs Content Type: {r_docs.headers.get('content-type')}")
print(f"/docs contains swagger-ui: {'swagger-ui' in r_docs.text.lower()}")

# Test real data endpoints:
# 1. /api/skill-scores
r_skill = requests.get(f"{BACKEND}/api/skill-scores")
print(f"\nEndpoint /api/skill-scores:")
print(f"Status: {r_skill.status_code}")
print(f"Response: {r_skill.text[:300]}")

# 2. /api/skill-scores/comparison?station_id=DELHI_MET&lead_time_hours=24
r_comp = requests.get(f"{BACKEND}/api/skill-scores/comparison?station_id=DELHI_MET&lead_time_hours=24")
print(f"\nEndpoint /api/skill-scores/comparison?station_id=DELHI_MET&lead_time_hours=24:")
print(f"Status: {r_comp.status_code}")
print(f"Response: {r_comp.text[:300]}")

# 3. /api/blend?region_id=1&valid_time=2026-09-27T00:00:00Z&lead_time_hrs=24&variable=rainfall
r_blend = requests.get(f"{BACKEND}/api/blend?region_id=1&valid_time=2026-09-27T00:00:00Z&lead_time_hrs=24&variable=rainfall")
print(f"\nEndpoint /api/blend:")
print(f"Status: {r_blend.status_code}")
print(f"Response: {r_blend.text[:300]}")

print("\n=== STEP 4: CORS CHECK ===")
# Test OPTIONS preflight from frontend origin
origin = "https://frontend-two-tan-24.vercel.app"
r_cors = requests.options(
    f"{BACKEND}/api/blend",
    headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type",
    }
)
print(f"OPTIONS preflight status: {r_cors.status_code}")
print(f"Access-Control-Allow-Origin: {r_cors.headers.get('access-control-allow-origin')}")
print(f"Access-Control-Allow-Credentials: {r_cors.headers.get('access-control-allow-credentials')}")
print(f"Access-Control-Allow-Methods: {r_cors.headers.get('access-control-allow-methods')}")

# Direct GET with Origin header
r_get_cors = requests.get(
    f"{BACKEND}/api/blend?region_id=1&valid_time=2026-09-27T00:00:00Z&lead_time_hrs=24&variable=rainfall",
    headers={"Origin": origin}
)
print(f"GET with Origin status: {r_get_cors.status_code}")
print(f"Access-Control-Allow-Origin in GET: {r_get_cors.headers.get('access-control-allow-origin')}")
