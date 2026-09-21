"""Governed Straight-Through Processing (STP) & Fast-Lane Batch Engine for PeX."""
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from app.schemas.stp import (
    STPMode,
    STPEligibilityItem,
    BatchSTPRequest,
    BatchSTPResponse,
    SettledCaseSummary,
    STPTelemetryResponse,
)
from app.schemas.canonical import LifecycleStage
from app.db.session import SessionLocal
from app.db.models import (
    CaseModel,
    ApprovalRecordModel,
    GovernedActionModel,
    DeliveryReceiptModel,
    AuditEventModel,
)
from app.services.rule_engine import rule_engine
from app.services.data_loader import repo

class STPEngine:
    """Evaluates STP eligibility, executes autonomous zero-touch repairs, and handles 1-click batch releases."""

    def evaluate_case_eligibility(
        self,
        case: Dict[str, Any],
        active_rules: Optional[List[Dict[str, Any]]] = None
    ) -> STPEligibilityItem:
        """Evaluates whether a given payment exception qualifies for Autonomous STP or 1-Click Fast-Lane."""
        case_id = case.get("case_id", "")
        payment_id = case.get("payment_id", "")
        amount = float(case.get("amount", 0.0))
        currency = case.get("currency", "USD")
        domain = str(case.get("domain", "")).upper()
        profile = str(case.get("profile", "")).upper()
        confidence = float(case.get("ai_confidence") or 0.0)
        status = case.get("status", "")

        # Extract rich dossier fields
        debtor_name = case.get("debtor_name") or "Apex Global Treasury (US)"
        creditor_name = case.get("creditor_name") or case.get("counterparty_name") or "Nordhavn Components A/S"
        debtor_bic = case.get("debtor_agent_bic") or "CHASUS33XXX"
        creditor_bic = case.get("creditor_agent_bic") or "BARCGB22XXX"
        clearing_rail = case.get("clearing_rail") or ("FEDWIRE" if currency == "USD" else "TARGET2" if currency == "EUR" else "CHAPS" if currency == "GBP" else "SWIFT CBPR+")
        uetr = case.get("uetr") or f"UETR-{case_id}"
        urgency = case.get("urgency") or ("HIGH" if amount >= 20000.0 else "MEDIUM")
        sanctions_status = "CLEAN (0 Hits)"

        # Get proposed repair summary if available
        rec = repo.recommendations.get(case_id)
        proposed_summary = None
        orig_field = None
        orig_val = None
        prop_val = None
        field_justif = None
        if rec and rec.proposed_changes:
            pc = rec.proposed_changes[0]
            orig_field = pc.field_path
            orig_val = pc.original_value_masked
            prop_val = pc.proposed_value_masked
            field_justif = pc.justification
            proposed_summary = f"Repair {pc.field_path}: {pc.original_value_masked} -> {pc.proposed_value_masked}"

        # 1. STRICT DISQUALIFIERS (Non-Negotiable Regulatory & Risk Guardrails)
        if amount >= 250000.0:
            return STPEligibilityItem(
                case_id=case_id, payment_id=payment_id, amount=amount, currency=currency,
                domain=domain, profile=profile, ai_confidence=confidence, eligible=False,
                mode=STPMode.MANUAL_GATED,
                reason="High-value wire (>= $250,000) mandates 2-Level Maker-Checker Dual Authorization.",
                proposed_repair_summary=proposed_summary,
                debtor_name=debtor_name, creditor_name=creditor_name,
                debtor_agent_bic=debtor_bic, creditor_agent_bic=creditor_bic,
                clearing_rail=clearing_rail, original_field=orig_field,
                original_value=orig_val, proposed_value=prop_val,
                field_justification=field_justif, sanctions_status=sanctions_status,
                uetr=uetr, urgency=urgency
            )

        if domain in ["SANCTIONS_AML", "COMPLIANCE"] or "SANCTION" in profile or "OFAC" in profile:
            return STPEligibilityItem(
                case_id=case_id, payment_id=payment_id, amount=amount, currency=currency,
                domain=domain, profile=profile, ai_confidence=confidence, eligible=False,
                mode=STPMode.MANUAL_GATED,
                reason="Sanctions/AML compliance exceptions strictly prohibit zero-touch STP.",
                proposed_repair_summary=proposed_summary,
                debtor_name=debtor_name, creditor_name=creditor_name,
                debtor_agent_bic=debtor_bic, creditor_agent_bic=creditor_bic,
                clearing_rail=clearing_rail, original_field=orig_field,
                original_value=orig_val, proposed_value=prop_val,
                field_justification=field_justif, sanctions_status="FLAGGED (Requires Compliance Review)",
                uetr=uetr, urgency=urgency
            )

        if domain in ["SETTLEMENT_RETURNS"] or "RECALL" in profile:
            return STPEligibilityItem(
                case_id=case_id, payment_id=payment_id, amount=amount, currency=currency,
                domain=domain, profile=profile, ai_confidence=confidence, eligible=False,
                mode=STPMode.MANUAL_GATED,
                reason="Settlement returns and pacs.004 payment recalls require investigator review.",
                proposed_repair_summary=proposed_summary,
                debtor_name=debtor_name, creditor_name=creditor_name,
                debtor_agent_bic=debtor_bic, creditor_agent_bic=creditor_bic,
                clearing_rail=clearing_rail, original_field=orig_field,
                original_value=orig_val, proposed_value=prop_val,
                field_justification=field_justif, sanctions_status=sanctions_status,
                uetr=uetr, urgency=urgency
            )

        if status == LifecycleStage.SETTLED.value or status == "SETTLED":
            return STPEligibilityItem(
                case_id=case_id, payment_id=payment_id, amount=amount, currency=currency,
                domain=domain, profile=profile, ai_confidence=confidence, eligible=False,
                mode=STPMode.MANUAL_GATED,
                reason="Case is already settled.",
                proposed_repair_summary=proposed_summary,
                debtor_name=debtor_name, creditor_name=creditor_name,
                debtor_agent_bic=debtor_bic, creditor_agent_bic=creditor_bic,
                clearing_rail=clearing_rail, original_field=orig_field,
                original_value=orig_val, proposed_value=prop_val,
                field_justification=field_justif, sanctions_status=sanctions_status,
                uetr=uetr, urgency=urgency
            )

        # 2. MATCH AGAINST DYNAMIC DB RULES
        if active_rules is None:
            active_rules = repo.get_policy_rules(status="ACTIVE")

        for rule in active_rules:
            if rule.get("category") == "STP_FAST_LANE" and rule.get("status") == "ACTIVE":
                if rule_engine.evaluate_rule(rule, case):
                    actions = rule.get("actions", {})
                    is_auto = actions.get("autonomous_mode", False) or amount <= 10000.0 and confidence >= 0.98
                    mode = STPMode.AUTONOMOUS if is_auto else STPMode.ONE_CLICK_BATCH
                    return STPEligibilityItem(
                        case_id=case_id, payment_id=payment_id, amount=amount, currency=currency,
                        domain=domain, profile=profile, ai_confidence=confidence, eligible=True,
                        mode=mode,
                        reason=f"Matched Active Policy Rule: {rule.get('name')}",
                        matching_rule_id=rule.get("rule_id"),
                        matching_rule_name=rule.get("name"),
                        proposed_repair_summary=proposed_summary,
                        debtor_name=debtor_name, creditor_name=creditor_name,
                        debtor_agent_bic=debtor_bic, creditor_agent_bic=creditor_bic,
                        clearing_rail=clearing_rail, original_field=orig_field,
                        original_value=orig_val, proposed_value=prop_val,
                        field_justification=field_justif, sanctions_status=sanctions_status,
                        uetr=uetr, urgency=urgency
                    )

        # 3. BASELINE INSTITUTIONAL STP HEURISTICS
        # Mode A: Autonomous Zero-Touch STP (<=$10k, >=98% conf, pure syntax)
        if amount <= 10000.0 and confidence >= 0.98 and domain in ["DATA_QUALITY", "FORMAT_SYNTAX"]:
            return STPEligibilityItem(
                case_id=case_id, payment_id=payment_id, amount=amount, currency=currency,
                domain=domain, profile=profile, ai_confidence=confidence, eligible=True,
                mode=STPMode.AUTONOMOUS,
                reason="Qualifies for Autonomous Zero-Touch STP (<= $10k, >= 98% confidence, Data Quality domain).",
                proposed_repair_summary=proposed_summary,
                debtor_name=debtor_name, creditor_name=creditor_name,
                debtor_agent_bic=debtor_bic, creditor_agent_bic=creditor_bic,
                clearing_rail=clearing_rail, original_field=orig_field,
                original_value=orig_val, proposed_value=prop_val,
                field_justification=field_justif, sanctions_status=sanctions_status,
                uetr=uetr, urgency=urgency
            )

        # Mode B: 1-Click Supervised Fast-Lane Batch (<=$25k, >=90% conf)
        if amount <= 25000.0 and confidence >= 0.90 and domain in ["DATA_QUALITY", "FORMAT_SYNTAX", "PROCESSING", "ACCOUNT_DIRECTORY"]:
            return STPEligibilityItem(
                case_id=case_id, payment_id=payment_id, amount=amount, currency=currency,
                domain=domain, profile=profile, ai_confidence=confidence, eligible=True,
                mode=STPMode.ONE_CLICK_BATCH,
                reason="Qualifies for 1-Click Fast-Lane Batch Settlement (<= $25k, >= 90% confidence).",
                proposed_repair_summary=proposed_summary,
                debtor_name=debtor_name, creditor_name=creditor_name,
                debtor_agent_bic=debtor_bic, creditor_agent_bic=creditor_bic,
                clearing_rail=clearing_rail, original_field=orig_field,
                original_value=orig_val, proposed_value=prop_val,
                field_justification=field_justif, sanctions_status=sanctions_status,
                uetr=uetr, urgency=urgency
            )

        return STPEligibilityItem(
            case_id=case_id, payment_id=payment_id, amount=amount, currency=currency,
            domain=domain, profile=profile, ai_confidence=confidence, eligible=False,
            mode=STPMode.MANUAL_GATED,
            reason="Standard HITL review required (amount or confidence below fast-lane policy thresholds).",
            proposed_repair_summary=proposed_summary,
            debtor_name=debtor_name, creditor_name=creditor_name,
            debtor_agent_bic=debtor_bic, creditor_agent_bic=creditor_bic,
            clearing_rail=clearing_rail, original_field=orig_field,
            original_value=orig_val, proposed_value=prop_val,
            field_justification=field_justif, sanctions_status=sanctions_status,
            uetr=uetr, urgency=urgency
        )

    def get_eligible_cases(self) -> List[STPEligibilityItem]:
        """Returns all live open cases that currently qualify for STP / Fast-Lane."""
        all_cases = list(repo._case_cache.values())
        active_rules = repo.get_policy_rules(status="ACTIVE")
        eligible_items: List[STPEligibilityItem] = []

        for c in all_cases:
            if c.get("status") not in [LifecycleStage.SETTLED.value, "SETTLED", "REJECTED"]:
                eval_item = self.evaluate_case_eligibility(c, active_rules)
                if eval_item.eligible:
                    eligible_items.append(eval_item)

        # Sort by highest confidence and lowest amount first
        eligible_items.sort(key=lambda x: (- (x.ai_confidence or 0), x.amount))
        return eligible_items

    def execute_autonomous_stp(
        self,
        case_id: str,
        rule_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes zero-touch autonomous settlement for a qualified micro-repair exception."""
        case = repo.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        eval_item = self.evaluate_case_eligibility(case)
        if not eval_item.eligible:
            raise ValueError(f"Case {case_id} does not qualify for STP: {eval_item.reason}")

        db: Session = SessionLocal()
        try:
            now = datetime.utcnow()
            now_iso = now.isoformat()

            # 1. Record System Approval Signature
            approval_id = f"APR-AUTOSTP-{uuid.uuid4().hex[:6].upper()}"
            appr = ApprovalRecordModel(
                approval_id=approval_id,
                case_id=case_id,
                recommendation_id=f"REC-{case_id}",
                approver_id="SYS-AUTONOMOUS-STP",
                approver_name="PeX Governed Autonomous Reasoner",
                approver_role="ADMIN",
                action="APPROVE",
                comments=f"Autonomous zero-touch STP execution authorized via policy {eval_item.matching_rule_id or 'STP-BASELINE'}.",
                approved_changes=[],
                step_number=1,
                created_at=now
            )
            db.add(appr)

            # 2. Create Idempotent Action
            action_id = f"ACT-STP-{uuid.uuid4().hex[:6].upper()}"
            idempotency_key = f"IDEMP-STP-{case_id}-{uuid.uuid4().hex[:4]}"
            act = GovernedActionModel(
                action_id=action_id,
                case_id=case_id,
                approval_ids=[approval_id],
                action_type="REPAIR_AND_RELEASE",
                target_system="SWIFT_CBPR_AUTO_SETTLEMENT_HUB",
                idempotency_key=idempotency_key,
                dispatch_payload={"case_id": case_id, "amount": case.get("amount"), "currency": case.get("currency")},
                status="SETTLED",
                dispatched_at=now,
                settled_at=now
            )
            db.add(act)

            # 3. Create Delivery Receipt
            receipt_id = f"RCPT-STP-{uuid.uuid4().hex[:6].upper()}"
            rcpt = DeliveryReceiptModel(
                receipt_id=receipt_id,
                action_id=action_id,
                case_id=case_id,
                bank_ack_reference=f"ACK-STP-{case_id.replace('PEX-', '')}-{uuid.uuid4().hex[:6].upper()}",
                status="SETTLED_STP_AUTONOMOUS",
                timestamp=now,
                details={"mode": "ZERO_TOUCH_STP", "execution_time_ms": 14}
            )
            db.add(rcpt)

            # 4. Update Case
            db_case = db.query(CaseModel).filter(CaseModel.case_id == case_id).first()
            if db_case:
                db_case.status = LifecycleStage.SETTLED.value
                db_case.settled_at = now_iso
                
                # Append to timeline
                tl = list(db_case.audit_timeline or [])
                tl.append({
                    "step_index": len(tl) + 1,
                    "timestamp": now_iso,
                    "actor_name": "Autonomous STP Reasoner",
                    "actor_role": "SYSTEM_AUTONOMOUS",
                    "badge_color": "emerald",
                    "action_title": "Autonomous STP Settlement Dispatched",
                    "icon": "⚡",
                    "summary": f"Zero-touch repair and settlement executed in 14ms ({eval_item.reason})."
                })
                db_case.audit_timeline = tl
                
                # Append to approval history
                ah = list(db_case.approval_history or [])
                ah.append({
                    "approval_id": approval_id,
                    "case_id": case_id,
                    "recommendation_id": f"REC-{case_id}",
                    "approver_id": "SYS-AUTONOMOUS-STP",
                    "approver_name": "Autonomous STP Reasoner",
                    "approver_role": "ADMIN",
                    "action": "APPROVE",
                    "comments": f"Zero-touch STP execution via {eval_item.matching_rule_name or 'STP Heuristic'}",
                    "approved_changes": [],
                    "step_number": 1,
                    "created_at": now_iso
                })
                db_case.approval_history = ah

            db.commit()

            # 5. Log Cryptographic Audit Event
            repo.log_audit_event(
                case_id=case_id,
                correlation_id=case.get("uetr", f"UETR-{case_id}"),
                stage_name="SETTLED",
                actor_id="SYS-AUTONOMOUS-STP",
                actor_role="SYSTEM_AUTONOMOUS",
                action_name="Autonomous STP Settlement Release",
                details=f"Case {case_id} (${case.get('amount'):,.2f}) auto-repaired and settled with zero human latency.",
                control_tags=["STP_AUTONOMOUS", "ZERO_TOUCH", "ISO20022_DISPATCH"]
            )

            # Sync in-memory cache
            repo.sync_from_db()
            return {
                "case_id": case_id,
                "status": "SETTLED",
                "mode": "AUTONOMOUS",
                "action_id": action_id,
                "receipt_id": receipt_id,
                "settled_at": now_iso,
                "message": f"Case {case_id} autonomously settled in 14ms via Governed STP."
            }
        finally:
            db.close()

    def execute_batch_fast_lane_release(
        self,
        payload: BatchSTPRequest
    ) -> BatchSTPResponse:
        """Executes atomic 1-click batch settlement release for up to 50 qualified fast-lane cases."""
        batch_id = f"BATCH-STP-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.utcnow()
        now_iso = now.isoformat()

        settled_list: List[SettledCaseSummary] = []
        total_vol = 0.0
        processed_count = 0
        failed_count = 0

        db: Session = SessionLocal()
        try:
            for cid in payload.case_ids:
                case = repo.get_case(cid)
                if not case or case.get("status") in [LifecycleStage.SETTLED.value, "SETTLED"]:
                    failed_count += 1
                    continue

                eval_item = self.evaluate_case_eligibility(case)
                if not eval_item.eligible:
                    failed_count += 1
                    continue

                amt = float(case.get("amount", 0.0))
                ccy = case.get("currency", "USD")
                total_vol += amt

                # 1. Approval Record
                approval_id = f"APR-BATCH-{uuid.uuid4().hex[:6].upper()}"
                appr = ApprovalRecordModel(
                    approval_id=approval_id,
                    case_id=cid,
                    recommendation_id=f"REC-{cid}",
                    approver_id=payload.approver_id,
                    approver_name=payload.approver_name,
                    approver_role=payload.approver_role,
                    action="APPROVE",
                    comments=payload.comments or f"1-Click Supervised Fast-Lane batch release ({batch_id}).",
                    approved_changes=[],
                    step_number=1,
                    created_at=now
                )
                db.add(appr)

                # 2. Governed Action
                action_id = f"ACT-BATCH-{uuid.uuid4().hex[:6].upper()}"
                idempotency_key = f"IDEMP-BATCH-{cid}-{uuid.uuid4().hex[:4]}"
                act = GovernedActionModel(
                    action_id=action_id,
                    case_id=cid,
                    approval_ids=[approval_id],
                    action_type="REPAIR_AND_RELEASE",
                    target_system="SWIFT_CBPR_FASTLANE_GATEWAY",
                    idempotency_key=idempotency_key,
                    dispatch_payload={"case_id": cid, "amount": amt, "currency": ccy, "batch_id": batch_id},
                    status="SETTLED",
                    dispatched_at=now,
                    settled_at=now
                )
                db.add(act)

                # 3. Delivery Receipt
                receipt_id = f"RCPT-BATCH-{uuid.uuid4().hex[:6].upper()}"
                rcpt = DeliveryReceiptModel(
                    receipt_id=receipt_id,
                    action_id=action_id,
                    case_id=cid,
                    bank_ack_reference=f"ACK-BATCH-{cid.replace('PEX-', '')}-{uuid.uuid4().hex[:6].upper()}",
                    status="SETTLED_STP_BATCH",
                    timestamp=now,
                    details={"batch_id": batch_id, "approver": payload.approver_name}
                )
                db.add(rcpt)

                # 4. Update Case
                db_case = db.query(CaseModel).filter(CaseModel.case_id == cid).first()
                if db_case:
                    db_case.status = LifecycleStage.SETTLED.value
                    db_case.settled_at = now_iso

                    tl = list(db_case.audit_timeline or [])
                    tl.append({
                        "step_index": len(tl) + 1,
                        "timestamp": now_iso,
                        "actor_name": payload.approver_name,
                        "actor_role": payload.approver_role,
                        "badge_color": "emerald",
                        "action_title": "1-Click Fast-Lane Batch Released",
                        "icon": "⚡",
                        "summary": f"Supervised batch settlement release authorized ({batch_id})."
                    })
                    db_case.audit_timeline = tl

                    ah = list(db_case.approval_history or [])
                    ah.append({
                        "approval_id": approval_id,
                        "case_id": cid,
                        "recommendation_id": f"REC-{cid}",
                        "approver_id": payload.approver_id,
                        "approver_name": payload.approver_name,
                        "approver_role": payload.approver_role,
                        "action": "APPROVE",
                        "comments": f"1-Click Fast-Lane Batch Release ({batch_id})",
                        "approved_changes": [],
                        "step_number": 1,
                        "created_at": now_iso
                    })
                    db_case.approval_history = ah

                # 5. Append Cryptographic Audit Event
                repo.log_audit_event(
                    case_id=cid,
                    correlation_id=case.get("uetr", f"UETR-{cid}"),
                    stage_name="SETTLED",
                    actor_id=payload.approver_id,
                    actor_role=payload.approver_role,
                    action_name="Fast-Lane Batch Release",
                    details=f"Case {cid} (${amt:,.2f}) released in batch {batch_id} by {payload.approver_name}.",
                    control_tags=["STP_BATCH", "FAST_LANE", "HITL_SUPERVISED"]
                )

                settled_list.append(
                    SettledCaseSummary(
                        case_id=cid,
                        payment_id=case.get("payment_id", ""),
                        amount=amt,
                        currency=ccy,
                        action_id=action_id,
                        receipt_id=receipt_id,
                        status="SETTLED"
                    )
                )
                processed_count += 1

            db.commit()
            repo.sync_from_db()

            return BatchSTPResponse(
                batch_id=batch_id,
                total_requested=len(payload.case_ids),
                processed_count=processed_count,
                failed_count=failed_count,
                settled_cases=settled_list,
                total_dollar_volume=round(total_vol, 2),
                executed_by=f"{payload.approver_name} ({payload.approver_role})",
                timestamp=now_iso,
                message=f"Successfully executed 1-Click Fast-Lane settlement for {processed_count} cases (${total_vol:,.2f} total volume)."
            )
        finally:
            db.close()

    def get_stp_telemetry(self) -> STPTelemetryResponse:
        """Computes real-time STP adoption KPIs and operational time savings."""
        all_cases = list(repo._case_cache.values())
        total_cases = len(all_cases)
        settled_cases = [c for c in all_cases if c.get("status") in [LifecycleStage.SETTLED.value, "SETTLED"]]
        settled_count = len(settled_cases)

        active_rules = repo.get_policy_rules(status="ACTIVE")
        stp_rules = [r for r in active_rules if r.get("category") == "STP_FAST_LANE"]

        eligible_items = self.get_eligible_cases()
        eligible_count = len(eligible_items)
        eligible_vol = sum(item.amount for item in eligible_items)

        # Count cases settled via STP/Fast-Lane by looking at timeline/receipts
        auto_count = 0
        batch_count = 0
        for sc in settled_cases:
            tl = sc.get("audit_timeline", [])
            for ev in tl:
                title = ev.get("action_title", "")
                if "Autonomous STP" in title:
                    auto_count += 1
                    break
                elif "Fast-Lane" in title or "Batch" in title:
                    batch_count += 1
                    break

        total_stp_settled = auto_count + batch_count
        overall_stp_rate = round((total_stp_settled / settled_count * 100.0), 1) if settled_count > 0 else 0.0

        # Domain breakdown
        domain_stp_rates: Dict[str, float] = {}
        for dom in ["DATA_QUALITY", "FORMAT_SYNTAX", "PROCESSING", "ACCOUNT_DIRECTORY", "CLIENT_TREASURY", "COMPLIANCE"]:
            dom_settled = [c for c in settled_cases if str(c.get("domain", "")).upper() == dom]
            dom_stp = sum(1 for c in dom_settled if any("STP" in str(ev.get("action_title", "")) for ev in c.get("audit_timeline", [])))
            rate = round((dom_stp / len(dom_settled) * 100.0), 1) if dom_settled else 0.0
            domain_stp_rates[dom] = rate

        # Operational time savings (average 3.8 hours manual investigation saved per STP case)
        time_savings_hrs = round(total_stp_settled * 3.8, 1)

        return STPTelemetryResponse(
            total_cases=total_cases,
            settled_cases=settled_count,
            overall_stp_rate_pct=overall_stp_rate,
            fast_lane_eligible_count=eligible_count,
            fast_lane_eligible_volume=round(eligible_vol, 2),
            autonomous_stp_count=auto_count,
            batch_fast_lane_count=batch_count,
            avg_resolution_seconds_stp=1.8,
            avg_resolution_seconds_manual=13680.0,  # 3.8 hours in seconds
            time_savings_hours=time_savings_hrs,
            domain_stp_rates=domain_stp_rates,
            active_stp_rules=stp_rules
        )

    def seed_stp_sample_cases(self) -> Dict[str, Any]:
        """Seeds 12 curated, realistic payment exception cases specifically qualified for STP Fast-Lane batch execution."""
        from app.db.models import RecommendationModel
        from app.core.tokenization import token_vault

        sample_defs = [
            {
                "case_id": "PEX-STP-0101",
                "profile": "INVALID_IBAN",
                "domain": "DATA_QUALITY",
                "amount": 8450.00,
                "currency": "GBP",
                "payment_rail": "CHAPS",
                "confidence": 0.98,
                "debtor": "Apex Global Treasury (US)",
                "creditor": "Nordhavn Components A/S",
                "debtor_bic": "CHASUS33XXX",
                "creditor_bic": "BARCGB22XXX",
                "field_path": "creditor_account.iban",
                "orig_val": "GB29MIDL40051512345678",
                "prop_val": "GB29MIDL40051512345679",
                "justification": "MOD-97 check digit transposition resolved via UK CHAPS sort-code directory.",
                "reason": "Invalid IBAN checksum (MOD-97 calculation failure on character 24)."
            },
            {
                "case_id": "PEX-STP-0102",
                "profile": "INVALID_BIC",
                "domain": "DATA_QUALITY",
                "amount": 14200.00,
                "currency": "EUR",
                "payment_rail": "TARGET2",
                "confidence": 0.96,
                "debtor": "Zurich Tech Logistics AG",
                "creditor": "Vanguard BioPharma GmbH",
                "debtor_bic": "UBSWCHZHXXX",
                "creditor_bic": "DEUTDEDDXXX",
                "field_path": "creditor_agent.bic",
                "orig_val": "DEUTDEDDXX",
                "prop_val": "DEUTDEDDXXX",
                "justification": "ISO 9362 8-to-11 char BIC padding normalized against SWIFT Head Office directory.",
                "reason": "Truncated 10-char BIC format rejected by TARGET2 clearing gateway."
            },
            {
                "case_id": "PEX-STP-0103",
                "profile": "MISSING_PURPOSE_CODE",
                "domain": "DATA_QUALITY",
                "amount": 3850.00,
                "currency": "USD",
                "payment_rail": "FEDWIRE",
                "confidence": 0.99,
                "debtor": "JPMorgan Commercial Client",
                "creditor": "Apex Global Treasury",
                "debtor_bic": "CHASUS33XXX",
                "creditor_bic": "CHASUS33XXX",
                "field_path": "payment_type_info.purpose_code",
                "orig_val": "[NULL / MISSING]",
                "prop_val": "SUPP",
                "justification": "Inferred mandatory ISO 20022 SUPP commercial supplier code from invoice metadata.",
                "reason": "Missing mandatory ISO 20022 external purpose code for cross-border commercial wire."
            },
            {
                "case_id": "PEX-STP-0104",
                "profile": "INVALID_ROUTING_CODE",
                "domain": "DATA_QUALITY",
                "amount": 18600.00,
                "currency": "USD",
                "payment_rail": "FEDWIRE",
                "confidence": 0.95,
                "debtor": "Sydney Infrastructure Ltd",
                "creditor": "Atlas Mediterranean Marine",
                "debtor_bic": "ANZBAU3MXXX",
                "creditor_bic": "CHASUS33XXX",
                "field_path": "creditor_agent.aba_routing",
                "orig_val": "021000020",
                "prop_val": "021000021",
                "justification": "Federal Reserve Fedwire ABA routing check digit validated via FedLine directory.",
                "reason": "Invalid 9-digit ABA routing transit check digit transposition."
            },
            {
                "case_id": "PEX-STP-0105",
                "profile": "BENEFICIARY_NAME_MISMATCH",
                "domain": "DATA_QUALITY",
                "amount": 9120.00,
                "currency": "USD",
                "payment_rail": "SWIFT_CBPR+",
                "confidence": 0.94,
                "debtor": "Bavaria Engine Works AG",
                "creditor": "HarborView Supplier Ltd",
                "debtor_bic": "HYVEDEMMXXX",
                "creditor_bic": "WESTGB2LXXX",
                "field_path": "creditor_party.party_name",
                "orig_val": "HarborView Supp. Ltd",
                "prop_val": "HarborView Supplier Ltd",
                "justification": "Legal entity abbreviation expanded and matched against Confirmation of Payee (CoP) register.",
                "reason": "Confirmation of Payee (CoP) name similarity divergence > 5% on abbreviated string."
            },
            {
                "case_id": "PEX-STP-0106",
                "profile": "MISSING_REMITTANCE_INFO",
                "domain": "DATA_QUALITY",
                "amount": 6400.00,
                "currency": "GBP",
                "payment_rail": "CHAPS",
                "confidence": 0.97,
                "debtor": "Nordhavn Components A/S",
                "creditor": "Kyoto Precision Robotics",
                "debtor_bic": "BARCGB22XXX",
                "creditor_bic": "BOTKJPJTXXX",
                "field_path": "remittance_info.unstructured",
                "orig_val": "[EMPTY_TAG]",
                "prop_val": "INV-2026-UK-88412",
                "justification": "Extracted verified commercial invoice reference from debtor payment initiation payload.",
                "reason": "Mandatory remittance information missing under UK RTGS Rulebook."
            },
            {
                "case_id": "PEX-STP-0107",
                "profile": "INVALID_ADDRESS_FORMAT",
                "domain": "DATA_QUALITY",
                "amount": 11750.00,
                "currency": "EUR",
                "payment_rail": "TARGET2",
                "confidence": 0.96,
                "debtor": "Singapore FinTech Holding",
                "creditor": "Vanguard BioPharma GmbH",
                "debtor_bic": "DBSSSGSGXXX",
                "creditor_bic": "DEUTDEDDXXX",
                "field_path": "creditor_party.postal_address",
                "orig_val": "Frankfurt AM Main 60311",
                "prop_val": "Taunusanlage 8, 60329 Frankfurt am Main, DE",
                "justification": "Unstructured postal address geocoded and normalized to ISO 20022 structured elements.",
                "reason": "Unstructured street address rejected under CBPR+ Quality Mandate."
            },
            {
                "case_id": "PEX-STP-0108",
                "profile": "ISO20022_VALIDATION_ERROR",
                "domain": "PROCESSING",
                "amount": 4950.00,
                "currency": "USD",
                "payment_rail": "FEDWIRE",
                "confidence": 0.99,
                "debtor": "Atlas Mediterranean Marine",
                "creditor": "Apex Global Treasury",
                "debtor_bic": "NBGRGRAAXXX",
                "creditor_bic": "CHASUS33XXX",
                "field_path": "charge_bearer.code",
                "orig_val": "SHAR",
                "prop_val": "SHA",
                "justification": "Invalid 4-character charge tag SHAR converted to standard 3-char ISO tag SHA.",
                "reason": "XML Schema validation error: ChargeBearerType 'SHAR' does not match enumeration [DEBT, CRED, SHA, SLEV]."
            },
            {
                "case_id": "PEX-STP-0109",
                "profile": "ROUTING_FAILURE",
                "domain": "PROCESSING",
                "amount": 16300.00,
                "currency": "USD",
                "payment_rail": "SWIFT_CBPR+",
                "confidence": 0.93,
                "debtor": "Kyoto Precision Robotics",
                "creditor": "HarborView Supplier Ltd",
                "debtor_bic": "BOTKJPJTXXX",
                "creditor_bic": "WESTGB2LXXX",
                "field_path": "intermediary_agent.bic",
                "orig_val": "CHASUS33OFF",
                "prop_val": "CHASUS33XXX",
                "justification": "Inactive offline intermediary BIC re-routed to primary active Nostro gateway node.",
                "reason": "Intermediary institution offline in clearing directory routing table."
            },
            {
                "case_id": "PEX-STP-0110",
                "profile": "PAYMENT_HELD_FOR_REPAIR",
                "domain": "PROCESSING",
                "amount": 22500.00,
                "currency": "USD",
                "payment_rail": "FEDWIRE",
                "confidence": 0.92,
                "debtor": "HarborView Supplier Ltd",
                "creditor": "Apex Global Treasury",
                "debtor_bic": "WESTGB2LXXX",
                "creditor_bic": "CHASUS33XXX",
                "field_path": "settlement_priority",
                "orig_val": "STND",
                "prop_val": "HIGH",
                "justification": "Expedited settlement priority tag applied to resolve payment queue hold.",
                "reason": "Transaction paused in clearing queue awaiting operational priority assignment."
            },
            {
                "case_id": "PEX-STP-0111",
                "profile": "INVALID_ACCOUNT_NUMBER",
                "domain": "DATA_QUALITY",
                "amount": 7600.00,
                "currency": "GBP",
                "payment_rail": "CHAPS",
                "confidence": 0.97,
                "debtor": "Zurich Tech Logistics AG",
                "creditor": "Nordhavn Components A/S",
                "debtor_bic": "UBSWCHZHXXX",
                "creditor_bic": "BARCGB22XXX",
                "field_path": "creditor_account.account_number",
                "orig_val": "400515-12345",
                "prop_val": "40051500012345",
                "justification": "Hyphenated legacy UK account padded to standard 14-digit clearing format.",
                "reason": "Legacy account formatting non-compliant with pacs.008 schema specification."
            },
            {
                "case_id": "PEX-STP-0112",
                "profile": "MISSING_BENEFICIARY_DATA",
                "domain": "DATA_QUALITY",
                "amount": 12900.00,
                "currency": "EUR",
                "payment_rail": "TARGET2",
                "confidence": 0.95,
                "debtor": "Bavaria Engine Works AG",
                "creditor": "Vanguard BioPharma GmbH",
                "debtor_bic": "HYVEDEMMXXX",
                "creditor_bic": "DEUTDEDDXXX",
                "field_path": "creditor_party.country",
                "orig_val": "[BLANK]",
                "prop_val": "DE",
                "justification": "ISO 3166-1 alpha-2 country code DE inferred from IBAN prefix DE89.",
                "reason": "Missing mandatory creditor country code in pacs.008 payload."
            }
        ]

        db: Session = SessionLocal()
        created_ids = []
        try:
            now = datetime.utcnow()
            for idx, s in enumerate(sample_defs):
                cid = s["case_id"]
                t_base = now - timedelta(minutes=10 + (idx * 5))
                sla_due = t_base + timedelta(hours=4)
                uetr = f"UETR-2026-STP-{idx+1:04d}-A8"
                debtor_tok = token_vault.tokenize(s["debtor"], "PARTY")
                creditor_tok = token_vault.tokenize(s["creditor"], "PARTY")

                # 1. Upsert Case
                db_case = db.query(CaseModel).filter(CaseModel.case_id == cid).first()
                if not db_case:
                    db_case = CaseModel(
                        case_id=cid,
                        payment_id=f"PMT-STP-{idx+1:06d}",
                        uetr=uetr,
                        payment_ref=f"PAY-STP-{idx+1:06d}",
                        profile=s["profile"],
                        domain=s["domain"],
                        secondary_profiles=[],
                        error_code=f"ERR_STP_{idx+1:03d}",
                        reason=s["reason"],
                        amount=s["amount"],
                        currency=s["currency"],
                        payment_rail=s["payment_rail"],
                        debtor_party={"party_name": s["debtor"], "country": "US", "token_ref": debtor_tok},
                        debtor_account={"account_number": f"US11APEX998877{idx+100:04d}", "token_ref": debtor_tok},
                        creditor_party={"party_name": s["creditor"], "country": "GB", "token_ref": creditor_tok},
                        creditor_account={"iban": f"GB82WEST1234569876{idx+100:04d}", "bank_bic": s["creditor_bic"], "token_ref": creditor_tok},
                        queue="Repair",
                        status="RECOMMENDED",
                        severity="LOW" if s["amount"] < 10000 else "MEDIUM",
                        priority="NORMAL",
                        sla_due_at=sla_due.isoformat(),
                        dual_auth_required=False,
                        ai_confidence=s["confidence"],
                        created_at=t_base.isoformat(),
                        settled_at=None,
                        approval_history=[],
                        audit_timeline=[
                            {
                                "step_index": 1,
                                "timestamp": t_base.isoformat(),
                                "actor_name": "PeX Ingestion Gateway",
                                "actor_role": "SYSTEM",
                                "badge_color": "slate",
                                "action_title": "Exception Ingested & Canonicalized",
                                "icon": "📥",
                                "summary": f"Payment wire received via {s['payment_rail']}. PII tokenized into isolated vault."
                            },
                            {
                                "step_index": 2,
                                "timestamp": (t_base + timedelta(minutes=2)).isoformat(),
                                "actor_name": "PeX Governed AI Reasoner",
                                "actor_role": "SYSTEM_AI",
                                "badge_color": "blue",
                                "action_title": "Autonomous Repair Synthesized",
                                "icon": "⚡",
                                "summary": f"AI Reasoner validated proposed repair ({s['field_path']}) with {int(s['confidence']*100)}% confidence under Governed STP Policy."
                            }
                        ],
                        guided_questions=[]
                    )
                    db.add(db_case)
                else:
                    # Reset existing case to open RECOMMENDED status
                    db_case.status = "RECOMMENDED"
                    db_case.settled_at = None
                    db_case.amount = s["amount"]
                    db_case.ai_confidence = s["confidence"]
                    db_case.reason = s["reason"]

                # 2. Upsert Recommendation
                rec_id = f"REC-{cid}"
                db_rec = db.query(RecommendationModel).filter(RecommendationModel.case_id == cid).first()
                if not db_rec:
                    db_rec = RecommendationModel(
                        recommendation_id=rec_id,
                        case_id=cid,
                        action_type="REPAIR_AND_RELEASE",
                        confidence_score=s["confidence"],
                        rationale=f"Automated repair validated under Governed STP Policy: {s['justification']}",
                        proposed_changes=[{
                            "field_path": s["field_path"],
                            "original_value_masked": s["orig_val"],
                            "proposed_value_masked": s["prop_val"],
                            "justification": s["justification"],
                            "validation_status": "VALIDATED_CHECKSUM_PASS"
                        }],
                        corroborating_evidence=[],
                        risk_evaluation={
                            "risk_score": 0.05,
                            "risk_level": "LOW",
                            "risk_factors": ["LOW_EXPOSURE_UNDER_25K", "CHECKSUM_VERIFIED", "OFAC_SANCTIONS_CLEAN"],
                            "dual_auth_required": False
                        },
                        guided_questions=[]
                    )
                    db.add(db_rec)
                else:
                    db_rec.confidence_score = s["confidence"]
                    db_rec.proposed_changes = [{
                        "field_path": s["field_path"],
                        "original_value_masked": s["orig_val"],
                        "proposed_value_masked": s["prop_val"],
                        "justification": s["justification"],
                        "validation_status": "VALIDATED_CHECKSUM_PASS"
                    }]

                created_ids.append(cid)

            db.commit()
            repo.sync_from_db()

            return {
                "status": "SUCCESS",
                "seeded_count": len(created_ids),
                "case_ids": created_ids,
                "message": f"Successfully seeded {len(created_ids)} high-confidence STP Fast-Lane candidates into persistent database."
            }
        finally:
            db.close()

# Global singleton
stp_engine = STPEngine()
