"""Golden (characterisation) tests for the profile engine.

Freezes today's behaviour of the end-to-end runner for every shipped fixture, plus the profiles that have no
fixture (they must keep failing closed). The profile-pack refactor must not change any of these outputs.

Regenerate ONLY when a behaviour change is intended and reviewed:
    PEX_REGEN_GOLDENS=1 python -m pytest tests/test_profile_goldens.py -q
"""
import copy
import json
import os
import re
from pathlib import Path

import pytest

from app.services.e2e_runner import E2EExecutionHarness

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_FILE = ROOT / "tests" / "goldens" / "e2e_goldens.json"
FIXTURE_DIRS = [ROOT / "e2e_fixtures" / "input", ROOT / "e2e_fixtures" / "eur"]

# Fields that are random or time based per run
VOLATILE = {"audit_event_id", "audit_chain_block_hash", "processing_latency_ms", "processed_at"}
# Random ids such as WVR-KYC-84F94EE6, INQ-44B01568, AUTH-MAND-CCDF37FA
_RAND_ID = re.compile(r"(?<=[A-Z]-)[0-9A-F]{6,12}\b")
# Run-time timestamps such as 2026-11-21T15:42:01.801271Z
_TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")
# Python set literals print in arbitrary order: {'60329', '60311'}
_SET = re.compile(r"\{('[^'{}]*'(?:, '[^'{}]*')+)\}")

# The catch-all with no resolution logic and no fixture. It must fail closed to human review.
NO_FIXTURE = [("ST-08", "SETTLEMENT_RETURNS")]   # general-exception catch-all: not in the 41-profile taxonomy
_BASE_FIXTURE = ROOT / "e2e_fixtures" / "input" / "DQ-03_missing_beneficiary_sufficient.json"


def _norm(value):
    if isinstance(value, str):
        value = _SET.sub(lambda m: "{" + ", ".join(sorted(m.group(1).split(", "))) + "}", value)
        return _TS.sub("<TS>", _RAND_ID.sub("<ID>", value))
    if isinstance(value, list):
        return [_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    return value


def snapshot(source) -> dict:
    """Run one input through a fresh harness and return the stable part of the result."""
    try:
        out = E2EExecutionHarness().process_input(source)
    except Exception as exc:  # frozen too: a changed failure mode is a changed behaviour
        return {"__error__": type(exc).__name__}
    data = out.model_dump(mode="json")
    return _norm({k: v for k, v in data.items() if k not in VOLATILE})


def _cases():
    cases = {}
    for d in FIXTURE_DIRS:
        for f in sorted(d.glob("*.json")):
            if f.stem == "manifest":
                continue
            cases[f"{d.name}/{f.stem}"] = f
    base = json.loads(_BASE_FIXTURE.read_text(encoding="utf-8"))
    for code, domain in NO_FIXTURE:
        b = copy.deepcopy(base)
        b["profile_id"], b["domain"], b["exception_id"] = code, domain, f"PROBE-{code}"
        cases[f"nofixture/{code}"] = b
    return cases


CASES = _cases()


def _load_goldens() -> dict:
    return json.loads(GOLDEN_FILE.read_text(encoding="utf-8")) if GOLDEN_FILE.exists() else {}


def test_regenerate_goldens_when_requested():
    if os.environ.get("PEX_REGEN_GOLDENS") != "1":
        pytest.skip("set PEX_REGEN_GOLDENS=1 to rewrite the golden file")
    GOLDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    gold = {name: snapshot(src) for name, src in CASES.items()}
    GOLDEN_FILE.write_text(json.dumps(gold, indent=1, sort_keys=True), encoding="utf-8")


@pytest.mark.parametrize("name", sorted(CASES))
def test_output_matches_golden(name):
    gold = _load_goldens()
    assert name in gold, f"no golden for {name}; run with PEX_REGEN_GOLDENS=1 after review"
    assert snapshot(CASES[name]) == gold[name]


def test_snapshots_are_deterministic():
    """Two runs of the same input give the same snapshot (otherwise goldens would flake)."""
    for name in ("input/TR-01_kyc_expired_sufficient", "input/ST-06_funds_trapped_inquiry", "nofixture/ST-08"):
        assert snapshot(CASES[name]) == snapshot(CASES[name]), name


def test_every_profile_without_logic_fails_closed():
    for code, _ in NO_FIXTURE:
        snap = snapshot(CASES[f"nofixture/{code}"])
        assert snap["stp_eligible"] is False, code
        assert snap["hitl_required"] is True, code


def test_golden_covers_all_cases():
    assert set(_load_goldens()) == set(CASES), "golden file is out of date"
