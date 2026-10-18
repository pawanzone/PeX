"""Batch approval of low-risk repairs (one-click supervised STP): review + approve.

Autonomous zero-touch STP stays governed by settings.STP_MAX_AMOUNT (default 10,000). This screen is the HUMAN
one-click batch tier: an approver releases validated micro-repairs under settings.BATCH_APPROVAL_MAX_AMOUNT (default 25,000,
compared in the payment currency, no FX). Every release goes through the outbound port (mode aware) and records an
approval + audit event per case.
"""
from __future__ import annotations

import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import settings
from app.schemas.approval import ApprovalAction, ApprovalRecord, UserRole
from app.schemas.recommendation import ProposedFieldChange
from app.services.data_loader import repo
from app.services.outbound_port import operation_mode, dispatch_to_bank_handoff, resolve_handoff_state
from app.services.state_machine import transition_case, IllegalTransition
from app.services.v2 import logic as lg
from app.services.v2 import ext as xt
from app.services.v2.actions import audit, touch, MICRO_POLICY_VERSION, actor_label
from app.services.v2.core import (
    V2Error, invalid, require, now, iso, money, rail_obj, profile_code, profile_label, is_compliance, role_of, HARD_BLOCK_STP,
)

RULE_ID = "MR-01"


def limit_amount() -> float:
    return float(settings.BATCH_APPROVAL_MAX_AMOUNT)


def policy_text() -> str:
    return f"Micro-repair {RULE_ID} · under {limit_amount():,.0f} · validated · evidence complete"


def is_candidate(case: Dict[str, Any], ext: Dict[str, Any]) -> bool:
    return lg.status_of(case) in ("RECOMMENDED", "VALIDATED") and (str(case.get("queue")) == "STP Fast-Lane" or bool(ext.get("batch_candidate")))


def evaluate(case: Dict[str, Any]) -> Dict[str, Any]:
    ext = lg.ext_of(case)
    chips_ok = [{"label": "Validated", "tone": "success"}, {"label": "Evidence complete", "tone": "success"},
                {"label": "No open hold", "tone": "success"}, {"label": "Within limit", "tone": "success"}]
    code = profile_code(case.get("profile"))
    ch = ext.get("change")
    es = lg.evidence_state(ext)
    reason = None
    if is_compliance(case) or str(ext.get("compliance_status") or "").upper() in ("SANCTIONS_HOLD", "AML_SUSPENDED"):
        reason = ("COMPLIANCE_HOLD", "Compliance hold", "An open compliance hold blocks batch approval.")
    elif es == "conflict":
        reason = ("EVIDENCE_CONFLICT", "Evidence conflict", "Sources disagree; a person must resolve the conflict first.")
    elif es == "missing":
        reason = ("EVIDENCE_MISSING", "Evidence incomplete", "Required evidence is missing.")
    elif ext.get("validation_failed") or not ch or (ch.get("proposed") or {}).get("status") == "Failed validation":
        reason = ("VALIDATION_FAILED", "Validation failed", ext.get("validation_failed") or "The proposed value does not pass validation.")
    elif code in HARD_BLOCK_STP:
        reason = ("HARD_BLOCK", "Not permitted for straight-through", f"{code} can never be released in a batch.")
    elif float(case.get("amount") or 0) >= limit_amount():
        reason = ("ABOVE_LIMIT", "Above batch limit", f"Amount is not under the {limit_amount():,.0f} micro-repair limit.")
    if reason:
        return {"eligible": False, "code": reason[0], "reason_label": reason[1], "detail": reason[2], "chips": []}
    return {"eligible": True, "code": None, "chips": chips_ok}


def _item(case, ev):
    ext = lg.ext_of(case)
    ch = ext.get("change") or {}
    return {
        "case_id": case["case_id"], "exception": {"code": profile_code(case.get("profile")), "label": profile_label(case.get("profile"))},
        "amount": money(case.get("amount"), case.get("currency")), "rail": rail_obj(case.get("payment_rail")),
        "change": {"field": ch.get("field_label"), "original": (ch.get("original") or {}).get("value"), "proposed": (ch.get("proposed") or {}).get("value"),
                   "highlight": (ch.get("proposed") or {}).get("highlight"), "source": ch.get("source")},
        "chips": ev["chips"],
    }


def review(user, case_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    from app.services.v2.rows import all_cases
    eligible, groups = [], OrderedDict()
    for case in all_cases():
        ext = lg.ext_of(case)
        if not is_candidate(case, ext):
            continue
        ev = evaluate(case)
        if ev["eligible"]:
            eligible.append((case, ev))
        else:
            g = groups.setdefault(ev["code"], {"reason": ev["reason_label"], "code": ev["code"], "count": 0, "cases": []})
            g["count"] += 1
            g["cases"].append({"case_id": case["case_id"], "detail": ev["detail"]})
    eligible.sort(key=lambda ce: ce[0]["case_id"])
    items = [_item(c, e) for c, e in eligible]
    sel = items if not case_ids else [i for i in items if i["case_id"] in set(case_ids)]
    cur: Dict[str, float] = {}
    total = 0.0
    for i in sel:
        cur[i["amount"]["currency"]] = cur.get(i["amount"]["currency"], 0.0) + i["amount"]["amount"]
        total += i["amount"]["amount"]
    largest = max(sel, key=lambda i: i["amount"]["amount"]) if sel else None
    return {
        "policy": {"rule_id": RULE_ID, "text": policy_text(), "limit": {"amount": limit_amount(), "currency": "payment currency (no FX)"},
                   "autonomous_limit": {"amount": float(settings.STP_MAX_AMOUNT)}},
        "eligible": items,
        "totals": {"selected": len(sel), "eligible": len(items), "total_value": [{"currency": k, "amount": round(v, 2)} for k, v in sorted(cur.items())],
                   "total_value_label": f"{total:,.2f}" + (" (mixed currencies)" if len(cur) > 1 else (f" {next(iter(cur))}" if cur else "")),
                   "largest": ({"case_id": largest["case_id"], "amount": largest["amount"]} if largest else None)},
        "not_eligible": {"total": sum(g["count"] for g in groups.values()), "groups": list(groups.values())},
        "footnote": "Handoff requests will be sent to the bank payment system. Execution is confirmed by the bank.",
        "mode": operation_mode(), "bank_comm": settings.BANK_COMM_MODE,
    }


def approve(user, case_ids: List[str]) -> Dict[str, Any]:
    require(user, "stp.approve")
    ids = [c for c in (case_ids or []) if c]
    if not ids:
        raise invalid("case_ids must contain at least one case", "case_ids")
    if len(ids) > 200:
        raise invalid("At most 200 cases per batch approval", "case_ids")
    mode = operation_mode()
    target, why = resolve_handoff_state(user.user_id, mode=mode)
    if target is None:
        raise V2Error(409, "INVALID_STATE", why)
    batch = f"BATCH-STP-{uuid.uuid4().hex[:6].upper()}"
    handed, recorded, skipped = 0, 0, []
    for cid in dict.fromkeys(ids):
        case = repo.get_case(cid)
        if not case:
            skipped.append({"case_id": cid, "reason": "Case not found"})
            continue
        ext = lg.ext_of(case)
        if not is_candidate(case, ext):
            skipped.append({"case_id": cid, "reason": f"Not in the batch approval pool (status {lg.status_of(case).lower()})"})
            continue
        ev = evaluate(case)
        if not ev["eligible"]:
            skipped.append({"case_id": cid, "reason": f"{ev['reason_label']}: {ev['detail']}"})
            continue
        if case.get("maker_id") and case["maker_id"] == user.user_id:
            skipped.append({"case_id": cid, "reason": "Separation of duties: you prepared this repair"})
            continue
        ch = ext.get("change") or {}
        pc = ProposedFieldChange(field_path=ch.get("field", "unknown"), original_value_masked=(ch.get("original") or {}).get("value") or "",
                                 proposed_value_masked=(ch.get("proposed") or {}).get("value") or "", justification=ch.get("source") or "Micro-repair policy",
                                 validation_status="VALIDATED")
        rec = ApprovalRecord(approval_id=f"APR-BATCH-{uuid.uuid4().hex[:6].upper()}", case_id=cid, recommendation_id=f"REC-{cid}",
                             approver_id=user.user_id, approver_name=user.name, approver_role=user.role, action=ApprovalAction.APPROVE,
                             comments=f"One-click batch approval ({batch}) under {RULE_ID}.", approved_changes=[pc], step_number=1, created_at=datetime.utcnow())
        try:
            repo.save_approval(rec)
            transition_case(case, "APPROVED", actor=actor_label(user), reason=f"Batch approval {batch} by {user.name} ({RULE_ID}).")
            d = rec.model_dump()
            d["created_at"] = rec.created_at.isoformat()
            d["action"] = "APPROVE"
            d["approver_role"] = role_of(user)
            case.setdefault("approval_history", []).append(d)
            res = dispatch_to_bank_handoff(case, actor=actor_label(user), approved_by=user.user_id,
                                           reason=f"Batch approval {batch}: handed to bank system (simulated); awaiting confirmation.")
        except IllegalTransition as e:
            skipped.append({"case_id": cid, "reason": str(e)})
            continue
        ext["batch_approved"] = batch
        if res.get("dispatched"):
            ext["handoff_id"] = f"HND-{int(uuid.uuid4().hex[:8], 16) % 90000 + 10000}"
            handed += 1
        else:
            recorded += 1
        touch(case, ext)
        xt.persist_ext(cid, ext)
        audit(case, user, "HITL_APPROVAL", "BATCH_APPROVED_FOR_BANK_HANDOFF", f"{user.name} approved {cid} in one-click batch {batch} ({RULE_ID}).",
              ["Batch approval", "Segregation of duties verified", f"MODE_{mode}"], before="RECOMMENDED", after=lg.status_of(case),
              reason=policy_text(), evidence_reviewed=len(ext.get("evidence") or []), policy_version=MICRO_POLICY_VERSION, sod="Passed")
    if mode == "SHADOW":
        msg = f"Shadow mode: {recorded} recorded, nothing was sent to the bank."
    else:
        msg = f"{handed} handoff requests sent (simulated). Awaiting bank confirmation."
    return {"batch_id": batch, "requested": len(ids), "handed_to_bank": handed, "recorded": recorded, "skipped": skipped, "mode": mode, "message": msg}
