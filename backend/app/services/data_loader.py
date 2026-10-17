"""Synthetic Data Loader & In-Memory Relational Repository for PeX across all 41 Market Profiles."""
import csv
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.config import settings
from app.core.tokenization import token_vault
from app.schemas.canonical import (
    CanonicalPayment, CanonicalException, CanonicalParty, CanonicalAccount,
    LifecycleStage, ExceptionProfile, ExceptionDomain, ExceptionSeverity, ExceptionPriority, CaseSummary,
    get_domain_for_profile
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

# Benchmark reference lists across all 41 Market Profiles and 5 Domains
all_profiles = [
    # Data Quality (9)
    ExceptionProfile.INVALID_IBAN, ExceptionProfile.INVALID_BIC, ExceptionProfile.MISSING_BENEFICIARY_DATA,
    ExceptionProfile.MISSING_REMITTANCE_INFO, ExceptionProfile.INVALID_ADDRESS_FORMAT, ExceptionProfile.MISSING_PURPOSE_CODE,
    ExceptionProfile.INVALID_ACCOUNT_NUMBER, ExceptionProfile.INVALID_ROUTING_CODE, ExceptionProfile.BENEFICIARY_NAME_MISMATCH,
    # Processing (9)
    ExceptionProfile.DUPLICATE_PAYMENT, ExceptionProfile.ROUTING_FAILURE, ExceptionProfile.ISO20022_VALIDATION_ERROR,
    ExceptionProfile.CUTOFF_MISSED, ExceptionProfile.CORRUPTED_MESSAGE_FORMAT, ExceptionProfile.INTERMEDIARY_BANK_REJECTION,
    ExceptionProfile.NETWORK_TIMEOUT, ExceptionProfile.QUEUE_PROCESSING_FAILURE, ExceptionProfile.PAYMENT_HELD_FOR_REPAIR,
    # Compliance (8)
    ExceptionProfile.SANCTIONS_SUSPECTED, ExceptionProfile.AML_ALERT, ExceptionProfile.PEP_MATCH,
    ExceptionProfile.RESTRICTED_CORRIDOR, ExceptionProfile.ADVERSE_MEDIA_MATCH, ExceptionProfile.HIGH_RISK_JURISDICTION,
    ExceptionProfile.REGULATORY_REPORTING_REQUIRED, ExceptionProfile.CUSTOMER_WATCHLIST_MATCH,
    # Client / Treasury (8)
    ExceptionProfile.KYC_EXPIRED, ExceptionProfile.INSUFFICIENT_FUNDS, ExceptionProfile.NOSTRO_SHORTFALL,
    ExceptionProfile.FX_RATE_UNAVAILABLE, ExceptionProfile.AUTHORIZATION_MISSING, ExceptionProfile.LIMIT_BREACH,
    ExceptionProfile.LIQUIDITY_CONSTRAINT, ExceptionProfile.CREDIT_EXPOSURE_BREACH,
    # Settlement / Returns (7)
    ExceptionProfile.RETURNED_PAYMENT, ExceptionProfile.ACCOUNT_CLOSED, ExceptionProfile.BENEFICIARY_ACCOUNT_FROZEN,
    ExceptionProfile.RECONCILIATION_BREAK, ExceptionProfile.SETTLEMENT_FAILURE, ExceptionProfile.FUNDS_TRAPPED_AT_CORRESPONDENT,
    ExceptionProfile.UNMATCHED_CREDIT
]

counterparties = [
    ("Nordhavn Components A/S", "GB", "GBP", "BARCGB22XXX"),
    ("HarborView Supplier Ltd", "GB", "USD", "WESTGB2L"),
    ("Apex Global Treasury", "US", "USD", "CHASUS33XXX"),
    ("Kyoto Precision Robotics", "JP", "JPY", "BOTKJPJTXXX"),
    ("Vanguard BioPharma GmbH", "DE", "EUR", "DEUTDEDDXXX"),
    ("Sydney Infrastructure Ltd", "AU", "AUD", "ANZBAU3MXXX"),
    ("Atlas Mediterranean Marine", "GR", "EUR", "NBGRGRAAXXX"),
    ("Zurich Tech Logistics AG", "CH", "CHF", "UBSWCHZHXXX"),
    ("Bavaria Engine Works AG", "DE", "EUR", "HYVEDEMMXXX"),
    ("Singapore FinTech Holding", "SG", "SGD", "DBSSSGSGXXX")
]

def build_rich_guided_recommendation(case_id: str, profile: ExceptionProfile, amount: float, creditor_name: str, creditor_country: str, case_idx: int) -> DecisionRecommendation:
    domain = get_domain_for_profile(profile)
    severity = ExceptionSeverity.HIGH if amount >= 250000.0 or domain == ExceptionDomain.COMPLIANCE else ExceptionSeverity.MEDIUM
    if amount >= 1000000.0:
        severity = ExceptionSeverity.CRITICAL

    # Default fallbacks
    action_type = ActionType.REPAIR_DATA
    conf_score = 0.92
    rationale = f"Evaluated under BIAN {domain.value} standard operating procedure."
    proposed_changes = []
    guided_questions = []
    step_assessment = []
    hypothesis_ranking = []

    # ==================== DOMAIN 1: DATA QUALITY ====================
    if profile == ExceptionProfile.INVALID_IBAN:
        action_type = ActionType.REPAIR_IBAN
        conf_score = 0.96
        rationale = "ISO 7064 MOD-97 algorithm resolved 2 transposed digits in the check sequence. Validated against Beneficiary Master Directory [SIMULATED]."
        
        # P0-5 Reconciled Pair: original invalid (rem 49), repair valid (rem 1)
        orig_clean = f"{creditor_country}82WEST12345698765423"
        repair_clean = f"{creditor_country}82WEST12345698765432"
        rearranged = repair_clean[4:] + repair_clean[:4]
        num_str = "".join(ch if ch.isdigit() else str(ord(ch) - 55) for ch in rearranged)
        rem = int(num_str) % 97

        proposed_changes = [ProposedFieldChange(
            field_path="creditor_account.iban",
            original_value_masked=f"{creditor_country}82 WEST 1234 5698 7654 23",
            proposed_value_masked=f"{creditor_country}82 WEST 1234 5698 7654 32",
            justification=f"Beneficiary standing instructions match active counterparty record. MOD-97 checksum verified (remainder = {rem}).",
            validation_status="VALIDATED_MOD97_PASS"
        )]
        guided_questions = [
            GuidedQuestionItem(category="DATA INTEGRITY", question="Did someone typo the account number, or is this routing to the wrong beneficiary?", investigation_tip="Check character transposition diff and Confirmation of Payee (CoP) name match score."),
            GuidedQuestionItem(category="REGULATORY CHECK", question="Does the repaired IBAN pass MOD-97 math and match the counterparty's Standing Settlement Instructions (SSI)?", investigation_tip="Verify ISO 7064 mathematical remainder = 1 and Master Directory active profile status.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="ISO 7064 MOD-97 Format Check", description="Mathematical remainder test", proof_detail=f"Raw MOD-97 remainder = {rem} (Deterministic Pass)", badge_label="VALIDATED", is_passed=(rem == 1)),
            StepAssessmentItem(step_number=2, step_title="Beneficiary Master Directory SSI [SIMULATED]", description="Standing settlement instruction cross-reference", proof_detail="Matched active profile in SSI Central Directory (Ref #SSI-9912) [SIMULATED]", badge_label="100% SSI MATCH", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Confirmation of Payee (CoP) [SIMULATED]", description="Account name verification at receiving bank", proof_detail=f"Beneficiary name '{creditor_name}' matches destination account [SIMULATED]", badge_label="NAME MATCHED", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Clearing Rail & Currency Fit", description="SWIFT CBPR+ pacs.008 format check", proof_detail="Target bank BIC active and accepts pacs.008 ISO 20022 messages", badge_label="CBPR+ PASS", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Behavioral Anomaly Guardrail [SIMULATED]", description="Mule account and velocity analysis", proof_detail="Zero velocity anomalies. Established 3.5yr counterparty relationship [SIMULATED]", badge_label="NO ANOMALIES", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Alphanumeric transposition in check digit sequence [SIMULATED]", confidence=0.96, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Incompatible domestic routing scheme [SIMULATED]", confidence=0.03, status="ELIMINATED", elimination_reason="Bank routing identifier is valid and active on national clearing rail"),
            HypothesisRankingItem(hypothesis_id="HYP-3", title="Counterparty account closure / de-registration [SIMULATED]", confidence=0.01, status="ELIMINATED", elimination_reason="Beneficiary master SSI registry (#SSI-9912) confirms active account status with good standing")
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
            GuidedQuestionItem(category="ROUTING INTEGRITY", question="Why is this BIC failing? Has the destination bank merged, closed this branch, or changed clearing rails?", investigation_tip="Inspect SWIFT CBPR+ directory lifecycle status and correspondent routing chain."),
            GuidedQuestionItem(category="MESSAGE COMPATIBILITY", question="Is the proposed replacement BIC capable of receiving pacs.008 cross-border messages?", investigation_tip="Verify network capability flags and RMA authorizations.")
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

    elif profile == ExceptionProfile.BENEFICIARY_NAME_MISMATCH:
        action_type = ActionType.REPAIR_DATA
        conf_score = 0.91
        rationale = f"Confirmation of Payee (CoP) partial match (92.4%). Two active corporate accounts verified for '{creditor_name}' in master registry."
        proposed_changes = [ProposedFieldChange(
            field_path="creditor_party.party_name",
            original_value_masked="Acme Tech",
            proposed_value_masked=creditor_name,
            justification="Confirmation of Payee (CoP) verified legal entity name from company register.",
            validation_status="VALIDATED_COP_MATCH"
        )]
        guided_questions = [
            GuidedQuestionItem(category="NAME VERIFICATION", question="Is this a genuine corporate trading name discrepancy or an authorized redirection attempt?", investigation_tip="Cross-examine corporate registry trading names and secondary tax IDs."),
            GuidedQuestionItem(category="ACCOUNT DISAMBIGUATION", question="Which active corporate account is requested for this settlement tranche?", investigation_tip="Commercial invoice references Operating IBAN; Treasury mandate references Sweeping IBAN.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Confirmation of Payee (CoP) Score", description="Fuzzy name matching algorithm", proof_detail="Jaro-Winkler similarity = 0.924 (Close Match Pass)", badge_label="CoP 92.4%", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Company Registry Verification", description="Official legal name lookup", proof_detail="Registered trading name confirmed in UK Companies House", badge_label="REGISTRY MATCH", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Multi-Account Registry Query", description="Beneficiary master account directory", proof_detail="2 active authorized accounts detected for Nordhavn Components A/S", badge_label="2 ACCOUNTS ACTIVE", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Debtor AP Match", description="Accounts payable ledger tie-out", proof_detail="Invoice #INV-2026-88 matches debtor approved PO", badge_label="PO VERIFIED", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Mule Account Filter", description="Authorized Push Payment (APP) check", proof_detail="Zero fraud or rapid depletion flags on destination accounts", badge_label="SAFE ACCOUNTS", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(
                hypothesis_id="HYP-1",
                title=f"Primary Commercial Operating IBAN (London Branch)",
                confidence=0.924,
                status="ELIGIBLE_CANDIDATE",
                candidate_value="GB82 WEST 1234 5698 7602",
                candidate_description="Main operational trading account on file with 14 settled disbursements."
            ),
            HypothesisRankingItem(
                hypothesis_id="HYP-2",
                title=f"Corporate Treasury Sweeping IBAN (Edinburgh Node)",
                confidence=0.898,
                status="ELIGIBLE_CANDIDATE",
                candidate_value="GB82 WEST 1234 5698 9914",
                candidate_description="Secondary liquidity pooling account on file with active standing authorization."
            ),
            HypothesisRankingItem(
                hypothesis_id="HYP-3",
                title="Impersonation / Invoice Redirection Fraud",
                confidence=0.012,
                status="ELIMINATED",
                elimination_reason="Account tenure > 4 years with 28 prior settled payments"
            )
        ]

    elif profile in [ExceptionProfile.MISSING_BENEFICIARY_DATA, ExceptionProfile.MISSING_REMITTANCE_INFO, ExceptionProfile.INVALID_ADDRESS_FORMAT, ExceptionProfile.MISSING_PURPOSE_CODE, ExceptionProfile.INVALID_ACCOUNT_NUMBER, ExceptionProfile.INVALID_ROUTING_CODE]:
        action_type = ActionType.REPAIR_DATA
        conf_score = 0.93
        rationale = f"Enriched mandatory ISO 20022 elements from verified counterparty KYC vault under SOP-114."
        proposed_changes = [ProposedFieldChange(
            field_path="creditor_party.postal_address",
            original_value_masked="Unstructured Address Line",
            proposed_value_masked="100 Bishopsgate, London EC2N 4AG, GB",
            justification="Structured postal address elements mapped to CBPR+ standard.",
            validation_status="VALIDATED_SCHEMA_ENRICHED"
        )]
        guided_questions = [
            GuidedQuestionItem(category="DATA ENRICHMENT", question="Can missing or malformed tags be deterministically enriched from master static data?", investigation_tip="Verify verified static data vault references and CBPR+ schema requirements."),
            GuidedQuestionItem(category="REGULATORY CLEARANCE", question="Does the enriched message comply with destination country central bank mandates?", investigation_tip="Check clearing rail mandatory tag tables.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Schema Tag Completeness", description="ISO 20022 tag structure check", proof_detail="Structured postal elements populated according to CBPR+ specs", badge_label="SCHEMA VALID", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Master Static Data Match", description="Customer profile cross-reference", proof_detail="Address elements verified against verified KYC vault", badge_label="VAULT MATCH", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Purpose Code Validation", description="External code list check", proof_detail="Purpose code 'GDSV' complies with destination rail requirements", badge_label="PURPOSE OK", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Clearing Transit Lookup", description="National routing directory", proof_detail="Active clearing transit participant confirmed", badge_label="ROUTING OK", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Governance Guardrail", description="Zero hallucination boundary", proof_detail="Deterministic enrichment completed without free-text speculation", badge_label="GOVERNED PASS", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Legacy ERP omitted structured CBPR+ tags", confidence=0.93, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Unregistered counterparty entity", confidence=0.07, status="ELIMINATED", elimination_reason="Counterparty exists with active corporate mandate")
        ]

    # ==================== DOMAIN 2: PROCESSING ====================
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
            GuidedQuestionItem(category="DUPLICATE TRIAGE", question="Is this an accidental duplicate batch retry by client ERP, or two legitimate separate installments?", investigation_tip="Check purchase order numbers, invoice references, and submission interval."),
            GuidedQuestionItem(category="COMMERCIAL EVIDENCE", question="Do both instructions have distinct commercial contracts and separate debit authorizations?", investigation_tip="Inspect idempotency key and ledger accounting logs.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="24h Temporal Clustering", description="Burst frequency analysis", proof_detail="Dispatched 42 mins apart (Exceeds 15m automated retry burst window)", badge_label="CLUSTERED", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Commercial Invoice Diff", description="Remittance metadata comparison", proof_detail=f"Distinct invoice references identified (INV-88910 vs INV-889{10+case_idx})", badge_label="DISTINCT INVOICE", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="UETR Uniqueness Check", description="SWIFT transaction identifier", proof_detail="Distinct valid end-to-end UETRs assigned by debtor core banking", badge_label="UNIQUE UETR", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Historical Installment Precedent", description="Recurring cadence analysis", proof_detail="Matches known monthly dual-tranche supplier contract structure", badge_label="PATTERN MATCH", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Ledger Overdraft Guardrail", description="Debtor balance verification", proof_detail="Debtor account contains sufficient liquidity for both disbursements", badge_label="FUNDS OK", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Legitimate recurring / multi-tranche commercial disbursement", confidence=0.91, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Accidental automated ERP resubmission retry", confidence=0.09, status="ELIMINATED", elimination_reason="Different invoice line items and independent purchase order references confirmed")
        ]

    elif profile in [ExceptionProfile.ROUTING_FAILURE, ExceptionProfile.ISO20022_VALIDATION_ERROR, ExceptionProfile.CUTOFF_MISSED, ExceptionProfile.CORRUPTED_MESSAGE_FORMAT, ExceptionProfile.INTERMEDIARY_BANK_REJECTION, ExceptionProfile.NETWORK_TIMEOUT, ExceptionProfile.QUEUE_PROCESSING_FAILURE, ExceptionProfile.PAYMENT_HELD_FOR_REPAIR]:
        action_type = ActionType.REROUTE_CLEARING if profile == ExceptionProfile.ROUTING_FAILURE else ActionType.RETRY_PROCESSING_QUEUE
        conf_score = 0.94
        rationale = f"Processing exception resolved via automated corridor re-routing and canonical syntax re-serialization."
        proposed_changes = [ProposedFieldChange(
            field_path="intermediary_agent.bic",
            original_value_masked="CORRUPT_ROUTE_01",
            proposed_value_masked="CHASUS33XXX",
            justification="Alternative Tier-1 correspondent clearing hop verified.",
            validation_status="VALIDATED_ROUTE_OPTIMIZED"
        )]
        guided_questions = [
            GuidedQuestionItem(category="PROCESSING AUDIT", question="Did the message fail at internal gateway or at external clearing hub?", investigation_tip="Check network ACK logs, SWIFT gpi tracker, and intermediary pacs.002 status."),
            GuidedQuestionItem(category="CUTOFF ADHERENCE", question="Does the re-routed payment satisfy destination clearing cutoff deadline?", investigation_tip="Verify value-date roll parameters and instant rail availability.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Message Syntax Validation", description="ISO 20022 XSD syntax audit", proof_detail="Sanitized XML passes full CBPR+ validation suite", badge_label="XSD PASS", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Intermediary Corridor Health", description="Correspondent availability", proof_detail="Target clearing intermediary JPMorgan Chase NY is ONLINE", badge_label="CORRIDOR ONLINE", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Cutoff Window Check", description="Settlement cutoff calculation", proof_detail="Est. dispatch meets Target2 / Fedwire cutoff window (1h 45m buffer)", badge_label="WINDOW MET", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Dead-Letter Queue Isolation", description="DLQ state inspection", proof_detail="Message freed from deadlock queue and restaged for execution", badge_label="STAGED", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Idempotency Protection", description="Duplicate dispatch safeguard", proof_detail="Single dispatch lock acquired; zero risk of double execution", badge_label="IDEMP LOCKED", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Transient network / intermediary clearing rejection", confidence=0.94, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Permanent non-settlement corridor embargo", confidence=0.06, status="ELIMINATED", elimination_reason="Correspondent clearing agreement is active with positive Nostro balance")
        ]

    # ==================== DOMAIN 3: COMPLIANCE ====================
    elif profile == ExceptionProfile.SANCTIONS_SUSPECTED:
        action_type = ActionType.CLEAR_FALSE_POSITIVE
        conf_score = 0.98
        rationale = "Secondary identifiers confirm target entity is a verified UK corporate, distinct from the designated individual on OFAC SDN list."
        proposed_changes = [ProposedFieldChange(
            field_path="compliance_screening.disposition",
            original_value_masked="SCREENING_HIT_TIER_2",
            proposed_value_masked="FALSE_POSITIVE_HOMONYM_CLEARED",
            justification="Secondary identifiers (Tax ID 889128, Inc Date 2014) confirm homonym false positive.",
            validation_status="VALIDATED_COMPLIANCE_PASS"
        )]
        guided_questions = [
            GuidedQuestionItem(category="SANCTIONS DISAMBIGUATION", question="Is this a true sanctioned entity or a false-positive homonym?", investigation_tip="Verify Tax ID, Country of Incorporation, Registration Date, and UBO chain."),
            GuidedQuestionItem(category="LEGAL AUTHORITY", question="Does the reviewer possess formal compliance approval authority to clear this alert?", investigation_tip="Enforce compliance-only sign-off under SOP-301.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="OFAC / EU List Cross-Check", description="Watchlist fuzzy matching test", proof_detail="Name similarity = 0.87 against SDN individual 'N. Components'", badge_label="ALERT 87%", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Tax ID / Registration Verification", description="Secondary identifier test", proof_detail="UK Companies House Reg #08819201 != SDN Individual Identifier", badge_label="TAX ID DIVERGENT", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Date of Incorporation Check", description="Temporal registration check", proof_detail="Incorporated in 2014 vs SDN designation date in 1982", badge_label="DOB MISMATCH", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Ultimate Beneficial Ownership (UBO)", description="Ownership structure audit", proof_detail="100% of UBO chain cleared. Zero PEP / SDN ownership > 0%", badge_label="UBO CLEARED", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Adverse Media & Negative News", description="Global adverse media scan", proof_detail="Zero adverse media hits or regulatory enforcement actions", badge_label="CLEAN MEDIA", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Homonym false positive on established UK corporate", confidence=0.98, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="True positive SDN blocked individual", confidence=0.02, status="ELIMINATED", elimination_reason="Independent registration numbers and incorporation dates differ completely from SDN record")
        ]

    elif profile in [ExceptionProfile.AML_ALERT, ExceptionProfile.PEP_MATCH, ExceptionProfile.RESTRICTED_CORRIDOR, ExceptionProfile.ADVERSE_MEDIA_MATCH, ExceptionProfile.HIGH_RISK_JURISDICTION, ExceptionProfile.REGULATORY_REPORTING_REQUIRED, ExceptionProfile.CUSTOMER_WATCHLIST_MATCH]:
        action_type = ActionType.RELEASE_COMPLIANCE_CLEARANCE
        conf_score = 0.95
        rationale = f"Enhanced Due Diligence (EDD) completed. Regulatory requirements verified under {profile.value} compliance SOP."
        proposed_changes = [ProposedFieldChange(
            field_path="compliance_screening.edd_certificate",
            original_value_masked="PENDING_REGULATORY_REVIEW",
            proposed_value_masked="EDD_CERTIFICATE_VERIFIED_CLEARED",
            justification="Mandatory compliance documentation verified by Compliance Officer.",
            validation_status="VALIDATED_REGULATORY_PASS"
        )]
        guided_questions = [
            GuidedQuestionItem(category="COMPLIANCE GATE", question="Has Enhanced Due Diligence (EDD) been formally signed off by MLRO?", investigation_tip="Verify source of wealth, commercial invoice, and regulatory reporting declaration."),
            GuidedQuestionItem(category="JURISDICTION RISK", question="Does the corridor require mandatory central bank reporting tags?", investigation_tip="Check BoP declaration requirements.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Regulatory Framework Audit", description="AML / FATF compliance check", proof_detail="Source of wealth verified against commercial contract #CC-8891", badge_label="EDD PASS", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Watchlist Disambiguation", description="PEP / SDN entity check", proof_detail="Zero active restrictions on corporate beneficiary", badge_label="CLEARED", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Corridor Risk Rating", description="Geopolitical territory check", proof_detail="Approved low-risk bilateral corridor (USD/EUR)", badge_label="LOW RISK", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Regulatory Declaration Tag", description="Balance of Payments declaration", proof_detail="Mandatory <RgltryRptg> BoP code GDSV populated", badge_label="BoP ATTACHED", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Audit Integrity Stamp", description="Compliance audit trail", proof_detail="Full compliance sign-off stamped into SHA-256 ledger", badge_label="AUDIT SEALED", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Legitimate commercial transaction with satisfied EDD requirements", confidence=0.95, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="High-risk illicit flow / money laundering structuring", confidence=0.05, status="ELIMINATED", elimination_reason="Audited financial statements and underlying trade contract confirmed")
        ]

    # ==================== DOMAIN 4: CLIENT / TREASURY ====================
    elif profile == ExceptionProfile.KYC_EXPIRED:
        action_type = ActionType.GRANT_KYC_WAIVER
        conf_score = 0.94
        rationale = "Customer periodic review is in progress. Counterparty qualifies for standard 30-day provisional waiver under SOP-302."
        proposed_changes = [ProposedFieldChange(
            field_path="customer_kyc.provisional_status",
            original_value_masked="EXPIRED_2026_07_15",
            proposed_value_masked="WAIVER_ACTIVE_30_DAYS",
            justification="Tier-1 corporate counterparty with clean 24-month audit history. Document refresh initiated.",
            validation_status="VALIDATED_SOP302_WAIVER"
        )]
        guided_questions = [
            GuidedQuestionItem(category="KYC GOVERNANCE", question="Is this counterparty eligible for a 30-day provisional processing waiver under SOP-302?", investigation_tip="Check counterparty risk rating, documentation refresh status, and historical dispute rate."),
            GuidedQuestionItem(category="HIGH-VALUE ESCALATION", question="Does this transaction exceed $250k requiring secondary Risk Approver dual sign-off?", investigation_tip="Enforce Step 1 Compliance -> Step 2 Risk dual approval chain.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Tier-1 Corporate Status", description="Institutional client categorization", proof_detail="Certified Tier-1 Multinational Corporate account", badge_label="TIER 1 CLIENT", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Documentation Refresh Status", description="CDD update pipeline", proof_detail="Refreshed board resolution received and in review by onboarding", badge_label="REFRESH IN PROGRESS", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="24-Month Risk Track Record", description="Historical SAR / dispute audit", proof_detail="Zero SARs, regulatory queries, or returned payments in 24 months", badge_label="CLEAN RECORD", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Corridor Risk Ceiling", description="Jurisdictional risk evaluation", proof_detail="Low-risk AUD/USD clearing corridor; well within credit limits", badge_label="LOW RISK", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="SOP-302 Waiver Compliance", description="Policy guardrail test", proof_detail="Provisional 30-day processing waiver authorized under SOP-302 §4", badge_label="WAIVER GRANTED", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Eligible for 30-day operational waiver during routine documentation refresh", confidence=0.94, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Unverified high-risk entity requiring immediate stop", confidence=0.06, status="ELIMINATED", elimination_reason="Established relationship with full corporate registry documentation on file")
        ]

    elif profile in [ExceptionProfile.INSUFFICIENT_FUNDS, ExceptionProfile.NOSTRO_SHORTFALL, ExceptionProfile.FX_RATE_UNAVAILABLE, ExceptionProfile.AUTHORIZATION_MISSING, ExceptionProfile.LIMIT_BREACH, ExceptionProfile.LIQUIDITY_CONSTRAINT, ExceptionProfile.CREDIT_EXPOSURE_BREACH]:
        action_type = ActionType.EXECUTE_TREASURY_TRANSFER
        conf_score = 0.95
        rationale = f"Treasury liquidity / credit positioning validated. Automated sweep or daylight overdraft facility allocated."
        proposed_changes = [ProposedFieldChange(
            field_path="treasury_liquidity.corridor_allocation",
            original_value_masked="SHORTFALL_FLAGGED",
            proposed_value_masked="NOSTRO_SWEEP_FUNDED",
            justification="Automated Nostro corridor sweep executed from central pool.",
            validation_status="VALIDATED_LIQUIDITY_FUNDED"
        )]
        guided_questions = [
            GuidedQuestionItem(category="LIQUIDITY ASSESSMENT", question="Is the Nostro corridor funded or does it require an intraday sweep?", investigation_tip="Check Nostro real-time balance and intraday credit line availability."),
            GuidedQuestionItem(category="MANDATE VERIFICATION", question="Has the debtor corporate signatory threshold been validated?", investigation_tip="Verify mandate authorization matrix.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Intraday Liquidity Position", description="Nostro corridor balance check", proof_detail="Central liquidity pool allocation confirmed ($14.2M available)", badge_label="FUNDS ALLOCATED", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Daylight Facility Check", description="Intraday credit line evaluation", proof_detail="Debtor daylight overdraft authorized within approved facility", badge_label="FACILITY ACTIVE", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="FX Market Rate Lock", description="Cross-currency rate quote", proof_detail="Guaranteed rate quote bound via secondary aggregator", badge_label="FX LOCKED", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Corporate Mandate Sign-Off", description="Dual signatory verification", proof_detail="Corporate treasurer authorization verified via digital portal", badge_label="MANDATE OK", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="BCBS 248 Buffer Protection", description="Central bank reserve minimums", proof_detail="Intraday liquidity outflow complies with regulatory buffer targets", badge_label="BUFFER MET", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Transient intraday liquidity timing / daylight facility covered", confidence=0.95, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Hard corporate credit default / insolvency event", confidence=0.03, status="ELIMINATED", elimination_reason="Debtor corporate treasury maintains $25.0M approved daylight overdraft facility with only 24.5% drawn"),
            HypothesisRankingItem(hypothesis_id="HYP-3", title="Corporate mandate breach / unauthorized drawdown", confidence=0.02, status="ELIMINATED", elimination_reason="Corporate signatory portal validated dual biometric CFO and Treasurer authorizations on file")
        ]

    # ==================== DOMAIN 5: SETTLEMENT / RETURNS ====================
    elif profile == ExceptionProfile.RETURNED_PAYMENT or profile in [ExceptionProfile.ACCOUNT_CLOSED, ExceptionProfile.BENEFICIARY_ACCOUNT_FROZEN, ExceptionProfile.RECONCILIATION_BREAK, ExceptionProfile.SETTLEMENT_FAILURE, ExceptionProfile.FUNDS_TRAPPED_AT_CORRESPONDENT, ExceptionProfile.UNMATCHED_CREDIT]:
        action_type = ActionType.RETURN_PRINCIPAL_REVERSAL
        conf_score = 0.95
        rationale = f"pacs.004 payment return parsed and matched against original pacs.008. Re-crediting debtor suspense account."
        proposed_changes = [ProposedFieldChange(
            field_path="settlement_ledger.suspense_recredit",
            original_value_masked="UNRECONCILED_RETURN",
            proposed_value_masked="RECONCILED_CREDIT_TO_ORIGINATOR",
            justification="pacs.004 return correlated to original UETR. Ledger credit authorized.",
            validation_status="VALIDATED_RETURN_RECONCILED"
        )]
        guided_questions = [
            GuidedQuestionItem(category="RETURN RECONCILIATION", question="What was the root cause return reason code in the pacs.004 message?", investigation_tip="Check ISO reason codes (AC04 Closed, AC06 Blocked, AG01 Currency) and intermediary fee deductions."),
            GuidedQuestionItem(category="LEDGER REVERSAL", question="Does the returned amount match the original principal minus authorized clearing charges?", investigation_tip="Reconcile gross vs net return ledger entries.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="pacs.004 Return Parsing", description="ISO return message validation", proof_detail="Valid pacs.004.001.09 message received from receiving bank", badge_label="pacs.004 VALID", is_passed=True),
            StepAssessmentItem(step_number=2, step_title="Original UETR Correlation", description="Outbound payment matching", proof_detail="Matched to outbound settlement pacs.008 (TxId #TX-88192)", badge_label="UETR MATCHED", is_passed=True),
            StepAssessmentItem(step_number=3, step_title="Fee & Principal Breakdown", description="Intermediary charges audit", proof_detail="Principal $42,000.00 - Intermediary fee $25.00 = Net return $41,975.00", badge_label="FEES AUDITED", is_passed=True),
            StepAssessmentItem(step_number=4, step_title="Debtor Suspense Account", description="Escrow positioning", proof_detail="Funds held safely in Nostro return suspense account", badge_label="SUSPENSE HELD", is_passed=True),
            StepAssessmentItem(step_number=5, step_title="Automated Client Advice", description="Customer notification", proof_detail="Remittance advice generated for customer treasury", badge_label="ADVICE READY", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Valid pacs.004 payment return requiring ledger re-credit", confidence=0.95, status="SELECTED"),
            HypothesisRankingItem(hypothesis_id="HYP-2", title="Uncorrelated erroneous credit transfer / phantom wire", confidence=0.03, status="ELIMINATED", elimination_reason="Original UETR and debtor account matched with 100% confidence in 90-day settlement archive"),
            HypothesisRankingItem(hypothesis_id="HYP-3", title="Duplicate return recall / double-crediting break", confidence=0.02, status="ELIMINATED", elimination_reason="Ledger reconciler verified exactly 1 outbound debit ($329,525.00) and zero prior re-credits")
        ]

    else:
        # General Fallback
        action_type = ActionType.REPAIR_DATA
        conf_score = 0.90
        rationale = "Validated against institutional policy rules."
        proposed_changes = [ProposedFieldChange(
            field_path="payment.status",
            original_value_masked="EXCEPTION",
            proposed_value_masked="REPAIRED",
            justification="Standard validation pass.",
            validation_status="VALIDATED"
        )]
        guided_questions = [
            GuidedQuestionItem(category="GENERAL TRIAGE", question="Does this exception satisfy standard clearing requirements?", investigation_tip="Verify master directory.")
        ]
        step_assessment = [
            StepAssessmentItem(step_number=1, step_title="Format Verification", description="Standard check", proof_detail="Format valid", badge_label="VALIDATED", is_passed=True)
        ]
        hypothesis_ranking = [
            HypothesisRankingItem(hypothesis_id="HYP-1", title="Standard exception repair", confidence=0.90, status="SELECTED")
        ]

    has_ambiguity = (profile == ExceptionProfile.BENEFICIARY_NAME_MISMATCH) or (case_id == "PEX-BEN-0050")
    amb_msg = "Multi-Candidate Ambiguity: Two eligible active accounts detected for counterparty. AI policy prohibits automated tie-breaking without Human Operator selection." if has_ambiguity else None

    return DecisionRecommendation(
        recommendation_id=f"REC-{case_id}",
        case_id=case_id,
        action_type=action_type,
        confidence_score=conf_score,
        rationale=rationale,
        proposed_changes=proposed_changes,
        ambiguity_detected=has_ambiguity,
        ambiguity_message=amb_msg,
        corroborating_evidence=[
            CorroboratingEvidenceRef(evidence_id="EVD-01", evidence_type="DIRECTORY_SSI", citation=f"BIAN {domain.value} Policy Registry §4.1"),
            CorroboratingEvidenceRef(evidence_id="EVD-02", evidence_type="MOD97_CHECK", citation="ISO 7064 Mathematical Verification Engine")
        ],
        risk_evaluation=RiskEvaluation(
            risk_level=severity,
            risk_score=0.15 if severity == ExceptionSeverity.LOW else (0.45 if severity == ExceptionSeverity.MEDIUM else 0.85),
            risk_factors=["High monetary value (>= $250k)" if amount >= 250000.0 else "Standard business transaction", f"{domain.value} domain validation"],
            dual_auth_required=(amount >= 250000.0)
        ),
        guided_questions=guided_questions,
        step_by_step_assessment=step_assessment,
        hypothesis_ranking=hypothesis_ranking,
        anomaly_guardrails=[
            AnomalyGuardrailItem(guardrail_name="Zero Financial Hallucination", status="PASSED", details="All values grounded in deterministic directory records"),
            AnomalyGuardrailItem(guardrail_name="Segregation of Duties", status="PASSED", details="Maker-Checker approval enforced")
        ],
        consequence_simulation=ConsequenceSimulation(
            estimated_settlement_velocity="2.1 seconds",
            cutoff_deadline_status=f"MEETS {creditor_country} CUTOFF (1h 45m buffer)",
            fee_penalty_avoidance=f"${150.00:,.2f} late inquiry fee avoided",
            nostro_liquidity_impact="Sufficient Liquidity in Corridor ($14.2M)"
        )
    )

class PeXRepository:
    def __init__(self):
        self.cases: Dict[str, Dict[str, Any]] = {}
        self.exceptions: Dict[str, CanonicalException] = {}
        self.payments: Dict[str, CanonicalPayment] = {}
        self.evidence: Dict[str, List[EvidenceItem]] = {}
        self.approvals: Dict[str, List[ApprovalRecord]] = {}
        self.recommendations: Dict[str, DecisionRecommendation] = {}
        self.actions: Dict[str, GovernedActionContract] = {}
        self.receipts: Dict[str, DeliveryReceipt] = {}
        self.beneficiaries: Dict[str, Dict[str, Any]] = {}
        self.policies: List[PolicyRule] = []
        self.historical_cases: List[Dict[str, Any]] = []
        self.audit_log: List[AuditEvent] = []
        self.latest_hash = "0" * 64

    @property
    def latest_chain_hash(self) -> str:
        return self.latest_hash

    @latest_chain_hash.setter
    def latest_chain_hash(self, value: str):
        self.latest_hash = value

    def save_case(self, case_dict: Dict[str, Any]):
        self.cases[case_dict["case_id"]] = case_dict

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self.cases.get(case_id)

    def list_cases(
        self,
        queue: Optional[str] = None,
        status: Optional[str] = None,
        profile: Optional[str] = None,
        domain: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = list(self.cases.values())
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
            results = [c for c in results if s in c.get("case_id", "").lower() or s in c.get("profile", "").lower() or s in str(c.get("creditor_party", {})).lower()]
        return results

    def load_all_data(self):
        self.preload_curated_live_cases()

    def _append_audit_event(self, case_id: str, correlation_id: str, stage_name: str, actor_id: str, actor_role: str, action_name: str, details: str, control_tags: List[str]):
        idx = len(self.audit_log) + 1
        ts = (datetime.utcnow() - timedelta(minutes=max(1, 100 - idx))).isoformat()
        current_hash = calculate_event_hash(
            event_index=idx,
            timestamp_iso=ts,
            case_id=case_id,
            stage_name=stage_name,
            actor_id=actor_id,
            action_name=action_name,
            details=details,
            prev_hash=self.latest_hash
        )
        ev = AuditEvent(
            event_index=idx,
            case_id=case_id,
            correlation_id=correlation_id,
            stage_name=stage_name,
            actor_id=actor_id,
            actor_role=actor_role,
            action_name=action_name,
            timestamp=ts,
            details=details,
            control_tags=control_tags,
            prev_hash=self.latest_hash,
            current_hash=current_hash
        )
        self.latest_hash = current_hash
        self.audit_log.append(ev)

    def preload_curated_live_cases(self):
        """Preloads 80 curated realistic cases covering ALL 41 Market Exception Profiles across 5 Domains."""
        self.cases.clear()
        self.approvals.clear()
        self.recommendations.clear()
        self.audit_log.clear()
        self.latest_hash = "0" * 64

        # List of all 41 profiles to seed
        all_profiles = [
            # Data Quality (9)
            ExceptionProfile.INVALID_IBAN, ExceptionProfile.INVALID_BIC, ExceptionProfile.MISSING_BENEFICIARY_DATA,
            ExceptionProfile.MISSING_REMITTANCE_INFO, ExceptionProfile.INVALID_ADDRESS_FORMAT, ExceptionProfile.MISSING_PURPOSE_CODE,
            ExceptionProfile.INVALID_ACCOUNT_NUMBER, ExceptionProfile.INVALID_ROUTING_CODE, ExceptionProfile.BENEFICIARY_NAME_MISMATCH,
            # Processing (9)
            ExceptionProfile.DUPLICATE_PAYMENT, ExceptionProfile.ROUTING_FAILURE, ExceptionProfile.ISO20022_VALIDATION_ERROR,
            ExceptionProfile.CUTOFF_MISSED, ExceptionProfile.CORRUPTED_MESSAGE_FORMAT, ExceptionProfile.INTERMEDIARY_BANK_REJECTION,
            ExceptionProfile.NETWORK_TIMEOUT, ExceptionProfile.QUEUE_PROCESSING_FAILURE, ExceptionProfile.PAYMENT_HELD_FOR_REPAIR,
            # Compliance (8)
            ExceptionProfile.SANCTIONS_SUSPECTED, ExceptionProfile.AML_ALERT, ExceptionProfile.PEP_MATCH,
            ExceptionProfile.RESTRICTED_CORRIDOR, ExceptionProfile.ADVERSE_MEDIA_MATCH, ExceptionProfile.HIGH_RISK_JURISDICTION,
            ExceptionProfile.REGULATORY_REPORTING_REQUIRED, ExceptionProfile.CUSTOMER_WATCHLIST_MATCH,
            # Client / Treasury (8)
            ExceptionProfile.KYC_EXPIRED, ExceptionProfile.INSUFFICIENT_FUNDS, ExceptionProfile.NOSTRO_SHORTFALL,
            ExceptionProfile.FX_RATE_UNAVAILABLE, ExceptionProfile.AUTHORIZATION_MISSING, ExceptionProfile.LIMIT_BREACH,
            ExceptionProfile.LIQUIDITY_CONSTRAINT, ExceptionProfile.CREDIT_EXPOSURE_BREACH,
            # Settlement / Returns (7)
            ExceptionProfile.RETURNED_PAYMENT, ExceptionProfile.ACCOUNT_CLOSED, ExceptionProfile.BENEFICIARY_ACCOUNT_FROZEN,
            ExceptionProfile.RECONCILIATION_BREAK, ExceptionProfile.SETTLEMENT_FAILURE, ExceptionProfile.FUNDS_TRAPPED_AT_CORRESPONDENT,
            ExceptionProfile.UNMATCHED_CREDIT
        ]

        counterparties = [
            ("Nordhavn Components A/S", "GB", "GBP", "BARCGB22XXX"),
            ("HarborView Supplier Ltd", "GB", "USD", "WESTGB2L"),
            ("Apex Global Treasury", "US", "USD", "CHASUS33XXX"),
            ("Kyoto Precision Robotics", "JP", "JPY", "BOTKJPJTXXX"),
            ("Vanguard BioPharma GmbH", "DE", "EUR", "DEUTDEDDXXX"),
            ("Sydney Infrastructure Ltd", "AU", "AUD", "ANZBAU3MXXX"),
            ("Atlas Mediterranean Marine", "GR", "EUR", "NBGRGRAAXXX"),
            ("Zurich Tech Logistics AG", "CH", "CHF", "UBSWCHZHXXX"),
            ("Bavaria Engine Works AG", "DE", "EUR", "HYVEDEMMXXX"),
            ("Singapore FinTech Holding", "SG", "SGD", "DBSSSGSGXXX")
        ]

        # Generate 82 cases (2 cases per profile)
        case_counter = 1
        for repeat in range(2):
            for p_idx, profile in enumerate(all_profiles):
                i = case_counter
                cp_name, cp_country, cp_ccy, cp_bic = counterparties[i % len(counterparties)]
                domain = get_domain_for_profile(profile)
                
                # Format case ID
                prefix = profile.value[:3]
                case_id = f"PEX-{prefix}-{i:04d}"
                uetr = f"UETR-2026-{prefix}-{i:04d}-A8"
                payment_ref = f"PAY-2026-{i:06d}"

                # Varied Amounts
                if i % 3 == 0:
                    amount = 45000.0 + (i * 1250.50)
                elif i % 3 == 1:
                    amount = 325000.0 + (i * 4500.0)  # High Value Dual Auth
                else:
                    amount = 1450000.0 + (i * 9800.0) # Critical High Value

                # Varied Stages
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

                # Queue assignment
                if domain == ExceptionDomain.COMPLIANCE:
                    queue = "Compliance"
                elif domain == ExceptionDomain.CLIENT_TREASURY:
                    queue = "Treasury"
                elif domain == ExceptionDomain.SETTLEMENT_RETURNS:
                    queue = "Investigation"
                elif domain == ExceptionDomain.PROCESSING:
                    queue = "Investigation" if profile == ExceptionProfile.DUPLICATE_PAYMENT else "Repair"
                else:
                    queue = "Repair"

                # Tokenize PII
                debtor_tok = token_vault.tokenize(f"Ordering Customer {i}", "PARTY")
                creditor_tok = token_vault.tokenize(cp_name, "PARTY")
                debtor_acc_tok = token_vault.tokenize(f"US11APEX998877{i:04d}", "ACC")
                creditor_iban_tok = token_vault.tokenize(f"{cp_country}82WEST1234569876{i:04d}", "IBAN")

                # Realistic Ingestion Timestamps & SLA Targets (Calculated strictly from Ingested Time)
                if i % 8 == 0:
                    t_base = datetime.utcnow() - timedelta(minutes=35)
                    sla_target_minutes = 120
                elif i % 8 == 1:
                    t_base = datetime.utcnow() - timedelta(minutes=85)
                    sla_target_minutes = 120
                elif i % 8 == 2:
                    t_base = datetime.utcnow() - timedelta(minutes=15)
                    sla_target_minutes = 240
                elif i % 8 == 3:
                    t_base = datetime.utcnow() - timedelta(minutes=10)
                    sla_target_minutes = 360
                elif i % 8 == 4:
                    t_base = datetime.utcnow() - timedelta(minutes=150)
                    sla_target_minutes = 120
                elif i % 8 == 5:
                    t_base = datetime.utcnow() - timedelta(minutes=45)
                    sla_target_minutes = 180
                elif i % 8 == 6:
                    t_base = datetime.utcnow() - timedelta(minutes=105)
                    sla_target_minutes = 120
                else:
                    t_base = datetime.utcnow() - timedelta(minutes=8)
                    sla_target_minutes = 480

                sla_due = t_base + timedelta(minutes=sla_target_minutes)

                # Audit Timeline Generation
                audit_timeline = [{
                    "step_index": 1,
                    "timestamp": t_base.isoformat(),
                    "actor_name": "PeX Ingestion Gateway",
                    "actor_role": "SYSTEM",
                    "badge_color": "slate",
                    "action_title": "Exception Ingested & Canonicalized",
                    "icon": "📥",
                    "summary": f"Payment wire received via SWIFT / CBPR+. PII tokenized into isolated vault reference {debtor_tok}."
                }]

                self._append_audit_event(
                    case_id=case_id,
                    correlation_id=uetr,
                    stage_name="INGESTION",
                    actor_id="SYS-INGEST",
                    actor_role="SYSTEM",
                    action_name="INGEST_EXCEPTION",
                    details=f"Payment exception {case_id} ({profile.value}) ingested across {domain.value} domain.",
                    control_tags=["Schema valid", "Token vault isolated", f"BIAN {domain.value}"]
                )

                if status != LifecycleStage.INGESTED:
                    t_ai = t_base + timedelta(minutes=10)
                    audit_timeline.append({
                        "step_index": 2,
                        "timestamp": t_ai.isoformat(),
                        "actor_name": "Priya Nair",
                        "actor_role": "OPERATOR (MAKER)",
                        "badge_color": "blue",
                        "action_title": "AI Reasoner Evaluated",
                        "icon": "⚡",
                        "summary": f"Analyst ran AI Reasoner. Grounded evidence under BIAN {domain.value} playbook."
                    })
                    self._append_audit_event(
                        case_id=case_id,
                        correlation_id=uetr,
                        stage_name="ANALYST_REPAIR",
                        actor_id="OP-9012",
                        actor_role="OPERATOR",
                        action_name="RUN_AI_REPAIR",
                        details=f"Analyst Priya Nair triggered AI reasoner for {profile.value}.",
                        control_tags=["Evidence grounded", "SOP aligned", "Maker review complete"]
                    )

                if status == LifecycleStage.RETURNED_FOR_REWORK or i % 9 == 4:
                    t_rework = t_base + timedelta(minutes=20)
                    audit_timeline.append({
                        "step_index": len(audit_timeline) + 1,
                        "timestamp": t_rework.isoformat(),
                        "actor_name": "Daniel Osei",
                        "actor_role": "OPERATIONS_APPROVER",
                        "badge_color": "amber",
                        "action_title": "Returned to Maker for Rework",
                        "icon": "⚠️",
                        "summary": "Approver requested clarification: 'Please confirm revised commercial invoice with client treasury.'"
                    })
                    self._append_audit_event(
                        case_id=case_id,
                        correlation_id=uetr,
                        stage_name="HITL_APPROVAL",
                        actor_id="APR-3191",
                        actor_role="OPERATIONS_APPROVER",
                        action_name="RETURN_TO_MAKER",
                        details=f"Approver returned case {case_id} to Maker for invoice re-verification.",
                        control_tags=["Rework cycle logged", "Audit comment captured"]
                    )

                approvals_list = []
                approval_hist = []

                if status in [LifecycleStage.AWAITING_SECOND_APPROVAL, LifecycleStage.APPROVED, LifecycleStage.SETTLED]:
                    t_l1 = t_base + timedelta(minutes=35)
                    rec1 = ApprovalRecord(
                        approval_id=f"APR-{i:04d}-S1",
                        case_id=case_id,
                        recommendation_id=f"REC-{case_id}",
                        approver_id="APR-3191" if queue != "Compliance" else "CMP-4420",
                        approver_name="Daniel Osei" if queue != "Compliance" else "Marisol Vega",
                        approver_role=UserRole.OPERATIONS_APPROVER if queue != "Compliance" else UserRole.COMPLIANCE_APPROVER,
                        action=ApprovalAction.APPROVE,
                        comments=f"Level 1 verification approved for {profile.value}.",
                        step_number=1,
                        approved_changes=[],
                        created_at=t_l1
                    )
                    approvals_list.append(rec1)
                    approval_hist.append(rec1.model_dump() if hasattr(rec1, "model_dump") else rec1.dict())
                    audit_timeline.append({
                        "step_index": len(audit_timeline) + 1,
                        "timestamp": t_l1.isoformat(),
                        "actor_name": "Daniel Osei" if queue != "Compliance" else "Marisol Vega",
                        "actor_role": "OPERATIONS_APPROVER" if queue != "Compliance" else "COMPLIANCE_APPROVER",
                        "badge_color": "emerald",
                        "action_title": "Level 1 Sign-off Approved",
                        "icon": "🛡️",
                        "summary": f"Level 1 verification approved for {profile.value}."
                    })
                    self._append_audit_event(
                        case_id=case_id,
                        correlation_id=uetr,
                        stage_name="HITL_APPROVAL",
                        actor_id="APR-3191" if queue != "Compliance" else "CMP-4420",
                        actor_role="OPERATIONS_APPROVER" if queue != "Compliance" else "COMPLIANCE_APPROVER",
                        action_name="APPROVAL_APPROVE",
                        details=f"Level 1 repair authorized by {'Daniel Osei' if queue != 'Compliance' else 'Marisol Vega'}.",
                        control_tags=["Level 1 sign-off complete", "Maker-Checker enforced"]
                    )

                if status in [LifecycleStage.APPROVED, LifecycleStage.SETTLED] and amount >= 250000.0:
                    t_l2 = t_base + timedelta(minutes=45)
                    rec2 = ApprovalRecord(
                        approval_id=f"APR-{i:04d}-S2",
                        case_id=case_id,
                        recommendation_id=f"REC-{case_id}",
                        approver_id="RSK-7714",
                        approver_name="Kenji Watanabe",
                        approver_role=UserRole.RISK_APPROVER,
                        action=ApprovalAction.APPROVE,
                        comments="Tier 2 High-Value Dual Authorization authorized.",
                        step_number=2,
                        approved_changes=[],
                        created_at=t_l2
                    )
                    approvals_list.append(rec2)
                    approval_hist.append(rec2.model_dump() if hasattr(rec2, "model_dump") else rec2.dict())
                    audit_timeline.append({
                        "step_index": len(audit_timeline) + 1,
                        "timestamp": t_l2.isoformat(),
                        "actor_name": "Kenji Watanabe",
                        "actor_role": "RISK_APPROVER",
                        "badge_color": "purple",
                        "action_title": "Level 2 Dual Authorization Approved",
                        "icon": "🔒",
                        "summary": "Tier-2 High-Value Dual Authorization signed off for dispatch."
                    })
                    self._append_audit_event(
                        case_id=case_id,
                        correlation_id=uetr,
                        stage_name="HITL_APPROVAL",
                        actor_id="RSK-7714",
                        actor_role="RISK_APPROVER",
                        action_name="APPROVAL_DUAL_AUTH",
                        details=f"Tier 2 Dual Authorization signed off by Kenji Watanabe for high-value dispatch.",
                        control_tags=["Dual-auth complete", "Risk threshold verified"]
                    )

                if status == LifecycleStage.SETTLED:
                    t_settle = t_base + timedelta(minutes=55)
                    ack_ref = f"ACK-SIM-{prefix}-{i:04d}"
                    audit_timeline.append({
                        "step_index": len(audit_timeline) + 1,
                        "timestamp": t_settle.isoformat(),
                        "actor_name": "PeX Settlement Kernel",
                        "actor_role": "SYSTEM",
                        "badge_color": "emerald",
                        "action_title": "Governed Settlement Dispatched & Reconciled",
                        "icon": "✓",
                        "summary": f"Transaction sealed with SHA-256 block hash and dispatched against external clearing rail. Delivery Receipt: {ack_ref}."
                    })
                    self._append_audit_event(
                        case_id=case_id,
                        correlation_id=uetr,
                        stage_name="ACTION_DISPATCH",
                        actor_id="SIM-SETTLE-KERNEL",
                        actor_role="SYSTEM",
                        action_name="SETTLEMENT_RECONCILED",
                        details=f"Case {case_id} settled and reconciled against external ledger. Delivery receipt reference: {ack_ref}.",
                        control_tags=["Ledger reconciled", "SHA-256 seal valid", "Outbound pacs.008 acknowledged"]
                    )

                # Store recommendations and approvals
                if status == LifecycleStage.INGESTED:
                    # In pure INGESTED status, no recommendation is attached yet - must be triggered by operator!
                    self.recommendations[case_id] = None
                    ai_conf = None
                else:
                    rec = build_rich_guided_recommendation(
                        case_id=case_id,
                        profile=profile,
                        amount=amount,
                        creditor_name=cp_name,
                        creditor_country=cp_country,
                        case_idx=i
                    )
                    self.recommendations[case_id] = rec
                    ai_conf = rec.confidence_score

                self.approvals[case_id] = approvals_list

                # Build Case Record
                # Extract guided questions for profile
                gq_items = build_rich_guided_recommendation(
                    case_id=case_id,
                    profile=profile,
                    amount=amount,
                    creditor_name=cp_name,
                    creditor_country=cp_country,
                    case_idx=i
                ).guided_questions

                case_dict = {
                    "case_id": case_id,
                    "guided_questions": [q.model_dump() if hasattr(q, "model_dump") else q.dict() for q in gq_items],
                    "payment_id": f"PMT-{i:06d}",
                    "uetr": uetr,
                    "payment_ref": payment_ref,
                    "profile": profile.value,
                    "domain": domain.value,
                    "secondary_profiles": [],
                    "error_code": f"ERR_{prefix}_{i:03d}",
                    "reason": f"Exception in {domain.value} domain: {profile.value.replace('_', ' ').title()}.",
                    "amount": round(amount, 2),
                    "currency": cp_ccy,
                    "payment_rail": "SWIFT_CBPR+" if cp_ccy != "USD" else "FEDWIRE_ISO20022",
                    "debtor_party": {"party_name": f"Ordering Corp {i}", "country": "US", "token_ref": debtor_tok},
                    "debtor_account": {"account_number": f"US11APEX998877{i:04d}", "token_ref": debtor_acc_tok},
                    "creditor_party": {"party_name": cp_name, "country": cp_country, "token_ref": creditor_tok},
                    "creditor_account": {"iban": f"{cp_country}82WEST1234569876{i:04d}", "bank_bic": cp_bic, "token_ref": creditor_iban_tok},
                    "queue": queue,
                    "status": status.value,
                    "severity": ExceptionSeverity.HIGH.value if amount >= 250000.0 else ExceptionSeverity.MEDIUM.value,
                    "priority": ExceptionPriority.HIGH.value if amount >= 250000.0 else ExceptionPriority.NORMAL.value,
                    "sla_due_at": sla_due.isoformat(),
                    "dual_auth_required": (amount >= 250000.0),
                    "ai_confidence": ai_conf,
                    "created_at": t_base.isoformat(),
                    "approval_history": approval_hist,
                    "settled_at": (t_base + timedelta(minutes=min(sla_target_minutes - 25, max(15, (i * 3) % 45)))).isoformat() if status == LifecycleStage.SETTLED else None,
                    "audit_timeline": audit_timeline
                }
                self.cases[case_id] = case_dict
                case_counter += 1

from app.db.repository import PeXDBRepository

repo = PeXDBRepository()
repo.load_all_data()

