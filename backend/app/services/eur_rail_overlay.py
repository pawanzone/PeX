"""Eurozone rail rules overlay for the E2E harness (P0.5 demo build).

What is REAL LOGIC here (deterministic, unit-testable, fail-closed):
  * SEPA Instant (rail ``SEPA_INST``): EUR only, per-payment amount limit, 10-second scheme timeout semantics
    (an instant payment cannot be *held* or *value-date rolled*; after a timeout the originator must NOT blindly
    retry because the beneficiary side may already have credited -> human status inquiry / return review).
  * SEPA return reason codes (ISO ExternalReturnReason1Code: AC01, AC04, AC06, AM04, MS03, RR04) mapped to
    ST-01/02/03-style handling. Only AC01/AC04 (account-data returns with a posted original debit) can be STP;
    AC06 (blocked) / RR04 (regulatory) go to human/compliance; AM04 / MS03 go to human review.
  * EU Verification of Payee (Instant Payments Regulation): only a full ``MATCH`` proceeds autonomously;
    ``CLOSE_MATCH`` needs the payer's confirmation, ``NO_MATCH`` / ``NOT_POSSIBLE`` go to a human.
  * DQ-05 CBPR+ structured postal address repair via ``dq05_transformer`` with a traceability guard: every
    structured component must be traceable to the inbound text (or to the bank's address master); nothing is invented.

What is SEEDED REFERENCE DATA (a real bank replaces it through configuration):
  * the SCT Inst limit (EUR 100,000 default), the 10 s timeout, the T2 / SEPA cut-off times (calendar adapter),
  * the reason-code policy table below, the sample bank/IBAN directories in the generator.

PeX never executes or settles: every outcome here only decides whether the instruction package may be
handed to the BANK autonomously or must go to a human first.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

EU_SCHEME_RAILS = {"SEPA_SCT", "SEPA_INST", "T2"}

SCT_INST_TIMEOUT_MS = int(os.getenv("PEX_SCT_INST_TIMEOUT_MS", "10000"))
SCT_INST_DEFAULT_LIMIT_EUR = float(os.getenv("PEX_SCT_INST_LIMIT_EUR", "100000"))

# code -> (handling, stp_allowed, action, rationale)
SEPA_RETURN_POLICY: Dict[str, Tuple[str, bool, str, str]] = {
    "AC01": ("ST-01", True, "RECREDIT_DEBTOR_LEDGER_AND_REQUEST_CORRECT_ACCOUNT",
             "IncorrectAccountNumber: return of funds; re-credit debtor once the original debit is verified."),
    "AC04": ("ST-02", True, "RECREDIT_DEBTOR_LEDGER_AND_FLAG_BENEFICIARY_ACCOUNT_CLOSED",
             "ClosedAccountNumber: re-credit debtor, flag beneficiary account as closed; never resend to the same account."),
    "AC06": ("ST-03", False, "HOLD_FOR_COMPLIANCE_REVIEW_BLOCKED_ACCOUNT",
             "BlockedAccount: may be legally or sanctions driven - never autonomous."),
    "AM04": ("TR-02", False, "HUMAN_REVIEW_INSUFFICIENT_FUNDS_RETURN",
             "InsufficientFunds: needs a human to confirm which side lacked funds and whether to represent."),
    "MS03": ("ST-01", False, "HUMAN_REVIEW_REASON_NOT_SPECIFIED",
             "NotSpecifiedReasonAgentGenerated: reason unknown - investigate with the counterparty bank before any re-credit."),
    "RR04": ("CO-04", False, "ROUTE_TO_COMPLIANCE_REGULATORY_REASON",
             "RegulatoryReason: statutory reason - compliance decision required."),
}

VOP_PROCEEDS = {"MATCH"}


class RailOutcome(dict):
    """Dict with attribute-style access to keep the runner hook small."""
    __getattr__ = dict.get


def _block(basis: str, action: str, notes: List[str]) -> Dict[str, Any]:
    return {"block": True, "basis": basis, "rec": {"action": action, "route": "HUMAN_REVIEW", "execution_owner": "BANK"},
            "notes": notes + [basis]}


def evaluate_rail_rules(profile: str, pmt: Any, ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return None when no EU rule applies, else {'block': bool, 'basis': str, 'rec': dict|None, 'notes': [...]}."""
    rail = (pmt.clearing_rail or "").upper()
    profile = (profile or "").upper()
    notes: List[str] = []
    ccy = (pmt.currency or "").upper()

    # ---- SEPA Instant -------------------------------------------------------------------------
    if rail == "SEPA_INST":
        if ccy != "EUR":
            return _block(f"SEPA Instant is EUR only (got {ccy}).", "RETURN_OR_REROUTE_REVIEW", notes)
        limit = float(ctx.get("sepa_inst_limit_eur") or SCT_INST_DEFAULT_LIMIT_EUR)
        if float(pmt.amount) > limit:
            return _block(f"Amount {pmt.amount:.2f} exceeds the SCT Inst limit EUR {limit:,.0f}; cannot complete as instant.",
                          "CONVERT_TO_SCT_OR_RETURN_REVIEW", notes)
        if profile in ("PR-04", "PR-09"):
            return _block("SEPA Instant is 24/7/365: no cut-off to miss and a payment cannot be held for repair "
                          "(value-date roll / hold not applicable). Reject or return decision needed.",
                          "REJECT_OR_RETURN_REVIEW_NO_HOLD", notes)
        if profile == "PR-07":
            elapsed = ctx.get("scheme_elapsed_ms")
            timed_out = bool(ctx.get("instant_timeout_exceeded")) or (isinstance(elapsed, (int, float)) and elapsed > SCT_INST_TIMEOUT_MS)
            if elapsed is None and not ctx.get("instant_timeout_exceeded"):
                return _block("SCT Inst timeout state unknown (no scheme_elapsed_ms evidence): cannot prove a retry is safe.",
                              "STATUS_INQUIRY_BEFORE_ANY_RETRY", notes)
            if timed_out:
                return _block(f"SCT Inst 10-second timeout exceeded ({elapsed} ms). The beneficiary PSP may already have credited: "
                              "no blind retry, no hold - status inquiry and return/reject review.",
                              "STATUS_INQUIRY_AND_RETURN_REVIEW", notes)
            notes.append(f"SCT Inst within 10 s window ({elapsed} ms).")
        return {"block": False, "notes": notes}

    if rail not in EU_SCHEME_RAILS:
        return None

    # ---- SEPA return reason codes (ST-01/02/03 style) -----------------------------------------
    if profile == "ST-01":
        ret = ctx.get("inward_pacs004_return") or {}
        code = str(ret.get("return_reason_code") or ctx.get("return_reason_code") or "").upper()
        if code in SEPA_RETURN_POLICY:
            handling, stp_ok, action, why = SEPA_RETURN_POLICY[code]
            notes.append(f"SEPA return {code} -> {handling}-style handling: {why}")
            if not stp_ok:
                return _block(f"Return reason {code} requires a human decision ({why})", action, notes)
            return {"block": False, "notes": notes, "rec_action": action, "handling": handling}
        return _block(f"Unrecognised or missing SEPA return reason code '{code}': fail closed.", "HUMAN_REVIEW_UNKNOWN_RETURN_REASON", notes)

    # ---- EU Verification of Payee ---------------------------------------------------------------
    if profile == "DQ-09":
        vop = ctx.get("verification_of_payee_confirmation") or {}
        status = str(vop.get("match_status") or "").upper()
        if status in VOP_PROCEEDS:
            return {"block": False, "notes": ["EU VoP: MATCH."]}
        reasons = {
            "CLOSE_MATCH": ("EU VoP CLOSE_MATCH: the payer must be shown the registered name and confirm before proceeding; "
                            "PeX must not silently align the beneficiary title.", "REQUEST_PAYER_CONFIRMATION_OF_VOP_NAME"),
            "NO_MATCH": ("EU VoP NO_MATCH: warn the payer; do not release without explicit payer decision.", "HOLD_AND_WARN_PAYER_VOP_NO_MATCH"),
        }
        basis, action = reasons.get(status, (f"EU VoP result '{status or 'MISSING'}' (NOT_POSSIBLE/unavailable): human decision required.",
                                             "HUMAN_REVIEW_VOP_NOT_POSSIBLE"))
        return _block(basis, action, notes)

    return None


# ----------------------------------------------------------------------------------------------
# DQ-05: CBPR+ structured postal address
# ----------------------------------------------------------------------------------------------
_POSTCODE = {
    "DE": r"^\d{5}$", "FR": r"^\d{5}$", "ES": r"^\d{5}$", "IT": r"^\d{5}$", "NL": r"^\d{4}\s?[A-Z]{2}$",
    "BE": r"^\d{4}$", "AT": r"^\d{4}$", "GB": r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", "US": r"^\d{5}(-\d{4})?$",
}


def resolve_dq05(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic DQ-05 resolution. Returns dict(r_det, r_uniq, v_det, repaired_fields, rec, basis)."""
    from app.services.dq05_address_resolver import dq05_transformer, VALID_ISO_COUNTRIES

    fail = lambda why: {"r_det": False, "r_uniq": False, "v_det": False, "repaired_fields": [], "rec": None, "basis": why}  # noqa: E731
    raw = ctx.get("creditor_postal_address")
    master = ctx.get("core_address_master") if isinstance(ctx.get("core_address_master"), dict) else None
    if not isinstance(raw, str) or not raw.strip():
        return fail("No inbound creditor postal address text (creditor_postal_address) to structure.")
    try:
        res = dq05_transformer.parse_and_resolve(raw, beneficiary_master_data=master)
    except Exception as e:  # resolver defects must fail closed, never crash the pipeline
        return fail(f"Address resolver error ({type(e).__name__}: {e}); fail closed.")
    if not res.success or not res.parsed_address:
        return fail(f"Address could not be deterministically parsed: {res.error_message or 'unknown'}")
    pa = res.parsed_address
    if not master:  # traceability guard: nothing may be invented
        hay = re.sub(r"\s+", " ", raw).lower()
        for label, val in (("street", pa.street_name), ("building number", pa.building_number),
                           ("postal code", pa.post_code), ("town", pa.town_name)):
            if not val or re.sub(r"\s+", " ", str(val)).lower() not in hay:
                return fail(f"Structured {label} '{val}' is not traceable to the inbound address text and no bank address master "
                            f"was supplied; refusing to infer (fail closed).")
    country_ok = pa.country_code in VALID_ISO_COUNTRIES
    pat = _POSTCODE.get(pa.country_code)
    postcode_ok = (not pat) or bool(pa.post_code and re.match(pat, pa.post_code.upper()))
    cbpr_ok = bool(pa.town_name and country_ok)  # CBPR+: TwnNm + Ctry mandatory
    v_det = bool(res.semantic_preservation_passed and cbpr_ok and postcode_ok)
    structured = pa.model_dump(exclude_none=True)
    basis = ("Unstructured postal address converted to ISO 20022 / CBPR+ structured fields ("
             f"{pa.town_name}, {pa.country_code} {pa.post_code}); semantic invariants preserved.")
    if res.is_ambiguous:
        basis = "Ambiguous address interpretation: " + "; ".join(res.ambiguity_reasons)
    elif not v_det:
        basis = "Structured address failed deterministic validation (postcode pattern / CBPR+ mandatory fields)."
    return {
        "r_det": True, "r_uniq": not res.is_ambiguous, "v_det": v_det,
        "repaired_fields": [{"field_path": "creditor.postal_address", "original_value": raw[:240], "repaired_value": structured}],
        "rec": {"action": "STRUCTURE_POSTAL_ADDRESS", "structured": structured, "iso20022_xml": pa.to_iso20022_xml_snippet()},
        "basis": basis,
    }
