"""Per-case v2 extension data: derivation for ANY case (seeded, batch pipeline, watcher), evidence rows, change summaries."""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.db.repository import PeXDBRepository  # noqa: F401  (typing only)
from app.services.data_loader import repo
from app.services.v2.core import (
    ext_store, now, parse_ts, iso, profile_code, profile_spec, domain_of, is_compliance, party_name, account_str,
)

EXT_VERSION = 1


# ----------------------------------------------------------------------------------------------
# IBAN helpers (real MOD-97)
# ----------------------------------------------------------------------------------------------
def iban_compact(s: Any) -> str:
    return re.sub(r"\s+", "", str(s or "")).upper()


def iban_group(s: Any) -> str:
    c = iban_compact(s)
    return " ".join(c[i:i + 4] for i in range(0, len(c), 4))


def iban_valid(s: Any) -> bool:
    c = iban_compact(s)
    if len(c) < 15 or not c[:2].isalpha() or not c[2:4].isdigit():
        return False
    try:
        return int("".join(str(int(ch, 36)) for ch in (c[4:] + c[:4]))) % 97 == 1
    except ValueError:
        return False


def looks_like_iban(s: Any) -> bool:
    c = iban_compact(s)
    return len(c) >= 15 and c[:2].isalpha() and c[2:4].isdigit()


def highlight_positions(a: str, b: str) -> Optional[List[int]]:
    """Character indexes (in the displayed strings) where two same-length values differ."""
    if not a or not b or len(a) != len(b):
        return None
    pos = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return pos or None


FIELD_LABELS = {
    "creditor_account.iban": "Creditor IBAN", "creditor_account.account_number": "Creditor account number",
    "creditor_agent.bic": "Creditor bank BIC", "creditor_agent.aba_routing": "Creditor routing number (ABA)",
    "creditor.name": "Beneficiary name", "remittance_info.structured": "Remittance information",
    "payment.value_date": "Value date", "purpose_code": "Purpose code", "remittance_info": "Remittance reference",
}


def field_label(path: str) -> str:
    return FIELD_LABELS.get(path, path.replace("_", " ").replace(".", " · ").capitalize())


def build_change(field_path: str, original: Any, proposed: Any, source: str = "", risk: str = "Low",
                 policy_basis: str = "", what_changes: Optional[str] = None, justification: str = "") -> Dict[str, Any]:
    o_raw = "" if original is None else str(original)
    p_raw = "" if proposed is None else str(proposed)
    is_iban = looks_like_iban(o_raw) or looks_like_iban(p_raw) or field_path.endswith("iban")
    o_disp = iban_group(o_raw) if is_iban and o_raw else o_raw
    p_disp = iban_group(p_raw) if is_iban and p_raw else p_raw
    o_status = p_status = None
    if is_iban:
        o_status = "Passes validation" if iban_valid(o_raw) else "Failed validation"
        p_status = "Passes validation" if iban_valid(p_raw) else "Failed validation"
    elif p_raw:
        o_status, p_status = ("Missing" if not o_raw else "Original value"), "Validated"
    hl = highlight_positions(o_disp, p_disp) if is_iban else None
    return {
        "what_changes": what_changes or f"{field_label(field_path)} corrected",
        "field": field_path, "field_label": field_label(field_path),
        "original": {"value": o_disp, "status": o_status, "highlight": hl},
        "proposed": {"value": p_disp, "status": p_status, "highlight": hl},
        "source": source, "risk": risk, "policy_basis": policy_basis, "justification": justification,
        "if_you_approve": "PeX hands the repaired instruction to the bank payment system. The bank executes and confirms. "
                          "Nothing is executed by PeX.",
    }


# ----------------------------------------------------------------------------------------------
# Evidence rows
# ----------------------------------------------------------------------------------------------
TIER_LABEL = {"bank_supplied": "Bank supplied", "external_authoritative": "Authoritative", "derived": "Derived",
              "historical": "Context only"}


def pretty(t: Any) -> str:
    return str(t).replace("_", " ").strip().capitalize()


def row(rid: str, check: str, result: str, source: str, authority: str, status: str, label: str,
        checked_at: Optional[str] = None, raw: Optional[dict] = None, kind: Optional[str] = None, item: Optional[str] = None) -> Dict[str, Any]:
    """`kind` is the type of check (checksum, directory, vop, history, ...); `item` names the expected-evidence item it covers when the
    kind alone does not say. Both let the AI view link its checklist to the checks that were run."""
    r = {"id": rid, "check": check, "result": result, "source": source, "authority": authority, "status": status,
         "status_label": label, "checked_at": checked_at or iso(now()), "can_view_source": True, "raw": raw or {}}
    if kind:
        r["kind"] = kind
    if item:
        r["item"] = item
    return r


def evidence_state_from_rows(rows: List[Dict[str, Any]], hint: Optional[str] = None) -> str:
    if any(r["status"] == "differs" for r in rows) or hint == "conflict":
        return "conflict"
    if any(r["status"] == "missing" for r in rows) or hint == "missing":
        return "missing"
    return "complete"


def rows_from_e2e(e2e_input, output) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    ts = iso(now())
    n = 0
    # deterministic repair checks (computed, never claimed)
    for rf in (output.repaired_fields or []):
        fp = str(rf.get("field_path", ""))
        ov, pv = rf.get("original_value"), rf.get("repaired_value")
        if fp.endswith("iban") or looks_like_iban(ov) or looks_like_iban(pv):
            n += 1
            rows.append(row(f"ev-{n}", "Creditor IBAN checksum",
                            f"Original {'passes' if iban_valid(ov) else 'fails'} mod-97; proposed {'passes' if iban_valid(pv) else 'fails'} mod-97",
                            "Payment instruction", "Deterministic check", "pass" if iban_valid(pv) else "fail",
                            "Passed" if iban_valid(pv) else "Failed", ts))
    srcs = {}
    for tier, d in (("bank_supplied", e2e_input.bank_supplied_evidence), ("external_authoritative", e2e_input.external_authoritative_evidence),
                    ("derived", e2e_input.derived_evidence), ("historical", e2e_input.historical_evidence)):
        for k in (d or {}):
            srcs[str(k).lower()] = tier
    for t in (output.evidence_used or []):
        n += 1
        tier = srcs.get(str(t).lower())
        rows.append(row(f"ev-{n}", pretty(t), "Available and consistent", TIER_LABEL.get(tier, "Evidence package"),
                        TIER_LABEL.get(tier, "Supporting"), "agree", "Agree", ts))
    for t in (output.evidence_missing or []):
        n += 1
        rows.append(row(f"ev-{n}", pretty(t), "Not found in any searched source", "Searched sources", "—", "missing", "Missing", ts))
    for c in (output.evidence_contradictions or []):
        n += 1
        rows.append(row(f"ev-{n}", "Contradicting evidence", str(c), "Evidence package", "Conflicting", "differs", "Differs", ts))
    return rows


def conflict_from_e2e(output) -> Optional[Dict[str, Any]]:
    if not output.evidence_contradictions:
        return None
    return {
        "field": "Evidence under review",
        "sources": [{"name": f"Contradiction {i + 1}", "value": str(c), "relation": "differs", "authority": "Conflicting",
                     "tag": "Differs", "changed_at": None} for i, c in enumerate(output.evidence_contradictions)],
        "note": "Sources contradict each other. Validation alone cannot decide which is correct.",
    }


def ext_from_e2e(case_dict: Dict[str, Any], e2e_input, output, batch_id: Optional[str] = None,
                 record_index: Optional[int] = None) -> Dict[str, Any]:
    """Build and store the v2 extension for a case created by the E2E pipeline (batch or file watcher)."""
    rows = rows_from_e2e(e2e_input, output)
    state = {"CONTRADICTORY": "conflict", "INSUFFICIENT": "missing"}.get(str(output.evidence_status).upper())
    state = evidence_state_from_rows(rows, state)
    change = None
    for rf in (output.repaired_fields or []):
        if "original_value" in rf or "repaired_value" in rf:
            change = build_change(str(rf.get("field_path", "")), rf.get("original_value"), rf.get("repaired_value"),
                                  source="PeX deterministic resolver", risk="Low" if float(case_dict.get("amount", 0)) < 250000 else "High",
                                  policy_basis="One approver" if float(case_dict.get("amount", 0)) < 250000 else "Dual authorisation (>= 250,000)",
                                  justification=output.resolution_basis or "")
            break
    pb = output.predicate_breakdown
    pr = e2e_input.payment_info
    d = {
        "v": EXT_VERSION, "source": "e2e",
        "cutoff_at": case_dict.get("sla_due_at"),
        "assignee": None,
        "counterparty": pr.creditor_name or party_name(case_dict.get("creditor_party")),
        "debtor": pr.debtor_name or party_name(case_dict.get("debtor_party")),
        "evidence": rows, "evidence_state": state,
        "evidence_inputs": {"status": output.evidence_status, "missing": list(output.evidence_missing or []),
                            "contradictions": list(output.evidence_contradictions or [])},
        "change": change,
        "conflict": conflict_from_e2e(output),
        "stp": {"eligible": bool(output.stp_eligible), "reason": output.stp_decision_reason,
                "predicates": {k: bool(getattr(pb, k)) for k in ("e_suff", "r_det", "r_uniq", "v_det", "v_auth", "p_bank", "c_comp", "x_pre")}},
        "recommended_action": (output.resolution_recommendation or {}).get("action") if isinstance(output.resolution_recommendation, dict) else None,
        "resolution_basis": output.resolution_basis,
        "compliance_status": output.compliance_status,
        "approval_requirement": output.approval_requirement,
        "next_action_hint": output.next_action,
        "batch": ({"batch_id": batch_id, "record": record_index} if batch_id else None),
        "last_change_at": iso(now()),
    }
    return d


# ----------------------------------------------------------------------------------------------
# Derivation for cases without stored ext (old seed, anything created outside the v2 paths)
# ----------------------------------------------------------------------------------------------
def _latest_ts(case: Dict[str, Any]) -> Optional[str]:
    tl = case.get("audit_timeline") or []
    if tl:
        return str(tl[-1].get("timestamp"))
    return case.get("created_at")


def derive_ext(case: Dict[str, Any]) -> Dict[str, Any]:
    cid = case["case_id"]
    rec = repo.recommendations.get(cid)
    created = parse_ts(case.get("created_at")) or now()
    cut = parse_ts(case.get("sla_due_at")) or (created + timedelta(hours=4))
    rows: List[Dict[str, Any]] = []
    n = 0
    state_hint = None
    change = None
    if rec is not None:
        for st in (rec.step_by_step_assessment or []):
            n += 1
            ok = bool(getattr(st, "is_passed", True))
            rows.append(row(f"ev-{n}", str(st.step_title), str(st.proof_detail), "PeX control", "Deterministic check",
                            "pass" if ok else "fail", "Passed" if ok else "Failed", case.get("created_at")))
        for ev in (rec.corroborating_evidence or []):
            n += 1
            rows.append(row(f"ev-{n}", pretty(ev.evidence_type), str(ev.citation), pretty(ev.evidence_type), "Supporting", "agree", "Agree",
                            case.get("created_at"), {"evidence_id": ev.evidence_id}))
        at = str(getattr(rec.action_type, "value", rec.action_type))
        if at == "INSUFFICIENT_EVIDENCE":
            state_hint = "missing"
        if rec.ambiguity_detected:
            state_hint = "conflict"
        if rec.proposed_changes:
            pc = rec.proposed_changes[0]
            change = build_change(pc.field_path, pc.original_value_masked, pc.proposed_value_masked, source="PeX recommendation",
                                  risk=str(getattr(rec.risk_evaluation.risk_level, "value", rec.risk_evaluation.risk_level)).title(),
                                  policy_basis=("One approver" if float(case.get("amount", 0)) < 250000 else "Dual authorisation (>= 250,000)"),
                                  justification=pc.justification)
    else:
        for t in (profile_spec(case.get("profile")).get("mandatory_evidence") or []):
            n += 1
            rows.append(row(f"ev-{n}", pretty(t), "Not yet gathered", "Evidence plan", "—", "missing", "Missing", case.get("created_at")))
        state_hint = "missing"
    return {
        "v": EXT_VERSION, "source": "derived", "derived": True,
        "cutoff_at": iso(cut), "assignee": None,
        "counterparty": party_name(case.get("creditor_party")), "debtor": party_name(case.get("debtor_party")),
        "evidence": rows, "evidence_state": evidence_state_from_rows(rows, state_hint),
        "change": change, "conflict": None, "stp": None,
        "last_change_at": _latest_ts(case),
    }


def get_ext(case: Dict[str, Any]) -> Dict[str, Any]:
    """Stored extension if any, else derived (cached in memory, persisted when an action changes it)."""
    cid = case["case_id"]
    e = ext_store.get(cid)
    if e is not None:
        return e
    d = derive_ext(case)
    ext_store.put(cid, d, persist=False)
    return d


def persist_ext(case_id: str, data: Dict[str, Any]):
    ext_store.put(case_id, data, persist=True)
    ext_store.flush()
