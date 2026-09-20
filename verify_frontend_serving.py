import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test root serving
r = client.get("/")
print("Root status:", r.status_code, "Content length:", len(r.text))
assert r.status_code == 200
assert "PeX Enterprise Platform" in r.text

print("Frontend serving verification test PASSED!")
