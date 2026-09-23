"""Update data_loader.py to include rich audit timelines and pre-populated audit events."""
from pathlib import Path

data_loader_path = Path(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\services\data_loader.py")

content = r'''"""Synthetic Data Loader & In-Memory Relational Repository for PeX."""
import csv
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.config import settings
from app.core.tokenization import token_vault
from app.schemas.canonical import (
    CanonicalPayment, CanonicalException, CanonicalParty, CanonicalAccount,
    LifecycleStage, ExceptionProfile, ExceptionSeverity, ExceptionPriority, CaseSummary
)
from app.schemas.context import PolicyRule, EvidenceItem, HistoricalPrecedent
from app.schemas.recommendation import (
    DecisionRecommendation, ProposedFieldChange, RiskEvaluation, CorroboratingEvidenceRef, ActionType,
    GuidedQuestionItem, StepAssessmentItem, HypothesisRankingItem, AnomalyGuardrailItem, ConsequenceSimulation
)
from app.schemas.approval import ApprovalRecord, ApprovalAction, UserRole
from app.schemas.action import GovernedActionContract, DeliveryReceipt
from app.schemas.audit import AuditEvent
from app.core.hashing import calculate_event_hash

def build_rich_guided_recommendation(case_id: str, profile: ExceptionProfile, amount: float, creditor_name: str, creditor_country: str, case_idx: int) -> DecisionRecommendation:
    severity = ExceptionSeverity.HIGH if amount >= 250000.0 or profile == ExceptionProfile.SANCTIONS_SUSPECTED else ExceptionSeverity.MEDIUM
    if amount >= 1000000.0:
        severity = ExceptionSeverity.CRITICAL

    if profile == ExceptionProfile.INVALID_IBAN:
        action_type = ActionType.REPAIR_IBAN
        conf_score = 0.96
        rationale = "ISO 7064 MOD-97 algorithm resolved 2 transposed digits in the check sequence. Validated against Beneficiary Master Directory."
        proposed_changes = [ProposedFieldChange(
            field_path="creditor_account.iban",
            original_value_masked=f"{creditor_country}82 WEST 1234 5698 7600 00",
            proposed_value_masked=f"{creditor_country}82 WEST 1234 5698 76{case_idx:04d}",
            justification="Beneficiary standing instructions match active counterparty record. MOD-97 checksum verified.",
            validation_status="VALIDATED_MOD97_PASS"
        )]
        guided_questions = [
            GuidedQuestionItem(
                category="DATA INTEGRITY",
                question="Did someone typo the account number, or is this routing to the wrong beneficiary?",
                investigation_tip="Check character transposition diff and Confirmation of Payee (CoP) name match score."
            ),
            GuidedQuestionItem(
                category="REGULATORY CHECK",
                question="Does the repaired IBAN pass MOD-97 math and match the counterparty's Standing Settlement Instructions (SSI)?",
                investigation_tip="Verify ISO 7064 mathematical remainder = 1 and Master Directory active profile status."
            )
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="ISO 7064 MOD-97 Format Check", description="Mathematical remainder test", proof_detail="Raw MOD-97 remainder = 1 (Deterministic Pass)", badge_label="VALIDATED", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Beneficiary Master Directory SSI", description="Standing settlement instruction cross-reference", proof_detail="Matched active profile in SSI Central Directory (Ref #SSI-9912)", badge_label="100% SSI MATCH", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Confirmation of Payee (CoP)", description="Account name verification at receiving bank", proof_detail=f"Beneficiary name '{creditor_name}' matches destination account", badge_label="NAME MATCHED", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Clearing Rail & Currency Fit", description="SWIFT CBPR+ pacs.008 format check", proof_detail="Target bank BIC active and accepts pacs.008 ISO 20022 messages", badge_label="CBPR+ PASS", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Behavioral Anomaly Guardrail", description="Mule account and velocity analysis", proof_detail="Zero velocity anomalies. Established 3.5yr counterparty relationship", badge_label="NO ANOMALIES", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Alphanumeric transposition in check digit sequence", confidence=0.96, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Incompatible domestic routing scheme", confidence=0.04, status="ELIMINATED", elimination_reason="Bank routing identifier is valid and active on national clearing rail")
        ]

    elif profile == ExceptionProfile.INVALID_BIC:
        action_type = ActionType.REPAIR_BIC
        conf_score = 0.94
        rationale = "Target branch BIC was consolidated into Head Office clearing node. Replacement BIC is active on SWIFT CBPR+."
        proposed_changes = [ProposedFieldChange(
            field_path="creditor_account.bank_bic",
            original_value_masked="WESTGB2LXXX",
            proposed_value_masked="WESTGB2L",
            justification="Active SWIFT CBPR+ routing BIC verified in clearing directory.",
            validation_status="VALIDATED_SWIFT_ACTIVE"
        )]
        guided_questions = [
            GuidedQuestionItem(
                category="ROUTING INTEGRITY",
                question="Why is this BIC failing? Has the destination bank merged, closed this branch, or changed clearing rails?",
                investigation_tip="Inspect SWIFT CBPR+ directory lifecycle status and correspondent routing chain."
            ),
            GuidedQuestionItem(
                category="MESSAGE COMPATIBILITY",
                question="Is the proposed replacement BIC capable of receiving pacs.008 cross-border messages?",
                investigation_tip="Verify network capability flags and RMA authorizations."
            )
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="SWIFT Directory Lookup", description="BIC lifecycle and status test", proof_detail="Original branch merged. Replacement Head Office BIC is ACTIVE", badge_label="ACTIVE REPLACEMENT", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Clearing Network Compatibility", description="ISO 20022 pacs.008 capability check", proof_detail="Receiving institution registered for pacs.008.001.08 clearing", badge_label="pacs.008 OK", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="3-Node Routing Chain", description="Correspondent intermediary path", proof_detail="Direct clearing path confirmed via Standard Chartered London", badge_label="ROUTE VERIFIED", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Liquidity & Nostro Verification", description="Outbound corridor liquidity check", proof_detail="Sufficient clearing ledger capacity on EUR/USD Nostro", badge_label="CLEARED", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Fraud & Screening Filter", description="Routing anomaly screening", proof_detail="Zero high-risk routing hops detected", badge_label="LOW RISK", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Branch merged into centralized institution BIC", confidence=0.94, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Deprecated MT103 legacy clearing route", confidence=0.06, status="ELIMINATED", elimination_reason="Target bank has fully cut over to ISO 20022 CBPR+")
        ]

    elif profile == ExceptionProfile.DUPLICATE_PAYMENT:
        action_type = ActionType.SUPPRESS_DUPLICATE if case_idx % 2 == 0 else ActionType.HOLD
        conf_score = 0.91
        rationale = "Instruction references distinct invoice metadata from original transaction. Temporal clustering confirms independent installment."
        proposed_changes = [ProposedFieldChange(
            field_path="remittance_information.invoice_reference",
            original_value_masked="INV-88910",
            proposed_value_masked=f"INV-889{10+case_idx}",
            justification="Purchase order and invoice references are verified distinct.",
            validation_status="VALIDATED_INVOICE_DISTINCT"
        )]
        guided_questions = [
            GuidedQuestionItem(
                category="DUPLICATE TRIAGE",
                question="Is this an accidental duplicate batch retry by client ERP, or two legitimate separate installments?",
                investigation_tip="Check purchase order numbers, invoice references, and submission interval."
            ),
            GuidedQuestionItem(
                category="COMMERCIAL EVIDENCE",
                question="Do both instructions have distinct commercial contracts and separate debit authorizations?",
                investigation_tip="Inspect idempotency key and ledger accounting logs."
            )
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Idempotency Token Check", description="Batch identifier comparison", proof_detail="Distinct client instruction token generated by client ERP", badge_label="DISTINCT KEYS", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Invoice Metadata Disambiguation", description="Purchase order and remittance matching", proof_detail=f"Original referenced INV-88910; this instruction references INV-889{10+case_idx}", badge_label="DISTINCT INVOICE", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Submission Time Delta", description="Interval between payments", proof_detail="Received 18.4 hours apart (Exceeds accidental double-click threshold)", badge_label="TIME INTERVAL OK", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Ledger Debit Precedent", description="Double debit risk scoring", proof_detail="Historical monthly cadence shows bi-monthly installment billing", badge_label="CADENCE MATCH", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Fraud Risk Assessment", description="Synthetic duplicate anomaly check", proof_detail="Beneficiary and debtor confirm active supply contract", badge_label="VERIFIED COMMERCIAL", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Legitimate recurring commercial installment", confidence=0.91, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Accidental ERP automated batch replay", confidence=0.09, status="ELIMINATED", elimination_reason="Distinct invoice identifiers attached to payload")
        ]

    elif profile == ExceptionProfile.SANCTIONS_SUSPECTED:
        action_type = ActionType.CLEAR_FALSE_POSITIVE
        conf_score = 0.89
        rationale = "Fuzzy hit disambiguated: Registration tax ID, incorporation date (2014 vs 1998), and secondary identifiers confirm homonym false positive."
        proposed_changes = [ProposedFieldChange(
            field_path="compliance_screening.disposition",
            original_value_masked="MATCH_SUSPECTED_OFAC",
            proposed_value_masked="CLEARED_FALSE_POSITIVE_HOMONYM",
            justification="Secondary identifiers confirm corporate entity is not the sanctioned party.",
            validation_status="VALIDATED_COMPLIANCE_PASS"
        )]
        guided_questions = [
            GuidedQuestionItem(
                category="SANCTIONS DISAMBIGUATION",
                question="Is this a true match against OFAC / EU watchlists, or a false positive homonym cleared by secondary IDs?",
                investigation_tip="Examine Date of Incorporation, Tax ID, and registered jurisdiction."
            ),
            GuidedQuestionItem(
                category="ADVERSE MEDIA & PEP",
                question="Are there adverse media reports or Politically Exposed Person (PEP) affiliations for this entity?",
                investigation_tip="Review real-time Dow Jones & World-Check screening logs."
            )
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Fuzzy String Match Analysis", description="Levenshtein & Jaro-Winkler analysis", proof_detail="Similarity score: 0.87 against watchlist entity 'Volga Industrial Holdings LLC'", badge_label="SCORE 0.87", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Secondary ID Disambiguation", description="Tax ID and registration number check", proof_detail="Target Tax ID: #AE-9920141 does NOT match sanctioned entity Tax ID", badge_label="TAX ID MISMATCH", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Incorporation Date Verification", description="Entity creation timeline", proof_detail="Client incorporated in 2014; Sanctioned entity established in 1998", badge_label="NON-MATCHING DATE", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="PEP & Adverse Media Scan", description="Global adverse media repository", proof_detail="0 PEP hits, 0 Adverse Media articles detected across 15,000 sources", badge_label="0 HITS", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="UBO Lineage Assessment", description="Ultimate beneficial ownership check", proof_detail="No shareholders with >10% stake appear on global sanctions lists", badge_label="NON-SANCTIONED UBO", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Homonym false positive match cleared by Tax ID & DOB", confidence=0.89, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="True sanctions SDN entity match", confidence=0.11, status="ELIMINATED", elimination_reason="Secondary registration records and incorporation dates completely diverge")
        ]

    elif profile == ExceptionProfile.KYC_EXPIRED:
        action_type = ActionType.GRANT_KYC_WAIVER
        conf_score = 0.92
        rationale = "Documentation gap is technical (Annual Financials expired 60d). UBO structure is unchanged. Eligible for SOP-302 30-day waiver."
        proposed_changes = [ProposedFieldChange(
            field_path="kyc_profile.waiver_status",
            original_value_masked="EXPIRED_PENDING_DOCS",
            proposed_value_masked="GRANTED_30DAY_WAIVER_SOP302",
            justification="Low-risk Tier 2 client granted standard 30-day provisional processing grace period.",
            validation_status="VALIDATED_KYC_WAIVER"
        )]
        guided_questions = [
            GuidedQuestionItem(
                category="KYC MATERIALITY",
                question="Is this a technical documentation expiration eligible for a temporary 30-day waiver (SOP-302), or a material change in UBO?",
                investigation_tip="Verify whether any beneficial ownership changed in the national company registry."
            ),
            GuidedQuestionItem(
                category="RISK TIER CRITERIA",
                question="Does the counterparty risk rating qualify for waiver authorization under institutional policy?",
                investigation_tip="Tier 1 and Tier 2 established corporate clients are eligible for temporary waivers."
            )
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Document Expiry Scope", description="Specific documentation gap", proof_detail="Annual Financial Statement 2024 expired 60d ago. Master KYC on file", badge_label="SCOPE DEFINED", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Beneficial Ownership Audit", description=">25% UBO Shareholder registry audit", proof_detail="Public registry verifies 0 changes in beneficial ownership", badge_label="ZERO UBO CHANGE", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Client Risk Rating Tier", description="Institutional risk classification", proof_detail="Client rated Tier 2 (Established Corporate / Low Default Probability)", badge_label="TIER 2 LOW RISK", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="SOP-302 Exemption Policy", description="Policy waiver criteria check", proof_detail="Transaction meets all 4 criteria for 30-day provisional processing waiver", badge_label="ELIGIBLE WAIVER", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Enhanced Due Diligence (EDD)", description="Documentation refresh workflow", proof_detail="Automated document request issued to client treasury desk", badge_label="QUEUED REFRESH", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Technical documentation lag with low risk profile", confidence=0.92, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Material corporate restructuring requiring hard freeze", confidence=0.08, status="ELIMINATED", elimination_reason="Corporate registration confirms unchanged management and ownership")
        ]

    else:  # RETURNED_PAYMENT
        action_type = ActionType.RETURN_PAYMENT
        conf_score = 0.95
        rationale = "pacs.004 return with code AC01 (Account Closed) paired with original pacs.008 transaction. Net credit computed for client ledger."
        proposed_changes = [ProposedFieldChange(
            field_path="accounting_ledger.disposition",
            original_value_masked="PENDING_RETURN_RECONCILIATION",
            proposed_value_masked=f"CREDIT_ORIGINATOR_NET_{amount-25.0:.2f}",
            justification="Original payment matched. Net refund calculated after $25 return fee deduction.",
            validation_status="VALIDATED_LEDGER_MATCH"
        )]
        guided_questions = [
            GuidedQuestionItem(
                category="RETURN CODE ANALYSIS",
                question="Why did the receiving bank reject this payment via pacs.004 (e.g. AC01 Account Closed)?",
                investigation_tip="Check SWIFT return code reason and receiving institution narrative."
            ),
            GuidedQuestionItem(
                category="LEDGER RECONCILIATION",
                question="Who bears the return charges, and how should the client's debit ledger be credited?",
                investigation_tip="Verify original UETR link, deduction fee schedule ($25.00), and net credit."
            )
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="pacs.004 Return Reason Code", description="Return message parsing", proof_detail="Code AC01 parsed: 'Beneficiary Account Closed / Transferred'", badge_label="AC01 PARSED", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Original Payment Pairing", description="UETR cross-referencing", proof_detail=f"Matched original pacs.008 dispatched 48h prior (UETR-2026-RET-{case_idx:04d}-A8)", badge_label="UETR LINKED", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Return Fee Computation", description="SWIFT return charge deduction", proof_detail="$25.00 return handling fee deducted per interbank agreement", badge_label="$25 DEDUCTED", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Net Refund Balance", description="Calculation of originator refund", proof_detail=f"Net credit amount: ${amount - 25.0:,.2f} ready for client ledger posting", badge_label="NET CALCULATED", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Accounting Ledger Route", description="Direct credit to debtor account", proof_detail="Originator account US89CHAS100200... verified active and open", badge_label="DIRECT REVERSAL", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Closed account return requiring immediate ledger refund", confidence=0.95, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Disputed commercial recall (camt.056)", confidence=0.05, status="ELIMINATED", elimination_reason="Message is an inbound pacs.004 return, not an inquiry or recall")
        ]

    anomaly_guardrails = [
        AnomalyGuardrailItem(guardrail_name="Velocity Spike Check", status="PASS", details="Normal payment frequency (1-4 payments/month to counterparty)"),
        AnomalyGuardrailItem(guardrail_name="Account Age & History", status="PASS", details="Destination account active > 3 years (Not a newly created mule account)"),
        AnomalyGuardrailItem(guardrail_name="Corridor & Currency Fit", status="PASS", details="Established trade corridor with standard clearing rails")
    ]

    consequence_sim = ConsequenceSimulation(
        estimated_settlement_velocity="2.1 seconds",
        cutoff_deadline_status="MEETS 16:00 EST CUTOFF",
        fee_penalty_avoidance="$150.00 late inquiry avoided",
        nostro_liquidity_impact=f"Sufficient Nostro Liquidity ($14.2M available in {creditor_country} Corridor)"
    )

    return DecisionRecommendation(
        recommendation_id=f"REC-{case_id}",
        case_id=case_id,
        action_type=action_type,
        confidence_score=conf_score,
        rationale=rationale,
        proposed_changes=proposed_changes,
        corroborating_evidence=[
            CorroboratingEvidenceRef(evidence_id=f"EVD-BMD-{case_idx:03d}", evidence_type="BENEFICIARY_DIRECTORY", citation="Beneficiary Master Directory SSI match verified."),
            CorroboratingEvidenceRef(evidence_id=f"EVD-SWIFT-{case_idx:03d}", evidence_type="SWIFT_ROUTING", citation="SWIFT CBPR+ clearing tables verified active.")
        ],
        risk_evaluation=RiskEvaluation(
            risk_level=severity,
            risk_score=0.06 if profile in [ExceptionProfile.INVALID_IBAN, ExceptionProfile.INVALID_BIC] else 0.12,
            risk_factors=["Format checks passed", "Counterparty identity grounded in master records"],
            dual_auth_required=amount >= settings.DUAL_AUTH_THRESHOLD
        ),
        guided_questions=guided_questions,
        step_by_step_assessment=step_assessment,
        hypothesis_ranking=hypothesis_ranking,
        anomaly_guardrails=anomaly_guardrails,
        consequence_simulation=consequence_sim,
        applied_policies=["POL-IBAN-AUTO-REPAIR", "POL-HIGH-VALUE-DUAL-AUTH", "POL-SOP-302-WAIVER"],
        model_identifier="mock-governed-reasoner-v1"
    )

class InMemoryRepository:
    def __init__(self):
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.banks: Dict[str, Dict[str, Any]] = {}
        self.bank_source_events: Dict[str, Dict[str, Any]] = {}
        self.beneficiaries: Dict[str, Dict[str, Any]] = {}
        self.evidence: Dict[str, Dict[str, Any]] = {}
        self.exceptions_raw: Dict[str, Dict[str, Any]] = {}
        self.historical_cases: List[Dict[str, Any]] = []
        self.kyc_profiles: Dict[str, Dict[str, Any]] = {}
        self.parties: Dict[str, Dict[str, Any]] = {}
        self.payments_raw: Dict[str, Dict[str, Any]] = {}
        self.policies: List[PolicyRule] = []
        self.reference_data: Dict[str, Dict[str, Any]] = {}
        self.screening_results: Dict[str, List[Dict[str, Any]]] = {}
        self.ground_truth: Dict[str, Dict[str, Any]] = {}
        
        # Active runtime states
        self.cases: Dict[str, Dict[str, Any]] = {}
        self.recommendations: Dict[str, DecisionRecommendation] = {}
        self.approvals: Dict[str, List[ApprovalRecord]] = {}
        self.actions: Dict[str, GovernedActionContract] = {}
        self.receipts: Dict[str, DeliveryReceipt] = {}
        self.audit_log: List[AuditEvent] = []
        self.latest_chain_hash: str = "0000000000000000000000000000000000000000000000000000000000000000"

    def _read_csv(self, file_path: Path) -> List[Dict[str, str]]:
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return [dict(row) for row in reader]

    def load_all_data(self):
        data_dir = settings.DATA_DIR
        if not data_dir.exists():
            print(f"Warning: Synthetic data directory not found at {data_dir}")
            return

        # 1. Token Map
        token_rows = self._read_csv(data_dir / "token_map.csv")
        token_vault.preload_tokens(token_rows)

        # 2. Reference Data & Banks
        for row in self._read_csv(data_dir / "reference_data.csv"):
            key = row.get("ref_key") or row.get("id") or str(len(self.reference_data))
            self.reference_data[key] = row
            
        for row in self._read_csv(data_dir / "banks.csv"):
            self.banks[row.get("bank_id", "")] = row

        # 3. Parties & Accounts & Beneficiaries
        for row in self._read_csv(data_dir / "parties.csv"):
            self.parties[row.get("party_id", "")] = row
            
        for row in self._read_csv(data_dir / "accounts.csv"):
            self.accounts[row.get("account_id", "")] = row

        for row in self._read_csv(data_dir / "beneficiaries.csv"):
            b_id = row.get("beneficiary_id") or row.get("id", "")
            self.beneficiaries[b_id] = row

        # 4. KYC & Screening
        for row in self._read_csv(data_dir / "kyc_profiles.csv"):
            self.kyc_profiles[row.get("party_id", "")] = row

        for row in self._read_csv(data_dir / "screening_results.csv"):
            pid = row.get("party_id", "")
            if pid not in self.screening_results:
                self.screening_results[pid] = []
            self.screening_results[pid].append(row)

        # 5. Policies
        for row in self._read_csv(data_dir / "policies.csv"):
            prof_str = row.get("exception_profile") or row.get("profile", "INVALID_IBAN")
            try:
                prof = ExceptionProfile(prof_str)
            except Exception:
                prof = ExceptionProfile.INVALID_IBAN
            
            mand_str = row.get("mandatory_evidence") or row.get("evidence_required", "")
            mand_list = [e.strip() for e in mand_str.split(",") if e.strip()] if mand_str else ["BENEFICIARY_PROFILE", "ACCOUNT_DIRECTORY"]
            
            rule = PolicyRule(
                policy_id=row.get("policy_id", f"POL-{len(self.policies)+1}"),
                profile=prof,
                rule_code=row.get("rule_code", "POL-DEF-01"),
                rule_description=row.get("rule_description", row.get("description", "Governed Exception Policy")),
                mandatory_evidence=mand_list,
                auto_repair_eligible=row.get("auto_repair_eligible", "false").lower() == "true",
                max_amount_threshold=float(row.get("max_amount_threshold", "1000000.0")),
                required_confidence_threshold=float(row.get("required_confidence_threshold", "0.85"))
            )
            self.policies.append(rule)

        # 6. Historical Cases
        self.historical_cases = self._read_csv(data_dir / "historical_cases.csv")

        # 7. Ground Truth
        for row in self._read_csv(data_dir / "evaluation_ground_truth.csv"):
            self.ground_truth[row.get("case_id", "")] = row

        # 8. Bank Source Events & Payments & Exceptions
        for row in self._read_csv(data_dir / "bank_source_events.csv"):
            self.bank_source_events[row.get("event_id", "")] = row

        for row in self._read_csv(data_dir / "payments.csv"):
            self.payments_raw[row.get("payment_id", "")] = row

        for row in self._read_csv(data_dir / "exceptions.csv"):
            self.exceptions_raw[row.get("exception_id", "")] = row

        # Initialize 50 Curated Test Cases across 6 Exception Profiles & Stages
        self._initialize_50_test_cases()
        print(f"Loaded {len(self.cases)} curated live cases across all 6 exception profiles & approval stages.")

    def _append_audit_event(self, case_id: str, correlation_id: str, stage_name: str, actor_id: str, actor_role: str, action_name: str, details: str, control_tags: List[str]):
        event_index = len(self.audit_log) + 1
        prev_hash = self.latest_chain_hash
        timestamp = datetime.utcnow()
        curr_hash = calculate_event_hash(
            event_index=event_index,
            timestamp_iso=timestamp.isoformat(),
            case_id=case_id,
            stage_name=stage_name,
            actor_id=actor_id,
            action_name=action_name,
            details=details,
            prev_hash=prev_hash
        )
        event = AuditEvent(
            event_index=event_index,
            timestamp=timestamp,
            case_id=case_id,
            correlation_id=correlation_id,
            stage_name=stage_name,
            actor_id=actor_id,
            actor_role=actor_role,
            action_name=action_name,
            details=details,
            control_tags=control_tags,
            prev_hash=prev_hash,
            current_hash=curr_hash
        )
        self.audit_log.append(event)
        self.latest_chain_hash = curr_hash

    def _initialize_50_test_cases(self):
        # Reset runtime collections to prevent duplicate increments across server restarts
        self.cases.clear()
        self.recommendations.clear()
        self.approvals.clear()
        self.audit_log.clear()
        self.latest_chain_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        PROFILES_SPECS = [
            {"p": ExceptionProfile.INVALID_IBAN, "q": "Repair", "c": "Nordhavn Components A/S", "co": "GB", "d": "Acme Global Holdings", "ccy": "USD", "r": "Beneficiary account identifier failed MOD-97 check validation against clearing directory.", "err": "ERR_IBAN_MOD97"},
            {"p": ExceptionProfile.INVALID_BIC, "q": "Repair", "c": "St. Gallen Precision AG", "co": "CH", "d": "Apex Logistics Group", "ccy": "EUR", "r": "Receiving BIC not found in SWIFT CBPR+ routing table or national clearing directory.", "err": "ERR_BIC_ROUTING"},
            {"p": ExceptionProfile.DUPLICATE_PAYMENT, "q": "Investigation", "c": "Cedar Grove Partners", "co": "SG", "d": "Meridian Maritime LLC", "ccy": "SGD", "r": "Identical amount, counterparty, and reference received within rolling 24-hour settlement window.", "err": "ERR_DUPLICATE_24H"},
            {"p": ExceptionProfile.SANCTIONS_SUSPECTED, "q": "Compliance", "c": "Volga Heavy Machinery OJSC", "co": "AE", "d": "OmniCorp Global Energy", "ccy": "USD", "r": "Beneficiary party matched OFAC/EU consolidated watchlist entity (Fuzzy Score >= 0.85).", "err": "ERR_SANCTIONS_MATCH"},
            {"p": ExceptionProfile.KYC_EXPIRED, "q": "Compliance", "c": "Vanguard Minerals Ltd", "co": "AU", "d": "Titan Financial Services", "ccy": "AUD", "r": "Counterparty KYC periodic review date is past due. Regulatory documentation update required.", "err": "ERR_KYC_PERIODIC_DUE"},
            {"p": ExceptionProfile.RETURNED_PAYMENT, "q": "Investigation", "c": "Kyoto Industrial Systems", "co": "JP", "d": "Atlas Trade Finance", "ccy": "JPY", "r": "Inbound pacs.004 return received from receiving institution with reason code AC01 (Account Closed).", "err": "ERR_PACS004_AC01"}
        ]

        amounts_pool = [
            18500.0, 42000.0, 89500.0, 125000.0, 168400.0, 215000.0,
            285000.0, 350000.0, 480000.0, 650000.0, 1200000.0, 2450000.0, 3274920.10
        ]

        total_records = 50
        for i in range(1, total_records + 1):
            prof_info = PROFILES_SPECS[(i - 1) % len(PROFILES_SPECS)]
            profile = prof_info["p"]
            queue = prof_info["q"]
            reason = prof_info["r"]
            err_code = prof_info["err"]
            creditor_name = prof_info["c"]
            creditor_country = prof_info["co"]
            debtor_name = prof_info["d"]
            currency = prof_info["ccy"]

            case_id = f"PEX-{profile.value[:3]}-{i:04d}"
            payment_id = f"PMT-{i:04d}"
            uetr = f"UETR-2026-{profile.value[:3]}-{i:04d}-A8"
            payment_ref = f"CLIENT-REF-{2026000 + i}"

            base_amount = amounts_pool[(i * 3) % len(amounts_pool)]
            amount = base_amount

            # Stage distribution
            if i in [1, 2, 3, 4, 13, 14, 19, 20, 25, 26, 31, 32]:
                status = LifecycleStage.INGESTED
            elif i in [7, 15, 21, 27, 33, 39]:
                status = LifecycleStage.AWAITING_SECOND_APPROVAL
                amount = max(amount, 350000.0)  # High value for Dual-Auth
            elif i in [11, 23, 35, 47]:
                status = LifecycleStage.APPROVED
            elif i in [5, 6, 8, 9, 10, 12, 16, 17, 18, 22, 24, 28, 29, 30, 34, 36]:
                status = LifecycleStage.PENDING_APPROVAL
            else:
                status = LifecycleStage.SETTLED

            severity = ExceptionSeverity.MEDIUM
            if amount >= 250000.0 or profile == ExceptionProfile.SANCTIONS_SUSPECTED:
                severity = ExceptionSeverity.HIGH
            if amount >= 1000000.0:
                severity = ExceptionSeverity.CRITICAL

            priority = ExceptionPriority.NORMAL
            if severity in [ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL]:
                priority = ExceptionPriority.HIGH
            if amount >= 1000000.0:
                priority = ExceptionPriority.CRITICAL

            sla_due = datetime.utcnow() + timedelta(hours=1, minutes=30 + (i % 30))

            debtor_tok = token_vault.tokenize(debtor_name, "PARTY")
            creditor_tok = token_vault.tokenize(creditor_name, "PARTY")

            approval_hist = []
            approvals_list: List[ApprovalRecord] = []
            audit_timeline = []

            # Step 1: Ingestion
            t_ingest = (datetime.utcnow() - timedelta(minutes=i * 8 + 45)).isoformat()
            audit_timeline.append({
                "step_index": 1,
                "timestamp": t_ingest,
                "actor_name": "PeX Ingestion Gateway",
                "actor_role": "SYSTEM",
                "badge_color": "slate",
                "action_title": "Exception Ingested & Canonicalized",
                "icon": "📥",
                "summary": f"Payment instruction received via SWIFT / CBPR+. PII tokenized in isolated vault."
            })
            self._append_audit_event(
                case_id=case_id,
                correlation_id=uetr,
                stage_name="INGESTION",
                actor_id="PEX-GATEWAY",
                actor_role="SYSTEM",
                action_name="INGEST_AND_CANONICALIZE",
                details=f"Payment exception {case_id} ingested. Tokenized PII vault reference created.",
                control_tags=["Schema valid", "Token vault isolated", "ISO 20022 canonicalized"]
            )

            # Step 2: AI Repair Context Assembly
            if status != LifecycleStage.INGESTED or i % 2 == 0:
                t_ai = (datetime.utcnow() - timedelta(minutes=i * 8 + 30)).isoformat()
                audit_timeline.append({
                    "step_index": 2,
                    "timestamp": t_ai,
                    "actor_name": "Priya Nair",
                    "actor_role": "OPERATOR (MAKER)",
                    "badge_color": "blue",
                    "action_title": "AI Repair Triggered & Grounded",
                    "icon": "⚡",
                    "summary": f"Analyst ran AI Reasoner. Generated MOD-97 checksum fix and SSI master directory match."
                })
                self._append_audit_event(
                    case_id=case_id,
                    correlation_id=uetr,
                    stage_name="ANALYST_REPAIR",
                    actor_id="OP-9012",
                    actor_role="OPERATOR",
                    action_name="RUN_AI_REPAIR",
                    details=f"Analyst Priya Nair triggered AI reasoner. Generated ISO 7064 MOD-97 proposal.",
                    control_tags=["Evidence grounded", "MOD-97 remainder = 1", "Maker review in progress"]
                )

            # Step 3: Rework Cycle (for specific cases to illustrate return loop)
            if i in [5, 7, 15, 21, 27, 33]:
                t_rework = (datetime.utcnow() - timedelta(minutes=i * 8 + 20)).isoformat()
                audit_timeline.append({
                    "step_index": 3,
                    "timestamp": t_rework,
                    "actor_name": "Daniel Osei",
                    "actor_role": "OPERATIONS_APPROVER",
                    "badge_color": "amber",
                    "action_title": "Returned to Maker for Rework",
                    "icon": "⚠️",
                    "summary": "Approver 1 requested clarification: 'Please confirm revised commercial invoice #INV-88911 with client treasury.'"
                })
                self._append_audit_event(
                    case_id=case_id,
                    correlation_id=uetr,
                    stage_name="HITL_APPROVAL",
                    actor_id="APR-3191",
                    actor_role="OPERATIONS_APPROVER",
                    action_name="RETURN_TO_MAKER",
                    details=f"Approver Daniel Osei returned case {case_id} to Maker for invoice re-verification.",
                    control_tags=["Rework cycle logged", "Audit comment captured"]
                )

                t_resub = (datetime.utcnow() - timedelta(minutes=i * 8 + 12)).isoformat()
                audit_timeline.append({
                    "step_index": 4,
                    "timestamp": t_resub,
                    "actor_name": "Priya Nair",
                    "actor_role": "OPERATOR (MAKER)",
                    "badge_color": "blue",
                    "action_title": "Rework Completed & Re-submitted",
                    "icon": "✍️",
                    "summary": "Analyst verified revised invoice #INV-88911 with client treasury. Re-submitted to Checker Approvals Queue."
                })
                self._append_audit_event(
                    case_id=case_id,
                    correlation_id=uetr,
                    stage_name="MAKER_SUBMISSION",
                    actor_id="OP-9012",
                    actor_role="OPERATOR",
                    action_name="RESUBMIT_TO_CHECKER",
                    details=f"Maker Priya Nair confirmed revised invoice and re-submitted case {case_id}.",
                    control_tags=["Segregation of duties active", "Pending Level 1 sign-off"]
                )

            # Step 4: Level 1 Approval (if in Awaiting Dual Auth, Approved, Settled)
            if status in [LifecycleStage.AWAITING_SECOND_APPROVAL, LifecycleStage.APPROVED, LifecycleStage.SETTLED]:
                t_l1 = (datetime.utcnow() - timedelta(minutes=i * 8 + 6)).isoformat()
                rec1 = ApprovalRecord(
                    approval_id=f"APR-{i:04d}-S1",
                    case_id=case_id,
                    recommendation_id=f"REC-{case_id}",
                    approver_id="APR-3191",
                    approver_name="Daniel Osei",
                    approver_role=UserRole.OPERATIONS_APPROVER,
                    action=ApprovalAction.APPROVE,
                    comments=f"Level 1 operational verification approved for {profile.value}. MOD-97 math remainder and Master SSI directory matched.",
                    step_number=1,
                    approved_changes=[],
                    created_at=datetime.utcnow() - timedelta(minutes=40)
                )
                approvals_list.append(rec1)
                approval_hist.append(rec1.dict())
                audit_timeline.append({
                    "step_index": len(audit_timeline) + 1,
                    "timestamp": t_l1,
                    "actor_name": "Daniel Osei",
                    "actor_role": "OPERATIONS_APPROVER",
                    "badge_color": "emerald",
                    "action_title": "Level 1 Operational Sign-off Approved",
                    "icon": "🛡️",
                    "summary": f"Level 1 operational verification approved. MOD-97 remainder and SSI match verified."
                })
                self._append_audit_event(
                    case_id=case_id,
                    correlation_id=uetr,
                    stage_name="HITL_APPROVAL",
                    actor_id="APR-3191",
                    actor_role="OPERATIONS_APPROVER",
                    action_name="APPROVAL_APPROVE",
                    details=f"Level 1 operational repair authorized by Daniel Osei.",
                    control_tags=["Level 1 sign-off complete", "MOD-97 verified"]
                )

            # Step 5: Level 2 Dual Authorization (if Approved or Settled and >= $250k)
            if (status in [LifecycleStage.APPROVED, LifecycleStage.SETTLED] and amount >= 250000.0):
                t_l2 = (datetime.utcnow() - timedelta(minutes=i * 8 + 3)).isoformat()
                rec2 = ApprovalRecord(
                    approval_id=f"APR-{i:04d}-S2",
                    case_id=case_id,
                    recommendation_id=f"REC-{case_id}",
                    approver_id="CMP-4420" if queue == "Compliance" else "RSK-7714",
                    approver_name="Marisol Vega" if queue == "Compliance" else "Kenji Watanabe",
                    approver_role=UserRole.COMPLIANCE_APPROVER if queue == "Compliance" else UserRole.RISK_APPROVER,
                    action=ApprovalAction.APPROVE,
                    comments="Tier 2 High-Value Dual Authorization authorized. Nostro corridor limits verified.",
                    step_number=2,
                    approved_changes=[],
                    created_at=datetime.utcnow() - timedelta(minutes=20)
                )
                approvals_list.append(rec2)
                approval_hist.append(rec2.dict())
                audit_timeline.append({
                    "step_index": len(audit_timeline) + 1,
                    "timestamp": t_l2,
                    "actor_name": "Kenji Watanabe" if queue != "Compliance" else "Marisol Vega",
                    "actor_role": "RISK_APPROVER" if queue != "Compliance" else "COMPLIANCE_APPROVER",
                    "badge_color": "purple",
                    "action_title": "Level 2 Dual Authorization Authorized",
                    "icon": "🔒",
                    "summary": "Tier-2 High-Value Dual Authorization signed off. Nostro corridor limits verified."
                })
                self._append_audit_event(
                    case_id=case_id,
                    correlation_id=uetr,
                    stage_name="HITL_APPROVAL",
                    actor_id="RSK-7714",
                    actor_role="RISK_APPROVER",
                    action_name="APPROVAL_DUAL_AUTH",
                    details=f"Tier 2 Dual Authorization signed off by Kenji Watanabe for high-value dispatch.",
                    control_tags=["Dual-auth complete", "Nostro limits verified"]
                )

            # Step 6: Settlement Dispatch (if Settled)
            if status == LifecycleStage.SETTLED:
                t_settle = (datetime.utcnow() - timedelta(minutes=i * 8)).isoformat()
                audit_timeline.append({
                    "step_index": len(audit_timeline) + 1,
                    "timestamp": t_settle,
                    "actor_name": "PeX Settlement Kernel",
                    "actor_role": "SYSTEM",
                    "badge_color": "emerald",
                    "action_title": "Governed Settlement Dispatched & Reconciled",
                    "icon": "✓",
                    "summary": f"Transaction sealed with SHA-256 block hash. Bank Receipt: ACK-SIM-{profile.value[:3]}-{i:04d}."
                })
                self._append_audit_event(
                    case_id=case_id,
                    correlation_id=uetr,
                    stage_name="SETTLEMENT",
                    actor_id="PEX-KERNEL",
                    actor_role="SYSTEM",
                    action_name="DISPATCH_AND_SETTLE",
                    details=f"Transaction cryptographically sealed. Bank Acknowledgement Receipt generated: ACK-SIM-{profile.value[:3]}-{i:04d}.",
                    control_tags=["SHA-256 sealed", "Ledger reconciled", "External rail ACK received"]
                )

            if approvals_list:
                self.approvals[case_id] = approvals_list

            case_obj = {
                "case_id": case_id,
                "payment_id": payment_id,
                "uetr": uetr,
                "payment_ref": payment_ref,
                "profile": profile,
                "error_code": err_code,
                "reason": reason,
                "amount": amount,
                "currency": currency,
                "payment_rail": "SWIFT / CBPR+" if i % 2 == 0 else "ISO 20022 pacs.008",
                "debtor_party": {
                    "party_id": f"PARTY-D-{i:03d}",
                    "party_name": debtor_name,
                    "country": "US",
                    "party_type": "DEBTOR",
                    "token_ref": debtor_tok
                },
                "debtor_account": {
                    "account_id": f"ACC-D-{i:03d}",
                    "account_number": f"100200300{i:02d}",
                    "iban": f"US89CHAS100200300{i:02d}12",
                    "currency": currency,
                    "bank_bic": "CHASUS33"
                },
                "creditor_party": {
                    "party_id": f"PARTY-C-{i:03d}",
                    "party_name": creditor_name,
                    "country": creditor_country,
                    "party_type": "CREDITOR",
                    "token_ref": creditor_tok
                },
                "creditor_account": {
                    "account_id": f"ACC-C-{i:03d}",
                    "account_number": f"9876{i:04d}",
                    "iban": f"{creditor_country}82WEST1234569876{i:04d}",
                    "currency": currency,
                    "bank_bic": "WESTGB2L"
                },
                "queue": queue,
                "status": status,
                "severity": severity,
                "priority": priority,
                "sla_due_at": sla_due,
                "dual_auth_required": amount >= settings.DUAL_AUTH_THRESHOLD,
                "ai_confidence": 0.96 if profile in [ExceptionProfile.INVALID_IBAN, ExceptionProfile.INVALID_BIC] else 0.88,
                "created_at": datetime.utcnow() - timedelta(minutes=i * 8),
                "approval_history": approval_hist,
                "audit_timeline": audit_timeline
            }
            self.cases[case_id] = case_obj

            self.recommendations[case_id] = build_rich_guided_recommendation(
                case_id=case_id,
                profile=profile,
                amount=amount,
                creditor_name=creditor_name,
                creditor_country=creditor_country,
                case_idx=i
            )

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self.cases.get(case_id)

    def save_case(self, case_obj: Dict[str, Any]):
        self.cases[case_obj["case_id"]] = case_obj

    def list_cases(
        self,
        queue: Optional[str] = None,
        status: Optional[str] = None,
        profile: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = list(self.cases.values())
        if queue and queue != "All" and queue != "All Queues":
            results = [c for c in results if c.get("queue") == queue]
        if status and status != "All" and status != "All Statuses":
            results = [c for c in results if c.get("status") == status or c.get("status", "").value == status]
        if profile and profile != "All" and profile != "All Types":
            results = [c for c in results if str(c.get("profile")) == profile or c.get("profile", "").value == profile]
        if search:
            s = search.lower()
            results = [
                c for c in results if
                s in c.get("case_id", "").lower() or
                s in c.get("uetr", "").lower() or
                s in c.get("payment_ref", "").lower() or
                s in c.get("creditor_party", {}).get("party_name", "").lower() or
                s in c.get("debtor_party", {}).get("party_name", "").lower()
            ]
        results.sort(key=lambda x: (1 if x.get("status") == LifecycleStage.SETTLED else 0, -x.get("amount", 0)))
        return results

repo = InMemoryRepository()
repo.load_all_data()
'''

with open(data_loader_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("data_loader.py updated with rich audit timelines!")
