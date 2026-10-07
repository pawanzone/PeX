"""Evidence Contract & Dossier Schemas for PeX Evidence-Driven STP Architecture.

Defines WHAT evidence must exist, its trust hierarchy tier, freshness criteria,
and contradiction behavior, strictly decoupled from network transport mechanisms.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class EvidenceTrustTier(str, Enum):
    """Authoritative Evidence Trust Tiers (Tier 1 is highest authority)."""
    TIER_1_BANK_AUTHORITATIVE = "TIER_1_BANK_AUTHORITATIVE"   # Core DDA, Customer Master, SSI Master, AML/TM
    TIER_2_EXTERNAL_AUTHORITATIVE = "TIER_2_EXTERNAL_AUTHORITATIVE" # SWIFTRef, FedLine, Pay.UK CoP, GLEIF LEI
    TIER_3_PEX_DERIVED = "TIER_3_PEX_DERIVED"                 # MOD-97 check, XSD parsing, SHA-256 hash collision
    TIER_4_HISTORICAL_PRECEDENT = "TIER_4_HISTORICAL_PRECEDENT" # Historical audit logs, past successful repairs


class EvidenceItemRequirement(BaseModel):
    """Specification of a single evidence requirement within an Evidence Contract."""
    item_name: str
    description: str
    role: str = "VALIDATION"                                  # IDENTIFICATION, VALIDATION, CORROBORATION, CONTEXT
    required_trust_tier: EvidenceTrustTier
    is_mandatory_for_stp: bool = True
    policy_freshness_seconds: Optional[int] = None           # Configurable TTL (None = message-scoped / no expiration)
    fallback_behavior: str = "SUSPEND_TO_OPERATIONS"
    contradiction_behavior: str = "SUSPEND_TO_INVESTIGATION"


class EvidenceContract(BaseModel):
    """The Evidence Contract defining all data requirements for a specific exception profile."""
    profile_id: str
    profile_name: str
    mandatory_evidence: List[EvidenceItemRequirement] = Field(default_factory=list)
    conditional_evidence: List[EvidenceItemRequirement] = Field(default_factory=list)
    optional_evidence: List[EvidenceItemRequirement] = Field(default_factory=list)
    audit_provenance_required: bool = True


class EvidenceItem(BaseModel):
    """A concrete evidence artifact gathered for an exception case."""
    item_name: str
    source_name: str
    trust_tier: EvidenceTrustTier
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)
    attestation_signature: Optional[str] = None
    is_valid: bool = True
    validation_error: Optional[str] = None


class EvidenceDossier(BaseModel):
    """Aggregated container of all evidence collected for a specific exception case."""
    case_id: str
    profile_id: str
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    items: Dict[str, EvidenceItem] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_item(self, item: EvidenceItem):
        self.items[item.item_name] = item

    def get_item(self, item_name: str) -> Optional[EvidenceItem]:
        return self.items.get(item_name)


class EvidenceContractRegistry:
    """Registry maintaining authoritative Evidence Contracts across the 41 BIAN exception profiles."""

    def __init__(self):
        self._contracts: Dict[str, EvidenceContract] = {}
        self._register_default_contracts()

    def register(self, contract: EvidenceContract):
        self._contracts[contract.profile_id] = contract

    def get_contract(self, profile_id: str) -> Optional[EvidenceContract]:
        return self._contracts.get(profile_id)

    def _register_default_contracts(self):
        # PR-03: ISO20022_ERROR (Phase 1 Vertical Slice Baseline)
        pr03_contract = EvidenceContract(
            profile_id="PR-03",
            profile_name="ISO20022_ERROR",
            mandatory_evidence=[
                EvidenceItemRequirement(
                    item_name="RAW_PAYLOAD",
                    description="Raw inbound payment exception message payload (XML or JSON string)",
                    role="IDENTIFICATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None # Scoped to the active message transaction
                ),
                EvidenceItemRequirement(
                    item_name="ISO20022_SCHEMA_SPEC",
                    description="Authoritative ISO 20022 / CBPR+ XML schema and structural rules definition",
                    role="VALIDATION",
                    required_trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None # Static release-bound schema standard
                ),
            ],
            conditional_evidence=[],
            optional_evidence=[
                EvidenceItemRequirement(
                    item_name="HISTORICAL_REPAIR_PATTERN",
                    description="Historical record of past XML tag re-sequencing for similar message structures",
                    role="CONTEXT",
                    required_trust_tier=EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT,
                    is_mandatory_for_stp=False,
                    policy_freshness_seconds=None
                )
            ]
        )
        self.register(pr03_contract)

        # PR-05: CORRUPTED_MESSAGE_FORMAT (Phase 2A Slice 1)
        pr05_contract = EvidenceContract(
            profile_id="PR-05",
            profile_name="CORRUPTED_MESSAGE_FORMAT",
            mandatory_evidence=[
                EvidenceItemRequirement(
                    item_name="RAW_PAYLOAD_BYTES",
                    description="Inbound raw payment exception payload bytes or string",
                    role="IDENTIFICATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="TARGET_SCHEME_CHARSET_SPEC",
                    description="Target scheme character set specification (e.g. SWIFT CBPR+ X-Set, ISO 20022 UTF-8)",
                    role="VALIDATION",
                    required_trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="BANK_TRANSLITERATION_POLICY",
                    description="Bank operational policy defining authorized transliterations and corridor character rules",
                    role="AUTHORIZATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
            ],
            conditional_evidence=[],
            optional_evidence=[
                EvidenceItemRequirement(
                    item_name="HISTORICAL_ENCODING_LOG",
                    description="Historical record of past character encodings and transliterations",
                    role="CONTEXT",
                    required_trust_tier=EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT,
                    is_mandatory_for_stp=False,
                    policy_freshness_seconds=None
                )
            ]
        )
        self.register(pr05_contract)

        # PR-08: UNSUPPORTED_SPECIAL_CHARACTERS (Phase 2A Slice 2)
        pr08_contract = EvidenceContract(
            profile_id="PR-08",
            profile_name="UNSUPPORTED_SPECIAL_CHARACTERS",
            mandatory_evidence=[
                EvidenceItemRequirement(
                    item_name="RAW_PAYLOAD",
                    description="Raw payment exception payload containing unsupported special characters",
                    role="IDENTIFICATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="TARGET_RAIL_CHARSET_SPEC",
                    description="Target clearing rail character set specification (e.g. SWIFT X-Set, Fedwire 18-char, CHAPS)",
                    role="VALIDATION",
                    required_trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="BANK_CHARACTER_SUBSTITUTION_POLICY",
                    description="Bank operational policy defining authorized character substitutions and corridor rules",
                    role="AUTHORIZATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="PROCESSING_STATE_RECORD",
                    description="Processing state metadata including queue status, retry count, and idempotency key",
                    role="VALIDATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
            ],
            conditional_evidence=[],
            optional_evidence=[
                EvidenceItemRequirement(
                    item_name="HISTORICAL_CHARACTER_LOG",
                    description="Historical record of past character substitutions and precedents",
                    role="CONTEXT",
                    required_trust_tier=EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT,
                    is_mandatory_for_stp=False,
                    policy_freshness_seconds=None
                )
            ]
        )
        self.register(pr08_contract)

        # DQ-05: INVALID_BENEFICIARY_POSTAL_ADDRESS (Phase 2A Slice 2)
        dq05_contract = EvidenceContract(
            profile_id="DQ-05",
            profile_name="INVALID_BENEFICIARY_POSTAL_ADDRESS",
            mandatory_evidence=[
                EvidenceItemRequirement(
                    item_name="RAW_PAYLOAD",
                    description="Raw payment exception payload containing beneficiary postal address (Cdtr/PstlAdr)",
                    role="IDENTIFICATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="POSTAL_STANDARD_SPEC",
                    description="UPU S42 and ISO 20022 postal address format structural specification",
                    role="VALIDATION",
                    required_trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="BANK_ADDRESS_POLICY",
                    description="Bank operational address policy governing normalization, parsing, and corridor validation",
                    role="AUTHORIZATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
            ],
            conditional_evidence=[
                EvidenceItemRequirement(
                    item_name="BENEFICIARY_MASTER_RECORD",
                    description="Authoritative bank customer or beneficiary master record for address corroboration",
                    role="CORROBORATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=False,
                    policy_freshness_seconds=86400 # 24 hour freshness
                ),
                EvidenceItemRequirement(
                    item_name="EXTERNAL_POSTAL_DIRECTORY",
                    description="External authoritative postal authority directory for country/postal code validation",
                    role="VALIDATION",
                    required_trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    is_mandatory_for_stp=False,
                    policy_freshness_seconds=604800 # 7 days
                )
            ],
            optional_evidence=[
                EvidenceItemRequirement(
                    item_name="HISTORICAL_ADDRESS_PRECEDENT",
                    description="Historical record of prior address resolutions for same beneficiary identity",
                    role="CONTEXT",
                    required_trust_tier=EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT,
                    is_mandatory_for_stp=False,
                    policy_freshness_seconds=None
                )
            ]
        )
        self.register(dq05_contract)

        # PR-01: DUPLICATE_PAYMENT (Phase 2A Slice 3)
        pr01_contract = EvidenceContract(
            profile_id="PR-01",
            profile_name="DUPLICATE_PAYMENT",
            mandatory_evidence=[
                EvidenceItemRequirement(
                    item_name="RAW_PAYLOAD",
                    description="Inbound raw payment exception payload candidate for duplicate analysis",
                    role="IDENTIFICATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="PAYMENT_IDENTITY_RECORD",
                    description="Deterministic payment fingerprint and identity components (UETR, canonical hash, E2E ID, accounts, amount)",
                    role="IDENTIFICATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="CURRENT_SETTLEMENT_STATE",
                    description="Authoritative current bank ledger and settlement state record (SETTLED, UNSETTLED, ALREADY_RELEASED, CANCELLED)",
                    role="AUTHORIZATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=3600 # 1 hour max ledger cache
                ),
                EvidenceItemRequirement(
                    item_name="BANK_DUPLICATE_POLICY",
                    description="Bank operational duplicate detection, suppression, and threshold policy",
                    role="AUTHORIZATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
            ],
            conditional_evidence=[],
            optional_evidence=[
                EvidenceItemRequirement(
                    item_name="HISTORICAL_PAYMENT_INDEX",
                    description="Historical payment index for similarity search, pattern clustering, and operator context",
                    role="CONTEXT",
                    required_trust_tier=EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT,
                    is_mandatory_for_stp=False,
                    policy_freshness_seconds=None
                )
            ]
        )
        self.register(pr01_contract)

        # DQ-08: INVALID_BIC_SWIFT (Phase 2A Slice 3)
        dq08_contract = EvidenceContract(
            profile_id="DQ-08",
            profile_name="INVALID_BIC_SWIFT",
            mandatory_evidence=[
                EvidenceItemRequirement(
                    item_name="RAW_PAYLOAD",
                    description="Raw payment exception payload containing original BIC element",
                    role="IDENTIFICATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="ORIGINAL_BIC_RECORD",
                    description="Extracted original BIC string, field location, and target institution details",
                    role="IDENTIFICATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
                EvidenceItemRequirement(
                    item_name="BIC_REFERENCE_DIRECTORY",
                    description="Authoritative external reference data directory for ISO 9362 BIC status, successors, and reachability",
                    role="VALIDATION",
                    required_trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=86400 # 24 hours freshness window
                ),
                EvidenceItemRequirement(
                    item_name="BANK_COUNTERPARTY_SSI",
                    description="Authoritative bank counterparty Standard Settlement Instructions (SSI) and master routing rules",
                    role="AUTHORIZATION",
                    required_trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=86400
                ),
                EvidenceItemRequirement(
                    item_name="TARGET_RAIL_ROUTING_SPEC",
                    description="Target clearing rail routing rules, reachability parameters, and corridor constraints",
                    role="VALIDATION",
                    required_trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    is_mandatory_for_stp=True,
                    policy_freshness_seconds=None
                ),
            ],
            conditional_evidence=[],
            optional_evidence=[
                EvidenceItemRequirement(
                    item_name="HISTORICAL_BIC_DIRECTORY",
                    description="Historical log of past BIC resolutions, migrations, and institution precedents",
                    role="CONTEXT",
                    required_trust_tier=EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT,
                    is_mandatory_for_stp=False,
                    policy_freshness_seconds=None
                )
            ]
        )
        self.register(dq08_contract)


# Global singleton registry instance
evidence_registry = EvidenceContractRegistry()

