import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from app.services.data_loader import repo

for cid, c in repo.cases.items():
    if "0017" in cid or "KYC" in cid or "SAN" in cid:
        print(cid, "| Queue:", c["queue"], "| Amount:", c["amount"], "| Status:", c["status"])
