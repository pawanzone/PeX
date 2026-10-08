"""Bank Evidence Required Configuration Schemas.

Authoritative schema definitions for the single, published Bank Evidence Required JSON
binding per (tenant_id, profile_id).
Reference: PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md Section 3.
"""
import hashlib
import json
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.schemas.contracts.evidence_schemas import TrustTier


class EvidenceAcquisitionMode(str, Enum):
    """Supported acquisition modes for evidence gathering."""
    MODE_1_INBOUND_PAYLOAD = "MODE_1_INBOUND_PAYLOAD"       # Pre-gathered in error JSON / transaction payload
    MODE_2_API_CONNECTOR = "MODE_2_API_CONNECTOR"           # Automated outbound query via Port adapter
    MODE_3_BANK_PUSH = "MODE_3_BANK_PUSH"                   # Asynchronous bank push via webhook/event
    MODE_4_HITL_OPERATOR = "MODE_4_HITL_OPERATOR"           # Human-in-the-loop manual entry in PeX UI


class HitlFieldType(str, Enum):
    """Field types for interactive Mode 4 human operator data entry."""
    TEXT = "text"
    NUMBER = "number"
    IBAN = "iban"
    BIC = "bic"
    DROPDOWN = "dropdown"
    BOOLEAN = "boolean"
    DOCUMENT = "document"


class HitlFieldDefinition(BaseModel):
    """Specification of an interactive input field in the PeX resolution workspace."""
    field_id: str
    label: str
    field_type: HitlFieldType = HitlFieldType.TEXT
    required: bool = True
    validation_regex: Optional[str] = None
    allowed_values: Optional[List[str]] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = None


class HitlWorkflowConfig(BaseModel):
    """Configuration for HITL human-in-the-loop interaction when evidence is missing."""
    enabled: bool = True
    target_role: str = "PAYMENT_OPERATOR"   # "PAYMENT_OPERATOR", "COMPLIANCE_OFFICER", "RISK_APPROVER"
    fields: List[HitlFieldDefinition] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=lambda: ["SUPPLY_EVIDENCE", "CONFIRM_REPAIR", "ESCALATE", "REJECT"])
    auto_re_evaluate: bool = True           # Immediately trigger 8-predicate re-evaluation upon submit


class EvidenceRuleDefinition(BaseModel):
    """Individual rule defining an evidence requirement within a published profile config."""
    rule_id: str
    evidence_type: str                      # e.g., "CORE_DDA_ACCOUNT", "ROUTING_DIRECTORY"
    mandatory: bool = True
    min_trust_tier: TrustTier = TrustTier.TIER_3_CLIENT_ERP
    condition_expression: Optional[str] = None  # e.g. "amount > 100000", "currency == 'USD'", None for unconditional
    acquisition_modes: List[EvidenceAcquisitionMode] = Field(
        default_factory=lambda: [
            EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD,
            EvidenceAcquisitionMode.MODE_3_BANK_PUSH,
            EvidenceAcquisitionMode.MODE_4_HITL_OPERATOR
        ]
    )
    freshness_ttl_seconds: int = 86400      # 24 hours default TTL
    description: Optional[str] = None


class BankEvidenceRequiredConfig(BaseModel):
    """Published, immutable single configuration document per (tenant_id, profile_id).

    Zero 3-way runtime merging: This document represents the single authoritative rule binding.
    """
    tenant_id: str = "DEFAULT_BANK"
    profile_id: str                         # e.g. "DQ-01", "DQ-08", "PR-01", "PR-08", "ST-01", "CO-04"
    config_version: str = "1.0.0"
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_by: str = "PEX_GOVERNANCE_SYSTEM"
    is_active: bool = True
    rules: List[EvidenceRuleDefinition] = Field(default_factory=list)
    hitl_config: Optional[HitlWorkflowConfig] = None
    governance_hash: Optional[str] = None

    def compute_governance_hash(self) -> str:
        """Computes deterministic SHA-256 hash of rules and parameters for tamper evidence."""
        rules_repr = [
            {
                "rule_id": r.rule_id,
                "evidence_type": r.evidence_type,
                "mandatory": r.mandatory,
                "min_trust_tier": int(r.min_trust_tier.value),
                "condition_expression": r.condition_expression
            }
            for r in sorted(self.rules, key=lambda x: x.rule_id)
        ]
        raw_repr = {
            "tenant_id": self.tenant_id,
            "profile_id": self.profile_id,
            "config_version": self.config_version,
            "rules": rules_repr
        }
        serialized = json.dumps(raw_repr, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def model_post_init(self, __context: Any) -> None:
        if not self.governance_hash:
            self.governance_hash = self.compute_governance_hash()


class HitlEvidenceSubmissionRequest(BaseModel):
    """Payload submitted by a human operator providing missing evidence in Mode 4."""
    case_id: str
    tenant_id: str = "DEFAULT_BANK"
    profile_id: str
    operator_id: str
    operator_role: str = "PAYMENT_OPERATOR"
    submitted_fields: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    action: str = "SUPPLY_EVIDENCE"


class HitlEvidenceSubmissionResponse(BaseModel):
    """Response returned immediately after operator evidence submission and re-evaluation."""
    case_id: str
    submission_id: str
    is_accepted: bool
    re_evaluation_triggered: bool
    new_evidence_sufficient: bool
    new_stp_eligible: bool
    new_status: str
    missing_evidence_remaining: List[str] = Field(default_factory=list)
    message: str
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
