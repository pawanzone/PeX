"""One-off: for every profile without a missing-evidence case, copy its first fixture and remove one mandatory evidence item."""
import json
from pathlib import Path
gold = json.loads(Path("tests/goldens/e2e_goldens.json").read_text())
packs = {json.loads(f.read_text())["code"]: json.loads(f.read_text()) for f in Path("backend/app/profile_packs/packs").glob("*.json")}
by = {}
for k, g in sorted(gold.items()):
    by.setdefault(g["detected_profile_id"], []).append((k, g))
made = []
for code, cs in sorted(by.items()):
    if code not in packs or packs[code]["outcome"] == "DECISION_SUPPORT" or any(g["evidence_status"] == "INSUFFICIENT" for _, g in cs):
        continue
    src = next(((k, g) for k, g in cs if k.startswith("input/")), None)
    if not src: continue
    raw = json.loads(Path("e2e_fixtures", src[0] + ".json").read_text())
    mand = [e["type"] for e in packs[code]["evidence"]["required"] if e.get("mandatory", True)]
    target = next((m for m in mand if any(m in (raw.get(b) or {}) or m.lower() in (raw.get(b) or {}) for b in ("bank_supplied_evidence", "external_authoritative_evidence", "derived_evidence"))), None)
    if not target: print("skip", code); continue
    for b in ("bank_supplied_evidence", "external_authoritative_evidence", "derived_evidence"):
        for key in list((raw.get(b) or {})):
            if key.upper() == target: raw[b].pop(key)
    raw["exception_id"] = raw["exception_id"] + "-MISSING-EVIDENCE"
    name = f"{code}_{packs[code]['name'].lower()}_missing_evidence"
    Path("e2e_fixtures/input", name + ".json").write_text(json.dumps(raw, indent=2) + "\n")
    made.append((code, target))
print(made)
