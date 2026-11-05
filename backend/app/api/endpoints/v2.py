"""UI v2 API (/api/v2). Contract: docs/ui_v2_api_contract.md. All bank communication is SIMULATED."""
from typing import Any, Dict, List, Optional

import json
import re

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.config import settings
from app.services.outbound_port import operation_mode
from app.services.v2 import actions as ac
from app.services.v2 import admin as ad
from app.services.v2 import audit as au
from app.services.v2 import batches as bt
from app.services.v2 import dashboard as db_
from app.services.v2 import home as hm
from app.services.v2 import pages as pg
from app.services.v2 import rows as rw
from app.services.v2 import stp as sp
from app.services.v2.core import (
    V2Error, current_user, writer_user, require, has_perm, role_of, ROLE_LABELS, PERMISSIONS, NAV, NAV_LABELS, now, iso, not_found,
)
from app.services.data_loader import repo
from app.services.v2 import logic as lg

_CASE_ID = re.compile(r"PEX-[A-Za-z0-9]+-\d+")


class PiiRoute(APIRoute):
    """Every JSON answer passes the PII filter: tokens by default, real values only under an active audited reveal."""

    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request: Request):
            resp = await original(request)
            from app.services.v2 import pii
            if not pii.enabled() or not str(resp.headers.get("content-type", "")).startswith("application/json"):
                return resp
            try:
                from app.core.auth import resolve_user_id
                from app.core.security import get_persona
                uid = resolve_user_id(request.headers.get("authorization"))
                persona = get_persona(uid)
                role = role_of(persona) if persona else ""
            except Exception:
                uid, role = None, ""
            data = json.loads(resp.body)
            # the "what the AI saw" view is never un-tokenised, not even during a reveal: it shows exactly what a model receives
            viewer = None if request.url.path.endswith("/ai-view") else uid
            masked = pii.mask_payload(data, viewer, _CASE_ID.findall(request.url.path), role)
            if masked is data:
                return resp
            out = JSONResponse(masked, status_code=resp.status_code)
            for k, val in resp.headers.items():
                if k.lower() not in ("content-length", "content-type"):
                    out.headers[k] = val
            return out
        return handler


router = APIRouter(route_class=PiiRoute)


# ---- bodies (all optional so the API answers with its own 422 messages) --------------------------
class SubmitBody(BaseModel):
    handover_note: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_id: Optional[str] = None


class AttachmentBody(BaseModel):
    name: Optional[str] = None
    content_base64: Optional[str] = None


class ApproveBody(BaseModel):
    reviewed: Optional[bool] = None
    comment: Optional[str] = None


class DeclineBody(BaseModel):
    reason_code: Optional[str] = None
    comment: Optional[str] = None


class RequestInfoBody(BaseModel):
    to: Optional[Any] = None
    method: Optional[str] = None
    message: Optional[str] = None
    draft: Optional[bool] = False
    reply_due: Optional[str] = None
    escalate_at: Optional[str] = None


class ReassessBody(BaseModel):
    note: Optional[str] = None
    provided: Optional[Dict[str, Any]] = None


class EscalateBody(BaseModel):
    to: Optional[str] = None
    reason: Optional[str] = None


class NoteBody(BaseModel):
    note: Optional[str] = None


class DecisionBody(BaseModel):
    option: Optional[str] = None
    comment: Optional[str] = None


class ComplianceBody(BaseModel):
    decision: Optional[str] = None
    reason_code: Optional[str] = None
    comment: Optional[str] = None


class ConfidenceReviewBody(BaseModel):
    decision: Optional[str] = "confirm"
    comment: Optional[str] = None


class DisambiguateBody(BaseModel):
    candidate_id: Optional[str] = None
    rationale: Optional[str] = None


class AssignBody(BaseModel):
    assignee: Optional[str] = "me"


class ViewBody(BaseModel):
    name: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    sort: Optional[str] = None


class StpApproveBody(BaseModel):
    case_ids: Optional[List[str]] = None


class ModeBody(BaseModel):
    integration_id: Optional[str] = None
    to_mode: Optional[str] = None
    reason: Optional[str] = None


def _idem(key, user, fn):
    return ac.with_idempotency(key, user, fn)


# ---- me / home -------------------------------------------------------------------------------------
@router.get("/me")
def me(user=Depends(current_user)):
    r = role_of(user)
    return {"user": {"user_id": user.user_id, "name": user.name, "role": r, "role_label": ROLE_LABELS.get(r, r), "title": user.title, "initials": user.avatar_initials,
                     "email": user.email, "max_approval_amount": user.max_approval_amount},
            "permissions": PERMISSIONS.get(r, []),
            "nav": [{"key": k, "label": NAV_LABELS[k][0], "path": NAV_LABELS[k][1]} for k in NAV.get(r, ["home"])],
            "mode": operation_mode(), "bank_comm": settings.BANK_COMM_MODE, "demo": bool(settings.PEX_DEMO), "now": iso(now()),
            "stp_limit": {"amount": float(__import__("app.services.v2.policy", fromlist=["x"]).get("zero_touch_limit")), "currency": "payment currency", "label": "Autonomous STP limit"},
            "batch_limit": {"amount": float(__import__("app.services.v2.policy", fromlist=["x"]).get("batch_limit")), "label": "One-click batch approval limit"},
            "unread_notifications": ac.list_notifications(user)["unread"]}


class PolicyChangeBody(BaseModel):
    key: str
    value: Any
    reason: str = ""


class PolicyPreviewBody(BaseModel):
    key: str
    value: Any


class PolicyNoteBody(BaseModel):
    note: Optional[str] = None


@router.get("/policy/params")
def policy_params(user=Depends(current_user)):
    require(user, "policy.read", "Only a Policy Owner can see and change rules.")
    from app.services.v2 import policy as po
    return po.listing()


@router.post("/policy/preview")
def policy_preview(body: PolicyPreviewBody, user=Depends(current_user)):
    require(user, "policy.read", "Only a Policy Owner can see and change rules.")
    from app.services.v2 import policy as po
    return po.impact(body.key, body.value)


@router.post("/policy/changes")
def policy_propose(body: PolicyChangeBody, user=Depends(writer_user)):
    require(user, "policy.write", "Only a Policy Owner can see and change rules.")
    from app.services.v2 import policy as po
    return po.propose(user, body.key, body.value, body.reason)


@router.post("/policy/changes/{change_id}/approve")
def policy_approve(change_id: str, body: PolicyNoteBody, user=Depends(writer_user)):
    require(user, "policy.approve", "Only a Policy Owner can approve rule changes.")
    from app.services.v2 import policy as po
    return po.approve(user, change_id, body.note)


@router.post("/policy/changes/{change_id}/reject")
def policy_reject(change_id: str, body: PolicyNoteBody, user=Depends(writer_user)):
    require(user, "policy.approve", "Only a Policy Owner can decide on rule changes.")
    from app.services.v2 import policy as po
    return po.reject(user, change_id, body.note)


@router.post("/policy/changes/{change_id}/withdraw")
def policy_withdraw(change_id: str, body: PolicyNoteBody, user=Depends(writer_user)):
    require(user, "policy.write", "Only a Policy Owner can withdraw a rule change.")
    from app.services.v2 import policy as po
    return po.withdraw(user, change_id, body.note)


@router.get("/reference/ontology")
def ref_ontology(user=Depends(current_user)):
    require(user, "reference.read", "Reference pages are for Administrators and Policy Owners.")
    from app.services.v2 import reference as rf
    return rf.ontology()


@router.get("/reference/data-model")
def ref_data_model(user=Depends(current_user)):
    require(user, "reference.read", "Reference pages are for Administrators and Policy Owners.")
    from app.services.v2 import reference as rf
    return rf.data_model()


@router.get("/reference/library")
def ref_library(user=Depends(current_user)):
    require(user, "reference.read", "Reference pages are for Administrators and Policy Owners.")
    from app.services.v2 import library as lb
    return lb.library()


@router.get("/reference/library/{code}")
def ref_library_profile(code: str, user=Depends(current_user)):
    require(user, "reference.read", "Reference pages are for Administrators and Policy Owners.")
    from app.services.v2 import library as lb
    return lb.profile(code)


@router.get("/reference/contract")
def ref_contract(user=Depends(current_user)):
    require(user, "reference.read", "Reference pages are for Administrators and Policy Owners.")
    from app.services.v2 import contract as ct
    return ct.overview()


@router.get("/reference/contract/{code}")
def ref_contract_profile(code: str, user=Depends(current_user)):
    require(user, "reference.read", "Reference pages are for Administrators and Policy Owners.")
    from app.services.v2 import contract as ct
    return ct.profile_contract(code)


@router.get("/reference/controls")
def ref_controls(user=Depends(current_user)):
    require(user, "reference.read", "Reference pages are for Administrators and Policy Owners.")
    from app.services.v2 import library as lb
    return lb.controls()


@router.get("/reference/sops")
def ref_sops(user=Depends(current_user)):
    require(user, "reference.read", "Reference pages are for Administrators and Policy Owners.")
    from app.services.v2 import reference as rf
    return rf.sops()


@router.get("/reference/sops/{code}")
def ref_sop(code: str, user=Depends(current_user)):
    require(user, "reference.read", "Reference pages are for Administrators and Policy Owners.")
    from app.services.v2 import reference as rf
    return rf.sop(code)


@router.get("/dashboard")
def dashboard(stuck_limit: int = 10, user=Depends(current_user)):
    """Bank-wide picture, identical for every role, plus extras for the caller's role."""
    require(user, "case.read")
    return db_.dashboard(user, stuck_limit)


@router.get("/home")
def home(user=Depends(current_user)):
    return hm.home(user)


# ---- worklist ---------------------------------------------------------------------------------------
@router.get("/worklist")
def worklist(tab: str = "ready", page: int = 1, page_size: int = 25, exception_type: Optional[str] = None, rail: Optional[str] = None,
             currency: Optional[str] = None, cutoff_band: Optional[str] = None, evidence: Optional[str] = None, q: Optional[str] = None,
             assignee: Optional[str] = None, sort: Optional[str] = None, dir: str = "asc", view: Optional[str] = None, scope: Optional[str] = None,
             user=Depends(current_user)):
    require(user, "case.read")
    if scope not in (None, "mine", "all"):
        raise V2Error(422, "VALIDATION", "scope must be mine or all", "scope")
    f = {"exception_type": exception_type, "rail": rail, "currency": currency, "cutoff_band": cutoff_band, "evidence": evidence, "q": q, "assignee": assignee}
    return rw.worklist(user, tab, page, page_size, f, sort or "", dir, scope, view)


@router.get("/worklist/views")
def views(user=Depends(current_user)):
    return rw.list_views(user)


@router.post("/worklist/views")
def create_view(body: ViewBody, user=Depends(writer_user)):
    return rw.create_view(user, body.name or "", body.filters or {}, body.sort)


@router.delete("/worklist/views/{view_id}")
def delete_view(view_id: str, user=Depends(writer_user)):
    return rw.delete_view(user, view_id)


@router.get("/worklist/{case_id}/preview")
def preview(case_id: str, user=Depends(current_user)):
    return rw.preview(case_id, user)


@router.get("/approvals")
def approvals(page: int = 1, page_size: int = 25, tier: str = "all", desk: str = "all", user=Depends(current_user)):
    require(user, "case.read")
    return rw.approvals_queue(user, page, page_size, tier, desk)


@router.get("/compliance/queue")
def compliance_queue(page: int = 1, page_size: int = 25, user=Depends(current_user)):
    require(user, "case.read")
    return rw.compliance_queue(user, page, page_size)


# ---- case page / actions -----------------------------------------------------------------------------
@router.get("/cases/{case_id}/page")
def case_page(case_id: str, user=Depends(current_user)):
    require(user, "case.read")
    return pg.case_page(case_id, user)


@router.get("/cases/{case_id}/journey")
def case_journey(case_id: str, user=Depends(current_user)):
    require(user, "case.read")
    return pg.case_page(case_id, user)["journey"]


@router.get("/cases/{case_id}/timeline")
def case_timeline(case_id: str, user=Depends(current_user)):
    require(user, "case.read")
    if not repo.get_case(case_id):
        raise not_found(f"Case {case_id}")
    return au.case_timeline(case_id)


@router.get("/cases/{case_id}/evidence/{evidence_id}")
def evidence_source(case_id: str, evidence_id: str, user=Depends(current_user)):
    require(user, "case.read")
    case = repo.get_case(case_id)
    if not case:
        raise not_found(f"Case {case_id}")
    for r in lg.ext_of(case).get("evidence") or []:
        if r["id"] == evidence_id:
            return {"id": r["id"], "check": r["check"], "result": r["result"], "source": r["source"], "authority": r["authority"], "checked_at": r["checked_at"],
                    "status": r["status"], "raw": r.get("raw") or {}, "note": "Simulated source view: the original system is not connected in this build."}
    raise not_found(f"Evidence {evidence_id}")


@router.get("/cases/{case_id}/evidence/{evidence_id}/dossier")
def evidence_dossier(case_id: str, evidence_id: str, user=Depends(current_user)):
    require(user, "case.read")
    from app.services.v2 import dossier as ds
    case = repo.get_case(case_id)
    if not case:
        raise not_found(f"Case {case_id}")
    d = ds.build(case, lg.ext_of(case).get("evidence") or [], evidence_id)
    if d is None:
        raise not_found(f"Evidence {evidence_id}")
    return d


@router.post("/cases/{case_id}/assign")
def assign(case_id: str, body: AssignBody, user=Depends(writer_user), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    return _idem(idem, user, lambda: ac.assign(case_id, user, body.assignee))


@router.post("/cases/{case_id}/attachments", status_code=201)
def attachment_add(case_id: str, body: AttachmentBody, user=Depends(writer_user)):
    from app.services.v2 import attachments as att
    return att.add(case_id, user, body.name, body.content_base64)


@router.delete("/cases/{case_id}/attachments/{attachment_id}")
def attachment_remove(case_id: str, attachment_id: str, user=Depends(writer_user)):
    from app.services.v2 import attachments as att
    att.remove(case_id, attachment_id, user)
    return {"ok": True}


@router.get("/cases/{case_id}/attachments/{attachment_id}/download")
def attachment_download(case_id: str, attachment_id: str, user=Depends(current_user)):
    from app.services.v2 import attachments as att
    name, ctype, data = att.open_file(case_id, attachment_id, user)
    safe = name.replace('"', "")
    return Response(content=data, media_type=ctype, headers={"Content-Disposition": f'attachment; filename="{safe}"', "X-Content-Type-Options": "nosniff",
                                                              "Cache-Control": "no-store"})


@router.post("/cases/{case_id}/submit")
def submit(case_id: str, body: SubmitBody, user=Depends(writer_user), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    return _idem(idem, user, lambda: ac.submit(case_id, user, body.handover_note, body.attachment_name, body.attachment_id))


@router.post("/cases/{case_id}/approve")
def approve(case_id: str, body: ApproveBody, user=Depends(writer_user), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    return _idem(idem, user, lambda: ac.approve(case_id, user, body.reviewed, body.comment))


@router.post("/cases/{case_id}/return")
def return_case(case_id: str, body: DeclineBody, user=Depends(writer_user), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    return _idem(idem, user, lambda: ac.return_to_maker(case_id, user, body.reason_code, body.comment))


@router.post("/cases/{case_id}/reject")
def reject(case_id: str, body: DeclineBody, user=Depends(writer_user), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    return _idem(idem, user, lambda: ac.reject(case_id, user, body.reason_code, body.comment))


@router.post("/cases/{case_id}/request-information")
def request_information(case_id: str, body: RequestInfoBody, user=Depends(writer_user), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    return _idem(idem, user, lambda: ac.request_information(case_id, user, body.to, body.method, body.message, bool(body.draft), body.reply_due, body.escalate_at))


@router.post("/cases/{case_id}/reassess")
def reassess(case_id: str, body: ReassessBody, user=Depends(writer_user)):
    return ac.reassess(case_id, user, body.note, body.provided)


@router.post("/cases/{case_id}/escalate")
def escalate(case_id: str, body: EscalateBody, user=Depends(writer_user)):
    return ac.escalate(case_id, user, body.to, body.reason)


@router.post("/cases/{case_id}/start-verification")
def start_verification(case_id: str, body: NoteBody, user=Depends(writer_user)):
    return ac.start_verification(case_id, user, body.note)


@router.post("/cases/{case_id}/check-status")
def check_status(case_id: str, user=Depends(writer_user)):
    return ac.check_status(case_id, user)


@router.post("/cases/{case_id}/request-bank-status")
def request_bank_status(case_id: str, body: NoteBody, user=Depends(writer_user)):
    return ac.request_bank_status(case_id, user, body.note)


@router.post("/cases/{case_id}/compliance/decision")
def compliance_decision(case_id: str, body: ComplianceBody, user=Depends(writer_user), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    return _idem(idem, user, lambda: ac.compliance_decision(case_id, user, body.decision, body.reason_code, body.comment))


@router.post("/cases/{case_id}/decision")
def record_decision(case_id: str, body: DecisionBody, user=Depends(writer_user), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    return _idem(idem, user, lambda: ac.record_decision(case_id, user, body.option, body.comment))


@router.post("/cases/{case_id}/confidence-review")
def confidence_review(case_id: str, body: ConfidenceReviewBody, user=Depends(writer_user), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    return _idem(idem, user, lambda: ac.confidence_review(case_id, user, body.decision, body.comment))


class RevealBody(BaseModel):
    reason: Optional[str] = None


@router.post("/cases/{case_id}/pii/reveal")
def pii_reveal(case_id: str, body: RevealBody, user=Depends(current_user)):
    return ac.pii_reveal(case_id, user, body.reason)


@router.get("/cases/{case_id}/ai-view")
def ai_view(case_id: str, user=Depends(current_user)):
    """The exact payload an AI model would receive for this case. Tokens, an amount band and derived facts only."""
    require(user, "case.read")
    return ac.ai_view(case_id, user)


@router.get("/connectors")
def connectors(user=Depends(current_user)):
    require(user, "case.read")
    from app.services.v2 import zone
    return {"connectors": zone.connector_status(),
            "note": "Simulated connectors return ISO 20022-shaped data. A connector set to real needs a registered adapter and fails closed without one."}


@router.post("/cases/{case_id}/pii/hide")
def pii_hide(case_id: str, user=Depends(current_user)):
    return ac.pii_hide(case_id, user)


class PingBody(BaseModel):
    note: Optional[str] = None
    level: Optional[int] = None


@router.post("/cases/{case_id}/ping")
def ping(case_id: str, body: PingBody, user=Depends(writer_user)):
    from app.services.v2 import expedite as ex
    return ex.ping(case_id, user, body.note, body.level)


@router.get("/cases/{case_id}/expedite")
def case_expedite(case_id: str, user=Depends(current_user)):
    from app.services.v2 import expedite as ex
    return ex.case_state(case_id, user)


@router.get("/expedite")
def expedite_inbox(user=Depends(current_user)):
    from app.services.v2 import expedite as ex
    return ex.inbox(user)


@router.post("/expedite/{entry_id}/ack")
def expedite_ack(entry_id: str, user=Depends(writer_user)):
    from app.services.v2 import expedite as ex
    return ex.acknowledge(entry_id, user)


@router.post("/cases/{case_id}/disambiguate")
def disambiguate(case_id: str, body: DisambiguateBody, user=Depends(writer_user)):
    return ac.disambiguate(case_id, user, body.candidate_id, body.rationale)


@router.get("/notifications")
def notifications(user=Depends(current_user)):
    return ac.list_notifications(user)


@router.post("/notifications/{nid}/read")
def read_notification(nid: str, user=Depends(current_user)):
    return ac.mark_read(user, nid)


# ---- batch approval (STP) -----------------------------------------------------------------------------
@router.get("/stp/review")
def stp_review(case_ids: Optional[str] = None, user=Depends(current_user)):
    require(user, "stp.approve", "Only approvers can review batch approvals.")
    return sp.review(user, [c for c in (case_ids or "").split(",") if c] or None)


@router.post("/stp/approve")
def stp_approve(body: StpApproveBody, user=Depends(writer_user)):
    return sp.approve(user, body.case_ids or [])


# ---- batches -----------------------------------------------------------------------------------------------
@router.get("/batches")
def batches(page: int = 1, page_size: int = 25, user=Depends(current_user)):
    require(user, "case.read")
    return bt.list_batches(page, page_size)


@router.post("/batches/upload")
async def batch_upload(file: UploadFile = File(...), user=Depends(writer_user)):
    require(user, "batch.upload")
    name = file.filename or "upload.json"
    if not name.lower().endswith((".json", ".jsonl", ".ndjson", ".json.gz", ".jsonl.gz", ".ndjson.gz")):
        raise V2Error(415, "VALIDATION", "Unsupported file type. Use .json, .jsonl, .ndjson or .json.gz", "file")
    from app.services.batch_pipeline import get_pipeline
    return {"batch_id": get_pipeline().save_upload(name, file.file), "status": "QUEUED"}


@router.get("/batches/{batch_id}")
def batch_detail(batch_id: str, tab: str = "all", page: int = 1, page_size: int = 25, user=Depends(current_user)):
    require(user, "case.read")
    return bt.get_batch(batch_id, tab, page, page_size)


@router.get("/batches/{batch_id}/records/{record}")
def batch_record(batch_id: str, record: int, user=Depends(current_user)):
    require(user, "case.read")
    return bt.record_detail(batch_id, record)


@router.get("/batches/{batch_id}/rejected")
def batch_rejected(batch_id: str, format: str = "jsonl", user=Depends(current_user)):
    require(user, "case.read")
    body, media, fname = bt.rejected_download(batch_id, format)
    return Response(content=body, media_type=media, headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.post("/batches/{batch_id}/reprocess")
async def batch_reprocess(batch_id: str, file: UploadFile = File(...), user=Depends(writer_user)):
    require(user, "batch.upload")
    return bt.reprocess(batch_id, file.filename or "corrected.jsonl", file.file)


# ---- audit ---------------------------------------------------------------------------------------------------
def _audit_filters(date_from, date_to, event_type, actor, role, exception_type, rail, q, case_id):
    return {"date_from": date_from, "date_to": date_to, "event_type": event_type, "actor": actor, "role": role,
            "exception_type": exception_type, "rail": rail, "q": q, "case_id": case_id}


@router.get("/audit/events")
def audit_events(date_from: Optional[str] = None, date_to: Optional[str] = None, event_type: Optional[str] = None, actor: Optional[str] = None,
                 role: Optional[str] = None, exception_type: Optional[str] = None, rail: Optional[str] = None, q: Optional[str] = None,
                 case_id: Optional[str] = None, page: int = 1, page_size: int = 50, user=Depends(current_user)):
    require(user, "audit.read")
    return au.events(_audit_filters(date_from, date_to, event_type, actor, role, exception_type, rail, q, case_id), page, page_size)


@router.get("/audit/events/{event_id}")
def audit_event(event_id: str, user=Depends(current_user)):
    require(user, "audit.read")
    return au.event_detail(event_id)


@router.get("/audit/export")
def audit_export(format: str = "csv", date_from: Optional[str] = None, date_to: Optional[str] = None, event_type: Optional[str] = None,
                 actor: Optional[str] = None, role: Optional[str] = None, exception_type: Optional[str] = None, rail: Optional[str] = None,
                 q: Optional[str] = None, case_id: Optional[str] = None, user=Depends(current_user)):
    require(user, "audit.export")
    if format != "csv":
        raise V2Error(422, "VALIDATION", "format must be csv", "format")
    body = au.export_csv(_audit_filters(date_from, date_to, event_type, actor, role, exception_type, rail, q, case_id))
    return Response(content=body, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="pex_audit_events.csv"'})


@router.get("/audit/cases")
def audit_cases(q: Optional[str] = None, page: int = 1, page_size: int = 25, user=Depends(current_user)):
    require(user, "audit.read")
    return au.cases_with_events(q, page, page_size)


@router.get("/audit/cases/{case_id}/report")
def audit_case_report(case_id: str, format: str = "json", user=Depends(current_user)):
    require(user, "audit.read")
    body, media, fname = au.case_report(case_id, format)
    if media == "application/json":
        return body
    return Response(content=body, media_type=media, headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/audit/control-reports")
def audit_control_reports(user=Depends(current_user)):
    require(user, "audit.read")
    return au.control_reports()


# ---- admin ----------------------------------------------------------------------------------------------------
@router.get("/admin/integrations")
def admin_integrations(user=Depends(current_user)):
    if not (has_perm(user, "admin.read") or role_of(user) == "SUPERVISOR"):
        require(user, "admin.read")
    return ad.integrations()


@router.get("/admin/handoffs")
def admin_handoffs(hours: int = 24, user=Depends(current_user)):
    if not (has_perm(user, "admin.read") or role_of(user) == "SUPERVISOR"):
        require(user, "admin.read")
    return ad.handoffs(hours)


@router.post("/admin/mode-change-request")
def admin_mode_request(body: ModeBody, user=Depends(writer_user)):
    return ad.request_mode_change(user, body.integration_id, body.to_mode, body.reason)


@router.get("/admin/mode-change-requests")
def admin_mode_requests(user=Depends(current_user)):
    require(user, "admin.read")
    return ad.list_mode_changes()


@router.post("/admin/mode-change-request/{mc_id}/approve")
def admin_mode_approve(mc_id: str, user=Depends(writer_user)):
    return ad.approve_mode_change(user, mc_id)


@router.post("/admin/mode-change-request/{mc_id}/reject")
def admin_mode_reject(mc_id: str, user=Depends(writer_user)):
    return ad.reject_mode_change(user, mc_id)


@router.get("/admin/roles")
def admin_roles(user=Depends(current_user)):
    require(user, "admin.read")
    return ad.roles()


@router.get("/admin/policies")
def admin_policies(user=Depends(current_user)):
    require(user, "admin.read")
    return ad.policies()


@router.get("/admin/exception-types")
def admin_exception_types(user=Depends(current_user)):
    require(user, "admin.read")
    return ad.exception_types()


# ---- network cases: investigations (camt.110/111) and recalls (camt.056/029) ------------------------------------
class NetInboundBody(BaseModel):
    xml: str


class NetSampleBody(BaseModel):
    kind: str = "INVESTIGATION"
    case_id: Optional[str] = None


class NetOutboundBody(BaseModel):
    kind: str
    uetr: str = ""
    case_id: Optional[str] = None
    reason_code: str
    narrative: str = ""
    counterparty_bic: str


class NetDraftBody(BaseModel):
    outcome: str
    reason_code: Optional[str] = None
    text: str = ""


class NetNoteBody(BaseModel):
    note: Optional[str] = None


class NetReturnBody(BaseModel):
    reference: str = ""


class NetReplyBody(BaseModel):
    outcome: Optional[str] = None


@router.get("/network/cases")
def network_list(kind: Optional[str] = None, direction: Optional[str] = None, status: Optional[str] = None, user=Depends(current_user)):
    from app.services.v2 import network as nw
    return nw.listing(user, kind, direction, status)


@router.get("/network/cases/{nid}")
def network_detail(nid: str, user=Depends(current_user)):
    from app.services.v2 import network as nw
    return nw.get_detail(user, nid)


@router.post("/network/inbound", status_code=201)
def network_inbound(body: NetInboundBody, user=Depends(writer_user)):
    from app.services.v2 import network as nw
    return nw.receive(user, body.xml)


@router.post("/network/inbound/sample", status_code=201)
def network_sample(body: NetSampleBody, user=Depends(writer_user)):
    from app.services.v2 import network as nw
    return nw.sample(user, body.kind, body.case_id)


@router.post("/network/outbound", status_code=201)
def network_outbound(body: NetOutboundBody, user=Depends(writer_user)):
    from app.services.v2 import network as nw
    return nw.raise_outbound(user, body.kind, body.uetr, body.reason_code, body.narrative, body.counterparty_bic, body.case_id)


@router.post("/network/cases/{nid}/draft")
def network_draft(nid: str, body: NetDraftBody, user=Depends(writer_user)):
    from app.services.v2 import network as nw
    return nw.draft(user, nid, body.outcome, body.reason_code, body.text)


@router.post("/network/cases/{nid}/authorise")
def network_authorise(nid: str, body: NetNoteBody, user=Depends(writer_user)):
    from app.services.v2 import network as nw
    return nw.authorise(user, nid, body.note)


@router.post("/network/cases/{nid}/simulate-reply")
def network_simulate(nid: str, body: NetReplyBody, user=Depends(writer_user)):
    from app.services.v2 import network as nw
    return nw.simulate_reply(user, nid, body.outcome)


@router.post("/network/cases/{nid}/bank-return")
def network_return(nid: str, body: NetReturnBody, user=Depends(writer_user)):
    from app.services.v2 import network as nw
    return nw.bank_return(user, nid, body.reference)


@router.post("/network/cases/{nid}/close")
def network_close(nid: str, body: NetNoteBody, user=Depends(writer_user)):
    from app.services.v2 import network as nw
    return nw.close(user, nid, body.note)
