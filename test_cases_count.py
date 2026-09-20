import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from app.services.data_loader import repo

print("Loaded cases count:", len(repo.cases))
print("list_cases count:", len(repo.list_cases()))
for c in repo.list_cases()[:5]:
    print(c["case_id"], c["profile"], c["status"], c["amount"])
