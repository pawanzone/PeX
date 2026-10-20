"""Shared helpers for the UI v2 API: errors, permissions, formatting, per-case extension store, profile catalogue."""
from __future__ import annotations

import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Header

from app.config import settings
from app.core.auth import resolve_user_id
from app.core.security import get_persona
from app.db.session import SessionLocal
from app.db.models import CaseExtModel


# ----------------------------------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------------------------------
class V2Error(Exception):
    def __init__(self, status: int, code: str, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.status, self.code, self.message, self.field = status, code, message, field

    def body(self) -> Dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "field": self.field}, "detail": self.message}


def not_found(what: str) -> V2Error:
    return V2Error(404, "NOT_FOUND", f"{what} not found")


def invalid(msg: str, field: Optional[str] = None) -> V2Error:
    return V2Error(422, "VALIDATION", msg, field)


def bad_state(msg: str) -> V2Error:
    return V2Error(409, "INVALID_STATE", msg)


# ----------------------------------------------------------------------------------------------
# Time
# ----------------------------------------------------------------------------------------------
_now_override: Optional[datetime] = None


def set_now(dt: Optional[datetime]) -> None:
    """Tests only: freeze the v2 clock."""
    global _now_override
    _now_override = dt


def now() -> datetime:
    return _now_override or datetime.now(timezone.utc)


def parse_ts(v: Any) -> Optional[datetime]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        s = str(v).replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def hhmm(dt: Optional[datetime]) -> Optional[str]:
    return dt.astimezone(timezone.utc).strftime("%H:%M") if dt else None


def duration_label(seconds: float) -> str:
    s = int(max(0, seconds))
    h, m = s // 3600, (s % 3600) // 60
    if h >= 1:
        return f"{h}h {m:02d}m" if m else f"{h}h"
    if m >= 1:
        return f"{m}m"
    return "<1m"


def cutoff_obj(at: Optional[datetime], ref: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    if at is None:
        return None
    ref = ref or now()
    left = (at - ref).total_seconds()
    if left <= 0:
        band, label = "passed", "Passed"
    else:
        label = duration_label(left)
        band = "under_1h" if left < 3600 else ("1_to_3h" if left <= 10800 else "over_3h")
    return {"at": iso(at), "hhmm": hhmm(at), "seconds_left": int(left), "time_left": label, "band": band}


def money(amount: Any, currency: Any) -> Dict[str, Any]:
    a = float(amount or 0.0)
    c = str(currency or "USD")
    return {"amount": a, "currency": c, "display": f"{c} {a:,.2f}"}


# ----------------------------------------------------------------------------------------------
# Rails / profiles
# ----------------------------------------------------------------------------------------------
def rail_obj(raw: Any) -> Dict[str, str]:
    r = str(raw or "").upper().replace(" ", "_")
    table = {
        "SWIFT": ("SWIFT_CBPR+", "SWIFT CBPR+"), "SWIFT_CBPR+": ("SWIFT_CBPR+", "SWIFT CBPR+"), "CBPR+": ("SWIFT_CBPR+", "SWIFT CBPR+"),
        "FEDWIRE": ("FEDWIRE", "Fedwire"), "CHAPS": ("CHAPS", "CHAPS"), "TARGET2": ("TARGET2", "T2"), "T2": ("TARGET2", "T2"),
        "SEPA": ("SEPA", "SEPA"), "SEPA_SCT": ("SEPA", "SEPA"), "SEPA_INST": ("SEPA", "SEPA"), "BACS": ("BACS", "BACS"),
    }
    if r in table:
        k, l = table[r]
        return {"key": k, "label": l}
    return {"key": r or "UNKNOWN", "label": (str(raw) if raw else "Unknown")}


SHORT_LABELS = {
    "INVALID_IBAN": "Invalid IBAN", "INVALID_BIC": "Invalid BIC", "MISSING_BENEFICIARY_DATA": "Missing beneficiary data",
    "MISSING_REMITTANCE_INFO": "Missing remittance", "INVALID_ADDRESS_FORMAT": "Invalid address format",
    "MISSING_PURPOSE_CODE": "Missing purpose code", "INVALID_ACCOUNT_NUMBER": "Invalid account number",
    "INVALID_ROUTING_CODE": "Invalid routing code", "BENEFICIARY_NAME_MISMATCH": "Name mismatch",
    "DUPLICATE_PAYMENT": "Possible duplicate", "ROUTING_FAILURE": "Routing failure",
    "ISO20022_VALIDATION_ERROR": "Message validation error", "CUTOFF_MISSED": "Cutoff missed",
    "CORRUPTED_MESSAGE_FORMAT": "Corrupted message", "INTERMEDIARY_BANK_REJECTION": "Intermediary rejection",
    "NETWORK_TIMEOUT": "Network timeout", "QUEUE_PROCESSING_FAILURE": "Queue failure", "PAYMENT_HELD_FOR_REPAIR": "Held for repair",
    "SANCTIONS_SUSPECTED": "Sanctions hit", "AML_ALERT": "AML alert", "PEP_MATCH": "PEP match",
    "RESTRICTED_CORRIDOR": "Restricted corridor", "ADVERSE_MEDIA_MATCH": "Adverse media",
    "HIGH_RISK_JURISDICTION": "High-risk jurisdiction", "REGULATORY_REPORTING_REQUIRED": "Regulatory reporting",
    "CUSTOMER_WATCHLIST_MATCH": "Watchlist match", "KYC_EXPIRED": "KYC expired", "INSUFFICIENT_FUNDS": "Insufficient funds",
    "NOSTRO_SHORTFALL": "Nostro shortfall", "FX_RATE_UNAVAILABLE": "FX rate unavailable", "AUTHORIZATION_MISSING": "Authorisation missing",
    "LIMIT_BREACH": "Limit breach", "LIQUIDITY_CONSTRAINT": "Liquidity constraint", "CREDIT_EXPOSURE_BREACH": "Credit exposure breach",
    "RETURNED_PAYMENT": "Returned payment", "ACCOUNT_CLOSED": "Account closed", "BENEFICIARY_ACCOUNT_FROZEN": "Account frozen",
    "RECONCILIATION_BREAK": "Reconciliation break", "SETTLEMENT_FAILURE": "Settlement failure",
    "FUNDS_TRAPPED_AT_CORRESPONDENT": "Funds trapped", "UNMATCHED_CREDIT": "Unmatched credit",
}

HARD_BLOCK_STP = {"TR-08", "ST-06"}
_code_to_enum: Optional[Dict[str, Any]] = None
_enum_to_code: Dict[str, str] = {}


def _maps():
    global _code_to_enum, _enum_to_code
    if _code_to_enum is None:
        from app.services.file_watcher import PROFILE_CODE_TO_ENUM
        _code_to_enum = dict(PROFILE_CODE_TO_ENUM)
        _enum_to_code = {v.value: k for k, v in _code_to_enum.items()}
    return _code_to_enum, _enum_to_code


def profile_code(profile: Any) -> str:
    """Canonical code (DQ-01...) for a case profile that may be a code or an enum name."""
    c2e, e2c = _maps()
    p = str(getattr(profile, "value", profile) or "").upper()
    if p in c2e:
        return p
    return e2c.get(p, p)


def profile_enum_name(profile: Any) -> str:
    c2e, _ = _maps()
    code = profile_code(profile)
    return c2e[code].value if code in c2e else str(profile)


def profile_label(profile: Any) -> str:
    return SHORT_LABELS.get(profile_enum_name(profile), str(profile).replace("_", " ").title())


def profile_spec(profile: Any) -> Dict[str, Any]:
    from app.services.profile_engine import PROFILE_SPECS
    c2e, _ = _maps()
    code = profile_code(profile)
    enum = c2e.get(code)
    return PROFILE_SPECS.get(enum, {}) if enum else {}


def domain_of(case: Dict[str, Any]) -> str:
    return str(getattr(case.get("domain"), "value", case.get("domain")) or "").upper()


def is_compliance(case: Dict[str, Any]) -> bool:
    return domain_of(case) == "COMPLIANCE" or str(case.get("queue")) == "Compliance"


def party_name(p: Any) -> str:
    if isinstance(p, dict):
        return str(p.get("party_name") or p.get("name") or "Unknown party")
    return str(p or "Unknown party")


def account_str(a: Any) -> str:
    if isinstance(a, dict):
        return str(a.get("iban") or a.get("account_number") or a.get("account_id") or "")
    return str(a or "")


# ----------------------------------------------------------------------------------------------
# Users, permissions
# ----------------------------------------------------------------------------------------------
ROLE_LABELS = {
    "OPERATOR": "Maker", "SUPERVISOR": "Supervisor", "OPERATIONS_APPROVER": "Operations Approver",
    "COMPLIANCE_APPROVER": "Compliance Officer", "RISK_APPROVER": "Risk Approver (tier 2)",
    "AUDIT_RISK": "Audit and Risk", "ADMIN": "Administrator",
}
PERMISSIONS: Dict[str, List[str]] = {
    "OPERATOR": ["case.read", "case.work", "case.assign", "batch.upload", "pii.reveal"],
    "SUPERVISOR": ["case.read", "case.work", "case.assign", "case.reassign", "audit.read", "batch.upload", "pii.reveal"],
    "OPERATIONS_APPROVER": ["case.read", "case.approve", "stp.approve", "pii.reveal"],
    "COMPLIANCE_APPROVER": ["case.read", "compliance.decide", "audit.read", "pii.reveal"],
    "RISK_APPROVER": ["case.read", "case.approve", "stp.approve", "compliance.decide", "pii.reveal"],
    "AUDIT_RISK": ["case.read", "audit.read", "audit.export", "pii.reveal"],
    "ADMIN": ["case.read", "case.approve", "audit.read", "audit.export", "admin.read", "admin.mode_change", "admin.mode_approve", "batch.upload"],
}
NAV = {
    "OPERATOR": ["home", "worklist", "batches"],
    "SUPERVISOR": ["home", "worklist", "approvals", "compliance", "batches", "audit"],
    "OPERATIONS_APPROVER": ["home", "approvals", "worklist", "batches"],
    "RISK_APPROVER": ["home", "approvals", "compliance", "worklist", "batches"],
    "COMPLIANCE_APPROVER": ["home", "compliance", "audit"],
    "AUDIT_RISK": ["audit"],
    "ADMIN": ["home", "batches", "audit", "admin"],
}
NAV_LABELS = {"home": ("Home", "/"), "worklist": ("Worklist", "/worklist"), "approvals": ("Approvals", "/approvals"),
              "compliance": ("Compliance", "/compliance"), "batches": ("Batches", "/batches"), "audit": ("Audit", "/audit"),
              "admin": ("Admin", "/admin")}


def role_of(user) -> str:
    return str(getattr(user.role, "value", user.role))


def has_perm(user, perm: str) -> bool:
    return perm in PERMISSIONS.get(role_of(user), [])


def require(user, perm: str, msg: Optional[str] = None):
    if not has_perm(user, perm):
        if role_of(user) == "AUDIT_RISK" and not perm.endswith(".read") and perm != "audit.export":
            raise V2Error(403, "READ_ONLY_ROLE", "Audit and Risk is a read-only role.")
        raise V2Error(403, "FORBIDDEN", msg or f"Your role ({ROLE_LABELS.get(role_of(user), role_of(user))}) cannot do this.")


def current_user(authorization: Optional[str] = Header(None)):
    from fastapi import HTTPException
    try:
        uid = resolve_user_id(authorization)
    except HTTPException as e:
        raise V2Error(401, "AUTH_REQUIRED", str(e.detail))
    p = get_persona(uid)
    if p is None:
        raise V2Error(401, "AUTH_REQUIRED", f"Unknown user '{uid}'")
    return p


def writer_user(authorization: Optional[str] = Header(None)):
    u = current_user(authorization)
    if role_of(u) == "AUDIT_RISK":
        raise V2Error(403, "READ_ONLY_ROLE", "Audit and Risk is a read-only role.")
    return u


def person(uid: Optional[str]) -> Optional[Dict[str, str]]:
    if not uid:
        return None
    p = get_persona(uid)
    if not p:
        return {"user_id": uid, "name": uid}
    return {"user_id": p.user_id, "name": p.name}


def role_label_for(uid: Optional[str], fallback: str = "") -> str:
    p = get_persona(uid) if uid else None
    return ROLE_LABELS.get(role_of(p), fallback) if p else fallback


# ----------------------------------------------------------------------------------------------
# Extension store (per-case v2 working data). Memory-first; writes are deferred while a batch
# transaction is open (SQLite single-writer) and flushed afterwards.
# ----------------------------------------------------------------------------------------------
class _ExtStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._mem: Dict[str, Dict[str, Any]] = {}
        self._dirty: set = set()
        self._loaded = False

    def reset(self):
        with self._lock:
            self._mem.clear()
            self._dirty.clear()
            self._loaded = False

    def _load(self):
        if self._loaded:
            return
        db = SessionLocal()
        try:
            for r in db.query(CaseExtModel).all():
                self._mem.setdefault(r.case_id, dict(r.data or {}))
            self._loaded = True
        except Exception:
            self._loaded = False
        finally:
            db.close()

    def get(self, case_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._load()
            return self._mem.get(case_id)

    def put(self, case_id: str, data: Dict[str, Any], persist: bool = True):
        with self._lock:
            self._mem[case_id] = data
            if persist:
                self._dirty.add(case_id)

    def patch(self, case_id: str, **kv):
        with self._lock:
            self._load()
            d = self._mem.setdefault(case_id, {})
            d.update(kv)
            self._dirty.add(case_id)
            return d

    def all_ids(self) -> List[str]:
        with self._lock:
            self._load()
            return list(self._mem.keys())

    def discard(self, case_id: str):
        with self._lock:
            self._mem.pop(case_id, None)
            self._dirty.discard(case_id)

    def flush(self):
        with self._lock:
            if not self._dirty:
                return
            ids = list(self._dirty)
            db = SessionLocal()
            try:
                stamp = iso(now())
                for cid in ids:
                    data = self._mem.get(cid)
                    if data is None:
                        continue
                    row = db.query(CaseExtModel).filter(CaseExtModel.case_id == cid).first()
                    if row:
                        row.data = _jsonable(data)
                        row.updated_at = stamp
                    else:
                        db.add(CaseExtModel(case_id=cid, data=_jsonable(data), updated_at=stamp))
                db.commit()
                self._dirty.difference_update(ids)
            except Exception as e:  # pragma: no cover
                db.rollback()
                print(f"[PeX v2] ext flush failed: {e}")
            finally:
                db.close()


def _jsonable(o: Any) -> Any:
    import json
    return json.loads(json.dumps(o, default=str))


ext_store = _ExtStore()


def save_ext(case_id: str, data: Dict[str, Any]):
    """Persist now (outside a batch transaction)."""
    ext_store.put(case_id, data)
    ext_store.flush()


def new_id(prefix: str) -> str:
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
