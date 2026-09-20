import urllib.request
import json
import time

time.sleep(1)
base_url = "http://localhost:8000"

print("1. Fetching /api/cases ...")
with urllib.request.urlopen(f"{base_url}/api/cases", timeout=5) as resp:
    cases = json.loads(resp.read().decode('utf-8'))
    print("   Total Cases returned from API:", len(cases))

print("\n2. Testing Marisol Vega HTTP Approval for PEX-KYC-0017 ...")
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

with urllib.request.urlopen(req, timeout=5) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    print("   HTTP Approval Response:", res)

print("\n3. Verifying updated case state ...")
with urllib.request.urlopen(f"{base_url}/api/cases/PEX-KYC-0017", timeout=5) as resp:
    detail = json.loads(resp.read().decode('utf-8'))
    print("   PEX-KYC-0017 New Status:", detail['case']['status'])
    print("   Approvals history count:", len(detail['approvals']))
    for a in detail['approvals']:
        print(f"     - Step {a['step_number']}: {a['approver_name']} ({a['approver_role']})")
