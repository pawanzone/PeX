"""One-off: copy each older profile's real runtime evidence (published reference config) into its pack."""
import json, glob, sys
sys.path.insert(0, "backend")
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
ad = InMemoryConfigurationAdapter()
n_new = n_old = 0
for f in sorted(glob.glob("backend/app/profile_packs/packs/*.json")):
    d = json.load(open(f))
    ev = d.get("evidence", {})
    ev.pop("mandatory", None)
    if not ev.get("required"):
        cfg = ad.get_evidence_config("DEFAULT_BANK", d["code"])
        assert cfg is not None, d["code"]
        assert all(r.condition_expression is None for r in cfg.rules), d["code"]
        ev["required"] = [{"type": r.evidence_type, "tier": int(r.min_trust_tier.value), **({} if r.mandatory else {"mandatory": False})} for r in cfg.rules]
        n_old += 1
    else:
        n_new += 1
    d["evidence"] = ev
    json.dump(d, open(f, "w"), indent=2); open(f, "a").write("\n")
print("migrated", n_old, "kept", n_new)
