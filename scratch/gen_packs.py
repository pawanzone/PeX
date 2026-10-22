"""One-off generator: lifts each inline resolution branch of e2e_runner into a resolver function (verbatim body)
and writes a pack per profile. Output is committed; this script is kept for reproducibility only."""
import ast, json, os, sys, textwrap
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/gen.db")
from app.services.file_watcher import PROFILE_CODE_TO_ENUM
from app.services.profile_engine import PROFILE_SPECS

RUNNER = ROOT / "backend/app/services/e2e_runner.py"
lines = RUNNER.read_text(encoding="utf-8").splitlines()
tree = ast.parse("\n".join(lines))
branches = {}
for node in ast.walk(tree):
    if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "profile" and isinstance(node.test.comparators[0], ast.Constant)):
        branches[node.test.comparators[0].value] = node
gold = json.loads((ROOT / "tests/goldens/e2e_goldens.json").read_text(encoding="utf-8"))
ENGINES = {"account_master_engine", "routing_clearing_engine", "remittance_document_engine",
           "settlement_reconciliation_engine", "compliance_dossier_engine", "treasury_exposure_engine",
           "wave4_resolution_engine"}
FAMILY_MODULE = {"DQ": "dq", "PR": "pr", "CO": "co", "TR": "tr", "ST": "st"}
NAME_OVERRIDE = {"DQ-03": "dq03_missing_beneficiary"}
Q = {"ACCOUNT_OWNERSHIP_BALANCE": ["ST-02", "ST-03", "TR-01", "TR-02", "TR-03", "TR-05", "TR-06", "TR-08"],
     "QUEUE_PROCESSING_STATE": ["PR-08", "PR-07", "PR-09", "TR-07"]}


def authority(code):
    if "DQ" in code or code in Q["ACCOUNT_OWNERSHIP_BALANCE"]:
        return "ACCOUNT_OWNERSHIP_BALANCE"
    if code in Q["QUEUE_PROCESSING_STATE"]:
        return "QUEUE_PROCESSING_STATE"
    if "CO" in code:
        return "LEGAL_PROHIBITION"
    return "CLEARING_SETTLEMENT_STATUS"


def resolver_name(code):
    return NAME_OVERRIDE.get(code) or f"{code.lower().replace('-', '')}_{PROFILE_CODE_TO_ENUM[code].name.lower()}"


mods = {k: [] for k in FAMILY_MODULE.values()}
packs = {}
for code, node in sorted(branches.items()):
    body = lines[node.body[0].lineno - 1: node.body[-1].end_lineno]
    body = textwrap.indent(textwrap.dedent("\n".join(body)), "    ")
    names = {n.id for st in node.body for n in ast.walk(st) if isinstance(n, ast.Name)}
    imports = []
    eng = sorted(names & ENGINES)
    if eng:
        imports.append(f"    from app.services.engines import {', '.join(eng)}")
    if "resolve_dq05" in names:
        imports.append("    from app.services.eur_rail_overlay import resolve_dq05")
    if "datetime" in names or "timezone" in names:
        imports.append("    from datetime import datetime, timezone")
    pre = ["    pmt, evidence_ctx, envelope, profile = ctx.pmt, ctx.evidence, ctx.envelope, ctx.profile"]
    if "active_policy" in names:
        pre.append("    active_policy = ctx.policy")
    pre += ["    r_det = False", "    r_uniq = False", "    v_det = False", "    resolution_rec = None",
            "    repaired_fields = []", "    resolution_basis = \"\""]
    name = resolver_name(code)
    fn = (f"@register_resolver(\"{name}\")\ndef {name}(ctx: ResolutionContext) -> ResolutionResult:\n"
          f"    \"\"\"{code} {PROFILE_CODE_TO_ENUM[code].name} (lifted verbatim from the e2e_runner branch).\"\"\"\n"
          + "\n".join(imports + pre) + "\n" + body + "\n"
          "    return ResolutionResult(determined=bool(r_det), unique=bool(r_uniq), validated=bool(v_det),\n"
          "                            repaired_fields=repaired_fields, recommendation=resolution_rec, basis=resolution_basis)\n")
    mods[FAMILY_MODULE[code[:2]]].append(fn)
    enum = PROFILE_CODE_TO_ENUM[code]
    spec = PROFILE_SPECS[enum]
    stp_seen = any(v.get("stp_eligible") is True for k, v in gold.items()
                   if k.split("/")[-1].split("_")[0].upper() == code)
    never = code == "TR-08"
    packs[code] = {
        "code": code, "name": enum.name, "family": spec["domain"].name, "version": 1,
        "outcome": "DECISION_SUPPORT" if never else "REPAIR",
        "stp": "NEVER" if never else ("ALLOWED" if stp_seen else "POLICY_GATED"),
        "evidence": {"mandatory": spec["mandatory_evidence"], "min_confidence": spec["min_confidence"]},
        "checks": [], "resolver": name, "authority_domain": authority(code),
        "action": "REPAIR_AND_RELEASE", "approval": {"when_not_stp": "MAKER_CHECKER"},
    }

pp = ROOT / "backend/app/profile_packs"
(pp / "resolvers").mkdir(exist_ok=True)
old = pp / "resolvers.py"
if old.exists():
    old.rename(pp / "resolvers_old_moved.tmp")
HEAD = ('"""{fam} resolvers: pure functions lifted verbatim from the e2e_runner branches (behaviour unchanged;\n'
        'the golden tests prove it). Generated once by scratch/gen_packs.py, maintained by hand from now on."""\n'
        "from app.profile_packs.registry import register_resolver\n"
        "from app.profile_packs.schema import ResolutionContext, ResolutionResult\n\n\n")
FAM = {"dq": "Data quality", "pr": "Processing", "co": "Compliance", "tr": "Treasury and client", "st": "Settlement and returns"}
for m, fns in mods.items():
    (pp / "resolvers" / f"{m}.py").write_text(HEAD.format(fam=FAM[m]) + "\n\n".join(fns), encoding="utf-8")
(pp / "resolvers" / "__init__.py").write_text('"""Importing the package registers every resolver."""\nfrom app.profile_packs.resolvers import dq, pr, co, tr, st  # noqa: F401\n', encoding="utf-8")
for code, pk in packs.items():
    (pp / "packs" / f"{code}.json").write_text(json.dumps(pk, indent=2) + "\n", encoding="utf-8")
print(len(packs), "packs;", {m: len(f) for m, f in mods.items()})
