import os, re, sys, importlib.util
from pathlib import Path

os.environ.setdefault("CLOUDFLARE_API_KEY", "dummy")
os.environ.setdefault("CLOUDFLARE_ACCOUNT_ID", "dummy")
os.environ.setdefault("WEATHER_API_KEY", "dummy")

spec = importlib.util.spec_from_file_location(
    "m", Path(__file__).parent / "backend" / "main.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

routes = sorted(getattr(r, "path", "") for r in m.app.routes)
print("ROUTES:", routes)
assert "/api/weather" in routes and "/api/chat" in routes and "/" in routes

def allowed(o):
    return o in m.allow_origins or re.match(m.allow_origin_regex, o)

checks = {
    "http://localhost:5173": True,
    "http://localhost:4173": True,
    "capacitor://localhost": True,
    "https://weathergpt.pages.dev": True,
    "https://abc123.weathergpt.pages.dev": True,
    "https://x.workers.dev": True,
    "https://weathergpt-backend-2udp.onrender.com": True,
    "https://evil.example.com": False,
    "http://localhost:9999": False,
}
for o, exp in checks.items():
    got = bool(allowed(o))
    print("CORS", "OK" if got == exp else "FAIL", o, got)
    assert got == exp, o

print("ALL_BACKEND_CHECKS_PASSED")