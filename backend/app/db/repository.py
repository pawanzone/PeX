"""Persistent Relational Database Repository for PeX Enterprise Platform."""
import logging
import os
import threading
from typing import Dict, List, Any, Optional

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

logger = logging.getLogger(__name__)

from app.db.session import SessionLocal
from app.db.models import (
    CaseModel,
    AuditEventModel,
    TokenVaultModel,
    RecommendationModel,
    ApprovalRecordModel,
    GovernedActionModel,
    DeliveryReceiptModel,
    UserModel,
    RolePermissionModel,
    PolicyRuleModel,
    ICDConfigurationModel,
)
from app.core.hashing import calculate_event_hash
from app.services.state_machine import normalize_status

def _sanitize_for_json(val: Any) -> Any:
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, dict):
        return {str(k): _sanitize_for_json(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_sanitize_for_json(item) for item in val]
    if hasattr(val, "value"):
        return val.value
    return val

class PeXDBRepository:
    """Database-backed repository providing persistent storage with thread-safe sessions."""

    def __init__(self):
        # In-memory fast cache synced with DB
        self._case_cache: Dict[str, Dict[str, Any]] = {}
        self._recommendations_cache: Dict[str, Any] = {}
        self._approvals_cache: Dict[str, List[Any]] = {}
        self._actions_cache: Dict[str, Any] = {}
        self._receipts_cache: Dict[str, Any] = {}
        self._rules_cache: Dict[str, Dict[str, Any]] = {}
        self._icd_cache: Dict[str, Dict[str, Any]] = {}
        self._latest_hash: str = "0" * 64
        self._audit_lock = threading.RLock()
        self._tl = threading.local()
        self._case_cache_max = int(os.getenv("PEX_CASE_CACHE_MAX", "20000"))


    def load_all_data(self):
        """Initializes database tables and syncs in-memory caches from persistent DB."""
        from app.db.init_db import init_db
        init_db()
        self.sync_from_db()

    def sync_from_db(self):
        """Refreshes in-memory caches from database records."""
        db: Session = SessionLocal()
        try:
            # Sync Cases
            db_cases = db.query(CaseModel).order_by(desc(CaseModel.created_at)).limit(self._case_cache_max).all()
            self._case_cache.clear()
            for c in db_cases:
                self._case_cache[c.case_id] = self._case_to_dict(c)

            # Sync Recommendations
            db_recs = db.query(RecommendationModel).order_by(desc(RecommendationModel.generated_at)).limit(self._case_cache_max).all()
            self._recommendations_cache.clear()
            for r in db_recs:
                self._recommendations_cache[r.case_id] = self._rec_to_schema(r)

            # Sync Approvals
            db_approvals = db.query(ApprovalRecordModel).order_by(ApprovalRecordModel.created_at).all()
            self._approvals_cache.clear()
            for a in db_approvals:
                if a.case_id not in self._approvals_cache:
                    self._approvals_cache[a.case_id] = []
                self._approvals_cache[a.case_id].append(self._approval_to_schema(a))

            # Sync Actions & Receipts
            db_actions = db.query(GovernedActionModel).all()
            self._actions_cache.clear()
            for act in db_actions:
                self._actions_cache[act.idempotency_key] = self._action_to_schema(act)

            db_receipts = db.query(DeliveryReceiptModel).all()
            self._receipts_cache.clear()
            for rcpt in db_receipts:
                self._receipts_cache[rcpt.action_id] = self._receipt_to_schema(rcpt)

            # Sync Policy Rules
            db_rules = db.query(PolicyRuleModel).all()
            self._rules_cache.clear()
            for r in db_rules:
                self._rules_cache[r.rule_id] = self._rule_to_dict(r)

            # Sync ICD Configurations
            db_icds = db.query(ICDConfigurationModel).all()
            self._icd_cache.clear()
            for icd in db_icds:
                self._icd_cache[icd.icd_id] = self._icd_to_dict(icd)

            # Sync Latest Hash
            latest_ev = db.query(AuditEventModel).order_by(desc(AuditEventModel.event_index)).first()
            if latest_ev:
                self._latest_hash = latest_ev.current_hash
            else:
                self._latest_hash = "0" * 64

            # Sync Token Vault
            from app.core.tokenization import token_vault
            db_tokens = db.query(TokenVaultModel).all()
            for t in db_tokens:
                token_vault._raw_to_token[t.raw_value.strip().replace(" ", "").upper()] = t.token_value
                token_vault._token_to_raw[t.token_value] = t.raw_value.strip().replace(" ", "").upper()

            print(f"[PeX Repo] Synced {len(self._case_cache)} cases, {len(self._rules_cache)} rules, {len(self._icd_cache)} ICD nodes, latest hash {self._latest_hash[:8]}... from DB.")
        finally:
            db.close()

    @property
    def latest_chain_hash(self) -> str:
        return self._latest_hash

    @latest_chain_hash.setter
    def latest_chain_hash(self, val: str):
        self._latest_hash = val

    @property
    def cases(self) -> Dict[str, Dict[str, Any]]:
        return self._case_cache

    @property
    def recommendations(self) -> Dict[str, Any]:
        return self._recommendations_cache

    @property
    def approvals(self) -> Dict[str, List[Any]]:
        return self._approvals_cache

    @property
    def actions(self) -> Dict[str, Any]:
        return self._actions_cache

    @property
    def receipts(self) -> Dict[str, Any]:
        return self._receipts_cache

    @property
    def rules(self) -> Dict[str, Dict[str, Any]]:
        return self._rules_cache

    @property
    def icd_nodes(self) -> Dict[str, Dict[str, Any]]:
        return self._icd_cache

    @property
    def policies(self) -> List[Any]:
        from app.schemas.canonical import ExceptionProfile
        from app.schemas.context import PolicyRule
        return [
            PolicyRule(
                policy_id="POL-IBAN-01",
                profile=ExceptionProfile.INVALID_IBAN,
                rule_code="POL-IBAN-AUTO-REPAIR",
                rule_description="Beneficiary IBAN repair eligible with standing instruction match.",
                mandatory_evidence=["BENEFICIARY_PROFILE", "ACCOUNT_DIRECTORY"],
                auto_repair_eligible=True,
                max_amount_threshold=250000.0,
                required_confidence_threshold=0.85
            )
        ]

    @property
    def beneficiaries(self) -> Dict[str, Any]:
        return {
            "BEN-GB-8841": {
                "beneficiary_id": "BEN-GB-8841",
                "name": "HarborView Supplier Ltd",
                "beneficiary_name": "HarborView Supplier Ltd",
                "standing_iban": "GB82WEST12345698765431",
                "clearing_bank": "National Westminster Bank PLC",
                "bic": "WESTGB2L",
                "verified_date": "2026-01-15",
                "standing_instruction_active": "true"
            }
        }

    @property
    def historical_cases(self) -> List[Dict[str, Any]]:
        return [
            {
                "case_id": "HIST-2025-0982",
                "similarity_score": "0.94",
                "action_taken": "REPAIR_IBAN",
                "outcome": "SETTLED_CONFIRMED",
                "rationale": "Repaired last check digit from 2 to 1 matching beneficiary directory."
            }
        ]

    @property
    def audit_log(self) -> List[Any]:
        """Returns all audit events ordered by event_index."""
        db: Session = SessionLocal()
        try:
            db_events = db.query(AuditEventModel).order_by(AuditEventModel.event_index).all()
            from app.schemas.audit import AuditEvent
            result = []
            for ev in db_events:
                try:
                    ts = datetime.fromisoformat(ev.timestamp.replace("Z", "+00:00").split("+")[0])
                except (ValueError, TypeError, AttributeError) as exc:
                    logger.warning(
                        "Failed to parse datetime timestamp '%s' for audit event index %s: %s. Using datetime.utcnow() fallback.",
                        ev.timestamp, ev.event_index, exc
                    )
                    ts = datetime.utcnow()
                result.append(AuditEvent(
                    event_index=ev.event_index,
                    timestamp=ts,
                    case_id=ev.case_id,
                    correlation_id=ev.correlation_id,
                    stage_name=ev.stage_name,
                    actor_id=ev.actor_id,
                    actor_role=ev.actor_role,
                    action_name=ev.action_name,
                    details=ev.details,
                    control_tags=ev.control_tags or [],
                    prev_hash=ev.prev_hash,
                    current_hash=ev.current_hash
                ))
            return result
        finally:
            db.close()

    def log_audit_event(
        self,
        case_id: str,
        correlation_id: str,
        stage_name: str,
        actor_id: str,
        actor_role: str,
        action_name: str,
        details: str,
        control_tags: Optional[List[str]] = None,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        debtor_account: Optional[str] = None,
        creditor_account: Optional[str] = None
    ):
        """Appends a new cryptographically chained audit event directly to DB and updates latest hash."""
        from app.schemas.audit import AuditEvent
        from app.core.hashing import calculate_event_hash
        
        # Auto-lookup financial fields from case if not explicitly provided
        if case_id and (amount is None or currency is None):
            c = self.get_case(case_id)
            if c:
                if amount is None:
                    amount = float(c.get("amount", 0.0)) if c.get("amount") is not None else None
                if currency is None:
                    currency = c.get("currency")
                if debtor_account is None:
                    debtor_account = c.get("debtor_account")
                if creditor_account is None:
                    creditor_account = c.get("creditor_account")

        def _extract_account_str(acc: Any) -> Optional[str]:
            if acc is None:
                return None
            if isinstance(acc, str):
                return acc
            if isinstance(acc, dict):
                return acc.get("account_number") or acc.get("iban") or acc.get("account_id") or str(acc)
            if hasattr(acc, "account_number") and getattr(acc, "account_number"):
                return str(getattr(acc, "account_number"))
            if hasattr(acc, "iban") and getattr(acc, "iban"):
                return str(getattr(acc, "iban"))
            if hasattr(acc, "account_id") and getattr(acc, "account_id"):
                return str(getattr(acc, "account_id"))
            return str(acc)

        debtor_account = _extract_account_str(debtor_account)
        creditor_account = _extract_account_str(creditor_account)
                    
        with self._audit_lock:
            ctx = self._bctx()
            db: Session = ctx.session if ctx else SessionLocal()
            try:
                if ctx:
                    idx, prev_hash = ctx.next_idx, ctx.prev_hash
                else:
                    latest_ev = db.query(AuditEventModel).order_by(desc(AuditEventModel.event_index)).first()
                    idx = (latest_ev.event_index + 1) if latest_ev else 1
                    prev_hash = latest_ev.current_hash if latest_ev else ("0" * 64)
                now_dt = datetime.utcnow()
                timestamp_iso = now_dt.isoformat()

                curr_hash = calculate_event_hash(
                    event_index=idx,
                    timestamp_iso=timestamp_iso,
                    case_id=case_id,
                    stage_name=stage_name,
                    actor_id=actor_id,
                    action_name=action_name,
                    details=details,
                    prev_hash=prev_hash,
                    amount=amount,
                    currency=currency,
                    debtor_account=debtor_account,
                    creditor_account=creditor_account
                )

                db_ev = AuditEventModel(
                    event_index=idx,
                    case_id=case_id,
                    correlation_id=correlation_id,
                    stage_name=stage_name,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    action_name=action_name,
                    timestamp=timestamp_iso,
                    details=details,
                    control_tags=control_tags or [],
                    amount=amount,
                    currency=currency,
                    debtor_account=debtor_account,
                    creditor_account=creditor_account,
                    prev_hash=prev_hash,
                    current_hash=curr_hash
                )
                db.add(db_ev)
                if ctx:
                    ctx.next_idx, ctx.prev_hash = idx + 1, curr_hash
                else:
                    db.commit()
                    self._latest_hash = curr_hash

                return AuditEvent(
                    event_index=idx,
                    timestamp=now_dt,
                    case_id=case_id,
                    correlation_id=correlation_id,
                    stage_name=stage_name,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    action_name=action_name,
                    details=details,
                    control_tags=control_tags or [],
                    amount=amount,
                    currency=currency,
                    debtor_account=debtor_account,
                    creditor_account=creditor_account,
                    prev_hash=prev_hash,
                    current_hash=curr_hash
                )
            except Exception as e:
                if not ctx:
                    db.rollback()
                print(f"[PeX DB Error] Failed to log audit event: {e}")
                raise e
            finally:
                if not ctx:
                    db.close()

    # ------------------------------------------------------------------
    # Bounded cache + batch (bulk transaction) support
    # ------------------------------------------------------------------
    def _cache_put(self, case_id: str, d: Dict[str, Any]):
        cache = self._case_cache
        if case_id in cache:
            cache[case_id] = d
            return
        while len(cache) >= self._case_cache_max and cache:
            cache.pop(next(iter(cache)))
        cache[case_id] = d

    def _bctx(self):
        return getattr(self._tl, "ctx", None)

    def begin_batch(self):
        """Start a bulk transaction on this thread: one session, one audit-chain read, no per-event commit.
        Holds the audit lock until commit_batch/rollback_batch so the hash chain stays gap-free."""
        self._audit_lock.acquire()
        try:
            class _Ctx:  # noqa: N801
                pass
            ctx = _Ctx()
            ctx.session = SessionLocal()
            latest = ctx.session.query(AuditEventModel).order_by(desc(AuditEventModel.event_index)).first()
            ctx.next_idx = (latest.event_index + 1) if latest else 1
            ctx.prev_hash = latest.current_hash if latest else ("0" * 64)
            ctx.pending_cases = {}
            ctx.pending_recs = {}
            ctx.mark = None
            self._tl.ctx = ctx
        except Exception:
            self._audit_lock.release()
            raise

    def batch_record_begin(self):
        ctx = self._bctx()
        ctx.mark = (set(ctx.session.new), ctx.next_idx, ctx.prev_hash, set(ctx.pending_cases), set(ctx.pending_recs))

    def batch_record_abort(self):
        """Discard everything staged since batch_record_begin (a single record failed)."""
        ctx = self._bctx()
        if not ctx or not ctx.mark:
            return
        before, idx, ph, cases, recs = ctx.mark
        for obj in list(ctx.session.new):
            if obj not in before:
                ctx.session.expunge(obj)
        ctx.next_idx, ctx.prev_hash = idx, ph
        for k in list(ctx.pending_cases):
            if k not in cases:
                ctx.pending_cases.pop(k)
        for k in list(ctx.pending_recs):
            if k not in recs:
                ctx.pending_recs.pop(k)

    def commit_batch(self, warm_cache: bool = False):
        ctx = self._bctx()
        try:
            ctx.session.commit()
            self._latest_hash = ctx.prev_hash
            if warm_cache:
                for k, v in ctx.pending_cases.items():
                    self._cache_put(k, v)
        except Exception:
            ctx.session.rollback()
            raise
        finally:
            self._end_batch(ctx)

    def rollback_batch(self):
        ctx = self._bctx()
        if ctx:
            try:
                ctx.session.rollback()
            finally:
                self._end_batch(ctx)

    def _end_batch(self, ctx):
        try:
            ctx.session.close()
        finally:
            self._tl.ctx = None
            self._audit_lock.release()

    def existing_case_ids(self, ids: List[str]) -> set:
        found = set()
        ids = list(ids)
        db: Session = SessionLocal()
        try:
            for i in range(0, len(ids), 400):
                part = ids[i:i + 400]
                rows = db.query(CaseModel.case_id).filter(CaseModel.case_id.in_(part)).all()
                found.update(r[0] for r in rows)
            return found
        finally:
            db.close()

    def existing_uetrs(self, uetrs: List[str]) -> set:
        found = set()
        uetrs = [u for u in uetrs if u]
        db: Session = SessionLocal()
        try:
            for i in range(0, len(uetrs), 400):
                part = uetrs[i:i + 400]
                rows = db.query(CaseModel.uetr).filter(CaseModel.uetr.in_(part)).all()
                found.update(r[0] for r in rows)
            return found
        finally:
            db.close()

    def case_count(self) -> int:
        db: Session = SessionLocal()
        try:
            return db.query(CaseModel).count()
        finally:
            db.close()

    def audit_event_count(self) -> int:
        db: Session = SessionLocal()
        try:
            return db.query(AuditEventModel).count()
        finally:
            db.close()

    @staticmethod
    def _audit_row_to_event(ev: AuditEventModel):
        from app.schemas.audit import AuditEvent
        try:
            ts = datetime.fromisoformat(ev.timestamp.replace("Z", "+00:00").split("+")[0])
        except (ValueError, TypeError, AttributeError):
            ts = datetime.utcnow()
        return AuditEvent(
            event_index=ev.event_index, timestamp=ts, case_id=ev.case_id,
            correlation_id=ev.correlation_id, stage_name=ev.stage_name, actor_id=ev.actor_id,
            actor_role=ev.actor_role, action_name=ev.action_name, details=ev.details,
            control_tags=ev.control_tags or [], prev_hash=ev.prev_hash, current_hash=ev.current_hash,
        )

    def recent_audit_events(self, limit: int = 200) -> List[Any]:
        """Most recent events, returned in ascending event_index order."""
        db: Session = SessionLocal()
        try:
            rows = db.query(AuditEventModel).order_by(desc(AuditEventModel.event_index)).limit(limit).all()
            return [self._audit_row_to_event(r) for r in reversed(rows)]
        finally:
            db.close()

    def case_audit_events(self, case_id: str) -> List[Any]:
        db: Session = SessionLocal()
        try:
            rows = (db.query(AuditEventModel).filter(AuditEventModel.case_id == case_id)
                    .order_by(AuditEventModel.event_index).all())
            return [self._audit_row_to_event(r) for r in rows]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # SQL-backed paging / aggregates (scale-safe, independent of the cache)
    # ------------------------------------------------------------------
    _ACTIONABLE_REPAIR = ("INGESTED", "CANONICALIZED", "VALIDATED", "INVESTIGATING", "RECOMMENDED",
                          "RETURNED_FOR_REWORK", "APPROVED", "FAILED")
    _PENDING_APPROVAL = ("PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL")

    @staticmethod
    def _norm_status(v: Any) -> str:
        return str(v or "").replace("LifecycleStage.", "")

    def page_cases(self, limit: int = 50, offset: int = 0, queue: Optional[str] = None, status: Optional[str] = None,
                   profile: Optional[str] = None, rail: Optional[str] = None, currency: Optional[str] = None,
                   q: Optional[str] = None, sort: str = "created_at", order: str = "desc") -> Dict[str, Any]:
        from sqlalchemy import String, cast, asc
        sortable = {"created_at": CaseModel.created_at, "amount": CaseModel.amount, "profile": CaseModel.profile,
                    "status": CaseModel.status, "queue": CaseModel.queue, "severity": CaseModel.severity,
                    "priority": CaseModel.priority, "case_id": CaseModel.case_id, "sla_due_at": CaseModel.sla_due_at}
        col = sortable.get(sort, CaseModel.created_at)
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        db: Session = SessionLocal()
        try:
            qry = db.query(CaseModel)
            def _f(c, v):
                return c == v
            if queue and queue != "All":
                qry = qry.filter(CaseModel.queue == queue)
            if status and status != "All":
                qry = qry.filter(or_(CaseModel.status == status, CaseModel.status == f"LifecycleStage.{status}"))
            if profile and profile != "All":
                qry = qry.filter(CaseModel.profile == profile)
            if rail and rail != "All":
                qry = qry.filter(CaseModel.payment_rail == rail)
            if currency and currency != "All":
                qry = qry.filter(CaseModel.currency == currency)
            if q:
                like = f"%{q.strip()}%"
                qry = qry.filter(or_(CaseModel.case_id.ilike(like), CaseModel.payment_ref.ilike(like),
                                     CaseModel.uetr.ilike(like), CaseModel.profile.ilike(like),
                                     cast(CaseModel.creditor_party, String).ilike(like)))
            total = qry.count()
            qry = qry.order_by(desc(col) if str(order).lower() != "asc" else asc(col), CaseModel.case_id)
            rows = qry.offset(offset).limit(limit).all()
            items = []
            for c in rows:
                cp = c.creditor_party or {}
                items.append({
                    "case_id": c.case_id, "payment_ref": c.payment_ref, "uetr": c.uetr, "profile": c.profile,
                    "domain": c.domain, "secondary_profiles": c.secondary_profiles or [], "error_code": c.error_code,
                    "reason": c.reason, "amount": c.amount, "currency": c.currency, "payment_rail": c.payment_rail,
                    "counterparty": cp.get("party_name") if isinstance(cp, dict) else None,
                    "queue": c.queue, "status": self._norm_status(c.status), "severity": c.severity,
                    "priority": c.priority, "sla_due_at": c.sla_due_at, "dual_auth_required": c.dual_auth_required,
                    "ai_confidence": c.ai_confidence, "created_at": c.created_at,
                    "dispatch_status": getattr(c, "dispatch_status", None),
                })
            return {"items": items, "total": total, "limit": limit, "offset": offset}
        finally:
            db.close()

    def summary_counts(self) -> Dict[str, Any]:
        from sqlalchemy import func
        db: Session = SessionLocal()
        try:
            def grp(col):
                return {str(k): int(n) for k, n in db.query(col, func.count()).group_by(col).all() if k is not None}
            by_status_raw = grp(CaseModel.status)
            by_status: Dict[str, int] = {}
            for k, n in by_status_raw.items():
                nk = self._norm_status(k)
                by_status[nk] = by_status.get(nk, 0) + n
            queue_status = db.query(CaseModel.queue, CaseModel.status, func.count()).group_by(CaseModel.queue, CaseModel.status).all()
            actionable = sum(int(n) for qn, st, n in queue_status if qn == "Repair" and self._norm_status(st) in self._ACTIONABLE_REPAIR)
            pending = sum(int(n) for qn, st, n in queue_status if self._norm_status(st) in self._PENDING_APPROVAL)
            return {
                "total": sum(by_status.values()),
                "by_status": by_status,
                "by_queue": grp(CaseModel.queue),
                "by_profile": grp(CaseModel.profile),
                "by_rail": grp(CaseModel.payment_rail),
                "actionable_repair": actionable,
                "pending_approvals_all": pending,
            }
        finally:
            db.close()

    def save_approval(self, approval_record: Any):
        """Persists an approval record to database and caches."""
        case_id = approval_record.case_id
        if case_id not in self._approvals_cache:
            self._approvals_cache[case_id] = []
        self._approvals_cache[case_id].append(approval_record)

        db: Session = SessionLocal()
        try:
            m = ApprovalRecordModel(
                approval_id=approval_record.approval_id,
                case_id=approval_record.case_id,
                recommendation_id=approval_record.recommendation_id,
                approver_id=approval_record.approver_id,
                approver_name=approval_record.approver_name,
                approver_role=approval_record.approver_role.value if hasattr(approval_record.approver_role, "value") else str(approval_record.approver_role),
                action=approval_record.action.value if hasattr(approval_record.action, "value") else str(approval_record.action),
                comments=approval_record.comments,
                approved_changes=_sanitize_for_json([c.model_dump() if hasattr(c, "model_dump") else (c.dict() if hasattr(c, "dict") else c) for c in (approval_record.approved_changes or [])]),
                step_number=approval_record.step_number,
                created_at=approval_record.created_at if isinstance(approval_record.created_at, datetime) else datetime.utcnow()
            )
            db.add(m)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[PeX DB Error] Failed to save approval record: {e}")
        finally:
            db.close()

    def save_case(self, case_dict: Dict[str, Any]):
        """Persists a case to database and updates in-memory cache."""
        case_id = case_dict["case_id"]
        ctx = self._bctx()
        if ctx:
            ctx.pending_cases[case_id] = case_dict
        else:
            self._cache_put(case_id, case_dict)

        db: Session = ctx.session if ctx else SessionLocal()
        try:
            existing = db.query(CaseModel).filter(CaseModel.case_id == case_id).first()
            if existing:
                existing.status = normalize_status(case_dict.get("status"))
                existing.queue = str(case_dict.get("queue"))
                existing.amount = float(case_dict.get("amount", 0.0))
                existing.currency = str(case_dict.get("currency", "USD"))
                existing.ai_confidence = case_dict.get("ai_confidence")
                existing.settled_at = case_dict.get("settled_at")
                existing.approval_history = _sanitize_for_json(case_dict.get("approval_history", []))
                existing.audit_timeline = _sanitize_for_json(case_dict.get("audit_timeline", []))
                existing.guided_questions = _sanitize_for_json(case_dict.get("guided_questions", []))
                existing.expedite_ping = case_dict.get("expedite_ping")
                existing.maker_id = case_dict.get("maker_id")
                existing.dispatch_status = case_dict.get("dispatch_status")
                existing.handed_off_at = case_dict.get("handed_off_at")
                existing.bank_ack_reference = case_dict.get("bank_ack_reference")
                existing.bank_clearing_system = case_dict.get("bank_clearing_system")
            else:
                new_c = CaseModel(
                    case_id=case_id,
                    payment_id=case_dict.get("payment_id", f"PMT-{case_id}"),
                    uetr=case_dict.get("uetr", f"UETR-{case_id}"),
                    payment_ref=case_dict.get("payment_ref", f"REF-{case_id}"),
                    profile=str(case_dict.get("profile")),
                    domain=str(case_dict.get("domain", "DATA_QUALITY")),
                    secondary_profiles=case_dict.get("secondary_profiles", []),
                    error_code=case_dict.get("error_code", "ERR_GEN"),
                    reason=case_dict.get("reason", "Exception"),
                    amount=float(case_dict.get("amount", 0.0)),
                    currency=str(case_dict.get("currency", "USD")),
                    payment_rail=str(case_dict.get("payment_rail", "SWIFT")),
                    debtor_party=_sanitize_for_json(case_dict.get("debtor_party", {})),
                    debtor_account=_sanitize_for_json(case_dict.get("debtor_account", {})),
                    creditor_party=_sanitize_for_json(case_dict.get("creditor_party", {})),
                    creditor_account=_sanitize_for_json(case_dict.get("creditor_account", {})),
                    queue=str(case_dict.get("queue", "Repair")),
                    status=normalize_status(case_dict.get("status", "PENDING_APPROVAL")),
                    severity=str(case_dict.get("severity", "MEDIUM")),
                    priority=str(case_dict.get("priority", "NORMAL")),
                    sla_due_at=str(case_dict.get("sla_due_at", datetime.utcnow().isoformat())),
                    dual_auth_required=bool(case_dict.get("dual_auth_required", False)),
                    ai_confidence=case_dict.get("ai_confidence"),
                    created_at=str(case_dict.get("created_at", datetime.utcnow().isoformat())),
                    settled_at=case_dict.get("settled_at"),
                    approval_history=_sanitize_for_json(case_dict.get("approval_history", [])),
                    audit_timeline=_sanitize_for_json(case_dict.get("audit_timeline", [])),
                    guided_questions=_sanitize_for_json(case_dict.get("guided_questions", [])),
                    expedite_ping=case_dict.get("expedite_ping"),
                    maker_id=case_dict.get("maker_id"),
                    dispatch_status=case_dict.get("dispatch_status"),
                    handed_off_at=case_dict.get("handed_off_at"),
                    bank_ack_reference=case_dict.get("bank_ack_reference"),
                    bank_clearing_system=case_dict.get("bank_clearing_system")
                )
                db.add(new_c)
            if not ctx:
                db.commit()
        except Exception as e:
            if ctx:
                raise
            db.rollback()
            print(f"[PeX DB Error] Failed to save case {case_id}: {e}")
        finally:
            if not ctx:
                db.close()

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        ctx = self._bctx()
        if ctx and case_id in ctx.pending_cases:
            return ctx.pending_cases[case_id]
        if case_id in self._case_cache:
            return self._case_cache[case_id]
        
        db: Session = SessionLocal()
        try:
            c = db.query(CaseModel).filter(CaseModel.case_id == case_id).first()
            if c:
                d = self._case_to_dict(c)
                self._cache_put(case_id, d)
                return d
            return None
        finally:
            db.close()

    def list_cases(
        self,
        queue: Optional[str] = None,
        status: Optional[str] = None,
        profile: Optional[str] = None,
        domain: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = list(self._case_cache.values())
        if domain and domain != "All":
            results = [c for c in results if c.get("domain") == domain]
        if queue and queue != "All":
            results = [c for c in results if c.get("queue") == queue]
        if status and status != "All":
            results = [c for c in results if c.get("status") == status]
        if profile and profile != "All":
            results = [c for c in results if c.get("profile") == profile]
        if search:
            s = search.lower()
            results = [
                c for c in results
                if s in c.get("case_id", "").lower()
                or s in c.get("profile", "").lower()
                or s in str(c.get("creditor_party", {})).lower()
                or s in str(c.get("payment_ref", "")).lower()
            ]
        return results

    def _append_audit_event(
        self,
        case_id: str,
        correlation_id: str,
        stage_name: str,
        actor_id: str,
        actor_role: str,
        action_name: str,
        details: str,
        control_tags: List[str]
    ):
        """Appends a new cryptographically chained event directly into the DB and updates chain head."""
        with self._audit_lock:
            ctx = self._bctx()
            db: Session = ctx.session if ctx else SessionLocal()
            try:
                if ctx:
                    idx, prev_hash = ctx.next_idx, ctx.prev_hash
                else:
                    latest_ev = db.query(AuditEventModel).order_by(desc(AuditEventModel.event_index)).first()
                    idx = (latest_ev.event_index + 1) if latest_ev else 1
                    prev_hash = latest_ev.current_hash if latest_ev else ("0" * 64)
                ts = datetime.utcnow().isoformat()

                current_hash = calculate_event_hash(
                    event_index=idx,
                    timestamp_iso=ts,
                    case_id=case_id,
                    stage_name=stage_name,
                    actor_id=actor_id,
                    action_name=action_name,
                    details=details,
                    prev_hash=prev_hash
                )
                ev = AuditEventModel(
                    event_index=idx,
                    case_id=case_id,
                    correlation_id=correlation_id,
                    stage_name=stage_name,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    action_name=action_name,
                    timestamp=ts,
                    details=details,
                    control_tags=control_tags or [],
                    prev_hash=prev_hash,
                    current_hash=current_hash
                )
                db.add(ev)
                if ctx:
                    ctx.next_idx, ctx.prev_hash = idx + 1, current_hash
                else:
                    db.commit()
                    self._latest_hash = current_hash
            except Exception as e:
                if ctx:
                    raise
                db.rollback()
                print(f"[PeX DB Error] Failed to append audit event for {case_id}: {e}")
            finally:
                if not ctx:
                    db.close()

    def _case_to_dict(self, c: CaseModel) -> Dict[str, Any]:
        return {
            "case_id": c.case_id,
            "payment_id": c.payment_id,
            "uetr": c.uetr,
            "payment_ref": c.payment_ref,
            "profile": c.profile,
            "domain": c.domain,
            "secondary_profiles": c.secondary_profiles or [],
            "error_code": c.error_code,
            "reason": c.reason,
            "amount": c.amount,
            "currency": c.currency,
            "payment_rail": c.payment_rail,
            "debtor_party": c.debtor_party or {},
            "debtor_account": c.debtor_account or {},
            "creditor_party": c.creditor_party or {},
            "creditor_account": c.creditor_account or {},
            "queue": c.queue,
            "status": c.status,
            "severity": c.severity,
            "priority": c.priority,
            "sla_due_at": c.sla_due_at,
            "dual_auth_required": c.dual_auth_required,
            "ai_confidence": c.ai_confidence,
            "created_at": c.created_at,
            "settled_at": c.settled_at,
            "approval_history": c.approval_history or [],
            "audit_timeline": c.audit_timeline or [],
            "guided_questions": c.guided_questions or [],
            "expedite_ping": c.expedite_ping,
            "maker_id": getattr(c, "maker_id", None),
            "dispatch_status": getattr(c, "dispatch_status", None),
            "handed_off_at": getattr(c, "handed_off_at", None),
            "bank_ack_reference": getattr(c, "bank_ack_reference", None),
            "bank_clearing_system": getattr(c, "bank_clearing_system", None)
        }

    def _rec_to_schema(self, r: RecommendationModel):
        from app.schemas.recommendation import (
            DecisionRecommendation, ActionType, RiskEvaluation, ProposedFieldChange,
            CorroboratingEvidenceRef, GuidedQuestionItem, StepAssessmentItem,
            HypothesisRankingItem, AnomalyGuardrailItem, ConsequenceSimulation
        )
        risk_data = dict(r.risk_evaluation) if r.risk_evaluation else {}
        if "risk_level" not in risk_data:
            risk_data["risk_level"] = "LOW"
        if "risk_factors" not in risk_data:
            risk_data["risk_factors"] = ["LOW_EXPOSURE_UNDER_25K", "CHECKSUM_VERIFIED"]
        if "risk_score" not in risk_data:
            risk_data["risk_score"] = 0.05
        if "dual_auth_required" not in risk_data:
            risk_data["dual_auth_required"] = False

        act_raw = r.action_type
        if isinstance(act_raw, str) and act_raw.startswith("ActionType."):
            act_raw = act_raw.split(".", 1)[1]
        try:
            act_val = ActionType(act_raw)
        except Exception:
            act_val = ActionType.REPAIR_DATA

        return DecisionRecommendation(
            recommendation_id=r.recommendation_id,
            case_id=r.case_id,
            action_type=act_val,
            confidence_score=r.confidence_score,
            rationale=r.rationale,
            proposed_changes=[ProposedFieldChange(**c) for c in (r.proposed_changes or [])],
            corroborating_evidence=[CorroboratingEvidenceRef(**e) for e in (r.corroborating_evidence or [])],
            risk_evaluation=RiskEvaluation(**risk_data),
            guided_questions=[GuidedQuestionItem(**q) for q in (r.guided_questions or [])],
            step_by_step_assessment=[StepAssessmentItem(**s) for s in (r.step_by_step_assessment or [])],
            hypothesis_ranking=[HypothesisRankingItem(**h) for h in (r.hypothesis_ranking or [])],
            anomaly_guardrails=[AnomalyGuardrailItem(**a) for a in (r.anomaly_guardrails or [])],
            consequence_simulation=ConsequenceSimulation(**r.consequence_simulation) if r.consequence_simulation else None,
            applied_policies=r.applied_policies or [],
            ambiguity_detected=getattr(r, "ambiguity_detected", False) or False,
            ambiguity_message=getattr(r, "ambiguity_message", None),
            model_identifier=r.model_identifier,
            prompt_tokens=r.prompt_tokens,
            completion_tokens=r.completion_tokens,
            generated_at=r.generated_at
        )

    def get_recommendation(self, case_id: str) -> Optional[Any]:
        """Returns the recommendation for a given case_id from cache or DB."""
        ctx = self._bctx()
        if ctx and case_id in ctx.pending_recs:
            return ctx.pending_recs[case_id]
        r = self._recommendations_cache.get(case_id)
        if r is not None:
            return r
        db: Session = SessionLocal()
        try:
            m = db.query(RecommendationModel).filter(RecommendationModel.case_id == case_id).first()
            if m:
                r = self._rec_to_schema(m)
                if len(self._recommendations_cache) < self._case_cache_max:
                    self._recommendations_cache[case_id] = r
                return r
            return None
        finally:
            db.close()

    def save_recommendation(self, rec: Any):
        """Persists or updates a DecisionRecommendation in database and cache."""
        case_id = rec.case_id if hasattr(rec, "case_id") else rec.get("case_id")
        ctx = self._bctx()
        if ctx:
            ctx.pending_recs[case_id] = rec
        elif len(self._recommendations_cache) < self._case_cache_max or case_id in self._recommendations_cache:
            self._recommendations_cache[case_id] = rec

        db: Session = ctx.session if ctx else SessionLocal()
        try:
            rec_id = rec.recommendation_id if hasattr(rec, "recommendation_id") else rec.get("recommendation_id")
            existing = db.query(RecommendationModel).filter(RecommendationModel.case_id == case_id).first()
            
            raw_dict = rec.model_dump() if hasattr(rec, "model_dump") else (rec.dict() if hasattr(rec, "dict") else dict(rec))
            act_str = raw_dict.get("action_type", "REPAIR_DATA")
            if hasattr(act_str, "value"):
                act_str = act_str.value
            elif isinstance(act_str, str) and act_str.startswith("ActionType."):
                act_str = act_str.split(".", 1)[1]
            
            if existing:
                existing.action_type = str(act_str)
                existing.confidence_score = float(raw_dict.get("confidence_score", 0.9))
                existing.rationale = str(raw_dict.get("rationale", ""))
                existing.proposed_changes = _sanitize_for_json(raw_dict.get("proposed_changes", []))
                existing.corroborating_evidence = _sanitize_for_json(raw_dict.get("corroborating_evidence", []))
                existing.risk_evaluation = _sanitize_for_json(raw_dict.get("risk_evaluation", {}))
                existing.guided_questions = _sanitize_for_json(raw_dict.get("guided_questions", []))
                existing.step_by_step_assessment = _sanitize_for_json(raw_dict.get("step_by_step_assessment", []))
                existing.hypothesis_ranking = _sanitize_for_json(raw_dict.get("hypothesis_ranking", []))
                existing.anomaly_guardrails = _sanitize_for_json(raw_dict.get("anomaly_guardrails", []))
                existing.consequence_simulation = _sanitize_for_json(raw_dict.get("consequence_simulation", {}))
                existing.applied_policies = _sanitize_for_json(raw_dict.get("applied_policies", []))
                existing.ambiguity_detected = bool(raw_dict.get("ambiguity_detected", False))
                existing.ambiguity_message = raw_dict.get("ambiguity_message")
            else:
                new_rec = RecommendationModel(
                    recommendation_id=rec_id or f"REC-{case_id}",
                    case_id=case_id,
                    action_type=str(act_str),
                    confidence_score=float(raw_dict.get("confidence_score", 0.9)),
                    rationale=str(raw_dict.get("rationale", "")),
                    proposed_changes=_sanitize_for_json(raw_dict.get("proposed_changes", [])),
                    corroborating_evidence=_sanitize_for_json(raw_dict.get("corroborating_evidence", [])),
                    risk_evaluation=_sanitize_for_json(raw_dict.get("risk_evaluation", {})),
                    guided_questions=_sanitize_for_json(raw_dict.get("guided_questions", [])),
                    step_by_step_assessment=_sanitize_for_json(raw_dict.get("step_by_step_assessment", [])),
                    hypothesis_ranking=_sanitize_for_json(raw_dict.get("hypothesis_ranking", [])),
                    anomaly_guardrails=_sanitize_for_json(raw_dict.get("anomaly_guardrails", [])),
                    consequence_simulation=_sanitize_for_json(raw_dict.get("consequence_simulation", {})),
                    applied_policies=_sanitize_for_json(raw_dict.get("applied_policies", [])),
                    ambiguity_detected=bool(raw_dict.get("ambiguity_detected", False)),
                    ambiguity_message=raw_dict.get("ambiguity_message"),
                    model_identifier=raw_dict.get("model_identifier", "mock-governed-reasoner-v1"),
                    prompt_tokens=int(raw_dict.get("prompt_tokens", 0)),
                    completion_tokens=int(raw_dict.get("completion_tokens", 0)),
                    generated_at=raw_dict.get("generated_at") or datetime.utcnow()
                )
                db.add(new_rec)
            if not ctx:
                db.commit()
        except Exception as e:
            if ctx:
                raise
            db.rollback()
            print(f"[PeX DB Error] Failed to save recommendation for {case_id}: {e}")
        finally:
            if not ctx:
                db.close()

    def _approval_to_schema(self, a: ApprovalRecordModel):
        from app.schemas.approval import ApprovalRecord, ApprovalAction, UserRole
        from app.schemas.recommendation import ProposedFieldChange
        return ApprovalRecord(
            approval_id=a.approval_id,
            case_id=a.case_id,
            recommendation_id=a.recommendation_id,
            approver_id=a.approver_id,
            approver_name=a.approver_name,
            approver_role=UserRole(a.approver_role),
            action=ApprovalAction(a.action),
            comments=a.comments,
            approved_changes=[ProposedFieldChange(**c) for c in (a.approved_changes or [])],
            step_number=a.step_number,
            created_at=a.created_at
        )

    def _action_to_schema(self, act: GovernedActionModel):
        from app.schemas.action import GovernedActionContract, ActionStatus
        from app.schemas.recommendation import ActionType
        try:
            act_type = ActionType(act.action_type)
        except (ValueError, KeyError):
            act_type = ActionType.REPAIR_AND_RELEASE
        return GovernedActionContract(
            action_id=act.action_id,
            case_id=act.case_id,
            approval_ids=act.approval_ids or [],
            action_type=act_type,
            target_system=act.target_system,
            idempotency_key=act.idempotency_key,
            dispatch_payload=act.dispatch_payload or {},
            status=ActionStatus(act.status),
            dispatched_at=act.dispatched_at,
            settled_at=act.settled_at
        )

    def _rule_to_dict(self, r: PolicyRuleModel) -> Dict[str, Any]:
        return {
            "rule_id": r.rule_id,
            "name": r.name,
            "natural_language_prompt": r.natural_language_prompt,
            "category": r.category,
            "domain": r.domain,
            "conditions": r.conditions or {},
            "actions": r.actions or {},
            "status": r.status,
            "version": r.version,
            "impact_summary": r.impact_summary,
            "maker_id": r.maker_id,
            "maker_name": r.maker_name,
            "maker_notes": r.maker_notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "checker_id": r.checker_id,
            "checker_name": r.checker_name,
            "checker_comments": r.checker_comments,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        }

    def _icd_to_dict(self, icd: ICDConfigurationModel) -> Dict[str, Any]:
        return {
            "icd_id": icd.icd_id,
            "name": icd.name,
            "institution_name": icd.institution_name,
            "bic": icd.bic,
            "rail": icd.rail,
            "adapter_type": icd.adapter_type,
            "endpoint_url": icd.endpoint_url,
            "latency_ms": icd.latency_ms,
            "status": icd.status,
            "config_payload": icd.config_payload or {},
            "maker_id": icd.maker_id,
            "maker_name": icd.maker_name,
            "maker_notes": icd.maker_notes,
            "created_at": icd.created_at.isoformat() if icd.created_at else None,
            "checker_id": icd.checker_id,
            "checker_name": icd.checker_name,
            "checker_comments": icd.checker_comments,
            "approved_at": icd.approved_at.isoformat() if icd.approved_at else None,
        }

    def get_policy_rules(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all policy rules, optionally filtered by status."""
        rules = list(self._rules_cache.values())
        if status:
            return [r for r in rules if r.get("status") == status]
        return rules

    def get_policy_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Returns a single policy rule by ID."""
        return self._rules_cache.get(rule_id)

    def save_policy_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates or updates a policy rule in persistent DB and syncs cache."""
        db: Session = SessionLocal()
        try:
            rule_id = rule_data.get("rule_id")
            existing = db.query(PolicyRuleModel).filter(PolicyRuleModel.rule_id == rule_id).first() if rule_id else None

            if existing:
                for k, v in rule_data.items():
                    if hasattr(existing, k) and k not in ["created_at"]:
                        setattr(existing, k, v)
                db.commit()
                db.refresh(existing)
                result = self._rule_to_dict(existing)
            else:
                new_rule = PolicyRuleModel(
                    rule_id=rule_data.get("rule_id"),
                    name=rule_data.get("name"),
                    natural_language_prompt=rule_data.get("natural_language_prompt"),
                    category=rule_data.get("category", "APPROVAL_GATING"),
                    domain=rule_data.get("domain", "ALL"),
                    conditions=rule_data.get("conditions", {}),
                    actions=rule_data.get("actions", {}),
                    status=rule_data.get("status", "PENDING_APPROVAL"),
                    version=rule_data.get("version", "1.0"),
                    impact_summary=rule_data.get("impact_summary"),
                    maker_id=rule_data.get("maker_id"),
                    maker_name=rule_data.get("maker_name"),
                    maker_notes=rule_data.get("maker_notes"),
                    checker_id=rule_data.get("checker_id"),
                    checker_name=rule_data.get("checker_name"),
                    checker_comments=rule_data.get("checker_comments"),
                    approved_at=rule_data.get("approved_at"),
                    created_at=datetime.utcnow()
                )
                db.add(new_rule)
                db.commit()
                db.refresh(new_rule)
                result = self._rule_to_dict(new_rule)

            self._rules_cache[result["rule_id"]] = result
            return result
        finally:
            db.close()

    def approve_policy_rule(
        self,
        rule_id: str,
        checker_id: str,
        checker_name: str,
        comments: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Checker approves and activates a policy rule with full audit trail."""
        db: Session = SessionLocal()
        try:
            rule = db.query(PolicyRuleModel).filter(PolicyRuleModel.rule_id == rule_id).first()
            if not rule:
                return None
            rule.status = "ACTIVE"
            rule.checker_id = checker_id
            rule.checker_name = checker_name
            rule.checker_comments = comments or "Approved by Checker"
            rule.approved_at = datetime.utcnow()
            db.commit()
            db.refresh(rule)
            result = self._rule_to_dict(rule)
            self._rules_cache[result["rule_id"]] = result
            return result
        finally:
            db.close()

    def reject_policy_rule(
        self,
        rule_id: str,
        checker_id: str,
        checker_name: str,
        comments: str
    ) -> Optional[Dict[str, Any]]:
        """Checker rejects or returns a policy rule with mandatory comments."""
        db: Session = SessionLocal()
        try:
            rule = db.query(PolicyRuleModel).filter(PolicyRuleModel.rule_id == rule_id).first()
            if not rule:
                return None
            rule.status = "REJECTED"
            rule.checker_id = checker_id
            rule.checker_name = checker_name
            rule.checker_comments = comments
            rule.approved_at = datetime.utcnow()
            db.commit()
            db.refresh(rule)
            result = self._rule_to_dict(rule)
            self._rules_cache[result["rule_id"]] = result
            return result
        finally:
            db.close()

    def get_icd_configs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all external ICD bank configurations, optionally filtered by status."""
        configs = list(self._icd_cache.values())
        if status:
            return [c for c in configs if c.get("status") == status]
        return configs

    def get_icd_config(self, icd_id: str) -> Optional[Dict[str, Any]]:
        """Returns a single ICD configuration by ID."""
        return self._icd_cache.get(icd_id)

    def save_icd_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates or updates an ICD configuration node in persistent DB."""
        db: Session = SessionLocal()
        try:
            icd_id = config_data.get("icd_id")
            existing = db.query(ICDConfigurationModel).filter(ICDConfigurationModel.icd_id == icd_id).first() if icd_id else None

            if existing:
                for k, v in config_data.items():
                    if hasattr(existing, k) and k not in ["created_at"]:
                        setattr(existing, k, v)
                db.commit()
                db.refresh(existing)
                result = self._icd_to_dict(existing)
            else:
                new_icd = ICDConfigurationModel(
                    icd_id=config_data.get("icd_id"),
                    name=config_data.get("name"),
                    institution_name=config_data.get("institution_name"),
                    bic=config_data.get("bic"),
                    rail=config_data.get("rail", "SWIFT_CBPR+"),
                    adapter_type=config_data.get("adapter_type", "DIRECTORY_LOOKUP"),
                    endpoint_url=config_data.get("endpoint_url"),
                    latency_ms=config_data.get("latency_ms", 12),
                    status=config_data.get("status", "PENDING_APPROVAL"),
                    config_payload=config_data.get("config_payload", {}),
                    maker_id=config_data.get("maker_id"),
                    maker_name=config_data.get("maker_name"),
                    maker_notes=config_data.get("maker_notes"),
                    checker_id=config_data.get("checker_id"),
                    checker_name=config_data.get("checker_name"),
                    checker_comments=config_data.get("checker_comments"),
                    approved_at=config_data.get("approved_at"),
                    created_at=datetime.utcnow()
                )
                db.add(new_icd)
                db.commit()
                db.refresh(new_icd)
                result = self._icd_to_dict(new_icd)

            self._icd_cache[result["icd_id"]] = result
            return result
        finally:
            db.close()

    def approve_icd_config(
        self,
        icd_id: str,
        checker_id: str,
        checker_name: str,
        comments: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Checker approves and activates an ICD bank node integration."""
        db: Session = SessionLocal()
        try:
            icd = db.query(ICDConfigurationModel).filter(ICDConfigurationModel.icd_id == icd_id).first()
            if not icd:
                return None
            icd.status = "ACTIVE"
            icd.checker_id = checker_id
            icd.checker_name = checker_name
            icd.checker_comments = comments or "Approved by Checker"
            icd.approved_at = datetime.utcnow()
            db.commit()
            db.refresh(icd)
            result = self._icd_to_dict(icd)
            self._icd_cache[result["icd_id"]] = result
            return result
        finally:
            db.close()

    def _receipt_to_schema(self, rcpt: DeliveryReceiptModel):
        from app.schemas.action import DeliveryReceipt
        return DeliveryReceipt(
            receipt_id=rcpt.receipt_id,
            action_id=rcpt.action_id,
            case_id=rcpt.case_id,
            bank_ack_reference=rcpt.bank_ack_reference,
            status=rcpt.status,
            timestamp=rcpt.timestamp,
            details=rcpt.details or {}
        )
