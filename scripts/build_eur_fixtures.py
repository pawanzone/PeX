#!/usr/bin/env python3
"""Builds the Eurozone fixture pack in e2e_fixtures/eur/ (deterministic; valid MOD-97 IBANs, fictional parties).

Usage: python scripts/build_eur_fixtures.py
Writes one JSON per scenario plus manifest.json (expected outcome per fixture; used by tests/test_eur_pack.py).
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.services.synthetic_batch import gen_iban, transpose_invalid, iban_valid  # noqa: E402

OUT = ROOT / "e2e_fixtures" / "eur"
OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(2026)
MANIFEST = {}
N = [0]


def uetr():
    import uuid
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def base(slug, profile, domain, err, msg, rail, amount, debtor_cc, creditor_cc, ccy="EUR", creditor_name=None, expect=None, why="", **ev):
    N[0] += 1
    d_iban, d_bic, _ = gen_iban(debtor_cc, rng)
    c_iban, c_bic, c_bank = gen_iban(creditor_cc, rng)
    rec = {
        "exception_id": f"PEX-EUR-{slug.upper().replace('_', '-')}",
        "tenant_id": "DEFAULT_BANK", "profile_id": profile, "domain": domain,
        "error_code": err, "error_message": msg,
        "payment_info": {
            "payment_id": f"PMT-EUR-{N[0]:04d}", "uetr": uetr(), "amount": amount, "currency": ccy,
            "clearing_rail": rail, "value_date": "2026-10-20",
            "debtor_name": "Rheinland Maschinenbau Treasury GmbH", "debtor_account": d_iban, "debtor_agent_bic": d_bic,
            "creditor_name": creditor_name or "Delta Kaas BV", "creditor_account": c_iban, "creditor_agent_bic": c_bic,
            "remittance_info": f"INV-2026-{N[0]:05d}",
        },
        "bank_supplied_evidence": ev.get("bank", {}), "external_authoritative_evidence": ev.get("ext", {}),
        "derived_evidence": ev.get("derived", {}), "historical_evidence": ev.get("hist", {}),
        "evidence_provenance": "NON_PRODUCTION_DEMO", "test_status": "TEST_ONLY",
    }
    if ev.get("policy"):
        rec["bank_policy_overrides"] = ev["policy"]
    MANIFEST[f"{slug}.json"] = {"expect_stp": expect, "why": why, "profile": profile, "rail": rail}
    return rec, c_iban, c_bic, c_bank


def save(slug, rec):
    (OUT / f"{slug}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------- A. SEPA SCT: IBAN check-digit transposition (DQ-01) ----------------
names = {"DE": "Elbe Chemie GmbH", "FR": "Loire Composants SA", "NL": "Delta Kaas BV", "ES": "Levante Cerámica SL", "IT": "Brianza Tessuti SpA"}
for cc in ("DE", "FR", "NL", "ES", "IT"):
    rec, good, bic, bank = base(f"sct_dq01_{cc.lower()}_transposition", "DQ-01", "DATA_QUALITY", "ERR_INVALID_IBAN_CHECKSUM",
                                "Creditor IBAN MOD-97 check digit failure on pacs.008 (SEPA Credit Transfer).", "SEPA_SCT",
                                4200.0 + rng.randint(0, 900), "DE", cc, creditor_name=names[cc], expect=True,
                                why=f"{cc} IBAN transposition, repair evidenced by core DDA + scheme directory",
                                ext={"routing_directory": {"bank_code": "0", "sepa_reachable": True, "country": cc}})
    bad = transpose_invalid(good, rng)
    rec["payment_info"]["creditor_account"] = bad
    rec["bank_supplied_evidence"] = {"core_dda_account": good, "verified_iban": good}
    rec["external_authoritative_evidence"]["routing_directory"]["bank_code"] = bank
    rec["derived_evidence"] = {"mod97_calculated_checksum": good[2:4], "inbound_transposition_detected": True}
    rec["historical_evidence"] = {"historical_match_count": 9, "confidence_heuristic": 0.97}
    assert iban_valid(good) and not iban_valid(bad)
    save(f"sct_dq01_{cc.lower()}_transposition", rec)

rec, good, *_ = base("sct_dq01_de_missing_core_dda", "DQ-01", "DATA_QUALITY", "ERR_INVALID_IBAN_CHECKSUM",
                     "Creditor IBAN checksum failed; mandatory core DDA evidence missing.", "SEPA_SCT", 3300.0, "DE", "DE",
                     expect=False, why="mandatory CORE_DDA_ACCOUNT evidence missing -> fail closed",
                     ext={"routing_directory": {"bank_code": "37040044", "sepa_reachable": True}})
rec["payment_info"]["creditor_account"] = transpose_invalid(rec["payment_info"]["creditor_account"], rng)
save("sct_dq01_de_missing_core_dda", rec)

rec, good, *_ = base("sct_dq01_de_contradictory", "DQ-01", "DATA_QUALITY", "ERR_INVALID_IBAN_CHECKSUM",
                     "Creditor IBAN checksum failed; core DDA and SSI directory disagree.", "SEPA_SCT", 3300.0, "DE", "DE",
                     expect=False, why="core DDA IBAN != SSI directory IBAN -> contradictory evidence",
                     ext={"routing_directory": {"bank_code": "37040044", "sepa_reachable": True}})
other, _, _ = gen_iban("DE", rng)
rec["bank_supplied_evidence"] = {"core_dda_account": good, "verified_iban": good, "ssi_directory_account": other}
rec["payment_info"]["creditor_account"] = transpose_invalid(good, rng)
save("sct_dq01_de_contradictory", rec)

# ---------------- B. SEPA Instant ----------------
def inst(slug, profile, amount, ccy="EUR", expect=None, why="", elapsed="unset", **kw):
    if profile == "PR-07":
        bank = {"gateway_socket_state": {"gateway_id": "GW-SEPA-INST-01", "status": "HEALTHY", "connected": True},
                "idempotency_ledger_lock": {"lock_status": "ACQUIRED", "lock_key": f"IDEMP-{slug}"},
                "retry_budget_record": {"max_retries": 3, "retries_exhausted": 0, "can_retry": True}}
        if elapsed != "unset":
            bank["scheme_elapsed_ms"] = elapsed
        r, *_ = base(slug, "PR-07", "PROCESSING", "ERR_NETWORK_TIMEOUT", "SCT Inst pacs.008 sent, no pacs.002 received.", "SEPA_INST",
                     amount, "DE", "NL", ccy=ccy, expect=expect, why=why, bank=bank)
        return r
    if profile == "PR-09":
        r, *_ = base(slug, "PR-09", "PROCESSING", "ERR_HELD_FOR_REPAIR", "Instant payment placed in repair queue.", "SEPA_INST",
                     amount, "DE", "NL", ccy=ccy, expect=expect, why=why,
                     bank={"payment_hub_repair_queue": {"status": "HELD_IN_REPAIR", "syntax_error": "ERR_SYNTAX_TAG_UNCLOSED"},
                           "syntax_error_specification": {"tag": "<RmtInf>", "action": "CLOSE_UNCLOSED_REMITTANCE_TAG"}})
        return r
    if profile == "PR-04":
        r, *_ = base(slug, "PR-04", "PROCESSING", "ERR_CLEARING_CUTOFF_MISSED", "Cut-off missed.", "SEPA_INST", amount, "DE", "NL",
                     ccy=ccy, expect=expect, why=why,
                     bank={"rail_operating_calendar": {"rail": "SEPA_INST", "is_operating_day": True},
                           "rail_cutoff_schedule": {"rail": "SEPA_INST", "cutoff_utc": "23:59"},
                           "bank_cutoff_policy": {"cutoff_buffer_minutes": 15, "allow_auto_value_date_roll": True}})
        return r
    # DQ-01 on SEPA_INST
    r, good, bic, bank = base(slug, "DQ-01", "DATA_QUALITY", "ERR_INVALID_IBAN_CHECKSUM", "Instant payment rejected: IBAN check digit failure.",
                              "SEPA_INST", amount, "DE", "DE", ccy=ccy, expect=expect, why=why,
                              ext={"routing_directory": {"bank_code": "37040044", "sepa_reachable": True, "sct_inst_reachable": True}})
    r["payment_info"]["creditor_account"] = transpose_invalid(good, rng)
    r["bank_supplied_evidence"] = {"core_dda_account": good, "verified_iban": good}
    r["derived_evidence"] = {"mod97_calculated_checksum": good[2:4], "inbound_transposition_detected": True}
    r["historical_evidence"] = {"historical_match_count": 6, "confidence_heuristic": 0.96}
    return r


save("inst_dq01_within_limit", inst("inst_dq01_within_limit", "DQ-01", 2500.0, expect=True, why="EUR, below limit: repair allowed"))
save("inst_dq01_over_limit", inst("inst_dq01_over_limit", "DQ-01", 150000.0, expect=False, why="above SCT Inst limit EUR 100,000 -> human"))
save("inst_dq01_wrong_currency", inst("inst_dq01_wrong_currency", "DQ-01", 2500.0, ccy="GBP", expect=False, why="SEPA Instant is EUR only"))
save("inst_pr07_timeout_exceeded", inst("inst_pr07_timeout_exceeded", "PR-07", 1800.0, expect=False, elapsed=12400,
                                        why="10 s scheme timeout exceeded: no blind retry/hold -> status inquiry/return review"))
save("inst_pr07_unknown_timeout_state", inst("inst_pr07_unknown_timeout_state", "PR-07", 1800.0, expect=False,
                                             why="no elapsed-time evidence: cannot prove retry is safe"))
save("inst_pr07_within_window", inst("inst_pr07_within_window", "PR-07", 1800.0, expect=None, elapsed=3100,
                                     why="within 10 s window: overlay does not block (engine decides)"))
save("inst_pr09_hold_not_allowed", inst("inst_pr09_hold_not_allowed", "PR-09", 1800.0, expect=False, why="instant payments cannot be held for repair"))
save("inst_pr04_cutoff_not_applicable", inst("inst_pr04_cutoff_not_applicable", "PR-04", 1800.0, expect=False, why="24/7 rail: no cut-off / value-date roll"))

# ---------------- C. T2 cut-off missed ----------------
def t2(slug, allow, expect, why):
    pol = None
    if not allow:
        pol = {"policy_id": "POL-NO-AUTO-ROLL", "policy_version": "v1.0.0", "environment": "TEST_ONLY",
               "w1_cutoff_buffer": {"cutoff_buffer_minutes": 15, "allow_auto_value_date_roll": False, "max_value_date_roll_days": 3,
                                    "require_client_roll_authorization": True}}
    r, *_ = base(slug, "PR-04", "PROCESSING", "ERR_CLEARING_CUTOFF_MISSED", "Instruction reached T2 after the customer-payment cut-off.", "T2",
                 8500.0, "DE", "FR", expect=expect, why=why,
                 bank={"rail_operating_calendar": {"rail": "T2", "is_operating_day": True},
                       "rail_cutoff_schedule": {"rail": "T2", "cutoff_utc": "16:00"},
                       "bank_cutoff_policy": {"cutoff_buffer_minutes": 15, "allow_auto_value_date_roll": allow}}, policy=pol)
    return r


save("t2_pr04_cutoff_roll_allowed", t2("t2_pr04_cutoff_roll_allowed", True, True, "policy allows a next-business-day roll"))
save("t2_pr04_cutoff_policy_blocked", t2("t2_pr04_cutoff_policy_blocked", False, False, "bank policy forbids autonomous value-date roll -> human"))

# ---------------- D. SEPA return reason codes ----------------
CODES = {"AC01": True, "AC04": True, "AC06": False, "AM04": False, "MS03": False, "RR04": False, "XX99": False}
for code, ok in CODES.items():
    r, *_ = base(f"sepa_return_{code.lower()}", "ST-01", "SETTLEMENT_RETURNS", "ERR_INWARD_RETURN_RECEIVED",
                 f"Inward pacs.004 return received (Return Reason {code}). Original debit posted.", "SEPA_SCT", 2800.0, "DE", "NL",
                 expect=ok, why=("STP-capable return reason" if ok else "needs human/compliance decision (or unknown code: fail closed)"),
                 bank={"original_debit_record": {"original_debit_posted": True, "original_uetr": uetr(), "ledger_account": "DE00"},
                       "original_debit_posted": True},
                 ext={"inward_pacs004_return": {"return_reason_code": code, "return_amount": 2800.0, "originating_bic": "INGBNL2AXXX"}},
                 derived={"amount_currency_match": True})
    save(f"sepa_return_{code.lower()}", r)
r, *_ = base("sepa_return_ac04_original_not_found", "ST-01", "SETTLEMENT_RETURNS", "ERR_INWARD_RETURN_UNMATCHED",
             "Return AC04 received but original debit cannot be found.", "SEPA_SCT", 2800.0, "DE", "NL", expect=False,
             why="original debit not found -> fail closed",
             ext={"inward_pacs004_return": {"return_reason_code": "AC04"}}, derived={"original_debit_posted": False})
save("sepa_return_ac04_original_not_found", r)

# ---------------- E. EU Verification of Payee ----------------
for status, score in (("CLOSE_MATCH", 0.88), ("NO_MATCH", 0.12), ("NOT_POSSIBLE", 0.0)):
    r, c_iban, *_ = base(f"eu_vop_{status.lower()}", "DQ-09", "DATA_QUALITY", "ERR_BENEFICIARY_NAME_MISMATCH",
                         "Verification of Payee returned a name variation.", "SEPA_SCT", 8000.0, "DE", "DE",
                         creditor_name="ELBE CHEMIE", expect=False,
                         why=f"VoP {status}: payer decision / human review required, no autonomous alignment")
    r["bank_supplied_evidence"] = {"core_account_title": {"account_number": c_iban, "account_title": "ELBE CHEMIE GMBH", "status": "ACTIVE"},
                                   "verification_of_payee_confirmation": {"match_score": score, "match_status": status}}
    save(f"eu_vop_{status.lower()}", r)

# ---------------- F. CBPR+ structured postal address (DQ-05) ----------------
ADDR = {
    "nl": ("NL", "Keizersgracht 123", "1015 CJ Amsterdam", "NL", "Delta Kaas BV"),
    "es": ("ES", "Calle Mayor 5", "28013 Madrid", "ES", "Levante Cerámica SL"),
    "it": ("IT", "Via Roma 10", "10121 Torino", "IT", "Brianza Tessuti SpA"),
    "fr": ("FR", "12 Rue de la Paix", "75002 Paris", "FR", "Loire Composants SA"),
    "de": ("DE", "Bahnhofstrasse 42", "60329 Frankfurt am Main", "DE", "Elbe Chemie GmbH"),
}
for k, (cc, street, towncode, ctry, nm) in ADDR.items():
    xml = f"<PstlAdr><AdrLine>{street}</AdrLine><AdrLine>{towncode}</AdrLine><Ctry>{ctry}</Ctry></PstlAdr>"
    r, *_ = base(f"cbpr_dq05_{k}_unstructured", "DQ-05", "DATA_QUALITY", "ERR_INVALID_POSTAL_ADDRESS",
                 "CBPR+ validation: creditor postal address only unstructured (AdrLine).", "SWIFT_CBPR+", 5400.0, "DE", cc,
                 creditor_name=nm, expect=True, why="every structured field traceable to inbound text",
                 bank={"creditor_postal_address": xml})
    save(f"cbpr_dq05_{k}_unstructured", r)

r, *_ = base("cbpr_dq05_de_ambiguous_postcode", "DQ-05", "DATA_QUALITY", "ERR_INVALID_POSTAL_ADDRESS",
             "Unstructured address with two conflicting postal codes.", "SWIFT_CBPR+", 5400.0, "DE", "DE", expect=False,
             why="two plausible postal codes -> R_uniq false",
             bank={"creditor_postal_address": "<PstlAdr><AdrLine>Bahnhofstrasse 42</AdrLine><AdrLine>60329 / 60311 Frankfurt</AdrLine><Ctry>DE</Ctry></PstlAdr>"})
save("cbpr_dq05_de_ambiguous_postcode", r)

r, *_ = base("cbpr_dq05_untraceable_components", "DQ-05", "DATA_QUALITY", "ERR_INVALID_POSTAL_ADDRESS",
             "Address text lacks street/postal code: nothing may be invented.", "SWIFT_CBPR+", 5400.0, "DE", "DE", expect=False,
             why="resolver would default street/postcode/town; traceability guard fails closed",
             bank={"creditor_postal_address": "<PstlAdr><AdrLine>Elbe Chemie GmbH, near the harbour</AdrLine><Ctry>DE</Ctry></PstlAdr>"})
save("cbpr_dq05_untraceable_components", r)

r, *_ = base("cbpr_dq05_missing_address_evidence", "DQ-05", "DATA_QUALITY", "ERR_INVALID_POSTAL_ADDRESS",
             "No address evidence supplied.", "SWIFT_CBPR+", 5400.0, "DE", "DE", expect=False, why="mandatory CREDITOR_POSTAL_ADDRESS missing")
save("cbpr_dq05_missing_address_evidence", r)

(OUT / "manifest.json").write_text(json.dumps(MANIFEST, indent=2), encoding="utf-8")
print(f"wrote {len(MANIFEST)} fixtures to {OUT}")
