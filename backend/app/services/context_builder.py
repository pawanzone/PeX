"""Context Builder: Assembles Tokenized Dossier for AI Model Gateway."""
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
