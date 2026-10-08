"""In-Memory Reference Contextual Authority Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements ContextualAuthorityPort using multi-dimensional question-domain routing.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.ports.authority_port import ContextualAuthorityPort
from app.schemas.contracts.authority_schemas import (
    QuestionDomain,
    AuthorityClassification,
    AuthorityResolutionContext,
)


class InMemoryContextualAuthorityAdapter(ContextualAuthorityPort):
    """Hermetic reference implementation of ContextualAuthorityPort."""

    def resolve_authority(
        self,
        question_domain: QuestionDomain,
        context_payload: Dict[str, Any]
    ) -> AuthorityResolutionContext:
        now = datetime.now(timezone.utc)
        force_fail = context_payload.get("simulate_authority_unavailable", False)

        if force_fail:
            return AuthorityResolutionContext(
                question_domain=question_domain,
                primary_authority_source="SIMULATED_UNAVAILABLE_AUTHORITY",
                authority_classification=AuthorityClassification.CORE_SYSTEM_OF_RECORD,
                is_valid_authority=False,
                authority_sovereignty_level="UNAVAILABLE",
                evaluated_at=now,
                details=context_payload,
                rejection_reason="Simulated authority timeout / 503 unavailable."
            )

        if question_domain == QuestionDomain.LEGAL_PROHIBITION:
            return AuthorityResolutionContext(
                question_domain=question_domain,
                primary_authority_source="STATUTORY_OFAC_EU_REGISTRY",
                authority_classification=AuthorityClassification.STATUTORY_REGULATORY,
                is_valid_authority=True,
                authority_sovereignty_level="BINDING_LEGAL",
                evaluated_at=now,
                details={"scope": "GLOBAL_SANCTIONS_AML"}
            )
        elif question_domain == QuestionDomain.BANK_OPERATIONAL_PERMISSION:
            return AuthorityResolutionContext(
                question_domain=question_domain,
                primary_authority_source="BANK_RISK_POLICY_DB",
                authority_classification=AuthorityClassification.BANK_ENTERPRISE_POLICY,
                is_valid_authority=True,
                authority_sovereignty_level="BINDING_OPERATIONAL",
                evaluated_at=now,
                details={"policy_mode": "ACTIVE"}
            )
        elif question_domain == QuestionDomain.ACCOUNT_OWNERSHIP_BALANCE:
            return AuthorityResolutionContext(
                question_domain=question_domain,
                primary_authority_source="CORE_BANKING_DDA_MASTER",
                authority_classification=AuthorityClassification.CORE_SYSTEM_OF_RECORD,
                is_valid_authority=True,
                authority_sovereignty_level="BINDING_TRANSACTIONAL",
                evaluated_at=now,
                details={"source": "CORE_DDA"}
            )
        elif question_domain == QuestionDomain.QUEUE_PROCESSING_STATE:
            return AuthorityResolutionContext(
                question_domain=question_domain,
                primary_authority_source="STREAMING_MESSAGE_BROKER",
                authority_classification=AuthorityClassification.CORE_SYSTEM_OF_RECORD,
                is_valid_authority=True,
                authority_sovereignty_level="BINDING_TRANSACTIONAL",
                evaluated_at=now,
                details={"broker_state": "ACTIVE"}
            )
        elif question_domain == QuestionDomain.CLEARING_SETTLEMENT_STATUS:
            return AuthorityResolutionContext(
                question_domain=question_domain,
                primary_authority_source="RTGS_CLEARING_CALENDAR",
                authority_classification=AuthorityClassification.SCHEME_OPERATING_RULE,
                is_valid_authority=True,
                authority_sovereignty_level="BINDING_OPERATIONAL",
                evaluated_at=now,
                details={"rail": context_payload.get("rail", "FEDWIRE")}
            )
        else: # HISTORICAL_PRECEDENT
            return AuthorityResolutionContext(
                question_domain=question_domain,
                primary_authority_source="HISTORICAL_REPAIR_DB",
                authority_classification=AuthorityClassification.ADVISORY_CONTEXT,
                is_valid_authority=True,
                authority_sovereignty_level="ADVISORY_ONLY",
                evaluated_at=now,
                details={"historical_authority_weight_pct": 0.0}
            )
