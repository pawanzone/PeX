"""Files attached to a case by a maker, shown to the approver with the handover note.

Rules
  - Upload needs the maker permission (case.work). Opening needs pii.reveal (the roles that may reveal personal data), because an attachment can hold real names and numbers.
  - Up to 5 MB. PDF, PNG, JPEG, text, CSV, Word (docx) and Excel (xlsx) only, and the content must match the type.
  - The file name is cleaned. The file is stored with its SHA-256 fingerprint. It is only ever sent back as a download.
  - A file can be tied to a submission only by the person who uploaded it, and only on the case it was uploaded to.
  - Adding and opening are recorded in the audit trail.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
import uuid
from typing import Any, Dict, Optional, Tuple

from app.db.models import V2AttachmentModel as M
from app.db.session import SessionLocal
from app.services.data_loader import repo
from app.services.v2 import actions as ac
from app.services.v2.core import V2Error, invalid, iso, not_found, now, require

MAX_BYTES = 5 * 1024 * 1024
TYPES = {
    "pdf": ("application/pdf", b"%PDF"), "png": ("image/png", b"\x89PNG\r\n\x1a\n"), "jpg": ("image/jpeg", b"\xff\xd8\xff"),
    "jpeg": ("image/jpeg", b"\xff\xd8\xff"), "txt": ("text/plain", None), "csv": ("text/csv", None),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04"),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK\x03\x04"),
}
ALLOWED_TEXT = ", ".join(sorted({"PDF", "PNG", "JPEG", "TXT", "CSV", "DOCX", "XLSX"}))


def clean_name(raw: str) -> str:
    n = re.sub(r"[\x00-\x1f\x7f]", "", str(raw or ""))
    n = n.replace("\\", "/").split("/")[-1].strip().strip(".")
    return n[:120]


def _meta(r: M) -> Dict[str, Any]:
    return {"id": r.id, "name": r.name, "size": r.size, "sha256": r.sha256, "content_type": r.content_type, "uploaded_by": r.uploaded_by, "uploaded_at": r.uploaded_at}


def add(case_id: str, user, name: Optional[str], content_base64: Optional[str]) -> Dict[str, Any]:
    require(user, "case.work", "Only the person preparing the case can attach files.")
    case = repo.get_case(case_id)
    if not case:
        raise not_found(f"Case {case_id}")
    fname = clean_name(name or "")
    if not fname:
        raise invalid("Choose a file to attach.", "name")
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext not in TYPES:
        raise invalid(f"This file type is not accepted. Use one of: {ALLOWED_TEXT}.", "name")
    if not content_base64:
        raise invalid("The file is empty.", "content_base64")
    if len(content_base64) > MAX_BYTES * 4 // 3 + 16:
        raise V2Error(413, "TOO_LARGE", "The file is larger than 5 MB.", "content_base64")
    try:
        data = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise invalid("The file could not be read.", "content_base64")
    if not data:
        raise invalid("The file is empty.", "content_base64")
    if len(data) > MAX_BYTES:
        raise V2Error(413, "TOO_LARGE", "The file is larger than 5 MB.", "content_base64")
    ctype, magic = TYPES[ext]
    if magic is not None and not data.startswith(magic):
        raise invalid(f"The content of this file does not look like a {ext.upper()} file.", "name")
    if magic is None:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise invalid(f"The content of this file does not look like a {ext.upper()} file.", "name")
        if "\x00" in text:
            raise invalid(f"The content of this file does not look like a {ext.upper()} file.", "name")
    row = M(id=uuid.uuid4().hex[:16], case_id=case_id, name=fname, content_type=ctype, size=len(data), sha256=hashlib.sha256(data).hexdigest(),
            data=data, uploaded_by=user.user_id, uploaded_at=iso(now()), linked=False)
    db = SessionLocal()
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        meta = _meta(row)
    finally:
        db.close()
    ac.audit(case, user, "HITL_ATTACHMENT", "ATTACHMENT_ADDED", f"{user.name} attached {fname} ({len(data)} bytes, SHA-256 {meta['sha256'][:12]}).",
             ["Attachment fingerprint recorded"])
    return meta


def _row(case_id: str, aid: str) -> M:
    db = SessionLocal()
    try:
        r = db.query(M).filter(M.id == aid, M.case_id == case_id).first()
        if r:
            db.expunge(r)
        return r
    finally:
        db.close()


def for_submit(case_id: str, aid: str, user) -> Dict[str, Any]:
    """Check a file can be tied to this submission and mark it as used. Returns what the handover note keeps."""
    r = _row(case_id, aid)
    if not r:
        raise not_found("Attachment")
    if r.uploaded_by != user.user_id:
        raise V2Error(403, "FORBIDDEN", "You can only attach a file you uploaded yourself.")
    db = SessionLocal()
    try:
        db.query(M).filter(M.id == aid).update({"linked": True})
        db.commit()
    finally:
        db.close()
    return {"id": r.id, "name": r.name, "size": r.size, "sha256": r.sha256}


def open_file(case_id: str, aid: str, user) -> Tuple[str, str, bytes]:
    require(user, "pii.reveal", "Your role cannot open attached files.")
    r = _row(case_id, aid)
    if not r:
        raise not_found("Attachment")
    case = repo.get_case(case_id)
    ac.audit(case, user, "HITL_ATTACHMENT", "ATTACHMENT_OPENED", f"{user.name} opened {r.name} (SHA-256 {r.sha256[:12]}).", ["Attachment access logged"])
    return r.name, r.content_type, bytes(r.data)


def remove(case_id: str, aid: str, user) -> None:
    require(user, "case.work")
    r = _row(case_id, aid)
    if not r:
        raise not_found("Attachment")
    if r.uploaded_by != user.user_id:
        raise V2Error(403, "FORBIDDEN", "You can only remove a file you uploaded yourself.")
    if r.linked:
        raise V2Error(409, "INVALID_STATE", "This file is already part of a submitted handover note and cannot be removed.")
    db = SessionLocal()
    try:
        db.query(M).filter(M.id == aid).delete()
        db.commit()
    finally:
        db.close()
