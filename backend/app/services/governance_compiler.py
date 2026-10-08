"""Governance Compiler & Configuration Validator for PeX.

Applies fail-closed architectural and regulatory rules to validate candidate Bank Evidence
Required JSON configurations before publication.
Reference: PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md Section 4.
"""
from typing import List, Dict, Any, Set, Tuple
from app.schemas.contracts.evidence_config_schemas import (
    BankEvidenceRequiredConfig,
    EvidenceRuleDefinition,
    HitlWorkflowConfig,
)
from app.schemas.contracts.evidence_schemas import TrustTier
from app.services.conditional_expression_engine import ConditionalExpressionEngine


class GovernanceValidationError(Exception):
    """Exception raised when a bank evidence configuration violates architectural or regulatory invariants."""
    def __init__(self, code: str, message: str, details: Dict[str, Any] = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.details = details or {}


class GovernanceCompiler:
    """Fail-closed compiler and validator for Bank Evidence Required configurations."""

    # Regulatory baseline mandates that cannot be bypassed or weakened
    REGULATORY_MANDATES: Dict[str, List[Dict[str, Any]]] = {
        "CO-04": [
            {
                "evidence_type": "SANCTIONS_WATCHLIST",
                "required_mandatory": True,
                "max_trust_tier": TrustTier.TIER_2_REGULATORY_SCHEME,
                "description": "Sanctions watchlist screening mandate cannot be downgraded or disabled."
            }
        ],
        "DQ-01": [
            {
                "evidence_type": "ROUTING_DIRECTORY",
                "required_mandatory": True,
                "max_trust_tier": TrustTier.TIER_2_REGULATORY_SCHEME,
                "description": "National/SWIFT routing directory lookup required for IBAN verification."
            }
        ],
        "PR-01": [
            {
                "evidence_type": "SETTLEMENT_LEDGER",
                "required_mandatory": True,
                "max_trust_tier": TrustTier.TIER_1_CORE_RECORD,
                "description": "Duplicate payment determination requires Tier 1 Core settlement ledger record."
            }
        ]
    }

    ALLOWED_CONTEXT_VARIABLES: Set[str] = {
        "amount",
        "currency",
        "corridor",
        "clearing_rail",
        "error_code",
        "creditor_country",
        "debtor_country",
        "is_cross_border",
        "counterparty_type",
        "channel",
        "exception_age_hours"
    }

    @classmethod
    def compile_and_validate(cls, config: BankEvidenceRequiredConfig) -> Tuple[bool, List[str]]:
        """Compiles and strictly validates a BankEvidenceRequiredConfig document.

        Args:
            config: Candidate configuration document.

        Returns:
            Tuple[bool, List[str]]: (True, warnings) if valid.

        Raises:
            GovernanceValidationError: If any architectural or regulatory invariant is violated.
        """
        warnings: List[str] = []

        # 1. Profile and Tenant ID checks
        if not config.profile_id or not config.profile_id.strip():
            raise GovernanceValidationError(
                "ERR_MISSING_PROFILE_ID",
                "Configuration must specify a non-empty profile_id."
            )
        if not config.tenant_id or not config.tenant_id.strip():
            raise GovernanceValidationError(
                "ERR_MISSING_TENANT_ID",
                "Configuration must specify a non-empty tenant_id."
            )

        # 2. Rule Count Check
        if not config.rules:
            raise GovernanceValidationError(
                "ERR_EMPTY_RULES",
                f"Configuration for profile '{config.profile_id}' must define at least one evidence rule."
            )

        mandatory_count = 0
        rule_types: Set[str] = set()

        for r in config.rules:
            # Check duplicate rule IDs or evidence types
            if r.evidence_type in rule_types:
                raise GovernanceValidationError(
                    "ERR_DUPLICATE_EVIDENCE_TYPE",
                    f"Duplicate evidence_type '{r.evidence_type}' in profile '{config.profile_id}'."
                )
            rule_types.add(r.evidence_type)

            if r.mandatory:
                mandatory_count += 1

            # 3. Trust Tier Floor Invariants
            # Tier 4 (AI / Historical Precedent) carries 0% sovereign authority and cannot be sole proof
            if r.min_trust_tier == TrustTier.TIER_4_HISTORICAL_AI and r.mandatory:
                warnings.append(
                    f"Rule '{r.rule_id}' specifies Tier 4 (AI/Advisory) as mandatory. "
                    f"Tier 4 carries 0% sovereign authority under PeX governance."
                )

            # 4. Conditional Expression Validation
            if r.condition_expression:
                try:
                    vars_found = ConditionalExpressionEngine.extract_variables(r.condition_expression)
                    # Check for unknown context variables
                    unknown_vars = vars_found - cls.ALLOWED_CONTEXT_VARIABLES
                    if unknown_vars:
                        raise GovernanceValidationError(
                            "ERR_UNKNOWN_CONTEXT_VARIABLE",
                            f"Rule '{r.rule_id}' references unknown context variables: {unknown_vars}. "
                            f"Permitted variables: {sorted(cls.ALLOWED_CONTEXT_VARIABLES)}"
                        )
                except Exception as e:
                    if isinstance(e, GovernanceValidationError):
                        raise
                    raise GovernanceValidationError(
                        "ERR_INVALID_EXPRESSION_SYNTAX",
                        f"Rule '{r.rule_id}' has invalid condition expression '{r.condition_expression}': {e}"
                    )

            # 5. Acquisition Mode Check
            if not r.acquisition_modes:
                raise GovernanceValidationError(
                    "ERR_NO_ACQUISITION_MODES",
                    f"Rule '{r.rule_id}' must specify at least one permitted acquisition mode."
                )

        # 6. Regulatory Baseline Non-Degradation Check (Evaluated with high priority)
        profile_norm = config.profile_id.upper()
        if profile_norm in cls.REGULATORY_MANDATES:
            for mandate in cls.REGULATORY_MANDATES[profile_norm]:
                req_type = mandate["evidence_type"]
                rule_match = next((r for r in config.rules if r.evidence_type == req_type), None)

                if not rule_match:
                    raise GovernanceValidationError(
                        "REJECT_REGULATORY_RULE_DOWNGRADE",
                        f"Mandatory regulatory rule '{req_type}' missing for profile '{profile_norm}'. {mandate['description']}"
                    )

                if mandate["required_mandatory"] and not rule_match.mandatory:
                    raise GovernanceValidationError(
                        "REJECT_REGULATORY_RULE_DOWNGRADE",
                        f"Regulatory rule '{req_type}' cannot be marked mandatory=False in profile '{profile_norm}'."
                    )

                if int(rule_match.min_trust_tier.value) > int(mandate["max_trust_tier"].value):
                    raise GovernanceValidationError(
                        "REJECT_REGULATORY_TRUST_TIER_DOWNGRADE",
                        f"Regulatory rule '{req_type}' trust tier cannot be downgraded to {rule_match.min_trust_tier.name}. "
                        f"Maximum allowed tier is {mandate['max_trust_tier'].name}."
                    )

        if mandatory_count == 0:
            raise GovernanceValidationError(
                "ERR_NO_MANDATORY_RULES",
                f"Configuration for profile '{config.profile_id}' must have at least one mandatory rule."
            )


        # 7. HITL Workflow Consistency Check
        if config.hitl_config and config.hitl_config.enabled:
            if not config.hitl_config.target_role:
                raise GovernanceValidationError(
                    "ERR_INVALID_HITL_CONFIG",
                    "HITL workflow configuration must specify a non-empty target_role."
                )
            if not config.hitl_config.fields:
                warnings.append(
                    f"HITL workflow for profile '{config.profile_id}' is enabled with zero custom fields."
                )

        # 8. Governance Hash Verification
        computed_hash = config.compute_governance_hash()
        if config.governance_hash and config.governance_hash != computed_hash:
            raise GovernanceValidationError(
                "ERR_GOVERNANCE_HASH_MISMATCH",
                f"Governance signature hash mismatch. Provided: {config.governance_hash}, Computed: {computed_hash}"
            )

        return True, warnings
