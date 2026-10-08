"""Dynamic Evidence Configuration Resolver.

Resolves published Bank Evidence Required JSON configurations per (tenant_id, profile_id)
and evaluates conditional rule applicability against transaction context.
Reference: PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md Section 3 & 4.
"""
from typing import Dict, List, Any, Optional, Set
from pydantic import BaseModel, Field

from app.schemas.contracts.evidence_config_schemas import (
    BankEvidenceRequiredConfig,
    EvidenceRuleDefinition,
    EvidenceAcquisitionMode,
    HitlWorkflowConfig,
)
from app.schemas.contracts.evidence_schemas import TrustTier
from app.ports.configuration_port import ConfigurationSchemaPort
from app.services.conditional_expression_engine import ConditionalExpressionEngine


class ResolvedEvidenceRequirements(BaseModel):
    """The evaluated, active evidence requirements for a specific exception transaction."""
    tenant_id: str
    profile_id: str
    config_version: str
    active_mandatory_types: List[str] = Field(default_factory=list)
    active_optional_types: List[str] = Field(default_factory=list)
    min_trust_tiers: Dict[str, TrustTier] = Field(default_factory=dict)
    acquisition_modes: Dict[str, List[EvidenceAcquisitionMode]] = Field(default_factory=dict)
    ttl_seconds: Dict[str, int] = Field(default_factory=dict)
    hitl_config: Optional[HitlWorkflowConfig] = None
    applied_rules: List[str] = Field(default_factory=list)


class DynamicEvidenceConfigResolver:
    """Service that resolves and evaluates published evidence configurations."""

    def __init__(self, config_port: ConfigurationSchemaPort):
        self._config_port = config_port

    def resolve_requirements(
        self,
        tenant_id: str,
        profile_id: str,
        transaction_context: Dict[str, Any]
    ) -> ResolvedEvidenceRequirements:
        """Resolves published configuration and evaluates conditional expressions for the transaction.

        Args:
            tenant_id: Bank identifier.
            profile_id: Exception profile code (e.g., 'DQ-01', 'PR-08').
            transaction_context: Payment attributes (amount, currency, rail, etc.).

        Returns:
            ResolvedEvidenceRequirements: Active mandatory and optional evidence requirements.
        """
        profile_norm = (profile_id or "UNKNOWN").upper()
        tenant_norm = (tenant_id or "DEFAULT_BANK").strip()

        # 1. Look up published config for specific tenant
        config = self._config_port.get_evidence_config(tenant_norm, profile_norm)

        # 2. Fall back to DEFAULT_BANK if tenant override is not present
        if not config and tenant_norm != "DEFAULT_BANK":
            config = self._config_port.get_evidence_config("DEFAULT_BANK", profile_norm)

        # 3. Fall back to canonical defaults if unconfigured
        if not config:
            config = self._create_canonical_fallback(tenant_norm, profile_norm)

        active_mandatory: List[str] = []
        active_optional: List[str] = []
        min_trust_tiers: Dict[str, TrustTier] = {}
        acquisition_modes: Dict[str, List[EvidenceAcquisitionMode]] = {}
        ttl_seconds: Dict[str, int] = {}
        applied_rules: List[str] = []

        for rule in config.rules:
            # Evaluate conditional expression
            is_active = True
            if rule.condition_expression:
                is_active = ConditionalExpressionEngine.evaluate(rule.condition_expression, transaction_context)

            if is_active:
                applied_rules.append(rule.rule_id)
                min_trust_tiers[rule.evidence_type] = rule.min_trust_tier
                acquisition_modes[rule.evidence_type] = rule.acquisition_modes
                ttl_seconds[rule.evidence_type] = rule.freshness_ttl_seconds

                if rule.mandatory:
                    active_mandatory.append(rule.evidence_type)
                else:
                    active_optional.append(rule.evidence_type)

        return ResolvedEvidenceRequirements(
            tenant_id=config.tenant_id,
            profile_id=config.profile_id,
            config_version=config.config_version,
            active_mandatory_types=active_mandatory,
            active_optional_types=active_optional,
            min_trust_tiers=min_trust_tiers,
            acquisition_modes=acquisition_modes,
            ttl_seconds=ttl_seconds,
            hitl_config=config.hitl_config,
            applied_rules=applied_rules
        )

    def _create_canonical_fallback(self, tenant_id: str, profile_id: str) -> BankEvidenceRequiredConfig:
        """Generates canonical baseline configuration if none is explicitly published."""
        fallback_mandatory_map = {
            "DQ-01": [("CORE_DDA_ACCOUNT", TrustTier.TIER_1_CORE_RECORD), ("ROUTING_DIRECTORY", TrustTier.TIER_2_REGULATORY_SCHEME)],
            "DQ-08": [("FEDLINE_ROUTING_DIRECTORY", TrustTier.TIER_2_REGULATORY_SCHEME), ("ROUTING_SYNTAX_MASTER", TrustTier.TIER_2_REGULATORY_SCHEME)],
            "PR-01": [("HISTORICAL_PAYMENT_JOURNAL", TrustTier.TIER_1_CORE_RECORD), ("SETTLEMENT_LEDGER", TrustTier.TIER_1_CORE_RECORD)],
            "PR-08": [("STREAMING_BROKER_JOURNAL", TrustTier.TIER_1_CORE_RECORD), ("DLQ_RECORD", TrustTier.TIER_1_CORE_RECORD)],
            "ST-01": [("INWARD_PACS004_RETURN", TrustTier.TIER_1_CORE_RECORD), ("ORIGINAL_DEBIT_RECORD", TrustTier.TIER_1_CORE_RECORD)],
            "CO-04": [("SANCTIONS_WATCHLIST", TrustTier.TIER_2_REGULATORY_SCHEME), ("CORRIDOR_POLICY_MATRIX", TrustTier.TIER_2_REGULATORY_SCHEME)],
        }
        pairs = fallback_mandatory_map.get(profile_id, [("CORE_DDA_ACCOUNT", TrustTier.TIER_1_CORE_RECORD)])
        
        rules = [
            EvidenceRuleDefinition(
                rule_id=f"RULE-{profile_id}-{i+1:02d}",
                evidence_type=ev_type,
                mandatory=True,
                min_trust_tier=tier,
                condition_expression=None,
                acquisition_modes=[
                    EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD,
                    EvidenceAcquisitionMode.MODE_3_BANK_PUSH,
                    EvidenceAcquisitionMode.MODE_4_HITL_OPERATOR
                ],
                freshness_ttl_seconds=86400,
                description=f"Standard mandatory baseline for {ev_type}"
            )
            for i, (ev_type, tier) in enumerate(pairs)
        ]

        return BankEvidenceRequiredConfig(
            tenant_id=tenant_id,
            profile_id=profile_id,
            config_version="1.0.0-CANONICAL-FALLBACK",
            published_by="PEX_SYSTEM_DEFAULTS",
            rules=rules
        )
