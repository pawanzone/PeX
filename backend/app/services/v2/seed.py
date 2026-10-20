"""UI v2 demo seed: the named showcase cases (all variants), the STP micro-repair batch, and extension data.

Idempotent: a marker case (PEX-STP-0101) tells us the seed already ran. Cutoffs are relative to seed time.
All IBANs are real MOD-97 valid (or deliberately invalid where the story needs it, verified at build time).
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.config import settings
from app.db.models import CaseModel
from app.services.data_loader import repo
from app.services.v2 import ext as xt
from app.services.v2 import zone
from app.services.v2.core import ext_store, now, iso

log = logging.getLogger("pex.v2.seed")
MARKER = "PEX-STP-0101"


def make_iban(cc: str, bban: str) -> str:
    num = int("".join(str(int(ch, 36)) for ch in (bban + cc + "00")))
    return f"{cc}{98 - num % 97:02d}{bban}"


def _corrupt(iban: str) -> str:
    """Swap two adjacent differing digits near the end until MOD-97 fails."""
    s = list(iban)
    for i in range(len(s) - 2, 6, -1):
        if s[i].isdigit() and s[i + 1].isdigit() and s[i] != s[i + 1]:
            t = s[:]
            t[i], t[i + 1] = t[i + 1], t[i]
            c = "".join(t)
            if not xt.iban_valid(c):
                return c
    raise RuntimeError("cannot corrupt")


def _profile(code: str):
    from app.services.file_watcher import PROFILE_CODE_TO_ENUM
    from app.services.data_loader import get_domain_for_profile
    en = PROFILE_CODE_TO_ENUM[code]
    return en.value, get_domain_for_profile(en).value


def _drop_existing(case_id: str):
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        db.query(CaseModel).filter(CaseModel.case_id == case_id).delete()
        db.commit()
    finally:
        db.close()
    repo._case_cache.pop(case_id, None)


def _ev(rid, check, result, source, auth, status, label, ts, kind=None, item=None):
    return xt.row(rid, check, result, source, auth, status, label, ts, kind=kind, item=item)


def _case(case_id: str, code: str, amount: float, ccy: str, rail: str, status: str, queue: str, cp: str, cc: str, iban: str,
          bic: str, created_min: int, cutoff_min: int, reason: str, maker: Optional[str] = None, dispatch: Optional[Dict[str, Any]] = None,
          approval_history: Optional[list] = None, debtor: str = "Ordering Corp", cred_acc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    t = now()
    created = t - timedelta(minutes=created_min)
    profile, domain = _profile(code)
    d = {
        "case_id": case_id, "payment_id": "PMT-" + case_id[4:], "uetr": f"UETR-2026-{case_id[4:]}-V2", "payment_ref": "PAY-" + case_id[4:],
        "profile": profile, "domain": domain, "secondary_profiles": [], "error_code": f"ERR_{code.replace('-', '_')}", "reason": reason,
        "amount": float(amount), "currency": ccy, "payment_rail": rail,
        "debtor_party": {"party_name": debtor, "country": "GB"}, "debtor_account": {"account_number": "GB11APEX99887700" + case_id[-4:]},
        "creditor_party": {"party_name": cp, "country": cc}, "creditor_account": cred_acc or {"iban": iban, "bank_bic": bic},
        "queue": queue, "status": status, "severity": "HIGH" if amount >= 250000 else "MEDIUM", "priority": "HIGH" if amount >= 250000 else "NORMAL",
        "sla_due_at": iso(t + timedelta(minutes=cutoff_min)), "dual_auth_required": amount >= 250000,
        "ai_confidence": 0.93, "created_at": iso(created), "settled_at": None, "approval_history": approval_history or [],
        "audit_timeline": [{"step_index": 1, "timestamp": iso(created), "actor_name": "PeX Ingestion Gateway", "actor_role": "SYSTEM", "badge_color": "slate",
                            "action_title": "Exception ingested", "icon": "📥", "summary": f"{case_id} received and canonicalised."}],
        "guided_questions": [], "expedite_ping": None, "maker_id": maker,
    }
    d.update(dispatch or {})
    _drop_existing(case_id)
    repo.save_case(d)
    return d


def _log(case: Dict[str, Any], stage: str, actor: str, role: str, action: str, text: str, tags: Optional[List[str]] = None):
    repo.log_audit_event(case_id=case["case_id"], correlation_id=case["uetr"], stage_name=stage, actor_id=actor, actor_role=role,
                         action_name=action, details="[DEMO_ONLY] " + zone.seal_text(text, case), control_tags=(tags or []) + ["DEMO_ONLY"],
                         amount=case["amount"], currency=case["currency"])


def _ingest(case, extra: Optional[list] = None):
    _log(case, "INGESTION", "SYS-INGEST", "SYSTEM", "INGEST_EXCEPTION", f"Payment exception {case['case_id']} ingested and canonicalised.", ["Schema valid"])
    for e in (extra or []):
        _log(case, *e)


def _base_ext(case, rows, state, **kw) -> Dict[str, Any]:
    t = now()
    d = {"v": xt.EXT_VERSION, "source": "seed", "cutoff_at": case["sla_due_at"], "assignee": None,
         "counterparty": case["creditor_party"]["party_name"], "debtor": case["debtor_party"]["party_name"],
         "evidence": rows, "evidence_state": state, "change": None, "conflict": None, "last_change_at": iso(t - timedelta(minutes=12))}
    d.update(kw)
    return d


def _put(case_id: str, e: Dict[str, Any]):
    ext_store.put(case_id, e, persist=True)


def seed_named() -> List[str]:
    t = now()
    ids: List[str] = []
    ts = lambda m: iso(t - timedelta(minutes=m))
    # Evidence rows come from the zone: the simulated connectors answer with real-looking values, the zone checks them and
    # returns tokens and derived facts only (same interface a real connector will use).
    ok_rows = lambda m, case, bad_iban, good_iban, extra=(): [
        zone.run("checksum", "ev-1", case, {"checksum": {"original": bad_iban, "proposed": good_iban}}, ts(m), source="Payment instruction"),
        _ev("ev-2", "Bank directory", "Bank code resolves to the named institution", "Bank directory", "Authoritative", "agree", "Agree", ts(m), kind="directory"),
        zone.run("history", "ev-3", case, {"checksum": {"original": bad_iban, "proposed": good_iban}, "history": {"count": 3, "same_account": 3}}, ts(m)),
        zone.run("vop", "ev-4", case, {"account_holder": case["creditor_party"]["party_name"]}, ts(m)),
        zone.run("core", "ev-5", case, {"account": {"status": "OPEN"}}, ts(m)),
        *extra]

    # ---- PEX-INV-0001: invalid IBAN, validated, submitted by Priya Nair with a handover note --------------------------------
    good = make_iban("GB", "NWBK60161331926819")
    bad = _corrupt(good)
    c = _case("PEX-INV-0001", "DQ-01", 8650, "GBP", "CHAPS", "PENDING_APPROVAL", "Repair", "Northbridge Supplies Ltd", "GB", bad, "NWBKGB2L",
              150, 95, "Creditor IBAN failed validation (mod-97).", maker="OP-9012")
    _ingest(c, [("ANALYST_REPAIR", "OP-9012", "OPERATOR", "RUN_AI_REPAIR", "Priya Nair reviewed the proposed IBAN repair.", ["Evidence grounded"]),
                ("MAKER_SUBMIT", "OP-9012", "OPERATOR", "CASE_SUBMITTED", "Priya Nair submitted the repair for approval with a handover note.", ["Maker-checker"])])
    ch = xt.build_change("creditor_account.iban", bad, good, source="Bank directory + payment history", risk="Low",
                         policy_basis="One approver", justification="Directory record and three prior payments use the proposed IBAN.")
    _put(c["case_id"], _base_ext(c, ok_rows(140, c, bad, good), "complete", change=ch, assignee="OP-9012",
        handover={"note": "Beneficiary confirmed the corrected IBAN by phone (invoice INV-2291 attached). Please release.", "by": {"user_id": "OP-9012", "name": "Priya Nair"},
                  "at": ts(35), "attachment": {"name": "INV-2291.pdf"}}, submitted_at=ts(35),
        stp={"eligible": False, "reason": "Maker-checker required"}, recommended_action="APPLY_REPAIR"))
    ids.append(c["case_id"])

    # ---- PEX-INV-0002: same story, still with the maker (DECISION variant) -----------------------------------------------
    good2 = make_iban("DE", "370400440532013000")
    c = _case("PEX-INV-0002", "DQ-01", 12400, "EUR", "SEPA", "VALIDATED", "Repair", "Rheinbach Metallbau GmbH", "DE", _corrupt(good2), "COBADEFF",
              70, 150, "Creditor IBAN failed validation (mod-97).")
    _ingest(c)
    ch = xt.build_change("creditor_account.iban", _corrupt(good2), good2, source="Bank directory", risk="Low", policy_basis="One approver",
                         justification="Single directory match; checksum passes.")
    _put(c["case_id"], _base_ext(c, ok_rows(60, c, _corrupt(good2), good2), "complete", change=ch))
    ids.append(c["case_id"])

    # ---- PEX-LOW-0096: valid repair, but a brand-new beneficiary with no payment history (confidence below 85%) ------------------
    good3 = make_iban("NL", "91ABNA0417164300")
    c = _case("PEX-LOW-0096", "DQ-01", 18900, "EUR", "SEPA", "VALIDATED", "Repair", "Oranje Techniek BV", "NL", _corrupt(good3), "ABNANL2A",
              55, 170, "Creditor IBAN failed validation (mod-97).")
    _ingest(c)
    ch = xt.build_change("creditor_account.iban", _corrupt(good3), good3, source="Bank directory", risk="Low", policy_basis="One approver",
                         justification="Checksum passes and the directory matches. No earlier payments to this beneficiary and no name check available.")
    rows = [_ev("ev-1", "Creditor IBAN checksum", "Original fails mod-97; proposed passes mod-97", "Payment instruction", "Deterministic check", "pass", "Passed", ts(50)),
            _ev("ev-2", "Bank directory", "Bank code resolves to the named institution", "Bank directory", "Authoritative", "agree", "Agree", ts(50)),
            _ev("ev-3", "Prior payments", "No earlier payments to this beneficiary", "Payment history", "Supporting", "info", "None found", ts(50))]
    _put(c["case_id"], _base_ext(c, rows, "complete", change=ch,
        confidence_inputs={"missing": ["Historical repair / settlement precedent", "CoP / VoP name check"]}))
    ids.append(c["case_id"])

    # ---- PEX-BEN-0012: missing beneficiary data (MISSING_INFO) -----------------------------------------------------------
    c = _case("PEX-BEN-0012", "DQ-03", 24300, "EUR", "SEPA", "INVESTIGATING", "Repair", "Valence Logistics SAS", "FR", "", "BNPAFRPP", 210, 55,
              "Beneficiary account details are incomplete.")
    _ingest(c)
    req_set = "Required-field set for corridor (R16 / scheme rules)"
    rows = [_ev("ev-1", "Beneficiary name", "Present on the instruction", "Payment instruction", "Supporting", "agree", "Agree", ts(200), item="Original payload (parties present)"),
            _ev("ev-2", "Beneficiary account", "No IBAN or account number on the instruction", "Payment instruction", "—", "missing", "Missing", ts(200), item=req_set),
            _ev("ev-3", "Beneficiary bank", "No BIC provided", "Payment instruction", "—", "missing", "Missing", ts(200), item=req_set),
            _ev("ev-4", "Prior payments", "No earlier payments to this beneficiary", "Payment history", "—", "missing", "Missing", ts(200))]
    needed = {"rows": [{"item": "Beneficiary IBAN or account number", "status": "missing", "note": "Not on the instruction"},
                       {"item": "Beneficiary bank BIC", "status": "missing", "note": "Not on the instruction"},
                       {"item": "Beneficiary name", "status": "found", "note": "Valence Logistics SAS"}],
              "searched": [{"source": "Payment instruction", "result": "Fields empty"}, {"source": "Bank directory", "result": "No record"}, {"source": "Prior payments", "result": "None found"}]}
    _put(c["case_id"], _base_ext(c, rows, "missing", needed=needed, contact="Camille Laurent (relationship manager)"))
    ids.append(c["case_id"])

    # ---- PEX-CON-0031: evidence conflict (three sources, design 06) ------------------------------------------------------------
    a = make_iban("DE", "370400440532013000")   # payment instruction and beneficiary master directory agree (real mod-97 values)
    b = make_iban("DE", "120300000000202051")   # invoice INV-4410 shows a different, also valid, IBAN
    c = _case("PEX-CON-0031", "DQ-01", 41200, "EUR", "SEPA", "INVESTIGATING", "Repair", "Hartmann Industrietechnik AG", "DE", a, "COBADEFF",
              180, 75, "Invoice bank details differ from the beneficiary master directory.")
    _ingest(c)
    world = {"checksum": {"instruction": a, "invoice": b}, "directory": {"iban": a}, "invoice": {"number": "INV-4410", "iban": b}}
    rows = [zone.run("checksum", "ev-1", c, world, ts(170)),
            zone.run("directory", "ev-2", c, world, ts(169)),
            zone.run("invoice", "ev-3", c, world, ts(160))]
    conflict = {"field": "Beneficiary account (IBAN)", "note": "Both IBANs pass checksum validation, so validation cannot decide this.",
                "sources": [{"name": "Payment instruction", "value": xt.iban_group(a), "relation": "agrees", "authority": "Originator", "tag": "Agree", "changed_at": None,
                             "received_at": ts(180), "note": "Supplied by originator"},
                            {"name": "Beneficiary master directory", "value": xt.iban_group(a), "relation": "agrees", "authority": "Authoritative", "tag": "Agree",
                             "changed_at": ts(60 * 24 * 40), "checked_at": ts(169)},
                            {"name": "Invoice INV-4410", "value": xt.iban_group(b), "relation": "differs", "authority": "Supporting", "tag": "Differs",
                             "changed_at": None, "received_at": ts(160), "note": "Received today"}],
                "why_blocked": ["Material field in conflict", "Invoice bank details differ from the directory", "Bank policy requires verification before any change"],
                "candidates": [{"id": "H-1", "title": "Keep the IBAN on the instruction and directory", "value": xt.iban_group(a), "confidence": 0.46, "source": "Instruction + directory"},
                               {"id": "H-2", "title": "Use the invoice IBAN", "value": xt.iban_group(b), "confidence": 0.44, "source": "Invoice INV-4410"}]}
    _put(c["case_id"], _base_ext(c, rows, "conflict", conflict=conflict))
    ids.append(c["case_id"])

    # ---- PEX-NAM-0027: beneficiary name mismatch (conflict, large) ------------------------------------------------------------
    nm = make_iban("NL", "ABNA0417164300")
    c = _case("PEX-NAM-0027", "DQ-09", 412000, "EUR", "TARGET2", "INVESTIGATING", "Repair", "Van der Berg Holding BV", "NL", nm, "ABNANL2A", 260, 120,
              "Beneficiary name does not match the account holder.")
    _ingest(c)
    world = {"account_holder": "V. d. Berg Vastgoed BV"}
    rows = [zone.run("vop", "ev-1", c, world, ts(250)),
            _ev("ev-2", "Instruction name", "Instruction says 'Van der Berg Holding BV'", "Payment instruction", "Supporting", "agree", "Agree", ts(250)),
            zone.run("checksum", "ev-3", c, world, ts(250))]
    conflict = {"field": "Beneficiary name", "note": "Account holder differs from the name on the instruction. This could be a different entity.",
                "sources": [{"name": "Payment instruction", "value": "Van der Berg Holding BV", "relation": "differs", "authority": "Supporting", "tag": "Instruction", "changed_at": None},
                            {"name": "Verification of Payee", "value": "V. d. Berg Vastgoed BV", "relation": "differs", "authority": "Authoritative", "tag": "Bank says", "changed_at": ts(250)}]}
    _put(c["case_id"], _base_ext(c, rows, "conflict", conflict=conflict))
    ids.append(c["case_id"])

    # ---- PEX-TMO-0044: status unknown -----------------------------------------------------------------------------------------
    c = _case("PEX-TMO-0044", "PR-07", 54000, "GBP", "CHAPS", "STATUS_UNKNOWN", "Investigation", "Kingsway Property Partners LLP", "GB",
              make_iban("GB", "BARC20040148652912"), "BARCGB22", 240, 30, "Network timeout after hand-off; no bank acknowledgement.", maker="OP-9012",
              dispatch={"dispatch_status": "STATUS_UNKNOWN_DO_NOT_RESEND", "handed_off_at": ts(185)})
    _ingest(c, [("DISPATCH", "SYS-OUTBOUND", "PLATFORM_GUARD", "HANDOFF_TO_BANK", "Instruction handed to the bank payment engine.", ["Outbound port"]),
                ("RECONCILER", "SYS-RECONCILER", "PLATFORM_GUARD", "STATUS_UNKNOWN", "No bank answer inside the timeout. Status unknown. Do not resend.", ["DO_NOT_RESEND"])])
    rows = [_ev("ev-1", "Hand-off acknowledgement", "None received", "Bank payment engine", "Authoritative", "missing", "Missing", ts(185))]
    _put(c["case_id"], _base_ext(c, rows, "complete", handoff_id="HND-48207", sim_script=["STILL_UNKNOWN", "ACCEPTED"],
                                 last_status_check={"at": ts(18), "result": "STILL_UNKNOWN", "by": "OP-9020", "simulated": True,
                                                    "text": "Simulated bank: no answer yet. Still unknown. Do not resend."}, status_checks=0))
    ids.append(c["case_id"])

    # ---- PEX-SAN-0102: sanctions hit (COMPLIANCE_HOLD) --------------------------------------------------------------------------
    c = _case("PEX-SAN-0102", "CO-01", 85000, "USD", "SWIFT_CBPR+", "INVESTIGATING", "Compliance", "Baltic Maritime Trading OU", "EE",
              make_iban("EE", "2200221020145685"), "EEUHEE2X", 120, 90, "Potential sanctions list match on the beneficiary name.")
    _ingest(c, [("SCREENING", "SYS-SCREEN", "SYSTEM", "SANCTIONS_ALERT", "Screening raised a potential name match. Payment held.", ["Compliance hold"])])
    cmp_rows = [{"attribute": "Name", "payment_party": "Baltic Maritime Trading OU", "listed_entity": "BALTIC MARITIME TRADING LTD", "result": "partial", "label": "Partial match"},
                {"attribute": "Country", "payment_party": "Estonia", "listed_entity": "Cyprus", "result": "differs", "label": "Differs"},
                {"attribute": "Registration no.", "payment_party": "Not provided", "listed_entity": "HE 391822", "result": "not_comparable", "label": "Not comparable"}]
    _put(c["case_id"], _base_ext(c, [_ev("ev-1", "Screening result", "Potential name match on bank-configured list", "Bank screening system", "Authoritative", "differs", "Differs", ts(115))],
                                 "complete", compliance_status="SANCTIONS_HOLD",
                                 compliance={"alert": {"reference": "SCR-48213"}, "party_comparison": cmp_rows, "notes": [], "attachments": [],
                                             "second_review": {"required": True, "state": "none", "first_reviewer": None}}))
    ids.append(c["case_id"])

    # ---- PEX-CUS-0067: customer watchlist (COMPLIANCE_HOLD, name-only) -------------------------------------------------------------
    c = _case("PEX-CUS-0067", "CO-08", 31500, "GBP", "CHAPS", "INVESTIGATING", "Compliance", "Okonkwo Imports Ltd", "GB",
              make_iban("GB", "HBUK40127612345678"), "HBUKGB4B", 95, 140, "Customer watchlist name match.")
    _ingest(c, [("SCREENING", "SYS-SCREEN", "SYSTEM", "WATCHLIST_ALERT", "Customer watchlist raised a name-only match. Payment held.", ["Compliance hold"])])
    _put(c["case_id"], _base_ext(c, [_ev("ev-1", "Watchlist", "Name-only match, no date of birth or registration", "Bank screening system", "Authoritative", "differs", "Differs", ts(90))],
                                 "complete", compliance_status="AML_SUSPENDED", compliance={"alert": {"reference": "SCR-48377"}}))
    ids.append(c["case_id"])

    # ---- PEX-RET-0035: returned payment, dual authorisation ---------------------------------------------------------------------------
    c = _case("PEX-RET-0035", "ST-01", 1793900, "AUD", "SWIFT_CBPR+", "PENDING_APPROVAL", "Investigation", "Coastal Resources Pty Ltd", "AU",
              make_iban("GB", "WEST12345698765432"), "WPACAU2S", 300, 200, "Payment returned by the beneficiary bank (account closed).", maker="OP-9020")
    _ingest(c, [("MAKER_SUBMIT", "OP-9020", "OPERATOR", "CASE_SUBMITTED", "Marcus Lee submitted the return handling for approval.", ["Maker-checker"])])
    ch = xt.build_change("payment.value_date", "", "Return credited to ordering account", source="Return message", risk="High",
                         policy_basis="Dual authorisation (>= 250,000)", justification="Funds returned; credit the ordering customer.", what_changes="Credit returned funds to the ordering customer")
    _put(c["case_id"], _base_ext(c, [_ev("ev-1", "Return message", "Bank returned the payment: account closed", "Beneficiary bank", "Authoritative", "agree", "Agree", ts(280))],
                                 "complete", change=ch, assignee="OP-9020",
                                 handover={"note": "Return confirmed by the beneficiary bank. Credit back to the ordering account.", "by": {"user_id": "OP-9020", "name": "Marcus Lee"}, "at": ts(40), "attachment": None},
                                 submitted_at=ts(40)))
    ids.append(c["case_id"])

    # ---- PEX-REC-0079: returned for rework -------------------------------------------------------------------------------------------
    g = make_iban("FR", "30004000031234567890143")
    c = _case("PEX-REC-0079", "ST-04", 19800, "EUR", "SEPA", "RETURNED_FOR_REWORK", "Investigation", "Lumiere Distribution SARL", "FR", g, "BNPAFRPP", 330, 60,
              "Reconciliation break between ledger and statement.", maker="OP-9021")
    _ingest(c, [("APPROVAL", "APR-3192", "OPERATIONS_APPROVER", "APPROVAL_RETURNED", "Mei Tan returned the case to the maker: evidence incomplete.", ["Maker-checker"])])
    ch = xt.build_change("remittance_info", "", "Match statement line 4412 to ledger entry L-9921", source="Statement", risk="Low", policy_basis="One approver",
                         what_changes="Reconciliation match proposed")
    _put(c["case_id"], _base_ext(c, [_ev("ev-1", "Statement line", "Line 4412 matches the amount", "Statement", "Supporting", "agree", "Agree", ts(320))], "complete",
                                 change=ch, assignee="OP-9021", returned={"by": {"user_id": "APR-3192", "name": "Mei Tan"}, "at": ts(50),
                                                                           "reason": "Evidence incomplete", "note": "Attach the statement line before resubmitting."}))
    ids.append(c["case_id"])

    # ---- PEX-DUP-0051: possible duplicate ---------------------------------------------------------------------------------------------
    c = _case("PEX-DUP-0051", "PR-01", 6900, "GBP", "BACS", "RECOMMENDED", "Investigation", "Ashford Cleaning Services Ltd", "GB",
              make_iban("GB", "LOYD30949701234567"), "LOYDGB21", 40, 180, "Possible duplicate of an earlier payment.")
    _ingest(c)
    _put(c["case_id"], _base_ext(c, [_ev("ev-1", "Duplicate check", "Same amount, beneficiary and reference within 24h", "Payment history", "Deterministic check", "differs", "Differs", ts(35))],
                                 "complete", possible_duplicate_of="PEX-DUP-0050"))
    ids.append(c["case_id"])

    # ---- PEX-SET-0039: handed to bank ---------------------------------------------------------------------------------------------------
    c = _case("PEX-SET-0039", "ST-05", 23400, "USD", "FEDWIRE_ISO20022", "DISPATCHED", "Investigation", "Midwest Freight Corp", "US", "", "CHASUS33", 200, 45,
              "Settlement failure; repaired instruction resent by the bank.", maker="OP-9012",
              dispatch={"dispatch_status": "HANDED_OFF_HOLD", "handed_off_at": ts(22), "bank_clearing_system": "FEDWIRE"},
              cred_acc={"account_number": "000123456789", "aba_routing": "021000021", "bank_bic": "CHASUS33"})
    _ingest(c, [("DISPATCH", "SYS-OUTBOUND", "PLATFORM_GUARD", "HANDOFF_TO_BANK", "Approved repair handed to the bank payment engine. PeX does not execute.", ["Outbound port"])])
    _put(c["case_id"], _base_ext(c, [_ev("ev-1", "Approval", "Approved by Mei Tan", "PeX approval record", "Authoritative", "agree", "Agree", ts(25))], "complete",
                                 handoff_id="HND-48213", last_approver={"user_id": "APR-3192", "name": "Mei Tan"}, last_status_check=None))
    ids.append(c["case_id"])

    # ---- PEX-EXE-0088: executed (bank confirmed) -----------------------------------------------------------------------------------------
    c = _case("PEX-EXE-0088", "DQ-02", 15200, "EUR", "SEPA", "EXECUTED_CONFIRMED", "Repair", "Fontaine Conseil SARL", "FR", make_iban("FR", "20041010050500013M02606"), "BNPAFRPP", 400, -60,
              "Invalid BIC repaired.", maker="OP-9012", dispatch={"dispatch_status": "BANK_CONFIRMED", "handed_off_at": ts(180), "bank_ack_reference": "BK-7731902", "bank_clearing_system": "SEPA"})
    _ingest(c, [("DISPATCH", "SYS-OUTBOUND", "PLATFORM_GUARD", "HANDOFF_TO_BANK", "Handed to the bank.", ["Outbound port"]),
                ("BANK_SIGNAL", "BANK-SIM", "BANK_SYSTEM", "EXECUTED_CONFIRMED", "Signed bank signal: executed (BK-7731902).", ["Signed inbound"])])
    _put(c["case_id"], _base_ext(c, [], "complete", handoff_id="HND-48190", bank_reference="BK-7731902", executed_at=ts(150)))
    ids.append(c["case_id"])

    # ---- PEX-WAT-0090: waiting on a reply -------------------------------------------------------------------------------------------------
    c = _case("PEX-WAT-0090", "DQ-03", 9800, "GBP", "BACS", "INVESTIGATING", "Repair", "Pennine Foods Ltd", "GB", "", "NWBKGB2L", 140, 120, "Beneficiary account details are incomplete.")
    _ingest(c)
    ri = {"state": "sent", "method": "Email", "sent_at": ts(35), "reply_due": iso(t + timedelta(minutes=85)), "escalate_at": iso(t + timedelta(minutes=100)),
          "message": "Please send the sort code and account number for Pennine Foods Ltd.", "to": {"party": "Pennine Foods Ltd", "contact": "Accounts payable", "role": "Customer contact"}}
    rows = [_ev("ev-1", "Beneficiary account", "No account number on the instruction", "Payment instruction", "—", "missing", "Missing", ts(130),
                item="Required-field set for corridor (R16 / scheme rules)")]
    _put(c["case_id"], _base_ext(c, rows, "missing", request_info=ri, assignee="OP-9022"))
    ids.append(c["case_id"])
    return ids


def seed_stp() -> List[str]:
    t = now()
    amounts = [4200, 6800, 9350, 12400, 8900, 15200, 7600, 11050, 13300, 10870, 16450, 20500]
    ccys = ["GBP", "EUR", "USD"]
    kinds = [("DQ-02", "invalid_bic"), ("DQ-01", "iban"), ("DQ-08", "routing"), ("DQ-05", "address")]
    cps = [("Alder Print Ltd", "GB"), ("Brandt Werkzeuge GmbH", "DE"), ("Cedar Point Supply Inc", "US"), ("Dupont Textiles SA", "FR"),
           ("Eastgate Dental Ltd", "GB"), ("Fischer Elektro GmbH", "DE"), ("Granite State Tools LLC", "US"), ("Haas Optik AG", "DE"),
           ("Ironbridge Fabrication Ltd", "GB"), ("Jansen Kaas BV", "NL"), ("Keystone Packaging LLC", "US"), ("Lindqvist Verkstad AB", "SE")]
    ids = []
    for k, amt in enumerate(amounts):
        n = 101 + k
        code, kind = kinds[k % len(kinds)]
        ccy = ccys[k % 3]
        cp, cc = cps[k]
        rail = {"GBP": "CHAPS", "EUR": "SEPA", "USD": "FEDWIRE_ISO20022"}[ccy]
        iban = make_iban(cc, {"GB": "NWBK60161331926819", "DE": "370400440532013000", "US": "", "FR": "30004000031234567890143", "NL": "ABNA0417164300", "SE": "50000000058398257466"}[cc]) if cc != "US" else ""
        c = _case(f"PEX-STP-{n:04d}", code, amt, ccy, rail, "RECOMMENDED", "STP Fast-Lane", cp, cc, iban, "DEUTDEFF", 90 - k * 3, 150 + k * 5,
                  "Low-value data repair eligible for one-click batch approval.")
        if kind == "invalid_bic":
            ch = xt.build_change("creditor_agent.bic", "LL0YGB2L" if k == 0 else "DEUTDEF0", "LLOYGB2L" if k == 0 else "DEUTDEFF", source="Bank directory", risk="Low", policy_basis="Micro-repair MR-01",
                                 what_changes="Creditor bank BIC corrected")
        elif kind == "iban":
            ch = xt.build_change("creditor_account.iban", _corrupt(iban), iban, source="Bank directory", risk="Low", policy_basis="Micro-repair MR-01")
        elif kind == "routing":
            ch = xt.build_change("creditor_agent.aba_routing", "02100002", "021000021", source="Routing directory", risk="Low", policy_basis="Micro-repair MR-01")
        else:
            ch = xt.build_change("creditor.address", "", f"{cp}, Main Street 1", source="Address registry", risk="Low", policy_basis="Micro-repair MR-01",
                                 what_changes="Structured address added")
        rows = [_ev("ev-1", "Deterministic validation", "Proposed value passes validation", "PeX control", "Deterministic check", "pass", "Passed", iso(t - timedelta(minutes=80))),
                _ev("ev-2", "Authoritative source", "Directory confirms the proposed value", "Directory", "Authoritative", "agree", "Agree", iso(t - timedelta(minutes=80)))]
        _ingest(c, [("RECOMMENDATION", "SYS-PEX", "SYSTEM", "RECOMMENDATION_MADE", "Deterministic micro-repair proposed and validated.", ["Validated"])])
        _put(c["case_id"], _base_ext(c, rows, "complete", change=ch, batch_candidate=True, stp={"eligible": True, "reason": "Micro-repair MR-01"}))
        ids.append(c["case_id"])
    # ineligible examples
    extra = [
        ("PEX-STP-0113", "DQ-01", 18200, "EUR", "SEPA", "Repair", "conflict"),
        ("PEX-STP-0114", "CO-08", 9400, "GBP", "CHAPS", "Compliance", "hold"),
        ("PEX-STP-0115", "DQ-01", 7300, "USD", "FEDWIRE_ISO20022", "STP Fast-Lane", "invalid"),
    ]
    for cid, code, amt, ccy, rail, queue, kind in extra:
        iban = make_iban("DE", "370400440532013000")
        c = _case(cid, code, amt, ccy, rail, "RECOMMENDED", queue, "Mercer & Wolf GmbH", "DE", iban, "COBADEFF", 60, 160, "Low-value repair candidate.")
        _ingest(c)
        ch = xt.build_change("creditor_account.iban", _corrupt(iban), iban if kind != "invalid" else _corrupt(iban)[:-1] + "0", source="Bank directory", risk="Low", policy_basis="Micro-repair MR-01")
        e = _base_ext(c, [_ev("ev-1", "Directory", "Checked", "Directory", "Authoritative", "agree", "Agree", iso(t))], "complete", change=ch, batch_candidate=True)
        if kind == "conflict":
            e["evidence_state"] = "conflict"
            e["evidence"] = [_ev("ev-1", "Directory vs master", "Two valid IBANs on file", "Customer master", "Authoritative", "differs", "Differs", iso(t))]
            e["conflict"] = {"field": "Creditor IBAN", "sources": [], "note": "Sources disagree."}
        elif kind == "hold":
            e["compliance_status"] = "AML_SUSPENDED"
        else:
            e["validation_failed"] = "The proposed IBAN does not pass mod-97."
        _put(cid, e)
        ids.append(cid)
    return ids


def _respread_baseline_cutoffs(db=None):
    """Baseline demo cases carry stale SLA times (already passed). Re-spread them from now so the demo clock looks live:
    3h to ~9h ahead in 7-minute steps. Named v2 cases are seeded afterwards with their own relative cutoffs."""
    from datetime import datetime, timezone
    from app.db.session import SessionLocal
    own = db is None
    db = db or SessionLocal()
    try:
        base = datetime.now(timezone.utc)
        rows = db.query(CaseModel).order_by(CaseModel.case_id).all()
        for i, c in enumerate(rows):
            c.sla_due_at = (base + timedelta(minutes=180 + (i * 7) % 360)).isoformat()
        db.commit()
    finally:
        if own:
            db.close()


def seed_v2(db=None) -> Dict[str, Any]:
    from app.services.v2.admin import ensure_integrations
    ext_store.reset()
    _respread_baseline_cutoffs(db)
    named = seed_named()
    stp = seed_stp()
    ext_store.flush()
    ensure_integrations(db)
    log.info("UI v2 seed: %d named, %d STP cases", len(named), len(stp))
    return {"named": len(named), "stp": len(stp)}


def maybe_auto_seed(db, fresh: bool = True):
    """Auto-seed only a brand-new (empty) database. Existing databases are seeded with scripts/seed_ui_v2_demo.py."""
    if not (settings.PEX_DEMO and settings.SEED_V2 and fresh):
        return None
    if db.query(CaseModel).filter(CaseModel.case_id == MARKER).first():
        return None
    return seed_v2(db)
