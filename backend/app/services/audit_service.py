"""Continuous Audit Service: Cryptographic SHA-256 Provenance Chaining for all 20 Lifecycle Steps."""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.schemas.audit import AuditEvent, ProvenanceChain, HashVerificationResult
from app.core.hashing import calculate_event_hash, verify_audit_chain, GENESIS_HASH
from app.services.data_loader import repo

class AuditService:
    def log_event(
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
    ) -> AuditEvent:
        return repo.log_audit_event(
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
            creditor_account=creditor_account
        )

    def get_case_provenance(self, case_id: str) -> ProvenanceChain:
        case_events = [e for e in repo.audit_log if e.case_id == case_id]
        head_hash = case_events[-1].current_hash if case_events else repo.latest_chain_hash
        return ProvenanceChain(
            case_id=case_id,
            chain_head_hash=head_hash,
            total_events=len(case_events),
            is_valid=True,
            events=case_events
        )

    def get_all_events(self, limit: int = 100) -> List[AuditEvent]:
        return list(reversed(repo.audit_log[-limit:]))

    def verify_chain(self) -> HashVerificationResult:
        from app.db.session import SessionLocal
        from app.db.models import AuditEventModel
        db = SessionLocal()
        try:
            db_events = db.query(AuditEventModel).order_by(AuditEventModel.event_index).all()
            raw_events = [{
                "event_index": ev.event_index,
                "timestamp": ev.timestamp,
                "case_id": ev.case_id,
                "stage_name": ev.stage_name,
                "actor_id": ev.actor_id,
                "action_name": ev.action_name,
                "details": ev.details,
                "amount": ev.amount,
                "currency": ev.currency,
                "debtor_account": ev.debtor_account,
                "creditor_account": ev.creditor_account,
                "prev_hash": ev.prev_hash,
                "current_hash": ev.current_hash
            } for ev in db_events]
            is_intact = verify_audit_chain(raw_events)
            latest_ev = db_events[-1] if db_events else None
            head_hash = latest_ev.current_hash if latest_ev else ("0" * 64)
            return HashVerificationResult(
                chain_head=head_hash,
                total_events_checked=len(db_events),
                is_intact=is_intact,
                verified_at=datetime.utcnow()
            )
        finally:
            db.close()

audit_service = AuditService()
