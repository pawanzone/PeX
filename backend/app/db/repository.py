"""Persistent Relational Database Repository for PeX Enterprise Platform."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

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
            db_cases = db.query(CaseModel).all()
            self._case_cache.clear()
            for c in db_cases:
                self._case_cache[c.case_id] = self._case_to_dict(c)

            # Sync Recommendations
            db_recs = db.query(RecommendationModel).all()
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
                except Exception:
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
        control_tags: Optional[List[str]] = None
    ):
        """Appends a new cryptographically chained audit event directly to DB and updates latest hash."""
        from app.schemas.audit import AuditEvent
        from app.core.hashing import calculate_event_hash
        db: Session = SessionLocal()
        try:
            idx = db.query(AuditEventModel).count() + 1
            latest_ev = db.query(AuditEventModel).order_by(desc(AuditEventModel.event_index)).first()
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
                prev_hash=prev_hash
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
                prev_hash=prev_hash,
                current_hash=curr_hash
            )
            db.add(db_ev)
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
                prev_hash=prev_hash,
                current_hash=curr_hash
            )
        except Exception as e:
            db.rollback()
            print(f"[PeX DB Error] Failed to log audit event: {e}")
            raise e
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
                approved_changes=_sanitize_for_json([c.dict() if hasattr(c, "dict") else c for c in (approval_record.approved_changes or [])]),
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
        self._case_cache[case_id] = case_dict

        db: Session = SessionLocal()
        try:
            existing = db.query(CaseModel).filter(CaseModel.case_id == case_id).first()
            if existing:
                existing.status = str(case_dict.get("status"))
                existing.queue = str(case_dict.get("queue"))
                existing.amount = float(case_dict.get("amount", 0.0))
                existing.currency = str(case_dict.get("currency", "USD"))
                existing.ai_confidence = case_dict.get("ai_confidence")
                existing.settled_at = case_dict.get("settled_at")
                existing.approval_history = _sanitize_for_json(case_dict.get("approval_history", []))
                existing.audit_timeline = _sanitize_for_json(case_dict.get("audit_timeline", []))
                existing.guided_questions = _sanitize_for_json(case_dict.get("guided_questions", []))
                existing.expedite_ping = case_dict.get("expedite_ping")
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
                    status=str(case_dict.get("status", "PENDING_APPROVAL")),
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
                    expedite_ping=case_dict.get("expedite_ping")
                )
                db.add(new_c)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[PeX DB Error] Failed to save case {case_id}: {e}")
        finally:
            db.close()

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        if case_id in self._case_cache:
            return self._case_cache[case_id]
        
        db: Session = SessionLocal()
        try:
            c = db.query(CaseModel).filter(CaseModel.case_id == case_id).first()
            if c:
                d = self._case_to_dict(c)
                self._case_cache[case_id] = d
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
        db: Session = SessionLocal()
        try:
            count = db.query(AuditEventModel).count()
            idx = count + 1
            ts = datetime.utcnow().isoformat()
            current_hash = calculate_event_hash(
                event_index=idx,
                timestamp_iso=ts,
                case_id=case_id,
                stage_name=stage_name,
                actor_id=actor_id,
                action_name=action_name,
                details=details,
                prev_hash=self._latest_hash
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
                prev_hash=self._latest_hash,
                current_hash=current_hash
            )
            db.add(ev)
            db.commit()
            self._latest_hash = current_hash
        except Exception as e:
            db.rollback()
            print(f"[PeX DB Error] Failed to append audit event for {case_id}: {e}")
        finally:
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
            "expedite_ping": c.expedite_ping
        }

    def _rec_to_schema(self, r: RecommendationModel):
        from app.schemas.recommendation import (
            DecisionRecommendation, ActionType, RiskEvaluation, ProposedFieldChange,
            CorroboratingEvidenceRef, GuidedQuestionItem, StepAssessmentItem,
            HypothesisRankingItem, AnomalyGuardrailItem, ConsequenceSimulation
        )
        return DecisionRecommendation(
            recommendation_id=r.recommendation_id,
            case_id=r.case_id,
            action_type=ActionType(r.action_type),
            confidence_score=r.confidence_score,
            rationale=r.rationale,
            proposed_changes=[ProposedFieldChange(**c) for c in (r.proposed_changes or [])],
            corroborating_evidence=[CorroboratingEvidenceRef(**e) for e in (r.corroborating_evidence or [])],
            risk_evaluation=RiskEvaluation(**r.risk_evaluation),
            guided_questions=[GuidedQuestionItem(**q) for q in (r.guided_questions or [])],
            step_by_step_assessment=[StepAssessmentItem(**s) for s in (r.step_by_step_assessment or [])],
            hypothesis_ranking=[HypothesisRankingItem(**h) for h in (r.hypothesis_ranking or [])],
            anomaly_guardrails=[AnomalyGuardrailItem(**a) for a in (r.anomaly_guardrails or [])],
            consequence_simulation=ConsequenceSimulation(**r.consequence_simulation) if r.consequence_simulation else None,
            applied_policies=r.applied_policies or [],
            model_identifier=r.model_identifier,
            prompt_tokens=r.prompt_tokens,
            completion_tokens=r.completion_tokens,
            generated_at=r.generated_at
        )

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
        return GovernedActionContract(
            action_id=act.action_id,
            case_id=act.case_id,
            approval_ids=act.approval_ids or [],
            action_type=ActionType(act.action_type),
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
