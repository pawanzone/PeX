"""Profile and control library (Admin, read only): every profile, its evidence contract, rules and decision options, plus the STP
predicates and controls, generated from the packs and a readable definitions file so nothing is typed twice.

  L1  The 8 STP predicates in the definitions file are exactly the engine's predicates; settings named for P_bank exist in STPPolicyConfig.
  L2  Every control names a file that exists, a valid applies_to rule and whether a bank can configure it.
  L3  Every term a pack uses (family, outcome, STP rule, approval path, authority domain, effect, tier) has a definition.
  L4  The library lists all 41 profiles with the fields a buyer reviews.
  L5  Each profile's detail equals its pack and explains every term; the evidence rows carry meaning and source from the semantic layer.
  L6  Control coverage is computed from the packs, not typed: counts and profile lists match.
  L7  Defaults shown for the bank-configurable inputs equal the code's defaults; the two STP limits in code are both shown.
  L8  Access follows the other reference pages; an unknown profile is a 404.
"""
import json
from pathlib import Path

import pytest

from app.core.auth import create_token
from app.profile_packs import registry
from app.schemas.policy_contract import STPEligibilityDecision, STPPolicyConfig

APP = Path(registry.__file__).resolve().parents[1]  # backend/app
DEFS = json.loads((APP / "profile_packs" / "definitions" / "controls.json").read_text(encoding="utf-8"))
PACKS = {c: registry.get_pack(c) for c in sorted(registry.load_packs())}


def H(uid="ADM-0002"):
    return {"Authorization": "Bearer " + create_token(uid)}


def get(client, path, uid="ADM-0002"):
    return client.get("/api/v2/reference/" + path, headers=H(uid))


def test_l1_predicates_match_the_engine():
    P = DEFS["stp_predicates"]
    assert [p["code"] for p in P] == ["E_suff", "R_det", "R_uniq", "V_det", "V_auth", "P_bank", "C_comp", "X_pre"]
    fields = set(STPEligibilityDecision.model_fields)
    for p in P:
        assert p["engine_field"] in fields, p["code"]
        assert p["meaning"] and p["fed_by"] and (APP.parent / p["enforced_in"]).exists(), p["code"]
        assert p["configurable"] in ("fixed", "bank-configurable")
    pb = next(p for p in P if p["code"] == "P_bank")
    assert pb["configurable"] == "bank-configurable" and set(pb["bank_settings"]) <= set(STPPolicyConfig.model_fields) and pb["bank_settings"]
    assert all(p["configurable"] == "fixed" for p in P if p["code"] != "P_bank")


def test_l2_controls_are_well_formed():
    ids = [c["id"] for c in DEFS["controls"]]
    assert len(ids) == len(set(ids)) >= 15
    for c in DEFS["controls"]:
        assert c["name"] and c["meaning"] and c["kind"], c["id"]
        assert (APP.parent / c["enforced_in"]).exists(), (c["id"], c["enforced_in"])
        assert c["configurable"] in ("fixed", "bank-configurable") and c["applies_to"] in ("all", "repair", "decision"), c["id"]


def test_l3_every_pack_term_is_defined():
    for code, p in PACKS.items():
        assert code.split("-")[0] in DEFS["families"], code
        assert p.outcome.value in DEFS["outcomes"] and p.stp.value in DEFS["stp_rules"], code
        assert p.approval.when_not_stp in DEFS["approval_paths"] and p.authority_domain in DEFS["authority_domains"], code
        for e in p.evidence.required:
            assert str(e.tier) in DEFS["evidence_tiers"], code
        if p.decision:
            assert {v.value for v in p.decision.effects.values()} <= set(DEFS["effects"]), code


def test_l4_library_lists_every_profile(client):
    d = get(client, "library").json()
    assert len(d["profiles"]) == 41 == len(PACKS) and d["summary"]["profiles"] == 41
    assert d["summary"]["by_outcome"]["REPAIR"] == 31 and d["summary"]["by_stp"]["NEVER"] == 10
    for r in d["profiles"]:
        p = PACKS[r["code"]]
        assert (r["name"], r["family"], r["outcome"], r["stp"], r["approval"], r["authority_domain"]) == (p.name, p.code.split("-")[0], p.outcome.value, p.stp.value, p.approval.when_not_stp, p.authority_domain)
        assert r["evidence_mandatory"] == len(p.evidence.mandatory_types) and r["evidence_total"] == len(p.evidence.required)
        assert r["validation_status"] == "Bank SME to validate against their process" and r["family_name"] and r["family_name"] == DEFS["families"][r["family"]]
        assert r["decision_options"] == (len(p.decision.options) if p.decision else 0)


@pytest.mark.parametrize("code", sorted(PACKS))
def test_l5_detail_equals_the_pack_and_explains_every_term(client, code):
    p = PACKS[code]
    d = get(client, f"library/{code}").json()
    assert d["code"] == code and d["version"] == p.version and d["action"] == p.action and d["resolver"] == p.resolver and d["checks"] == p.checks
    assert [(e["type"], e["tier"], e["mandatory"]) for e in d["evidence"]] == [(e.type, e.tier, e.mandatory) for e in p.evidence.required]
    for e in d["evidence"]:
        assert e["proves"] and e["source_system"] and e["tier_meaning"], (code, e["type"])
    assert d["stp_meaning"] == DEFS["stp_rules"][p.stp.value] and d["approval_meaning"] == DEFS["approval_paths"][p.approval.when_not_stp]
    assert d["authority_meaning"] == DEFS["authority_domains"][p.authority_domain] and d["outcome_meaning"] == DEFS["outcomes"][p.outcome.value]
    if p.decision:
        assert d["decision"]["reviewer_role"] == p.decision.reviewer_role and d["decision"]["target_field"] == p.decision.target_field
        assert [(o["option"], o["effect"]) for o in d["decision"]["options"]] == [(o, p.decision.effects[o].value) for o in p.decision.options]
        assert all(o["effect_meaning"] for o in d["decision"]["options"])
    else:
        assert d["decision"] is None
    assert d["validation_status"] == "Bank SME to validate against their process"
    ctl = {c["id"] for c in DEFS["controls"]}
    assert d["controls"] and {c["id"] for c in d["controls"]} <= ctl
    assert ("CTL-07" in {c["id"] for c in d["controls"]}) == bool(p.decision)
    assert ("CTL-01" in {c["id"] for c in d["controls"]}) == (p.outcome.value == "REPAIR")


def test_l6_control_coverage_is_computed_from_the_packs(client):
    d = get(client, "controls").json()
    c = {x["id"]: x for x in d["controls"]}
    assert set(c) == {x["id"] for x in DEFS["controls"]}
    assert set(c["CTL-07"]["profiles"]) == {k for k, p in PACKS.items() if p.decision}
    assert set(c["CTL-01"]["profiles"]) == {k for k, p in PACKS.items() if p.outcome.value == "REPAIR"}
    assert set(c["CTL-03"]["profiles"]) == set(PACKS) and c["CTL-03"]["breakdown"] == {"ALLOWED": 29, "POLICY_GATED": 2, "NEVER": 10}
    assert c["CTL-09"]["breakdown"] == {"MAKER_CHECKER": 32, "COMPLIANCE_THEN_RISK": 6, "SINGLE": 3}
    assert all(set(x["profiles"]) <= set(PACKS) for x in c.values())
    pr = {x["code"]: x for x in d["stp_predicates"]}
    assert list(pr) == ["E_suff", "R_det", "R_uniq", "V_det", "V_auth", "P_bank", "C_comp", "X_pre"]
    assert pr["P_bank"]["profiles"] == sorted(k for k, p in PACKS.items() if p.stp.value != "NEVER")


def test_l7_defaults_come_from_the_code(client):
    d = get(client, "controls").json()
    cfg = STPPolicyConfig()
    s = {x["key"]: x for x in d["bank_settings"]}
    assert s["max_stp_amount"]["default"] == cfg.max_stp_amount and s["dual_auth_threshold"]["default"] == cfg.dual_auth_threshold
    assert s["allowed_corridors"]["default"] == cfg.allowed_corridors and s["auto_stp_enabled"]["default"] == cfg.auto_stp_enabled
    from app.config import settings
    assert s["zero_touch_limit"]["default"] == float(settings.STP_MAX_AMOUNT)
    assert any("two different" in x["note"].lower() or "differ" in x["note"].lower() for x in d["bank_settings"] if x["key"] in ("max_stp_amount", "zero_touch_limit"))


def test_l8_access_follows_the_reference_pages_and_unknown_profile_is_404(client):
    from test_reference import ALLOWED, DENIED  # same people as the other reference pages
    for uid in ALLOWED:
        assert get(client, "library", uid).status_code == 200 and get(client, "controls", uid).status_code == 200
    for uid in DENIED:
        assert get(client, "library", uid).status_code == 403 and get(client, "controls", uid).status_code == 403 and get(client, "library/DQ-01", uid).status_code == 403
    assert get(client, "library/DQ-99").status_code == 404
    for verb in (client.post, client.put, client.delete):
        assert verb("/api/v2/reference/library", headers=H()).status_code in (404, 405)


def test_l9_bank_settings_show_the_value_in_force_and_the_release_mode(client):
    from app.services.v2 import policy
    d = get(client, "controls").json()
    s = {x["key"]: x for x in d["bank_settings"]}
    assert s["release_mode"]["value"] == "APPROVE_ALL" and s["release_mode"]["default"] == "APPROVE_ALL" and s["release_mode"]["source"].startswith("Bank policy")
    assert s["zero_touch_limit"]["value"] == policy.get("zero_touch_limit") and s["batch_limit"]["value"] == policy.get("batch_limit")
    assert "no trigger" in s["zero_touch_limit"]["note"].lower()          # honest: nothing releases on its own yet
    assert all("value" in x for x in d["bank_settings"])


def test_l10_a_changed_mode_shows_in_the_library(client):
    from app.services.v2 import policy
    from app.services.v2 import seed as v2seed
    v2seed.seed_v2()
    policy.reset_all()
    try:
        c = client.post("/api/v2/policy/changes", json={"key": "release_mode", "value": "REVIEW_EACH", "reason": "pilot"}, headers=H("POL-8001")).json()
        client.post(f"/api/v2/policy/changes/{c['id']}/approve", json={"note": "ok"}, headers=H("POL-8002"))
        s = {x["key"]: x for x in get(client, "controls").json()["bank_settings"]}
        assert s["release_mode"]["value"] == "REVIEW_EACH" and s["release_mode"]["default"] == "APPROVE_ALL"
    finally:
        policy.reset_all()
