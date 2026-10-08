"""Contextual Authority Contract Schemas.

Defines the multi-dimensional contextual authority model where authority is evaluated
relative to the specific operational, legal, or transactional question.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class QuestionDomain(str, Enum):
    """Operational/Legal question domain."""
    LEGAL_PROHIBITION = "LEGAL_PROHIBITION"         # Sanctions, AML, FATF, Travel Rule
    BANK_OPERATIONAL_PERMISSION = "BANK_PERMISSION" # STP amount thresholds, credit limits, Maker-Checker rules
    ACCOUNT_OWNERSHIP_BALANCE = "ACCOUNT_BALANCE"   # Core DDA account state, ledger balance, freeze flags
    QUEUE_PROCESSING_STATE = "QUEUE_STATE"          # Broker queue depth, in-flight lease, poison message
    CLEARING_SETTLEMENT_STATUS = "CLEARING_STATUS"  # RTGS settlement status, scheme cutoff clocks, network reachability
    HISTORICAL_PRECEDENT = "HISTORICAL_PRECEDENT"   # Prior case repairs, statistical similarity (0% authority)


class AuthorityClassification(str, Enum):
    """Classification of the authority source."""
    STATUTORY_REGULATORY = "STATUTORY_REGULATORY"   # Tier 1 Sovereign Legal Override
    BANK_ENTERPRISE_POLICY = "BANK_POLICY"         # Tier 1 Bank Operational Permission
    CORE_SYSTEM_OF_RECORD = "CORE_SYSTEM_RECORD"   # Tier 1 Transactional Ground Truth
    SCHEME_OPERATING_RULE = "SCHEME_RULE"           # Clearing scheme directory / calendar
    ADVISORY_CONTEXT = "ADVISORY_CONTEXT"           # Tier 4 Context (0% authority)


class AuthorityResolutionContext(BaseModel):
    """Context and result of an authority lookup."""
    question_domain: QuestionDomain
    primary_authority_source: str                   # e.g., "CORE_DDA_FINACLE", "OFAC_SDN_REGISTRY", "BANK_RISK_POLICY"
    authority_classification: AuthorityClassification
    is_valid_authority: bool                        # V_auth component
    authority_sovereignty_level: str                # "BINDING_LEGAL", "BINDING_OPERATIONAL", "BINDING_TRANSACTIONAL", "ADVISORY_ONLY"
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
    rejection_reason: Optional[str] = None
