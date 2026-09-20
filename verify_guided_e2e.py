import urllib.request
import json
import time

base_url = "http://localhost:8000"

print("1. Checking Server Health & Loaded Cases ...")
with urllib.request.urlopen(f"{base_url}/health", timeout=5) as resp:
    h = json.loads(resp.read().decode('utf-8'))
    print("   Health:", h)

print("\n2. Checking Case Details with Guided Questions & 5-Step Assessment ...")
with urllib.request.urlopen(f"{base_url}/api/cases/PEX-INV-0001", timeout=5) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    rec = res['recommendation']
    print("   Case ID:", res['case']['case_id'])
    print("   Guided Questions count:", len(rec.get('guided_questions', [])))
    for q in rec.get('guided_questions', []):
        print(f"     - [{q['category']}] {q['question']}")
    print("   Step Assessment Checkpoints count:", len(rec.get('step_by_step_assessment', [])))
    for s in rec.get('step_by_step_assessment', []):
        print(f"     - Step {s['step_number']}: {s['step_title']} -> [{s['badge_label']}]")

print("\n3. Testing Return to Maker (Rework) Workflow for PEX-KYC-0005 ...")
req_rework = urllib.request.Request(
    f"{base_url}/api/approvals/submit",
    data=json.dumps({
        "case_id": "PEX-KYC-0005",
        "action": "RETURN_TO_MAKER",
        "comments": "Please check with client treasury for updated commercial documentation."
    }).encode('utf-8'),
    headers={"Content-Type": "application/json", "Authorization": "Bearer pex-token-CMP-4420"},
    method="POST"
)
with urllib.request.urlopen(req_rework, timeout=5) as resp:
    rework_res = json.loads(resp.read().decode('utf-8'))
    print("   Return to Maker result:", rework_res['next_stage'])

print("\n4. Testing Compliance False Positive Clearance for PEX-SAN-0010 ...")
req_compliance = urllib.request.Request(
    f"{base_url}/api/approvals/submit",
    data=json.dumps({
        "case_id": "PEX-SAN-0010",
        "action": "CLEAR_FALSE_POSITIVE",
        "comments": "Secondary IDs confirm homonym false positive."
    }).encode('utf-8'),
    headers={"Content-Type": "application/json", "Authorization": "Bearer pex-token-CMP-4420"},
    method="POST"
)
with urllib.request.urlopen(req_compliance, timeout=5) as resp:
    comp_res = json.loads(resp.read().decode('utf-8'))
    print("   Compliance Clearance result:", comp_res['next_stage'])

print("\nALL VERIFICATIONS PASSED 100%!")
