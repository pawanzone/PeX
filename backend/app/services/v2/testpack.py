"""Manual-test data pack: one known-state case for each of the 41 profiles, plus the extra cases for the full-workflow sets.

Run through scripts/reset_and_seed_demo.py (wipes the database, then seeds the baseline, the showcase cases and this pack).
Case ids are TST-<profile>-<nn>: nn=01 is always the clean workflow for that profile. Every id, persona and expected outcome is
listed in PACK, and the manual test workbook is generated from the same list, so data and instructions cannot drift apart.

All names, accounts and amounts are invented. IBANs are real MOD-97 valid unless the story needs an invalid one.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

from app.services.v2 import ext as xt
from app.services.v2 import library as lib
from app.services.v2.core import iso, now, person
from app.services.v2 import seed as sd

# ---- people (demo personas) ----------------------------------------------------------------------------------------------
MAKER = "OP-9012"          # Priya Nair, Operator
MAKER2 = "OP-9013"         # Amina Okafor, Operator
OPS_APPROVER = "APR-3191"  # Daniel Osei
COMP1 = "CMP-4420"         # Marisol Vega, Compliance
COMP2 = "CMP-6001"         # Amara Okafor, Compliance
RISK = "RSK-7714"          # Kenji Watanabe, Risk

# ---- repair profiles: the proposed change each one shows --------------------------------------------------------------------
# code: (counterparty, country, amount, currency, rail, field, original, proposed, what changes, source)
R: Dict[str, tuple] = {
    "DQ-02": ("Aldous Hartley Ltd", "GB", 7400, "GBP", "CHAPS", "creditor_agent.bic", "LL0YGB2L", "LLOYGB2L", "Creditor bank BIC corrected", "Bank directory"),
    "DQ-03": ("Valence Logistics SAS", "FR", 24300, "EUR", "SEPA", "creditor_account.iban", "", "", "Beneficiary IBAN supplied by the client", "Client reply, checksum validated"),
    "DQ-04": ("Meridian Textiles GmbH", "DE", 15600, "EUR", "SEPA", "remittance_info", "", "INV-2026-1187 / PO 44021", "Remittance reference added from the invoice", "Invoice record"),
    "DQ-05": ("Hallam Freight Ltd", "GB", 9200, "GBP", "BACS", "creditor.address", "", "14 Quarry Lane, Sheffield S1 2AB, GB", "Structured address added", "Address registry"),
    "DQ-06": ("Koda Trading Pte Ltd", "SG", 33800, "USD", "SWIFT_CBPR+", "purpose_code", "", "SUPP", "Purpose code added for the corridor", "Corridor purpose-code set"),
    "DQ-07": ("Brightwater Dental Ltd", "GB", 4150, "GBP", "FPS", "creditor_account.account_number", "1234567", "12345678", "Account number corrected to 8 digits", "Sort-code and account directory"),
    "DQ-08": ("Cedar Point Supply Inc", "US", 18750, "USD", "FEDWIRE_ISO20022", "creditor_agent.aba_routing", "02100002", "021000021", "ABA routing number corrected", "Routing directory"),
    "DQ-09": ("Van Dijk Installatie BV", "NL", 21400, "EUR", "SEPA", "creditor.name", "Van Dyk Installatie", "Van Dijk Installatie BV", "Beneficiary name aligned to the account holder", "Verification of Payee"),
    "PR-01": ("Ashford Cleaning Services Ltd", "GB", 6900, "GBP", "BACS", "payment.status", "Duplicate suspected", "Release (not a duplicate: different invoice)", "Duplicate cleared after invoice check", "Payment history + invoice"),
    "PR-02": ("Nordlys Shipping AS", "NO", 27300, "EUR", "SWIFT_CBPR+", "routing.intermediary_bic", "CHASUS33", "DEUTDEFF", "Intermediary bank changed to a reachable route", "Correspondent routing table"),
    "PR-03": ("Sakura Components KK", "JP", 56000, "USD", "SWIFT_CBPR+", "message.structure", "Unstructured postal address (fails schema)", "Structured postal address (schema valid)", "Message fixed to pass ISO 20022 validation", "ISO 20022 schema"),
    "PR-04": ("Granite State Tools LLC", "US", 12900, "USD", "FEDWIRE_ISO20022", "payment.value_date", "2026-11-10", "2026-11-12", "Value date moved to the next cut-off", "Cut-off calendar"),
    "PR-05": ("Brandt Werkzeuge GmbH", "DE", 8800, "EUR", "SEPA", "message.encoding", "Corrupted tag <CdtrAgt>", "Rebuilt from the original payload", "Message rebuilt from the original payload", "Original payload"),
    "PR-06": ("Pennine Foods Ltd", "GB", 14300, "GBP", "CHAPS", "routing.intermediary_bic", "BARCGB22 (rejected)", "HBUKGB4B", "Alternative intermediary selected after rejection", "Correspondent routing table"),
    "PR-07": ("Kingsway Property Partners LLP", "GB", 54000, "GBP", "CHAPS", "payment.status", "Unknown after timeout", "Bank confirms not received: safe to re-submit", "Status resolved by the bank before any re-submission", "Bank status answer"),
    "PR-08": ("Fischer Elektro GmbH", "DE", 11200, "EUR", "SEPA", "payment.queue", "Stuck in processing queue Q7", "Re-queued to Q2", "Payment re-queued after a processing failure", "Queue monitor"),
    "PR-09": ("Lindqvist Verkstad AB", "SE", 16800, "EUR", "SEPA", "payment.hold", "Held for repair", "Repaired and released from hold", "Hold released after repair", "Repair worklist"),
    "ST-01": ("Coastal Resources Pty Ltd", "GB", 94500, "AUD", "SWIFT_CBPR+", "payment.value_date", "", "Return credited to ordering account", "Credit returned funds to the ordering customer", "Return message"),
    "ST-02": ("Eastgate Dental Ltd", "GB", 5300, "GBP", "FPS", "creditor_account.account_number", "20041010 (closed)", "Updated account from the client", "New account supplied after the old one closed", "Client reply"),
    "ST-03": ("Jansen Kaas BV", "NL", 19500, "EUR", "SEPA", "payment.action", "Beneficiary account frozen", "Return funds to the ordering customer", "Return instruction raised for a frozen account", "Bank notification"),
    "ST-06": ("Haas Optik AG", "DE", 38600, "EUR", "TARGET2", "payment.action", "Funds trapped at correspondent", "Release request sent to the correspondent", "Release of trapped funds requested", "Correspondent statement"),
    "TR-01": ("Oranje Techniek BV", "NL", 22100, "EUR", "SEPA", "customer.kyc_status", "Expired 2026-09-30", "Refreshed 2026-11-10", "KYC refreshed; payment can proceed", "KYC record"),
    "TR-02": ("Keystone Packaging LLC", "US", 13400, "USD", "FEDWIRE_ISO20022", "payment.funding", "Insufficient funds", "Funded from the linked sweep account", "Funds moved from the linked account", "Account balance"),
    "TR-03": ("Dupont Textiles SA", "FR", 47000, "EUR", "TARGET2", "nostro.funding", "Nostro shortfall EUR 47,000", "Top-up transfer raised", "Nostro top-up requested", "Nostro balance"),
    "TR-04": ("Sakura Components KK", "JP", 31200, "JPY", "SWIFT_CBPR+", "payment.fx_rate", "No rate available", "Rate applied from the treasury feed", "FX rate applied from the treasury feed", "Treasury rate feed"),
    "TR-05": ("Mercer & Wolf GmbH", "DE", 17900, "EUR", "SEPA", "payment.authorisation", "Missing second signature", "Authorisation evidence attached", "Customer authorisation attached", "Customer mandate"),
    "TR-06": ("Alder Print Ltd", "GB", 26500, "GBP", "CHAPS", "customer.limit", "Daily limit exceeded", "Temporary limit uplift approved", "Limit uplift for one payment", "Limit record"),
    "TR-07": ("Lumiere Distribution SARL", "FR", 35200, "EUR", "TARGET2", "liquidity.window", "Liquidity constraint at 14:00", "Scheduled for the 16:00 window", "Release moved to the next liquidity window", "Liquidity forecast"),
    "TR-08": ("Fontaine Conseil SARL", "FR", 88000, "EUR", "SWIFT_CBPR+", "credit.exposure", "Exposure over limit", "Exposure approved within the temporary headroom", "Exposure breach reviewed and approved", "Counterparty exposure record"),
    "CO-04": ("Baltic Maritime Trading OU", "EE", 29000, "EUR", "SWIFT_CBPR+", "payment.corridor", "Restricted corridor", "Corridor cleared by policy matrix", "Restricted-corridor check cleared", "Corridor policy matrix"),
    "CO-07": ("Okonkwo Imports Ltd", "GB", 21500, "GBP", "CHAPS", "regulatory.report", "Statutory report missing", "Statutory report attached", "Regulatory reporting data added", "Central bank reporting codes"),
}
CO_TWO_STEP = ["CO-01", "CO-02", "CO-03", "CO-05", "CO-06", "CO-08"]
CO_ALERT = {"CO-01": ("Baltic Maritime Trading OU", "EE", 85000, "USD", "SANCTIONS_HOLD", "Potential sanctions list match on the beneficiary name."),
            "CO-02": ("Redwood Metals Trading FZE", "AE", 62000, "USD", "AML_SUSPENDED", "AML monitoring alert: structuring pattern."),
            "CO-03": ("Hartmann Beratung GmbH", "DE", 40500, "EUR", "AML_SUSPENDED", "Beneficiary director matches a politically exposed person."),
            "CO-05": ("Lakeshore Holdings Ltd", "GB", 33000, "GBP", "AML_SUSPENDED", "Adverse media hit on the beneficiary's owner."),
            "CO-06": ("Danube Export Kft", "HU", 52000, "EUR", "AML_SUSPENDED", "Payment routed through a high-risk jurisdiction."),
            "CO-08": ("Okonkwo Imports Ltd", "GB", 31500, "GBP", "AML_SUSPENDED", "Customer watchlist name match.")}
ST_DECISION = {"ST-04": ("Lumiere Distribution SARL", "FR", 19800, "EUR", "SEPA"),
               "ST-05": ("Midwest Freight Corp", "US", 23400, "USD", "FEDWIRE_ISO20022"),
               "ST-07": ("Westbrook Services Ltd", "GB", 8300, "GBP", "BACS")}
COUNTRY_BBAN = {"GB": ("GB", "NWBK60161331926819"), "DE": ("DE", "370400440532013000"), "FR": ("FR", "30004000031234567890143"),
                "NL": ("NL", "ABNA0417164300"), "SE": ("SE", "50000000058398257466"), "EE": ("EE", "2200221020145685"),
                "NO": ("NO", "8601111794"), "HU": ("HU", "117730161111101800000000")}

BANK_REJECTS = {"TST-DQ01-12"}   # the simulated bank rejects this one after hand-off
PACK: List[Dict[str, Any]] = []


def _add(case_id: str, code: str, scenario: str, **kw):
    PACK.append({"case_id": case_id, "code": code, "scenario": scenario, **kw})


def _pname(code: str) -> str:
    return lib.profile(code)["name"].replace("_", " ").capitalize()


def _evidence_rows(code: str, t_min: int = 40) -> List[Dict[str, Any]]:
    """One row for each evidence item the profile's confidence model expects, named exactly as the model names it, so coverage is complete."""
    from app.services.v2 import evidence_model as em
    out = []
    try:
        items = em.PROFILES[code][2]
    except Exception:
        items = []
    for n, it in enumerate([i for i in items if i.get("system") != "EVENT"], 1):
        auth = "Authoritative" if it.get("gate") else "Supporting"
        out.append(xt.row(f"ev-{n}", it["name"], f"{it['name']} checked and consistent with the proposed outcome", it.get("source") or "Bank source", auth, "agree", "Agree",
                          iso(now() - timedelta(minutes=t_min)), item=it["name"]))
    return out or [xt.row("ev-1", "Deterministic validation", "Proposed value passes validation", "PeX control", "Deterministic check", "pass", "Passed", iso(now()))]


def _iban_for(cc: str) -> str:
    c, b = COUNTRY_BBAN.get(cc, ("GB", "NWBK60161331926819"))
    return sd.make_iban(c, b)


def _repair_case(case_id: str, code: str):
    cp, cc, amt, ccy, rail, field, orig, prop, what, source = R[code]
    iban = _iban_for(cc)
    c = sd._case(case_id, code, amt, ccy, rail, "VALIDATED", "Repair", cp, cc, iban, "NWBKGB2L", 90, 180, f"{_pname(code)}: repair proposed from the evidence.")
    sd._ingest(c)
    ch = xt.build_change(field, orig, prop, source=source, risk="Low", policy_basis="One approver", justification=f"{source} supports the proposed value.", what_changes=what)
    sd._put(case_id, sd._base_ext(c, _evidence_rows(code), "complete", change=ch, stp={"eligible": False, "reason": "Maker-checker required"}, recommended_action="APPLY_REPAIR"))
    return c


def _compliance_repair_case(case_id: str, code: str):
    cp, cc, amt, ccy, rail, field, orig, prop, what, source = R[code]
    c = sd._case(case_id, code, amt, ccy, rail, "INVESTIGATING", "Compliance", cp, cc, _iban_for(cc), "NWBKGB2L", 100, 150,
                 f"{_pname(code)}: compliance clearance needed before the repair.")
    sd._ingest(c, [("SCREENING", "SYS-SCREEN", "SYSTEM", "COMPLIANCE_ALERT", "Compliance check raised. Payment held.", ["Compliance hold"])])
    ch = xt.build_change(field, orig, prop, source=source, risk="Low", policy_basis="One approver", what_changes=what)
    sd._put(case_id, sd._base_ext(c, _evidence_rows(code, 95), "complete", change=ch, compliance_status="AML_SUSPENDED",
                                  compliance={"alert": {"reference": "SCR-" + case_id[-6:]}, "notes": [], "attachments": [],
                                              "second_review": {"required": False, "state": "none", "first_reviewer": None}}))
    return c


def _compliance_case(case_id: str, code: str, amount: float = None):
    cp, cc, amt, ccy, status, reason = CO_ALERT[code]
    amt = amount if amount is not None else amt
    c = sd._case(case_id, code, amt, ccy, "SWIFT_CBPR+", "INVESTIGATING", "Compliance", cp, cc, _iban_for(cc), "NWBKGB2L", 100, 150, reason)
    sd._ingest(c, [("SCREENING", "SYS-SCREEN", "SYSTEM", "COMPLIANCE_ALERT", "Screening raised an alert. Payment held.", ["Compliance hold"])])
    cmp_rows = [{"attribute": "Name", "payment_party": cp, "listed_entity": cp.upper(), "result": "partial", "label": "Partial match"},
                {"attribute": "Country", "payment_party": cc, "listed_entity": "Different", "result": "differs", "label": "Differs"},
                {"attribute": "Registration no.", "payment_party": "Not provided", "listed_entity": "On file", "result": "not_comparable", "label": "Not comparable"}]
    sd._put(case_id, sd._base_ext(c, _evidence_rows(code, 95), "complete", compliance_status=status,
                                  compliance={"alert": {"reference": "SCR-" + case_id[-6:]}, "party_comparison": cmp_rows, "notes": [], "attachments": [],
                                              "second_review": {"required": True, "state": "none", "first_reviewer": None}}))
    return c


def _st_case(case_id: str, code: str):
    cp, cc, amt, ccy, rail = ST_DECISION[code]
    c = sd._case(case_id, code, amt, ccy, rail, "RECOMMENDED", "Investigation", cp, cc, _iban_for(cc), "NWBKGB2L", 120, 200,
                 f"{_pname(code)}: a person must choose how to resolve it.")
    sd._ingest(c)
    dec = lib.profile(code)["decision"]
    sd._put(case_id, sd._base_ext(c, _evidence_rows(code), "complete", decision_request={
        "action": "DECISION_REQUIRED", "target": dec["target_field"], "options": [o["option"] for o in dec["options"]],
        "reviewer_role": dec["reviewer_role"], "evidence_complete": True, "missing": [], "conflicting": []}))
    return c


def _iban_case(case_id: str, amount: float = 8650, low: bool = False):
    good = sd.make_iban("NL", "91ABNA0417164300") if low else sd.make_iban("GB", "NWBK60161331926819")
    bad = sd._corrupt(good)
    cp = "Oranje Techniek BV" if low else "Northbridge Supplies Ltd"
    c = sd._case(case_id, "DQ-01", amount, "EUR" if low else "GBP", "SEPA" if low else "CHAPS", "VALIDATED", "Repair", cp, "NL" if low else "GB", bad,
                 "ABNANL2A" if low else "NWBKGB2L", 90, 180, "Creditor IBAN failed validation (mod-97).")
    sd._ingest(c)
    hi = amount >= 250000
    ch = xt.build_change("creditor_account.iban", bad, good, source="Bank directory + payment history", risk="High" if hi else "Low",
                         policy_basis="Dual authorisation (>= 250,000)" if hi else "One approver",
                         justification="Directory record and prior payments use the proposed IBAN.")
    from app.services.v2 import zone
    ts = lambda m: iso(now() - timedelta(minutes=m))
    if low:
        rows = [xt.row("ev-1", "Creditor IBAN checksum", "Original fails mod-97; proposed passes mod-97", "Payment instruction", "Deterministic check", "pass", "Passed", ts(50)),
                xt.row("ev-2", "Bank directory", "Bank code resolves to the named institution", "Bank directory", "Authoritative", "agree", "Agree", ts(50)),
                xt.row("ev-3", "Prior payments", "No earlier payments to this beneficiary", "Payment history", "Supporting", "info", "None found", ts(50))]
        e = sd._base_ext(c, rows, "complete", change=ch, confidence_inputs={"missing": ["Historical repair / settlement precedent", "CoP / VoP name check"]})
    else:
        rows = [zone.run("checksum", "ev-1", c, {"checksum": {"original": bad, "proposed": good}}, ts(60), source="Payment instruction"),
                xt.row("ev-2", "Bank directory", "Bank code resolves to the named institution", "Bank directory", "Authoritative", "agree", "Agree", ts(60), kind="directory"),
                zone.run("history", "ev-3", c, {"checksum": {"original": bad, "proposed": good}, "history": {"count": 3, "same_account": 3}}, ts(60)),
                zone.run("vop", "ev-4", c, {"account_holder": cp}, ts(60)),
                zone.run("core", "ev-5", c, {"account": {"status": "OPEN"}}, ts(60))]
        e = sd._base_ext(c, rows, "complete", change=ch, stp={"eligible": False, "reason": "Maker-checker required"}, recommended_action="APPLY_REPAIR")
    sd._put(case_id, e)
    return c


def _pending_iban_case(case_id: str, maker: str, amount: float = 8650, cutoff: int = 180):
    from app.services.data_loader import repo
    c = _iban_case(case_id, amount)
    c["status"] = "PENDING_APPROVAL"
    c["maker_id"] = maker
    c["sla_due_at"] = iso(now() + timedelta(minutes=cutoff))
    repo.save_case(c)
    sd._log(c, "MAKER_SUBMIT", maker, "OPERATOR", "CASE_SUBMITTED", f"{(person(maker) or {}).get('name', maker)} submitted the repair for approval.", ["Maker-checker"])
    e = xt.get_ext(c)
    t = now()
    e.update({"handover": {"note": "Directory record and three prior payments use the proposed IBAN. Please approve.", "by": person(maker), "at": iso(t - timedelta(minutes=20)), "attachment": None},
              "submitted_at": iso(t - timedelta(minutes=20)), "assignee": maker, "approver_assigned": OPS_APPROVER, "cutoff_at": c["sla_due_at"],
              "confidence_review": {"required": False, "state": "none"}})
    sd._put(case_id, e)
    return c


def _conflict_case(case_id: str):
    from app.services.v2 import zone
    a = sd.make_iban("DE", "370400440532013000")
    b = sd.make_iban("DE", "120300000000202051")
    c = sd._case(case_id, "DQ-01", 41200, "EUR", "SEPA", "INVESTIGATING", "Repair", "Hartmann Industrietechnik AG", "DE", a, "COBADEFF", 180, 160,
                 "Invoice bank details differ from the beneficiary master directory.")
    sd._ingest(c)
    ts = lambda m: iso(now() - timedelta(minutes=m))
    world = {"checksum": {"instruction": a, "invoice": b}, "directory": {"iban": a}, "invoice": {"number": "INV-4410", "iban": b}}
    rows = [zone.run("checksum", "ev-1", c, world, ts(170)), zone.run("directory", "ev-2", c, world, ts(169)), zone.run("invoice", "ev-3", c, world, ts(160))]
    conflict = {"field": "Beneficiary account (IBAN)", "note": "Both IBANs pass checksum validation, so validation cannot decide this.",
                "sources": [{"name": "Payment instruction", "value": xt.iban_group(a), "relation": "agrees", "authority": "Originator", "tag": "Agree", "changed_at": None},
                            {"name": "Beneficiary master directory", "value": xt.iban_group(a), "relation": "agrees", "authority": "Authoritative", "tag": "Agree", "changed_at": None},
                            {"name": "Invoice INV-4410", "value": xt.iban_group(b), "relation": "differs", "authority": "Supporting", "tag": "Differs", "changed_at": None}],
                "why_blocked": ["Material field in conflict"],
                "candidates": [{"id": "H-1", "title": "Keep the IBAN on the instruction and directory", "value": xt.iban_group(a), "confidence": 0.46, "source": "Instruction + directory"},
                               {"id": "H-2", "title": "Use the invoice IBAN", "value": xt.iban_group(b), "confidence": 0.44, "source": "Invoice INV-4410"}]}
    sd._put(case_id, sd._base_ext(c, rows, "conflict", conflict=conflict))
    return c


def _missing_iban_case(case_id: str, code: str = "DQ-01"):
    c = sd._case(case_id, code, 24300, "EUR", "SEPA", "INVESTIGATING", "Repair", "Valence Logistics SAS", "FR", "", "BNPAFRPP", 200, 150,
                 "Beneficiary account details are incomplete.")
    sd._ingest(c)
    t = lambda m: iso(now() - timedelta(minutes=m))
    rows = [xt.row("ev-1", "Beneficiary name", "Present on the instruction", "Payment instruction", "Supporting", "agree", "Agree", t(190)),
            xt.row("ev-2", "Beneficiary IBAN", "No IBAN or account number on the instruction", "Payment instruction", "—", "missing", "Missing", t(190),
                   item="Required-field set for corridor (R16 / scheme rules)")]
    needed = {"rows": [{"item": "Beneficiary IBAN or account number", "status": "missing", "note": "Not on the instruction"},
                       {"item": "Beneficiary name", "status": "found", "note": "Valence Logistics SAS"}],
              "searched": [{"source": "Payment instruction", "result": "Fields empty"}, {"source": "Bank directory", "result": "No record"}]}
    sd._put(case_id, sd._base_ext(c, rows, "missing", needed=needed, contact="Camille Laurent (relationship manager)"))
    return c


def seed_testpack() -> Dict[str, Any]:
    """Create every pack case. Safe to call repeatedly: each case is dropped and re-created."""
    from app.services.v2.core import ext_store
    PACK.clear()
    ids: List[str] = []

    def mk(case_id, code, scenario, fn, path):
        c = fn()
        ext = xt.get_ext(c)
        ch = ext.get("change") or {}
        _add(case_id, code, scenario, path=path, counterparty=(c.get("creditor_party") or {}).get("party_name"), amount=c.get("amount"),
             currency=c.get("currency"), rail=c.get("payment_rail"), uetr=c.get("uetr"),
             change=(f"{ch.get('field_label')}: {(ch.get('original') or {}).get('value') or '(empty)'} -> {(ch.get('proposed') or {}).get('value') or '(from client reply)'}" if ch else ""),
             reason=c.get("reason"))
        ids.append(case_id)

    for row in lib.library()["profiles"]:
        code, path = row["code"], row["approval"]
        cid = f"TST-{code.replace('-', '')}-01"
        if code in CO_TWO_STEP:
            mk(cid, code, "CLEAN", lambda cid=cid, code=code: _compliance_case(cid, code), path)
        elif code in ST_DECISION:
            mk(cid, code, "CLEAN", lambda cid=cid, code=code: _st_case(cid, code), path)
        elif code == "DQ-01":
            mk(cid, code, "CLEAN", lambda cid=cid: _iban_case(cid), path)
        elif code == "DQ-03":
            mk(cid, code, "CLEAN", lambda cid=cid: _missing_iban_case(cid, "DQ-03"), path)
        elif code in ("CO-04", "CO-07"):
            mk(cid, code, "CLEAN", lambda cid=cid, code=code: _compliance_repair_case(cid, code), path)
        else:
            mk(cid, code, "CLEAN", lambda cid=cid, code=code: _repair_case(cid, code), path)

    mp = "MAKER_CHECKER"
    mk("TST-DQ01-02", "DQ-01", "RETURN_TO_MAKER", lambda: _iban_case("TST-DQ01-02", 9300), mp)
    mk("TST-DQ01-03", "DQ-01", "REJECT", lambda: _iban_case("TST-DQ01-03", 11800), mp)
    mk("TST-DQ01-04", "DQ-01", "ESCALATE", lambda: _iban_case("TST-DQ01-04", 15200), mp)
    mk("TST-DQ01-05", "DQ-01", "MISSING_INFO", lambda: _missing_iban_case("TST-DQ01-05"), mp)
    mk("TST-DQ01-06", "DQ-01", "CONFLICT", lambda: _conflict_case("TST-DQ01-06"), mp)
    mk("TST-DQ01-07", "DQ-01", "LOW_CONFIDENCE", lambda: _iban_case("TST-DQ01-07", 18900, low=True), mp)
    mk("TST-DQ01-08", "DQ-01", "DUAL_AUTHORISATION", lambda: _iban_case("TST-DQ01-08", 480000), mp)
    mk("TST-DQ01-09", "DQ-01", "SOD_BLOCK", lambda: _pending_iban_case("TST-DQ01-09", OPS_APPROVER, 7700), mp)
    mk("TST-DQ01-10", "DQ-01", "REVIEW_TICK", lambda: _pending_iban_case("TST-DQ01-10", MAKER, 8650), mp)
    mk("TST-DQ01-11", "DQ-01", "SLA_CHASE", lambda: _pending_iban_case("TST-DQ01-11", MAKER2, 6400, cutoff=12), mp)
    mk("TST-DQ01-12", "DQ-01", "BANK_REJECTS", lambda: _iban_case("TST-DQ01-12", 7200), mp)

    cp = "COMPLIANCE_THEN_RISK"
    mk("TST-CO01-02", "CO-01", "CONFIRM_BLOCK", lambda: _compliance_case("TST-CO01-02", "CO-01", 72000), cp)
    mk("TST-CO01-03", "CO-01", "ESCALATE", lambda: _compliance_case("TST-CO01-03", "CO-01", 54000), cp)
    mk("TST-CO01-04", "CO-01", "RISK_REJECTS", lambda: _compliance_case("TST-CO01-04", "CO-01", 91000), cp)

    mk("TST-ST05-02", "ST-05", "STOP_OPTION", lambda: _st_case("TST-ST05-02", "ST-05"), "SINGLE")
    mk("TST-ST07-02", "ST-07", "HOLD_OPTION", lambda: _st_case("TST-ST07-02", "ST-07"), "SINGLE")

    ext_store.flush()
    import json
    from pathlib import Path
    out = Path(__file__).resolve().parents[4] / "scripts" / "testpack_manifest.json"
    try:
        out.write_text(json.dumps(PACK, indent=1, default=str))
        (out.parent / "profiles_snapshot.json").write_text(json.dumps(lib.library()["profiles"], indent=1, default=str))
    except Exception:  # read-only checkout: the seed itself still worked
        pass
    return {"cases": len(ids), "ids": ids}
