"""SME review: the bank's experts validate the profiles and controls, and PeX records where that stands.

Statuses are kept apart from the content: review never edits a profile, a control, a policy or a case. A sign-off keeps the hash of the content it
was given on, so a later change to that content shows as CHANGED_SINCE_SIGNOFF instead of a stale green. Reviewers can work in Excel: export a
workbook, fill in Status and Reviewer comment, import it back.
"""
from __future__ import annotations

import hashlib
import io
import json
import uuid
from typing import Any, Dict, List, Optional

from app.db.models import V2ReviewCommentModel, V2ReviewStatusModel
from app.db.session import SessionLocal
from app.services.audit_service import audit_service
from app.services.v2 import library
from app.services.v2.core import V2Error, iso, now, role_of

CASE_ID = "SME-REVIEW"
KINDS = ("profile", "control")
SETTABLE = ("IN_REVIEW", "CHANGES_REQUESTED", "SIGNED_OFF")
ALL_STATUS = ("NOT_REVIEWED",) + SETTABLE + ("CHANGED_SINCE_SIGNOFF",)
LABEL = {"NOT_REVIEWED": "Not reviewed", "IN_REVIEW": "In review", "CHANGES_REQUESTED": "Changes requested", "SIGNED_OFF": "Signed off",
         "CHANGED_SINCE_SIGNOFF": "Changed since sign-off"}
FROM_LABEL = {v.lower(): k for k, v in LABEL.items() if k in SETTABLE}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# --- content and ids ---------------------------------------------------------------------------------------------
def _control_defs() -> Dict[str, Dict[str, Any]]:
    return {c["id"]: c for c in library.defs()["controls"]}


def _profile_rows() -> Dict[str, Dict[str, Any]]:
    return {p["code"]: p for p in library.library()["profiles"]}


def exists(kind: str, id_: str) -> bool:
    return (id_ in _profile_rows()) if kind == "profile" else (id_ in _control_defs()) if kind == "control" else False


def content_hash(kind: str, id_: str) -> str:
    body = library.profile(id_) if kind == "profile" else _control_defs()[id_]
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def short(h: str) -> str:
    return h[:12]


def _audit(user, action: str, text: str):
    audit_service.log_event(case_id=CASE_ID, correlation_id=CASE_ID, stage_name="SME_REVIEW", actor_id=user.user_id, actor_role=role_of(user),
                            action_name=action, details=text, control_tags=["SME review"], amount=None, currency=None)


def _need(kind: str, id_: str):
    if kind not in KINDS:
        raise V2Error(400, "INVALID", "kind must be profile or control")
    if not exists(kind, id_):
        raise V2Error(404, "NOT_FOUND", f"{kind.capitalize()} {id_} is not in the library")


# --- reads -------------------------------------------------------------------------------------------------------
def _stored():
    db = SessionLocal()
    try:
        st = {(r.kind, r.item_id): r for r in db.query(V2ReviewStatusModel).all()}
        cm = db.query(V2ReviewCommentModel).order_by(V2ReviewCommentModel.created_at, V2ReviewCommentModel.id).all()
        for o in list(st.values()) + cm:
            db.expunge(o)
        return st, cm
    finally:
        db.close()


def _row(kind: str, id_: str, name: str, extra: Dict[str, Any], st, comments) -> Dict[str, Any]:
    r = st.get((kind, id_))
    ver = content_hash(kind, id_)
    status = r.status if r else "NOT_REVIEWED"
    if r and r.status == "SIGNED_OFF" and r.signed_off_hash != ver:
        status = "CHANGED_SINCE_SIGNOFF"
    open_n = sum(1 for c in comments if c.kind == kind and c.item_id == id_ and c.status == "OPEN")
    return {"kind": kind, "id": id_, "name": name, **extra, "status": status, "status_label": LABEL[status], "stored_status": r.status if r else None,
            "reviewer": r.reviewer if r else None, "reviewer_name": r.reviewer_name if r else None, "reviewed_at": r.reviewed_at if r else None,
            "version": short(ver), "signed_off_on_version": short(r.signed_off_hash) if r and r.signed_off_hash else None, "open_comments": open_n}


def items(kind: str) -> Dict[str, Any]:
    if kind not in KINDS:
        raise V2Error(400, "INVALID", "kind must be profile or control")
    st, cm = _stored()
    if kind == "profile":
        rows = [_row("profile", c, p["name"], {"family": p["family"], "outcome": p["outcome"], "stp": p["stp"]}, st, cm) for c, p in sorted(_profile_rows().items())]
    else:
        rows = [_row("control", i, c["name"], {"control_kind": c["kind"]}, st, cm) for i, c in sorted(_control_defs().items())]
    return {"items": rows, "total": len(rows)}


def _count(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"total": len(rows)}
    for s in ALL_STATUS:
        out[s] = sum(1 for r in rows if r["status"] == s)
    out["percent_signed_off"] = round(100 * out["SIGNED_OFF"] / len(rows), 1) if rows else 0.0
    return out


def summary() -> Dict[str, Any]:
    p, c = items("profile")["items"], items("control")["items"]
    _, cm = _stored()
    return {"profiles": _count(p), "controls": _count(c), "open_comments": sum(1 for x in cm if x.status == "OPEN"), "labels": LABEL}


def _comment_dict(c: V2ReviewCommentModel) -> Dict[str, Any]:
    return {"id": c.id, "kind": c.kind, "item_id": c.item_id, "part": c.part, "text": c.text, "author": c.author, "author_name": c.author_name, "created_at": c.created_at,
            "status": c.status, "addressed_by": c.addressed_by, "addressed_at": c.addressed_at, "addressed_note": c.addressed_note}


def detail(kind: str, id_: str) -> Dict[str, Any]:
    _need(kind, id_)
    row = [r for r in items(kind)["items"] if r["id"] == id_][0]
    _, cm = _stored()
    return {**row, "comments": [_comment_dict(c) for c in cm if c.kind == kind and c.item_id == id_]}


# --- writes ------------------------------------------------------------------------------------------------------
def _open_count(db, kind: str, id_: str) -> int:
    return db.query(V2ReviewCommentModel).filter(V2ReviewCommentModel.kind == kind, V2ReviewCommentModel.item_id == id_, V2ReviewCommentModel.status == "OPEN").count()


def _apply_status(db, user, kind: str, id_: str, status: str, note: Optional[str], name: Optional[str]):
    if status not in SETTABLE:
        raise V2Error(400, "INVALID", "status must be one of " + ", ".join(SETTABLE))
    if status == "SIGNED_OFF" and _open_count(db, kind, id_):
        raise V2Error(409, "INVALID_STATE", "Resolve the open comments before signing off: an item with an open comment cannot be signed off")
    r = db.query(V2ReviewStatusModel).filter_by(kind=kind, item_id=id_).first()
    if not r:
        r = V2ReviewStatusModel(kind=kind, item_id=id_)
        db.add(r)
    r.status, r.reviewer, r.reviewer_name, r.reviewed_at = status, user.user_id, (name or None), iso(now())
    r.signed_off_hash = content_hash(kind, id_) if status == "SIGNED_OFF" else None
    r.note = (note or None) and str(note)[:1024]


def set_status(user, kind: str, id_: str, status: str, note: Optional[str] = None) -> Dict[str, Any]:
    _need(kind, id_)
    db = SessionLocal()
    try:
        _apply_status(db, user, kind, id_, str(status or ""), note, None)
        db.commit()
    finally:
        db.close()
    _audit(user, "SME_STATUS_SET", f"{kind.capitalize()} {id_} set to {LABEL.get(status, status)}." + (f" Note: {note}" if note else ""))
    return detail(kind, id_)


def _add_comment(db, user, kind: str, id_: str, text: str, part: Optional[str], name: Optional[str]) -> Optional[V2ReviewCommentModel]:
    text = (text or "").strip()
    part = (part or "").strip() or None
    if not text or len(text) > 2000:
        raise V2Error(400, "INVALID", "A comment needs 1 to 2000 characters")
    if part and len(part) > 160:
        raise V2Error(400, "INVALID", "The part reference can be at most 160 characters")
    same = db.query(V2ReviewCommentModel).filter_by(kind=kind, item_id=id_, text=text, status="OPEN").all()
    if any((c.part or None) == part for c in same):
        return None
    c = V2ReviewCommentModel(id="RC-" + uuid.uuid4().hex[:8].upper(), kind=kind, item_id=id_, part=part, text=text, author=user.user_id, author_name=name or None, created_at=iso(now()), status="OPEN")
    db.add(c)
    return c


def add_comment(user, kind: str, id_: str, text: str, part: Optional[str] = None) -> Dict[str, Any]:
    _need(kind, id_)
    db = SessionLocal()
    try:
        c = _add_comment(db, user, kind, id_, text, part, None)
        db.commit()
        out = _comment_dict(c) if c else None
        if c is None:
            raise V2Error(409, "DUPLICATE", "The same open comment already exists")
    finally:
        db.close()
    _audit(user, "SME_COMMENT_ADDED", f"Comment on {kind} {id_}" + (f" ({part})" if part else "") + ".")
    return out


def address_comment(user, cid: str, note: Optional[str]) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        c = db.query(V2ReviewCommentModel).filter_by(id=cid).first()
        if not c:
            raise V2Error(404, "NOT_FOUND", "Comment not found")
        c.status, c.addressed_by, c.addressed_at, c.addressed_note = "ADDRESSED", user.user_id, iso(now()), (note or None) and str(note)[:1024]
        db.commit()
        out = _comment_dict(c)
        where = f"{c.kind} {c.item_id}"
    finally:
        db.close()
    _audit(user, "SME_COMMENT_ADDRESSED", f"Comment {cid} on {where} marked addressed.")
    return out


def clear(user) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        a = db.query(V2ReviewStatusModel).delete()
        b = db.query(V2ReviewCommentModel).delete()
        db.commit()
    finally:
        db.close()
    _audit(user, "SME_REVIEW_CLEARED", f"Cleared {a} review status(es) and {b} comment(s).")
    return {"cleared_status": a, "cleared_comments": b}


# --- Excel -------------------------------------------------------------------------------------------------------
def export_xlsx() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = Workbook()
    ws = wb.active
    ws.title = "Read me"
    for r in [["PeX profile and control review workbook"], [""],
              ["How to use it"],
              ["1. On the Profiles and Controls sheets, set Status to one of: In review, Changes requested, Signed off. Leave it blank to change nothing."],
              ["2. Write notes in Reviewer comment. A row with a comment cannot also be Signed off; sign off after the comment is addressed."],
              ["3. On the Evidence sheet, a Reviewer comment is attached to that evidence item of that profile."],
              ["4. Do not change the Version column. It ties your review to the exact content you saw; a changed item is refused when you send the file back."],
              ["5. Send the file back to the Administrator, who imports it into PeX."],
              [""], ["Review changes no content. Comments are work items for the PeX team; nothing in this file edits a rule or a profile."]]:
        ws.append(r)
    ws["A1"].font = Font(bold=True, size=14)
    ws["A3"].font = Font(bold=True)
    ws.column_dimensions["A"].width = 120
    st, cm = _stored()
    head_fill = PatternFill("solid", fgColor="0B3A6F")

    def sheet(name: str, heads: List[str], rows: List[List[Any]], widths: List[int], status_col: Optional[int]):
        w = wb.create_sheet(name)
        w.append(heads)
        for c in w[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = head_fill
            c.alignment = Alignment(wrap_text=True, vertical="top")
        for r in rows:
            w.append(r)
        for i, wd in enumerate(widths, start=1):
            w.column_dimensions[chr(64 + i)].width = wd
        w.freeze_panes = "B2"
        if status_col:
            dv = DataValidation(type="list", formula1='"In review,Changes requested,Signed off"', allow_blank=True)
            w.add_data_validation(dv)
            dv.add(f"{chr(64 + status_col)}2:{chr(64 + status_col)}{max(2, w.max_row)}")
        return w

    prof = _profile_rows()
    prow = []
    for code, p in sorted(prof.items()):
        r = _row("profile", code, p["name"], {}, st, cm)
        prow.append([code, p["name"], p["family"], p["outcome"], p["stp"], p["approval"], r["version"], r["status_label"], None, None, None])
    sheet("Profiles", ["Code", "Name", "Family", "Outcome", "Straight-through", "Approval path", "Version", "Current status", "Status", "Reviewer comment", "Reviewer"], prow,
          [10, 36, 8, 12, 16, 22, 14, 18, 20, 50, 20], 9)
    erow = []
    for code in sorted(prof):
        ver = short(content_hash("profile", code))
        for e in library.profile(code)["evidence"]:
            erow.append([code, e["type"], "Must have" if e["mandatory"] else "Optional", e["tier"], e["proves"], e["source_system"], ver, None, None])
    sheet("Evidence", ["Code", "Evidence", "Need", "Trust tier", "What it proves", "Source system", "Version", "Reviewer comment", "Reviewer"], erow, [10, 36, 12, 10, 50, 34, 14, 50, 20], None)
    crow = []
    for cid, c in sorted(_control_defs().items()):
        r = _row("control", cid, c["name"], {}, st, cm)
        crow.append([cid, c["name"], c["kind"], c["configurable"], r["version"], r["status_label"], None, None, None])
    sheet("Controls", ["ID", "Name", "Kind", "Configurable", "Version", "Current status", "Status", "Reviewer comment", "Reviewer"], crow, [10, 40, 14, 16, 14, 18, 20, 50, 20], 7)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _cells(ws) -> List[Dict[str, Any]]:
    heads = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
    rows = []
    for i, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(v is None or str(v).strip() == "" for v in r):
            continue
        rows.append({"_row": i, **{h: (str(v).strip() if v is not None and str(v).strip() != "" else None) for h, v in zip(heads, r) if h}})
    return rows


def import_xlsx(user, data: bytes) -> Dict[str, Any]:
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(data), data_only=True, read_only=False)
    except Exception:
        raise V2Error(400, "INVALID", "The file is not an Excel workbook (.xlsx)")
    need = {"Profiles": ("Code", "Version", "Status"), "Controls": ("ID", "Version", "Status"), "Evidence": ("Code", "Evidence", "Version", "Reviewer comment")}
    if "Profiles" not in wb.sheetnames or "Controls" not in wb.sheetnames:
        raise V2Error(400, "INVALID", "This is not a PeX review workbook: it needs Profiles and Controls sheets")
    applied = 0
    rejected: List[Dict[str, Any]] = []
    db = SessionLocal()
    try:
        def bad(sheet, row, id_, why):
            rejected.append({"sheet": sheet, "row": row, "id": id_ or "", "reason": why})

        for sheet in ("Profiles", "Controls", "Evidence"):
            if sheet not in wb.sheetnames:
                continue
            ws = wb[sheet]
            heads = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
            miss = [h for h in need[sheet] if h not in heads]
            if miss:
                raise V2Error(400, "INVALID", f"The {sheet} sheet is missing the column(s): {', '.join(miss)}")
            for r in _cells(ws):
                kind = "control" if sheet == "Controls" else "profile"
                id_ = r.get("ID") if sheet == "Controls" else r.get("Code")
                if not id_ or not exists(kind, id_):
                    bad(sheet, r["_row"], id_, f"{kind.capitalize()} {id_ or '(blank)'} is not in the library")
                    continue
                text, label, name = r.get("Reviewer comment"), r.get("Status"), r.get("Reviewer")
                if sheet == "Evidence":
                    if not text:
                        continue
                    if r.get("Version") != short(content_hash("profile", id_)):
                        bad(sheet, r["_row"], id_, "This profile changed since the file was exported; export a fresh workbook")
                        continue
                    if r.get("Evidence") not in {e["type"] for e in library.profile(id_)["evidence"]}:
                        bad(sheet, r["_row"], id_, f"Evidence {r.get('Evidence')} is not part of this profile")
                        continue
                    try:
                        if _add_comment(db, user, "profile", id_, text, f"evidence: {r['Evidence']}", name):
                            applied += 1
                    except V2Error as e:
                        bad(sheet, r["_row"], id_, e.message if hasattr(e, "message") else str(e))
                    continue
                if not label and not text:
                    continue
                if r.get("Version") != short(content_hash(kind, id_)):
                    bad(sheet, r["_row"], id_, "This item changed since the file was exported; export a fresh workbook")
                    continue
                status = None
                if label:
                    status = FROM_LABEL.get(label.lower())
                    if not status:
                        bad(sheet, r["_row"], id_, f"Status '{label}' is not one of: In review, Changes requested, Signed off")
                        continue
                    if status == "SIGNED_OFF" and text:
                        bad(sheet, r["_row"], id_, "A row with a comment cannot be signed off; sign off once the comment is addressed")
                        continue
                try:
                    did = False
                    if text and _add_comment(db, user, kind, id_, text, None, name):
                        did = True
                    if status:
                        _apply_status(db, user, kind, id_, status, None, name)
                        did = True
                    applied += did
                    db.flush()
                except V2Error as e:
                    bad(sheet, r["_row"], id_, getattr(e, "message", None) or str(e))
        db.commit()
    except V2Error:
        db.rollback()
        raise
    finally:
        db.close()
    _audit(user, "SME_REVIEW_IMPORTED", f"Imported a review workbook: {applied} row(s) applied, {len(rejected)} rejected.")
    return {"applied": applied, "rejected": rejected}
