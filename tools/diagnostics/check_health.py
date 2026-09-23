import urllib.request
import json
with urllib.request.urlopen("http://localhost:8000/health", timeout=3) as resp:
    print("Server Health:", json.loads(resp.read().decode('utf-8')))
