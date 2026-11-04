"""A reviewer records one of the pack's options with a reason; the effect decides what happens to the case."""
import json

import pytest

from app.core.security import get_persona
from app.profile_packs import registry
from app.schemas.canonical import LifecycleStage
from app.services.data_loader import repo
from app.services.file_watcher import PROFILE_CODE_TO_ENUM
from app.services.v2 import actions as ac
from app.services.v2 import logic as lg
from app.services.v2.core import V2Error, ext_store

CMP1, CMP2, RSK, OPS1, OPS2, ADM = (get_persona(x) for x in ("CMP-4420", "CMP-5502", "RSK-7714", "APR-3191", "APR-3192", "ADM-0001"))
_next = [20]


def _case(code, complete=True):
    """A workable case with a stored decision request, as the E2E pipeline would leave it."""
    pack = registry.get_pack(code)
    cid = list(repo.cases)[_next[0]]
    _next[0] += 1
    case = repo.cases[cid]
    case.update({"amount": 40_000.0, "status": LifecycleStage.INVESTIGATING, "profile": PROFILE_CODE_TO_ENUM[code], "maker_id": "OP-9012",
                 "dual_auth_required": False, "queue": "Compliance" if code.startswith("CO") else "Repair", "approval_history": []})
    repo.approvals[cid] = []
    base = lg.ext_of(case)
    d = pack.decision
    dr = ({"action": "DECISION_REQUIRED", "target": d.target_field, "options": list(d.options), "reviewer_role": d.reviewer_role,
           "evidence_complete": True, "missing": [], "conflicting": []} if complete else
          {"action": "INVESTIGATION_HOLD", "target": d.target_field, "options": [], "reviewer_role": d.reviewer_role,
           "evidence_complete": False, "missing": ["SCREENING_RECORD"], "conflicting": []})
    ext_store.put(cid, {k: v for k, v in {**base, "decision_request": dr}.items() if k not in ("decision", "decision_history", "compliance")}, persist=False)
    return cid, pack


def _opt(pack, effect):
    return next(o for o, e in pack.decision.effects.items() if e.value == effect)


def _decide(cid, user, option, comment="Reviewed the evidence."):
    return ac.record_decision(cid, user, option, comment)


# ---- guards -------------------------------------------------------------------------------------------
def test_only_the_named_role_can_decide():
    cid, pack = _case("CO-02")
    for who in (RSK, OPS1, ADM):
        with pytest.raises(V2Error) as e:
            _decide(cid, who, _opt(pack, "PROCEED"))
        assert e.value.status == 403
    cid, pack = _case("ST-04")
    with pytest.raises(V2Error):
        _decide(cid, CMP1, _opt(pack, "PROCEED"))


def test_reason_is_required_and_option_must_be_one_of_the_packs():
    cid, pack = _case("CO-02")
    with pytest.raises(V2Error):
        _decide(cid, CMP1, _opt(pack, "PROCEED"), comment="  ")
    with pytest.raises(V2Error):
        _decide(cid, CMP1, "SOMETHING_ELSE")


def test_cannot_decide_while_evidence_is_incomplete():
    cid, pack = _case("CO-02", complete=False)
    with pytest.raises(V2Error):
        _decide(cid, CMP1, "ESCALATE_FOR_SAR_REVIEW")


def test_the_maker_cannot_decide_their_own_case():
    cid, pack = _case("ST-04")
    repo.cases[cid]["maker_id"] = OPS1.user_id
    with pytest.raises(V2Error) as e:
        _decide(cid, OPS1, _opt(pack, "PROCEED"))
    assert e.value.code == "SOD_VIOLATION"


# ---- PROCEED -------------------------------------------------------------------------------------------
def test_compliance_proceed_counts_as_step_one_then_risk_approves_once():
    cid, pack = _case("CO-02")
    out = _decide(cid, CMP1, _opt(pack, "PROCEED"))
    case = repo.cases[cid]
    assert lg.status_of(case) == "PENDING_APPROVAL" and out["ok"]
    ext = lg.ext_of(case)
    assert ext["decision"]["option"] == _opt(pack, "PROCEED") and ext["decision"]["by"] == CMP1.user_id and ext["decision"]["final"] is True
    assert ext["compliance"]["released_by"]["user_id"] == CMP1.user_id
    assert lg.is_dual(case) is False                            # release was step one
    ok, code, msg = lg.approve_gate(case, CMP1)
    assert not ok                                               # the decider cannot approve (and has no approve permission)
    ok, code, msg = lg.approve_gate(case, RSK)
    assert ok, msg


def test_settlement_proceed_needs_a_different_approver():
    cid, pack = _case("ST-04")
    _decide(cid, OPS1, _opt(pack, "PROCEED"))
    case = repo.cases[cid]
    assert lg.status_of(case) == "PENDING_APPROVAL"
    ok, code, msg = lg.approve_gate(case, OPS1)
    assert not ok and code == "SOD_VIOLATION"
    ok, code, msg = lg.approve_gate(case, OPS2)
    assert ok, msg


def test_a_second_decision_after_a_final_one_is_refused():
    cid, pack = _case("ST-05")
    _decide(cid, OPS1, _opt(pack, "PROCEED"))
    with pytest.raises(V2Error):
        _decide(cid, OPS2, _opt(pack, "STOP"))


# ---- ESCALATE / HOLD -----------------------------------------------------------------------------------
def test_escalate_moves_the_case_to_escalated():
    cid, pack = _case("CO-03")
    _decide(cid, CMP1, _opt(pack, "ESCALATE"))
    assert lg.status_of(repo.cases[cid]) == "ESCALATED"
    assert lg.ext_of(repo.cases[cid])["decision"]["final"] is True


def test_hold_keeps_the_case_open_and_can_be_decided_again():
    cid, pack = _case("ST-07")
    before = lg.status_of(repo.cases[cid])
    _decide(cid, OPS1, _opt(pack, "HOLD"), "Waiting for the ordering bank.")
    ext = lg.ext_of(repo.cases[cid])
    assert lg.status_of(repo.cases[cid]) == before
    assert ext["decision"]["final"] is False and len(ext["decision_history"]) == 1
    _decide(cid, OPS1, _opt(pack, "PROCEED"), "Ordering bank replied.")
    assert lg.ext_of(repo.cases[cid])["decision"]["final"] is True
    assert len(lg.ext_of(repo.cases[cid])["decision_history"]) == 2


# ---- STOP ----------------------------------------------------------------------------------------------
def test_settlement_stop_rejects_the_case():
    cid, pack = _case("ST-05")
    _decide(cid, OPS1, _opt(pack, "STOP"), "Recall confirmed.")
    assert lg.status_of(repo.cases[cid]) == "REJECTED"
    assert lg.ext_of(repo.cases[cid])["decision"]["final"] is True


def test_compliance_stop_needs_a_second_compliance_reviewer():
    cid, pack = _case("CO-05")
    stop = _opt(pack, "STOP")
    _decide(cid, CMP1, stop)
    case = repo.cases[cid]
    assert lg.status_of(case) != "REJECTED" and lg.ext_of(case)["decision"]["state"] == "awaiting_second_review"
    with pytest.raises(V2Error) as e:
        _decide(cid, CMP1, stop)                                # same person cannot confirm
    assert e.value.code == "SOD_VIOLATION"
    _decide(cid, CMP2, stop, "Confirmed.")
    assert lg.status_of(repo.cases[cid]) == "REJECTED"
    assert lg.ext_of(repo.cases[cid])["decision"]["final"] is True


def test_a_different_option_replaces_a_pending_stop():
    cid, pack = _case("CO-01")
    _decide(cid, CMP1, _opt(pack, "STOP"))
    _decide(cid, CMP2, _opt(pack, "ESCALATE"), "Needs senior eyes.")
    assert lg.status_of(repo.cases[cid]) == "ESCALATED"


# ---- audit ---------------------------------------------------------------------------------------------
def test_every_decision_is_audited():
    from app.services.audit_service import audit_service
    cid, pack = _case("CO-06")
    n0 = audit_service.get_case_provenance(cid).total_events
    _decide(cid, CMP1, _opt(pack, "PROCEED"), "FATF enhanced due diligence verified.")
    events = audit_service.get_case_provenance(cid).events
    assert len(events) == n0 + 1
    last = events[-1]
    assert last.actor_id == CMP1.user_id and last.action_name == "DECISION_RECORDED"
    assert _opt(pack, "PROCEED") in last.details
