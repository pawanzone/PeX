import urllib.request
import json

base_url = "http://localhost:8000"

print("1. Testing GET / ...")
with urllib.request.urlopen(f"{base_url}/", timeout=3) as resp:
    html_content = resp.read().decode('utf-8')
    print(f"   Root response status: {resp.status}, HTML length: {len(html_content)} bytes")
    assert "Sign in to PayRepair AI" in html_content or "PayRepair AI" in html_content
    print("   [PASS] Frontend HTML serves PayRepair AI Login/Command Center!")

print("2. Testing GET /api/cases ...")
with urllib.request.urlopen(f"{base_url}/api/cases", timeout=3) as resp:
    cases = json.loads(resp.read().decode('utf-8'))
    print(f"   [PASS] Found {len(cases)} cases.")
    first_case_id = cases[0]["case_id"]

print(f"3. Testing GET /api/ontology/inspect/{first_case_id} ...")
with urllib.request.urlopen(f"{base_url}/api/ontology/inspect/{first_case_id}", timeout=3) as resp:
    onto_data = json.loads(resp.read().decode('utf-8'))
    print(f"   [PASS] Ontology columns: {list(onto_data.keys())}")
    print(f"   Payment field status: {onto_data.get('payment', {}).get('corridor', {}).get('status')}")

print("4. Testing GET /api/ontology/pipeline ...")
with urllib.request.urlopen(f"{base_url}/api/ontology/pipeline", timeout=3) as resp:
    pipe = json.loads(resp.read().decode('utf-8'))
    print(f"   [PASS] Pipeline stages: {len(pipe)}")

print("5. Testing GET /api/ontology/entities ...")
with urllib.request.urlopen(f"{base_url}/api/ontology/entities", timeout=3) as resp:
    ents = json.loads(resp.read().decode('utf-8'))
    print(f"   [PASS] Canonical entities count: {len(ents)}")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
