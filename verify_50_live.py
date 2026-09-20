import urllib.request
import json
import time

time.sleep(1)
base_url = "http://localhost:8000"

with urllib.request.urlopen(f"{base_url}/api/cases", timeout=5) as resp:
    cases = json.loads(resp.read().decode('utf-8'))
    print("=== LIVE PROBE STATUS: 200 OK ===")
    print("Total Cases loaded in Live API:", len(cases))
    
    profiles = {}
    statuses = {}
    for c in cases:
        p = str(c.get("profile"))
        s = str(c.get("status"))
        profiles[p] = profiles.get(p, 0) + 1
        statuses[s] = statuses.get(s, 0) + 1
    
    print("\n--- 6 Exception Types Breakdown (Total 50) ---")
    for p, count in sorted(profiles.items()):
        print(f"  • {p}: {count} cases")
        
    print("\n--- Approval Lifecycle Stages Breakdown ---")
    for s, count in sorted(statuses.items()):
        print(f"  • {s}: {count} cases")
