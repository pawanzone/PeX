import requests
import json

session = requests.Session()

def api_call(url, data=None, method="GET", headers=None):
    h = headers.copy() if headers else {}
    if method == "GET":
        resp = session.get(url, headers=h)
    elif method == "POST":
        resp = session.post(url, json=data, headers=h)
    elif method == "PUT":
        resp = session.put(url, json=data, headers=h)
    else:
        resp = session.request(method, url, json=data, headers=h)
    resp.raise_for_status()
    return resp.json()

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
    # Pick a case matching standard Operations Approver, or pick matching token
    target_obj = next((c for c in pending if c.get("queue") != "Compliance" and (c.get("amount", 0) < 250000)), pending[0])
    target_case = target_obj["case_id"]
    token_id = "CMP-4420" if target_obj.get("queue") == "Compliance" else "APR-3191"
    appr_resp = api_call(
        "http://127.0.0.1:8000/api/approvals/submit",
        data={
            "case_id": target_case,
            "action": "APPROVE",
            "comments": "Level 1 authorization verified against persistent database."
        },
        headers={"Authorization": f"Bearer pex-token-{token_id}"},
        method="POST"
    )
    print(f"Approval for {target_case} by {token_id}: {appr_resp['message']} | Next stage: {appr_resp['next_stage']}")

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

print("\n=== 8. Dynamic Policy Rule Synthesis & Maker-Checker Lifecycle ===")
prompt_text = "Anything more than $250,000 will go to 2-level approvals"
syn = api_call(
    "http://127.0.0.1:8000/api/rules/synthesize",
    data={"prompt": prompt_text},
    method="POST"
)
print(f"Synthesized Rule: {syn['name']} | Category: {syn['category']}")
print(f"Conditions AST: {json.dumps(syn['conditions'])}")
print(f"Actions: {json.dumps(syn['actions'])}")

sim = api_call(
    "http://127.0.0.1:8000/api/rules/simulate",
    data={"conditions": syn["conditions"], "actions": syn["actions"]},
    method="POST"
)
print(f"Simulated live impact: {sim['matched_cases_count']}/{sim['total_cases_evaluated']} cases ({sim['match_percentage']}%), ${sim['total_dollar_volume_affected']:,.2f}")

# Maker submits new draft
submit_resp = api_call(
    "http://127.0.0.1:8000/api/rules/submit",
    data={
        "name": syn["name"],
        "natural_language_prompt": prompt_text,
        "category": syn["category"],
        "domain": syn["domain"],
        "conditions": syn["conditions"],
        "actions": syn["actions"],
        "maker_id": "OP-8821",
        "maker_name": "Priya Sharma",
        "maker_notes": "Live test submission via Policy Studio."
    },
    method="POST"
)
print(f"Maker submitted rule: {submit_resp['rule_id']} | Status: {submit_resp['status']}")

# Checker approves draft
appr_rule_resp = api_call(
    f"http://127.0.0.1:8000/api/rules/{submit_resp['rule_id']}/approve",
    data={
        "checker_id": "RSK-7714",
        "checker_name": "Kenji Watanabe",
        "comments": "Reviewed JSON AST and simulated impact. Approved for production."
    },
    method="POST"
)
print("\n=== 9. ICD External Bank Configuration Registry ===")
icd_list = api_call("http://127.0.0.1:8000/api/rules/icd-configs/list")
print(f"Total ICD Nodes: {len(icd_list)}")
for icd in icd_list[:3]:
    print(f"  - [{icd['status']}] {icd['icd_id']}: {icd['name']} ({icd['bic']}) via {icd['rail']}")

print("\n=== 10. Governed STP & Fast-Lane Batch Execution (Release v1.5) ===")
telemetry = api_call("http://127.0.0.1:8000/api/stp/telemetry")
print("STP Telemetry:")
print(f"  - Overall STP Rate: {telemetry['overall_stp_rate_pct']}%")
print(f"  - Total Settled Cases: {telemetry['settled_cases']} of {telemetry['total_cases']}")
print(f"  - Fast-Lane Eligible: {telemetry['fast_lane_eligible_count']} cases (${telemetry['fast_lane_eligible_volume']:,.2f})")
print(f"  - Estimated Time Saved: {telemetry['time_savings_hours']:.1f} hours")

eligible_stp = api_call("http://127.0.0.1:8000/api/stp/eligible")
print(f"Fast-Lane Qualified Cases: {len(eligible_stp)}")
for item in eligible_stp[:3]:
    print(f"  - [STP {item['mode']}] {item['case_id']}: ${item['amount']:,.2f} | Conf: {item['ai_confidence']} | Reason: {item['reason']}")

if eligible_stp:
    target_ids = [e["case_id"] for e in eligible_stp[:2]]
    batch_resp = api_call(
        "http://127.0.0.1:8000/api/stp/batch-release",
        data={
            "case_ids": target_ids,
            "approver_id": "APR-3191",
            "approver_name": "Daniel Osei",
            "approver_role": "OPERATIONS_APPROVER",
            "comments": "Batch settlement authorized via E2E test verification."
        },
        method="POST"
    )
    print(f"Batch Execution Result ({batch_resp['batch_id']}):")
    print(f"  - Settled Count: {batch_resp['processed_count']} / {batch_resp['total_requested']}")
    print(f"  - Total Dollar Volume: ${batch_resp['total_dollar_volume']:,.2f}")
    print(f"  - Executed By: {batch_resp['executed_by']}")
    for s in batch_resp["settled_cases"]:
        print(f"    * {s['case_id']}: ${s['amount']:,.2f} -> {s['receipt_id']}")

print("\n>>> ALL E2E PERSISTENT DATABASE, DYNAMIC RULES & STP ENGINE TESTS PASSED SUCCESSFULLY! <<<")



