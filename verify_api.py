import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("1. Health Check:")
r = client.get("/health")
print(r.status_code, r.json())
assert r.status_code == 200

print("\n2. List Personas:")
r = client.get("/api/auth/personas")
print(r.status_code, len(r.json()), "personas")
assert r.status_code == 200

print("\n3. List Cases:")
r = client.get("/api/cases")
cases = r.json()
print(r.status_code, len(cases), "cases loaded")
assert len(cases) > 0

sample_case_id = cases[0]["case_id"]
print(f"\n4. Investigate Case ({sample_case_id}):")
r = client.post(f"/api/cases/{sample_case_id}/investigate")
print(r.status_code, r.json().get("recommendation", {}).get("action_type"))
assert r.status_code == 200

print("\n5. Submit Approval (Daniel Osei):")
approval_payload = {
    "case_id": sample_case_id,
    "action": "APPROVE",
    "comments": "Verified against beneficiary standing instructions."
}
r = client.post(
    "/api/approvals/submit",
    json=approval_payload,
    headers={"Authorization": "Bearer pex-token-APR-3191"}
)
print(r.status_code, r.json())
assert r.status_code == 200

print("\n6. Execute Simulated Action:")
r = client.post("/api/actions/execute", json={"case_id": sample_case_id})
print(r.status_code, r.json())
assert r.status_code == 200

print("\n7. Verify SHA-256 Audit Chain:")
r = client.get("/api/governance/audit-chain/verify")
print(r.status_code, r.json())
assert r.json()["is_intact"] is True

print("\nAll Backend API Core Verification Tests Passed Successfully!")
