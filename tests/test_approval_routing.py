"""The pack decides who must authorise a case that is not straight-through (the amount rule only ever tightens it)."""
import pytest

from app.profile_packs import registry

EXPECT = {"MAKER_CHECKER": "MAKER_CHECKER_DUAL_AUTH", "SINGLE": "SINGLE_APPROVER",
          "COMPLIANCE_THEN_RISK": "COMPLIANCE_THEN_RISK_SIGN_OFF"}
CODES = sorted(registry.load_packs())


@pytest.mark.parametrize("code", CODES)
def test_requirement_follows_the_pack(code):
    assert registry.approval_requirement_for(code, stp_eligible=False) == EXPECT[registry.get_pack(code).approval.when_not_stp]


@pytest.mark.parametrize("code", CODES)
def test_straight_through_needs_no_approval(code):
    assert registry.approval_requirement_for(code, stp_eligible=True) == "NONE_AUTONOMOUS_STP"


def test_unknown_profile_and_unknown_value_fail_closed(monkeypatch):
    assert registry.approval_requirement_for("ZZ-99", stp_eligible=False) == "MAKER_CHECKER_DUAL_AUTH"
    p = registry.get_pack("CO-01")
    bad = p.model_copy(update={"approval": p.approval.model_copy(update={"when_not_stp": "SOMETHING_NEW"})})
    monkeypatch.setattr(registry, "get_pack", lambda code: bad)
    assert registry.approval_requirement_for("CO-01", stp_eligible=False) == "MAKER_CHECKER_DUAL_AUTH"


def test_flag_off_keeps_the_strict_default(monkeypatch):
    monkeypatch.setenv("PEX_PROFILE_PACKS", "off")
    assert registry.approval_requirement_for("ST-04", stp_eligible=False) == "MAKER_CHECKER_DUAL_AUTH"


def _run(prefix, variant):
    from test_profile_goldens import CASES
    from app.services.e2e_runner import E2EExecutionHarness
    key = next(k for k in CASES if k.startswith(f"input/{prefix}_") and k.endswith(variant.replace(".json", "")))
    return E2EExecutionHarness().process_input(CASES[key])


@pytest.mark.parametrize("prefix,expected", [("CO-01", "COMPLIANCE_THEN_RISK_SIGN_OFF"), ("CO-06", "COMPLIANCE_THEN_RISK_SIGN_OFF"),
                                              ("ST-04", "SINGLE_APPROVER"), ("ST-07", "SINGLE_APPROVER")])
def test_end_to_end_output_carries_the_pack_requirement(prefix, expected):
    assert _run(prefix, "sufficient.json").approval_requirement == expected


def test_old_profile_output_unchanged():
    assert _run("DQ-03", "sufficient.json").approval_requirement in ("MAKER_CHECKER_DUAL_AUTH", "NONE_AUTONOMOUS_STP")


# ---- v2 layer: the requirement can force a second approver; the amount rule still applies on top ----
def _case(amount, req):
    from app.services.v2 import ext as xt
    case = {"case_id": f"T-{req}-{amount}", "amount": amount, "status": "PENDING_APPROVAL"}
    xt.ext_store.put(case["case_id"], {"approval_requirement": req}, persist=False)
    return case


def test_compliance_then_risk_is_always_two_step():
    from app.services.v2 import logic as lg
    assert lg.is_dual(_case(1_000, "COMPLIANCE_THEN_RISK_SIGN_OFF")) is True


def test_single_approver_small_amount_is_one_step():
    from app.services.v2 import logic as lg
    assert lg.is_dual(_case(1_000, "SINGLE_APPROVER")) is False


def test_single_approver_large_amount_still_dual():
    from app.services.v2 import logic as lg
    assert lg.is_dual(_case(5_000_000, "SINGLE_APPROVER")) is True
