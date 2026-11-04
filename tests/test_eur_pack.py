"""Eurozone pack: SEPA SCT / SEPA Instant / T2 / SEPA return codes / EU VoP / CBPR+ structured address.

Every fixture in e2e_fixtures/eur runs through the REAL E2E harness (E2EExecutionHarness.process_input).
Invariants: a case is STP-eligible only if all 8 predicates pass; fail-closed fixtures must never be STP.

What is real logic vs seeded reference data is documented in app/services/eur_rail_overlay.py and docs/p05_batch_report.md.
"""
import json
from pathlib import Path

import pytest

from app.services.e2e_runner import E2EExecutionHarness
from app.services.eur_rail_overlay import SEPA_RETURN_POLICY, evaluate_rail_rules, resolve_dq05
from app.services.synthetic_batch import iban_valid

EUR_DIR = Path(__file__).resolve().parent.parent / "e2e_fixtures" / "eur"
MANIFEST = json.loads((EUR_DIR / "manifest.json").read_text(encoding="utf-8"))
PRED = ("e_suff", "r_det", "r_uniq", "v_det", "v_auth", "p_bank", "c_comp", "x_pre")


def _run(name):
    out = E2EExecutionHarness().process_input(EUR_DIR / name)  # fresh harness: isolated idempotency/evidence ports
    return out, json.loads((EUR_DIR / name).read_text(encoding="utf-8"))


def test_pack_is_complete():
    assert len(MANIFEST) >= 30
    for must in ("sct_dq01_de_transposition", "sct_dq01_fr_transposition", "sct_dq01_nl_transposition", "sct_dq01_es_transposition",
                 "sct_dq01_it_transposition", "inst_pr07_timeout_exceeded", "t2_pr04_cutoff_policy_blocked", "sepa_return_ac04",
                 "eu_vop_close_match", "cbpr_dq05_nl_unstructured"):
        assert f"{must}.json" in MANIFEST


@pytest.mark.parametrize("name", sorted(MANIFEST))
def test_fixture_outcome_matches_expectation(name):
    exp = MANIFEST[name]["expect_stp"]
    out, rec = _run(name)
    pb = out.predicate_breakdown
    assert out.stp_eligible == all(getattr(pb, k) for k in PRED), "STP must equal the conjunction of the 8 predicates"
    assert out.execution_owner == "BANK"
    if exp is not None:
        assert out.stp_eligible is exp, f"{name}: {MANIFEST[name]['why']} | {out.stp_decision_reason}"
    if exp is False:
        assert out.hitl_required and out.next_action == "ROUTE_TO_OPERATIONS_WORKLIST"
    assert rec["payment_info"]["clearing_rail"] != "TARGET2", "new data uses the name T2"


# ---------------------------------------------------------------- SCT IBAN repairs
@pytest.mark.parametrize("cc", ["de", "fr", "nl", "es", "it"])
def test_sct_transposition_repair_is_real_and_valid(cc):
    out, rec = _run(f"sct_dq01_{cc}_transposition.json")
    bad = rec["payment_info"]["creditor_account"]
    good = rec["bank_supplied_evidence"]["verified_iban"]
    assert bad[:2] == good[:2] == cc.upper()
    assert not iban_valid(bad) and iban_valid(good)
    diff = [i for i in range(len(bad)) if bad[i] != good[i]]
    assert len(diff) == 2 and diff[1] == diff[0] + 1 and bad[diff[0]] == good[diff[1]], "adjacent transposition"
    rf = out.repaired_fields[0]
    assert rf["original_value"] == bad and rf["repaired_value"] == good
    assert out.stp_eligible and "SEPA_SCT" in out.resolution_basis


# ---------------------------------------------------------------- SEPA Instant
def test_sepa_inst_limit_currency_timeout_and_no_hold():
    over, _ = _run("inst_dq01_over_limit.json")
    assert not over.stp_eligible and "limit" in over.stp_decision_reason.lower()
    ccy, _ = _run("inst_dq01_wrong_currency.json")
    assert not ccy.stp_eligible and "EUR only" in ccy.stp_decision_reason
    to, _ = _run("inst_pr07_timeout_exceeded.json")
    assert not to.stp_eligible and to.resolution_recommendation["action"] == "STATUS_INQUIRY_AND_RETURN_REVIEW"
    assert to.resolution_recommendation["route"] == "HUMAN_REVIEW"
    hold, _ = _run("inst_pr09_hold_not_allowed.json")
    assert not hold.stp_eligible and hold.resolution_recommendation["action"] == "REJECT_OR_RETURN_REVIEW_NO_HOLD"
    ok, _ = _run("inst_pr07_within_window.json")
    assert ok.predicate_breakdown.r_det  # inside the 10 s window the overlay does not block


def test_overlay_unit_rules():
    class P:  # minimal payment stub
        def __init__(self, rail, amount=1000.0, ccy="EUR"):
            self.clearing_rail, self.amount, self.currency = rail, amount, ccy
    assert evaluate_rail_rules("DQ-01", P("FEDWIRE", ccy="USD"), {}) is None
    assert evaluate_rail_rules("PR-07", P("SEPA_INST"), {"scheme_elapsed_ms": 10001})["block"]
    assert not evaluate_rail_rules("PR-07", P("SEPA_INST"), {"scheme_elapsed_ms": 9999})["block"]
    assert evaluate_rail_rules("DQ-01", P("SEPA_INST", amount=100000.01), {})["block"]
    assert not evaluate_rail_rules("DQ-01", P("SEPA_INST", amount=100000.0), {})["block"]
    assert evaluate_rail_rules("DQ-01", P("SEPA_INST", amount=150000.0), {"sepa_inst_limit_eur": 200000})["block"] is False
    assert not evaluate_rail_rules("DQ-09", P("SEPA_SCT"), {"verification_of_payee_confirmation": {"match_status": "MATCH"}})["block"]
    for st in ("CLOSE_MATCH", "NO_MATCH", "NOT_POSSIBLE", ""):
        assert evaluate_rail_rules("DQ-09", P("SEPA_SCT"), {"verification_of_payee_confirmation": {"match_status": st}})["block"]
    assert evaluate_rail_rules("DQ-09", P("TARGET2"), {}) is None  # legacy rail name untouched


# ---------------------------------------------------------------- Return reason codes
def test_return_codes_policy_and_outcomes():
    stp_codes = {c for c, v in SEPA_RETURN_POLICY.items() if v[1]}
    assert stp_codes == {"AC01", "AC04"}
    assert set(SEPA_RETURN_POLICY) == {"AC01", "AC04", "AC06", "AM04", "MS03", "RR04"}
    for code in SEPA_RETURN_POLICY:
        out, _ = _run(f"sepa_return_{code.lower()}.json")
        assert out.stp_eligible == (code in stp_codes), code
        assert out.resolution_recommendation["action"] == SEPA_RETURN_POLICY[code][2]
    ac04, _ = _run("sepa_return_ac04.json")
    assert ac04.resolution_recommendation["handling"] == "ST-02"
    assert not _run("sepa_return_xx99.json")[0].stp_eligible


# ---------------------------------------------------------------- T2
def test_t2_cutoff_roll_and_policy_block():
    ok, rec = _run("t2_pr04_cutoff_roll_allowed.json")
    assert ok.stp_eligible and ok.repaired_fields[0]["repaired_value"] > rec["payment_info"]["value_date"]
    assert "T2 cutoff time: 16:00 UTC" in ok.resolution_basis
    blocked, _ = _run("t2_pr04_cutoff_policy_blocked.json")
    assert not blocked.stp_eligible and not blocked.predicate_breakdown.r_det


# ---------------------------------------------------------------- EU VoP
def test_vop_only_match_proceeds_and_none_of_the_pack_is_autonomous():
    for st in ("close_match", "no_match", "not_possible"):
        out, _ = _run(f"eu_vop_{st}.json")
        assert not out.stp_eligible and "VoP" in out.resolution_basis


# ---------------------------------------------------------------- CBPR+ DQ-05
@pytest.mark.parametrize("k,town", [("nl", "Amsterdam"), ("es", "Madrid"), ("it", "Torino"), ("fr", "Paris"), ("de", "Frankfurt")])
def test_dq05_structuring_is_traceable(k, town):
    out, rec = _run(f"cbpr_dq05_{k}_unstructured.json")
    assert out.stp_eligible
    st = out.repaired_fields[0]["repaired_value"]
    raw = rec["bank_supplied_evidence"]["creditor_postal_address"]
    assert st["town_name"] == town and st["country_code"] == k.upper()
    for f in ("street_name", "building_number", "post_code", "town_name"):
        assert st[f] in raw, f"{f} must be traceable to the inbound text"
    assert "<TwnNm>" in out.resolution_recommendation["iso20022_xml"]


def test_dq05_fail_closed_cases():
    assert not _run("cbpr_dq05_de_ambiguous_postcode.json")[0].stp_eligible
    assert not _run("cbpr_dq05_untraceable_components.json")[0].stp_eligible
    assert not _run("cbpr_dq05_missing_address_evidence.json")[0].stp_eligible
    assert resolve_dq05({"creditor_postal_address": "Somewhere, Germany"})["r_det"] is False
    with_master = resolve_dq05({"creditor_postal_address": "Somewhere, Germany",
                                "core_address_master": {"country_code": "DE", "street_name": "Hafenstrasse", "building_number": "3",
                                                        "post_code": "20457", "town_name": "Hamburg"}})
    assert with_master["r_det"] and with_master["v_det"]  # authoritative bank master supplies the fields


# ---------------------------------------------------------------- unrelated hardening found while building the pack
def test_unregistered_profile_fails_closed():  # ST-08 (general exception) is the only code with no pack
    """Before: unknown profiles got r_det=r_uniq=v_det=True and reached STP with any default mandatory evidence."""
    rec = {"exception_id": "PEX-EUR-UNREG-1", "profile_id": "ST-08", "domain": "SETTLEMENT", "error_code": "E", "error_message": "m",
           "payment_info": {"payment_id": "P-UNREG", "uetr": "5c1f6a8e-2d34-4b57-9a10-0e5a7b3c9d11", "amount": 500.0, "currency": "EUR",
                            "clearing_rail": "SEPA_SCT", "debtor_name": "A", "creditor_name": "B"},
           "bank_supplied_evidence": {"core_dda_account": "DE89370400440532013000"},
           "evidence_provenance": "NON_PRODUCTION_DEMO", "test_status": "TEST_ONLY"}
    out = E2EExecutionHarness().process_input(rec)
    assert out.predicate_breakdown.e_suff and not out.stp_eligible and not out.predicate_breakdown.r_det
    assert "fail closed" in out.resolution_basis


# ---------------------------------------------------------------- through the batch pipeline (watcher path)
def test_eur_pack_through_batch_pipeline(tmp_path):
    from app.services.batch_pipeline import BatchPipeline
    from app.services.file_watcher import FileWatcherService
    from app.services.data_loader import repo
    import uuid
    recs = []
    for name in sorted(MANIFEST):
        r = json.loads((EUR_DIR / name).read_text(encoding="utf-8"))
        tag = uuid.uuid4().hex[:8].upper()  # unique ids: the test DB persists between runs
        r["exception_id"] += f"-{tag}"
        r["payment_info"]["uetr"] = str(uuid.uuid4())
        recs.append(r)
    p = tmp_path / "inbox"
    p.mkdir()
    (p / "eur.json.gz").write_bytes(__import__("gzip").compress(json.dumps({"batch_id": "EUR-PACK", "source_system": "TEST", "records": recs}).encode()))
    w = FileWatcherService(input_dir=p, output_dir=tmp_path / "outbox", archive_dir=tmp_path / "archive")
    pl = BatchPipeline(base_dir=tmp_path, watcher=w, chunk_size=10)
    b = pl.wait(pl.submit_file(p / "eur.json.gz"), 300)
    assert b["processed"] == len(recs) and b["failed"] == 0
    lines = [json.loads(l) for l in pl.results_path(b["batch_id"]).read_text().splitlines()]
    for ln in lines:
        assert ln["stp_eligible"] == all(ln["predicates"].values())
    stp = [ln for ln in lines if ln["stp_eligible"]]
    assert stp and all(ln["queue"] == "STP Fast-Lane" for ln in stp)
    de = [ln for ln in lines if "SCT-DQ01-DE-TRANSPOSITION" in ln["exception_id"]]
    assert de
    case = repo.get_case(de[0]["exception_id"])
    assert case["debtor_party"]["country"] == "DE" and case["creditor_party"]["country"] == "DE"  # derived from IBAN, not hard-coded
