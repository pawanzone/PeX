import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from app.services.data_loader import repo

print("Total cases in repo:", len(repo.cases))
for cid, c in repo.cases.items():
    print(cid, "Status:", c["status"])
