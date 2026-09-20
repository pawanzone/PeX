"""Database Auto-Creation & Seeding for PeX Enterprise Platform."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.models import (
    UserModel,
    RolePermissionModel,
    CaseModel,
    AuditEventModel,
    TokenVaultModel,
    RecommendationModel,
    ApprovalRecordModel,
    GovernedActionModel,
    DeliveryReceiptModel,
    RawBankEventModel,
)
from app.core.security import DEMO_PERSONAS
from app.core.tokenization import token_vault

def create_tables():
    """Idempotently creates all relational tables across the active engine."""
    Base.metadata.create_all(bind=engine)

def seed_users(db: Session):
    """Populates initial user personas and RBAC roles."""
    if db.query(UserModel).count() > 0:
        return

    for p in DEMO_PERSONAS.values():
        u = UserModel(
            user_id=p.user_id,
            name=p.name,
            email=p.email,
            role=p.role.value if hasattr(p.role, "value") else str(p.role),
            title=p.title,
            department=p.department,
            avatar_initials=p.avatar_initials,
            badge_color=p.badge_color,
            max_approval_amount=p.max_approval_amount,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(u)

    # Initial RBAC Permission Scopes
    initial_permissions = [
        ("OPERATOR", "exceptions:read", "Read all exception queues"),
        ("OPERATOR", "exceptions:repair", "Execute AI reasoner and submit repair proposals"),
        ("OPERATIONS_APPROVER", "exceptions:approve_l1", "Level 1 approval up to $250k"),
        ("OPERATIONS_APPROVER", "exceptions:rework", "Return case to Maker for rework"),
        ("COMPLIANCE_APPROVER", "compliance:clear_false_positive", "Clear OFAC/EU sanctions false positive homonyms"),
        ("COMPLIANCE_APPROVER", "compliance:grant_kyc_waiver", "Grant 30-day provisional KYC processing waivers"),
        ("RISK_APPROVER", "exceptions:dual_auth", "Tier 2 high-value dual authorization ($250k+)"),
        ("ADMIN", "admin:all", "Full administrative control and policy tuning"),
    ]
    for role, scope, desc in initial_permissions:
        rp = RolePermissionModel(role=role, permission_scope=scope, description=desc)
        db.add(rp)

    db.commit()

def seed_initial_data(db: Session, force_reseed: bool = False):
    """Populates 82 benchmark cases across all 41 exception profiles if table is empty."""
    case_count = db.query(CaseModel).count()
    if case_count > 0 and not force_reseed:
        print(f"[PeX DB] Persistent database contains {case_count} cases. Skipping seed.")
        return

    # Import data_loader to generate benchmark fixtures
    from app.services.data_loader import (
        all_profiles,
        counterparties,
        build_rich_guided_recommendation,
        get_domain_for_profile,
        LifecycleStage,
        ExceptionDomain,
        ExceptionSeverity,
        ExceptionPriority,
    )
    from app.core.hashing import calculate_event_hash
    from datetime import timedelta

    print("[PeX DB] Fresh database detected. Seeding 82 curated benchmark cases and audit hash chains...")

    seen_tokens = set()
    latest_hash = "0" * 64
    audit_index = 1
    case_counter = 1

    for repeat in range(2):
        for p_idx, profile in enumerate(all_profiles):
            i = case_counter
            cp_name, cp_country, cp_ccy, cp_bic = counterparties[i % len(counterparties)]
            domain = get_domain_for_profile(profile)
            
            prefix = profile.value[:3]
            case_id = f"PEX-{prefix}-{i:04d}"
            uetr = f"UETR-2026-{prefix}-{i:04d}-A8"
            payment_ref = f"PAY-2026-{i:06d}"

            if i % 3 == 0:
                amount = 45000.0 + (i * 1250.50)
            elif i % 3 == 1:
                amount = 325000.0 + (i * 4500.0)
            else:
                amount = 1450000.0 + (i * 9800.0)

            if i % 7 == 0:
                status = LifecycleStage.INGESTED
            elif i % 7 == 1:
                status = LifecycleStage.RECOMMENDED
            elif i % 7 == 2:
                status = LifecycleStage.PENDING_APPROVAL
            elif i % 7 == 3:
                status = LifecycleStage.AWAITING_SECOND_APPROVAL if amount >= 250000.0 else LifecycleStage.PENDING_APPROVAL
            elif i % 7 == 4:
                status = LifecycleStage.RETURNED_FOR_REWORK
            elif i % 7 == 5:
                status = LifecycleStage.APPROVED
            else:
                status = LifecycleStage.SETTLED

            if domain == ExceptionDomain.COMPLIANCE:
                queue = "Compliance"
            elif domain == ExceptionDomain.CLIENT_TREASURY:
                queue = "Treasury"
            elif domain == ExceptionDomain.SETTLEMENT_RETURNS:
                queue = "Investigation"
            elif domain == ExceptionDomain.PROCESSING:
                queue = "Investigation" if profile.value == "DUPLICATE_PAYMENT" else "Repair"
            else:
                queue = "Repair"

            # Tokenize PII
            debtor_tok = token_vault.tokenize(f"Ordering Customer {i}", "PARTY")
            creditor_tok = token_vault.tokenize(cp_name, "PARTY")
            debtor_acc_tok = token_vault.tokenize(f"US11APEX998877{i:04d}", "ACC")
            creditor_iban_tok = token_vault.tokenize(f"{cp_country}82WEST1234569876{i:04d}", "IBAN")

            # Persist unique token mappings into DB
            for raw_val, tok_val, tok_type in [
                (f"Ordering Customer {i}", debtor_tok, "PARTY"),
                (cp_name, creditor_tok, "PARTY"),
                (f"US11APEX998877{i:04d}", debtor_acc_tok, "ACC"),
                (f"{cp_country}82WEST1234569876{i:04d}", creditor_iban_tok, "IBAN"),
            ]:
                if tok_val and tok_val not in seen_tokens:
                    seen_tokens.add(tok_val)
                    h = tok_val.split("-")[-1]
                    db.add(TokenVaultModel(raw_hash=h, raw_value=raw_val, token_value=tok_val, token_type=tok_type))

            # Realistic Timestamps
            t_base = datetime.utcnow() - timedelta(minutes=max(5, (100 - i * 2) % 360))
            sla_due = t_base + timedelta(minutes=180)

            # Audit event 1: Ingestion
            ts_ingest = t_base.isoformat()
            ingest_curr_hash = calculate_event_hash(
                event_index=audit_index,
                timestamp_iso=ts_ingest,
                case_id=case_id,
                stage_name="INGESTION",
                actor_id="SYS-INGEST",
                action_name="INGEST_EXCEPTION",
                details=f"Payment exception {case_id} ({profile.value}) ingested across {domain.value} domain.",
                prev_hash=latest_hash
            )
            ev1 = AuditEventModel(
                event_index=audit_index,
                case_id=case_id,
                correlation_id=uetr,
                stage_name="INGESTION",
                actor_id="SYS-INGEST",
                actor_role="SYSTEM",
                action_name="INGEST_EXCEPTION",
                timestamp=ts_ingest,
                details=f"Payment exception {case_id} ({profile.value}) ingested across {domain.value} domain.",
                control_tags=["Schema valid", "Token vault isolated", f"BIAN {domain.value}"],
                prev_hash=latest_hash,
                current_hash=ingest_curr_hash
            )
            db.add(ev1)
            latest_hash = ingest_curr_hash
            audit_index += 1

            audit_timeline = [{
                "step_index": 1,
                "timestamp": ts_ingest,
                "actor_name": "PeX Ingestion Gateway",
                "actor_role": "SYSTEM",
                "badge_color": "slate",
                "action_title": "Exception Ingested & Canonicalized",
                "icon": "📥",
                "summary": f"Payment wire received via SWIFT / CBPR+. PII tokenized into isolated vault reference {debtor_tok}."
            }]

            rec = None
            ai_conf = None
            if status != LifecycleStage.INGESTED:
                t_ai = t_base + timedelta(minutes=10)
                ts_ai = t_ai.isoformat()
                ai_curr_hash = calculate_event_hash(
                    event_index=audit_index,
                    timestamp_iso=ts_ai,
                    case_id=case_id,
                    stage_name="ANALYST_REPAIR",
                    actor_id="OP-9012",
                    action_name="RUN_AI_REPAIR",
                    details=f"Analyst Priya Nair triggered AI reasoner for {profile.value}.",
                    prev_hash=latest_hash
                )
                ev2 = AuditEventModel(
                    event_index=audit_index,
                    case_id=case_id,
                    correlation_id=uetr,
                    stage_name="ANALYST_REPAIR",
                    actor_id="OP-9012",
                    actor_role="OPERATOR",
                    action_name="RUN_AI_REPAIR",
                    timestamp=ts_ai,
                    details=f"Analyst Priya Nair triggered AI reasoner for {profile.value}.",
                    control_tags=["Evidence grounded", "SOP aligned", "Maker review complete"],
                    prev_hash=latest_hash,
                    current_hash=ai_curr_hash
                )
                db.add(ev2)
                latest_hash = ai_curr_hash
                audit_index += 1

                audit_timeline.append({
                    "step_index": 2,
                    "timestamp": ts_ai,
                    "actor_name": "Priya Nair",
                    "actor_role": "OPERATOR (MAKER)",
                    "badge_color": "blue",
                    "action_title": "AI Reasoner Evaluated",
                    "icon": "⚡",
                    "summary": f"Analyst ran AI Reasoner. Grounded evidence under BIAN {domain.value} playbook."
                })

                rec = build_rich_guided_recommendation(
                    case_id=case_id,
                    profile=profile,
                    amount=amount,
                    creditor_name=cp_name,
                    creditor_country=cp_country,
                    case_idx=i
                )
                ai_conf = rec.confidence_score

                # Add recommendation model to DB
                rec_model = RecommendationModel(
                    recommendation_id=rec.recommendation_id,
                    case_id=case_id,
                    action_type=rec.action_type.value,
                    confidence_score=rec.confidence_score,
                    rationale=rec.rationale,
                    proposed_changes=[c.dict() for c in rec.proposed_changes],
                    corroborating_evidence=[e.dict() for e in rec.corroborating_evidence],
                    risk_evaluation=rec.risk_evaluation.dict(),
                    guided_questions=[q.dict() for q in rec.guided_questions],
                    step_by_step_assessment=[s.dict() for s in rec.step_by_step_assessment],
                    hypothesis_ranking=[h.dict() for h in rec.hypothesis_ranking],
                    anomaly_guardrails=[a.dict() for a in rec.anomaly_guardrails],
                    consequence_simulation=rec.consequence_simulation.dict() if rec.consequence_simulation else None,
                    applied_policies=rec.applied_policies,
                    model_identifier=rec.model_identifier,
                    prompt_tokens=rec.prompt_tokens,
                    completion_tokens=rec.completion_tokens,
                    generated_at=rec.generated_at
                )
                db.add(rec_model)

            approval_hist = []
            if status in [LifecycleStage.AWAITING_SECOND_APPROVAL, LifecycleStage.APPROVED, LifecycleStage.SETTLED]:
                t_l1 = t_base + timedelta(minutes=35)
                rec1 = ApprovalRecordModel(
                    approval_id=f"APR-{i:04d}-S1",
                    case_id=case_id,
                    recommendation_id=f"REC-{case_id}",
                    approver_id="APR-3191" if queue != "Compliance" else "CMP-4420",
                    approver_name="Daniel Osei" if queue != "Compliance" else "Marisol Vega",
                    approver_role="OPERATIONS_APPROVER" if queue != "Compliance" else "COMPLIANCE_APPROVER",
                    action="APPROVE",
                    comments=f"Level 1 verification approved for {profile.value}.",
                    approved_changes=[],
                    step_number=1,
                    created_at=t_l1
                )
                db.add(rec1)
                approval_hist.append({
                    "approval_id": rec1.approval_id,
                    "case_id": case_id,
                    "recommendation_id": rec1.recommendation_id,
                    "approver_id": rec1.approver_id,
                    "approver_name": rec1.approver_name,
                    "approver_role": rec1.approver_role,
                    "action": rec1.action,
                    "comments": rec1.comments,
                    "approved_changes": [],
                    "step_number": 1,
                    "created_at": t_l1.isoformat()
                })

            if status in [LifecycleStage.APPROVED, LifecycleStage.SETTLED] and amount >= 250000.0:
                t_l2 = t_base + timedelta(minutes=45)
                rec2 = ApprovalRecordModel(
                    approval_id=f"APR-{i:04d}-S2",
                    case_id=case_id,
                    recommendation_id=f"REC-{case_id}",
                    approver_id="RSK-7714",
                    approver_name="Kenji Watanabe",
                    approver_role="RISK_APPROVER",
                    action="APPROVE",
                    comments="Tier 2 High-Value Dual Authorization authorized.",
                    approved_changes=[],
                    step_number=2,
                    created_at=t_l2
                )
                db.add(rec2)
                approval_hist.append({
                    "approval_id": rec2.approval_id,
                    "case_id": case_id,
                    "recommendation_id": rec2.recommendation_id,
                    "approver_id": rec2.approver_id,
                    "approver_name": rec2.approver_name,
                    "approver_role": rec2.approver_role,
                    "action": rec2.action,
                    "comments": rec2.comments,
                    "approved_changes": [],
                    "step_number": 2,
                    "created_at": t_l2.isoformat()
                })

            gq_items = build_rich_guided_recommendation(
                case_id=case_id,
                profile=profile,
                amount=amount,
                creditor_name=cp_name,
                creditor_country=cp_country,
                case_idx=i
            ).guided_questions

            case_model = CaseModel(
                case_id=case_id,
                payment_id=f"PMT-{i:06d}",
                uetr=uetr,
                payment_ref=payment_ref,
                profile=profile.value,
                domain=domain.value,
                secondary_profiles=[],
                error_code=f"ERR_{prefix}_{i:03d}",
                reason=f"Exception in {domain.value} domain: {profile.value.replace('_', ' ').title()}.",
                amount=round(amount, 2),
                currency=cp_ccy,
                payment_rail="SWIFT_CBPR+" if cp_ccy != "USD" else "FEDWIRE_ISO20022",
                debtor_party={"party_name": f"Ordering Corp {i}", "country": "US", "token_ref": debtor_tok},
                debtor_account={"account_number": f"US11APEX998877{i:04d}", "token_ref": debtor_acc_tok},
                creditor_party={"party_name": cp_name, "country": cp_country, "token_ref": creditor_tok},
                creditor_account={"iban": f"{cp_country}82WEST1234569876{i:04d}", "bank_bic": cp_bic, "token_ref": creditor_iban_tok},
                queue=queue,
                status=status.value,
                severity=ExceptionSeverity.HIGH.value if amount >= 250000.0 else ExceptionSeverity.MEDIUM.value,
                priority=ExceptionPriority.HIGH.value if amount >= 250000.0 else ExceptionPriority.NORMAL.value,
                sla_due_at=sla_due.isoformat(),
                dual_auth_required=(amount >= 250000.0),
                ai_confidence=ai_conf,
                created_at=t_base.isoformat(),
                settled_at=(t_base + timedelta(minutes=45)).isoformat() if status == LifecycleStage.SETTLED else None,
                approval_history=approval_hist,
                audit_timeline=audit_timeline,
                guided_questions=[q.dict() for q in gq_items],
                expedite_ping=None
            )
            db.add(case_model)
            case_counter += 1

    db.commit()
    print(f"[PeX DB] Successfully seeded {db.query(CaseModel).count()} cases, {db.query(AuditEventModel).count()} audit events, and {db.query(UserModel).count()} users into persistent DB.")

def init_db(force_reseed: bool = False):
    """Entrypoint to initialize database tables and seed baseline data."""
    create_tables()
    db = SessionLocal()
    try:
        seed_users(db)
        seed_initial_data(db, force_reseed=force_reseed)
    finally:
        db.close()
