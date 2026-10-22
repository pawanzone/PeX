import sys, json
sys.path.insert(0, "backend")
from app.profile_packs import registry
from app.services.e2e_runner import E2EExecutionHarness
h = E2EExecutionHarness()
rows = {}
for code, pk in sorted(registry.load_packs().items()):
    r = h.dynamic_config_resolver.resolve_requirements("DEFAULT_BANK", code, {})
    rt = [(t, r.min_trust_tiers[t].value if hasattr(r.min_trust_tiers[t],'value') else str(r.min_trust_tiers[t])) for t in r.active_mandatory_types]
    pkv = [(e.type, e.tier) for e in pk.evidence.required]
    rows[code] = {"runtime": rt, "pack": pkv, "ver": r.config_version}
    flag = "OK " if [t for t,_ in rt] == [t for t,_ in pkv] else "DIFF"
    print(flag, code, r.config_version, "\n   rt:", rt, "\n   pk:", pkv)
json.dump(rows, open("/tmp/ev_dump.json","w"), indent=1)
