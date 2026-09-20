import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from app.services.data_loader import repo

print(f"Total live cases in repo: {len(repo.cases)}")
for cid, c in repo.cases.items():
    print(f"Case: {cid} | Amount: ${c['amount']:,.2f} | Status: {c['status']} | Queue: {c['queue']} | Profile: {c['profile']}")
