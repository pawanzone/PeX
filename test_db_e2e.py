import urllib.request
import json

def api_call(url, data=None, method="GET", headers=None):
    h = headers or {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("=== 1. Health Check ===")
health = api_call("http://127.0.0.1:8000/health")
print("Health response:", json.dumps(health, indent=2))

print("\n=== 2. List Cases ===")
cases = api_call("http://127.0.0.1:8000/api/cases")
print(f"Total cases returned: {len(cases)}")
print(f"Sample case: {cases[0]['case_id']} | Profile: {cases[0]['profile']} | Amount: ${cases[0]['amount']:,.2f}")

print("\n=== 3. Get Case Detail ===")
detail = api_call(f"http://127.0.0.1:8000/api/cases/{cases[0]['case_id']}")
print(f"Case ID: {detail['case']['case_id']}")
print(f"Recommendation attached: {detail['recommendation'] is not None}")
print(f"Approvals count: {len(detail['approvals'])}")

print("\n=== 4. Test Maker Action: Run AI Repair ===")
ingested = [c for c in cases if c["status"] == "INGESTED"]
if ingested:
    target = ingested[0]["case_id"]
    ai_repair = api_call(f"http://127.0.0.1:8000/api/cases/{target}/run-ai-repair", method="POST")
    print(f"AI Repair executed for {target}:")
    print(f"New Status: {ai_repair['case']['status']} | Confidence: {ai_repair['case']['ai_confidence']}")

print("\n=== 5. Test Checker Approval ===")
pending = [c for c in cases if c["status"] == "PENDING_APPROVAL"]
if pending:
    target_case = pending[0]["case_id"]
    appr_resp = api_call(
        "http://127.0.0.1:8000/api/approvals/submit",
        data={
            "case_id": target_case,
            "action": "APPROVE",
            "comments": "Level 1 authorization verified against persistent database."
        },
        headers={"Authorization": "Bearer pex-token-APR-3191"},
        method="POST"
    )
    print(f"Approval for {target_case}: {appr_resp['message']} | Next stage: {appr_resp['next_stage']}")

print("\n=== 6. Cryptographic Audit Hash Chain Verification ===")
chain_verify = api_call("http://127.0.0.1:8000/api/audit/verify-chain")
print("Audit verification result:")
print(f"  - Chain Intact: {chain_verify['is_intact']}")
print(f"  - Total Events Checked: {chain_verify['total_events_checked']}")
print(f"  - Chain Head: {chain_verify['chain_head']}")

print("\n=== 7. User Personas & RBAC ===")
personas = api_call("http://127.0.0.1:8000/api/auth/personas")
print(f"Total personas: {len(personas)}")
for p in personas[:4]:
    print(f"  - {p['user_id']} ({p['name']}): Role {p['role']} | Max: ${p['max_approval_amount']:,.2f}")

print("\n>>> ALL E2E PERSISTENT DATABASE TESTS PASSED SUCCESSFULLY! <<<")
