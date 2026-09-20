import urllib.request
import json
with urllib.request.urlopen("http://localhost:8000/api/cases", timeout=3) as r:
    data = json.loads(r.read().decode('utf-8'))
    print(f"Server is HEALTHY. Status: {r.status}, Total cases: {len(data)}")
