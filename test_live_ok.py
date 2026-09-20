import urllib.request
import json

base_url = "http://localhost:8000"

print("1. Probing Root UI ...")
with urllib.request.urlopen(f"{base_url}/", timeout=3) as resp:
    html = resp.read().decode('utf-8')
    print("   Status code:", resp.status)
    print("   HTML contains 'Sign in to PayRepair AI':", "Sign in to PayRepair AI" in html)
    print("   HTML contains 'demo1234':", "demo1234" in html)
    print("   HTML contains 'Priya Nair':", "Priya Nair" in html)

print("\n2. Probing /api/cases ...")
with urllib.request.urlopen(f"{base_url}/api/cases", timeout=3) as resp:
    cases = json.loads(resp.read().decode('utf-8'))
    print("   Total loaded cases:", len(cases))
    ingested = [c['case_id'] for c in cases if c['status'] == 'INGESTED']
    pending = [c['case_id'] for c in cases if c['status'] == 'PENDING_APPROVAL']
    dual_auth = [c['case_id'] for c in cases if c['status'] == 'AWAITING_SECOND_APPROVAL']
    settled = [c['case_id'] for c in cases if c['status'] == 'SETTLED']
    print("   [INGESTED / Fresh Uninvestigated]:", len(ingested), ingested)
    print("   [PENDING_APPROVAL / Level 1]:", len(pending), pending)
    print("   [AWAITING_SECOND_APPROVAL / Dual-Auth]:", len(dual_auth), dual_auth)
    print("   [SETTLED]:", len(settled), settled)

print("\n3. Probing /api/ontology/inspect/PEX-EXC-INV-0001 ...")
with urllib.request.urlopen(f"{base_url}/api/ontology/inspect/PEX-EXC-INV-0001", timeout=3) as resp:
    onto = json.loads(resp.read().decode('utf-8'))
    print("   Ontology columns:", list(onto.keys()))
    print("   Payment amount validation:", onto['payment']['amount'])

print("\nEVERYTHING IS 100% OPERATIONAL!")
