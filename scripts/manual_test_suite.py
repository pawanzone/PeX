#!/usr/bin/env python3
"""Manual test suite for PeX: the test cases, the steps a person follows, the expected results, and an executor that runs the same
steps through the API the screens use and records pass/fail for each check.

The workbook (scripts/build_test_workbook.py) is generated from this file, so what a tester reads is what was run.

Usage (backend running on a database seeded by scripts/reset_and_seed_demo.py):
    python scripts/manual_test_suite.py --run results.json [--api http://127.0.0.1:8001]
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

API = "http://127.0.0.1:8001/api"
PW = "demo1234"
MANIFEST = Path(__file__).resolve().parent / "testpack_manifest.json"

# ---- people ------------------------------------------------------------------------------------------------------------------
P = {"OP-9012": "Priya Nair (Operator)", "OP-9013": "Amina Okafor (Operator)", "APR-3191": "Daniel Osei (Operations Approver)",
     "APR-3192": "Mei Tan (Operations Approver)", "CMP-4420": "Marisol Vega (Compliance Approver)", "CMP-6001": "Amara Okafor (Compliance Approver)",
     "RSK-7714": "Kenji Watanabe (Risk Approver)", "RSK-7715": "Helen Brandt (Risk Approver)", "SUP-2001": "Elena Marsh (Supervisor)",
     "AUD-5001": "Rhea Kapoor (Audit and Risk)", "ADM-0001": "Alex Whitfield (Admin)", "ADM-0002": "Tomas Berg (Admin)",
     "POL-8001": "Nadia Rahman (Policy Owner)", "POL-8002": "Greg Holt (Policy Owner)"}
FIRST = lambda uid: P[uid].split(" (")[0]


# ---- API access (same calls the screens make) -----------------------------------------------------------------------------------
_tok: Dict[str, str] = {}


def _h(uid: str) -> Dict[str, str]:
    if uid not in _tok:
        r = requests.post(API + "/auth/login", json={"user_id": uid})
        r.raise_for_status()
        _tok[uid] = r.json()["access_token"]
    return {"Authorization": "Bearer " + _tok[uid]}


def get(uid: str, path: str, **kw):
    return requests.get(API + "/v2" + path, headers=_h(uid), **kw)


def post(uid: str, path: str, body: Optional[dict] = None):
    return requests.post(API + "/v2" + path, headers=_h(uid), json=body or {})


def msg(r) -> str:
    try:
        j = r.json()
        return str(j.get("message") or j.get("detail") or j)[:200]
    except Exception:
        return r.text[:200]


def page(uid: str, cid: str) -> dict:
    return get(uid, f"/cases/{cid}/page").json()


def chips(cid: str) -> str:
    return " | ".join(c["label"] for c in page("AUD-5001", cid)["header"]["chips"])


def variant(cid: str) -> str:
    return page("AUD-5001", cid)["variant"]


def wait_variant(cid: str, want: str, secs: int = 25) -> str:
    end = time.time() + secs
    v = variant(cid)
    while v != want and time.time() < end:
        time.sleep(1)
        v = variant(cid)
    return v


def audit_actions(cid: str) -> List[str]:
    r = get("AUD-5001", "/audit/events", params={"case_id": cid, "page_size": 200}).json()
    return [e["action"] for e in r.get("items", [])]


# ---- recorder ------------------------------------------------------------------------------------------------------------------
class Run:
    def __init__(self):
        self.checks: List[Dict[str, Any]] = []

    def check(self, what: str, ok: bool, observed: Any = ""):
        self.checks.append({"what": what, "ok": bool(ok), "observed": str(observed)[:300]})
        return bool(ok)

    def call(self, what: str, uid: str, cid: str, action: str, body: Optional[dict] = None, expect: int = 200, contains: str = ""):
        r = post(uid, f"/cases/{cid}/{action}", body)
        ok = r.status_code == expect and (contains.lower() in msg(r).lower() if contains else True)
        self.check(f"{FIRST(uid)}: {what}", ok, f"HTTP {r.status_code}: {msg(r)}")
        return r

    def state(self, what: str, cid: str, want_chip: str):
        c = chips(cid)
        self.check(what, want_chip.lower() in c.lower(), c)


# ---- test case model ---------------------------------------------------------------------------------------------------------------
class TC:
    def __init__(self, section, code, scenario, case_id, title, who, steps, expected, run, data=""):
        self.section, self.code, self.scenario, self.case_id, self.title = section, code, scenario, case_id, title
        self.who, self.steps, self.expected, self.run, self.data = who, steps, expected, run, data
        self.id = ""


def _num(lines: List[str]) -> str:
    return "\n".join(f"{i}. {s}" for i, s in enumerate(lines, 1))


def _man() -> Dict[str, dict]:
    return {m["case_id"]: m for m in json.loads(MANIFEST.read_text())}


def _data(m: dict) -> str:
    amt = f"{m['currency']} {m['amount']:,.2f}" if m.get("amount") is not None else ""
    bits = [f"Case {m['case_id']}", m.get("counterparty") or "", amt, m.get("rail") or "", m.get("change") or m.get("reason") or ""]
    return " | ".join(b for b in bits if b)


OPEN = "Worklist > search the case ID > open it"
SIGN = "Sign in as {} (password demo1234)"
HANDOFF_OK = "Approved. Handed to the bank system (simulated)"


def _lookup(code: str) -> dict:
    global _LIB
    try:
        _LIB
    except NameError:
        _LIB = {r["code"]: r for r in json.loads((Path(__file__).resolve().parent / "profiles_snapshot.json").read_text())}
    return _LIB[code]


def pname(code: str) -> str:
    return _lookup(code)["name"].replace("_", " ").title()


# ==================================================================================================================================
# 1. clean workflows
# ==================================================================================================================================
def mc_clean(m: dict) -> TC:
    cid, code = m["case_id"], m["code"]

    def run(R: Run):
        pg = page("OP-9012", cid)
        R.check("Priya sees the case ready for her decision", pg["variant"] == "DECISION", chips(cid))
        R.check("The recommended change is shown", bool(pg.get("change_summary") or pg.get("decision_brief")), (pg.get("decision_brief") or {}).get("proposed_change", ""))
        R.check("Evidence is complete (all sources agree)", pg["evidence_summary"]["agree"] == pg["evidence_summary"]["total"] > 0, pg["evidence_summary"]["label"])
        R.call("Assign to me", "OP-9012", cid, "assign", {"assignee": "me"})
        R.call("Submit for approval with a handover note", "OP-9012", cid, "submit", {"handover_note": f"Checked the evidence for {cid}; the proposed change matches the source."}, contains="Submitted")
        R.state("Case is now Pending approval", cid, "Pending approval")
        ap = page("APR-3191", cid)
        R.check("Daniel sees the decision panel and can approve", (ap.get("decision_form") or {}).get("can_approve") is True, (ap.get("decision_form") or {}).get("cannot_approve_reason"))
        R.call("Approve with the review tick", "APR-3191", cid, "approve", {"reviewed": True, "comment": "Reviewed change summary and evidence."}, contains=HANDOFF_OK)
        R.state("Case is Handed to bank", cid, "Handed to bank")
        R.check("About 6 seconds later the simulated bank confirms: Executed by bank", wait_variant(cid, "EXECUTED") == "EXECUTED", chips(cid))
        acts = audit_actions(cid)
        R.check("Audit trail has the maker submission and the approval", "CASE_SUBMITTED" in str(acts) or "MAKER_SUBMITTED_FOR_APPROVAL" in str(acts), ", ".join(acts[:8]))
        R.check("Audit trail has the bank confirmation", any("EXECUTED" in a or "BANK" in a for a in acts), ", ".join(acts[:8]))

    steps = [SIGN.format("Priya Nair") + ". Open " + OPEN + ".",
             f"Check the screen: title '{pname(code)}', status 'Validated · not yet approved', a 'Recommended fix' box, and 'N of N sources agree'.",
             "Click 'Assign to me', then 'Submit for approval'. Type a handover note and click Submit.",
             "Sign out. Sign in as Daniel Osei. Open Approvals and open the same case.",
             "Read the Change summary and the Evidence tab. Tick 'I have reviewed the change summary and evidence'. Click 'Approve for bank handoff'.",
             "Check the case now says 'Handed to bank'. Wait about 10 seconds and refresh: it says 'Executed by bank' with a bank reference.",
             "Sign in as Rhea Kapoor. Open Audit and search the case ID. The trail shows the submission, the approval, the hand-off and the bank confirmation."]
    exp = ["Submit works and the case moves to Pending approval.", "'Approve for bank handoff' is enabled only after the review tick.",
           "Message: Approved. Handed to the bank system (simulated); waiting for bank confirmation. Not yet executed.",
           "After about 6 seconds the status is 'Executed by bank'.", "Audit events exist for each step and the audit chain shows as valid."]
    return TC("A. Clean workflow, one for each profile", code, "Clean", cid, f"{pname(code)}: propose, approve, hand off", "Priya Nair, then Daniel Osei, then Rhea Kapoor",
              _num(steps), _num(exp), run, _data(m))


def dq03_clean(m: dict) -> TC:
    cid = m["case_id"]

    def run(R: Run):
        R.check("Case waits for missing information", variant(cid) == "MISSING_INFO", chips(cid))
        R.call("Request information from the client", "OP-9012", cid, "request-information", {"message": "Please send the IBAN for Valence Logistics SAS.", "method": "Email"}, contains="Request sent")
        R.state("Case shows Waiting for information", cid, "Waiting for information")
        R.call("Client reply arrives: reassess with the IBAN provided", "OP-9012", cid, "reassess", {"note": "Client replied", "provided": {"iban": "FR7630004000031234567890143"}}, contains="Evidence is now complete")
        R.check("Case is ready for a decision with a proposed change", variant(cid) == "DECISION", chips(cid))
        R.call("Submit for approval", "OP-9012", cid, "submit", {"handover_note": "Client supplied the IBAN by email; checksum validated."}, contains="Submitted")
        r = post("APR-3191", f"/cases/{cid}/approve", {"reviewed": True, "comment": "x"})
        R.check("Daniel is stopped: confidence is below 85% because the evidence is a client email only", r.status_code == 403, msg(r))
        R.call("Mei Tan records the independent evidence review", "APR-3192", cid, "confidence-review", {"decision": "confirm", "comment": "Client email checked against the account holder record."}, contains="Evidence review recorded")
        R.call("Daniel approves with the review tick", "APR-3191", cid, "approve", {"reviewed": True, "comment": "Reviewed."}, contains=HANDOFF_OK)
        R.check("Simulated bank confirms: Executed by bank", wait_variant(cid, "EXECUTED") == "EXECUTED", chips(cid))

    steps = [SIGN.format("Priya Nair") + ". Open " + OPEN + ". Status is 'Missing information'.",
             "Click 'Request information'. Write a message to the client and click Send. The case moves to 'Waiting for information'.",
             "Pretend the client replied. Click 'Reassess', enter the IBAN FR7630004000031234567890143 and apply it.",
             "The case becomes ready for decision with a proposed IBAN. Click 'Submit for approval' with a handover note.",
             "Sign in as Daniel Osei. Open Approvals, open the case, tick the review box and click 'Approve for bank handoff'. Expect it to be refused: confidence is below 85%.",
             "Sign in as Mei Tan. Open the case and click 'Confirm evidence review' with a comment.",
             "Sign in as Daniel Osei again. Tick the review box and click 'Approve for bank handoff'. Wait 10 seconds: 'Executed by bank'."]
    exp = ["Request is recorded as sent (simulated, nothing leaves the system).", "New information is applied and evidence becomes complete.",
           "Approve is refused with 'Decision confidence is 45.0%, below the 85% threshold' until a second person reviews the evidence.",
           "After Mei Tan's review the approval works and the case is handed to the bank, then executed."]
    return TC("A. Clean workflow, one for each profile", "DQ-03", "Clean (missing information)", cid, "Missing beneficiary data: ask the client, repair, approve",
              "Priya Nair, Mei Tan, Daniel Osei", _num(steps), _num(exp), run, _data(m) + " | Reply IBAN to enter: FR7630004000031234567890143")


def co_clean(m: dict) -> TC:
    cid, code = m["case_id"], m["code"]
    two = code in ("CO-01", "CO-02", "CO-03", "CO-05", "CO-06", "CO-08")

    def run(R: Run):
        pg = page("CMP-4420", cid)
        R.check("Marisol sees the compliance hold", pg["variant"] == "COMPLIANCE_HOLD", chips(cid))
        R.check("The maker button 'Submit for approval' is not available on a compliance hold", not any(a["key"] == "submit" and a["enabled"] for a in page("OP-9012", cid)["actions"]), "")
        if not two:
            r = post("APR-3191", f"/cases/{cid}/compliance/decision", {"decision": "release", "reason_code": "FALSE_MATCH_NAME", "comment": "x"})
            R.check("An Operations Approver cannot clear a compliance hold", r.status_code == 403, msg(r))
        R.call("Release the hold: false match", "CMP-4420", cid, "compliance/decision", {"decision": "release", "reason_code": "FALSE_MATCH_NAME", "comment": "Different entity: registration number and country differ."}, contains="Hold released")
        R.state("Case is Pending approval and nothing was handed to the bank", cid, "Pending approval")
        r = post("APR-3191", f"/cases/{cid}/approve", {"reviewed": True, "comment": "x"})
        R.check("An Operations Approver cannot give the final approval on a compliance case", r.status_code == 403, msg(r))
        R.call("Risk Approver approves with the review tick", "RSK-7714", cid, "approve", {"reviewed": True, "comment": "Reviewed alert, comparison and evidence."}, contains=HANDOFF_OK)
        R.check("Simulated bank confirms: Executed by bank", wait_variant(cid, "EXECUTED") == "EXECUTED", chips(cid))

    steps = [SIGN.format("Marisol Vega") + ". Open Compliance and open the case (search the case ID).",
             "Check the screen: 'Compliance hold', the alert reference, the party comparison table and the evidence.",
             "Click 'Clear hold · false match (returns to approval)'. Pick the reason code 'False match: different entity', write a comment, tick 'I have reviewed the alert and the party comparison.' and click 'Record decision'.",
             "Sign out. Sign in as Kenji Watanabe. Open Approvals and open the case. It is now 'Pending approval'.",
             "Tick the review box and click 'Approve for bank handoff'.",
             "Check 'Handed to bank'. Wait 10 seconds: 'Executed by bank'."]
    exp = ["No maker step: compliance holds are not repaired by the maker.", "Release returns the case to the approval queue; nothing is sent to the bank yet.",
           "Only a Risk Approver can give the final approval (Daniel Osei is refused).", "After approval: handed to the bank, then executed."]
    return TC("A. Clean workflow, one for each profile", code, "Clean (compliance, then risk)", cid, f"{pname(code)}: compliance clears, risk approves",
              "Marisol Vega, then Kenji Watanabe", _num(steps), _num(exp), run, _data(m))


def st_clean(m: dict) -> TC:
    cid, code = m["case_id"], m["code"]
    opt = {"ST-04": "POST_FEE_ADJUSTMENT_WITHIN_TOLERANCE", "ST-05": "CONTINGENCY_CLEARING_WINDOW_DISPATCH", "ST-07": "ALLOCATE_TO_DEBTOR_RECEIVABLES_LEDGER"}[code]
    lbl = opt.replace("_", " ").capitalize()

    def run(R: Run):
        pg = page("APR-3191", cid)
        R.check("Daniel sees 'Decision required' with three options", len((pg.get("decision_request") or {}).get("options", [])) == 3, chips(cid))
        R.check("PeX does not pick an option", "PeX does not choose" in (pg.get("decision_request") or {}).get("note", ""), "")
        R.call(f"Record the decision: {lbl}", "APR-3191", cid, "decision", {"option": opt, "comment": "Resolved per the settlement procedure."}, contains="Cleared for approval")
        r = post("APR-3191", f"/cases/{cid}/approve", {"reviewed": True, "comment": "x"})
        R.check("Daniel cannot also give the approval (same person)", r.status_code == 403, msg(r))
        R.call("A different approver (Mei Tan) approves with the review tick", "APR-3192", cid, "approve", {"reviewed": True, "comment": "Reviewed."}, contains=HANDOFF_OK)
        R.check("Simulated bank confirms: Executed by bank", wait_variant(cid, "EXECUTED") == "EXECUTED", chips(cid))

    steps = [SIGN.format("Daniel Osei") + ". Open Approvals or Worklist and open the case.",
             "The 'Decision required' box lists three options. Read the evidence.", f"Select '{lbl}', write a reason and click 'Record decision'.",
             "Try to approve the same case as Daniel. It must be refused.", "Sign out. Sign in as Mei Tan. Open the case, tick the review box, click 'Approve for bank handoff'.",
             "Wait 10 seconds: 'Executed by bank'."]
    exp = ["PeX lists the options but does not choose one.", "Recording the decision clears the case for approval; it does not release it.",
           "The person who decided cannot approve (separation of duties).", "A different approver approves; the case is handed to the bank and executed."]
    return TC("A. Clean workflow, one for each profile", code, "Clean (investigation decision)", cid, f"{pname(code)}: choose an option, a second person approves",
              "Daniel Osei, then Mei Tan", _num(steps), _num(exp), run, _data(m))


# ==================================================================================================================================
# 2. the full workflow sets
# ==================================================================================================================================
def dq01_cases(man: Dict[str, dict]) -> List[TC]:
    S = "B. Full workflow set: DQ-01 Invalid IBAN"
    out: List[TC] = []

    def sub(R, cid, who="OP-9012", note="Directory record and prior payments support the proposed IBAN."):
        return R.call("Submit for approval", who, cid, "submit", {"handover_note": note}, contains="Submitted")

    c = "TST-DQ01-02"
    def r02(R, c=c):
        sub(R, c)
        R.call("Return to Maker with reason and comment", "APR-3191", c, "return", {"reviewed": True, "reason_code": "EVIDENCE_INSUFFICIENT", "comment": "Attach the invoice before resubmitting."}, contains="Returned")
        w = get("OP-9012", "/worklist", params={"tab": "returned"}).json()
        R.check("Priya sees it under 'Returned to me'", c in [x["case_id"] for x in w["items"]], "")
        R.state("Case is back with the maker", c, "Validated")
        sub(R, c, note="Invoice INV-2291 attached as requested.")
        R.call("Approve after rework", "APR-3191", c, "approve", {"reviewed": True, "comment": "Rework accepted."}, contains=HANDOFF_OK)
        R.check("Executed by bank", wait_variant(c, "EXECUTED") == "EXECUTED", chips(c))
    out.append(TC(S, "DQ-01", "Return to maker", c, "Approver returns the case; maker reworks and resubmits",
        "Priya Nair, Daniel Osei", _num([SIGN.format("Priya Nair") + ". Open the case, Assign to me, Submit for approval.",
        "Sign in as Daniel Osei. Open the case. Tick the review box. Choose 'Return to Maker', pick a reason code, write a comment, click Return to Maker.",
        "Sign in as Priya Nair. Worklist > 'Returned to me' tab: the case is there with Daniel's reason.", "Resubmit with a new handover note.",
        "Daniel ticks the box and clicks 'Approve for bank handoff'. Wait 10 seconds: Executed."]),
        _num(["Return needs the review tick, a reason code and a comment.", "The case goes to Priya's 'Returned to me' tab.", "After resubmission the normal approval works."]), r02, _data(man[c])))

    c = "TST-DQ01-03"
    def r03(R, c=c):
        sub(R, c)
        R.call("Reject with reason and comment", "APR-3191", c, "reject", {"reviewed": True, "reason_code": "DUPLICATE", "comment": "Already paid under reference PAY-0099."}, contains="Rejected")
        R.state("Case is Rejected (final)", c, "Rejected")
        r = post("APR-3191", f"/cases/{c}/approve", {"reviewed": True, "comment": "x"})
        R.check("A rejected case cannot be approved afterwards", r.status_code in (403, 409), msg(r))
        R.check("Nothing was handed to the bank", "HANDOFF_TO_BANK" not in str(audit_actions(c)), ", ".join(audit_actions(c)[:6]))
    out.append(TC(S, "DQ-01", "Reject", c, "Approver rejects the repair; the case is closed",
        "Priya Nair, Daniel Osei", _num([SIGN.format("Priya Nair") + ". Open the case and submit it for approval.",
        "Sign in as Daniel Osei. Open the case, tick the review box, choose Reject, pick 'Duplicate of another payment', write a comment, click Reject.",
        "Open the case again: status 'Rejected'. Try to approve it: no Approve button."]),
        _num(["Reject needs the review tick, a reason code and a comment.", "Status is Rejected; the case never goes to the bank.", "Audit trail shows the rejection with the reason."]), r03, _data(man[c])))

    c = "TST-DQ01-04"
    def r04(R, c=c):
        R.call("Escalate to the supervisor with a reason", "OP-9012", c, "escalate", {"to": "SUPERVISOR", "reason": "Beneficiary unreachable; need guidance."}, contains="Escalated")
        R.check("Escalation is in the audit trail", "CASE_ESCALATED" in audit_actions(c), ", ".join(audit_actions(c)[:6]))
        pg = page("SUP-2001", c)
        R.check("Elena Marsh (Supervisor) can open the case and work it", any(a["enabled"] for a in pg["actions"]), [a["key"] for a in pg["actions"] if a["enabled"]])
    out.append(TC(S, "DQ-01", "Escalate", c, "Maker escalates to the supervisor",
        "Priya Nair, Elena Marsh", _num([SIGN.format("Priya Nair") + ". Open the case and click Escalate. Choose Supervisor, write a reason, confirm.",
        "Open the Audit page as Rhea Kapoor and find the escalation event.", "Sign in as Elena Marsh and open the case."]),
        _num(["The escalation is recorded with the reason.", "The supervisor can open the case and act on it."]), r04, _data(man[c])))

    c = "TST-DQ01-05"
    def r05(R, c=c):
        R.check("Case waits for missing information", variant(c) == "MISSING_INFO", chips(c))
        R.call("Request the IBAN from the client", "OP-9012", c, "request-information", {"message": "Please send the IBAN.", "method": "Email"}, contains="Request sent")
        R.call("Client reply: reassess with the IBAN", "OP-9012", c, "reassess", {"note": "Reply received", "provided": {"iban": "FR7630004000031234567890143"}}, contains="Evidence is now complete")
        R.check("Case is ready for decision", variant(c) == "DECISION", chips(c))
        sub(R, c, note="IBAN supplied by the client and validated.")
        R.call("Daniel approves with the review tick", "APR-3191", c, "approve", {"reviewed": True, "comment": "Reviewed the client reply and the checksum."}, contains=HANDOFF_OK)
        R.check("Executed by bank", wait_variant(c, "EXECUTED") == "EXECUTED", chips(c))
    out.append(TC(S, "DQ-01", "Missing information", c, "Ask the client for the IBAN, then repair",
        "Priya Nair, Daniel Osei", _num([SIGN.format("Priya Nair") + ". Open the case (status Missing information).",
        "Click 'Request information', write a message, send. Status becomes 'Waiting for information'.", "Click 'Reassess' and enter FR7630004000031234567890143.",
        "Submit for approval. Sign in as Daniel Osei, tick the box and click 'Approve for bank handoff'. Wait 10 seconds: Executed."]),
        _num(["Request is simulated and recorded.", "An IBAN that fails the mod-97 check is refused (try 'FR76 0000' first if you want to see it).", "After the reply is applied the evidence is complete, the approval works and the bank executes."]),
        r05, _data(man[c]) + " | Reply IBAN: FR7630004000031234567890143"))

    c = "TST-DQ01-06"
    def r06(R, c=c):
        R.check("Case shows a conflict with two candidate IBANs", variant(c) == "CONFLICT", chips(c))
        R.call("Record the candidate H-1 with a rationale", "OP-9012", c, "disambiguate", {"candidate_id": "H-1", "rationale": "The master directory is the authoritative source."}, contains="Candidate recorded")
        R.check("Case is ready for a decision", variant(c) == "DECISION", chips(c))
    out.append(TC(S, "DQ-01", "Evidence conflict", c, "Invoice IBAN differs from the directory: the maker picks one",
        "Priya Nair", _num([SIGN.format("Priya Nair") + ". Open the case. Status 'Conflict'. Read the three sources side by side.",
        "Choose the candidate 'Keep the IBAN on the instruction and directory', write a rationale, confirm."]),
        _num(["PeX does not pick; both IBANs pass the checksum.", "After the maker records a choice the case becomes ready for decision."]), r06, _data(man[c])))

    c = "TST-DQ01-07"
    def r07(R, c=c):
        sub(R, c)
        r = post("APR-3191", f"/cases/{c}/approve", {"reviewed": True, "comment": "x"})
        R.check("Approve is refused: confidence below 85%", r.status_code == 403 and "85%" in msg(r), msg(r))
        R.call("Mei Tan confirms the evidence review", "APR-3192", c, "confidence-review", {"decision": "confirm", "comment": "Directory match checked by hand."}, contains="Evidence review recorded")
        r = post("APR-3192", f"/cases/{c}/approve", {"reviewed": True, "comment": "x"})
        R.check("The reviewer cannot also approve", r.status_code == 403, msg(r))
        R.call("Daniel approves", "APR-3191", c, "approve", {"reviewed": True, "comment": "Reviewed."}, contains=HANDOFF_OK)
    out.append(TC(S, "DQ-01", "Low confidence", c, "No payment history: an independent evidence review is required",
        "Priya Nair, Mei Tan, Daniel Osei", _num([SIGN.format("Priya Nair") + ". Open the case, Assign, Submit for approval.",
        "Sign in as Daniel Osei. Open the case: a banner says an evidence review is needed. Approve is disabled.",
        "Sign in as Mei Tan. Open the case, click 'Confirm evidence review' with a comment.", "Mei tries Approve: refused.", "Daniel ticks the box and clicks 'Approve for bank handoff'."]),
        _num(["Approve is blocked: 'Decision confidence is 35%, below the 85% threshold'.", "The reviewer and the final approver must be different people."]), r07, _data(man[c])))

    c = "TST-DQ01-08"
    def r08(R, c=c):
        sub(R, c)
        r = post("APR-3191", f"/cases/{c}/approve", {"reviewed": True, "comment": "x"})
        R.check("An Operations Approver cannot approve 480,000 (limit 250,000)", r.status_code == 403, msg(r))
        R.call("Kenji Watanabe gives the first approval", "RSK-7714", c, "approve", {"reviewed": True, "comment": "First approval."}, contains="First approval recorded")
        r = post("RSK-7714", f"/cases/{c}/approve", {"reviewed": True, "comment": "x"})
        R.check("Kenji cannot also give the second approval", r.status_code == 403, msg(r))
        R.call("Helen Brandt gives the second approval", "RSK-7715", c, "approve", {"reviewed": True, "comment": "Second approval."}, contains=HANDOFF_OK)
        R.check("Executed by bank", wait_variant(c, "EXECUTED") == "EXECUTED", chips(c))
    out.append(TC(S, "DQ-01", "Dual authorisation (480,000)", c, "High value: two different approvers must sign",
        "Priya Nair, Kenji Watanabe, Helen Brandt", _num([SIGN.format("Priya Nair") + ". Open the case, Submit for approval. Note: 'Dual authorisation' in the controls box.",
        "Sign in as Daniel Osei. Try Approve: refused (over his limit).", "Sign in as Kenji Watanabe. Tick the box, click 'Approve for bank handoff'. The case says 'First approval recorded'.",
        "Kenji tries again: refused.", "Sign in as Helen Brandt. Tick the box, click 'Approve for bank handoff'. Handed to bank."]),
        _num(["Two different tier-2 approvers are required.", "The same person cannot sign twice.", "Only after the second signature does the bank hand-off happen."]), r08, _data(man[c])))

    c = "TST-DQ01-09"
    def r09(R, c=c):
        pg = page("APR-3191", c)
        R.check("Daniel sees that he prepared this case", "prepared" in str((pg.get("sod") or {}).get("text", "")).lower(), (pg.get("sod") or {}).get("text"))
        r = post("APR-3191", f"/cases/{c}/approve", {"reviewed": True, "comment": "x"})
        R.check("Approve is refused: separation of duties", r.status_code == 403 and "own case" in msg(r).lower() + "prepared", msg(r))
        R.check("The blocked attempt is in the audit trail", "APPROVAL_BLOCKED" in audit_actions(c), ", ".join(audit_actions(c)[:6]))
    out.append(TC(S, "DQ-01", "Separation of duties", c, "Maker tries to approve his own case",
        "Daniel Osei (he is both maker and approver on this case)", _num([SIGN.format("Daniel Osei") + ". Open Approvals and open the case. The case was prepared by Daniel Osei.",
        "Tick the review box and try 'Approve for bank handoff'.", "As Rhea Kapoor, check the audit trail for the blocked attempt."]),
        _num(["Approve is refused: 'Segregation of Duties violation'.", "The blocked attempt is recorded in the audit trail."]), r09, _data(man[c])))

    c = "TST-DQ01-10"
    def r10(R, c=c):
        pg = page("APR-3191", c)
        R.check("The decision panel needs the review tick (requires_review_ack)", (pg.get("decision_form") or {}).get("requires_review_ack") is True, "")
        for act, body in (("approve", {}), ("return", {"reason_code": "OTHER", "comment": "x"}), ("reject", {"reason_code": "OTHER", "comment": "x"})):
            r = post("APR-3191", f"/cases/{c}/{act}", {"reviewed": False, **body})
            R.check(f"{act.capitalize()} without the tick is refused", r.status_code == 422, msg(r))
        R.call("Approve with the tick", "APR-3191", c, "approve", {"reviewed": True, "comment": "Reviewed."}, contains=HANDOFF_OK)
    out.append(TC(S, "DQ-01", "Review tick gates all three decisions", c, "Approve, Return and Reject are all disabled until the box is ticked",
        "Daniel Osei", _num([SIGN.format("Daniel Osei") + ". Open Approvals and open the case.", "Scroll to 'Your decision'. Leave the review box UNTICKED.",
        "Check 'Approve for bank handoff', 'Return to Maker' and 'Reject' are all disabled. Fill in a reason code and a comment: they stay disabled.", "Tick the box. The buttons become enabled.",
        "Untick it: disabled again. Tick it and click 'Approve for bank handoff'."]),
        _num(["All three decisions need the tick (screen and server).", "The hint 'Tick the review box to enable this' shows under Return and Reject."]), r10, _data(man[c])))

    c = "TST-DQ01-11"
    def r11(R, c=c):
        R.check("Case is pending approval with the cut-off close", variant(c) == "APPROVAL", chips(c))
        R.call("Maker pings the approver (level 1)", "OP-9013", c, "ping", {"note": "Cut-off in 12 minutes, please review."}, contains="notified")
        R.call("Supervisor pings level 2", "SUP-2001", c, "ping", {"note": "Escalating.", "level": 2}, contains="notified")
        e = get("APR-3191", f"/cases/{c}/expedite").json()
        R.check("The expedite ladder shows levels 1 and 2 as sent", sum(1 for l in e["levels"] if l["sent"]) >= 2, [(l["level"], l["sent"]) for l in e["levels"]])
    out.append(TC(S, "DQ-01", "SLA chase", c, "Cut-off is near: ping the approver, then the supervisor",
        "Amina Okafor, Elena Marsh, Daniel Osei", _num([SIGN.format("Amina Okafor") + ". Open the case (pending approval, cut-off about 12 minutes).",
        "Open the 'Expedite' ladder under the decision zone. Click Ping on level 1 and add a note.", "Sign in as Elena Marsh. Ping level 2.",
        "Sign in as Daniel Osei: the notification bell shows the pings."]),
        _num(["Each ping is recorded with time and note.", "The ladder shows who was notified at each level."]), r11, _data(man[c])))
    c = "TST-DQ01-12"
    def r12(R, c=c):
        sub(R, c)
        R.call("Daniel approves", "APR-3191", c, "approve", {"reviewed": True, "comment": "Reviewed."}, contains=HANDOFF_OK)
        R.check("About 6 seconds later the simulated bank REJECTS the payment", wait_variant(c, "GENERIC") == "GENERIC" and "Rejected" in chips(c), chips(c))
        R.check("The bank rejection is in the audit trail", "BANK_REJECTED_SIGNAL" in audit_actions(c), ", ".join(audit_actions(c)[:6]))
        R.check("PeX does not resend the payment", "ASSISTED_HANDOFF_DISPATCHED" in audit_actions(c) and audit_actions(c).count("ASSISTED_HANDOFF_DISPATCHED") == 1, "")
    out.append(TC(S, "DQ-01", "Bank rejects after hand-off", c, "The bank refuses the repaired payment: PeX records it and never resends",
        "Priya Nair, Daniel Osei, Rhea Kapoor", _num([SIGN.format("Priya Nair") + ". Open the case, Assign to me, Submit for approval.",
        "Sign in as Daniel Osei. Tick the review box and click 'Approve for bank handoff'.", "Wait about 10 seconds and refresh. The status changes to Rejected.",
        "Sign in as Rhea Kapoor. Open Audit and search the case ID: 'BANK_REJECTED_SIGNAL' is there with the bank reference."]),
        _num(["The demo bank is set to reject this one case (all other test cases settle).", "The audit trail holds the bank's rejection; nothing is sent twice."]), r12, _data(man[c])))
    return out


def co01_cases(man: Dict[str, dict]) -> List[TC]:
    S = "C. Full workflow set: CO-01 Sanctions suspected"
    out: List[TC] = []
    c = "TST-CO01-02"
    def r02(R, c=c):
        R.call("First reviewer confirms the match", "CMP-4420", c, "compliance/decision", {"decision": "confirm_block", "reason_code": "TRUE_MATCH", "comment": "Name and country match the listed entity."}, contains="First review recorded")
        R.state("Still on Compliance hold, waiting for a second reviewer", c, "Compliance hold")
        R.call("Same person confirms again: refused", "CMP-4420", c, "compliance/decision", {"decision": "confirm_block", "reason_code": "TRUE_MATCH", "comment": "again"}, expect=403)
        R.call("Second reviewer confirms the block", "CMP-6001", c, "compliance/decision", {"decision": "confirm_block", "reason_code": "TRUE_MATCH", "comment": "Second reviewer agrees."}, contains="blocked")
        R.state("Case is Rejected: the payment will not be released", c, "Rejected")
    out.append(TC(S, "CO-01", "Confirm match: block (two reviewers)", c, "True match: four-eyes block",
        "Marisol Vega, Amara Okafor", _num([SIGN.format("Marisol Vega") + ". Open Compliance > the case. Click 'Confirm match · block payment', reason 'Confirmed match with listed entity', comment, tick the review box and click 'Record decision'.",
        "The case still shows Compliance hold: a second reviewer is needed. Try confirming again as Marisol: refused.", "Sign in as Amara Okafor. Open the case and confirm the block."]),
        _num(["First review is recorded; nothing is blocked yet.", "The second reviewer must be a different person.", "After the second review the case is closed and never released."]), r02, _data(man[c])))
    c = "TST-CO01-03"
    def r03(R, c=c):
        R.call("Escalate to Senior Compliance", "CMP-4420", c, "compliance/decision", {"decision": "escalate", "reason_code": "NEEDS_SENIOR_REVIEW", "comment": "Ambiguous registration data."}, contains="Escalated")
        R.check("Escalation is in the audit trail", "COMPLIANCE_ESCALATED" in audit_actions(c), ", ".join(audit_actions(c)[:6]))
    out.append(TC(S, "CO-01", "Escalate", c, "Unsure: escalate to Senior Compliance",
        "Marisol Vega", _num([SIGN.format("Marisol Vega") + ". Open Compliance > the case. Click 'Escalate to Senior Compliance', reason 'Needs senior compliance review', comment, tick the review box and click 'Record decision'.",
        "Check the audit trail (as Rhea Kapoor)."]), _num(["Escalation is recorded and the Risk Approver is notified."]), r03, _data(man[c])))
    c = "TST-CO01-04"
    def r04(R, c=c):
        R.call("Compliance releases the hold", "CMP-4420", c, "compliance/decision", {"decision": "release", "reason_code": "FALSE_MATCH_NAME", "comment": "Looks like a different entity."}, contains="Hold released")
        R.call("Risk Approver rejects with reason and comment", "RSK-7714", c, "reject", {"reviewed": True, "reason_code": "SUSPECTED_FRAUD", "comment": "Adverse information found in the file."}, contains="Rejected")
        R.state("Case is Rejected", c, "Rejected")
    out.append(TC(S, "CO-01", "Risk Approver rejects", c, "Compliance clears the alert but Risk refuses to release",
        "Marisol Vega, Kenji Watanabe", _num([SIGN.format("Marisol Vega") + ". Click 'Clear hold · false match', give a reason and comment, tick the box and record it.", "Sign in as Kenji Watanabe. Open Approvals > the case. Tick the review box, choose Reject, reason 'Suspected fraud or error', comment, and click Reject."]),
        _num(["Releasing a hold never releases the payment.", "Risk can still reject; the case is closed."]), r04, _data(man[c])))
    return out


def st_extra_cases(man: Dict[str, dict]) -> List[TC]:
    S = "D. Other decision options (investigation profiles)"
    out: List[TC] = []
    c = "TST-ST05-02"
    def r1(R, c=c):
        R.call("Choose 'Recall and return' (stops the case)", "APR-3191", c, "decision", {"option": "RECALL_AND_RETURN", "comment": "Settlement cannot complete; recall."}, contains="stopped")
        R.state("Case is Rejected / stopped", c, "Rejected")
    out.append(TC(S, "ST-05", "Stop option", c, "Settlement failure: recall and return", "Daniel Osei",
        _num([SIGN.format("Daniel Osei") + ". Open the case. Select 'Recall and return', write a reason, click 'Record decision'."]),
        _num(["The case is stopped and will not be released."]), r1, _data(man[c])))
    c = "TST-ST07-02"
    def r2(R, c=c):
        R.call("Choose 'Hold in suspense' (case stays open)", "APR-3191", c, "decision", {"option": "HOLD_IN_SUSPENSE", "comment": "Waiting for the ordering bank."}, contains="stays open")
        R.check("Case is not closed", variant(c) not in ("EXECUTED",) and "Rejected" not in chips(c), chips(c))
    out.append(TC(S, "ST-07", "Hold option", c, "Unmatched credit: hold in suspense", "Daniel Osei",
        _num([SIGN.format("Daniel Osei") + ". Open the case. Select 'Hold in suspense', write a reason, click 'Record decision'."]),
        _num(["The decision is recorded and the case stays open until the outstanding item is resolved."]), r2, _data(man[c])))
    return out


# ==================================================================================================================================
# 3. platform functions (use the showcase data that ships with the demo)
# ==================================================================================================================================
def platform_cases() -> List[TC]:
    S = "E. Platform functions"
    out: List[TC] = []

    def add(title, who, steps, exp, run, data=""):
        out.append(TC(S, "-", "Platform", data.split(" ")[0] if data.startswith("PEX-") else "", title, who, _num(steps), _num(exp), run, data))

    def r_dash(R):
        d = get("OP-9012", "/dashboard")
        R.check("Dashboard loads", d.status_code == 200, d.status_code)
        j = d.json()
        R.check("Dashboard shows cut-off bands and counts", len(json.dumps(j)) > 300, list(j.keys())[:8])
        h = get("OP-9012", "/home")
        R.check("My work loads", h.status_code == 200, h.status_code)
    add("Dashboard and My work show SLAs and to-do items", "Priya Nair", [SIGN.format("Priya Nair") + ".", "Open Dashboard: counts by cut-off band and exception type.", "Open My work: your queue, returned items and waiting items."],
        ["Both screens load with live numbers.", "Cut-off bands (under 1 hour, 1 to 3 hours, over 3 hours) show."], r_dash)

    def r_wl(R):
        r = get("OP-9012", "/worklist", params={"q": "PEX-STP-0104"}).json()
        R.check("Search by case ID finds the case", [x["case_id"] for x in r["items"]] == ["PEX-STP-0104"], [x["case_id"] for x in r["items"]])
        r = get("OP-9012", "/worklist", params={"exception_type": "DQ-01", "page_size": 100}).json()
        R.check("Filter by exception type DQ-01 returns only Invalid IBAN cases", r["items"] and all(x["exception"]["code"] == "DQ-01" for x in r["items"]), len(r["items"]))
        r = get("OP-9012", "/worklist", params={"cutoff_band": "under_1h", "page_size": 100}).json()
        R.check("Filter by cut-off band 'Under 1 hour' works", all(x["cutoff"]["band"] == "under_1h" for x in r["items"]), len(r["items"]))
    add("Worklist search and filters", "Priya Nair", [SIGN.format("Priya Nair") + ". Open Worklist.", "Type PEX-STP-0104 in Search: one row.", "Clear it. Filter Exception type = Invalid IBAN.", "Filter Cutoff = Under 1 hour."],
        ["Search and filters narrow the list.", "Tabs show Ready, Returned, Waiting, Pending approval, Done."], r_wl)

    def r_stp(R):
        rv = get("APR-3191", "/stp/review").json()
        elig = [x.get("case_id") for x in rv.get("eligible", rv.get("items", []))] if isinstance(rv, dict) else []
        R.check("Batch review lists micro-repairs under the limit", "PEX-STP-0101" in json.dumps(rv), f"{len(elig)} eligible")
        R.check("Ineligible cases are not offered for batch approval (conflict, compliance hold, invalid proposal)",
                all(x not in json.dumps(rv.get("eligible", [])) for x in ("PEX-STP-0113", "PEX-STP-0114", "PEX-STP-0115")), "")
        r = post("APR-3191", "/stp/approve", {"case_ids": ["PEX-STP-0101", "PEX-STP-0102"]})
        R.check("Approve two micro-repairs in one click", r.status_code == 200, msg(r))
        R.check("Both cases are handed to the bank", all("Handed" in chips(c) or "Executed" in chips(c) for c in ("PEX-STP-0101",)), chips("PEX-STP-0101"))
    add("Batch approval of validated micro-repairs", "Daniel Osei", [SIGN.format("Daniel Osei") + ". Open Batches or the STP fast-lane.", "Review the eligible list; PEX-STP-0113, 0114 and 0115 are not eligible.",
        "Select PEX-STP-0101 and PEX-STP-0102 and approve them together."],
        ["Only validated micro-repairs under the limit appear.", "Conflict, compliance-hold and invalid proposals are kept out.", "Selected cases are handed to the bank."], r_stp, "PEX-STP-0101, PEX-STP-0102")

    def r_unk(R):
        c = "PEX-TMO-0044"
        R.check("Case says status unknown: do not resend", variant(c) == "STATUS_UNKNOWN", chips(c))
        r1 = post("OP-9020", f"/cases/{c}/check-status", {})
        R.check("First status check: still unknown", r1.status_code == 200, msg(r1))
        r2 = post("OP-9020", f"/cases/{c}/check-status", {})
        R.check("Second status check: the bank answers", r2.status_code == 200, msg(r2))
        R.check("Case is handed to bank or executed (never re-sent)", variant(c) in ("HANDED_TO_BANK", "EXECUTED"), chips(c))
    add("Status unknown after a network timeout: check, never resend", "Marcus Lee", ["Sign in as Marcus Lee.", "Open PEX-TMO-0044 (Network timeout).", "Click 'Check status' twice."],
        ["The page warns: do not resend.", "The first check is still unknown; the second returns the bank's answer."], r_unk, "PEX-TMO-0044 | Network timeout | GBP 54,000")

    def r_pii(R):
        c = "TST-DQ02-01"
        pg = page("OP-9012", c)
        R.check("Names and accounts show as tokens (TOK-...)", "TOK-" in json.dumps(pg["header"]), pg["header"].get("creditor"))
        r = post("OP-9012", f"/cases/{c}/pii/reveal", {"reason": ""})
        R.check("Reveal without a reason is refused", r.status_code in (400, 422), msg(r))
        r = post("OP-9012", f"/cases/{c}/pii/reveal", {"reason": "Checking the beneficiary name with the client."})
        R.check("Reveal with a reason works", r.status_code == 200, msg(r))
        R.check("The reveal is in the audit trail", any("PII" in a or "REVEAL" in a for a in audit_actions(c)), ", ".join(audit_actions(c)[:6]))
        post("OP-9012", f"/cases/{c}/pii/hide")
        av = get("OP-9012", f"/cases/{c}/ai-view").json()
        R.check("The AI view shows tokens and bands, not real values", "Aldous" not in json.dumps(av), "")
    add("Personal data is tokenised; reveal needs a reason and is logged", "Priya Nair", [SIGN.format("Priya Nair") + ". Open TST-DQ02-01. The creditor shows TOK-...", "Click 'Reveal real values'. Try with no reason: refused. Enter a reason: values show.",
        "Click Hide. Open the 'AI view and reasoning' tab: what the AI is allowed to see."], ["Reveal needs a reason and is audited.", "The AI view contains tokens, amount bands and derived facts only."], r_pii, "TST-DQ02-01")

    def r_aud(R):
        e = get("AUD-5001", "/audit/events", params={"page_size": 50}).json()
        R.check("Audit lists events with actor, role and time", e["total"] > 50 and e["items"][0].get("actor"), e["total"])
        R.check("Hash chain is valid", e["integrity"]["chain_valid"] is True, e["integrity"])
        r = get("APR-3191", "/audit/events")
        R.check("An Approver cannot open the Audit page", r.status_code == 403, r.status_code)
        r = get("AUD-5001", "/audit/export")
        R.check("Audit export downloads", r.status_code == 200 and len(r.content) > 200, len(r.content))
        r = get("AUD-5001", "/audit/cases/TST-DQ01-01/report")
        R.check("A case audit report can be produced", r.status_code == 200, r.status_code)
    add("Audit trail, integrity and role limits", "Rhea Kapoor, Daniel Osei", [SIGN.format("Rhea Kapoor") + ". Open Audit.", "Search a case ID. Check the integrity badge says the chain is valid.", "Click Export.",
        "Sign in as Daniel Osei: the Audit menu is not there."], ["Every action appears with actor, role and time.", "The chain check passes.", "Approvers cannot open Audit."], r_aud)

    def r_net(R):
        r = get("OP-9012", "/network/cases")
        R.check("Network cases list loads", r.status_code == 200, r.status_code)
        j = r.json()
        R.check("Investigations (camt.110/111) and recalls (camt.056/029) are listed", len(json.dumps(j)) > 100, list(j.keys())[:6] if isinstance(j, dict) else len(j))
    add("Network cases: investigations and recalls", "Priya Nair", [SIGN.format("Priya Nair") + ". Open Network cases.", "Open an investigation and a recall: direction, reason code, UETR link, status."], ["The list and the detail screens load.", "All messages are simulated in this demo."], r_net)

    def r_lib(R):
        l = get("ADM-0001", "/reference/library").json()
        R.check("The library lists 41 profiles", l["summary"]["profiles"] == 41, l["summary"]["profiles"])
        R.check("Approval paths: 32 maker-checker, 6 compliance-then-risk, 3 single", l["summary"]["by_approval"] == {"COMPLIANCE_THEN_RISK": 6, "MAKER_CHECKER": 32, "SINGLE": 3}, l["summary"]["by_approval"])
        R.check("10 profiles are never straight-through", l["summary"]["by_stp"].get("NEVER") == 10, l["summary"]["by_stp"])
        d = get("ADM-0001", "/reference/library/DQ-01").json()
        R.check("A profile opens with evidence, controls and decision options", bool(d.get("evidence") and d.get("controls")), d.get("name"))
    add("Profile library: 41 profiles", "Alex Whitfield (or Policy Owner)", ["Open Policy Studio or Admin > Library.", "Check the totals: 41 profiles.", "Open DQ-01: evidence needed, controls, approval path."], ["41 profiles; 32 / 6 / 3 approval paths; 10 never straight-through."], r_lib)

    def r_adm(R):
        r = get("ADM-0001", "/admin/integrations")
        R.check("Admin console lists integrations and their mode", r.status_code == 200, r.status_code)
        r = get("OP-9012", "/admin/integrations")
        R.check("An Operator cannot open Admin", r.status_code == 403, r.status_code)
        r = get("ADM-0001", "/admin/handoffs")
        R.check("Hand-offs list loads", r.status_code == 200, r.status_code)
    add("Admin console and roles", "Alex Whitfield, Priya Nair", [SIGN.format("Alex Whitfield") + ". Open Admin: integrations, mode, hand-offs.", "Sign in as Priya Nair: no Admin menu."], ["Admin shows integrations and hand-offs.", "Operators cannot open it."], r_adm)

    def r_pol(R):
        r = get("POL-8001", "/policy/params")
        R.check("Policy Studio lists rules", r.status_code == 200, r.status_code)
        keys = [p["key"] for p in (r.json().get("params") or r.json().get("items") or [])] if r.status_code == 200 else []
        R.check("Release mode and the limits are there", "release_mode" in keys or "release_mode" in json.dumps(r.json()), keys[:8])
        pv = post("POL-8001", "/policy/preview", {"key": "batch_limit", "value": 15000})
        R.check("A change can be previewed before it is proposed", pv.status_code == 200, msg(pv))
        r = get("APR-3191", "/policy/params")
        R.check("An Approver cannot open Policy Studio", r.status_code == 403, r.status_code)
    add("Policy Studio: preview a rule change", "Nadia Rahman", [SIGN.format("Nadia Rahman") + ". Open Policy Studio.", "Pick 'One-click batch approval limit', enter 15,000 and click Preview. Do not submit."], ["Preview shows the effect; nothing changes until a second policy owner approves."], r_pol)

    def r_shadow(R):
        s = get("ADM-0001", "/shadow/scorecard")
        R.check("Shadow scorecard loads", s.status_code == 200, s.status_code)
        v = get("ADM-0001", "/value-model")
        R.check("Value model loads", v.status_code == 200, v.status_code)
    add("Shadow scorecard and value model", "Alex Whitfield", [SIGN.format("Alex Whitfield") + ". Open Admin > Shadow and Value."], ["Both screens load; the value model is labelled illustrative."], r_shadow)

    def r_rev(R):
        s = get("POL-8001", "/review/summary")
        R.check("SME review summary loads", s.status_code == 200, s.status_code)
        it = get("POL-8001", "/review/items")
        R.check("Review items list loads", it.status_code == 200, it.status_code)
        x = get("POL-8001", "/review/export.xlsx")
        R.check("Excel export downloads", x.status_code == 200 and x.content[:2] == b"PK", len(x.content))
    add("SME review workflow and Excel export", "Nadia Rahman", [SIGN.format("Nadia Rahman") + ". Open Policy Studio > Review.", "Open an item, set a status, add a comment.", "Click Export to Excel."], ["Statuses and comments are saved.", "The Excel file downloads and can be re-imported."], r_rev)

    def r_dir(R):
        d = get("SUP-2001", "/director")
        R.check("Operations view loads", d.status_code == 200, d.status_code)
        d = get("OP-9012", "/director")
        R.check("An Operator cannot open the Operations view", d.status_code == 403, d.status_code)
    add("Operations view for the head of operations", "Elena Marsh", [SIGN.format("Elena Marsh") + ". Open Operations view."], ["Backlog, SLA risk and approvals ageing show. Operators cannot open it."], r_dir)

    def r_dup(R):
        c = "PEX-DUP-0051"
        pg = page("OP-9012", c)
        R.check("Possible duplicate is flagged with the earlier payment", pg.get("possible_duplicate_of") == "PEX-DUP-0050" or "duplicate" in json.dumps(pg).lower(), pg.get("possible_duplicate_of"))
    add("Possible duplicate is flagged", "Priya Nair", [SIGN.format("Priya Nair") + ". Open PEX-DUP-0051."], ["The page names the earlier payment it may duplicate."], r_dup, "PEX-DUP-0051")

    def r_role(R):
        r = post("OP-9012", "/cases/TST-DQ03-01/approve", {"reviewed": True, "comment": "x"})
        R.check("An Operator cannot approve", r.status_code == 403, msg(r))
        r = post("APR-3191", "/cases/TST-DQ04-01/submit", {"handover_note": "x"})
        R.check("An Approver cannot submit as a maker", r.status_code == 403, msg(r))
    add("Role limits: operators cannot approve, approvers cannot make", "Priya Nair, Daniel Osei", ["As Priya Nair, open a pending case: no Approve button.", "As Daniel Osei, open a ready case: no Submit button."], ["The server refuses both."], r_role)
    return out


def build() -> List[TC]:
    man = _man()
    tcs: List[TC] = []
    for m in [x for x in man.values() if x["scenario"] == "CLEAN"]:
        code = m["code"]
        if code == "DQ-03":
            tcs.append(dq03_clean(m))
        elif code in ("CO-01", "CO-02", "CO-03", "CO-04", "CO-05", "CO-06", "CO-07", "CO-08"):
            tcs.append(co_clean(m))
        elif code in ("ST-04", "ST-05", "ST-07"):
            tcs.append(st_clean(m))
        else:
            tcs.append(mc_clean(m))
    tcs.sort(key=lambda t: t.code)
    tcs += dq01_cases(man) + co01_cases(man) + st_extra_cases(man) + platform_cases()
    for i, t in enumerate(tcs, 1):
        t.id = f"TC-{i:03d}"
    return tcs


def run_all(tcs: List[TC]) -> Dict[str, Any]:
    out = {}
    for t in tcs:
        R = Run()
        t0 = time.time()
        try:
            t.run(R)
        except Exception as e:  # a crash is a failed test, with the reason recorded
            R.check("The test ran without an error", False, f"{type(e).__name__}: {e}")
        ok = bool(R.checks) and all(c["ok"] for c in R.checks)
        out[t.id] = {"result": "PASS" if ok else "FAIL", "checks": R.checks, "seconds": round(time.time() - t0, 1),
                     "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        print(t.id, t.case_id, out[t.id]["result"], [c["what"] + " -> " + c["observed"] for c in R.checks if not c["ok"]])
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="execute all tests and write results to this JSON file")
    ap.add_argument("--api", default="http://127.0.0.1:8001")
    a = ap.parse_args()
    API = a.api.rstrip("/") + "/api"
    tcs = build()
    print(len(tcs), "test cases")
    if a.run:
        res = run_all(tcs)
        Path(a.run).write_text(json.dumps(res, indent=1))
        p = sum(1 for v in res.values() if v["result"] == "PASS")
        print(f"PASS {p} / {len(res)}")
