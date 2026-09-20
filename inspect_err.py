import urllib.request
import urllib.error
import json

base_url = "http://localhost:8000"

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
        print("Success:", resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
