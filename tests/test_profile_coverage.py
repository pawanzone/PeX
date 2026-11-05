"""Every profile pack is covered by fixtures, and every repair profile has a case with incomplete or conflicting evidence that stays out of STP."""
import json
import pytest
from app.profile_packs import registry
from app.services.e2e_runner import E2EExecutionHarness
from test_profile_goldens import CASES

REPAIR = sorted(c for c, p in registry.load_packs().items() if p.outcome.value == "REPAIR")


def _raw(src):
    return json.loads(json.dumps(src)) if isinstance(src, dict) else json.loads(src.read_text(encoding="utf-8"))


def test_every_pack_has_at_least_two_fixtures():
    from collections import Counter
    n = Counter(_raw(p).get("profile_id") for p in CASES.values())
    thin = [c for c in registry.load_packs() if n[c] < 2]
    assert not thin, f"profiles with fewer than 2 fixtures: {thin}"


@pytest.mark.parametrize("code", REPAIR)
def test_repair_profile_with_incomplete_or_conflicting_evidence_is_never_straight_through(code):
    from test_profile_goldens import _load_goldens
    gold = _load_goldens()
    missing = [(n, s) for n, s in CASES.items() if gold.get(n, {}).get("detected_profile_id") == code and gold[n].get("evidence_status") != "SUFFICIENT"]
    assert missing, f"{code} has no fixture with incomplete or conflicting evidence"
    for n, src in missing:
        raw = _raw(src)
        raw["payment_info"]["amount"] = 100.0
        out = E2EExecutionHarness().process_input(raw)
        assert out.evidence_status != "SUFFICIENT" and (out.evidence_missing or out.evidence_contradictions) and out.stp_eligible is False, n
