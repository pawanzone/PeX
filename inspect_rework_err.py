import urllib.request
import urllib.error
import json

base_url = "http://localhost:8000"

req_rework = urllib.request.Request(
    f"{base_url}/api/approvals/submit",
    data=json.dumps({
        "case_id": "PEX-INV-0005",
        "action": "RETURN_TO_MAKER",
        "comments": "Please check with client treasury for updated commercial invoice."
    }).encode('utf-8'),
    headers={"Content-Type": "application/json", "Authorization": "Bearer pex-token-APR-3191"},
    method="POST"
)

try:
    with urllib.request.urlopen(req_rework, timeout=5) as resp:
        print("Success:", resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
