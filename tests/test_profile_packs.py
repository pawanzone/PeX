"""Profile packs: schema, registry, flag, fail-closed resolver handling, and equivalence with the frozen goldens."""
import json

import pytest

from app.profile_packs import registry
from app.profile_packs.schema import ProfilePack, ResolutionResult, ResolutionContext

BASE = {
    "code": "DQ-03", "name": "MISSING_BENEFICIARY_DATA", "family": "DATA_QUALITY", "version": 1,
    "outcome": "REPAIR", "stp": "ALLOWED",
    "evidence": {"required": [{"type": "BENEFICIARY_PROFILE", "tier": 1}, {"type": "CLIENT_VAULT", "tier": 1}], "min_confidence": 0.88},
    "checks": ["directory", "core"], "resolver": "dq03_missing_beneficiary",
    "authority_domain": "ACCOUNT_OWNERSHIP_BALANCE", "action": "REPAIR_AND_RELEASE",
    "approval": {"when_not_stp": "MAKER_CHECKER"},
}


def pack(**over):
    return {**BASE, **over}


# ---- schema ----------------------------------------------------------------------------------
def test_valid_pack_loads():
    p = ProfilePack(**BASE)
    assert p.code == "DQ-03" and p.outcome == "REPAIR" and p.stp == "ALLOWED"


@pytest.mark.parametrize("bad", [
    pack(code="XX-01"), pack(code="DQ-3"), pack(version=0), pack(outcome="MAGIC"), pack(stp="SOMETIMES"),
    pack(unknown_field=1), pack(resolver=None),                      # REPAIR needs a resolver
    pack(outcome="DECISION_SUPPORT", stp="ALLOWED", resolver=None),  # decision support may never be straight-through
    pack(outcome="REPAIR", stp="NEVER"),                             # NEVER-STP cannot be a repair
])
def test_invalid_packs_are_rejected(bad):
    with pytest.raises(Exception):
        ProfilePack(**bad)


def test_decision_support_pack_without_resolver_is_valid():
    p = ProfilePack(**pack(code="CO-01", name="SANCTIONS_SUSPECTED", family="COMPLIANCE", outcome="DECISION_SUPPORT",
                           stp="NEVER", resolver=None, checks=["screening"],
                           authority_domain="LEGAL_PROHIBITION", action="INVESTIGATION_HOLD",
                           approval={"when_not_stp": "COMPLIANCE_THEN_RISK"},
                           decision={"target_field": "x.y", "options": ["A", "B"], "reviewer_role": "COMPLIANCE_APPROVER"}))
    assert p.resolver is None


# ---- registry --------------------------------------------------------------------------------
def test_bundled_packs_load_and_reference_registered_resolvers():
    packs = registry.load_packs()
    assert "DQ-03" in packs
    for p in packs.values():
        if p.resolver:
            assert registry.get_resolver(p.resolver) is not None, p.code


def test_unknown_resolver_in_a_pack_file_is_a_load_error(tmp_path):
    (tmp_path / "x.json").write_text(json.dumps(pack(resolver="does_not_exist")), encoding="utf-8")
    with pytest.raises(ValueError):
        registry.load_packs(tmp_path)


def test_duplicate_codes_are_a_load_error(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(BASE), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(BASE), encoding="utf-8")
    with pytest.raises(ValueError):
        registry.load_packs(tmp_path)


def test_get_pack_unknown_code_is_none():
    assert registry.get_pack("ZZ-99") is None


# ---- flag ------------------------------------------------------------------------------------
def test_flag_is_on_by_default_and_can_be_switched_off(monkeypatch):
    monkeypatch.delenv("PEX_PROFILE_PACKS", raising=False)
    assert registry.is_enabled("DQ-03") is True
    assert registry.is_enabled("ZZ-99") is False  # no pack: legacy path
    for off in ("off", "NONE", "0", "false"):
        monkeypatch.setenv("PEX_PROFILE_PACKS", off)
        assert registry.is_enabled("DQ-03") is False, off


def test_flag_lists_specific_profiles(monkeypatch):
    monkeypatch.setenv("PEX_PROFILE_PACKS", " dq-03 , PR-02 ")
    assert registry.is_enabled("DQ-03") is True
    assert registry.is_enabled("PR-02") is False or registry.get_pack("PR-02") is not None
    assert registry.is_enabled("DQ-01") is False


def test_flag_star_enables_every_profile_that_has_a_pack(monkeypatch):
    monkeypatch.setenv("PEX_PROFILE_PACKS", "*")
    assert registry.is_enabled("DQ-03") is True
    assert registry.is_enabled("ZZ-99") is False  # no pack, so the legacy path


# ---- fail closed -----------------------------------------------------------------------------
def test_resolver_that_raises_fails_closed(monkeypatch):
    monkeypatch.setenv("PEX_PROFILE_PACKS", "DQ-03")

    def boom(ctx):
        raise RuntimeError("resolver broke")
    monkeypatch.setitem(registry._RESOLVERS, "dq03_missing_beneficiary", boom)
    res = registry.resolve_if_enabled("DQ-03", ResolutionContext(profile="DQ-03", pmt=None, evidence={}, envelope=None))
    assert isinstance(res, ResolutionResult)
    assert (res.determined, res.unique, res.validated) == (False, False, False)
    assert "fail" in res.basis.lower()


def test_resolve_if_enabled_returns_none_when_flag_off(monkeypatch):
    monkeypatch.setenv("PEX_PROFILE_PACKS", "off")
    assert registry.resolve_if_enabled("DQ-03", ResolutionContext(profile="DQ-03", pmt=None, evidence={}, envelope=None)) is None


# ---- consistency with the legacy profile spec (until that spec is generated from packs) -------
def test_pack_matches_legacy_profile_spec_except_evidence():
    from app.services.profile_engine import PROFILE_SPECS
    from app.services.file_watcher import PROFILE_CODE_TO_ENUM
    for code, p in registry.load_packs().items():
        spec = PROFILE_SPECS[PROFILE_CODE_TO_ENUM[code]]
        assert p.evidence.min_confidence == spec["min_confidence"], code
        assert p.name == PROFILE_CODE_TO_ENUM[code].name, code


# ---- equivalence: packs on must reproduce the frozen goldens exactly --------------------------
def test_every_ported_profile_reproduces_its_goldens(monkeypatch):
    from test_profile_goldens import CASES, snapshot, _load_goldens
    monkeypatch.setenv("PEX_PROFILE_PACKS", "*")
    gold = _load_goldens()
    ported = set(registry.load_packs())
    checked = 0
    for name, src in CASES.items():
        code = name.split("/")[-1].split("_")[0].upper()
        if code in ported:
            assert snapshot(src) == gold[name], name
            checked += 1
    assert checked >= 2  # at least the sufficient + insufficient fixture of each ported profile


def test_pack_path_is_actually_used_when_enabled(monkeypatch):
    """Guards the equivalence test: with the flag on, the pack resolver (not the legacy branch) runs."""
    from test_profile_goldens import CASES, snapshot
    calls = []
    real = registry._RESOLVERS["dq03_missing_beneficiary"]
    monkeypatch.setitem(registry._RESOLVERS, "dq03_missing_beneficiary", lambda ctx: (calls.append(1), real(ctx))[1])
    src = CASES["input/DQ-03_missing_beneficiary_sufficient"]
    monkeypatch.setenv("PEX_PROFILE_PACKS", "DQ-03")
    snapshot(src)
    assert calls, "pack resolver was not called"
    calls.clear()
    monkeypatch.setenv("PEX_PROFILE_PACKS", "off")
    snapshot(src)
    assert not calls, "flag off must use the legacy branch"


def test_all_goldens_reproduce_with_every_pack_on(monkeypatch):
    """The strongest equivalence check: flag * over ALL frozen cases (fixtures with any file name)."""
    from test_profile_goldens import CASES, snapshot, _load_goldens
    monkeypatch.setenv("PEX_PROFILE_PACKS", "*")
    gold = _load_goldens()
    for name, src in CASES.items():
        assert snapshot(src) == gold[name], name


def test_every_pack_has_a_valid_authority_domain_and_a_registered_resolver():
    from app.schemas.contracts.authority_schemas import QuestionDomain
    packs = registry.load_packs()
    assert len(packs) >= 37
    for code, p in packs.items():
        assert p.authority_domain in QuestionDomain.__members__, code
        if p.resolver:
            assert registry.get_resolver(p.resolver) is not None, code


def test_never_straight_through_packs_never_stp_in_any_golden():
    from test_profile_goldens import CASES, snapshot
    never = {c for c, p in registry.load_packs().items() if p.stp.value == "NEVER"}
    assert "TR-08" in never
    for name, src in CASES.items():
        code = name.split("/")[-1].split("_")[0].upper()
        if code in never:
            assert snapshot(src)["stp_eligible"] is False, name
