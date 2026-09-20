import os

srv_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\services"

# 4. context_builder.py
with open(os.path.join(srv_dir, "context_builder.py"), "w", encoding="utf-8") as f:
    f.write('''"""Context Builder: Assembles Tokenized Dossier for AI Model Gateway."""
import uuid
from typing import List, Dict, Any, Optional

from app.schemas.canonical import CanonicalPayment, CanonicalException, ExceptionProfile
from app.schemas.context import (
    TokenizedInvestigationContext, TokenizedPaymentContext, TokenizedParty, TokenizedAccount,
    EvidenceItem, PolicyRule, HistoricalPrecedent
)
from app.core.tokenization import token_vault

class ContextBuilder:
    def build_investigation_context(
        self,
        payment: CanonicalPayment,
        exception: CanonicalException,
        evidence_items: List[EvidenceItem],
        policies: List[PolicyRule],
        historical_cases: List[HistoricalPrecedent]
    ) -> TokenizedInvestigationContext:
        debtor_token = payment.debtor_party.token_ref or token_vault.tokenize(payment.debtor_party.party_name, "PARTY")
        creditor_token = payment.creditor_party.token_ref or token_vault.tokenize(payment.creditor_party.party_name, "PARTY")
        
        debtor_acc_token = payment.debtor_account.token_ref or token_vault.tokenize(payment.debtor_account.account_number or "", "ACC")
        creditor_acc_token = payment.creditor_account.token_ref or token_vault.tokenize(payment.creditor_account.iban or "", "IBAN")

        tokenized_pmt = TokenizedPaymentContext(
            payment_id=payment.payment_id,
            uetr=payment.uetr,
            amount=payment.amount,
            currency=payment.currency,
            debtor_party=TokenizedParty(
                token_id=debtor_token,
                party_role="DEBTOR",
                country=payment.debtor_party.country
            ),
            debtor_account=TokenizedAccount(
                token_id=debtor_acc_token,
                currency=payment.currency,
                masked_identifier=token_vault.mask_identifier(payment.debtor_account.account_number or ""),
                bank_bic=payment.debtor_account.bank_bic
            ),
            creditor_party=TokenizedParty(
                token_id=creditor_token,
                party_role="CREDITOR",
                country=payment.creditor_party.country
            ),
            creditor_account=TokenizedAccount(
                token_id=creditor_acc_token,
                currency=payment.currency,
                masked_identifier=token_vault.mask_identifier(payment.creditor_account.iban or ""),
                bank_bic=payment.creditor_account.bank_bic
            ),
            payment_rail=payment.payment_rail
        )

        sanitized_evidence: List[EvidenceItem] = []
        for e in evidence_items:
            san_data = dict(e.data)
            if "standing_iban" in san_data:
                san_data["masked_standing_iban"] = token_vault.mask_identifier(san_data["standing_iban"])
            sanitized_evidence.append(EvidenceItem(
                evidence_id=e.evidence_id,
                evidence_type=e.evidence_type,
                source_connector=e.source_connector,
                retrieved_at=e.retrieved_at,
                provenance_id=e.provenance_id,
                is_mandatory=e.is_mandatory,
                data=san_data,
                relevance_score=e.relevance_score
            ))

        est_tokens = 450 + len(sanitized_evidence) * 120 + len(policies) * 80 + len(historical_cases) * 100

        return TokenizedInvestigationContext(
            context_id=f"CTX-{uuid.uuid4().hex[:8].upper()}",
            case_id=exception.case_id,
            profile=exception.profile,
            tokenized_payment=tokenized_pmt,
            evidence_items=sanitized_evidence,
            policies=policies,
            historical_cases=historical_cases,
            token_usage_estimated=est_tokens
        )

context_builder = ContextBuilder()
''')

# 5. model_gateway.py
with open(os.path.join(srv_dir, "model_gateway.py"), "w", encoding="utf-8") as f:
    f.write('''"""Model Gateway: Pluggable AI Reasoning layer with Deterministic Mock & Live Provider capabilities."""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import settings
from app.schemas.context import TokenizedInvestigationContext
from app.schemas.recommendation import (
    DecisionRecommendation, ActionType, ProposedFieldChange,
    CorroboratingEvidenceRef, RiskEvaluation
)
from app.schemas.canonical import ExceptionSeverity
from app.core.tokenization import token_vault

class ModelGateway:
    def evaluate_investigation(
        self,
        context: TokenizedInvestigationContext,
        scenario_key: Optional[str] = None
    ) -> DecisionRecommendation:
        case_id = context.case_id
        profile = context.profile
        amount = context.tokenized_payment.amount

        if scenario_key == "IBAN-ESCALATE-001" or "ESCALATE" in case_id:
            return DecisionRecommendation(
                recommendation_id=f"REC-{uuid.uuid4().hex[:6].upper()}",
                case_id=case_id,
                action_type=ActionType.ESCALATE,
                confidence_score=0.94,
                rationale="Conflicting beneficiary records detected between Account Directory and Standing Instructions. Multiple possible IBAN corrections found; automated repair unsafe without counterparty confirmation.",
                proposed_changes=[],
                corroborating_evidence=[
                    CorroboratingEvidenceRef(
                        evidence_id="EVD-BEN-CONFLICT",
                        evidence_type="BENEFICIARY_PROFILE",
                        citation="Beneficiary registry returned two distinct active IBANs with mismatched sort codes."
                    )
                ],
                risk_evaluation=RiskEvaluation(
                    risk_level=ExceptionSeverity.HIGH,
                    risk_score=0.75,
                    risk_factors=["AMBIGUOUS_REPAIR_CANDIDATES", "POTENTIAL_PAYMENT_MISDIRECTION"],
                    dual_auth_required=True
                ),
                model_identifier="mock-governed-reasoner-v1",
                prompt_tokens=620,
                completion_tokens=140
            )

        if scenario_key == "IBAN-MISSING-EVIDENCE-001" or not context.evidence_items:
            return DecisionRecommendation(
                recommendation_id=f"REC-{uuid.uuid4().hex[:6].upper()}",
                case_id=case_id,
                action_type=ActionType.INSUFFICIENT_EVIDENCE,
                confidence_score=0.98,
                rationale="Mandatory account directory and beneficiary profile evidence could not be retrieved. Policy POL-IBAN-AUTO-REPAIR strictly forbids automated or manual field alteration without verified directory records.",
                proposed_changes=[],
                corroborating_evidence=[],
                risk_evaluation=RiskEvaluation(
                    risk_level=ExceptionSeverity.MEDIUM,
                    risk_score=0.50,
                    risk_factors=["MISSING_MANDATORY_EVIDENCE", "UNABLE_TO_VERIFY_MOD97"],
                    dual_auth_required=False
                ),
                model_identifier="mock-governed-reasoner-v1",
                prompt_tokens=410,
                completion_tokens=110
            )

        orig_masked = context.tokenized_payment.creditor_account.masked_identifier or "GB82****765432"
        corrected_raw = "GB82WEST12345698765431"
        proposed_masked = token_vault.mask_identifier(corrected_raw)
        
        rec = DecisionRecommendation(
            recommendation_id=f"REC-{uuid.uuid4().hex[:6].upper()}",
            case_id=case_id,
            action_type=ActionType.REPAIR_IBAN,
            confidence_score=0.96,
            rationale=f"Beneficiary IBAN checksum corrected from ...{orig_masked[-4:]} to ...{proposed_masked[-4:]}. Corrected IBAN matches verified Standing Instructions in Beneficiary Master Directory and satisfies ISO 7064 MOD-97 check.",
            proposed_changes=[
                ProposedFieldChange(
                    field_path="creditor_account.iban",
                    original_value_masked=orig_masked,
                    proposed_value_masked=proposed_masked,
                    raw_proposed_value=corrected_raw,
                    justification="Typographical checksum error in check digits; matched standing instruction record.",
                    validation_status="MOD97_VALIDATED"
                )
            ],
            corroborating_evidence=[
                CorroboratingEvidenceRef(
                    evidence_id="EVD-BEN-01",
                    evidence_type="BENEFICIARY_PROFILE",
                    citation="Beneficiary Master Directory standing instruction active since 2026-01-15."
                ),
                CorroboratingEvidenceRef(
                    evidence_id="EVD-ACC-01",
                    evidence_type="ACCOUNT_DIRECTORY",
                    citation="National Westminster Bank PLC BIC WESTGB2L clearing directory validated."
                )
            ],
            risk_evaluation=RiskEvaluation(
                risk_level=ExceptionSeverity.LOW if amount < settings.DUAL_AUTH_THRESHOLD else ExceptionSeverity.HIGH,
                risk_score=0.12 if amount < settings.DUAL_AUTH_THRESHOLD else 0.45,
                risk_factors=[] if amount < settings.DUAL_AUTH_THRESHOLD else ["HIGH_VALUE_TRANSACTION_THRESHOLD_EXCEEDED"],
                dual_auth_required=amount >= settings.DUAL_AUTH_THRESHOLD
            ),
            model_identifier="mock-governed-reasoner-v1",
            prompt_tokens=580,
            completion_tokens=165
        )
        return rec

model_gateway = ModelGateway()
''')

# 6. decision_engine.py
with open(os.path.join(srv_dir, "decision_engine.py"), "w", encoding="utf-8") as f:
    f.write('''"""Decision Engine: Evaluates AI recommendations against institutional governance policies."""
from typing import Dict, Any, Tuple
from app.schemas.recommendation import DecisionRecommendation, ActionType
from app.schemas.canonical import ExceptionProfile
from app.config import settings

class DecisionEngine:
    def evaluate_governance_gate(
        self,
        recommendation: DecisionRecommendation,
        profile: ExceptionProfile,
        amount: float
    ) -> Tuple[bool, str]:
        if recommendation.action_type in [ActionType.REPAIR_IBAN, ActionType.REPAIR_BIC, ActionType.REPAIR_AND_RESUBMIT]:
            if recommendation.confidence_score < 0.85:
                return False, "Confidence score below institutional threshold (0.85). Action routed for manual investigation."
            return True, "Passed to Human-in-the-Loop Approval Queue."

        if recommendation.action_type == ActionType.ESCALATE:
            return True, "Escalation confirmed. Routed to Senior Tier 2 Operations Queue."

        if recommendation.action_type == ActionType.INSUFFICIENT_EVIDENCE:
            return True, "Safe Non-Action enforced. Case held pending missing evidence retrieval."

        return True, "Passed"

decision_engine = DecisionEngine()
''')

print("Wrote context_builder.py, model_gateway.py, and decision_engine.py")
