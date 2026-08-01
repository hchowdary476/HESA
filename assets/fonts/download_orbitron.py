"""Download Orbitron font files for JARVIS QML."""
import urllib.request
import os

os.makedirs("assets/fonts", exist_ok=True)

# jsDelivr CDN hosts npm @fontsource packages including TTF files
base = "https://cdn.jsdelivr.net/npm/@fontsource/orbitron@5.0.3/files/"
files = [
    ("orbitron-latin-400-normal.woff2", "orbitron-latin-400-normal.woff2"),
    ("orbitron-latin-700-normal.woff2", "orbitron-latin-700-normal.woff2"),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

for remote, local in files:
    url = base + remote
    out = os.path.join("assets/fonts", local)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        with open(out, "wb") as f:
            f.write(data)
        print(f"OK: {local} ({len(data)} bytes)")
    except Exception as e:
        print(f"FAIL: {local} -> {e}")
