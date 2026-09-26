import requests
import re

r = requests.get("https://frontend-two-tan-24.vercel.app")
print("HTML status:", r.status_code)
js_files = re.findall(r'src="([^"]+\.js)"', r.text)
print("JS files:", js_files)
for js in js_files:
    url = "https://frontend-two-tan-24.vercel.app" + js if js.startswith("/") else js
    r_js = requests.get(url)
    matches = set(re.findall(r'https?://[a-zA-Z0-9\.\-_:]+', r_js.text))
    api_matches = [m for m in matches if "railway" in m or "localhost" in m or "api" in m or "vercel" in m]
    print(f"URLs in {js}:", api_matches)
