import urllib.request
import json
import time

time.sleep(1)
base_url = "http://localhost:8000"

print("1. Checking Total Loaded Cases ...")
with urllib.request.urlopen(f"{base_url}/api/cases", timeout=5) as resp:
    cases = json.loads(resp.read().decode('utf-8'))
    print(f"   Total Cases: {len(cases)}")

print("\n2. Testing Marisol Vega (Compliance Approver) approving PEX-KYC-0017 ...")
req = urllib.request.Request(
    f"{base_url}/api/approvals/submit",
    data=json.dumps({
        "case_id": "PEX-KYC-0017",
        "action": "APPROVE",
        "comments": "Compliance Dual-Authorization signed off by Marisol Vega"
    }).encode('utf-8'),
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer pex-token-CMP-4420"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("   Approval Success:", res['success'], "| Message:", res['message'], "| Next Stage:", res['next_stage'])
except Exception as e:
    print("   Approval Error:", e)

print("\n3. Testing Marisol Vega (Compliance Approver) executing Level 2 Dual-Auth on PEX-DUP-0015 ...")
req2 = urllib.request.Request(
    f"{base_url}/api/approvals/submit",
    data=json.dumps({
        "case_id": "PEX-DUP-0015",
        "action": "APPROVE",
        "comments": "Tier 2 Dual Authorization signed off by Marisol Vega"
    }).encode('utf-8'),
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer pex-token-CMP-4420"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req2, timeout=5) as resp:
        res2 = json.loads(resp.read().decode('utf-8'))
        print("   Level 2 Dual-Auth Success:", res2['success'], "| Message:", res2['message'], "| Next Stage:", res2['next_stage'])
except Exception as e:
    print("   Dual-Auth Error:", e)
